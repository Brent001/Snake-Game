"""Scene rendering on top of the baked scenery: horizon, decor chunks, boss arenas, ambience and vignette.

Everything here costs a handful of `create_image` calls per frame (the old code created 600-2,000 vector items).
"""
import math

from ..config import CELL, CHUNK, DAY_GRADE_STIPPLE, GRID_H, GRID_W, WORLD_H
from ..world.layout import ARENA_ZONE, ARENAS
from ..world.level import B2MAP, BMAP, NODES, WALLS, WMAP
from .terrain import LEVELS, wall_chunk_set
from .world_draw_consts import RENDER_WALLS
from .scenery import (AP, ARENA_MARGIN, AURA_COL, AURA_FRAMES, MOON_GLOW, SC, SceneryBank, horizon_h, paint_moon, paint_sun, sky_rows)

# ambience per biome: (sprite, count, drift px/s (vx, vy), sway px)
AMBIENCE = {
    0: (("mote", 22, (7, 5), 6),),
    1: (("snow", 34, (-6, 24), 16),),
    2: (("firefly", 14, (0, 0), 34), ("spore", 18, (3, -14), 10)),
    3: (("ember", 26, (2, -28), 12),),
    4: (("wisp", 8, (4, -9), 22), ("petal", 14, (-12, 16), 12)),
    5: (("petal", 28, (-18, 20), 14),),
}


class SceneMixin:
    # ------------------------------------------------------------------ bank / day-night
    @property
    def bank(self):
        b = self.__dict__.get("_bank")
        if b is None:
            import tkinter as tk
            b = self._bank = SceneryBank(tk, self.canvas, GRID_W, GRID_H, lambda x, y: BMAP[y][x],
                lambda x, y: (x, y) in WALLS or (x, y) in NODES or (x, y) in ARENA_ZONE)
            b.maps = (BMAP, B2MAP, WMAP)
            b.is_wall = lambda x, y: (x, y) in RENDER_WALLS
        return b

    def is_night(self, cb):
        if cb == 0:
            return True
        n = self.__dict__.get("_night", True)
        if n and self.dl > 0.62:
            n = False
        elif not n and self.dl < 0.38:
            n = True
        self._night = n
        return n

    # ------------------------------------------------------------------ horizon (sky + ridge + mist)
    # ------------------------------------------------------------------ dynamic sky (gradient + sun + moon + stars)
    def _cel_sprite(self, kind, k, hor, y_center, half):
        """Sun / moon sprite cropped at the horizon: returns (image, top_y) or None when fully hidden.
        `half` = sprite half-height in real px.  Rows below the horizon are removed so a rising body really emerges."""
        top = y_center - half
        rows = int((hor - top) // SC)
        total = int(half * 2 // SC)
        if rows <= 0:
            return None
        cut = max(0, total - rows)
        key = (kind, k, cut)
        bank = self.bank
        img = bank.c.get(("cel",) + key)
        if img is None:
            art = paint_sun(k) if kind == "sun" else paint_moon(k)
            for y in range(max(0, art.h - cut), art.h):          # rows below the horizon become transparent
                art.span(0, art.w, y, b"\x00\x00\x00\x00")
            img = bank.c[("cel",) + key] = bank._img(art, SC)
        return img, top

    def draw_dynamic_sky(self, cb, W, H, dy, parx):
        c, bank, t = self.canvas, self.bank, self.time
        hor = horizon_h(H)
        ph, elev, dl, tw = self.sun_phase, self.sun_elev, self.dl, self.sun_tw
        rising = self.sun_rising
        # ---- gradient: rebuilt only when the (quantised) state changes, drawn as ~26 flat bands
        key = (cb, int(dl * 48), int(tw * 12), rising)
        if self.__dict__.get("_sky_key") != key:
            self._sky_key, self._sky_rows = key, sky_rows(cb, dl, tw, rising)
        rows = self._sky_rows
        n = len(rows)
        y0 = -34 + dy
        span = hor + 3 - y0
        for i, col in enumerate(rows):
            ya = y0 + span * i // n
            yb = y0 + span * (i + 1) // n + 1
            c.create_rectangle(0, ya, W, yb, fill=col, outline="")
        # ---- stars fade in one by one as the sky darkens (colour is mixed with the band behind, i.e. a true alpha)
        a_night = max(0.0, min(1.0, (0.52 - dl) / 0.42))
        if a_night > 0 and self.quality > 0:
            from ..utils import mix
            total = 56 if self.quality > 1 else 30
            top_h = max(20, hor - 26)
            for i in range(total):
                rank = i / total
                al = max(0.0, min(1.0, a_night * 1.7 - rank * 0.7))
                if al <= 0:
                    continue
                tw_k = 0.65 + 0.35 * math.sin(t * (1.1 + (i % 5) * 0.37) + i * 1.7)
                x = (i * 211 + 40 - parx * 0.02) % W
                yy = (i * 67 + 11) % top_h
                band = rows[min(n - 1, max(0, int((yy / hor) * (n - 1))))]
                col = mix(band, "#ffffff" if i % 3 else "#cfe8ff", al * tw_k)
                sz = 3 if i % 7 == 0 else 2
                c.create_rectangle(x, yy + dy, x + sz, yy + dy + sz, fill=col, outline="")
        # ---- sun and moon travel along an arc; sunrise / sunset glow lies on the horizon below the sun
        if elev > -0.30:
            sx = W * (0.10 + 0.80 * min(1.0, ph / 0.5)) if ph < 0.5 else W * 0.9
            sy = hor - elev * hor * 0.68
            if tw > 0.06 and elev < 0.5:
                g = bank.horizon_glow(max(1, min(4, int(round(tw * 4)))), rising)
                c.create_image(sx, hor + dy + 2, image=g, anchor="s")
            kk = 0 if elev > 0.62 else 1 if elev > 0.38 else 2 if elev > 0.18 else 3 if elev > 0.05 else 4
            got = self._cel_sprite("sun", kk, hor, sy, 7.5 * SC)
            if got:
                c.create_image(sx, got[1] + dy, image=got[0], anchor="n")
        if elev < 0.30:
            mph = (ph + 0.5) % 1.0
            mx = W * (0.10 + 0.80 * min(1.0, mph / 0.5)) if mph < 0.5 else W * 0.9
            my = hor + elev * hor * 0.68
            got = self._cel_sprite("moon", cb if cb in MOON_GLOW else 1, hor, my, 7.5 * SC)
            if got:
                c.create_image(mx, got[1] + dy, image=got[0], anchor="n")
        # ---- silhouettes (baked for 5 light levels, near-invisible steps) and the faster ridge
        lvl = int(round(dl * 4))
        sky = bank.skyline(cb, lvl, W, H)
        ridge = bank.ridge_dl(cb, lvl, W, H)
        Ws = sky.width()
        for img, f in ((sky, 0.02), (ridge, 0.06)):
            ox = -((parx * f) % Ws)
            c.create_image(ox, dy, image=img, anchor="nw")
            if ox + Ws < W:
                c.create_image(ox + Ws, dy, image=img, anchor="nw")

    def draw_horizon(self, cb):
        c, bank, t = self.canvas, self.bank, self.time
        W, H = self.bw, self.bh
        night = self.is_night(cb)
        parx = self.cam_x * CELL
        pary = self.cam_y * CELL
        dy = -int(pary / (GRID_H * CELL) * 26)               # a little vertical parallax across the whole world
        if cb == 0:                                          # Frost Moon: eternal night, classic baked sky
            sky = bank.sky(cb, night, W, H)
            ridge = bank.ridge(cb, night, W, H)
            Ws = sky.width()
            for img, f in ((sky, 0.02), (ridge, 0.06)):
                ox = -((parx * f) % Ws)
                c.create_image(ox, dy, image=img, anchor="nw")
                if ox + Ws < W:
                    c.create_image(ox + Ws, dy, image=img, anchor="nw")
        else:
            self.draw_dynamic_sky(cb, W, H, dy, parx)
        hor = horizon_h(H)
        fog = bank.fog(cb, W, H)
        Wf = fog.width()
        for k, (speed, y, f) in enumerate(((7.0, hor - 40, 0.10), (-4.0, hor + 28, 0.16))):
            ox = -((parx * f + t * speed) % Wf)
            c.create_image(ox, y + dy, image=fog, anchor="nw")
            if ox + Wf < W:
                c.create_image(ox + Wf, y + dy, image=fog, anchor="nw")
        if cb == 0 and self.quality > 0:                       # twinkling stars over the Frost Moon (other biomes: draw_dynamic_sky)
            mote = bank.particle("mote", 0)
            for i in range(12 if self.quality > 1 else 6):
                if (int(t * 1.3 + i * 0.37) + i) % 3:
                    x = (i * 211 + 40 - parx * 0.02) % W
                    y = (i * 67 + 11) % max(20, hor - 24)
                    c.create_image(x, y + dy, image=mote)
        if cb == 0:                                            # shooting stars over the Frost Moon
            for k in range(2):
                ph = (t * 0.16 + k * 0.5) % 1.0
                if ph < 0.16:
                    u = ph / 0.16
                    x, y = W * (0.15 + 0.5 * k) + u * 260, 20 + u * 90 + k * 30
                    c.create_line(x - 46, y - 22, x, y, fill="#5faee8", width=2)
                    c.create_line(x - 16, y - 8, x, y, fill="#f0fbff", width=2)

    # ------------------------------------------------------------------ baked terrain layers
    def terrain_lvl(self):
        """Day-light step the terrain chunks are baked for (the palettes follow the day / night cycle)."""
        return int(round(self.dl * (LEVELS - 1)))

    def _visible_chunks(self, margin=0):
        x0, y0 = int(math.floor(self.cam_x)), int(math.floor(self.cam_y))
        cx0, cx1 = max(0, x0 // CHUNK - margin), min((GRID_W - 1) // CHUNK, (x0 + int(self.vw) + 2) // CHUNK + margin)
        cy0, cy1 = max(0, y0 // CHUNK - margin), min((WORLD_H - 1) // CHUNK, (y0 + int(self.vh) + 2) // CHUNK + margin)
        return cx0, cx1, cy0, cy1

    def _draw_layer(self, kind, chunk_ok):
        c, bank = self.canvas, self.bank
        lvl = self.terrain_lvl()
        cx0, cx1, cy0, cy1 = self._visible_chunks()
        for cy in range(cy0, cy1 + 1):
            for cx in range(cx0, cx1 + 1):
                if not chunk_ok(cx, cy):
                    continue
                stale = kind != "decor" and bank.tc.get((kind, cx, cy), (lvl,))[0] != lvl
                rebake = stale and self._bake_budget > 0
                if rebake or not bank.terrain_cached(kind, cx, cy):
                    self._bake_budget -= 1                    # (a missing chunk is always baked: nothing to show otherwise)
                img = bank.terrain(kind, cx, cy, lvl, rebake)
                if img is not None:
                    c.create_image(self.px(cx * CHUNK), self.py(cy * CHUNK), image=img, anchor="nw")

    @property
    def tint_chunks(self):
        s = self.__dict__.get("_tint_chunks")
        if s is None:
            s = self._tint_chunks = {(x // CHUNK, y // CHUNK) for y in range(WORLD_H) for x in range(0, GRID_W, 2) if WMAP[y][x]}
        return s

    @property
    def wall_chunks(self):
        s = self.__dict__.get("_wall_chunks")
        if s is None:
            s = self._wall_chunks = wall_chunk_set(RENDER_WALLS)
        return s

    def begin_terrain(self):
        self._bake_budget = 3                                 # stale chunks re-baked per frame (day/night steps)
        cx0, cx1, cy0, cy1 = self._visible_chunks(margin=1)   # 3 layers per visible chunk (+ring) and some slack
        self.bank.tc_cap = max(72, int((cx1 - cx0 + 1) * (cy1 - cy0 + 1) * 3 * 1.4))

    def draw_tint(self):
        tc = self.tint_chunks
        self._draw_layer("tint", lambda cx, cy: (cx, cy) in tc)

    def draw_ground_decor(self):
        self._draw_layer("decor", lambda cx, cy: True)

    def draw_walls(self):
        wc = self.wall_chunks
        self._draw_layer("walls", lambda cx, cy: (cx, cy) in wc)

    def prefetch_terrain(self):
        """Bake ONE missing chunk just outside the screen per frame, so scrolling never has to paint on demand."""
        bank, lvl = self.bank, self.terrain_lvl()
        cx0, cx1, cy0, cy1 = self._visible_chunks(margin=1)
        wc, tc = self.wall_chunks, self.tint_chunks
        for cy in range(cy0, cy1 + 1):
            for cx in range(cx0, cx1 + 1):
                for kind, ok in (("decor", True), ("walls", (cx, cy) in wc), ("tint", (cx, cy) in tc)):
                    if ok and not bank.terrain_cached(kind, cx, cy):
                        bank.terrain(kind, cx, cy, lvl)
                        return

    # ------------------------------------------------------------------ boss arenas
    def draw_arena(self):
        c, bank, t = self.canvas, self.bank, self.time
        for ai, a in enumerate(ARENAS):
            if not (a["x2"] + 3 >= self.cam_x and a["x1"] - 3 <= self.cam_x + self.vw
                    and a["y2"] + 3 >= self.cam_y and a["y1"] - 3 <= self.cam_y + self.vh):
                continue
            img, torches = bank.arena(ai, a)
            ox, oy = a["x1"] - 1 - ARENA_MARGIN, a["y1"] - 1 - ARENA_MARGIN
            c.create_image(self.px(ox), self.py(oy), image=img, anchor="nw")
            b = self.boss
            fighting = self.boss_active() and b["idx"] == ai
            if fighting and b["state"] in ("fight", "banner") and (b["phase"] > 0 or b["state"] == "fight"):
                f = int(t * 6) % AURA_FRAMES
                c.create_image(self.px(a["x1"]), self.py(a["y1"]), image=bank.aura(ai, a, f), anchor="nw")
            fl = int(t * 9)
            for k, (tx, ty) in enumerate(torches):
                c.create_image(self.px(ox + tx), self.py(oy + ty) - 3, image=bank.flame(ai, fl + k))

    # ------------------------------------------------------------------ ambience particles + bats
    def draw_ambience(self, cb):
        c, bank, t = self.canvas, self.bank, self.time
        from .ambient import PARTS
        W, H = self.bw, self.bh
        cxo, cyo = self.cam_x * CELL, self.cam_y * CELL
        scale = (1.0, 0.65, 0.4)[2 - self.quality]
        sin = math.sin
        idx = 0
        for kind, n, (vx, vy), sway in AMBIENCE[cb]:
            n = int(n * scale)
            for j in range(n):
                x0, y0, sp, ph = PARTS[(idx + j) % len(PARTS)]
                x = (x0 + t * vx * sp + sin(t * 0.8 + ph) * sway - cxo * 0.5) % W
                y = (y0 + t * vy * sp - cyo * 0.5) % H
                if kind == "firefly":
                    x = (x0 + sin(t * 0.3 + ph) * 60 - cxo * 0.5) % W
                    y = (y0 * 0.6 + sin(t * 0.37 + ph * 2) * 40 - cyo * 0.5) % H
                c.create_image(x, y, image=bank.particle(kind, int(t * 4 + ph * 2) % 3 if kind != "mote" else 0))
            idx += n
        if cb == 3 and self.quality > 0:
            for k in range(3):
                x = (t * 46 + k * 330) % (W + 80) - 40
                y = 46 + 28 * sin(t * 0.9 + k * 2.1) + k * 24
                c.create_image(x, y, image=bank.particle("bat", int(t * 9 + k) % 3))

    # ------------------------------------------------------------------ dawn / dusk / night colour wash
    def _stipple_ok(self):
        v = self.__dict__.get("_stip")
        if v is None:
            try:
                ws = str(self.root.tk.call("tk", "windowingsystem"))
            except Exception:
                ws = ""
            v = self._stip = bool(DAY_GRADE_STIPPLE) and ws in ("win32", "x11")     # Aqua ignores stipple (would be solid)
        return v

    def draw_grade(self, cb):
        """Dithered full-screen wash: warm gold / rose at sunrise, orange at sunset, a faint deep blue at night.
        One stippled rectangle (hardware pattern brush) - no per-pixel work."""
        if cb == 0 or getattr(self, "in_dungeon", False) or not self._stipple_ok():
            return
        tw, dl = self.sun_tw, self.dl
        if tw > 0.12:
            col = "#ffb87a" if self.sun_rising else "#ff7a3c"
            pat = "gray12"                                   # (gray25 turned the blue terrain muddy grey)
        elif dl < 0.22:
            col, pat = "#06103a", "gray12"
        else:
            return
        self.canvas.create_rectangle(0, 0, self.bw, self.bh, fill=col, stipple=pat, outline="")

    # ------------------------------------------------------------------ edge vignette (one image)
    def draw_vignette(self, cb):
        b = self.boss
        boss = b["idx"] if self.boss_active() else None
        dl = self.dl
        lvl = 2 if (cb == 0 or dl < 0.2) else (1 if dl < 0.42 else 0)     # bright daylight: no edge dither at all
        if getattr(self, "in_dungeon", False):
            lvl = 1
        if lvl == 0:
            return
        vk = (cb, self.bw, self.bh, boss, lvl)
        if self.__dict__.get("_vig_key") != vk:
            self._vig_key, self._vig_img = vk, self.bank.vignette(cb, self.bw, self.bh, boss, lvl)
        img = self._vig_img
        self.canvas.create_image((self.bw - img.width()) // 2, self.bh - img.height(), image=img, anchor="nw")

    # ------------------------------------------------------------------ idle pre-baking (runs while a menu is showing)
    def spawn_terrain_jobs(self):
        from ..world.layout import START_SNAKE
        sx, sy = START_SNAKE[0]
        jobs = []
        for cy in range(max(0, sy // CHUNK - 3), min(WORLD_H // CHUNK, sy // CHUNK + 1) + 1):
            for cx in range(0, 7):
                jobs.append(("terr", "decor", cx, cy))
                if (cx, cy) in self.wall_chunks:
                    jobs.append(("terr", "walls", cx, cy))
                if (cx, cy) in self.tint_chunks:
                    jobs.append(("terr", "tint", cx, cy))
        return jobs

    def warm_scenery(self):
        """Bake one scenery asset per call so nothing has to be painted mid-fight (arenas take ~70 ms each)."""
        bank = self.bank
        if not bank.todo:
            if self.__dict__.get("_warm_done"):
                return
            self._warm_done = True
            bank.todo = ([("arena", i) for i in range(len(ARENAS))]
                + [("biome", 0, True)]
                + [("dsky", b, lvl) for b in range(1, 6) for lvl in range(5)]          # silhouettes for every light level
                + [("aura", i, f) for i in range(len(ARENAS)) for f in range(AURA_FRAMES)]
                + self.spawn_terrain_jobs())
        job = bank.todo.pop(0)
        if job[0] == "arena":
            bank.arena(job[1], ARENAS[job[1]])
        elif job[0] == "terr":
            bank.terrain(job[1], job[2], job[3], self.terrain_lvl())
        elif job[0] == "biome":
            bank.sky(job[1], job[2], self.bw, self.bh)
            bank.ridge(job[1], job[2], self.bw, self.bh)
            bank.fog(job[1], self.bw, self.bh)
        elif job[0] == "dsky":
            bank.skyline(job[1], job[2], self.bw, self.bh)
            bank.ridge_dl(job[1], job[2], self.bw, self.bh)
            if job[2] == 0:
                bank.fog(job[1], self.bw, self.bh)
        else:
            bank.aura(job[1], ARENAS[job[1]], job[2])
