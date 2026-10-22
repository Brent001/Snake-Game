"""Menu rendering: animated 8-bit synthwave home screen, class select, controls screen and the pause menu."""
import math
import random
import tkinter as tk

from ..config import C_CYAN, C_MUTED, C_TEXT
from ..data.classes import CLASS_ORDER, CLASSES
from ..data.pixelfont import compile_text, text_width
from ..data.sprites import SPR, sprite_runs
from ..utils import mix
from ..systems.menu import SETTINGS_ROWS, SETTINGS_HELP, CREDITS_LINES

MONO = ("Consolas", 9, "bold")
NEON_C, NEON_P = "#37f0ff", "#ff2d95"
PANEL_BG, PANEL_LINE = "#070b1e", "#14456a"

_r = random.Random(11)
MENU_STARS = [(_r.random(), _r.random(), _r.random() * 6, _r.choice((1, 1, 1, 2))) for _ in range(44)]


def _city():
    r, x, out = random.Random(5), 0, []
    while x < 420:
        w, h = r.randint(3, 7), r.randint(5, 17)
        wins = [(r.randint(1, w - 2), r.randint(1, h - 2), r.random() * 6.3) for _ in range(3)]
        out.append((x, w, h, wins))
        x += w + r.randint(0, 2)
    return out


CITY = _city()
_PIX_CACHE = {}


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def chamfer(x0, y0, x1, y1, k):
    return [x0 + k, y0, x1, y0, x1, y1 - k, x1 - k, y1, x0, y1, x0, y0 + k]


class MenuViewMixin:
    # ------------------------------------------------------------------ primitives
    def pix_text_image(self, text, s, col, grad, shadow, only=None):
        """Pixel-font text rasterised once into a PhotoImage -> (image, origin dx, origin dy) or None. `only` = one glyph."""
        cache = self.__dict__.setdefault("_ptext_cache", {})
        key = (text, s, col, grad, shadow, only)
        if key in cache:
            return cache[key]
        runs, w = compile_text(text)
        sel = [r for r in runs if only is None or r[0] == only]
        if not sel:
            cache[key] = None
            return None
        gx0 = 0 if only is None else min(r[1] for r in sel)
        gx1 = w if only is None else max(r[1] + r[3] for r in sel)
        sdx, sdy = (shadow[1], shadow[2]) if shadow else (0, 0)
        ax, ay = gx0 * s + min(0, sdx), min(0, sdy)
        img = tk.PhotoImage(master=self.canvas, width=int(round(gx1 * s + max(0, sdx) - ax)) + 2,
            height=int(round(7 * s + max(0, sdy) - ay)) + 2)
        layers = ([(shadow[0], sdx, sdy)] if shadow else []) + [(None, 0, 0)]
        for lc, ox, oy in layers:
            for _ch, gx, gy, gw in sel:
                colr = lc or (mix(grad[0], grad[1], gy / 6) if grad else col)
                x1, y1 = int(round(gx * s + ox - ax)), int(round(gy * s + oy - ay))
                img.put(colr, to=(x1, y1, max(x1 + 1, int(round((gx + gw) * s + ox - ax))), max(y1 + 1, int(round((gy + 1) * s + oy - ay)))))
        cache[key] = (img, ax, ay)
        return cache[key]

    def ptext(self, x, y, text, s, col="#ffffff", anchor="w", shadow=None, grad=None, wob=0.0, glitch=0.0):
        """Draw 8-bit pixel-font text. anchor: w / c / e. grad=(top, bottom) colours; shadow=(colour, dx, dy)."""
        runs, w = compile_text(text)
        tw = w * s
        if anchor == "c":
            x -= tw / 2
        elif anchor == "e":
            x -= tw
        c = self.canvas
        if glitch:                                    # rare 0.1 s glitch frame: draw it the slow, exact way
            layers = ([(shadow[0], shadow[1], shadow[2])] if shadow else []) + [(None, 0, 0)]
            for lc, ox, oy in layers:
                for ch, gx, gy, gw in runs:
                    yo = math.sin(self.time * 2.4 + ch * 0.6) * wob if wob else 0.0
                    xo = glitch if gy < 3 else 0.0
                    colr = lc or (mix(grad[0], grad[1], gy / 6) if grad else col)
                    c.create_rectangle(x + ox + gx * s + xo, y + oy + gy * s + yo, x + ox + (gx + gw) * s + xo,
                        y + oy + (gy + 1) * s + yo, fill=colr, outline="")
            return tw
        if wob:                                       # wobbling title: one cached image per glyph
            for i in range(len(text)):
                hit = self.pix_text_image(text.upper(), s, col, grad, shadow, only=i)
                if hit:
                    c.create_image(x + hit[1], y + hit[2] + math.sin(self.time * 2.4 + i * 0.6) * wob, image=hit[0], anchor="nw")
            return tw
        hit = self.pix_text_image(text.upper(), s, col, grad, shadow)
        if hit:
            c.create_image(x + hit[1], y + hit[2], image=hit[0], anchor="nw")
        return tw

    def draw_pix(self, name, cx, cy, s, pal=None):
        """Draw a sprite grid from SPR centred at (cx, cy) with an optional palette override (cached image)."""
        rows, base = SPR[name]
        pal = dict(base, **(pal or {}))
        key = (name, tuple(sorted(pal.items())), s)
        cache = self.__dict__.setdefault("_pix_img_cache", {})
        img = cache.get(key)
        if img is None:
            if (name, tuple(sorted(pal.items()))) not in _PIX_CACHE:
                _PIX_CACHE[(name, tuple(sorted(pal.items())))] = sprite_runs(rows, pal)
            runs, n = _PIX_CACHE[(name, tuple(sorted(pal.items())))]
            img = tk.PhotoImage(master=self.canvas, width=int(round(n * s)) + 1, height=int(round(len(rows) * s)) + 1)
            for x, y, w, col in runs:
                x1, y1 = int(round(x * s)), int(round(y * s))
                img.put(col, to=(x1, y1, max(x1 + 1, int(round((x + w) * s))), max(y1 + 1, int(round((y + 1) * s)))))
            cache[key] = img
        self.canvas.create_image(cx, cy, image=img)

    def scanlines(self, x0, y0, x1, y1):
        """Faint panel scanlines baked into one transparent image per panel size."""
        w, h = int(x1 - x0) - 14, int(y1 - y0) - 12
        if w <= 0 or h <= 0:
            return
        cache = self.__dict__.setdefault("_scan_cache", {})
        img = cache.get((w, h))
        if img is None:
            img = tk.PhotoImage(master=self.canvas, width=w + 1, height=h)
            for k in range(0, h, 6):
                img.put("#0a1128", to=(0, k, w + 1, k + 1))
            cache[(w, h)] = img
        self.canvas.create_image(x0 + 7, y0 + 7, image=img, anchor="nw")

    def panel(self, x0, y0, x1, y1, col=NEON_C, cut=14):
        c = self.canvas
        c.create_polygon(chamfer(x0, y0, x1, y1, cut), fill=PANEL_BG, outline=col, width=2)
        c.create_polygon(chamfer(x0 + 5, y0 + 5, x1 - 5, y1 - 5, cut - 3), fill="", outline=PANEL_LINE)
        for sx, sy, dx, dy in ((x0, y0, 1, 1), (x1, y1, -1, -1)):          # glowing corner brackets
            c.create_line(sx + dx * 2, sy + dy * 22 + dy * 0, sx + dx * 2, sy + dy * 2, sx + dx * 22, sy + dy * 2, fill="#ffffff", width=2)
        t = self.time
        self.scanlines(x0, y0, x1, y1)
        sy = y0 + 8 + ((t * 70) % max(10, (y1 - y0 - 16)))                  # sweeping scan beam
        c.create_line(x0 + 7, sy, x1 - 7, sy, fill="#1c6a90")

    # ------------------------------------------------------------------ background
    def sky_bands_image(self, bw, hz):
        cache = self.__dict__.setdefault("_bg_cache", {})
        img = cache.get(("sky", bw, hz))
        if img is None:
            n = 24
            img = tk.PhotoImage(master=self.canvas, width=bw, height=hz + 2)
            for i in range(n):
                k = i / (n - 1)
                col = mix("#05010f", "#1a0638", min(1.0, k * 1.4))
                if k > 0.7:
                    col = mix(col, "#8a1a72", (k - 0.7) / 0.3 * 0.9)
                img.put(col, to=(0, int(hz * i / n), bw, int(hz * (i + 1) / n) + 1))
            cache[("sky", bw, hz)] = img
        return img

    def city_image(self, bw, hz):
        cache = self.__dict__.setdefault("_bg_cache", {})
        img = cache.get(("city", bw, hz))
        if img is None:
            bsz = 8
            img = tk.PhotoImage(master=self.canvas, width=bw, height=17 * bsz + 2)
            for x, w, h, _wins in CITY:
                x0 = x * bsz
                if x0 > bw:
                    break
                top = 17 * bsz - h * bsz
                x1 = min(bw, x0 + w * bsz + 1)
                img.put("#2a1060", to=(x0, top, x1, 17 * bsz + 1))
                img.put("#0b0524", to=(x0 + 1, top + 1, max(x0 + 1, x1 - 1), 17 * bsz))
            cache[("city", bw, hz)] = img
        return img

    def _menu_base_image(self, bw, bh):
        """Bake the expensive title background once per size/class palette.

        The old title screen recreated dozens of Canvas objects for the skyline, grid, stars and sun every frame.
        This version keeps the pixel-art look but puts all static artwork into one PhotoImage; only small accents
        are animated each frame.
        """
        cache = self.__dict__.setdefault("_menu_base_cache", {})
        hz = int(bh * 0.56)
        pal = tuple(CLASSES[self.pclass]["pal"])
        key = (bw, bh, pal)
        img = cache.get(key)
        if img is not None:
            return img
        img = tk.PhotoImage(master=self.canvas, width=bw, height=bh)
        n = 24
        for i in range(n):
            k = i / (n - 1)
            col = mix("#05010f", "#1a0638", min(1.0, k * 1.4))
            if k > 0.7:
                col = mix(col, "#8a1a72", (k - 0.7) / 0.3 * 0.9)
            img.put(col, to=(0, int(hz * i / n), bw, int(hz * (i + 1) / n) + 1))
        # Static sun.
        r = int(min(bw, bh) * 0.20)
        cx, cy = int(bw * 0.70), hz - int(r * 0.12)
        b = 6
        for dy in range(-r, r, b):
            yy = cy + dy
            if yy + b > hz:
                break
            hw = int(math.sqrt(max(0.0, r * r - (dy + b / 2) ** 2)) / b) * b
            frac = (dy + r) / (2 * r)
            if hw <= 0 or (frac > 0.5 and (dy // b) % 4 == 0):
                continue
            img.put(mix("#ffe45a", NEON_P, frac), to=(cx - hw, yy, cx + hw + 1, yy + b))
        # Baked skyline bodies.
        bsz = 8
        img.put("#2a1060", to=(0, hz - 17 * bsz, bw, hz))
        for x, w, h, _wins in CITY:
            x0 = x * bsz
            if x0 >= bw:
                break
            top = hz - h * bsz
            x1 = min(bw, x0 + w * bsz + 1)
            img.put("#2a1060", to=(x0, top, x1, hz))
            img.put("#0b0524", to=(x0 + 1, top + 1, max(x0 + 1, x1 - 1), hz))
        # Floor and a restrained pixel perspective grid.
        img.put("#07031a", to=(0, hz, bw, bh))
        img.put(NEON_P, to=(0, hz, bw, min(bh, hz + 3)))
        vx = bw / 2
        # Tk PhotoImage line-like primitives are easiest as narrow rectangles here.
        for i in range(-9, 10):
            x_bottom = int(vx + i * bw / 8.5)
            x_top = int(vx + i * 9)
            # Simple stepped approximation of perspective lines.
            for yy in range(hz + 4, bh, 6):
                u = (yy - hz) / max(1, bh - hz)
                x = int(x_top + (x_bottom - x_top) * u)
                if 0 <= x < bw:
                    img.put("#3a1480", to=(x, yy, x + 1, min(bh, yy + 1)))
        for yy in range(hz + 12, bh, max(12, (bh - hz) // 7)): 
            img.put("#2a0a5a", to=(0, yy, bw, min(bh, yy + 1)))
        cache[key] = img
        return img

    def draw_synth_bg(self):
        c, bw, bh, t = self.canvas, self.bw, self.bh, self.time
        hz = int(bh * 0.56)
        pal = CLASSES[self.pclass]["pal"]
        c.create_image(0, 0, image=self.sky_bands_image(bw, hz), anchor="nw")      # banded sky (baked, 1 item)
        for u, v, ph, sz in MENU_STARS:                                     # twinkling stars
            tw = 0.3 + 0.7 * ((math.sin(t * 2 + ph) + 1) / 2)
            x, y = int(u * bw), int(v * hz * 0.85)
            c.create_rectangle(x, y, x + sz * 2, y + sz * 2, fill=mix("#05010f", "#ffffff", tw * 0.9), outline="")
        r = int(min(bw, bh) * 0.20)                                         # striped retro sun
        cx, cy = int(bw * 0.70), hz - int(r * 0.12 + 3 * math.sin(t * 0.8))
        b = 6
        for k, dy in enumerate(range(-r, r, b)):
            yy = cy + dy
            if yy + b > hz:
                break
            hw = int(math.sqrt(max(0.0, r * r - (dy + b / 2) ** 2)) / b) * b
            frac = (dy + r) / (2 * r)
            if hw <= 0 or (frac > 0.5 and (k + int(t * 3)) % 4 == 0):
                continue
            c.create_rectangle(cx - hw, yy, cx + hw, yy + b, fill=mix("#ffe45a", NEON_P, frac), outline="")
        bsz = 8                                                             # blinking pixel skyline
        c.create_image(0, hz - 17 * bsz, image=self.city_image(bw, hz), anchor="nw")   # building bodies (baked)
        for x, w, h, wins in CITY:
            x0 = x * bsz
            if x0 > bw:
                break
            top = hz - h * bsz
            for wx, wy, ph in wins:
                if math.sin(t * 1.3 + ph) > -0.3:
                    c.create_rectangle(x0 + wx * bsz + 1, top + wy * bsz + 1, x0 + wx * bsz + 6, top + wy * bsz + 6,
                        fill=NEON_C if ph > 3.1 else NEON_P, outline="")
        c.create_rectangle(0, hz, bw, bh, fill="#07031a", outline="")       # neon grid floor
        c.create_rectangle(0, hz, bw, hz + 3, fill=NEON_P, outline="")
        vx = bw / 2
        for i in range(-11, 12):
            c.create_line(vx + i * 9, hz, vx + i * bw / 8.5, bh, fill="#3a1480")
        for k in range(12):
            tt = (k + (t * 0.5) % 1) / 12
            y = hz + (bh - hz) * (tt ** 2.2)
            c.create_line(0, y, bw, y, fill=mix("#2a0a5a", NEON_P, tt))
        self.draw_crawler(bh * 0.88, pal)

    def draw_crawler(self, base, pal):
        """The 8-bit snake that slithers across the bottom of every menu screen."""
        c, t, bw = self.canvas, self.time, self.bw
        hx = (t * 110) % (bw + 500) - 150

        def ypos(x):
            return base + math.sin(x * 0.022 + t * 1.5) * 16

        for i in range(18, 0, -1):
            x = hx - i * 13
            if x < -20 or x > bw:
                continue
            y = ypos(x)
            c.create_rectangle(x + 2, y + 14, x + 14, y + 17, fill="#12062a", outline="")
            c.create_rectangle(x, y, x + 12, y + 12, fill=pal[1] if i % 2 else pal[3], outline="#0a0a14")
            c.create_rectangle(x + 2, y + 2, x + 6, y + 5, fill=pal[4], outline="")
        y = ypos(hx)
        c.create_rectangle(hx, y - 1, hx + 18, y + 14, fill=pal[1], outline="#0a0a14")
        c.create_rectangle(hx + 2, y + 1, hx + 8, y + 4, fill=pal[4], outline="")
        blink = (t % 3.0) < 0.12
        for ex in (hx + 8, hx + 8):
            if not blink:
                c.create_rectangle(ex, y + 3, ex + 5, y + 8, fill="#ffffff", outline="")
                c.create_rectangle(ex + 3, y + 4, ex + 5, y + 7, fill="#0a0a14", outline="")
        if int(t * 4) % 3 == 0:                                             # tongue flick
            c.create_rectangle(hx + 18, y + 6, hx + 25, y + 8, fill="#ff3050", outline="")
            c.create_rectangle(hx + 24, y + 4, hx + 27, y + 6, fill="#ff3050", outline="")
            c.create_rectangle(hx + 24, y + 8, hx + 27, y + 10, fill="#ff3050", outline="")

    def draw_title(self, t):
        bw, bh = self.bw, self.bh
        text = "REPAIR TERMINAL"
        s = max(3, min(10, int(bw * 0.84 / compile_text(text)[1])))
        slide = (1 - ease(t / 0.9)) * -220
        bob = math.sin(self.time * 2.0) * 1.2 if t > 0.9 else 0.0
        y = int(bh * 0.06 + slide + bob)
        glitch = s if (self.time % 7.0) < 0.08 else 0.0
        # One cached pixel image for the title instead of one Canvas image per glyph.
        self.ptext(bw / 2, y, text, s, anchor="c", shadow=("#6a1060", int(s * 0.55), int(s * 0.55)),
            grad=("#8ffbff", "#ff5da2"), glitch=glitch)
        ty = y + 7 * s + s * 1.4
        x0, x1 = bw / 2 - text_width(text, s) / 2, bw / 2 + text_width(text, s) / 2
        self.canvas.create_line(x0, ty, x1, ty, fill="#14456a", width=2)
        seg = x0 + ((self.time * 260) % max(1, x1 - x0))
        self.canvas.create_rectangle(seg, ty - 1, min(x1, seg + 72), ty + 1, fill="#ffffff", outline="")
        sub = "SNAKE ACTION-RPG   //   EAT. EVOLVE. REPAIR."
        shown = max(0, int((t - 0.9) * 26))
        txt = sub[:shown] + ("*" if int(self.time * 2.5) % 2 == 0 and shown < len(sub) + 6 else "")
        if shown:
            self.ptext(bw / 2, ty + 14, txt, 2, "#9fd0ff", anchor="c")
        # Pixel-art title frame / scan brackets.
        pulse = 0.55 + 0.45 * math.sin(self.time * 3.0)
        col = mix("#173451", NEON_C, pulse)
        self.canvas.create_rectangle(x0 - 18, y - 9, x0 - 10, y - 6, fill=col, outline="")
        self.canvas.create_rectangle(x1 + 10, y - 9, x1 + 18, y - 6, fill=NEON_P, outline="")

    # ------------------------------------------------------------------ screens
    def draw_menu_screen(self):
        self.menu_rects = []
        self.draw_synth_bg()
        t = self.time - self.menu_t0
        if self.state == "menu":
            self.draw_title(t)
            self.draw_list_menu("// MAIN MENU", t)
            self.draw_loadout()
            self.ptext(self.bw / 2, self.bh - 18, "W/S: SELECT    ENTER: CONFIRM    F11: FULLSCREEN", 2,
                "#4a6a9a", anchor="c")
        elif self.state == "classes":
            self.draw_class_select()
        elif self.state == "controls":
            self.draw_controls()
        elif self.state == "settings":
            self.draw_settings()
        elif self.state == "keybindings":
            self.draw_keybindings()
        elif self.state == "credits":
            self.draw_credits()

    def draw_list_menu(self, header, t, centered=False):
        c, bw, bh = self.canvas, self.bw, self.bh
        items = self.menu_items()
        n = len(items)
        row_h = 40 if n >= 7 else 46
        pw, ph = 330, 66 + n * row_h + 14
        slide = (1 - ease((t - 0.4) / 0.7)) * -420 if not centered else 0
        x0 = (bw - pw) / 2 if centered else 40 + slide
        y0 = (bh - ph) / 2 if centered else max(112, bh * 0.27)
        x1, y1 = x0 + pw, y0 + ph
        self.panel(x0, y0, x1, y1)
        self.ptext(x0 + 22, y0 + 18, header, 2, NEON_C)
        if int(self.time * 2) % 2 == 0:
            c.create_rectangle(x1 - 30, y0 + 18, x1 - 20, y0 + 28, fill=NEON_P, outline="")
        c.create_line(x0 + 18, y0 + 40, x1 - 18, y0 + 40, fill=PANEL_LINE, width=2)
        for i, (_act, label, sub) in enumerate(items):
            iy = y0 + 54 + i * row_h
            sel = i == self.menu_sel
            self.menu_rects.append((x0 + 10, iy - 4, x1 - 10, iy + 38, "item", i))
            if sel:
                pulse = 0.5 + 0.5 * math.sin(self.time * 6)
                c.create_rectangle(x0 + 12, iy - 4, x1 - 12, iy + 38, fill=mix("#0a2640", "#0f4466", pulse), outline=NEON_C)
                c.create_rectangle(x0 + 12, iy - 4, x0 + 20, iy + 38, fill=NEON_C, outline="")
                if int(self.time * 3) % 2 == 0:
                    ax = x0 + 32
                    c.create_polygon(ax, iy + 9, ax, iy + 27, ax + 12, iy + 18, fill=NEON_P, outline="")
            col = "#ffffff" if sel else "#6f9bd1"
            self.ptext(x0 + 54 + (4 if sel else 0), iy + 8, label, 3, col, shadow=("#000000", 2, 2) if sel else None)
            if sub:
                self.ptext(x1 - 24, iy + 14, sub, 2, CLASSES[self.pclass]["col"] if label == "CLASS" else "#7aa7d6", anchor="e")

    def draw_loadout(self):
        c, bw, bh = self.canvas, self.bw, self.bh
        cls = CLASSES[self.pclass]
        w, h = 270, 132
        x1, x0 = bw - 36, bw - 36 - w
        y0 = bh * 0.62
        if x0 < 390:
            return
        slide = (1 - ease((self.time - self.menu_t0 - 0.7) / 0.7)) * 400
        x0, x1 = x0 + slide, x1 + slide
        self.panel(x0, y0, x1, y0 + h, cls["col"], 12)
        self.ptext(x0 + 18, y0 + 14, "// LOADOUT", 2, cls["col"])
        self.draw_pix("snake_head", x0 + 44, y0 + 58, 4, dict(G=cls["pal"][0], H=cls["pal"][1]))
        self.ptext(x0 + 86, y0 + 38, cls["name"], 3, "#ffffff")
        self.ptext(x0 + 86, y0 + 64, cls["role"], 2, cls["col"])
        for i, (lab, v) in enumerate(cls["bars"].items()):
            bx, by = x0 + 18 + (i % 2) * 124, y0 + 92 + (i // 2) * 18
            self.ptext(bx, by, lab, 2, "#7aa7d6")
            for k in range(5):
                c.create_rectangle(bx + 40 + k * 14, by, bx + 40 + k * 14 + 10, by + 10,
                    fill=cls["col"] if k < v else "#16223f", outline="")

    def draw_class_select(self):
        c, bw, bh = self.canvas, self.bw, self.bh
        self.ptext(bw / 2, bh * 0.05, "SELECT CLASS", 6, anchor="c", shadow=("#6a1060", 3, 3), grad=("#8ffbff", "#ff5da2"))
        n, gap = len(CLASS_ORDER), 14
        cw = min(210, (bw - 60 - gap * (n - 1)) / n)
        ch = int(bh * 0.60)
        x0 = (bw - (n * cw + (n - 1) * gap)) / 2
        y0 = int(bh * 0.19)
        small = ("Consolas", 8, "bold") if cw < 185 else MONO
        for i, cid in enumerate(CLASS_ORDER):
            cls = CLASSES[cid]
            sel = i == self.class_sel
            x, y = x0 + i * (cw + gap), y0 - (8 if sel else 0)
            self.menu_rects.append((x, y, x + cw, y + ch, "class", i))
            c.create_polygon(chamfer(x, y, x + cw, y + ch, 16), fill="#0a1024" if not sel else "#0d1a3a",
                outline=cls["col"] if sel else "#1f3a66", width=3 if sel else 2)
            c.create_rectangle(x + 8, y + 8, x + cw - 8, y + 30, fill=cls["col"] if sel else mix(cls["col"], "#0a1024", 0.65), outline="")
            self.ptext(x + cw / 2, y + 13, cls["role"], 2, "#05080f", anchor="c")
            bob = math.sin(self.time * 3 + i) * 3 if sel else 0
            self.draw_pix("snake_head", x + cw / 2, y + 74 + bob, 5, dict(G=cls["pal"][0], H=cls["pal"][1]))
            self.ptext(x + cw / 2, y + 110, cls["name"], 3, "#ffffff" if sel else "#8fb4e0", anchor="c")
            for k, (lab, v) in enumerate(cls["bars"].items()):
                by = y + 146 + k * 20
                bx = x + cw / 2 - 52
                self.ptext(bx, by, lab, 2, "#7aa7d6")
                for p in range(5):
                    c.create_rectangle(bx + 44 + p * 14, by, bx + 44 + p * 14 + 10, by + 10,
                        fill=cls["col"] if p < v else "#16223f", outline="")
            for k, line in enumerate(cls["desc"]):
                c.create_text(x + cw / 2, y + 242 + k * 15, text=line, fill=C_TEXT if sel else C_MUTED, font=small)
            if sel and int(self.time * 2.5) % 2 == 0:
                self.ptext(x + cw / 2, y + ch - 24, "> SELECT <", 2, cls["col"], anchor="c")
        self.menu_rects.append((18, bh - 44, 150, bh - 10, "back", 0))
        c.create_rectangle(18, bh - 44, 150, bh - 10, fill="#0a1024", outline=NEON_C, width=2)
        self.ptext(84, bh - 33, "< BACK", 2, NEON_C, anchor="c")
        self.ptext(bw / 2, bh - 18, "A/D: BROWSE    ENTER: CHOOSE    ESC: BACK", 2, "#4a6a9a", anchor="c")
        if self.in_game:
            self.ptext(bw / 2, bh * 0.19 + ch + 16, "APPLIES TO THE NEXT NEW GAME", 2, "#ffd34d", anchor="c")

    CONTROLS = [("WASD / ARROWS", "MOVE"), ("LEFT CLICK", "CLASS PRIMARY ATTACK"), ("RIGHT CLICK", "HOLD TO RUN"),
        ("SHIFT", "DASH"), ("SPACE", "FIRE PULSE CHARGE"), ("Q E R F C", "FIVE ACTIVE SKILL SLOTS"),
        ("X", "SWITCH SKILL SET"), ("1-9 / WHEEL / [ ]", "SWITCH ELEMENT"), ("TAB", "PASSIVE / SKILL TREES"),
        ("ESC / P", "PAUSE MENU"), ("M / N", "MINIMAP / RESTART"), ("SETTINGS", "KEY BINDINGS / RESET DEFAULTS")]

    def draw_controls(self):
        c, bw, bh = self.canvas, self.bw, self.bh
        self.ptext(bw / 2, bh * 0.04, "CONTROLS", 6, anchor="c", shadow=("#6a1060", 3, 3), grad=("#8ffbff", "#ff5da2"))
        half = (len(self.CONTROLS) + 1) // 2
        x0, y0, x1, y1 = 36, bh * 0.17, bw - 36, bh * 0.17 + 22 + half * 27 + 84
        self.panel(x0, y0, x1, y1)
        colw = (x1 - x0 - 40) / 2
        for i, (key, act) in enumerate(self.CONTROLS):
            cx = x0 + 22 + (i // half) * colw
            ry = y0 + 22 + (i % half) * 27
            c.create_rectangle(cx, ry, cx + 124, ry + 21, fill="#0c1a38", outline=NEON_C)
            if key == "X":
                key = str(self.settings.get("skill_set_toggle_key", "x")).upper()
            c.create_text(cx + 62, ry + 11, text=key, fill="#ffffff", font=MONO)
            c.create_text(cx + 136, ry + 11, text=act, anchor="w", fill=C_TEXT, font=MONO)
        ty = y0 + 36 + half * 27
        from ..data.keybinds import SKILL_LABELS, SKILL_SLOT_IDS, skill_ids_for_bar
        slot_keys = self.settings.get("skill_slot_keys", {})
        def bar_hint(index):
            items = []
            for slot, skill_id in zip(SKILL_SLOT_IDS, skill_ids_for_bar(self.run_class, index)):
                ability = self.skill_tier("v")["short"].upper() if skill_id == "class_skill" else SKILL_LABELS[skill_id]
                items.append(f"{slot_keys.get(slot, '?').upper()} {ability}")
            return f"SET {index + 1}: " + "  /  ".join(items)
        tips = [bar_hint(0), bar_hint(1),
            "HIT A WALL / OBSTACLE = DAMAGE, NOT DEATH. PRESS THE OPPOSITE DIRECTION WHILE BLOCKED TO REVERSE."]
        for k, line in enumerate(tips):
            c.create_text(x0 + 22, ty + k * 18, anchor="w", text=line, fill="#ffd34d", font=MONO)
        self.menu_rects.append((18, bh - 44, 150, bh - 10, "back", 0))
        c.create_rectangle(18, bh - 44, 150, bh - 10, fill="#0a1024", outline=NEON_C, width=2)
        self.ptext(84, bh - 33, "< BACK", 2, NEON_C, anchor="c")
        self.ptext(bw / 2, bh - 18, "ESC / ENTER: BACK", 2, "#4a6a9a", anchor="c")

    def draw_settings(self):
        c, bw, bh = self.canvas, self.bw, self.bh
        self.ptext(bw / 2, bh * 0.045, "SETTINGS", 6, anchor="c", shadow=("#6a1060", 3, 3), grad=("#8ffbff", "#ff5da2"))
        pw = min(760, bw - 70)
        x0, x1 = (bw - pw) / 2, (bw + pw) / 2
        y0, y1 = bh * 0.14, bh - 74
        self.panel(x0, y0, x1, y1, NEON_C, 14)
        c.create_text(x0 + 26, y0 + 28, text="AUDIO / VIDEO / ACCESSIBILITY", anchor="w", fill="#ffffff", font=MONO)
        row_y = y0 + 48
        # Fit all settings, including the new keybindings entry, above the help text.
        row_h = min(34, (y1 - row_y - 88) / max(1, len(SETTINGS_ROWS)))
        for i, (key, label, desc) in enumerate(SETTINGS_ROWS):
            yy = row_y + i * row_h
            selected = i == self.settings_sel
            if selected:
                c.create_rectangle(x0 + 20, yy - 4, x1 - 20, yy + row_h - 5, fill="#0d1e3e", outline=NEON_C, width=1)
            c.create_text(x0 + 34, yy + 9, text=label, anchor="w", fill="#ffffff" if selected else "#7ea6d8", font=("Consolas", 8, "bold"))
            c.create_text(x0 + 34, yy + 22, text=desc, anchor="w", fill="#4f719b", font=("Consolas", 6))
            c.create_rectangle(x1 - 184, yy + 2, x1 - 154, yy + 27, fill="#09132b", outline="#25456b")
            c.create_text(x1 - 169, yy + 12, text="<", fill=NEON_C, font=MONO)
            c.create_rectangle(x1 - 148, yy + 1, x1 - 70, yy + 26, fill="#09132b", outline="#25456b")
            val = self.settings_value_text(key)
            c.create_text(x1 - 109, yy + 13, text=val, fill=NEON_C if selected else "#9bb9df", font=("Consolas", 8, "bold"))
            c.create_rectangle(x1 - 64, yy + 1, x1 - 34, yy + 26, fill="#09132b", outline="#25456b")
            c.create_text(x1 - 49, yy + 12, text=">", fill=NEON_C, font=MONO)
            self.menu_rects.append((x1 - 184, yy + 1, x1 - 154, yy + 26, "settings_prev", i))
            self.menu_rects.append((x1 - 64, yy + 1, x1 - 34, yy + 26, "settings_next", i))
            if key == "keybindings":
                self.menu_rects.append((x1 - 148, yy + 1, x1 - 70, yy + 26, "settings_open", i))
        hy = row_y + len(SETTINGS_ROWS) * row_h + 6
        for i, line in enumerate(SETTINGS_HELP):
            c.create_text(x0 + 26, hy + i * 15, text=line, anchor="w", fill="#5f83ac", font=("Consolas", 7))
        self.menu_rects.append((18, bh - 48, 150, bh - 12, "back", 0))
        c.create_rectangle(18, bh - 48, 150, bh - 12, fill="#0a1024", outline=NEON_C, width=2)
        self.ptext(84, bh - 37, "< BACK", 2, NEON_C, anchor="c")
        self.ptext(bw / 2, bh - 20, "W/S SELECT    A/D CHANGE    ENTER OPEN    ESC BACK", 2, "#4a6a9a", anchor="c")

    def draw_keybindings(self):
        c, bw, bh = self.canvas, self.bw, self.bh
        self.ptext(bw / 2, bh * 0.045, "KEY BINDINGS", 6, anchor="c",
                   shadow=("#6a1060", 3, 3), grad=("#8ffbff", "#ff5da2"))
        x0, x1 = max(44, (bw - 700) / 2), min(bw - 44, (bw + 700) / 2)
        y0, row_h = bh * 0.16, min(62, (bh * 0.55) / 6)
        self.panel(x0, y0, x1, y0 + 6 * row_h + 105, NEON_C, 14)
        c.create_text(x0 + 28, y0 + 24, text="SKILL BAR  //  FIVE CLOSE-REACH SLOTS + TOGGLE",
                      anchor="w", fill="#ffffff", font=MONO)
        slot_keys = self.settings.get("skill_slot_keys", {})
        rows = [(f"SLOT {i + 1}", slot_keys.get(f"slot_{i + 1}", "?").upper(),
                 "Shared by the same position on both skill sets") for i in range(5)]
        rows.append(("SWITCH SKILL SET", self.settings.get("skill_set_toggle_key", "x").upper(),
                     "Swap the five active skills without resetting cooldowns"))
        for i, (label, value, desc) in enumerate(rows):
            yy = y0 + 44 + i * row_h
            selected = i == getattr(self, "keybinds_sel", 0)
            c.create_rectangle(x0 + 20, yy, x1 - 20, yy + row_h - 6,
                               fill="#0d1e3e" if selected else "#080f23",
                               outline=NEON_C if selected else "#1b3558", width=2 if selected else 1)
            c.create_text(x0 + 36, yy + 13, text=label, anchor="w",
                          fill="#ffffff" if selected else "#7ea6d8", font=("Consolas", 10, "bold"))
            c.create_text(x0 + 36, yy + 31, text=desc, anchor="w",
                          fill="#4f719b", font=("Consolas", 7))
            c.create_rectangle(x1 - 118, yy + 7, x1 - 36, yy + row_h - 14,
                               fill="#09132b", outline=NEON_C)
            val = "PRESS KEY..." if selected and getattr(self, "awaiting_keybind", False) else value
            c.create_text(x1 - 77, yy + row_h / 2 - 2, text=val, fill=NEON_C,
                          font=("Consolas", 12, "bold"))
            self.menu_rects.append((x0 + 20, yy, x1 - 20, yy + row_h - 6, "keybind", i))
        footer_y = y0 + 44 + 6 * row_h + 8
        c.create_rectangle(x0 + 24, footer_y, x0 + 190, footer_y + 30,
                           fill="#09132b", outline=NEON_P, width=2)
        c.create_text(x0 + 107, footer_y + 15, text="RESET DEFAULTS (R)",
                      fill=NEON_P, font=("Consolas", 8, "bold"))
        self.menu_rects.append((x0 + 24, footer_y, x0 + 190, footer_y + 30, "keybind_reset", 0))
        message = ("PRESS A LETTER KEY  •  ESC CANCELS" if getattr(self, "awaiting_keybind", False)
                   else getattr(self, "keybind_message", "W/S SELECT  •  ENTER REBIND  •  R RESET"))
        c.create_text(x0 + 210, footer_y + 15, text=message[:78], anchor="w",
                      fill="#ffd34d" if getattr(self, "awaiting_keybind", False) else "#8daed4",
                      font=("Consolas", 8))
        self.menu_rects.append((18, bh - 48, 150, bh - 12, "back", 0))
        c.create_rectangle(18, bh - 48, 150, bh - 12, fill="#0a1024", outline=NEON_C, width=2)
        self.ptext(84, bh - 37, "< BACK", 2, NEON_C, anchor="c")
        self.ptext(bw / 2, bh - 20,
                   "W/S SELECT    ENTER REBIND    R RESET DEFAULTS    ESC BACK", 2, "#4a6a9a", anchor="c")

    def settings_value_text(self, key):
        if key == "keybindings":
            return "OPEN"
        s = self.settings[key]
        if key.endswith("_volume"):
            return f"{int(round(s * 100)):3d}%"
        if key == "vfx_quality":
            return ("LOW", "MED", "HIGH")[int(s)]
        if key == "fps_cap":
            return "UNLIMITED" if int(s) == 0 else f"{int(s)} FPS"
        return "ON" if s else "OFF"

    def draw_credits(self):
        c, bw, bh = self.canvas, self.bw, self.bh
        self.ptext(bw / 2, bh * 0.045, "CREDITS", 6, anchor="c", shadow=("#6a1060", 3, 3), grad=("#8ffbff", "#ff5da2"))
        x0, x1 = 46, bw - 46
        y0, y1 = bh * 0.13, bh - 60
        self.panel(x0, y0, x1, y1, NEON_P, 14)
        clip_top, clip_bottom = y0 + 38, y1 - 16
        c.create_rectangle(x0 + 8, clip_top, x1 - 8, clip_bottom, fill=PANEL_BG, outline="")
        y = clip_top + 12 - self.credits_scroll
        for cat, name, desc in CREDITS_LINES:
            if y < clip_top - 30 or y > clip_bottom + 24:
                y += 28 if cat or name or desc else 18
                continue
            if not cat and not name and not desc:
                y += 14
                continue
            if cat:
                c.create_text(x0 + 22, y, text=cat, anchor="w", fill=NEON_C if cat in ("TEAM", "AUDIO") else NEON_P, font=("Consolas", 7, "bold"))
            c.create_text(x0 + 92, y, text=name, anchor="w", fill="#ffffff", font=MONO)
            c.create_text(x0 + 305, y, text=desc, anchor="w", fill="#7fa5d4", font=("Consolas", 7))
            y += 28
        max_scroll = max(0.0, y - clip_bottom + 18)
        self.credits_scroll = min(self.credits_scroll, max_scroll)
        c.create_text(x1 - 22, clip_bottom + 2, text="W/S / WHEEL  SCROLL", anchor="e", fill="#4a6a9a", font=("Consolas", 7))
        self.menu_rects.append((18, bh - 48, 150, bh - 12, "back", 0))
        c.create_rectangle(18, bh - 48, 150, bh - 12, fill="#0a1024", outline=NEON_C, width=2)
        self.ptext(84, bh - 37, "< BACK", 2, NEON_C, anchor="c")
        self.ptext(bw / 2, bh - 20, "ESC / ENTER: BACK", 2, "#4a6a9a", anchor="c")

    def draw_pause_menu(self):
        """Futuristic pause menu drawn over the frozen game."""
        c, bw, bh = self.canvas, self.bw, self.bh
        c.create_rectangle(0, 0, bw, bh, fill="#02040a", stipple="gray50", outline="")
        self.menu_rects = []
        self.ptext(bw / 2, bh / 2 - 190, "PAUSED", 6, anchor="c", shadow=("#6a1060", 3, 3), grad=("#8ffbff", "#ff5da2"))
        self.draw_list_menu("// SYSTEM", 99, centered=True)
