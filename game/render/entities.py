"""Entity rendering: 8-bit sprites, enemies, bosses, bullets, player shots, effects and the snake itself."""
import math
import tkinter as tk
from pathlib import Path

from ..config import (C_BOARD, C_GOLD, C_CYAN, CELL, HEAD_HIT, NUM_FRAGMENTS, SNAKE_BODY, SNAKE_CORE,
    SNAKE_EDGE_HI, SNAKE_EDGE_LO, SNAKE_GLOW_HI, SNAKE_GLOW_LO)
from ..data.bosses import BOSSES
from ..data.elements import ECOL
from ..data.enemies import ENEMY_TYPES, UNIQUE_NAMES
from ..data.sprites import SPRITE_RUNS
from ..utils import mix, rounded_rect
from ..world.layout import ARENAS

_ENEMY_ANIM_DIR = Path(__file__).resolve().parents[1] / "assets" / "enemy_anim"

HEAD_SHAPE = [
    (0.54, 0.0), (0.12, -0.17), (0.20, -0.40), (-0.04, -0.30), (-0.16, -0.46),
    (-0.27, -0.20), (-0.12, 0.0), (-0.27, 0.20), (-0.16, 0.46), (-0.04, 0.30),
    (0.20, 0.40), (0.12, 0.17),
]


class EntityRenderMixin:
    def shadow_image(self, w, h, stipple):
        """Stepped pixel-art contact shadow baked once into a PhotoImage (was a stippled polygon + 3 stippled rects
        per enemy per frame; stippled items are slow in the Windows canvas)."""
        cache = self.__dict__.setdefault("_shadow_cache", {})
        key = (int(round(w)), int(round(h)), stipple)
        img = cache.get(key)
        if img is None:
            wi, hi = key[0], key[1]
            ox, oy = int(wi * 0.72) + 2, hi + 2
            img = tk.PhotoImage(master=self.canvas, width=ox * 2 + 1, height=oy * 2 + 1)
            col = "#171521"
            half = (lambda x, y: (x + y) & 1 == 0) if stipple == "gray50" else (lambda x, y: x % 2 == 0 and y % 2 == 0)
            rx, ry = max(1.0, wi * 0.72), max(1.0, hi * 0.80)
            for j in range(-oy, oy + 1):
                for i in range(-ox, ox + 1):
                    inside = (i / rx) ** 2 + (j / ry) ** 2 <= 1.0
                    if inside and half(i, j):
                        img.put(col, to=(i + ox, j + oy, i + ox + 1, j + oy + 1))
            cache[key] = img
        return img

    def draw_pixel_shadow(self, cx, cy, w=10, h=4, stipple="gray50"):
        """Stepped pixel-art contact shadow; intentionally static and not a lighting system."""
        self.canvas.create_image(cx, cy, image=self.shadow_image(w, h, stipple))

    # ---- 8-bit characters
    def sprite_image(self, name, scale, flash, dim):
        """Each 8-bit sprite is rasterised once into a PhotoImage, so drawing it costs 1 canvas item instead of ~20."""
        cache = self.__dict__.setdefault("_sprite_cache", {})
        key = (name, scale, flash, dim)
        img = cache.get(key)
        if img is None:
            runs, n = SPRITE_RUNS[name]
            size = max(1, int(round(n * scale)))
            img = tk.PhotoImage(master=self.canvas, width=size, height=size)
            for x, y, w, col in runs:
                f = "#ffffff" if flash else (mix(col, "#05080f", dim) if dim else col)
                x1, y1 = int(round(x * scale)), int(round(y * scale))
                img.put(f, to=(x1, y1, max(x1 + 1, int(round((x + w) * scale))), max(y1 + 1, int(round((y + 1) * scale)))))
            cache[key] = img
        return img

    def draw_sprite(self, name, cx, cy, scale, flash=False, dim=0.0):
        self.canvas.create_image(cx, cy, image=self.sprite_image(name, scale, flash, dim))

    def touhou_boss_image(self, name, scale, dim=0.0):
        """Load the supplied 16x16 Touhou sprite and scale it with nearest-neighbour pixels."""
        cache = self.__dict__.setdefault("_touhou_boss_cache", {})
        key = (name, scale, dim)
        if key in cache:
            return cache[key]
        path = Path(__file__).resolve().parents[1] / "assets" / "touhou" / f"{name}.png"
        if not path.exists():
            return None
        img = tk.PhotoImage(master=self.canvas, file=str(path))
        if scale > 1:
            img = img.zoom(scale, scale)
        cache[key] = img
        return img

    # ---- animated boss sprites (Touhou Pixel Characters by Code-Farmer, 64x64 cells, 4 columns x 24 rows)
    # Row blocks (4 rows each, order up / down / left / right): idle 2f, walk 4f, swing 2f, charge 1f, ready 2f, down 1f.
    BOSS_ANIM = {"idle": (0, 2, 5.0), "walk": (4, 4, 11.0), "swing": (8, 2, 10.0), "charge": (12, 1, 1.0),
                 "ready": (16, 2, 7.0), "down": (20, 1, 1.0)}
    BOSS_DIR = {"up": 0, "down": 1, "left": 2, "right": 3}

    def boss_sheet(self, name):
        cache = self.__dict__.setdefault("_boss_sheets", {})
        if name not in cache:
            path = Path(__file__).resolve().parents[1] / "assets" / "bosses" / f"{name}.png"
            cache[name] = tk.PhotoImage(master=self.canvas, file=str(path)) if path.exists() else None
        return cache[name]

    def boss_frame(self, name, anim, direction, t, scale):
        """One animation frame cut from the sheet and nearest-neighbour zoomed (cached per name/anim/dir/frame/scale)."""
        sheet = self.boss_sheet(name)
        if sheet is None:
            return None
        row0, frames, fps = self.BOSS_ANIM[anim]
        f = int(t * fps) % frames
        key = (name, anim, direction, f, scale)
        cache = self.__dict__.setdefault("_boss_frames", {})
        img = cache.get(key)
        if img is None:
            r = row0 + self.BOSS_DIR[direction]
            x0, y0 = f * 64 + 4, r * 64 + 4
            img = tk.PhotoImage(master=self.canvas)
            img.tk.call(img, "copy", sheet, "-from", x0, y0, x0 + 56, y0 + 56, "-zoom", scale, scale)
            cache[key] = img
        return img

    def boss_pose(self, i, b, active, bx, by):
        """Choose (anim, direction) from what the boss is actually doing, so the sprite follows the fight."""
        mem = self.__dict__.setdefault("_boss_mem", {})
        m = mem.get(i)
        now = self.time
        if m is None or now - m["t"] > 0.5:
            m = mem[i] = dict(x=bx, y=by, t=now, face="down", move_t=-9.0)
        dt = now - m["t"]
        if dt > 0:
            vx, vy = (bx - m["x"]) / dt, (by - m["y"]) / dt
            if vx * vx + vy * vy > 0.35 and dt < 0.2:
                m["move_t"] = now
                m["face"] = ("right" if vx > 0 else "left") if abs(vx) > abs(vy) else ("down" if vy > 0 else "up")
            m["x"], m["y"], m["t"] = bx, by, now
        if not active:
            return "idle", "down"
        st = b.get("state")
        if st == "dying":
            return "down", "down"
        # face the player while standing or casting
        hx, hy = self.snake_points()[0]
        dx, dy = hx - bx, hy - by
        to_player = ("right" if dx > 0 else "left") if abs(dx) > abs(dy) else ("down" if dy > 0 else "up")
        cast = b.get("cast")
        casting_now = cast is not None and now - cast[2] < 0.5
        mv = b.get("move")
        if mv is not None and mv.get("t", 9.0) < mv.get("warn", 0.0):
            return "charge", to_player                      # telegraph of a dash / warp / kiss
        if mv is not None or now - m["move_t"] < 0.15:
            return ("swing" if casting_now else "walk"), (m["face"] if mv is None else to_player if mv.get("k") != "dash" else m["face"])
        if casting_now:
            return "swing", to_player
        if b.get("hold") or b.get("sk"):
            return "ready", to_player                       # channelling a beam / maintaining a skill
        return "idle", to_player

    def draw_touhou_boss_sprite(self, name, cx, cy, scale=4, flash=False, dim=0.0, anim="idle", direction="down", t=None):
        t = self.time if t is None else t
        img = self.boss_frame(name, anim, direction, t, max(1, scale // 2))
        if img is None:
            img = self.touhou_boss_image(name, scale, dim)
        if img is None:
            self.draw_sprite(name, cx, cy, scale, flash=flash, dim=dim)
            return
        self.canvas.create_image(cx, cy, image=img)
        if flash:
            r = max(img.width(), img.height()) * 0.42
            self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#ffffff", width=3)

    # ---- snake body segment: rasterised once per colour variant (was 4 canvas items incl. 2 smoothed splines)
    def body_tile(self, edge, glow, core, armor):
        cache = self.__dict__.setdefault("_body_cache", {})
        key = (edge, glow, core, armor, CELL)
        img = cache.get(key)
        if img is not None:
            return img
        T = CELL
        half = T / 2
        img = tk.PhotoImage(master=self.canvas, width=T, height=T)

        def rbox(px, py, hx, hy, r):
            qx, qy = abs(px) - hx + r, abs(py) - hy + r
            return math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0) - r

        for j in range(T):
            py = j + 0.5 - half
            run_col, run_x = None, 0
            for i in range(T + 1):
                col = None
                if i < T:
                    px = i + 0.5 - half
                    d = rbox(px, py, half - 4, half - 4, 5)
                    if abs(d) <= 1.0:
                        col = edge
                    elif d < 0:
                        col = SNAKE_BODY
                    elif d <= 3.5:
                        col = glow
                    if abs(rbox(px, py, 4.5, 4.5, 2)) <= 0.5 or px * px + py * py <= 3.24:
                        col = core
                    if armor:
                        if max(abs(px), abs(py)) <= 10.5 and max(abs(px), abs(py)) >= 9.5:
                            col = edge
                        elif abs(py) <= 0.5 and abs(px) <= 10:
                            col = glow
                if col != run_col:
                    if run_col is not None:
                        img.put(run_col, to=(run_x, j, i, j + 1))
                    run_col, run_x = col, i
        cache[key] = img
        return img


    def enemy_anim_frame(self, name, frame, scale, flash=False):
        """4-frame squash/stretch strip made from the existing 8-bit enemy art."""
        cache = self.__dict__.setdefault("_enemy_anim_sheets", {})
        sheet = cache.get(name, False)
        if sheet is False:                                  # looked up once per sprite name (was a Path.resolve() every call)
            path = _ENEMY_ANIM_DIR / f"{name}.png"
            sheet = tk.PhotoImage(master=self.canvas, file=str(path)) if path.exists() else None
            cache[name] = sheet
        if sheet is None:
            return self.sprite_image(name, scale, flash, 0.0)
        key=(name,int(frame)%4,round(scale,2),bool(flash))
        fcache=self.__dict__.setdefault("_enemy_anim_frames", {})
        if key in fcache:
            return fcache[key]
        # Keep the transparent border so the squash/stretch motion does not clip.
        img=tk.PhotoImage(master=self.canvas)
        z=max(1,int(round(scale)))
        x0=(int(frame)%4)*16
        img.tk.call(img, "copy", sheet, "-from", x0, 0, x0+16, 16, "-zoom", z, z)
        if flash:
            # Flashing is communicated by the existing canvas outline; keep this frame crisp.
            pass
        fcache[key]=img
        return img

    def draw_enemy_animated(self, name, cx, cy, scale, frame, flash=False):
        img=self.enemy_anim_frame(name, frame, scale, flash)
        self.canvas.create_image(cx, cy, image=img)

    def draw_enemy(self, e):
        c = self.canvas
        info = ENEMY_TYPES[e["t"]]
        cx, cy = self.center(e["x"], e["y"])
        scale = 5 if e["elite"] == 2 else 4 if e["elite"] else 3
        self.draw_pixel_shadow(cx, cy + 5, max(7, int(7 * scale)), max(2, int(2.5 * scale)))
        anim_frame = int((self.time * 7 + e.get("anim_t", 0.0)) % 4)
        bob = math.sin(self.time * 4.2 + e["x"] * 0.7 + e.get("anim_t", 0.0)) * 2.5
        pulse_scale = scale
        if e.get("dead") and e.get("death_t", 0.0) > 0:
            p = max(0.0, min(1.0, e["death_t"] / 0.62))
            rr = (1.0 - p) * CELL * (0.9 + 0.4 * e["elite"])
            if rr > 1:
                c.create_oval(cx-rr, cy+ bob-rr, cx+rr, cy+bob+rr, outline=mix(info["col"], "#ffffff", p), width=max(1, int(3*p+1)))
            for k in range(5):
                a = self.time * 5 + k * math.pi * 2 / 5
                d = CELL * (1.0-p) * (0.5 + k*.15)
                c.create_rectangle(cx+math.cos(a)*d-2, cy+bob+math.sin(a)*d-2, cx+math.cos(a)*d+2, cy+bob+math.sin(a)*d+2, fill=info["col"], outline="")
            return
        if self.heat_t > 0:
            rr = 8 * scale
            c.create_oval(cx - rr, cy - rr + bob, cx + rr, cy + rr + bob, outline="#ff9a3a", width=2)
        if e.get("shield", 0.0) > 0:
            rr = 9 * pulse_scale
            c.create_oval(cx - rr, cy - rr + bob, cx + rr, cy + rr + bob, outline="#7df9ff", width=2, dash=(4, 3))
            c.create_arc(cx - rr, cy - rr + bob, cx + rr, cy + rr + bob, start=-60, extent=210, outline="#ffffff", width=2)
        if e["st"] == "hidden" and e["elite"] < 2:
            self.draw_enemy_animated(info["sprite"], cx, cy + bob, max(2, int(pulse_scale)), anim_frame)
            return
        if e["elite"] == 2:                         # unique champions glow
            rr = 9 * scale
            c.create_oval(cx - rr, cy - rr + bob, cx + rr, cy + rr + bob, outline=mix(C_GOLD, C_BOARD, 0.5 - 0.3 * self.pulse(4)), width=3)
        if e["st"] == "aim" and info["ai"] == "sniper":
            c.create_line(cx, cy, cx + math.cos(e["ang"]) * CELL * 12, cy + math.sin(e["ang"]) * CELL * 12, fill="#ff5d6c", dash=(4, 4))
        self.draw_enemy_animated(info["sprite"], cx, cy + bob, pulse_scale, anim_frame,
            flash=e["flash"] > 0 or (info["ai"] in ("bomber", "ambush") and e["st"] in ("wind", "hidden") and int(self.time * 12) % 2 == 0))
        top = cy + bob - 7 * scale
        if e["elite"] == 2:
            c.create_text(cx, top - 16, text="UNIQUE  " + UNIQUE_NAMES[e["t"]].upper(), fill=C_GOLD, font=("Segoe UI", 8, "bold"))
        elif e["elite"]:
            c.create_text(cx, top - 14, text="ELITE", fill=C_GOLD, font=("Segoe UI", 7, "bold"))
        if e["hp"] < e["maxhp"] or self.heat_t > 0 or e["elite"] == 2:
            w = 8 * scale
            c.create_rectangle(cx - w, top - 6, cx + w, top - 2, fill="#05080f", outline="")
            c.create_rectangle(cx - w, top - 6, cx - w + 2 * w * max(0.0, e["hp"] / e["maxhp"]), top - 2, fill="#ff5d6c", outline="")
        if e["aura"]:
            aura_col = ECOL.get(e["aura"], "#ffffff")
            c.create_oval(cx + 6 * scale - 5, top - 5, cx + 6 * scale + 5, top + 5, fill=aura_col, outline="#ffffff")
            ar = (10 + 3 * math.sin(self.time * 7)) * scale / 3
            c.create_oval(cx-ar, cy+bob-ar, cx+ar, cy+bob+ar, outline=aura_col, width=1, dash=(2,5))
        if e["shred"] > 0:
            c.create_text(cx - 6 * scale, top, text="\u25bc", fill=ECOL["electro"], font=("Segoe UI", 8, "bold"))
        if e["freeze"] > 0:
            rr = 7 * scale
            c.create_rectangle(cx - rr, cy - rr, cx + rr, cy + rr, outline="#9fefff", width=3)
        if e["st"] == "wind":
            c.create_text(cx, top - 10, text="!", fill="#ff5d6c", font=("Segoe UI", 14, "bold"))
        elif e["st"] == "shield":
            c.create_text(cx, top - 10, text="SHIELD", fill="#7df9ff", font=("Segoe UI", 7, "bold"))

    def draw_boss(self):
        c = self.canvas
        b = self.boss
        for i, a in enumerate(ARENAS):
            if i in self.defeated and not (b.get("state") == "dying" and b.get("idx") == i):
                continue
            active = self.boss_active() and b["idx"] == i
            bx, by = (b["x"], b["y"]) if active else (a["mx"], a["y1"] + 3.2)
            if not self.visible(bx, by):
                continue
            locked = a["final"] and self.collected < NUM_FRAGMENTS
            col = BOSSES[i]["phases"][b["phase"]]["color"] if active else "#33466e"
            dim = lambda t: mix(col, "#05080f", t)
            cx, cy = self.center(bx, by)
            self.draw_pixel_shadow(cx, cy + CELL*1.9, int(CELL*1.65), int(CELL*0.42))
            spin = self.time * (0.6 if active else 0.15)
            # Larger, more imposing boss presentation inside the dungeon chamber.
            R = CELL * (3.0 if active else 2.5)
            c.create_oval(cx - R, cy - R, cx + R, cy + R, outline=dim(0.55), width=2, dash=(8, 6))
            c.create_oval(cx - R * 0.72, cy - R * 0.72, cx + R * 0.72, cy + R * 0.72,
                outline=dim(0.72), width=1, dash=(3, 9))
            for off, sgn in ((0, 1), (math.pi / 3, -1)):
                tri = []
                for k in range(3):
                    ang = sgn * spin + off + k * 2 * math.pi / 3
                    tri += [cx + R * 0.85 * math.cos(ang), cy + R * 0.85 * math.sin(ang)]
                c.create_polygon(tri, fill="", outline=dim(0.5), width=2)
            bob = math.sin(self.time * 3) * 3
            if b.get("state") == "dying" and b.get("idx") == i:
                dp = max(0.0, min(1.0, b.get("death_t", 0.0) / 1.45))
                spin *= 1.8
                cx += math.sin(self.time * 13) * (1.0-dp) * 7
                cy -= (1.0-dp) * CELL * 1.5
                for k in range(10):
                    ang = self.time * 2.5 + k * math.pi / 5
                    rr2 = CELL * (1.0 + (1.0-dp) * 3.0)
                    c.create_rectangle(cx+math.cos(ang)*rr2-3, cy+math.sin(ang)*rr2-3, cx+math.cos(ang)*rr2+3, cy+math.sin(ang)*rr2+3, fill=col, outline="")
                self.draw_touhou_boss_sprite(BOSSES[i]["sprite"], cx, cy, 6 + int((1.0-dp)*2), flash=True, dim=0.0, anim="down", direction="down")
                c.create_text(cx, cy + R + 18, text="SPELL CARD BREAK", fill="#ffffff", font=("Segoe UI", 11, "bold"))
                continue
            if active and b.get("hidden"):
                self.draw_boss_hidden(cx, cy)
                continue
            anim, face = self.boss_pose(i, b, active, bx, by)
            self.draw_touhou_boss_sprite(BOSSES[i]["sprite"], cx, cy + bob * 0.5, 6 if active else 5,
                flash=active and b["flash"] > 0, dim=0.0 if active else (0.8 if locked else 0.6),
                anim=anim, direction=face)
            if active:
                # Three orbiting spell sigils make the boss visually readable even in dense danmaku.
                for k in range(3):
                    ang = -spin * 1.6 + k * 2 * math.pi / 3
                    ox, oy = cx + CELL * 2.25 * math.cos(ang), cy + CELL * 2.25 * math.sin(ang)
                    sr = CELL * 0.18
                    c.create_oval(ox - sr, oy - sr, ox + sr, oy + sr, fill=col, outline="#ffffff", width=1)
                    c.create_line(ox - sr*1.5, oy, ox + sr*1.5, oy, fill=dim(0.25), width=1)
                c.create_text(cx, cy + R + 18, text=BOSSES[i]["name"], fill=col,
                    font=("Segoe UI", 11, "bold"))

    def draw_shot(self, s):
        """Directional elemental laser: long, crisp beam with a tapered pixel head.

        The player projectile is intentionally a laser again: no orb head, no circular
        projectile body. Depth comes from an offset pixel shadow and layered beam widths.
        """
        x, y, dx, dy = s["x"], s["y"], s["dx"], s["dy"]
        if not self.visible(x, y):
            return
        c = self.canvas
        el = s.get("el", "pulse")
        col = ECOL.get(el, C_CYAN)
        mag = max(0.001, math.hypot(dx, dy))
        ux, uy = dx / mag, dy / mag
        nx, ny = -uy, ux
        cx, cy = self.center(x, y)

        # Compact laser: short, blunt-ended, directional, and clearly beam-like.
        # Keep enough length to read as a laser without becoming a long projectile.
        length = CELL * 0.58
        tail = CELL * 0.16
        ex, ey = cx + ux * length, cy + uy * length
        tx, ty = cx - ux * tail, cy - uy * tail

        # Offset pixel shadow: depth without a black contour around the beam.
        sx0, sy0 = tx + nx * 2.0, ty + ny * 2.0
        sx1, sy1 = ex + nx * 2.0, ey + ny * 2.0
        shadow = mix(col, "#14151d", 0.82)
        c.create_line(sx0, sy0, sx1, sy1, fill=shadow, width=5, stipple="gray50")
        c.create_line(sx0, sy0, sx1, sy1, fill=shadow, width=2)

        # Normal soft glow, kept subtle so the laser silhouette remains crisp.
        c.create_line(tx, ty, ex, ey, fill=mix(col, "#ffffff", 0.05), width=8, stipple="gray25")
        c.create_line(tx, ty, ex, ey, fill=mix(col, "#ffffff", 0.16), width=5, stipple="gray50")

        # Stylized pixel '+' / 'x' accents along the beam.
        accent = mix(col, "#ffffff", 0.34)
        for q in (0.16, 0.62):
            px, py = cx + ux * length * q, cy + uy * length * q
            a = 2
            c.create_rectangle(px-a, py-1, px+a, py+1, fill=accent, outline="")
            c.create_rectangle(px-1, py-a, px+1, py+a, fill=accent, outline="")

        # Main laser body + white-hot center line.
        c.create_line(tx, ty, ex, ey, fill=col, width=4)
        c.create_line(cx - ux * (tail * 0.65), cy - uy * (tail * 0.65),
                      cx + ux * (length - 1), cy + uy * (length - 1),
                      fill=mix(col, "#ffffff", 0.70), width=2)
        c.create_line(cx - ux * (tail * 0.25), cy - uy * (tail * 0.25),
                      cx + ux * (length - 2), cy + uy * (length - 2),
                      fill="#ffffff", width=1)

        # Blunt end-cap: no arrow, spearhead, triangle, or orb.
        cap = 2.0
        c.create_line(ex - nx * cap, ey - ny * cap, ex + nx * cap, ey + ny * cap,
                      fill=mix(col, "#ffffff", 0.45), width=2)

        # Element identity is layered on top of the same laser silhouette.
        if el == "electro":
            for q, sg in ((0.25, 1), (0.62, -1), (0.84, 1)):
                px, py = cx + ux * length * q, cy + uy * length * q
                c.create_line(px + nx * 3 * sg, py + ny * 3 * sg,
                              px - ux * 4 + nx * 1 * sg, py - uy * 4 + ny * 1 * sg,
                              fill="#f4ffff", width=1)
        elif el == "pyro":
            px, py = cx + ux * (length * 0.75), cy + uy * (length * 0.75)
            c.create_polygon(px + ux * 5, py + uy * 5, px - ux * 1 + nx * 3, py - uy * 1 + ny * 3,
                             px - ux * 2, py - uy * 2, px - ux * 1 - nx * 2, py - uy * 1 - ny * 2,
                             fill="#fff0ae", outline="")
        elif el == "cryo":
            px, py = cx + ux * (length * 0.62), cy + uy * (length * 0.62)
            c.create_line(px - nx * 4, py - ny * 4, px + nx * 4, py + ny * 4, fill="#f4ffff", width=1)
            c.create_line(px - ux * 3, py - uy * 3, px + ux * 3, py + uy * 3, fill="#f4ffff", width=1)
        elif el == "hydro":
            px, py = cx + ux * (length * 0.58), cy + uy * (length * 0.58)
            c.create_arc(px-6, py-4, px+6, py+4, start=int(self.time*180), extent=135, outline="#eaffff", width=1)
        elif el == "dendro":
            px, py = cx + ux * (length * 0.66), cy + uy * (length * 0.66)
            c.create_polygon(px + ux*4, py + uy*4, px + nx*3, py + ny*3, px - ux*2, py - uy*2,
                             px - nx*2, py - ny*2, fill="#eaffbf", outline="")
        elif el == "anemo":
            px, py = cx + ux * (length * 0.53), cy + uy * (length * 0.53)
            c.create_arc(px-5, py-5, px+5, py+5, start=int(self.time*220), extent=125, outline="#f4ffff", width=1)
        elif el == "geo":
            px, py = cx + ux * (length * 0.68), cy + uy * (length * 0.68)
            c.create_polygon(px + ux*4, py + uy*4, px + nx*3, py + ny*3, px - ux*2, py - uy*2,
                             px - nx*3, py - ny*3, fill="#ffe9a8", outline="")
        elif el == "abyss":
            px, py = cx + ux * (length * 0.58), cy + uy * (length * 0.58)
            c.create_line(px-nx*3, py-ny*3, px+ux*2+nx, py+uy*2+ny, fill="#f0ddff", width=1)
            c.create_line(px+nx*3, py+ny*3, px+ux*2-nx, py+uy*2-ny, fill="#f0ddff", width=1)
        elif el == "light":
            px, py = cx + ux * (length * 0.70), cy + uy * (length * 0.70)
            c.create_line(px-4, py, px+4, py, fill="#fffde0", width=1)
            c.create_line(px, py-3, px, py+3, fill="#fffde0", width=1)

    def _fx_solid(self, pts, fill, shadow_src):
        """Solid pixel-style polygon with a hard offset shadow (same look as the original strike thrust)."""
        c = self.canvas
        c.create_polygon(*[v + (2 if i % 2 == 0 else 3) for i, v in enumerate(pts)], fill=mix(shadow_src, "#14151d", 0.80), outline="")
        c.create_polygon(*pts, fill=fill, outline="")

    def draw_effect(self, x, y, t, kind, extra=None):
        if not self.visible(x, y):
            return
        c = self.canvas
        cx, cy = self.center(x, y)
        if kind == "boom":
            r = CELL * (0.2 + 0.7 * t)
            c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=mix("#ff4f7d", C_BOARD, t), width=3)
            r2 = r * 0.55
            c.create_oval(cx - r2, cy - r2, cx + r2, cy + r2, outline=mix("#ffffff", C_BOARD, t), width=2)
            for k in range(8):
                ang = math.pi / 4 * k
                c.create_line(cx + r * 0.6 * math.cos(ang), cy + r * 0.6 * math.sin(ang),
                    cx + r * 1.2 * math.cos(ang), cy + r * 1.2 * math.sin(ang), fill=mix("#ffb3c6", C_BOARD, t), width=2)
        elif kind == "hit":
            r = CELL * (0.1 + 0.45 * t)
            c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=mix(C_CYAN, C_BOARD, t), width=2)
        elif kind == "blast":
            rad, col = extra
            u = min(1.0, t * 1.6)
            r = rad * CELL * u
            # Premium impact bloom: dark halo -> colored shell -> white-hot core.
            for mul, width, fade in ((1.18, 8, 0.84), (1.02, 4, 0.48), (0.72, 2, 0.14)):
                rr = r * mul
                c.create_oval(cx - rr, cy - rr, cx + rr, cy + rr, outline=mix(col, C_BOARD, fade), width=width)
            core = max(2.0, r * (0.14 + 0.25 * (1.0-u)))
            c.create_oval(cx-core, cy-core, cx+core, cy+core, fill=mix("#ffffff", col, 0.24+0.55*u), outline="")
            for k in range(10):
                a = self.time * 2.4 + k * math.tau / 10
                d0, d1 = r * 0.34, r * (0.92 + 0.30 * u)
                c.create_line(cx+math.cos(a)*d0, cy+math.sin(a)*d0, cx+math.cos(a)*d1, cy+math.sin(a)*d1,
                              fill=mix(col, "#ffffff", 0.28*u), width=2)
        elif kind == "slash":
            # Powerful directional thrust. Older boss impacts can supply only a colour;
            # use the player's current facing as a safe fallback direction.
            payload = tuple(extra or ())
            col0 = payload[0] if len(payload) > 0 else "#ffffff"
            if len(payload) >= 3:
                dx, dy = payload[1], payload[2]
            else:
                dx, dy = getattr(self, "direction", (0.0, -1.0))
            wm = payload[3] if len(payload) > 3 else 1.0
            mag = max(0.001, math.hypot(dx, dy))
            ux, uy = dx / mag, dy / mag
            nx, ny = -uy, ux
            fade = max(0.0, min(1.0, t))
            col = mix(col0, C_BOARD, fade * 0.35)

            # Fast wind-up, then a strong forward punch and short recovery.
            hit = min(1.0, t * 2.15)
            settle = max(0.0, (t - 0.62) / 0.38)
            reach = CELL * (1.45 + wm * 0.72) * (0.34 + 0.92 * hit) * (1.0 - 0.15 * settle)
            width = max(3.0, CELL * (0.16 + 0.08 * wm) * (0.65 + 0.35 * hit))
            bx, by = cx - ux * CELL * 0.38, cy - uy * CELL * 0.38
            tip = (cx + ux * reach, cy + uy * reach)
            shoulder = (cx + ux * reach * 0.55, cy + uy * reach * 0.55)

            # Offset pixel shadow gives the strike a grounded, game-like depth.
            offx, offy = nx * 2.0, ny * 2.0
            c.create_polygon(
                bx + offx, by + offy,
                shoulder[0] + nx * width * 1.15 + offx, shoulder[1] + ny * width * 1.15 + offy,
                tip[0] + offx, tip[1] + offy,
                shoulder[0] - nx * width * 1.15 + offx, shoulder[1] - ny * width * 1.15 + offy,
                fill=mix(col0, "#14151d", 0.80), outline="")

            # Heavy tapered thrust body.
            c.create_polygon(
                bx, by,
                shoulder[0] + nx * width, shoulder[1] + ny * width,
                tip[0], tip[1],
                shoulder[0] - nx * width, shoulder[1] - ny * width,
                fill=col, outline="")

            # Bright spine, not a glow: makes the thrust read immediately.
            spine_start = (cx + ux * CELL * 0.05, cy + uy * CELL * 0.05)
            c.create_line(spine_start[0], spine_start[1], tip[0] - ux * CELL * 0.12, tip[1] - uy * CELL * 0.12,
                          fill=mix("#ffffff", col, 0.18 + 0.35 * fade), width=2)

            # Two angular pressure cuts behind the main thrust.
            trail_len = CELL * (0.70 + 0.35 * hit)
            for side in (-1, 1):
                ax0 = cx - ux * trail_len + nx * side * CELL * 0.18
                ay0 = cy - uy * trail_len + ny * side * CELL * 0.18
                ax1 = cx + ux * CELL * 0.18 + nx * side * CELL * 0.10
                ay1 = cy + uy * CELL * 0.18 + ny * side * CELL * 0.10
                c.create_line(ax0, ay0, ax1, ay1, fill=mix(col0, "#ffffff", 0.32), width=2)

            # Pixel impact mark at the tip during the strike's active frame.
            if hit > 0.34:
                for q in (-1, 0, 1):
                    px = tip[0] + ux * CELL * 0.08 + nx * q * 2.2
                    py = tip[1] + uy * CELL * 0.08 + ny * q * 2.2
                    c.create_rectangle(px-1, py-1, px+1, py+1, fill="#ffffff" if q == 0 else col, outline="")
        elif kind == "fang_bite":
            # VIPER: two solid tapered fangs snap shut on the target. Crisp pixel shapes, hard shadow, green drip.
            col0, dx, dy = extra
            mag = max(0.001, math.hypot(dx, dy))
            ux, uy = dx / mag, dy / mag
            nx, ny = -uy, ux
            fade = max(0.0, min(1.0, t * 1.3))
            snap = min(1.0, t * 5.0)
            col = mix(col0, C_BOARD, fade * 0.40)
            gap = CELL * (0.46 - 0.34 * snap)
            for side in (-1, 1):
                bx, by = cx + ux * CELL * 0.30 + nx * side * gap * 1.5, cy + uy * CELL * 0.30 + ny * side * gap * 1.5
                tx, ty = cx + ux * CELL * (1.20 + 0.25 * snap) + nx * side * gap * 0.35, cy + uy * CELL * (1.20 + 0.25 * snap) + ny * side * gap * 0.35
                w = CELL * 0.14
                pts = [bx + nx * w, by + ny * w, tx, ty, bx - nx * w, by - ny * w]
                self._fx_solid(pts, col, col0)
                c.create_line(bx, by, tx - ux * 2, ty - uy * 2, fill=mix("#ffffff", col, 0.25 + 0.3 * fade), width=1)
                c.create_rectangle(tx - 1, ty - 1, tx + 1, ty + 1, fill="#ffffff", outline="")
            if snap >= 1.0:
                mx_, my_ = cx + ux * CELL * 1.3, cy + uy * CELL * 1.3
                for q in (-1, 0, 1):
                    px, py = mx_ + nx * q * 3, my_ + ny * q * 3
                    c.create_rectangle(px - 1, py - 1, px + 1, py + 1, fill="#ffffff" if q == 0 else col, outline="")
                drip = CELL * 0.30 * min(1.0, (t - 0.2) * 4.0)
                dcol = mix("#7ddb4a", C_BOARD, fade * 0.6)
                for q in (-1, 1):
                    px, py = mx_ + nx * q * CELL * 0.12, my_ + CELL * 0.1 + drip
                    c.create_rectangle(px - 1, py - 2, px + 1, py + 2, fill=dcol, outline="")
        elif kind == "tail_slam":
            # PYTHON: a ground-pounding shockwave. White-hot impact flash, a thick expanding ring with a bright leading
            # edge, glowing cracks tearing through the floor, flying rock chunks, and a rolling dust cloud.
            col0, radius = extra
            R = CELL * radius
            u = min(1.0, t * 2.6)                              # shockwave expansion (fast, eased out)
            u = 1.0 - (1.0 - u) ** 3
            fade = max(0.0, min(1.0, (t - 0.55) / 0.85))
            rr = R * (0.18 + 0.82 * u)
            # scorched impact decal
            if t < 1.2:
                dr = R * 0.55 * (0.4 + 0.6 * u)
                c.create_oval(cx - dr, cy - dr, cx + dr, cy + dr, fill=mix("#0b0a10", C_BOARD, 0.25 + fade * 0.7), outline="", stipple="gray50")
            # glowing cracks (deterministic jagged lines)
            for k in range(10):
                a0 = k * math.tau / 10 + 0.17 * (k % 3)
                L = R * (0.55 + 0.42 * ((k * 37) % 10) / 10.0) * u
                pts = [cx, cy]
                for i in range(1, 5):
                    f = i / 4
                    j = math.sin(k * 7.3 + i * 2.1) * 0.20
                    pts += [cx + math.cos(a0 + j * (1 - f)) * L * f, cy + math.sin(a0 + j * (1 - f)) * L * f]
                c.create_line(*pts, fill=mix("#0b0a10", C_BOARD, fade * 0.8), width=5)
                c.create_line(*pts, fill=mix(col0, C_BOARD, fade * 0.7), width=2)
                c.create_line(*pts, fill=mix("#ffffff", col0, 0.35 + 0.4 * fade), width=1)
            # main shockwave band: shadow, body, white-hot leading edge
            band = max(4, int(CELL * 1.0 * (1.0 - 0.72 * u)))
            c.create_oval(cx - rr + 3, cy - rr + 4, cx + rr + 3, cy + rr + 4, outline=mix(col0, "#14151d", 0.85), width=band)
            c.create_oval(cx - rr, cy - rr, cx + rr, cy + rr, outline=mix(col0, C_BOARD, fade * 0.8), width=band)
            c.create_oval(cx - rr, cy - rr, cx + rr, cy + rr, outline=mix("#ffffff", col0, 0.15 + 0.5 * fade), width=2)
            if u > 0.35:                                       # trailing second ring
                r2 = rr * 0.72
                c.create_oval(cx - r2, cy - r2, cx + r2, cy + r2, outline=mix(col0, C_BOARD, 0.35 + fade * 0.6), width=max(2, band // 2))
            # flying rock chunks on ballistic arcs
            for k in range(14):
                a_ = k * math.tau / 14 + (k % 4) * 0.19
                reach_ = R * (0.45 + 0.55 * ((k * 53) % 10) / 10.0) * u
                lift = math.sin(min(1.0, t * 1.6) * math.pi) * CELL * (0.7 + 0.9 * ((k * 31) % 10) / 10.0)
                px, py = cx + math.cos(a_) * reach_, cy + math.sin(a_) * reach_ * 0.92 - lift
                sz = 2 + (k % 3)
                c.create_rectangle(px - sz + 2, py - sz + 3, px + sz + 2, py + sz + 3, fill="#14151d", outline="")
                c.create_rectangle(px - sz, py - sz, px + sz, py + sz, fill=mix("#a8967a" if k % 2 else "#6d5f4a", C_BOARD, fade), outline="")
            # crown of stone/shock spikes bursting out of the ring edge
            if t < 1.1:
                for k in range(12):
                    a_ = k * math.tau / 12 + 0.12
                    ux_, uy_ = math.cos(a_), math.sin(a_)
                    nx_, ny_ = -uy_, ux_
                    base_r = rr + band * 0.4
                    h = CELL * (0.35 + 0.30 * ((k * 17) % 5) / 5.0) * (1.0 - fade) * min(1.0, u * 1.6)
                    w = CELL * 0.17
                    bxk, byk = cx + ux_ * base_r, cy + uy_ * base_r
                    self._fx_solid([bxk + nx_ * w, byk + ny_ * w, bxk + ux_ * h, byk + uy_ * h, bxk - nx_ * w, byk - ny_ * w],
                                   mix("#c9b98a", C_BOARD, fade * 0.6), "#8a7a5a")
            # dust: pixel puffs rolling out and rising
            for k in range(18):
                a_ = k * math.tau / 18 + (k % 3) * 0.13
                d = R * (0.55 + 0.45 * ((k * 41) % 10) / 10.0) * u
                px, py = cx + math.cos(a_) * d, cy + math.sin(a_) * d * 0.9 - t * CELL * (0.4 + 0.5 * (k % 3) / 2)
                sz = 2 + (k % 4)
                c.create_rectangle(px - sz, py - sz, px + sz, py + sz, fill=mix("#d8cba8", C_BOARD, 0.35 + fade * 0.65), outline="")
            # initial impact flash
            if t < 0.2:
                fr = R * 0.42 * (1.0 - t / 0.2) + 4
                c.create_oval(cx - fr, cy - fr, cx + fr, cy + fr, fill=mix("#ffffff", col0, 0.15 + t * 2.5), outline="")
        elif kind == "volt_slash":
            # MAMBA: a wide crescent lightning blade that sweeps across the whole hit arc, leaves a hot afterimage,
            # crackles along its edge and bursts into an X of sparks where it connects.
            col0, dx, dy, reach, half, hit = extra
            ang0 = math.atan2(dy, dx)
            R = CELL * reach * 0.95
            fade = max(0.0, min(1.0, (t - 0.1) * 1.8))
            sweep = min(1.0, t * 6.0)
            col = mix(col0, C_BOARD, fade * 0.45)
            head = ang0 - half * 1.15 + sweep * half * 2.3          # blade leading angle
            span = half * 2.3 * min(1.0, sweep * 1.3)               # how much of the arc is drawn
            n = 22
            outer, inner = [], []
            for i in range(n + 1):
                f = i / n
                ang = head - span * f
                thick = R * 0.42 * math.sin(math.pi * (0.12 + 0.88 * (1.0 - f)) ** 0.9) * (1.0 - fade * 0.5)
                jag = math.sin(i * 2.7 + 1.3) * CELL * 0.05
                outer += [cx + math.cos(ang) * (R + jag), cy + math.sin(ang) * (R + jag)]
                inner += [cx + math.cos(ang) * (R - thick), cy + math.sin(ang) * (R - thick)]
            pts = outer + [inner[j] for k in range(n, -1, -1) for j in (2 * k, 2 * k + 1)]
            self._fx_solid(pts, col, col0)
            c.create_line(*outer, fill=mix("#c18bff", C_BOARD, fade * 0.5), width=4)
            c.create_line(*outer, fill=mix("#ffffff", col, 0.15 + 0.5 * fade), width=2)
            if sweep > 0.4:                                          # thin echo crescent trailing behind the main blade
                echo = []
                for i in range(n + 1):
                    ang = head - span * (i / n) - 0.16
                    echo += [cx + math.cos(ang) * R * 0.80, cy + math.sin(ang) * R * 0.80]
                c.create_line(*echo, fill=mix("#c18bff", C_BOARD, 0.25 + fade * 0.7), width=3)
            # hot afterimage streak from the head along the aim line, with a fixed zig-zag crackle
            ux, uy = math.cos(ang0), math.sin(ang0)
            nx, ny = -uy, ux
            L = R * (0.35 + 0.65 * sweep)
            zp = []
            offs = [0.0, 0.12, -0.12, 0.10, -0.09, 0.07, 0.0]
            for i, o in enumerate(offs):
                f = i / (len(offs) - 1)
                zp += [cx + ux * L * f + nx * o * CELL, cy + uy * L * f + ny * o * CELL]
            c.create_line(*[v + 2 for v in zp], fill=mix("#c18bff", "#14151d", 0.8), width=5)
            c.create_line(*zp, fill=mix("#c18bff", C_BOARD, fade * 0.5), width=4)
            c.create_line(*zp, fill=mix("#ffffff", C_BOARD, fade * 0.4), width=1)
            # impact X + sparks at the tip of the aim line
            if sweep > 0.55:
                tx, ty = cx + ux * R * 0.88, cy + uy * R * 0.88
                k_ = CELL * (0.30 + 0.35 * (1.0 if hit else 0.4))
                for sgn in (-1, 1):
                    c.create_line(tx - ux * k_ + nx * sgn * k_, ty - uy * k_ + ny * sgn * k_,
                                  tx + ux * k_ - nx * sgn * k_, ty + uy * k_ - ny * sgn * k_,
                                  fill=mix("#ffffff", C_BOARD, fade * 0.6), width=3)
                for q in range(6):
                    a_ = q * math.tau / 6 + 0.5
                    d_ = CELL * (0.35 + 0.5 * sweep)
                    px, py = tx + math.cos(a_) * d_, ty + math.sin(a_) * d_
                    c.create_rectangle(px - 1, py - 1, px + 1, py + 1, fill="#ffffff" if q % 2 else "#c18bff", outline="")
        elif kind == "volt_arc":
            tx, ty = extra
            ex, ey = self.center(tx, ty)
            fade = max(0.0, min(1.0, t * 1.8))
            mag = max(1.0, math.hypot(ex - cx, ey - cy))
            nx, ny = -(ey - cy) / mag, (ex - cx) / mag
            pts = []
            offs = [0.0, 0.16, -0.14, 0.12, -0.10, 0.0]
            for i, o in enumerate(offs):
                f = i / (len(offs) - 1)
                pts += [cx + (ex - cx) * f + nx * o * CELL, cy + (ey - cy) * f + ny * o * CELL]
            c.create_line(*[v + 2 for v in pts], fill=mix("#c18bff", "#14151d", 0.8), width=4)
            c.create_line(*pts, fill=mix("#c18bff", C_BOARD, fade * 0.5), width=4)
            c.create_line(*pts, fill=mix("#ffffff", C_BOARD, fade * 0.4), width=1)
        elif kind == "spit":
            dx, dy = extra[0], extra[1]
            reach = extra[2] if len(extra) > 2 else 9.0
            width_mul = extra[3] if len(extra) > 3 else 1.0
            col0 = ECOL["dendro"]
            col = mix(col0, C_BOARD, t)
            for k, width, fade in ((-0.32, 9, 0.82), (-0.15, 6, 0.54), (0, 3, 0.08), (0.15, 6, 0.54), (0.32, 9, 0.82)):
                ox, oy = -dy * k * CELL * width_mul, dx * k * CELL * width_mul
                c.create_line(cx + ox, cy + oy, cx + dx * CELL * reach + ox, cy + dy * CELL * reach + oy,
                              fill=mix(col0, C_BOARD, fade + t*0.10), width=width)
        elif kind == "element_cast":
            el, ang = extra
            col = ECOL.get(el, C_CYAN)
            r = CELL * (0.25 + 0.65 * min(1.0, t))
            c.create_oval(cx-r, cy-r, cx+r, cy+r, outline=col, width=2)
            for k in range(4):
                a = ang + k * math.pi / 2
                c.create_line(cx, cy, cx + math.cos(a) * r * 1.8, cy + math.sin(a) * r * 1.8, fill=mix(col, "#ffffff", 0.35), width=1)
        elif kind == "element_hit":
            el, intensity, blocked = extra
            col = ECOL.get(el, C_CYAN)
            fade = min(1.0, t)
            r = CELL * (0.22 + 0.70 * intensity * fade)
            c.create_oval(cx-r, cy-r, cx+r, cy+r, outline=mix(col, "#ffffff", 0.28), width=2)
            if blocked:
                c.create_line(cx-r, cy-r, cx+r, cy+r, fill=col, width=2)
                c.create_line(cx-r, cy+r, cx+r, cy-r, fill=col, width=2)
            else:
                for k in range(5):
                    a = self.time * 4 + k * math.pi * 2 / 5
                    rr = r * (0.6 + 0.15 * k)
                    c.create_rectangle(cx+math.cos(a)*rr-2, cy+math.sin(a)*rr-2, cx+math.cos(a)*rr+2, cy+math.sin(a)*rr+2, fill=col, outline="")
        elif kind == "reaction_burst":
            react, trig, aur = extra
            cols = {"vaporize":"#64dfff", "melt":"#ff9a3a", "freeze":"#bfefff", "overload":"#ff553d",
                    "electro-charged":"#c18bff", "superconduct":"#d8c8ff", "burning":"#ff7040",
                    "bloom":"#7ddb4a", "quicken":"#9cff86", "spread":"#7ddb4a", "aggravate":"#c18bff",
                    "swirl":"#6fffd0", "crystallize":"#f5c542", "eclipse":"#fff3b0"}
            col = cols.get(react, ECOL.get(trig, "#ffffff"))
            r = CELL * (0.35 + 1.7 * min(1.0, t))
            c.create_oval(cx-r, cy-r, cx+r, cy+r, outline=col, width=4)
            c.create_oval(cx-r*0.55, cy-r*0.55, cx+r*0.55, cy+r*0.55, outline="#ffffff", width=2)
            c.create_text(cx, cy-r*0.45, text=react.upper(), fill="#ffffff", font=("Segoe UI", 9, "bold"))
            for k in range(8):
                a = self.time * 1.8 + k * math.pi / 4
                d0, d1 = r*0.45, r*1.25
                c.create_line(cx+math.cos(a)*d0, cy+math.sin(a)*d0, cx+math.cos(a)*d1, cy+math.sin(a)*d1, fill=col, width=2)
        elif kind == "boss_hit":
            (el,) = extra
            col = ECOL.get(el, "#ffffff")
            r = CELL * (0.18 + 0.70 * min(1.0, t))
            c.create_oval(cx-r, cy-r, cx+r, cy+r, outline=col, width=3)
            for k in range(6):
                a = k * math.pi / 3 + self.time * 2
                d = r * 1.5
                c.create_line(cx+math.cos(a)*r*0.5, cy+math.sin(a)*r*0.5, cx+math.cos(a)*d, cy+math.sin(a)*d, fill=col, width=2)
        elif kind == "boss_cast":
            idx, name, col = extra
            r = CELL * (0.55 + 2.0 * min(1.0, t))
            c.create_oval(cx-r, cy-r*0.72, cx+r, cy+r*0.72, outline=mix(col, "#ffffff", 0.30), width=3, dash=(6,4))
            for k in range(10):
                a = self.time * (1.2 + idx*0.13) + k * math.pi * 2 / 10
                d = r * (0.65 + 0.22 * math.sin(self.time*4+k))
                c.create_line(cx+math.cos(a)*r*0.35, cy+math.sin(a)*r*0.35, cx+math.cos(a)*d, cy+math.sin(a)*d, fill=col, width=2)
        elif kind == "save":
            r = CELL * (0.3 + 1.2 * t / 2)
            c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=mix("#fff1a0", C_BOARD, t / 2), width=3)
        else:
            r = CELL * (0.1 + 0.25 * t)
            col = mix(C_CYAN, C_BOARD, t)
            c.create_line(cx - r, cy - r, cx + r, cy + r, fill=col, width=2)
            c.create_line(cx - r, cy + r, cx + r, cy - r, fill=col, width=2)

    # ---- snake
    def draw_snake(self):
        c = self.canvas
        dead = self.state == "failed"
        ghost = self.invincible > 0 and int(self.time * 14) % 2 == 0
        pts = self.snake_points()
        if dead and getattr(self, "death_t", 0.0) > 0:
            p = max(0.0, min(1.0, self.death_t / 1.35))
            hx, hy = self.center(*pts[0])
            rr = CELL * (0.7 + (1.0-p) * 2.6)
            c.create_oval(hx-rr, hy-rr, hx+rr, hy+rr, outline="#ff6b6b", width=max(1, int(4*p)))
            for k in range(14):
                a = self.time * 4 + k * math.pi * 2 / 14
                d = CELL * (0.6 + (1.0-p) * 3.5)
                sx, sy = hx + math.cos(a)*d, hy + math.sin(a)*d
                c.create_rectangle(sx-2, sy-2, sx+2, sy+2, fill="#ffc0c0", outline="")
        last = len(pts) - 1
        for i in range(last, -1, -1):
            x, y = pts[i]
            if not self.visible(x, y):
                continue
            cx, cy = self.center(x, y)
            # Ground shadow belongs to the whole snake, not just the head.
            # Keep it compact so adjacent body shadows read as one continuous contact shadow.
            shadow_w = int(CELL * (0.72 if i > 0 else 0.96))
            shadow_h = int(CELL * (0.22 if i > 0 else 0.28))
            self.draw_pixel_shadow(cx, cy + CELL * (0.56 if i > 0 else 0.62), shadow_w, shadow_h)
            wave = round((math.sin(self.time * 7 - i * 0.75) + 1) * 2.5) / 5
            if dead:
                edge, glow, core = "#ff6b6b", "#5a1818", "#ffc0c0"
            elif ghost:
                edge, glow, core = "#d9f0ff", "#27506e", "#ffffff"
            else:
                pal = self.cls["pal"]                   # each class has its own colours
                edge = mix(pal[0], pal[1], wave)
                glow = mix(pal[2], pal[3], wave)
                core = pal[4]
                if self.camo_t > 0:                 # camouflaged snake fades into the floor
                    edge, glow, core = mix(edge, C_BOARD, 0.6), mix(glow, C_BOARD, 0.6), mix(core, C_BOARD, 0.6)
            if self.coil_t > 0 and not dead:
                r = CELL * (0.62 + 0.08 * math.sin(self.time * 8 - i))
                c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=ECOL["geo"], width=2)
            if i == 0:
                if self.dash_t > 0:
                    dx, dy = self.direction
                    for k in (-6, 0, 6):
                        c.create_line(cx - dx * 10 - dy * k, cy - dy * 10 + dx * k, cx - dx * 34 - dy * k, cy - dy * 34 + dx * k,
                            fill=ECOL["anemo"], width=2)
                elif self.running:
                    dx, dy = self.direction
                    for k in (-5, 5):
                        c.create_line(cx - dx * 12 - dy * k, cy - dy * 12 + dx * k, cx - dx * 26 - dy * k, cy - dy * 26 + dx * k,
                            fill=C_GOLD, width=2)
                if self.bulwark_t > 0 and not dead:
                    c.create_oval(cx - CELL * 0.85, cy - CELL * 0.85, cx + CELL * 0.85, cy + CELL * 0.85, outline="#ffa23c", width=3)
                self.draw_head(cx, cy, edge, glow, core)
            elif i == last:
                self.draw_tail(pts, cx, cy, edge, glow)
            else:
                c.create_image(cx, cy, image=self.body_tile(edge, glow, core, self.S["form_tank"] > 0 and not dead))
        if self.boss_active() and self.state == "playing":
            hx, hy = self.center(*pts[0])
            hr = HEAD_HIT * CELL * 0.8
            c.create_oval(hx - hr, hy - hr, hx + hr, hy + hr, fill="#ffffff", outline="#ff4f7d", width=2)

    def draw_head(self, cx, cy, edge, glow, core):
        c = self.canvas
        # v28: restore the original head silhouette exactly; only the motion is animated.
        # Each class gets a slightly different head-bob cadence without changing the art.
        cid = getattr(self, "run_class", getattr(self, "pclass", "cobra"))
        # Keep the original head welded to the first body segment.  The previous
        # animation translated the head too far sideways, which made it look like
        # the neck could snap away from the snake.  Animation is now deliberately
        # rough and subtle: only a tiny breathing offset plus a short attack nudge.
        motion = {"viper": (5.0, 0.0030), "python": (3.2, 0.0018),
                  "cobra": (4.0, 0.0012), "mamba": (7.0, 0.0034)}.get(cid, (4.0, 0.0020))
        rate, amp = motion
        bob = math.sin(getattr(self, "time", 0.0) * rate) * amp
        base_ca, base_sa = math.cos(self.head_angle), math.sin(self.head_angle)
        cx += -base_sa * bob * CELL
        cy += base_ca * bob * CELL
        if self.lunge_t > 0:
            off = CELL * 0.24 * math.sin(math.pi * (1 - self.lunge_t / 0.22))
            cx += self.lunge_dir[0] * off
            cy += self.lunge_dir[1] * off
        ca, sa = base_ca, base_sa
        if self.S["form_ranged"] > 0:             # cobra hood
            hood = []
            for hx, hy in ((-0.05, -0.2), (-0.38, -0.62), (-0.62, -0.28), (-0.66, 0.0), (-0.62, 0.28), (-0.38, 0.62), (-0.05, 0.2)):
                hood += [cx + (hx * ca - hy * sa) * CELL, cy + (hx * sa + hy * ca) * CELL]
            c.create_polygon(hood, fill=SNAKE_BODY, outline=edge, width=2)
        pts = []
        for hx, hy in HEAD_SHAPE:
            pts += [cx + (hx * ca - hy * sa) * CELL, cy + (hx * sa + hy * ca) * CELL]
        c.create_polygon(pts, fill="", outline=glow, width=8)
        c.create_polygon(pts, fill=SNAKE_BODY, outline=edge, width=2)
        a = (cx + (0.36 * ca) * CELL, cy + (0.36 * sa) * CELL)
        b = (cx - (0.10 * ca) * CELL, cy - (0.10 * sa) * CELL)
        c.create_line(*a, *b, fill=core, width=2, capstyle="round")
        if self.lunge_t > 0:                      # fangs
            for k in (-1, 1):
                fx = cx + (0.5 * ca - 0.1 * k * -sa) * CELL
                fy = cy + (0.5 * sa - 0.1 * k * ca) * CELL
                c.create_line(fx, fy, fx + ca * 8, fy + sa * 8, fill="#ffffff", width=2)

    def draw_tail(self, pts, cx, cy, edge, glow):
        c = self.canvas
        (ax, ay), (bx, by) = pts[-2], pts[-1]
        ux, uy = bx - ax, by - ay
        norm = math.hypot(ux, uy) or 1.0
        ux, uy = ux / norm, uy / norm
        r = CELL * 0.22
        c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=glow, width=7)
        c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=edge, width=2)
        tip = (cx + ux * (r + CELL * 0.26), cy + uy * (r + CELL * 0.26))
        base = (cx + ux * r, cy + uy * r)
        c.create_line(*base, *tip, fill=glow, width=6, capstyle="round")
        c.create_line(*base, *tip, fill=edge, width=2, capstyle="round")
        nx, ny = -uy * CELL * 0.1, ux * CELL * 0.1
        c.create_line(tip[0] + nx, tip[1] + ny, tip[0] - nx, tip[1] - ny, fill=edge, width=2)
