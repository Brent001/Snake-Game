"""Baked scenery: biome horizons, fog, vignettes, outdoor decor chunks, boss arenas, spell auras and bullet sprites.

Every function in the PAINT section is pure Python (no Tk) and returns an `Art`; the `SceneryBank` at the bottom turns
those into cached `tk.PhotoImage`s (optionally on a worker thread) so the per-frame cost of any of this scenery is a
handful of `create_image` calls.
"""
import colorsys
import json
import math
from pathlib import Path
import random
import threading
import queue

from ..config import CELL
from .pixelart import Art, BAYER, blend, photo, rgba

SC = 3                       # backdrop / arena pixel size (real px per painted pixel)
DSC = 2                      # decor chunk pixel size
CHUNK = 16                   # decor chunk side, in cells
BIOME_KEYS = ("frost", "lake", "forest", "scarlet", "nether", "shrine")

# sky ramps (top -> bottom), night variant / day variant. The Frost Moon is always night.
SKY = {
    0: (("#02050f", "#050b20", "#0a1838", "#102a58"), None),
    1: (("#06182c", "#0b2b46", "#145066", "#2a7f93"), ("#5fb4dc", "#8fd3ee", "#bfe9f6", "#e4f8fd")),
    2: (("#040d08", "#0a1f13", "#123a22", "#215f36"), ("#2f7a48", "#4f9e5a", "#7ac26e", "#b0e090")),
    3: (("#10030b", "#2a0a1a", "#4c1228", "#80203c"), ("#6a2238", "#a04050", "#d07a70", "#f2b494")),
    4: (("#060616", "#0e0e2c", "#1b1a48", "#33317c"), ("#4a4a90", "#7470b8", "#a098d8", "#d4ccf4")),
    5: (("#0d051c", "#2a0c36", "#5a1b4a", "#92305a"), ("#c4607a", "#e88c8c", "#f8b49a", "#ffdcb4")),
}
HAZE = {0: "#12305a", 1: "#9fe0ee", 2: "#6fd08a", 3: "#c0405a", 4: "#8a80d8", 5: "#e07a9a"}   # fog / mist colour
VIG = {0: "#010310", 1: "#020b18", 2: "#010a04", 3: "#14020a", 4: "#030312", 5: "#120418"}


def horizon_h(H):
    return int(max(150, min(270, H * 0.31)))


# =============================================================================================== PAINT helpers
def ramp(art, y0, y1, cols, tr=5):
    """Vertical colour ramp built from solid bands with ordered-dither transitions (pure 8-bit look)."""
    n = len(cols)
    h = max(1, y1 - y0)
    for y in range(y0, y1):
        f = (y - y0) / h * n
        i = min(n - 1, int(f))
        col = rgba(cols[i])
        # dither toward the next band during the last `tr` rows of each band
        band_end = (i + 1) * h / n
        d = band_end - (y - y0)
        if i < n - 1 and d <= tr:
            thr = int((1 - d / tr) * 16)
            nxt = rgba(cols[i + 1])
            pat = b"".join(nxt if BAYER[y & 3][k] < thr else col for k in range(4))
            row = pat * (art.w // 4 + 1)
            art.buf[(y * art.w) * 4:(y * art.w + art.w) * 4] = row[:art.w * 4]
        else:
            art.span(0, art.w, y, col)


def stars(art, rnd, n, y1, cols=("#ffffff", "#cfe8ff", "#ffe8c0")):
    for _ in range(n):
        x, y = rnd.randrange(art.w), rnd.randrange(max(1, y1))
        c = rnd.choice(cols)
        art.pset(x, y, rgba(c))
        if rnd.random() < 0.12:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                art.pset(x + dx, y + dy, rgba(blend(c, "#000000", 0.55)))


def shade_ellipse(art, cx, cy, rx, ry, c="#000000"):
    """50 % checker-dithered ellipse (cheap ground shadow with binary alpha)."""
    col = rgba(c)
    for y in range(int(cy - ry), int(cy + ry) + 1):
        dy = (y + 0.5 - cy) / ry
        if abs(dy) > 1:
            continue
        half = rx * math.sqrt(1 - dy * dy)
        for x in range(int(round(cx - half)), int(round(cx + half))):
            if (x + y) & 1:
                art.pset(x, y, col)


def mountains(art, rnd, base, amp, col, edge=None, step=5, rough=0.6, snow=None):
    """Jagged silhouette ridge ending at `base`; returns the heights for reuse."""
    w = art.w
    hs, h = [], rnd.uniform(0.3, 1.0)
    for x in range(0, w + step, step):
        h = max(0.1, min(1.0, h + rnd.uniform(-rough, rough) * 0.5))
        hs.append(h)
    hs[-1] = hs[0]                     # seamless wrap
    for i in range(len(hs) - 1):
        x0, x1 = i * step, (i + 1) * step
        for x in range(x0, x1):
            t = (x - x0) / step
            top = base - amp * (hs[i] * (1 - t) + hs[i + 1] * t)
            for y in range(int(top), base):
                art.pset(x, y, rgba(col))
            if edge:
                art.pset(x, int(top), rgba(edge))
            if snow and base - top > amp * 0.55:
                for k in range(1 + int((base - top - amp * 0.55) * 0.5)):
                    art.pset(x, int(top) + k, rgba(snow))
    return hs


def tree_pine(art, x, base, h, col, hi=None):
    """Triangular pine of height h (painted pixels)."""
    for k in range(h):
        wd = int(1 + k * 0.42)
        art.span(x - wd, x + wd + 1, base - h + k, rgba(col))
    art.rect(x, base - 1, x + 1, base + 1, col)
    if hi:
        for k in range(0, h, 3):
            art.pset(x - int(1 + k * 0.42), base - h + k, rgba(hi))


def blob_tree(art, x, base, r, col, hi, trunk="#1a0f08"):
    art.rect(x - 1, base - r, x + 1, base, trunk)
    art.ellipse(x, base - r - r * 0.5, r, r * 0.85, col)
    art.ellipse(x - r * 0.35, base - r - r * 0.8, r * 0.5, r * 0.4, hi)


def fade_below(art, y0, rows, col, solid_until=0):
    """Dithered fade of colour `col` over rows below the horizon (soft join with the ground)."""
    art.dither_rows(0, art.w, y0, y0 + rows, col, lambda y: max(0.0, 1.0 - (y - y0 - solid_until) / rows))


# =============================================================================================== BACKDROPS
def paint_sky(biome, W, H, night, dl=None):
    """Far scenery strip (binary alpha), seamlessly wrapping horizontally.

    dl=None  -> the classic opaque sky (ramp + stars + sun / moon baked in); used by the always-night Frost Moon.
    dl=0..1  -> dynamic mode: ONLY the silhouettes, tinted for that light level.  The gradient, stars, sun and moon are
                drawn live every frame behind it (see SceneMixin.draw_horizon), which is what makes sunrise smooth."""
    hor = horizon_h(H) // SC
    w = W // SC
    art = Art(w, hor + 14, wrapx=True)
    ramps = SKY[biome]
    bg = dl is None or ramps[1] is None                # True: paint the sky itself too
    if dl is not None and ramps[1] is not None:
        cols = tuple(blend(a, b, dl) for a, b in zip(ramps[0], ramps[1]))
        night = dl < 0.5
        rnd = random.Random(biome * 977 + 13)           # same seed at every light level -> identical silhouettes
        bg = False
    else:
        rnd = random.Random(biome * 977 + (0 if night else 13))
        cols = ramps[0] if (night or ramps[1] is None) else ramps[1]
        night = night or ramps[1] is None
    wrnd = random.Random(biome * 31 + 7)                # lit-window pattern must not disturb the silhouette sequence
    if bg:
        ramp(art, 0, hor, cols)
    bottom = cols[-1]
    if bg and night:
        stars(art, rnd, int(w * 0.5), int(hor * 0.8))
    if biome == 0:                                    # ---------------- FROST MOON: Earth-rise over a lunar horizon
        ex, ey, r = int(w * 0.30), int(hor * 0.46), int(hor * 0.36)
        art.glow(ex, ey, r + 9, "#2d6aa8", 0.55)
        art.ellipse(ex, ey, r, r, "#17427a")
        art.ellipse(ex - 1, ey - 1, r - 1, r - 1, "#1f5c9a")
        for (dx, dy, rx, ry, c) in ((-6, -4, 7, 3, "#3f9a82"), (3, -9, 6, 3, "#357f6e"), (5, 4, 7, 4, "#3f9a82"), (-9, 6, 4, 3, "#2e7468")):
            art.ellipse(ex + dx, ey + dy, rx, ry, c)
        for (dx, dy, rx, c) in ((-4, -10, 8, "#cfe9ff"), (6, 0, 6, "#bfe0f6"), (-8, 3, 5, "#cfe9ff"), (0, 9, 7, "#a8d0ee")):
            art.rect(ex + dx - rx // 2, ey + dy, ex + dx + rx // 2, ey + dy + 1, c)
        # terminator shadow (lit from the upper-left) as dither, then a bright rim
        art.dither_fn(ex - r, ey - r, ex + r + 1, ey + r + 1, "#050a1c",
            lambda x, y: max(0.0, min(1.0, ((x - ex) * 0.7 + (y - ey) * 0.7) / r - 0.15)) if (x - ex) ** 2 + (y - ey) ** 2 < r * r else 0)
        for a in range(200, 330, 2):
            art.pset(int(ex + math.cos(math.radians(a)) * r), int(ey + math.sin(math.radians(a)) * r), rgba("#9fdcff"))
        art.glow(int(w * 0.72), int(hor * 0.25), 11, "#1d4a86", 0.8)           # distant nebula
        mountains(art, rnd, hor, hor * 0.34, "#0a1630", "#27456f", step=6, rough=1.1)
    elif biome == 1:                                  # ---------------- MISTY LAKE: snow peaks + pines
        if bg:
            art.glow(int(w * 0.68), int(hor * 0.42), 12, "#d9f6ff" if night else "#ffffff", 0.55 if night else 0.8)
            art.ellipse(int(w * 0.68), int(hor * 0.42), 4, 4, "#e8fbff")
        far = blend(bottom, "#0a2a40" if night else "#4a86a8", 0.75)
        mountains(art, rnd, hor, hor * 0.62, far, blend(far, "#ffffff", 0.35), step=9, rough=1.3, snow="#e8f6ff" if not night else "#9fcfe6")
        mountains(art, rnd, hor, hor * 0.28, blend(far, "#000000", 0.25), None, step=5, rough=1.0)
    elif biome == 2:                                  # ---------------- FOREST OF MAGIC: giant canopy + moon
        if bg and night:
            art.glow(int(w * 0.62), int(hor * 0.30), 15, "#9fffb0", 0.5)
            art.ellipse(int(w * 0.62), int(hor * 0.30), 6, 6, "#e6ffd8")
        elif bg:
            art.glow(int(w * 0.62), int(hor * 0.28), 14, "#ffffd0", 0.7)
        far = blend(bottom, "#02080a", 0.55)
        for i in range(0, w, 9):
            blob_tree(art, i + rnd.randrange(4), hor, rnd.randint(7, 11), far, blend(far, "#6fd08a", 0.18))
    elif biome == 3:                                  # ---------------- SCARLET MANSION: blood moon + silhouette
        if bg and night:
            art.glow(int(w * 0.76), int(hor * 0.36), 20, "#ff3050", 0.65)
            art.ellipse(int(w * 0.76), int(hor * 0.36), 9, 9, "#ff4a4a")
            art.ellipse(int(w * 0.76) - 2, int(hor * 0.36) - 2, 7, 7, "#ff7a6a")
        elif bg:
            art.glow(int(w * 0.76), int(hor * 0.36), 14, "#ffd0a0", 0.6)
        wall = blend(bottom, "#0a0206", 0.7)
        base = hor
        art.rect(int(w * 0.2), base - 15, int(w * 0.62), base, wall)                              # main hall
        art.rect(int(w * 0.30), base - 24, int(w * 0.36), base - 14, wall)                         # tower
        art.poly([(w * 0.29, base - 24), (w * 0.33, base - 34), (w * 0.37, base - 24)], wall)
        art.ellipse(int(w * 0.33), base - 20, 2, 2, "#e0c070" if night else wall)                  # clock
        art.rect(int(w * 0.46), base - 21, int(w * 0.52), base - 14, wall)
        art.poly([(w * 0.455, base - 21), (w * 0.49, base - 29), (w * 0.525, base - 21)], wall)
        for k in range(int(w * 0.22), int(w * 0.6), 5):
            if night and wrnd.random() < 0.55:
                art.rect(k, base - 9, k + 2, base - 5, "#ffcf6a")
        mountains(art, rnd, hor, hor * 0.18, blend(wall, bottom, 0.3), None, step=7, rough=0.8)
    elif biome == 4:                                  # ---------------- NETHERWORLD: moon, long stairs, gates
        if bg:
            art.glow(int(w * 0.64), int(hor * 0.34), 20, "#cfc4ff", 0.5)
            art.ellipse(int(w * 0.64), int(hor * 0.34), 8, 8, "#f4f0ff")
            art.ellipse(int(w * 0.64) - 3, int(hor * 0.34) - 2, 2, 2, "#d8d2f4")
        far = blend(bottom, "#04041a", 0.6)
        mountains(art, rnd, hor, hor * 0.42, far, blend(far, "#a898ff", 0.25), step=8, rough=1.0)
        for gx in (0.16, 0.5, 0.84):                                                              # gates
            x = int(w * gx)
            col = blend(far, "#000000", 0.2)
            art.rect(x - 7, hor - 18, x - 5, hor, col)
            art.rect(x + 5, hor - 18, x + 7, hor, col)
            art.rect(x - 9, hor - 19, x + 9, hor - 17, col)
            art.rect(x - 7, hor - 15, x + 7, hor - 14, col)
        for k in range(22):                                                                         # stairs
            art.rect(int(w * 0.33) + k * 2, hor - 4 - k, int(w * 0.33) + k * 2 + 6, hor - 3 - k, blend(far, "#6a5aaa", 0.25))
    else:                                             # ---------------- HAKUREI SHRINE: dusk mountains + torii
        sx, sy = int(w * 0.70), int(hor * 0.62)
        if bg:
            art.glow(sx, sy, 20, "#ff9a6a" if night else "#fff0c0", 0.65)
            art.ellipse(sx, sy, 8, 8, "#ff6a5a" if night else "#fff6d0")
        far = blend(bottom, "#1a0818", 0.62)
        mountains(art, rnd, hor, hor * 0.5, far, blend(far, "#ff9ac8", 0.22), step=9, rough=1.2)
        for k in range(5):                                                                          # streaky dusk clouds
            y = int(hor * (0.12 + 0.13 * k))
            xx = rnd.randrange(w)
            art.dither_rows(xx, xx + rnd.randint(25, 55), y, y + 2, "#ffb0a0" if night else "#ffffff", lambda yy: 0.7)
    fade_below(art, hor, 14, bottom)
    return art


def paint_ridge(biome, W, H, night, dl=None):
    """Nearer silhouettes along the horizon (the layer that parallaxes faster than the sky).
    dl (0..1) tints them for a continuous light level instead of the night / day pair."""
    hor = horizon_h(H) // SC
    w = W // SC
    art = Art(w, hor + 6, wrapx=True)
    ramps = SKY[biome]
    if dl is not None and ramps[1] is not None:
        rnd = random.Random(biome * 313 + 7)             # identical layout at every light level
        night = dl < 0.5
        bottom = blend(ramps[0][-1], ramps[1][-1], dl)
        dark = blend(bottom, "#000000", 0.78 - 0.23 * dl)
        mid = blend(bottom, "#000000", 0.62 - 0.22 * dl)
    else:
        rnd = random.Random(biome * 313 + (0 if night else 7))
        night = night or ramps[1] is None
        bottom = (ramps[0] if night else ramps[1])[-1]
        dark = blend(bottom, "#000000", 0.78 if night else 0.55)
        mid = blend(bottom, "#000000", 0.62 if night else 0.4)
    if biome == 0:
        mountains(art, rnd, hor + 2, hor * 0.22, dark, "#1e3a62", step=4, rough=1.3)
        for x in (int(w * 0.09), int(w * 0.46), int(w * 0.83)):                         # lunar pylons with glowing tips
            h = rnd.randint(14, 24)
            art.rect(x - 2, hor - h, x + 3, hor + 1, "#102440")
            art.rect(x - 1, hor - h - 3, x + 2, hor - h, "#1c3c66")
            art.pset(x, hor - h - 4, rgba("#9fe8ff"))
            art.glow(x, hor - h - 4, 4, "#5ecbff", 0.8)
        art.ellipse(int(w * 0.64), hor, 9, 4, "#0d1d38")                                  # a habitat dome
        art.ellipse(int(w * 0.64), hor - 1, 7, 5, "#16305a", ring=0)
        art.rect(int(w * 0.64) - 7, hor - 1, int(w * 0.64) + 8, hor + 2, "#0d1d38")
    elif biome == 1:
        for x in range(0, w, 6):
            tree_pine(art, x + rnd.randrange(3), hor + 1, rnd.randint(9, 18), dark, blend(dark, "#d8f4ff", 0.6 if night else 0.8))
    elif biome == 2:
        for x in range(0, w, 7):
            blob_tree(art, x + rnd.randrange(4), hor + 1, rnd.randint(6, 10), dark, mid)
        for k in range(4):                                                                  # giant glowing mushrooms
            x = rnd.randrange(w)
            art.rect(x - 1, hor - 6, x + 1, hor + 1, "#3a2a40")
            art.ellipse(x, hor - 7, 5, 3, "#7a3aa8")
            art.glow(x, hor - 7, 8, "#d28cff", 0.7)
            art.pset(x - 2, hor - 8, rgba("#ffe9a0"))
    elif biome == 3:
        for x in range(0, w, 4):                                                            # wrought-iron fence
            art.rect(x, hor - 6, x + 1, hor + 1, dark)
            art.pset(x, hor - 7, rgba(dark))
        art.rect(0, hor - 4, w, hor - 3, dark)
        for x in range(0, w, 17):
            art.ellipse(x + 3, hor - 8, 3, 3, mid)                                          # rose bushes
            art.pset(x + 3, hor - 9, rgba("#c02040"))
    elif biome == 4:
        for x in range(0, w, 16):
            h = rnd.randint(11, 17)
            art.rect(x + 3, hor - h // 2, x + 5, hor + 1, dark)
            art.ellipse(x + 4, hor - h // 2 - 1, 6, 4, mid)
            art.ellipse(x + 2, hor - h // 2 - 2, 3, 2, blend(mid, "#ffb7e8", 0.5))
            art.pset(x + 6, hor - h // 2 + 1, rgba("#ffd0f0"))
    else:
        for x in range(0, w, 11):
            art.ellipse(x + 4, hor, 7, 3, dark)
        for x in (int(w * 0.18), int(w * 0.58)):                                            # torii in the distance
            art.rect(x - 8, hor - 17, x - 6, hor + 1, "#7a1c2c")
            art.rect(x + 6, hor - 17, x + 8, hor + 1, "#7a1c2c")
            art.rect(x - 11, hor - 20, x + 11, hor - 18, "#a02a3a")
            art.rect(x - 9, hor - 15, x + 9, hor - 14, "#7a1c2c")
        for x in (int(w * 0.36), int(w * 0.80)):                                            # stone lanterns with warm glow
            art.rect(x - 1, hor - 8, x + 1, hor + 1, "#2a1a28")
            art.rect(x - 3, hor - 11, x + 3, hor - 8, "#2a1a28")
            art.rect(x - 1, hor - 10, x + 1, hor - 8, "#ffd88a")
            art.glow(x, hor - 9, 7, "#ffb060", 0.7)
    return art


# =============================================================================================== DYNAMIC SKY
TW_RISE = ("#7a4a9a", "#ff8fb0", "#ffc27a")        # sunrise: violet -> rose -> gold   (top of glow -> horizon)
TW_SET = ("#5a2a6a", "#ff5a4a", "#ff9a3a")         # sunset : plum   -> red  -> amber
MOON_COL = {1: ("#eaffff", "#bfe6f2"), 2: ("#e6ffd8", "#a8e0a8"), 3: ("#ff7a6a", "#d83a3a"), 4: ("#f4f0ff", "#c9c0f0"),
            5: ("#ffe6ee", "#f0b0c8")}
MOON_GLOW = {1: "#d9f6ff", 2: "#9fffb0", 3: "#ff3050", 4: "#cfc4ff", 5: "#ffb0d0"}
SUN_COLS = ("#fffbe0", "#fff0a8", "#ffd860", "#ffa63a", "#ff6a2a")


def sky_rows(biome, dl, tw, rising, n=26):
    """n horizontal band colours (top -> horizon): night ramp -> day ramp by `dl`, then warmed towards the sunrise /
    sunset colours near the horizon by `tw`."""
    night, day = SKY[biome]
    day = day or night
    glow = TW_RISE if rising else TW_SET
    out = []
    for i in range(n):
        t = i / (n - 1)                                  # 0 = zenith, 1 = horizon
        k = t * (len(night) - 1)
        j = min(len(night) - 2, int(k))
        f = k - j
        c = blend(blend(night[j], day[j], dl), blend(night[j + 1], day[j + 1], dl), f)
        if tw > 0.02:
            g = blend(glow[0], glow[1], min(1.0, t * 1.6)) if t < 0.625 else blend(glow[1], glow[2], (t - 0.625) / 0.375)
            c = blend(c, g, min(0.92, tw * (t ** 2.1) * 1.15))
        out.append(c)
    return out


def paint_sun(k):
    r = 6
    art = Art(r * 2 + 3, r * 2 + 3)
    c = r + 1
    col = SUN_COLS[k]
    art.glow(c, c, r + 1, blend(col, "#ffffff", 0.35), 0.9)
    art.ellipse(c, c, r, r, col)
    art.ellipse(c - 1, c - 1, r - 2, r - 2, blend(col, "#ffffff", 0.45))
    return art


def paint_moon(biome):
    r = 6
    lit, shade = MOON_COL.get(biome, MOON_COL[1])
    art = Art(r * 2 + 3, r * 2 + 3)
    c = r + 1
    art.ellipse(c, c, r, r, lit)
    for dx, dy, rr in ((-2, -2, 1.6), (2, 1, 2.0), (-1, 3, 1.1)):                       # craters
        art.ellipse(c + dx, c + dy, rr, rr, shade)
    art.dither_fn(c - r, c - r, c + r + 1, c + r + 1, shade,
        lambda x, y: max(0.0, min(1.0, ((x - c) * 0.6 + (y - c) * 0.6) / r)) * 0.6 if (x - c) ** 2 + (y - c) ** 2 < r * r else 0)
    return art


def paint_horizon_glow(k, rising):
    """Wide flat glow (dithered, binary alpha). k scales strength; colour follows the sunrise / sunset palette."""
    glow = TW_RISE if rising else TW_SET
    rx, ry = 62, 22
    art = Art(rx * 2 + 1, ry + 2)
    s = k / 4.0
    col = glow[2]
    mid = glow[1]

    def fn(x, y):
        d = ((x - rx) / rx) ** 2 + ((y - ry) / ry) ** 2
        return 0.0 if d >= 1 else (1 - d) ** 1.4 * s

    art.dither_fn(0, 0, art.w, art.h, mid, lambda x, y: fn(x, y) * 0.55 if ((x - rx) / rx) ** 2 + ((y - ry) / ry) ** 2 < 1 else 0)
    art.dither_fn(int(rx * 0.35), int(ry * 0.3), int(rx * 1.65), art.h, col,
        lambda x, y: fn((x - rx) * 1.7 + rx, (y - ry) * 1.7 + ry))
    return art


def paint_fog(biome, W, H):
    """Wide, wrapping, dithered mist band (binary alpha)."""
    w = W // SC
    h = 26
    art = Art(w, h, wrapx=True)
    rnd = random.Random(biome * 61 + 5)
    col = HAZE[biome]
    for k in range(7):
        cx, cy = rnd.randrange(w), rnd.randint(8, 18)
        rx, ry = rnd.randint(22, 48), rnd.randint(3, 6)
        for y in range(cy - ry, cy + ry + 1):
            dy = (y - cy) / ry
            if abs(dy) >= 1:
                continue
            half = rx * (1 - dy * dy) ** 0.6
            lv = 0.55 * (1 - abs(dy))
            thr = int(lv * 16 + 0.5)
            for x in range(int(cx - half), int(cx + half)):
                edge = 1 - abs(x - cx) / half
                if BAYER[y & 3][x & 3] < thr * min(1.0, edge * 2.2) + 0.01:
                    art.pset(x, y, rgba(col))
    return art


def paint_vignette(biome, W, H, tint=None, strength=1.0):
    """Edge darkening (and bottom shade for the HUD) as one binary-alpha dither image."""
    w, h = W // SC, H // SC
    art = Art(w, h)
    col = tint or VIG[biome]
    side = max(6, int(w * 0.075))                 # was 16 % of the width: now a thin rim only
    c = rgba(col)
    for y in range(h):
        vy = 0.0
        for x in range(w):
            vx = 0.0
            if x < side:
                vx = (side - x) / side
            elif x >= w - side:
                vx = (x - (w - side)) / side
            lv = max(vx * vx, vy * vy * 0.8) * strength
            # skip the faint tail: a sparse Bayer dither reads as stray "x" / "+" marks, especially on light ground
            if lv >= 0.2 and BAYER[y & 3][x & 3] < lv * 16:
                art.pset(x, y, c)
    return art


# =============================================================================================== DECOR CHUNKS
def cell_hash(x, y):
    h = (x * 374761393 + y * 668265263 + 1013904223) & 0xffffffff
    h ^= h >> 13
    h = (h * 1274126177) & 0xffffffff
    h ^= h >> 16
    return h


def _blade(art, x, y, h, lean, c1, c2=None):
    for k in range(h):
        art.pset(x + int(lean * k / max(1, h)), y - k, rgba(c1 if (k < h - 1 or not c2) else c2))


def _decor_frost(art, cx, cy, h, r):
    v = r
    if v < 0.18:                       # crater
        art.ellipse(cx, cy + 1, 6, 3, "#0d1c34")
        art.ellipse(cx, cy, 6, 3, "#27456f", ring=1.2)
        art.pset(cx - 4, cy - 2, rgba("#4f7aa8"))
    elif v < 0.5:                      # ice spire
        art.poly([(cx - 3, cy + 5), (cx - 1, cy - 8), (cx + 1, cy - 4), (cx + 3, cy - 9), (cx + 4, cy + 5)], "#2f6aa8")
        art.poly([(cx - 1, cy + 5), (cx + 1, cy - 4), (cx + 3, cy - 9), (cx + 4, cy + 5)], "#5aa6e8")
        art.line(cx - 1, cy - 7, cx - 2, cy + 3, "#d8f4ff")
    elif v < 0.8:                      # moon rock
        shade_ellipse(art, cx, cy + 4, 5, 2)
        art.ellipse(cx, cy + 1, 4, 3, "#3a4f70")
        art.ellipse(cx - 1, cy, 2, 1.5, "#5f7a9c")
    else:                              # frost sparkle
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            art.pset(cx + dx, cy + dy, rgba("#9fdcff" if (dx or dy) else "#ffffff"))


def _decor_lake(art, cx, cy, h, r):
    v = r
    if v < 0.28:                       # reeds + cattails
        for k, dx in enumerate((-3, 0, 3)):
            _blade(art, cx + dx, cy + 6, 9 + k * 2, (k - 1) * 2, "#3a9a8c", "#8a5a3a")
    elif v < 0.5:                      # lily pad
        art.ellipse(cx, cy + 2, 5, 3, "#2f8a78")
        art.rect(cx, cy, cx + 3, cy + 2, "#10405e")
        art.pset(cx - 2, cy + 1, rgba("#ffd0e8"))
    elif v < 0.78:                     # ice chunk
        shade_ellipse(art, cx, cy + 5, 6, 2)
        art.poly([(cx - 5, cy + 3), (cx - 2, cy - 4), (cx + 3, cy - 3), (cx + 6, cy + 3)], "#9fdcf0")
        art.poly([(cx - 2, cy - 4), (cx + 3, cy - 3), (cx + 1, cy + 3), (cx - 3, cy + 3)], "#e8fbff")
    else:                              # ripple
        art.ellipse(cx, cy + 2, 6, 3, "#6fb8d0", ring=1)
        art.ellipse(cx, cy + 2, 3, 1.5, "#a0dcee", ring=1)


def _decor_forest(art, cx, cy, h, r):
    v = r
    if v < 0.2:                        # tree
        shade_ellipse(art, cx, cy + 6, 7, 3)
        art.rect(cx - 1, cy, cx + 2, cy + 7, "#4a2e1c")
        art.ellipse(cx, cy - 2, 7, 6, "#14402a")
        art.ellipse(cx - 2, cy - 4, 4, 3, "#1f6a3a")
        art.ellipse(cx + 2, cy - 1, 3, 2, "#2f8a4a")
    elif v < 0.42:                     # mushroom
        cap = ("#a02848", "#7a3aa8", "#c06a2a")[h % 3]
        art.rect(cx - 1, cy + 1, cx + 1, cy + 6, "#e8d4aa")
        art.ellipse(cx, cy, 5, 3.5, cap)
        for dx, dy in ((-2, -1), (1, -2), (2, 0)):
            art.pset(cx + dx, cy + dy, rgba("#fff0d0"))
        art.glow(cx, cy, 8, cap, 0.35)
    elif v < 0.7:                      # grass tuft
        for k, dx in enumerate((-4, -1, 2, 4)):
            _blade(art, cx + dx, cy + 6, 6 + (k % 3) * 2, (k - 2), "#3f9a54", "#8aff9a" if k == 1 else None)
    else:                              # fern / glowing flower
        _blade(art, cx, cy + 6, 9, 3, "#2f7b46")
        _blade(art, cx, cy + 6, 8, -3, "#3f9a54")
        art.pset(cx, cy - 4, rgba("#ffe9a0"))
        art.glow(cx, cy - 4, 5, "#ffe9a0", 0.5)


def _decor_scarlet(art, cx, cy, h, r):
    v = r
    if v < 0.25:                       # rose bush
        shade_ellipse(art, cx, cy + 5, 6, 2)
        art.ellipse(cx, cy + 1, 6, 4, "#14301c")
        for dx, dy in ((-3, -1), (2, -2), (0, 2), (4, 1)):
            art.ellipse(cx + dx, cy + dy, 1.6, 1.6, "#c8284a")
            art.pset(cx + dx, cy + dy, rgba("#ff8a9a"))
    elif v < 0.42:                     # lamp post
        art.rect(cx, cy - 2, cx + 1, cy + 8, "#2a1a24")
        art.rect(cx - 2, cy - 6, cx + 3, cy - 2, "#3a2430")
        art.rect(cx - 1, cy - 5, cx + 2, cy - 3, "#ffd477")
        art.glow(cx, cy - 4, 9, "#ff9a5a", 0.6)
    elif v < 0.7:                      # cobble patch
        for dx in range(-5, 6, 4):
            for dy in range(-3, 4, 3):
                art.rect(cx + dx, cy + dy, cx + dx + 3, cy + dy + 2, "#4a2030" if (dx + dy) & 1 else "#5a2a3a")
    else:                              # iron fence post
        art.rect(cx - 5, cy + 3, cx + 6, cy + 4, "#2a1620")
        for dx in (-4, 0, 4):
            art.rect(cx + dx, cy - 4, cx + dx + 1, cy + 5, "#3a2030")
            art.pset(cx + dx, cy - 5, rgba("#ff4f6d"))


def _decor_nether(art, cx, cy, h, r):
    v = r
    if v < 0.2:                        # cherry tree
        shade_ellipse(art, cx, cy + 6, 7, 3)
        art.rect(cx - 1, cy, cx + 2, cy + 7, "#4b3156")
        for dx, dy, rr in ((-3, -3, 5), (3, -3, 5), (0, -6, 5), (0, -1, 6)):
            art.ellipse(cx + dx, cy + dy, rr, rr * 0.8, "#c48ac0" if (dx + dy) & 1 else "#e0a8d8")
        art.pset(cx + 2, cy - 7, rgba("#ffffff"))
    elif v < 0.4:                      # tombstone
        shade_ellipse(art, cx, cy + 6, 5, 2)
        art.rect(cx - 4, cy - 2, cx + 5, cy + 6, "#6a6a98")
        art.ellipse(cx, cy - 2, 4.5, 3.5, "#6a6a98")
        art.rect(cx, cy - 3, cx + 1, cy + 2, "#2a2a52")
        art.rect(cx - 2, cy - 1, cx + 3, cy, "#2a2a52")
    elif v < 0.55:                     # hitodama (spirit flame)
        art.glow(cx, cy, 9, "#9fd8ff", 0.7)
        art.ellipse(cx, cy + 1, 3, 3.5, "#bfe6ff")
        art.poly([(cx - 2, cy), (cx, cy - 6), (cx + 2, cy)], "#bfe6ff")
        art.pset(cx, cy, rgba("#ffffff"))
    else:                              # petal drift
        for k in range(7):
            art.rect(cx - 5 + (k * 5) % 10, cy - 2 + (k * 3) % 6, cx - 3 + (k * 5) % 10, cy - 1 + (k * 3) % 6, "#ffb7e8")


def _decor_shrine(art, cx, cy, h, r):
    v = r
    if v < 0.2:                        # stone lantern
        shade_ellipse(art, cx, cy + 7, 6, 2)
        art.rect(cx - 1, cy - 1, cx + 2, cy + 7, "#6a5a68")
        art.rect(cx - 4, cy - 6, cx + 5, cy - 1, "#7a6a78")
        art.rect(cx - 2, cy - 5, cx + 3, cy - 2, "#ffd88a")
        art.rect(cx - 5, cy - 8, cx + 6, cy - 6, "#5a4a58")
        art.glow(cx, cy - 4, 9, "#ffb060", 0.6)
    elif v < 0.4:                      # sakura shrub
        shade_ellipse(art, cx, cy + 6, 7, 3)
        art.ellipse(cx, cy, 7, 5.5, "#c45a78")
        art.ellipse(cx - 2, cy - 2, 4, 3, "#ffa0c0")
        art.pset(cx + 3, cy - 2, rgba("#ffffff"))
    elif v < 0.68:                     # shide on a pole
        art.rect(cx, cy - 6, cx + 1, cy + 7, "#7b3a28")
        art.line(cx - 6, cy - 4, cx + 7, cy - 4, "#d4a34c")
        for dx in (-5, -1, 3, 6):
            art.rect(cx + dx, cy - 3, cx + dx + 2, cy + 1, "#f4e8d0")
    else:                              # raked gravel arcs
        art.ellipse(cx, cy + 2, 6, 3, "#8a5a72", ring=1)
        art.ellipse(cx, cy + 2, 3, 1.5, "#8a5a72", ring=1)


DECOR_FN = (_decor_frost, _decor_lake, _decor_forest, _decor_scarlet, _decor_nether, _decor_shrine)
DENSITY = (0.17, 0.16, 0.20, 0.15, 0.20, 0.17)


def paint_chunk(chunk_x, chunk_y, biome_at, skip, grid_w, grid_h):
    """One 16x16-cell chunk of static ground scenery as a single binary-alpha image (15 painted px per cell)."""
    cp = CELL // DSC
    art = Art(CHUNK * cp, CHUNK * cp)
    x0, y0 = chunk_x * CHUNK, chunk_y * CHUNK
    for gy in range(y0, min(grid_h - 1, y0 + CHUNK)):
        for gx in range(x0, min(grid_w - 1, x0 + CHUNK)):
            if gx < 1 or gy < 1 or skip(gx, gy):
                continue
            h = cell_hash(gx, gy)
            r = h / 4294967296.0
            b = biome_at(gx, gy)
            if r >= DENSITY[b]:
                continue
            DECOR_FN[b](art, (gx - x0) * cp + cp // 2, (gy - y0) * cp + cp // 2, h, r / DENSITY[b])
    return art


# =============================================================================================== BOSS ARENAS
AP = CELL // SC                   # painted pixels per cell in arena art (10)
ARENA_MARGIN = 2                  # cells of shadow / props painted outside the wall ring

THEMES = [   # floor a/b, grout, wall a/b, trim, accent, light
    dict(fa="#0c2840", fb="#10304c", grout="#081c2e", wa="#3f86a8", wb="#2c6a8a", trim="#bfeaff", acc="#5ecbff", hi="#e8fbff"),
    dict(fa="#102a18", fb="#14341e", grout="#0a1c10", wa="#3a2616", wb="#2a1a0e", trim="#6fd08a", acc="#77e58c", hi="#d6ff9a"),
    dict(fa="#1a0a12", fb="#2a1020", grout="#10050a", wa="#4a1424", wb="#340c18", trim="#e0b050", acc="#ff5478", hi="#ffcf6e"),
    dict(fa="#1a1838", fb="#222048", grout="#0e0c24", wa="#7a76aa", wb="#5a5688", trim="#d4c8ff", acc="#c09cff", hi="#ffc8ec"),
    dict(fa="#2a1a24", fb="#321f2c", grout="#1a0e16", wa="#8a2a35", wb="#6a1c28", trim="#f4e8d0", acc="#ff86b7", hi="#ffe4ed"),
]


def _bricks(art, x1, y1, x2, y2, ca, cb, rnd, bh=5, bw=10):
    art.rect(x1, y1, x2, y2, ca)
    for yy in range(y1, y2, bh):
        art.rect(x1, yy, x2, yy + 1, cb)
        off = ((yy - y1) // bh % 2) * (bw // 2)
        for xx in range(x1 + off, x2, bw):
            art.rect(xx, yy, xx + 1, min(y2, yy + bh), cb)
    for _ in range((x2 - x1) * (y2 - y1) // 40):
        art.pset(rnd.randrange(x1, x2), rnd.randrange(y1, y2), rgba(blend(ca, "#ffffff", 0.12)))


def paint_arena(ai, a):
    """The whole boss chamber (floor, walls, door frame, themed props) as ONE image. Returns (art, torches)."""
    th = THEMES[ai]
    cols = (a["x2"] - a["x1"] + 1) + 2 + 2 * ARENA_MARGIN
    rows = (a["y2"] - a["y1"] + 1) + 2 + 2 * ARENA_MARGIN
    art = Art(cols * AP, rows * AP)
    rnd = random.Random(900 + ai)
    m = ARENA_MARGIN
    ring_x1, ring_y1 = m * AP, m * AP                        # outer corner of the wall ring
    ring_x2, ring_y2 = (cols - m) * AP, (rows - m) * AP
    ix1, iy1, ix2, iy2 = ring_x1 + AP, ring_y1 + AP, ring_x2 - AP, ring_y2 - AP   # floor rectangle
    # ---- drop shadow around the chamber (dither, binary alpha)
    sh = rgba("#000000")
    for y in range(rows * AP):
        for x in range(cols * AP):
            if ring_x1 <= x < ring_x2 and ring_y1 <= y < ring_y2:
                continue
            d = max(ring_x1 - x, x - ring_x2 + 1, ring_y1 - y, y - ring_y2 + 1)
            if d > 0 and BAYER[y & 3][x & 3] < (1 - d / (m * AP + 1)) * 11:
                art.pset(x, y, sh)
    # ---- floor
    for gy in range(iy1 // AP, iy2 // AP):
        for gx in range(ix1 // AP, ix2 // AP):
            art.rect(gx * AP, gy * AP, gx * AP + AP, gy * AP + AP, th["fa"] if (gx + gy) & 1 else th["fb"])
            art.rect(gx * AP, gy * AP + AP - 1, gx * AP + AP, gy * AP + AP, th["grout"])
            art.rect(gx * AP + AP - 1, gy * AP, gx * AP + AP, gy * AP + AP, th["grout"])
            for _ in range(3):
                art.pset(gx * AP + rnd.randrange(AP - 1), gy * AP + rnd.randrange(AP - 1), rgba(blend(th["fa"], th["trim"], 0.10)))
    cxp, cyp = (ix1 + ix2) // 2, (iy1 + iy2) // 2
    doorc = (a["cx"] - a["x1"] + 1 + m) * AP + AP // 2     # door centre (painted px)
    _ARENA_PROPS[ai](art, th, rnd, ix1, iy1, ix2, iy2, cxp, cyp, doorc)
    _big_room(art, th, rnd, ix1, iy1, ix2, iy2, cxp, cyp, doorc, ai)
    # ---- wall ring (brick) with inner shadow ledge and door opening
    _bricks(art, ring_x1, ring_y1, ring_x2, iy1, th["wa"], th["wb"], rnd)
    _bricks(art, ring_x1, iy2, ring_x2, ring_y2, th["wa"], th["wb"], rnd)
    _bricks(art, ring_x1, iy1, ix1, iy2, th["wa"], th["wb"], rnd)
    _bricks(art, ix2, iy1, ring_x2, iy2, th["wa"], th["wb"], rnd)
    for x in range(ix1, ix2):
        for k in range(3):
            if BAYER[(iy1 + k) & 3][x & 3] < 10 - k * 3:
                art.pset(x, iy1 + k, rgba("#000000"))
    art.rect(ring_x1, ring_y1, ring_x2, ring_y1 + 1, th["trim"])
    art.rect(ring_x1, ring_y2 - 1, ring_x2, ring_y2, th["trim"])
    art.rect(ring_x1, ring_y1, ring_x1 + 1, ring_y2, th["trim"])
    art.rect(ring_x2 - 1, ring_y1, ring_x2, ring_y2, th["trim"])
    # door opening: 5 cells wide on the bottom wall, with a dark threshold and stone jambs
    dx1, dx2 = doorc - 25, doorc + 25
    art.rect(dx1, iy2, dx2, ring_y2, "#05070e")
    art.rect(dx1 - 3, iy2, dx1, ring_y2, th["trim"])
    art.rect(dx2, iy2, dx2 + 3, ring_y2, th["trim"])
    art.rect(dx1, iy2, dx2, iy2 + 2, th["acc"])
    # ---- corner pillars + torch sconces (flames are animated by the renderer)
    torches = []
    for (px, py) in ((ix1, iy1), (ix2, iy1), (ix1, iy2), (ix2, iy2)):
        art.rect(px - 7, py - 7, px + 7, py + 7, th["wb"])
        art.frame(px - 7, py - 7, px + 7, py + 7, th["trim"])
        art.rect(px - 4, py - 4, px + 4, py + 4, th["wa"])
    for fx in (0.22, 0.5, 0.78):
        torches.append(((ix1 + (ix2 - ix1) * fx) / AP, (iy1 - 3) / AP))
    for fy in (0.45,):
        torches.append(((ix1 - 3) / AP, (iy1 + (iy2 - iy1) * fy) / AP))
        torches.append(((ix2 + 3) / AP, (iy1 + (iy2 - iy1) * fy) / AP))
    for tx, ty in torches:
        art.rect(int(tx * AP) - 1, int(ty * AP), int(tx * AP) + 2, int(ty * AP) + 6, "#1a1218")
        art.rect(int(tx * AP) - 3, int(ty * AP) + 5, int(tx * AP) + 4, int(ty * AP) + 7, "#2a2028")
    return art, torches


def _props_lake(art, th, rnd, x1, y1, x2, y2, cx, cy, doorc):
    for _ in range(26):                                      # ice cracks
        x, y = rnd.randrange(x1, x2), rnd.randrange(y1, y2)
        for _s in range(rnd.randint(4, 9)):
            nx, ny = x + rnd.randint(-4, 4), y + rnd.randint(-3, 3)
            art.line(x, y, nx, ny, "#2a6a90")
            x, y = nx, ny
    for r, c in ((46, "#1f5a84"), (36, "#2f7aa8")):          # snowflake sigil
        art.ellipse(cx, cy, r, r * 0.8, c, ring=1)
    for k in range(6):
        ang = k * math.pi / 3
        ex, ey = cx + math.cos(ang) * 44, cy + math.sin(ang) * 35
        art.line(cx, cy, ex, ey, "#3f8ab8", t=1)
        for s in (0.55, 0.8):
            bx, by = cx + math.cos(ang) * 44 * s, cy + math.sin(ang) * 35 * s
            for sg in (-1, 1):
                art.line(bx, by, bx + math.cos(ang + sg * 0.9) * 8, by + math.sin(ang + sg * 0.9) * 6, "#3f8ab8")
    art.glow(cx, cy, 22, "#5ecbff", 0.45)
    for (sx, sy) in ((x1, y1), (x2, y1), (x1, y2), (x2, y2)):   # snow drifts in the corners
        art.glow(sx, sy, 34, "#e8fbff", 0.9)


def _props_forest(art, th, rnd, x1, y1, x2, y2, cx, cy, doorc):
    for _ in range(40):                                      # moss + soil patches
        c = rnd.choice(("#1a4a2a", "#0c2214", "#2a1c12"))
        art.ellipse(rnd.randrange(x1, x2), rnd.randrange(y1, y2), rnd.randint(4, 12), rnd.randint(3, 7), c)
    for _ in range(80):
        x, y = rnd.randrange(x1, x2), rnd.randrange(y1, y2)
        _blade(art, x, y, rnd.randint(2, 4), rnd.randint(-1, 1), "#3f9a54")
    pts = [(cx + math.cos(k * math.pi / 3 + math.pi / 6) * 56, cy + math.sin(k * math.pi / 3 + math.pi / 6) * 42) for k in range(6)]
    for i in range(6):                                       # Marisa's hexagram, inlaid in gold
        a, b = pts[i], pts[(i + 2) % 6]
        art.line(a[0], a[1], b[0], b[1], "#8a7a30")
    art.ellipse(cx, cy, 58, 44, "#8a7a30", ring=1)
    for k in range(16):                                      # fairy ring of mushrooms
        ang = k * math.pi * 2 / 16
        mx, my = cx + math.cos(ang) * 62, cy + math.sin(ang) * 48
        art.rect(mx - 1, my, mx + 1, my + 4, "#e8d4aa")
        art.ellipse(mx, my, 3.5, 2.5, "#7a3aa8" if k % 2 else "#a02848")
        art.pset(mx - 1, my - 1, rgba("#fff0d0"))
    art.glow(cx, cy, 30, "#77e58c", 0.35)


def _props_scarlet(art, th, rnd, x1, y1, x2, y2, cx, cy, doorc):
    art.rect(doorc - 20, y1 + 30, doorc + 20, y2, "#6a1228")           # red carpet from the door to the dais
    art.rect(doorc - 20, y1 + 30, doorc - 18, y2, th["trim"])
    art.rect(doorc + 18, y1 + 30, doorc + 20, y2, th["trim"])
    for yy in range(y1 + 34, y2, 10):
        art.rect(doorc - 17, yy, doorc + 17, yy + 1, "#8a1a36")
    art.rect(doorc - 50, y1 + 6, doorc + 50, y1 + 30, "#3a1626")       # dais + steps
    art.rect(doorc - 50, y1 + 28, doorc + 50, y1 + 30, th["trim"])
    for s in range(3):
        art.rect(doorc - 44 + s * 4, y1 + 8 + s * 5, doorc + 44 - s * 4, y1 + 10 + s * 5, "#4a1c30")
    art.rect(doorc - 6, y1 + 8, doorc + 6, y1 + 22, "#14040a")         # throne silhouette
    art.rect(doorc - 8, y1 + 4, doorc + 8, y1 + 10, "#14040a")
    art.pset(doorc, y1 + 6, rgba("#ff4a5a"))
    art.ellipse(cx, cy, 26, 20, "#b01a3a", ring=2)                      # emblem: moon + wings
    art.ellipse(cx, cy, 15, 12, "#ffcf5a", ring=1)
    art.poly([(cx - 34, cy), (cx - 22, cy - 9), (cx - 24, cy), (cx - 22, cy + 9)], "#6a1228")
    art.poly([(cx + 34, cy), (cx + 22, cy - 9), (cx + 24, cy), (cx + 22, cy + 9)], "#6a1228")
    for k in range(5):                                                  # stained-glass light shafts
        sx = x1 + 30 + k * ((x2 - x1 - 60) // 4)
        col = "#ff3050" if k % 2 else "#ffcf5a"
        for y in range(y1, y2):
            off = int((y - y1) * 0.45)
            for x in range(sx + off, sx + off + 12):
                if x1 <= x < x2 and BAYER[y & 3][x & 3] < 3:
                    art.pset(x, y, rgba(col))


def _props_nether(art, th, rnd, x1, y1, x2, y2, cx, cy, doorc):
    for r in (30, 58, 88):
        art.ellipse(cx, cy, r * 1.15, r * 0.82, "#4a3a8a", ring=1)
    for k in range(8):
        ang = k * math.pi / 4
        art.line(cx + math.cos(ang) * 30, cy + math.sin(ang) * 24, cx + math.cos(ang) * 100, cy + math.sin(ang) * 72, "#33296a")
    for k in range(8):                                                  # unlit spirit-lamp bases on the outer ring
        ang = k * math.pi / 4 + math.pi / 8
        lx, ly = cx + math.cos(ang) * 101, cy + math.sin(ang) * 72
        art.ellipse(lx, ly, 4, 3, "#2a2a5a")
        art.ellipse(lx, ly, 2, 1.5, "#9fd8ff")
    for _ in range(30):                                                 # fallen cherry petals
        px, py = rnd.randrange(x1, x2), rnd.randrange(y1, y2)
        art.rect(px, py, px + 2, py + 1, "#ffb7e8" if rnd.random() < 0.7 else "#e0a8d8")
    art.glow(cx, cy, 34, "#c09cff", 0.4)


def _props_shrine(art, th, rnd, x1, y1, x2, y2, cx, cy, doorc):
    for k in range(10):                                                 # raked gravel
        rr = 16 + k * 9
        art.ellipse(cx, cy, rr * 1.5, rr, "#3a2434", ring=1)
    art.rect(doorc - 8, cy, doorc + 8, y2, "#4a3040")                  # stone path to the door
    for yy in range(cy, y2, 10):
        art.rect(doorc - 8, yy, doorc + 8, yy + 1, "#2a1a24")
    R = 40                                                              # yin-yang (muted so bullets stay readable)
    for y in range(cy - R, cy + R + 1):
        for x in range(cx - R, cx + R + 1):
            dx, dy = x - cx, y - cy
            if dx * dx + dy * dy > R * R:
                continue
            top = dx * dx + (dy + R / 2) ** 2 <= (R / 2) ** 2
            bot = dx * dx + (dy - R / 2) ** 2 <= (R / 2) ** 2
            light = (dx > 0) if not (top or bot) else bot
            if top:
                light = False
            if bot:
                light = True
            if (dx * dx + (dy + R / 2) ** 2) <= (R / 6) ** 2:
                light = True
            if (dx * dx + (dy - R / 2) ** 2) <= (R / 6) ** 2:
                light = False
            art.pset(x, y, rgba("#7a5a6e" if light else "#5a1a30"))
    art.ellipse(cx, cy, R + 1, R + 1, "#a0607a", ring=1)
    for k in range(4):                                                  # sakura petals on the ground
        px, py = rnd.randrange(x1, x2), rnd.randrange(y1, y2)
        art.rect(px, py, px + 2, py + 1, "#ffb4ca")
    art.glow(cx, cy, 26, "#ff86b7", 0.25)


def _big_room(art, th, rnd, x1, y1, x2, y2, cx, cy, doorc, ai):
    """The dungeons are ~4x the old room: inlaid borders, a processional path and pillars keep the extra floor from looking empty."""
    acc, trim = th["acc"], th["trim"]
    inl = blend(th["fa"], acc, 0.35)
    for k, ins in enumerate((AP * 2, AP * 3)):                      # inlaid frame bands near the walls
        art.frame(x1 + ins, y1 + ins, x2 - ins, y2 - ins, inl if k == 0 else blend(th["fa"], trim, 0.22))
    art.rect(doorc - 3, cy + 30, doorc + 3, y2, inl)                 # path from the door toward the centre
    art.rect(doorc - 3, cy + 30, doorc - 2, y2, blend(th["fa"], trim, 0.4))
    art.rect(doorc + 2, cy + 30, doorc + 3, y2, blend(th["fa"], trim, 0.4))
    for sx, sy in ((0.2, 0.28), (0.8, 0.28), (0.2, 0.72), (0.8, 0.72), (0.5, 0.2)):   # rune circles + pillars
        px, py = x1 + (x2 - x1) * sx, y1 + (y2 - y1) * sy
        art.ellipse(px, py, 26, 20, inl, ring=1)
        art.ellipse(px, py, 15, 11, blend(th["fa"], acc, 0.5), ring=1)
        art.glow(px, py, 18, acc, 0.22)
        art.rect(px - 5, py - 5, px + 5, py + 5, th["wb"])
        art.frame(px - 5, py - 5, px + 5, py + 5, trim)
        art.rect(px - 3, py - 3, px + 3, py + 3, th["wa"])
    for _ in range(60):                                              # scattered cracks / rubble
        x, y = rnd.randrange(x1, x2), rnd.randrange(y1, y2)
        art.rect(x, y, x + rnd.randint(1, 3), y + 1, blend(th["fa"], "#000000", 0.45))


_ARENA_PROPS = (_props_lake, _props_forest, _props_scarlet, _props_nether, _props_shrine)


# =============================================================================================== SPELL-CARD AURAS
AURA_FRAMES = 4
AURA_COL = ("#5ecbff", "#ffd34d", "#ff4f6d", "#d74cff", "#ff7a9c")      # per boss (Cirno, Marisa, Remilia, Flandre, Reimu)


def paint_aura(ai, a, frame, col=None):
    """Touhou-style spell-card background: an animated dithered motif over the arena floor (half resolution, binary alpha)."""
    cols = a["x2"] - a["x1"] + 1
    rows = a["y2"] - a["y1"] + 1
    q = AP // 2
    w, h = cols * q, rows * q
    art = Art(w, h)
    cx, cy = w / 2, h / 2
    col = col or AURA_COL[ai]
    f = frame * (2 * math.pi / AURA_FRAMES)
    pi = math.pi
    if ai == 0:        # Cirno: drifting snow-crystal lattice
        def fn(x, y):
            v = math.cos(x * 0.45 + f * 0.5) * math.cos(y * 0.45 - f * 0.5)
            return max(0.0, v - 0.55) * 1.6
    elif ai == 1:      # Marisa: rotating star-burst
        def fn(x, y):
            ang = math.atan2(y - cy, x - cx)
            r = math.hypot(x - cx, y - cy)
            return max(0.0, math.sin(12 * ang + f * 1.5 + r * 0.04) - 0.7) * max(0.0, 1 - r / (w * 0.55)) * 2.2
    elif ai == 2:      # Remilia: blood-moon ripples
        def fn(x, y):
            r = math.hypot((x - cx) * 0.8, y - cy)
            return max(0.0, math.sin(r * 0.28 - f * 1.5) - 0.8) * 2.5 * max(0.0, 1 - r / (w * 0.5))
    elif ai == 3:      # Flandre: broken scarlet cage / destructive starburst
        def fn(x, y):
            ang = math.atan2(y - cy, x - cx)
            r = math.hypot(x - cx, y - cy)
            cage = max(0.0, math.sin(4 * ang + f * 1.7 + r * 0.055) - 0.76) * 2.8
            burst = max(0.0, math.sin(r * 0.32 - f * 2.2) - 0.90) * 2.0
            return (cage + burst) * max(0.0, 1 - r / (w * 0.55))
    else:              # Reimu: eight-fold seal rays + barrier rings
        def fn(x, y):
            ang = math.atan2(y - cy, x - cx)
            r = math.hypot(x - cx, y - cy)
            ray = max(0.0, math.sin(8 * ang + f) - 0.85) * 3
            ring = max(0.0, math.sin(r * 0.22 - f) - 0.9) * 3
            return (ray + ring) * max(0.0, 1 - r / (w * 0.55))
    art.dither_fn(0, 0, w, h, blend(col, "#000000", 0.5), lambda x, y: fn(x, y) * 0.55)
    return art


# =============================================================================================== SPRITES
def paint_flame(ai, frame):
    th = THEMES[ai]
    art = Art(9, 12)
    sway = (0, 1, -1)[frame % 3]
    art.glow(4, 7, 5, th["acc"], 0.8)
    art.poly([(1, 11), (4 + sway, 1), (7, 11)], th["acc"])
    art.poly([(2, 11), (4 + sway, 4), (6, 11)], th["hi"])
    art.rect(3, 8, 6, 11, "#fff7cf")
    return art


def paint_particle(kind, frame):
    if kind == "snow":
        art = Art(5, 5)
        for dx, dy in ((2, 2), (1, 2), (3, 2), (2, 1), (2, 3)):
            art.pset(dx, dy, rgba("#e8fbff" if (dx, dy) == (2, 2) else "#9fdcf0"))
    elif kind == "spore":
        art = Art(7, 7)
        art.glow(3, 3, 3.4, "#d8ff70", 0.9)
        art.pset(3, 3, rgba("#ffffff"))
    elif kind == "firefly":
        art = Art(9, 9)
        art.glow(4, 4, 4.4, "#c8ff86", 0.9 if frame % 2 else 0.5)
        art.pset(4, 4, rgba("#ffffd0"))
    elif kind == "ember":
        art = Art(5, 5)
        art.glow(2, 2, 2.6, "#ff7a3a", 0.9)
        art.pset(2, 2, rgba("#ffe0a0"))
    elif kind == "petal":
        art = Art(6, 6)
        pts = ((1, 1), (2, 1), (3, 2), (4, 3), (3, 3), (2, 2)) if frame % 2 else ((1, 3), (2, 2), (3, 2), (4, 1), (4, 2), (2, 3))
        for x, y in pts:
            art.pset(x, y, rgba("#ffb4ca"))
    elif kind == "wisp":
        art = Art(9, 11)
        art.glow(4, 6, 5, "#9fd8ff", 0.6)
        art.poly([(2, 9), (4, 1 + frame % 2), (6, 9)], "#bfe6ff")
        art.ellipse(4, 8, 2.4, 2, "#e8fbff")
        art.pset(3, 8, rgba("#4a6aa0"))
        art.pset(5, 8, rgba("#4a6aa0"))
    elif kind == "bat":
        art = Art(11, 7)
        up = frame % 3
        wing = "#2d1725"
        art.ellipse(5, 4, 1.5, 2, wing)
        for sg in (-1, 1):
            tip = (5 + sg * 5, (1, 3, 5)[up])
            art.poly([(5 + sg, 3), tip, (5 + sg * 3, 5), (5 + sg, 5)], wing)
        art.pset(4, 3, rgba("#ff4a5a"))
        art.pset(6, 3, rgba("#ff4a5a"))
    elif kind == "mote":
        art = Art(4, 4)
        art.rect(1, 1, 3, 3, "#cfe8ff")
    else:
        art = Art(3, 3)
        art.rect(0, 0, 3, 3, "#ffffff")
    return art


def _rot(pts, ang):
    c, s = math.cos(ang), math.sin(ang)
    return [(x * c - y * s, x * s + y * c) for x, y in pts]


def paint_bullet(kind, col, R, angi=0, frame=0):
    """Touhou-style bullet sprites. R = radius in painted px; directional kinds use 16 angle steps."""
    dark = blend(col, "#000000", 0.72)
    mid = blend(col, "#ffffff", 0.55)
    S = int(R * 2.6) * 2 + 5
    art = Art(S, S)
    c = S / 2
    ang = angi * (2 * math.pi / 16)

    def P(pts, color):
        art.poly([(c + x, c + y) for x, y in _rot(pts, ang)], color)

    if kind == "orb":
        art.ellipse(c, c, R + 1.5, R + 1.5, dark)
        art.ellipse(c, c, R + 0.5, R + 0.5, col)
        art.ellipse(c, c, max(1, R - 1.2), max(1, R - 1.2), mid)
        if R >= 3:
            art.ellipse(c, c, R - 2.2, R - 2.2, "#ffffff")
    elif kind == "ring":                      # a dead / inactive ghost bullet: hollow
        art.ellipse(c, c, R + 0.5, R + 0.5, blend(col, "#000000", 0.35), ring=1)
    elif kind == "rice":
        P([(1.9 * R + 1, 0), (0.6 * R, 0.95 * R + 1), (-1.7 * R, 0.8 * R), (-1.7 * R, -0.8 * R), (0.6 * R, -0.95 * R - 1)], dark)
        P([(1.8 * R, 0), (0.5 * R, 0.8 * R), (-1.5 * R, 0.6 * R), (-1.5 * R, -0.6 * R), (0.5 * R, -0.8 * R)], col)
        P([(1.2 * R, 0), (0, 0.4 * R), (-1.2 * R, 0.3 * R), (-1.2 * R, -0.3 * R), (0, -0.4 * R)], "#ffffff")
    elif kind == "knife":
        P([(2.5 * R + 1, 0), (0.6 * R, 0.9 * R + 1), (-1.8 * R, 0.6 * R + 1), (-1.8 * R, -0.6 * R - 1), (0.6 * R, -0.9 * R - 1)], dark)
        P([(2.4 * R, 0), (0.5 * R, 0.8 * R), (-1.2 * R, 0.4 * R), (-1.2 * R, -0.4 * R), (0.5 * R, -0.8 * R)], "#f0f4ff")
        P([(-1.2 * R, 0.5 * R), (-1.9 * R, 0.5 * R), (-1.9 * R, -0.5 * R), (-1.2 * R, -0.5 * R)], col)
    elif kind == "amulet":
        P([(-1.5 * R - 1, -1.0 * R - 1), (1.5 * R + 1, -1.0 * R - 1), (1.5 * R + 1, 1.0 * R + 1), (-1.5 * R - 1, 1.0 * R + 1)], dark)
        P([(-1.4 * R, -0.9 * R), (1.4 * R, -0.9 * R), (1.4 * R, 0.9 * R), (-1.4 * R, 0.9 * R)], "#fff4f4")
        P([(-0.5 * R, -0.9 * R), (0.5 * R, -0.9 * R), (0.5 * R, 0.9 * R), (-0.5 * R, 0.9 * R)], col)
    elif kind == "ice":
        P([(2.4 * R + 1, 0), (0, 1.0 * R + 1), (-1.4 * R - 1, 0), (0, -1.0 * R - 1)], dark)
        P([(2.3 * R, 0), (0, 0.9 * R), (-1.3 * R, 0), (0, -0.9 * R)], "#e8fbff")
        P([(1.4 * R, 0), (0, 0.4 * R), (-0.6 * R, 0), (0, -0.4 * R)], col)
    elif kind == "star":
        pts = []
        for k in range(10):
            rr = (1.7 if k % 2 == 0 else 0.75) * R
            a2 = k * math.pi / 5 - math.pi / 2
            pts.append((math.cos(a2) * rr, math.sin(a2) * rr))
        P([(x * 1.25, y * 1.25) for x, y in pts], dark)
        P(pts, col)
        P([(x * 0.45, y * 0.45) for x, y in pts], "#ffffff")
    elif kind == "bfly":
        wob = 0.5 if frame % 2 else 1.0
        for sg in (-1, 1):
            P([(0, 0), (-1.6 * R, sg * 1.9 * R * wob), (0.9 * R, sg * 1.5 * R * wob)], dark)
            P([(0, 0), (-1.4 * R, sg * 1.6 * R * wob), (0.7 * R, sg * 1.2 * R * wob)], col)
        P([(1.0 * R, 0), (0, 0.35 * R), (-1.0 * R, 0), (0, -0.35 * R)], "#ffffff")
    else:
        art.ellipse(c, c, R, R, col)
    return art


# =============================================================================================== CACHE / BANK
def _bucket(v, q=96):
    return ((int(v) + q - 1) // q) * q


class SceneryBank:
    """Turns painted Arts into cached tk.PhotoImages. All painting is deterministic and cheap (<=90 ms for the biggest piece)."""

    def __init__(self, tk, master, grid_w, grid_h, biome_at, skip):
        self.tk, self.master = tk, master
        self.gw, self.gh, self.biome_at, self.skip = grid_w, grid_h, biome_at, skip
        self.c = {}
        self.chunks = {}
        self.bullets = {}
        self.torches = {}
        self.todo = []
        self.tc = {}                    # baked terrain layers: (kind, cx, cy) -> (lvl, PhotoImage | None)
        self.tc_cap = 90                # set per frame from the visible chunk count (see SceneMixin.begin_terrain)
        self.maps = None                # (BMAP, B2MAP, WMAP) - set by SceneMixin
        self.is_wall = None

    def _img(self, art, zoom):
        return photo(self.tk, self.master, art.b64(), zoom)

    def _get(self, key, build, zoom):
        img = self.c.get(key)
        if img is None:
            img = self.c[key] = self._img(build(), zoom)
        return img

    # ---- frame housekeeping: caches are trimmed between frames only, so no live canvas item loses its image
    def begin_frame(self):
        while len(self.chunks) > 56:
            self.chunks.pop(next(iter(self.chunks)))
        while len(self.tc) > self.tc_cap:                        # LRU: the least recently drawn terrain chunk goes first
            self.tc.pop(next(iter(self.tc)))
        if len(self.bullets) > 700:
            self.bullets.clear()
        if len(self.c) > 140:                                  # window was resized a lot: drop stale layer sizes
            for k in [k for k in self.c if k[0] in ("sky", "ridge", "fog", "vig", "skyl", "ridl")][:60]:
                self.c.pop(k, None)

    # ---- layers
    def sky(self, b, night, W, H):
        Wb = _bucket(W)
        return self._get(("sky", b, night, Wb, horizon_h(H)), lambda: paint_sky(b, Wb, H, night), SC)

    def ridge(self, b, night, W, H):
        Wb = _bucket(W)
        return self._get(("ridge", b, night, Wb, horizon_h(H)), lambda: paint_ridge(b, Wb, H, night), SC)

    # ---- dynamic-sky layers (sunrise / sunset): everything is keyed on a coarse light level, never on the clock
    def skyline(self, b, lvl, W, H):
        """Silhouette strip for light level lvl/4 (transparent above the mountains)."""
        Wb = _bucket(W)
        return self._get(("skyl", b, lvl, Wb, horizon_h(H)), lambda: paint_sky(b, Wb, H, False, lvl / 4.0), SC)

    def ridge_dl(self, b, lvl, W, H):
        Wb = _bucket(W)
        return self._get(("ridl", b, lvl, Wb, horizon_h(H)), lambda: paint_ridge(b, Wb, H, False, lvl / 4.0), SC)

    def sun_sprite(self, k):
        """Sun disc, k = 0 (high, white-yellow) .. 4 (on the horizon, deep orange)."""
        return self._get(("sun", k), lambda: paint_sun(k), 3)

    def moon_sprite(self, b):
        return self._get(("moon", b), lambda: paint_moon(b), 3)

    def horizon_glow(self, k, rising):
        """Wide dithered glow lying on the horizon around the rising / setting sun; k = 1..4 strength."""
        return self._get(("hglow", k, bool(rising)), lambda: paint_horizon_glow(k, rising), 3)

    def fog(self, b, W, H):
        Wb = _bucket(W)
        return self._get(("fog", b, Wb), lambda: paint_fog(b, Wb, H), SC)

    def vignette(self, b, W, H, boss=None, night=2):
        """`night` is now a level: 2 = dark night rim, 1 = dusk / dungeon (faint), 0 = daytime (nothing is drawn)."""
        Wb, Hb = _bucket(W), _bucket(H)
        tint = blend(AURA_COL[boss], "#000000", 0.8) if boss is not None else None
        strength = (0.0, 0.5, 0.9)[int(night)]
        return self._get(("vig", b, Wb, Hb, boss, int(night)), lambda: paint_vignette(b, Wb, Hb, tint, strength), SC)

    def chunk(self, cx, cy):
        img = self.chunks.get((cx, cy))
        if img is None:
            img = self.chunks[(cx, cy)] = self._img(paint_chunk(cx, cy, self.biome_at, self.skip, self.gw, self.gh), DSC)
        else:
            self.chunks[(cx, cy)] = self.chunks.pop((cx, cy))        # LRU touch
        return img

    def terrain(self, kind, cx, cy, lvl, rebake=True):
        """Baked terrain chunk image (or None when the layer is empty there).  A chunk baked for another day-light
        level is re-baked only when `rebake` is true (the caller meters that) - otherwise the old one is reused."""
        key = (kind, cx, cy)
        ent = self.tc.pop(key, None)
        if ent is not None and (kind == "decor" or ent[0] == lvl or not rebake):
            self.tc[key] = ent                                    # LRU touch
            return ent[1]
        from . import terrain as T
        bm, b2, wm = self.maps
        if kind == "tint":
            art = T.paint_tint(cx, cy, lvl, bm, b2, wm)
        elif kind == "walls":
            art = T.paint_walls(cx, cy, lvl, bm, b2, wm, self.is_wall)
        else:
            art = T.paint_decor(cx, cy, bm, b2, wm, self.skip)
        img = self._img(art, DSC) if art is not None else None
        self.tc[key] = (lvl, img)
        return img

    def terrain_cached(self, kind, cx, cy):
        return (kind, cx, cy) in self.tc

    def node(self, frame):
        from . import terrain as T
        return self._get(("node", frame % T.NODE_FRAMES), lambda: T.paint_node(frame % T.NODE_FRAMES), DSC)

    def arena(self, ai, a):
        key = ("arena", ai)
        if key not in self.c:
            art, torches = paint_arena(ai, a)
            self.c[key] = self._img(art, SC)
            self.torches[ai] = torches
        return self.c[key], self.torches[ai]

    def aura(self, ai, a, frame):
        return self._get(("aura", ai, frame % AURA_FRAMES), lambda: paint_aura(ai, a, frame % AURA_FRAMES), 6)

    def flame(self, ai, frame):
        return self._get(("flame", ai, frame % 3), lambda: paint_flame(ai, frame), DSC)

    def particle(self, kind, frame):
        return self._get(("p", kind, frame % 3), lambda: paint_particle(kind, frame), DSC)

    def bullet(self, kind, col, R, angi=0, frame=0):
        key = (kind, col, R, angi if kind not in ("orb", "ring") else 0, frame % 2 if kind == "bfly" else 0)
        img = self.bullets.get(key)
        if img is None:
            img = self._atlas_bullet(kind, col, R, key[3], key[4])
            if img is None:
                img = self._img(paint_bullet(kind, col, R, key[3], key[4]), DSC)
            self.bullets[key] = img
        return img

    # ---- Danmaku-pack bullet sprites (baked by tools/assets/make_bullets.py into assets/bullets/)
    ATLAS_KINDS = ("orb", "star", "bfly", "rice", "amulet", "knife", "ice")
    ATLAS_DIR = Path(__file__).resolve().parent.parent / "assets" / "bullets"

    def _atlas_col(self, col):
        hs = self.__dict__.get("_hues")
        if hs is None:
            try:
                hs = json.load(open(self.ATLAS_DIR / "hues.json"))
            except Exception:
                hs = []
            self._hues = hs
        if not hs:
            return None
        r, g, b = (int(col[i:i + 2], 16) / 255 for i in (1, 3, 5))
        h, sat, v = colorsys.rgb_to_hsv(r, g, b)
        if sat < 0.28:
            return 0 if v > 0.45 else 1
        best, bd = 3, 9.0
        for i in range(3, len(hs)):
            d = abs(h - hs[i])
            d = min(d, 1 - d)
            if d < bd:
                best, bd = i, d
        return best

    def _atlas_bullet(self, kind, col, R, angi, frame):
        if kind not in self.ATLAS_KINDS or not (isinstance(col, str) and col.startswith("#") and len(col) == 7):
            return None
        try:
            size = 14 if R <= 2 else 18 if R == 3 else 22 if R <= 5 else 30
            sheet = self.sheets.get((kind, size)) if hasattr(self, "sheets") else None
            if sheet is None:
                if not hasattr(self, "sheets"):
                    self.sheets = {}
                sheet = self.sheets[(kind, size)] = self.tk.PhotoImage(master=self.master, file=str(self.ATLAS_DIR / f"{kind}_{size}.png"))
            c = self._atlas_col(col)
            if c is None:
                return None
            directional = kind in ("rice", "amulet", "knife", "ice")
            cell = math.ceil(size * 1.45) if directional else size
            row = angi % 16 if directional else (frame % 2 if kind == "bfly" else 0)
            out = self.tk.PhotoImage(master=self.master, width=cell, height=cell)
            self.master.tk.call(out, "copy", sheet, "-from", c * cell, row * cell, (c + 1) * cell, (row + 1) * cell, "-to", 0, 0)
            return out
        except Exception:
            return None
