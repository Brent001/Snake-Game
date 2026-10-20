"""Baked terrain layers.  Each is one 16x16-cell chunk painted ONCE into a binary-alpha image (see pixelart.py), so the
whole ground costs a handful of create_image calls per frame no matter how detailed it is.

  tint    biome-transition belts: the floors of two neighbouring biomes ordered-dithered into each other
  decor   foliage / rocks / mushrooms ... - in a belt, both biomes' plants grow side by side
  walls   masonry for every structure: bricks / ice blocks / hedge, lit rim on the exposed sides, raised front face,
          dithered shadow cast on the floor below

The three layers are drawn in that order (tint < grid < decor < walls).  Chunks are baked for a day-light level
`lvl` (0..4) because the palettes follow the day / night cycle; a stale chunk is re-baked a couple per frame.
"""
from functools import lru_cache

from ..config import CELL, CHUNK, GRID_H, GRID_W, WORLD_H
from ..data.biomes import STYLES
from ..utils import mix
from .pixelart import Art, BAYER, rgba
from .scenery import DECOR_FN, DENSITY, DSC, cell_hash

CP = CELL // DSC                      # painted pixels per cell (15)
LEVELS = 9                            # day-light steps a chunk is baked for (finer steps = smoother dusk / dawn)
WALL_STYLE = ("ice", "ice", "hedge", "brick", "brick", "brick")      # per biome
CLEAR = b"\x00\x00\x00\x00"


def pal_for(lvl):
    """Palette of every biome at day-light step `lvl` (same formula as SnakeTerminal.build_pal)."""
    dl = lvl / (LEVELS - 1)
    return [{k: mix(v[0], v[1], 0.0 if i == 0 else dl) for k, v in s["pal"].items()} for i, s in enumerate(STYLES)]


_PAL = {}


def palette(lvl):
    p = _PAL.get(lvl)
    if p is None:
        p = _PAL[lvl] = pal_for(lvl)
    return p


# ====================================================================================== tint (biome belts)
@lru_cache(maxsize=4096)
def _tint_row(f_hi, rowmod, colmod, hi, lo):
    """15 painted pixels of one row: `hi` colour where the Bayer threshold is below f_hi/16, else `lo`."""
    a, b = rgba(hi), rgba(lo)
    row = BAYER[rowmod]
    return b"".join(a if row[(colmod + i) & 3] < f_hi else b for i in range(CP))


def paint_tint(cx, cy, lvl, bmap, b2map, wmap):
    art = Art(CHUNK * CP, CHUNK * CP)
    x0, y0 = cx * CHUNK, cy * CHUNK
    pal = palette(lvl)
    used = False
    for gy in range(y0, min(y0 + CHUNK, WORLD_H)):
        br, b2r, wr = bmap[gy], b2map[gy], wmap[gy]
        for gx in range(x0, min(x0 + CHUNK, GRID_W)):
            w = wr[gx]
            if not w:
                continue
            b, b2 = br[gx], b2r[gx]
            # both sides of a border must use the SAME dither pattern, so express it as coverage of the higher-id biome
            if b > b2:
                hi_c, lo_c, f_hi = pal[b]["floor"], pal[b2]["floor"], 16 - w
            else:
                hi_c, lo_c, f_hi = pal[b2]["floor"], pal[b]["floor"], w
            px0, py0 = (gx - x0) * CP, (gy - y0) * CP
            for r in range(CP):
                o = ((py0 + r) * art.w + px0) * 4
                art.buf[o:o + CP * 4] = _tint_row(f_hi, (py0 + r) & 3, px0 & 3, hi_c, lo_c)
            used = True
    return art if used else None


# ====================================================================================== decor (foliage)
def paint_decor(cx, cy, bmap, b2map, wmap, skip):
    art = Art(CHUNK * CP, CHUNK * CP)
    x0, y0 = cx * CHUNK, cy * CHUNK
    for gy in range(max(1, y0), min(WORLD_H - 1, y0 + CHUNK)):
        br, b2r, wr = bmap[gy], b2map[gy], wmap[gy]
        for gx in range(max(1, x0), min(GRID_W - 1, x0 + CHUNK)):
            if skip(gx, gy):
                continue
            h = cell_hash(gx, gy)
            r = h / 4294967296.0
            b, w = br[gx], wr[gx]
            if w and (cell_hash(gy, gx) & 255) < w * 16:        # inside a belt both biomes' plants grow
                b = b2r[gx]
            if r >= DENSITY[b]:
                continue
            DECOR_FN[b](art, (gx - x0) * CP + CP // 2, (gy - y0) * CP + CP // 2, h, r / DENSITY[b])
    return art


# ====================================================================================== walls
def _blend_col(pal, b, b2, w, key):
    c = pal[b][key]
    return mix(c, pal[b2][key], w / 16.0) if w else c


@lru_cache(maxsize=6000)
def _tile(style, fill, edge, glow, mask, var, par):
    """One wall cell as 15 rows of RGBA bytes.  mask bits: 1 = open above, 2 = open below, 4 = open right, 8 = open left."""
    N, S, E, W = bool(mask & 1), bool(mask & 2), bool(mask & 4), bool(mask & 8)
    F = rgba(fill)
    light = rgba(mix(fill, "#ffffff", 0.13))
    shade = rgba(mix(fill, "#000000", 0.26))
    mort = rgba(mix(fill, "#000000", 0.40))
    px = [[F] * CP for _ in range(CP)]
    # Keep the old chunky wall silhouette, but do NOT draw an internal seam/grid on
    # every cell.  The previous per-cell highlight/shade lines made large structures
    # look like wireframes.  Texture is now sparse, while the exposed outer edges
    # below provide the readable pixel-art silhouette.
    if style == "brick":
        for k in range(7):
            x = (var * 5 + k * 9 + par * 3) % CP
            y = (var * 3 + k * 7 + par * 4) % 10
            px[y][x] = light if k % 2 == 0 else shade
            if x + 1 < CP:
                px[y][x + 1] = px[y][x]
    elif style == "ice":
        # Small crystalline pixels only; no horizontal/vertical seam through the tile.
        for k in range(6):
            x = (var * 3 + k * 5 + par * 2) % CP
            y = (var * 7 + k * 3 + par) % CP
            px[y][x] = light
        px[(3 + var * 2) % CP][(10 + par * 2) % CP] = rgba("#ffffff")
    else:                                                      # hedge / foliage
        for k in range(12):
            x, y = (var * 7 + k * 5) % CP, (var * 3 + k * 11) % CP
            px[y][x] = light if k % 3 else shade
            if x + 1 < CP:
                px[y][x + 1] = px[y][x]
    EDGE, GL = rgba(edge), rgba(glow)
    HI = rgba(mix(edge, fill, 0.55))
    face = 11 if S else CP                                     # rows >= face are the raised front of the block
    if S:
        front = rgba(mix(fill, "#000000", 0.5))
        fj = rgba(mix(fill, "#000000", 0.62))
        for y in range(11, CP):
            px[y] = [front] * CP
        for jx in ((3, 10) if par else (6, 13)):
            for y in range(11, CP - 1):
                px[y][jx] = fj
        px[11] = [HI] * CP
        px[CP - 1] = [rgba(mix(edge, "#000000", 0.4))] * CP
    if N:
        for x in range(CP):
            px[0][x] = EDGE
            px[1][x] = HI
    if W:
        for y in range(face if not S else CP):
            px[y][0] = EDGE
            if y > 1:
                px[y][1] = HI if y < face else px[y][1]
    if E:
        for y in range(CP):
            px[y][CP - 1] = EDGE if y < face else rgba(mix(edge, "#000000", 0.4))
            if y < face and y > 1:
                px[y][CP - 2] = GL
    return [b"".join(r) for r in px]


@lru_cache(maxsize=64)
def _shadow_row(level, rowmod, colmod):
    dark = rgba("#02050a")
    row = BAYER[rowmod]
    return b"".join(dark if row[(colmod + i) & 3] < level else CLEAR for i in range(CP))


SHADOW = (5, 3)                    # compact contact shadow under a wall (out of 16)


def paint_walls(cx, cy, lvl, bmap, b2map, wmap, is_wall):
    art = Art(CHUNK * CP, CHUNK * CP)
    x0, y0 = cx * CHUNK, cy * CHUNK
    pal = palette(lvl)
    used = False
    for gy in range(y0, min(y0 + CHUNK, WORLD_H)):
        br, b2r, wr = bmap[gy], b2map[gy], wmap[gy]
        for gx in range(x0, min(x0 + CHUNK, GRID_W)):
            px0, py0 = (gx - x0) * CP, (gy - y0) * CP
            if not is_wall(gx, gy):
                if gy > 1 and is_wall(gx, gy - 1):                            # shadow cast on the floor below a wall
                    for r in range(len(SHADOW)):
                        o = ((py0 + r) * art.w + px0) * 4
                        art.buf[o:o + CP * 4] = _shadow_row(SHADOW[r], (py0 + r) & 3, px0 & 3)
                    used = True
                continue
            b, b2, w = br[gx], b2r[gx], wr[gx]
            mask = ((not is_wall(gx, gy - 1)) * 1 + (not is_wall(gx, gy + 1)) * 2
                + (not is_wall(gx + 1, gy)) * 4 + (not is_wall(gx - 1, gy)) * 8)
            tile = _tile(WALL_STYLE[b], _blend_col(pal, b, b2, w, "wall"), _blend_col(pal, b, b2, w, "edge"),
                _blend_col(pal, b, b2, w, "glow"), mask, cell_hash(gx, gy) & 3, (gx + gy) & 1)
            for r in range(CP):
                o = ((py0 + r) * art.w + px0) * 4
                art.buf[o:o + CP * 4] = tile[r]
            used = True
    return art if used else None


def wall_chunk_set(walls):
    """Chunks that contain a wall, or lie just below one (the shadow spills into the next chunk down)."""
    s = set()
    for x, y in walls:
        s.add((x // CHUNK, y // CHUNK))
        if y % CHUNK == CHUNK - 1:
            s.add((x // CHUNK, y // CHUNK + 1))
    return s


# ====================================================================================== hazard node sprites
NODE_FRAMES = 12


def paint_node(frame):
    """The rotating spike-star hazard, pre-rotated (the 16-point star repeats every 45 degrees)."""
    import math
    art = Art(16, 16)
    cx = cy = 7.5
    r_out, r_in = 6.9, 4.0
    rot = frame / NODE_FRAMES * (math.pi / 4)
    pts = []
    for i in range(16):
        ang = math.pi * 2 * i / 16 - math.pi / 2 + rot
        r = r_out if i % 2 == 0 else r_in
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    edge = pts + [pts[0]]
    art.poly(pts, "#8f0f33")
    for a, b in zip(edge, edge[1:]):
        art.line(a[0], a[1], b[0], b[1], "#ff4f7d")
    art.ellipse(cx, cy, 3.3, 3.3, "#ffc2d2", ring=1.0)
    art.rect(7, 7, 9, 9, "#ffc2d2")
    return art
