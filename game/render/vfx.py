"""Premium procedural VFX layer for Repair Terminal.

Tkinter has no GPU bloom/post-processing pipeline, so this module builds a faux
HDR look from layered shapes, bright cores, stippled halo passes, particles,
impact rings, directional trails, hit-stop and camera shake. Everything remains
vector/procedural and scales with the existing quality setting.
"""
import math
import random
import tkinter as tk

from ..config import C_BOARD, C_CYAN, C_GOLD, C_PINK, CELL
from ..data.elements import ECOL
from ..utils import mix
from .gpu_pipeline import GpuVfxOverlay


class VfxMixin:
    """Runtime VFX state + renderer."""

    def init_vfx(self):
        self.vfx_particles = []
        self.vfx_seq = 0
        self.vfx_flash = 0.0
        self.vfx_flash_col = "#ffffff"
        self.vfx_flash_power = 0.0
        self.vfx_ring = []
        self.hit_stop = 0.0
        self.shake = max(getattr(self, "shake", 0.0), 0.0)
        if getattr(self, "gpu_fx", None) is None:          # created ONCE: reset_game() runs on every NEW GAME
            self.gpu_fx = GpuVfxOverlay()
            self.gpu_fx_enabled = self.gpu_fx.start()

    def vfx_shake(self, power=0.15, duration=None):
        if duration is None:
            duration = 0.18 + power * 0.45
        self.shake = max(getattr(self, "shake", 0.0), min(1.0, power))
        self.__dict__["shake_t"] = max(self.__dict__.get("shake_t", 0.0), duration)

    def vfx_hitstop(self, duration=0.035):
        # Tiny freezes sell heavy impacts. Never allow attacks to lock the game.
        self.hit_stop = max(getattr(self, "hit_stop", 0.0), min(0.08, duration))

    def vfx_flash_screen(self, col="#ffffff", power=0.22, duration=0.12):
        self.vfx_flash_col = col
        self.vfx_flash_power = max(self.vfx_flash_power, power)
        self.vfx_flash = max(self.vfx_flash, duration)

    def _vfx_rng(self):
        self.vfx_seq += 1
        return random.Random((int(self.time * 1000) << 5) ^ self.vfx_seq)

    def vfx_burst(self, x, y, col, count=14, speed=4.5, size=0.10, life=0.55, kind="spark", spread=math.tau):
        if not hasattr(self, "vfx_particles"):
            self.init_vfx()
        q = getattr(self, "quality", 2)
        scale = 1.0 if q > 1 else (0.62 if q > 0 else 0.34)
        n = max(2, int(count * scale))
        rng = self._vfx_rng()
        for _ in range(n):
            ang = rng.uniform(-spread / 2, spread / 2) + rng.random() * math.tau
            sp = speed * (0.25 + rng.random() * 0.95)
            lf = life * (0.55 + rng.random() * 0.80)
            self.vfx_particles.append({
                "x": float(x), "y": float(y), "vx": math.cos(ang) * sp, "vy": math.sin(ang) * sp,
                "life": lf, "max": lf, "size": size * (0.65 + rng.random() * 1.35),
                "col": col, "kind": kind, "drag": 0.90 + rng.random() * 0.07,
                "gravity": rng.uniform(-0.15, 0.35), "spin": rng.uniform(-5, 5),
                "phase": rng.random() * math.tau,
            })
        cap = 240 if q > 1 else (150 if q > 0 else 80)
        if len(self.vfx_particles) > cap:
            self.vfx_particles = self.vfx_particles[-cap:]

    def vfx_arc(self, x, y, col, radius=1.0, life=0.45, width=2.0, start=0.0, extent=180):
        self.vfx_ring.append({"x": x, "y": y, "r": radius, "life": life, "max": life,
                              "col": col, "width": width, "start": start, "extent": extent})
        if len(self.vfx_ring) > 40:
            self.vfx_ring = self.vfx_ring[-40:]

    def vfx_impact(self, x, y, col, power=1.0, element=None, critical=False, boss=False):
        """One call for the expensive-feeling combat feedback."""
        p = max(0.4, power)
        self.vfx_burst(x, y, col, 12 + int(8 * p), 3.8 + 3.2 * p, 0.09 + 0.04 * p, 0.42 + 0.10 * p, "spark")
        self.vfx_burst(x, y, "#ffffff", 5 + int(3 * p), 2.0 + p, 0.05, 0.28 + 0.06 * p, "shard")
        self.vfx_arc(x, y, mix(col, "#ffffff", 0.25), 0.35 + 0.35 * p, 0.32 + 0.14 * p, 2.0 + p * 1.5, 0, 310)
        self.vfx_arc(x, y, col, 0.65 + 0.70 * p, 0.48 + 0.16 * p, 2.0 + p, 40, 250)
        self.vfx_hitstop(0.045 if critical else (0.03 if boss else 0.018))
        self.vfx_shake(0.20 + 0.08 * p if critical else 0.10 + 0.06 * p)
        if critical:
            self.vfx_flash_screen(col, 0.13 if not boss else 0.18, 0.10)
        if boss or critical:
            self.vfx_burst(x, y, mix(col, "#ffffff", 0.55), 8, 5.8, 0.07, 0.65, "diamond")
        if element:
            self.vfx_element_signature(x, y, element, p)

    def vfx_element_signature(self, x, y, el, power=1.0):
        col = ECOL.get(el, C_CYAN)
        p = max(0.5, power)
        if el == "electro":
            for k in range(3):
                self.vfx_arc(x, y, col, 0.45 + 0.18 * k * p, 0.28 + 0.07 * k, 2,
                             k * 120 + self.time * 80, 150)
            self.vfx_burst(x, y, col, 7, 5.0, 0.07, 0.42, "bolt")
        elif el == "pyro":
            self.vfx_burst(x, y, col, 10, 4.6, 0.10, 0.48, "ember")
            self.vfx_arc(x, y, "#ffd78b", 0.65 * p, 0.40, 2.5, self.time * 50, 280)
        elif el == "cryo":
            self.vfx_burst(x, y, "#dffcff", 12, 3.8, 0.08, 0.62, "snow")
            self.vfx_arc(x, y, col, 0.8 * p, 0.50, 2, 0, 360)
        elif el == "hydro":
            self.vfx_burst(x, y, col, 9, 3.6, 0.09, 0.52, "droplet")
            self.vfx_arc(x, y, "#c9f3ff", 0.72 * p, 0.48, 2, 20, 300)
        elif el == "dendro":
            self.vfx_burst(x, y, col, 11, 3.7, 0.09, 0.58, "leaf")
            self.vfx_arc(x, y, "#eaffc8", 0.52 * p, 0.46, 2, 30, 260)
        elif el == "anemo":
            self.vfx_arc(x, y, col, 0.7 * p, 0.50, 2, self.time * 180, 260)
            self.vfx_arc(x, y, "#eaffff", 0.45 * p, 0.42, 1, -self.time * 220, 230)
        elif el == "geo":
            self.vfx_burst(x, y, col, 8, 3.2, 0.11, 0.52, "shard")
            self.vfx_arc(x, y, "#fff4bd", 0.75 * p, 0.52, 2.5, 45, 270)
        elif el == "abyss":
            self.vfx_arc(x, y, col, 0.8 * p, 0.62, 3, -self.time * 120, 320)
            self.vfx_burst(x, y, "#e9d8ff", 8, 3.5, 0.08, 0.65, "void")
        elif el == "light":
            self.vfx_arc(x, y, "#fff8ca", 0.9 * p, 0.44, 3, self.time * 100, 300)
            self.vfx_burst(x, y, "#ffffff", 10, 4.4, 0.08, 0.46, "star")
        elif el == "pulse":
            self.vfx_arc(x, y, C_CYAN, 0.65 * p, 0.36, 2, 0, 280)

    def vfx_update(self, dt):
        if not hasattr(self, "vfx_particles"):
            self.init_vfx()
        # Hit-stop freezes simulation, while the visual layer still advances very slightly.
        if self.hit_stop > 0:
            self.hit_stop = max(0.0, self.hit_stop - dt)
        alive = []
        for pt in self.vfx_particles:
            pt["life"] -= dt
            if pt["life"] <= 0:
                continue
            pt["x"] += pt["vx"] * dt
            pt["y"] += pt["vy"] * dt
            drag = pt.get("drag", 0.94) ** (dt * 60)
            pt["vx"] *= drag
            pt["vy"] = pt["vy"] * drag + pt.get("gravity", 0.0) * dt
            alive.append(pt)
        self.vfx_particles = alive
        new_rings = []
        for r in self.vfx_ring:
            r["life"] -= dt
            if r["life"] > 0:
                new_rings.append(r)
        self.vfx_ring = new_rings
        self.vfx_flash = max(0.0, self.vfx_flash - dt)
        self.vfx_flash_power = max(0.0, self.vfx_flash_power - dt * 1.8)
        self.__dict__["shake_t"] = max(0.0, self.__dict__.get("shake_t", 0.0) - dt)
        if self.__dict__.get("shake_t", 0.0) <= 0:
            self.shake = max(0.0, self.shake - dt * 2.8)

        gpu = getattr(self, "gpu_fx", None)
        if gpu is not None and getattr(self, "gpu_fx_enabled", False):     # (CPU mode used to build these lists for nothing)
            # Transform world-space FX into canvas-space once on the Tk thread, then the GL thread only renders.
            particles = []
            for pt in self.vfx_particles:
                if not self.visible(pt["x"], pt["y"]):
                    continue
                px, py = self.center(pt["x"], pt["y"])
                particles.append({
                    "sx": px, "sy": py,
                    "size_px": max(2.0, CELL * float(pt.get("size", 0.1)) * 0.9),
                    "angle": self.time * float(pt.get("spin", 0.0)) + float(pt.get("phase", 0.0)),
                    "life": pt["life"], "max": pt["max"], "col": pt["col"],
                })
            rings = []
            for r in self.vfx_ring:
                if not self.visible(r["x"], r["y"]):
                    continue
                px, py = self.center(r["x"], r["y"])
                rings.append({
                    "sx": px, "sy": py,
                    "radius_px": CELL * float(r["r"]),
                    "life": r["life"], "max": r["max"],
                    "col": r["col"], "start": r["start"], "extent": r["extent"],
                })
            try:
                gpu.set_geometry(self.canvas.winfo_rootx(), self.canvas.winfo_rooty(), self.bw, self.bh,
                                  self.state == "playing" or self.state == "ready")
                gpu.submit({
                    "time": self.time, "particles": particles, "rings": rings,
                    "flash": self.vfx_flash, "flash_power": self.vfx_flash_power,
                    "flash_col": self.vfx_flash_col,
                })
            except Exception:
                pass

    def _particle_shape(self, c, px, py, sz, col, kind, ang, alpha):
        # alpha controls mixing toward the board because Canvas primitives have no general alpha.
        faint = mix(col, "#ffffff", max(0.0, min(0.50, (1.0 - alpha) * 0.35)))
        bright = mix(col, "#ffffff", min(0.72, alpha * 0.85))
        if kind in ("shard", "diamond", "snow", "leaf", "star"):
            ca, sa = math.cos(ang), math.sin(ang)
            pts = []
            if kind == "star":
                for k in range(8):
                    rr = sz * (1.35 if k % 2 == 0 else 0.45)
                    a = ang + k * math.pi / 4
                    pts.extend((px + math.cos(a)*rr, py + math.sin(a)*rr))
            elif kind == "leaf":
                pts = [px, py-sz*1.2, px+sz*0.6, py, px, py+sz*1.2, px-sz*0.6, py]
            else:
                pts = [px + ca*sz*1.5, py + sa*sz*1.5, px - sa*sz*0.7, py + ca*sz*0.7,
                       px - ca*sz*1.5, py - sa*sz*1.5, px + sa*sz*0.7, py - ca*sz*0.7]
            c.create_polygon(*pts, outline=faint, fill="")
            c.create_line(px-ca*sz, py-sa*sz, px+ca*sz, py+sa*sz, fill=bright, width=max(1, int(sz*0.8)))
        elif kind == "bolt":
            pts = [px-sz*1.4, py-sz*0.3, px-sz*0.1, py-sz*0.1, px-sz*0.55, py+sz*0.85,
                   px+sz*1.4, py+sz*0.05, px+sz*0.15, py-sz*0.08, px+sz*0.6, py-sz*0.9]
            c.create_line(*pts, fill=faint, width=max(1, int(sz*0.8)))
            c.create_line(px-sz*1.15, py-sz*0.2, px+sz*1.15, py+sz*0.0, fill=bright, width=1)
        elif kind in ("ember", "droplet"):
            c.create_oval(px-sz, py-sz, px+sz, py+sz, fill=faint, outline=bright, width=1)
            c.create_oval(px-sz*0.36, py-sz*0.36, px+sz*0.36, py+sz*0.36, fill="#ffffff", outline="")
        elif kind == "void":
            c.create_oval(px-sz*1.3, py-sz*1.3, px+sz*1.3, py+sz*1.3, outline=faint, width=max(1, int(sz*0.75)), dash=(2,3))
            c.create_oval(px-sz*0.45, py-sz*0.45, px+sz*0.45, py+sz*0.45, fill=bright, outline="")
        else:
            c.create_line(px-sz*1.4, py-sz*0.15, px+sz*1.4, py+sz*0.15, fill=faint, width=max(1, int(sz)))
            c.create_line(px-sz*0.8, py, px+sz*0.8, py, fill=bright, width=1)

    def glow_sprite(self, col, sz, alpha):
        """The stippled halo + pixel-cross glow of one particle, baked into one transparent image (it used to be
        2 stippled ovals + 8 rectangles = 10 canvas items per particle per frame)."""
        cache = self.__dict__.setdefault("_glow_cache", {})
        szb = max(1, int(round(sz * 2)))                        # half-pixel buckets
        ab = int(min(1.0, alpha) * 4)                           # 5 alpha buckets
        key = (col, szb, ab)
        img = cache.get(key)
        if img is None:
            sz_ = szb / 2.0
            a_ = ab / 4.0
            soft = mix(col, "#ffffff", 0.08)
            sg = mix(col, "#ffffff", min(0.55, 0.20 + a_ * 0.32))
            g = max(2.0, sz_ * 2.5)
            R = int(g) + 2
            img = tk.PhotoImage(master=self.canvas, width=2 * R + 1, height=2 * R + 1)
            r2 = sz_ * 1.35
            for j in range(-R, R + 1):
                for i in range(-R, R + 1):
                    d2 = i * i + j * j
                    if d2 <= g * g and i % 2 == 0 and j % 2 == 0:          # ~ stipple gray25
                        img.put(soft, to=(i + R, j + R, i + R + 1, j + R + 1))
                    elif d2 <= r2 * r2 and (i + j) % 2 == 0:               # ~ stipple gray50
                        img.put(soft, to=(i + R, j + R, i + R + 1, j + R + 1))
            q = max(1, int(round(sz_ * 0.42)))
            for ox, oy, mul in ((-2*q,0,1),(2*q,0,1),(0,-q,1),(0,q,1),(-q,-q,0.7),(q,-q,0.7),(-q,q,0.7),(q,q,0.7)):
                rr = max(1, int(round(q * mul)))
                x0, y0 = R + ox - rr, R + oy - rr
                x0, y0 = max(0, x0), max(0, y0)
                x1, y1 = min(2 * R + 1, R + ox + rr), min(2 * R + 1, R + oy + rr)
                if x1 > x0 and y1 > y0:
                    img.put(sg, to=(x0, y0, x1, y1))
            cache[key] = img
        return img

    def draw_vfx(self):
        """World-space particles/rings. CPU fallback; the GPU pipeline owns them when enabled."""
        if getattr(self, "gpu_fx_enabled", False):
            return
        c = self.canvas
        # rings first -> particles appear in front and feel layered
        for r in self.vfx_ring:
            if not self.visible(r["x"], r["y"]):
                continue
            t = max(0.0, min(1.0, r["life"] / max(0.001, r["max"])))
            age = 1.0 - t
            cx, cy = self.center(r["x"], r["y"])
            rr = CELL * r["r"] * (0.55 + age * 0.75)
            col = mix(r["col"], C_BOARD, 0.25 + age * 0.40)
            w = max(1, int(r["width"] * (0.55 + t)))
            c.create_arc(cx-rr, cy-rr*0.82, cx+rr, cy+rr*0.82, start=r["start"] + age*35,
                         extent=r["extent"], outline=mix(col, "#ffffff", 0.35*t), width=w)
            if t > 0.40:
                c.create_oval(cx-rr*0.85, cy-rr*0.70, cx+rr*0.85, cy+rr*0.70,
                              outline=mix(r["col"], "#ffffff", 0.32), width=1, dash=(3,7))

        for pt in self.vfx_particles:
            if not self.visible(pt["x"], pt["y"]):
                continue
            life = max(0.0, min(1.0, pt["life"] / max(0.001, pt["max"])))
            # bright at birth, soft at death; hold a stronger core in the middle.
            alpha = min(1.0, life * 1.5) * (0.45 + 0.55 * math.sin((1.0-life) * math.pi))
            cx, cy = self.center(pt["x"], pt["y"])
            sz = CELL * pt["size"] * (0.50 + 0.70 * alpha)
            col = pt["col"]
            c.create_image(cx, cy, image=self.glow_sprite(col, sz, alpha))
            self._particle_shape(c, cx, cy, max(1.2, sz), col, pt["kind"], self.time * pt.get("spin", 0) + pt.get("phase", 0), alpha)

    def shutdown_gpu_fx(self):
        gpu = getattr(self, "gpu_fx", None)
        if gpu is not None:
            try:
                gpu.stop()
            except Exception:
                pass

    def draw_vfx_overlay(self):
        """Screen-space polish: flash and subtle cinematic bars during major moments."""
        c = self.canvas
        if self.vfx_flash > 0 and self.vfx_flash_power > 0:
            p = min(0.75, self.vfx_flash_power)
            # Tk stipple gives an alpha-like wash without huge PhotoImages.
            c.create_rectangle(0, 0, self.bw, self.bh,
                               fill=mix(self.vfx_flash_col, C_BOARD, 0.70), outline="", stipple="gray12")
            if p > 0.16:
                c.create_oval(self.bw*0.5-self.bh*0.22, self.bh*0.5-self.bh*0.22,
                              self.bw*0.5+self.bh*0.22, self.bh*0.5+self.bh*0.22,
                              outline=mix(self.vfx_flash_col, "#ffffff", 0.5), width=2, stipple="gray50")

        # Boss fights get a very subtle cinematic frame, only while active.
        if getattr(self, "boss_active", lambda: False)() and getattr(self, "in_dungeon", False):
            h = min(24, self.bh * 0.035)
            c.create_rectangle(0, 0, self.bw, h, fill="#05060c", outline="")
            c.create_rectangle(0, self.bh-h, self.bw, self.bh, fill="#05060c", outline="")
