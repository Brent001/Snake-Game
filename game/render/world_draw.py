"""World rendering: camera helpers, master draw(), floor, sky, decor, walls, doors, nodes and pickups."""
import math
import tkinter as tk

from ..config import (C_BOARD, C_CYAN, C_GOLD, C_GOLD_DIM, C_MINT, C_MINT_DIM, C_ZONE_EDGE, CELL, EFFECT_TIME,
    GRID_H, GRID_W)
from ..data.elements import ECOL
from ..utils import mix
from ..systems.menu import FULL_MENUS
from ..world.layout import ARENAS, CORE, arena_at
from ..data.bosses import BOSSES
from .scenery import AURA_COL
from ..config import NUM_FRAGMENTS, WORLD_H
from ..world.level import BMAP, SAVE_CELLS
from .world_draw_consts import RENDER_WALLS      # noqa: F401  (kept importable from here)
from ..data.biomes import STYLES



class WorldRenderMixin:
    def pulse(self, rate=3.0):
        return (math.sin(self.time * rate) + 1) / 2

    def px(self, x):
        return (x - self.cam_x) * CELL

    def py(self, y):
        return (y - self.cam_y) * CELL

    def visible(self, x, y):
        return self.cam_x - 1 <= x <= self.cam_x + self.vw and self.cam_y - 1 <= y <= self.cam_y + self.vh

    def center(self, x, y):
        return self.px(x) + CELL / 2, self.py(y) + CELL / 2

    def draw(self):
        c = self.canvas
        prev_state = getattr(self, "_last_draw_state", None)
        if self.state == "tree":
            # Tree screens are retained between frames; only their small dynamic
            # overlays are refreshed.  Entering the tree from another screen clears
            # the old scene once.
            if prev_state != "tree":
                c.delete("all")
                self._tree_canvas_ready = False
                self._skill_tree_static_key = None
                self._passive_tree_static_key = None
            self._last_draw_state = self.state
            self._ret = {}
        elif prev_state == "tree":
            c.delete("all")
            self._tree_canvas_ready = False
            self._skill_tree_static_key = None
            self._passive_tree_static_key = None
        if self.state in FULL_MENUS:
            c.delete("all")
            self._ret = {}
        elif self.state != "tree":
            c.delete("!keep")                      # retained HUD pieces (tag "keep") survive from frame to frame
        for name, cap in (("_ptext_cache", 500), ("_pix_img_cache", 120), ("_body_cache", 300), ("_scan_cache", 24), ("_bg_cache", 8), ("_sky_cache", 500), ("_glow_cache", 400), ("_shadow_cache", 60)):
            cache = self.__dict__.get(name)
            if cache is not None and len(cache) > cap:      # dropped between frames, so no live item loses its image
                cache.clear()
        self.menu_rects = []
        if self.state in FULL_MENUS:
            self.draw_menu_screen()
            self._last_draw_state = self.state
            return
        if self.state == "tree":
            self.draw_tree()
            self._last_draw_state = self.state
            return
        cx_ = int(min(GRID_W - 1, max(0, self.cam_x + self.vw / 2)))
        cy_ = int(min(GRID_H - 1, max(0, self.cam_y + self.vh / 2)))
        cb = BMAP[cy_][cx_]

        self.bank.begin_frame()
        hx_, hy_ = self.snake[0]
        dungeon = arena_at(hx_, hy_) is not None
        self.in_dungeon = dungeon
        if dungeon:                                   # boss dungeon: an indoor room, no sky / outdoor decor
            c.create_rectangle(0, 0, self.bw, self.bh, fill="#05060c", outline="")
            self.draw_arena()
            self.draw_boss_arena_vfx()
        else:
            self.begin_terrain()
            self.draw_floor()
            self.draw_tint()                                  # biome-transition belts (dithered floor blend)
            ox = -(self.cam_x % 1) * CELL
            oy = -(self.cam_y % 1) * CELL
            c.create_image(ox, oy, image=self.grid_image(self.pal[cb]["grid"]), anchor="nw")   # 1 item instead of ~55 lines
            self.draw_horizon(cb)
            self.draw_ground_decor()
            self.draw_portals()
            self.draw_ambience(cb)

        if not dungeon:
            self.draw_walls()
        self.draw_doors()
        vx0, vy0, vx1, vy1 = self.cam_x - 1, self.cam_y - 1, self.cam_x + self.vw, self.cam_y + self.vh
        node_img = self.bank.node(int(self.time * 12 / 1.3))          # 12 pre-rotated frames, one image per hazard
        for x, y in self.nodes.near(vx0, vy0, vx1, vy1):
            c.create_image(self.px(x) + CELL / 2, self.py(y) + CELL / 2, image=node_img)
        for (x, y), kind in self.pickups.near(vx0, vy0, vx1, vy1):
            self.draw_pickup(x, y, kind)
        for (x, y), kind in self.foods.near(vx0, vy0, vx1, vy1):
            self.draw_food(x, y, kind)
        for cell in SAVE_CELLS:
            if self.visible(*cell):
                self.draw_save(cell)
        for x, y in self.remaining:
            if self.visible(x, y):
                self.draw_fragment(x, y)
        for x, y in self.charges.near(vx0, vy0, vx1, vy1):
            self.draw_charge(x, y)
        self.draw_core()
        self.draw_decoy()
        self.draw_cores()
        self.draw_skill_zones()
        ex0, ex1, ey0, ey1 = self.cam_x - 1, self.cam_x + self.vw, self.cam_y - 1, self.cam_y + self.vh
        for e in self.active_enemies():
            if ex0 <= e["x"] <= ex1 and ey0 <= e["y"] <= ey1 and (not e["dead"] or e.get("death_t", 0.0) > 0):
                self.draw_enemy(e)
        self.draw_boss_mechanics()
        self.draw_boss_skills()
        self.draw_boss()
        self.draw_boss_power_vfx()
        self.draw_snake()
        for shot in self.shots:
            self.draw_shot(shot)
        self.draw_bullets()
        self.draw_vfx()
        for x, y, t0, kind, *extra in self.effects:
            t = (self.time - t0) / EFFECT_TIME
            if t >= 0:
                payload = extra[0] if extra else None
                # Effects are data-driven and some older boss attacks used a compact
                # payload. Keep rendering tolerant so one malformed effect can never
                # take down the Tkinter animation callback.
                self.draw_effect(x, y, t, kind, payload)
        self.draw_floats()
        self.draw_scent()
        self.draw_grade(cb)
        self.draw_vignette(cb)
        if not dungeon:
            self.prefetch_terrain()
        self.draw_boss_ui()
        self.draw_cast_banner()
        self.draw_biome_transition()
        self.draw_portal_transition()
        self.draw_biome_banner()
        self.draw_hurt_flash()
        self.draw_hud()
        self.draw_hotbar()
        self.draw_crosshair()
        self.draw_clock()
        if self.show_minimap:
            self.draw_minimap()
        self.draw_overlay()
        self._last_draw_state = self.state

    def draw_portal_transition(self):
        pf = getattr(self, "portal_fx", None)
        if not pf or not pf.get("active"):
            return
        c = self.canvas
        t = max(0.0, min(1.0, pf.get("t", 0.0) / max(0.01, pf.get("dur", 1.0))))
        ease = t * t * (3 - 2 * t)
        col = pf.get("color", C_CYAN)
        cx, cy = self.bw * 0.5, self.bh * 0.54
        # Tunnel overlay keeps the actual world visible while the snake travels through a portal.
        alpha_steps = 4
        for k in range(alpha_steps):
            q = (k + 1) / alpha_steps
            rr = (80 + 150 * q) * (0.70 + 0.30 * math.sin(t * math.pi))
            c.create_oval(cx-rr, cy-rr*0.62, cx+rr, cy+rr*0.62, outline=mix(col, "#050813", 0.35 + 0.11*k), width=max(1,int(2*q)))
        if pf.get("mode") == "enter":
            sx, sy = self.bw * 0.50, self.bh * 0.92
            ex, ey = cx, cy
        else:
            sx, sy = cx, cy
            ex, ey = self.bw * 0.50, self.bh * 0.10
        px = sx + (ex-sx)*ease
        py = sy + (ey-sy)*ease
        length = max(12, int(70 * (1.0 - 0.72*ease)))
        # Draw a small pixel-snake silhouette that stretches/compresses through the portal.
        for i in range(7):
            u = i / 6.0
            off = u * length
            yy = py + (off if pf.get("mode") == "enter" else -off)
            rad = max(2, int(7 * (1.0 - 0.55*ease) * (1.0-u*0.25)))
            c.create_oval(px-rad, yy-rad, px+rad, yy+rad, fill=mix(col, "#07101b", 0.35), outline=col, width=1)
        head_r = max(3, int(10 * (1.0 - 0.65*ease)))
        c.create_oval(px-head_r, py-head_r, px+head_r, py+head_r, fill="#07101b", outline="#ffffff", width=2)
        c.create_text(cx, cy + 105, text=("ENTERING " + pf.get("label", "PORTAL").upper()) if pf.get("mode") == "enter" else "RETURNING THROUGH PORTAL", fill="#dce9ff", font=("Segoe UI", 9, "bold"))
        # Vignette toward the portal center.
        c.create_rectangle(0,0,self.bw,self.bh, outline=mix(col,"#050813",0.80), width=max(1,int(3 + 2*math.sin(t*math.pi))))

    def draw_skill_zones(self):
        """Render persistent player-made hazard zones used by class-exclusive keystones."""
        c = self.canvas
        for z in getattr(self, "skill_zones", []):
            if not self.visible(z["x"], z["y"]):
                continue
            cx, cy = self.center(z["x"], z["y"])
            phase = self.time * 3.2 + z["x"] * 0.7 + z["y"] * 0.35
            pulse = 0.88 + 0.12 * math.sin(phase)
            r = z["r"] * CELL * pulse
            col = z.get("col", ECOL.get(z.get("el", "dendro"), C_CYAN))
            c.create_oval(cx-r, cy-r, cx+r, cy+r, outline=mix(col, "#05070f", 0.40), width=2)
            r2 = r * 0.72
            c.create_oval(cx-r2, cy-r2, cx+r2, cy+r2, outline=mix(col, "#05070f", 0.58), width=1, dash=(4, 4))
            for k in range(6):
                a = phase * 0.45 + k * math.pi / 3
                px, py = cx + math.cos(a) * r2, cy + math.sin(a) * r2
                c.create_rectangle(px-2, py-2, px+2, py+2, fill=col, outline="")

    def grid_image(self, color):
        """Grid lines baked into one transparent image (rebuilt only when the colour / window size changes)."""
        cols, rows = int(self.vw) + 2, int(self.vh) + 2
        cache = self.__dict__.setdefault("_grid_cache", {})
        key = (color, cols, rows)
        img = cache.get(key)
        if img is None:
            w, h = (cols - 1) * CELL + 1, (rows - 1) * CELL + 1
            img = tk.PhotoImage(master=self.canvas, width=w + CELL, height=h + CELL)
            for i in range(cols):
                img.put(color, to=(i * CELL, 0, i * CELL + 1, h + CELL))
            for j in range(rows):
                img.put(color, to=(0, j * CELL, w + CELL, j * CELL + 1))
            cache[key] = img
            while len(cache) > 4:
                cache.pop(next(iter(cache)))
        return img

    def draw_floor(self):
        c = self.canvas
        x0, y0 = int(math.floor(self.cam_x)), int(math.floor(self.cam_y))
        xs, xe = max(x0, 0), min(x0 + int(self.vw) + 1, GRID_W - 1)
        ya, yb = max(y0, 0), min(y0 + int(self.vh) + 2, GRID_H)
        key = (xs, xe, ya, yb)
        if self.__dict__.get("_floor_key") != key:
            # merge equal biome runs horizontally, then identical runs of consecutive rows vertically
            rects, active = [], {}
            for y in range(ya, yb):
                row = BMAP[y]
                runs = set()
                sx, cb = xs, row[xs]
                for x in range(xs + 1, xe + 2):
                    nb = row[x] if x <= xe else -1
                    if nb != cb:
                        runs.add((sx, x, cb))
                        sx, cb = x, nb
                for k in [k for k in active if k not in runs]:
                    rects.append((k[0], active.pop(k), k[1], y, k[2]))
                for k in runs:
                    active.setdefault(k, y)
            for k, ys_ in active.items():
                rects.append((k[0], ys_, k[1], yb, k[2]))
            self._floor_key, self._floor_rects = key, rects
        pal, cx, cy = self.pal, self.cam_x, self.cam_y
        for xa, ya_, xb, yb_, b in self._floor_rects:
            c.create_rectangle((xa - cx) * CELL, (ya_ - cy) * CELL, (xb - cx) * CELL + 1, (yb_ - cy) * CELL + 1,
                fill=pal[b]["floor"], outline="")

    def draw_boss_mechanics(self):
        b = self.boss
        if b.get("state") not in ("fight", "dying"):
            return
        c = self.canvas
        for hz in b.get("hazards", []):
            x, y = self.center(hz["x"], hz["y"])
            age, warn, life = hz["age"], hz["warn"], hz["life"]
            r = hz["r"] * CELL
            if hz["kind"] == "blast":
                active = age >= warn
                pulse = 1.0 + 0.08 * math.sin(self.time * 12)
                rr = r * pulse * (1.15 if active else 1.0)
                c.create_oval(x-rr, y-rr, x+rr, y+rr, outline="#ff536d" if active else "#ffb1bf", width=4 if active else 2, dash=() if active else (6,4))
                if not active:
                    c.create_text(x, y, text="!", fill="#ffeff3", font=("Segoe UI", 14, "bold"))
            elif hz["kind"] == "shard":
                active = age >= warn
                rr = r * (1.0 + min(age / max(warn, .1), 1.0) * 0.9)
                c.create_oval(x-rr, y-rr, x+rr, y+rr, outline="#d9f4ff" if not active else "#8fe8ff", width=2, dash=(4,3) if not active else ())
                if active:
                    c.create_polygon(x, y-12, x+5, y, x, y+12, x-5, y, fill="#bfeeff", outline="#ffffff")
            else:
                # Four rotating beams around the arena centre; only a narrow part is dangerous.
                a = hz.get("ang", 0.0) + self.time * 0.85
                length = b.get("mech_len", 9.0) * CELL
                width = 10
                c.create_line(x, y, x + math.cos(a)*length, y + math.sin(a)*length, fill="#ff6b82", width=width)
                c.create_line(x, y, x + math.cos(a+math.pi)*length, y + math.sin(a+math.pi)*length, fill="#ff6b82", width=width)
                c.create_oval(x-18, y-18, x+18, y+18, outline="#ffd0da", width=2)

    def draw_doors(self):
        c = self.canvas
        fill = mix("#3a120b", "#6a2212", self.pulse(2.0))
        for i, a in enumerate(ARENAS):
            cells = sorted(a["door"])
            if not self.visible(*cells[2]):
                continue
            if self.is_locked(cells[0]):
                for cell in cells:
                    px, py = self.px(cell[0]), self.py(cell[1])
                    c.create_rectangle(px, py, px + CELL, py + CELL, fill=fill, outline=C_ZONE_EDGE, width=2)
            else:                                                  # open exit: a shimmering return portal
                col = AURA_COL[i]
                x0, y0 = self.px(cells[0][0]), self.py(cells[0][1])
                w = CELL * len(cells)
                for k in range(4):
                    ph = (self.time * 0.8 + k * 0.25) % 1.0
                    c.create_line(x0 + 4, y0 + CELL * (1 - ph), x0 + w - 4, y0 + CELL * (1 - ph), fill=mix(col, "#05060c", ph), width=2)
                c.create_rectangle(x0, y0, x0 + w, y0 + CELL, outline=col, width=2)
                c.create_text(x0 + w / 2, y0 + CELL * 1.45, text="EXIT PORTAL", fill=col, font=("Segoe UI", 8, "bold"))

    def draw_portals(self):
        """Overworld gates into the boss dungeons: a rune circle on the ground, a swirling gate and a label."""
        c, t = self.canvas, self.time
        for i, a in enumerate(ARENAS):
            ox, oy = a["ow"]
            if not (self.cam_x - 5 <= ox <= self.cam_x + self.vw + 5 and self.cam_y - 5 <= oy <= self.cam_y + self.vh + 5):
                continue
            cx, cy = self.center(ox, oy)
            locked = a["final"] and self.collected < NUM_FRAGMENTS
            done = i in self.defeated
            col = "#7a7f94" if locked else ("#6fe3a8" if done else AURA_COL[i])
            dark = "#05060c"
            R = CELL * 2.7
            c.create_oval(cx - R, cy - R * 0.62 + 10, cx + R, cy + R * 0.62 + 10, fill=dark, outline="", stipple="gray50")
            c.create_oval(cx - R, cy - R * 0.62 + 10, cx + R, cy + R * 0.62 + 10, outline=col, width=2, dash=(10, 6), dashoffset=int(t * 14))
            c.create_oval(cx - R * 0.74, cy - R * 0.46 + 10, cx + R * 0.74, cy + R * 0.46 + 10, outline=col, width=1, dash=(3, 7), dashoffset=-int(t * 10))
            rx, ry = CELL * 1.35, CELL * 1.85
            pul = 1 + 0.05 * math.sin(t * 3 + i)
            c.create_oval(cx - rx * pul - 5, cy - ry * pul - 5, cx + rx * pul + 5, cy + ry * pul + 5, fill=dark, outline=col, width=3)
            for k in range(5):
                f = 1 - k * 0.19
                c.create_oval(cx - rx * f * pul, cy - ry * f * pul, cx + rx * f * pul, cy + ry * f * pul,
                    fill=mix(col, dark, 0.25 + 0.16 * k) if not locked else mix(col, dark, 0.55 + 0.1 * k), outline="")
            if not locked:
                for k in range(3):
                    st = (t * 140 + k * 120) % 360
                    ff = 0.85 - k * 0.22
                    c.create_arc(cx - rx * ff, cy - ry * ff, cx + rx * ff, cy + ry * ff, start=st, extent=110, style="arc",
                        outline=mix(col, "#ffffff", 0.45), width=3)
                for k in range(8):                                  # motes drifting up into the gate
                    ph = (t * 0.5 + k / 8) % 1.0
                    mx = cx + math.sin(k * 2.4 + t) * rx * 0.9 * (1 - ph)
                    my = cy + ry * 0.9 - ph * ry * 1.8
                    c.create_rectangle(mx - 2, my - 2, mx + 2, my + 2, fill=mix("#ffffff", col, ph), outline="")
            else:
                c.create_line(cx - rx, cy - ry * 0.6, cx + rx, cy + ry * 0.6, fill="#c0c4d6", width=4)
                c.create_line(cx - rx, cy + ry * 0.6, cx + rx, cy - ry * 0.6, fill="#c0c4d6", width=4)
            name = BOSSES[i]["name"].upper()
            label = f"SEALED - {NUM_FRAGMENTS} FRAGMENTS NEEDED" if locked else (name + "  -  CLEARED" if done else name + "'S DUNGEON")
            c.create_text(cx + 1, cy - ry - 16 + 1, text=label, fill=dark, font=("Segoe UI", 9, "bold"))
            c.create_text(cx, cy - ry - 16, text=label, fill="#ffffff" if not locked else "#c0c4d6", font=("Segoe UI", 9, "bold"))

    def draw_food(self, x, y, kind):
        c = self.canvas
        cx, cy = self.center(x, y)
        gold = kind == "gold"
        bob = math.sin(self.time * 3 + x * 0.7 + y * 0.3) * 2
        c.create_oval(cx - 9, cy + 9, cx + 9, cy + 14, fill=mix(self.pal[self.cur_biome]["floor"], "#000000", 0.45), outline="")
        c.create_oval(cx - 15, cy - 15 + bob, cx + 15, cy + 15 + bob, outline=mix(self.pal[self.cur_biome]["floor"], "#ffd34d" if gold else "#ff4d6d", 0.35), width=2)
        self.draw_sprite("food_gold" if gold else "food", cx, cy + bob - 1, 2.7 if gold else 2.3)
        if gold and int(self.time * 4 + x) % 3 == 0:
            c.create_rectangle(cx + 8, cy - 14 + bob, cx + 11, cy - 11 + bob, fill="#ffffff", outline="")

    def draw_node(self, x, y):
        c = self.canvas
        cx, cy = self.center(x, y)
        r_out, r_in = CELL * 0.46, CELL * 0.27
        pts = []
        for i in range(16):
            ang = math.pi * 2 * i / 16 - math.pi / 2 + self.time * 0.6
            r = r_out if i % 2 == 0 else r_in
            pts += [cx + r * math.cos(ang), cy + r * math.sin(ang)]
        c.create_polygon(pts, fill="#8f0f33", outline="#ff4f7d", width=2)
        r = CELL * 0.15
        c.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#ffc2d2", width=2)
        c.create_oval(cx - 2, cy - 2, cx + 2, cy + 2, fill="#ffc2d2", outline="")

    def draw_fragment(self, x, y):
        c = self.canvas
        cx, cy = self.center(x, y)
        r = CELL * (0.28 + 0.06 * self.pulse(5))
        c.create_oval(cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3, outline=C_GOLD_DIM, width=5)
        c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=C_GOLD, width=2)
        c.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, fill=C_GOLD, outline="")

    def draw_charge(self, x, y):
        c = self.canvas
        cx, cy = self.center(x, y)
        r = CELL * (0.34 + 0.04 * self.pulse(6))
        hexa = []
        for i in range(6):
            ang = math.pi / 3 * i
            hexa += [cx + r * math.cos(ang), cy + r * math.sin(ang)]
        c.create_polygon(hexa, fill="", outline=C_MINT_DIM, width=6)
        c.create_polygon(hexa, fill="#0b2a22", outline=C_MINT, width=2)
        bolt = [(-0.06, -0.24), (0.12, -0.02), (0.02, -0.02), (0.07, 0.24), (-0.12, 0.0), (-0.02, 0.0)]
        c.create_polygon([v for bx, by in bolt for v in (cx + bx * CELL, cy + by * CELL)], fill=C_MINT, outline="")

    def draw_pickup(self, x, y, kind):
        c = self.canvas
        cx, cy = self.center(x, y)
        bob = math.sin(self.time * 3 + x) * 2
        cy += bob
        if kind == "heal":
            for n in range(5):
                a = n * 2 * math.pi / 5 + self.time
                c.create_oval(cx + 6 * math.cos(a) - 4, cy + 6 * math.sin(a) - 4, cx + 6 * math.cos(a) + 4, cy + 6 * math.sin(a) + 4,
                    fill="#ff9ac8", outline="")
            c.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, fill="#ffe08a", outline="")
        elif kind == "xp":
            w = 6 + 4 * math.sin(self.time * 12 + x)
            c.create_polygon(cx, cy, cx - w, cy - 7, cx - w, cy + 5, fill="#7df9ff", outline="")
            c.create_polygon(cx, cy, cx + w, cy - 7, cx + w, cy + 5, fill="#ffb3d1", outline="")
        elif kind == "stam":
            c.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, fill="#0e3a44", outline=C_CYAN, width=2)
            c.create_oval(cx - 2, cy - 2, cx + 2, cy + 2, fill=C_CYAN, outline="")
        elif kind == "dmg":
            c.create_polygon(cx, cy - 9, cx + 7, cy, cx, cy + 9, cx - 7, cy, fill="#6a0f20", outline="#ff5d6c", width=2)
        elif kind == "speed":
            c.create_line(cx - 7, cy - 6, cx, cy, cx - 7, cy + 6, fill="#6fffd0", width=3)
            c.create_line(cx, cy - 6, cx + 7, cy, cx, cy + 6, fill="#6fffd0", width=3)
        elif kind == "shield":
            hexa = []
            for i in range(6):
                a = math.pi / 3 * i + math.pi / 6
                hexa += [cx + 9 * math.cos(a), cy + 9 * math.sin(a)]
            c.create_polygon(hexa, fill="#4a3a0a", outline=C_GOLD, width=2)
        elif kind == "regen":
            c.create_rectangle(cx - 2.5, cy - 8, cx + 2.5, cy + 8, fill=C_MINT, outline="")
            c.create_rectangle(cx - 8, cy - 2.5, cx + 8, cy + 2.5, fill=C_MINT, outline="")
            c.create_oval(cx - 10, cy - 10, cx + 10, cy + 10, outline=C_MINT_DIM, width=2)
        elif kind == "crit":
            c.create_polygon(cx, cy - 10, cx + 3, cy - 3, cx + 10, cy, cx + 3, cy + 3, cx, cy + 10, cx - 3, cy + 3,
                cx - 10, cy, cx - 3, cy - 3, fill="#5a3a0a", outline=C_GOLD, width=2)
        elif kind == "elixir":
            c.create_oval(cx - 7, cy - 3, cx + 7, cy + 9, fill="#7a2a8a", outline="#e0a0ff", width=2)
            c.create_rectangle(cx - 2.5, cy - 9, cx + 2.5, cy - 2, fill="#e0a0ff", outline="")
        elif kind == "ammo":
            hexa = []
            for i in range(6):
                a = math.pi / 3 * i
                hexa += [cx + 8 * math.cos(a), cy + 8 * math.sin(a)]
            c.create_polygon(hexa, fill="#0b2a22", outline=C_MINT, width=2)
            c.create_text(cx, cy, text="+6", fill=C_MINT, font=("Segoe UI", 7, "bold"))
        elif kind == "emorb":
            r = 7 + 1.5 * math.sin(self.time * 5)
            c.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#2a1a4a", outline=ECOL["electro"], width=2)
            for n in range(3):
                a = self.time * 3 + n * 2.1
                c.create_oval(cx + 11 * math.cos(a) - 2, cy + 11 * math.sin(a) - 2, cx + 11 * math.cos(a) + 2,
                    cy + 11 * math.sin(a) + 2, fill=ECOL["anemo"], outline="")
        else:
            col = ECOL[kind[3:]]
            r = 11 + 2 * math.sin(self.time * 4)
            c.create_oval(cx - r - 4, cy - r - 4, cx + r + 4, cy + r + 4, outline=mix(col, "#05080f", 0.6), width=3)
            pts = []
            for i in range(8):
                a = i * math.pi / 4 - math.pi / 2
                rr = r if i % 2 == 0 else r * 0.4
                pts += [cx + rr * math.cos(a), cy + rr * math.sin(a)]
            c.create_polygon(pts, fill=col, outline="#ffffff")

    def draw_cores(self):
        c = self.canvas
        for x, y, t in self.cores:
            if not self.visible(x, y):
                continue
            cx, cy = self.center(x, y)
            r = CELL * (0.22 + 0.05 * self.pulse(8))
            warn = t < 2.0 and int(self.time * 10) % 2 == 0
            c.create_oval(cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3, outline=mix(ECOL["dendro"], C_BOARD, 0.6), width=3)
            c.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#ffffff" if warn else ECOL["dendro"], outline="#d8ff9a", width=2)
        for x, y, _dmg, _life in self.missiles:
            if not self.visible(x, y):
                continue
            cx, cy = self.center(x, y)
            c.create_oval(cx - 8, cy - 8, cx + 8, cy + 8, outline=mix(ECOL["electro"], C_BOARD, 0.5), width=3)
            c.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill=ECOL["dendro"], outline="#ffffff")

    def draw_save(self, cell):
        c = self.canvas
        cx, cy = self.center(*cell)
        seen = cell in self.visited_saves
        col = "#fff1a0" if seen else "#d8b840"
        r = 12 + 3 * math.sin(self.time * 4)
        c.create_oval(cx - r - 6, cy - r - 6, cx + r + 6, cy + r + 6, outline=mix(col, "#05080f", 0.75), width=3)
        pts = []
        for i in range(8):
            a = i * math.pi / 4 - math.pi / 2
            rr = r if i % 2 == 0 else r * 0.28
            pts += [cx + rr * math.cos(a), cy + rr * math.sin(a)]
        c.create_polygon(pts, fill=col, outline="#ffffff")
        for k in range(3):
            a = self.time * 1.5 + k * 2.1
            c.create_rectangle(cx + 20 * math.cos(a) - 1, cy + 14 * math.sin(a) - 1, cx + 20 * math.cos(a) + 1, cy + 14 * math.sin(a) + 1,
                fill="#ffffff", outline="")

    def draw_core(self):
        c = self.canvas
        if self.state == "won" or not self.visible(*CORE):
            return
        cx, cy = self.center(*CORE)
        if not self.boss_defeated:
            r = CELL * 0.3
            c.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#2a3f66", width=2, dash=(4, 3))
            return
        r = CELL * (0.34 + 0.07 * self.pulse(5.5))
        diamond = [cx, cy - r, cx + r, cy, cx, cy + r, cx - r, cy]
        c.create_polygon(diamond, fill="", outline="#1c5b66", width=6)
        c.create_polygon(diamond, fill="#0e3a44", outline=C_CYAN, width=2)
        c.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill=C_CYAN, outline="")

    def draw_decoy(self):
        if not self.decoy or not self.visible(self.decoy["x"], self.decoy["y"]):
            return
        c = self.canvas
        cx, cy = self.center(self.decoy["x"], self.decoy["y"])
        c.create_oval(cx - 11, cy - 11, cx + 11, cy + 11, outline="#7aa8c8", dash=(3, 3), width=2)
        c.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, outline="#a8d0e8")
