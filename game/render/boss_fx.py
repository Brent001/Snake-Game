"""Rendering for boss signature skills, Touhou-style bullet sprites and the spell-card cast banner."""
import math

from ..config import C_BOARD, CELL
from ..data.bosses import BOSSES
from ..utils import mix
from ..world.layout import ARENAS
from .scenery import DSC

DIRECTIONAL = ("rice", "knife", "amulet", "ice", "bfly")
RAINBOW = ("#ff5d8f", "#ffd34d", "#7df9ff", "#b8ff8a", "#c78bff")


class BossFxMixin:
    # ------------------------------------------------------------------ bullets (baked sprites, 1 cheap image each)
    def draw_bullets(self):
        c, bank, t = self.canvas, self.bank, self.time
        cam_x, cam_y = self.cam_x, self.cam_y
        x_hi, y_hi = cam_x + self.vw + 1, cam_y + self.vh + 1
        k16 = 16 / (2 * math.pi)
        fr = int(t * 8)
        for bl in self.bullets:
            x, y = bl[0], bl[1]
            if x < cam_x - 1 or x > x_hi or y < cam_y - 1 or y > y_hi:
                continue
            beh = bl[6]
            kind, col = "orb", bl[5]
            if beh is not None:
                kind, col = beh.get("kind", "orb"), beh.get("col", col)
                if beh.get("dead"):
                    kind = "ring"
            travel = beh.get("travel", 0.0) if beh else 0.0
            brange = beh.get("range", 999.0) if beh else 999.0
            fade_start = brange * 0.78
            fade = 1.0 if travel <= fade_start else max(0.12, 1.0 - (travel - fade_start) / max(0.1, brange - fade_start))
            R = max(1, int(round(bl[4] * CELL / DSC * fade)))
            angi = int(round(math.atan2(bl[3], bl[2]) * k16)) % 16 if (kind in DIRECTIONAL and (bl[2] or bl[3])) else 0
            cx, cy = (x - cam_x) * CELL + CELL / 2, (y - cam_y) * CELL + CELL / 2
            if self.quality > 0:
                sp = math.hypot(bl[2], bl[3])
                trail = min(26.0, 5.0 + sp * 0.85)
                if sp > 0.01:
                    ux, uy = bl[2] / sp, bl[3] / sp
                    # Three broad passes create depth around a tiny pixel bullet.
                    for mul, width, fade in ((1.0, max(4, R*2), 0.72), (0.62, max(2, R), 0.45), (0.30, 1, 0.18)):
                        tx, ty = cx - ux * trail * mul, cy - uy * trail * mul
                        c.create_line(tx, ty, cx, cy, fill=mix(col, "#ffffff", fade), width=width, capstyle="round")
            c.create_image(cx, cy, image=bank.bullet(kind, col, R, angi, fr))
            c.create_oval(cx-max(1,R*0.38), cy-max(1,R*0.38), cx+max(1,R*0.38), cy+max(1,R*0.38), fill="#ffffff", outline="")
            if kind in ("star", "amulet"):
                c.create_text(cx, cy, text="+" if kind == "star" else "◇", fill="#ffffff", font=("Segoe UI", 6, "bold"))
        for bl in self.ebullets:
            x, y, _vx, _vy, r, col, _t = bl[:7]
            if not self.visible(x, y):
                continue
            cx, cy = self.center(x, y)

            # Enemy trap fields are encoded as ``field:#rrggbb`` so they can
            # share the normal projectile tuple/update logic.  They are an
            # area effect, not a bullet colour, so strip the tag before
            # rendering and draw the field as a pulsing ground circle.
            if isinstance(col, str) and col.startswith("field:"):
                field_col = col[6:]
                pulse = 0.55 + 0.45 * math.sin(self.time * 5.0 + x * 0.7 + y * 0.4)
                rr = r * CELL
                inner = rr * (0.82 + 0.10 * pulse)
                c.create_oval(cx - rr, cy - rr, cx + rr, cy + rr,
                              outline=field_col, width=2)
                c.create_oval(cx - inner, cy - inner, cx + inner, cy + inner,
                              outline=field_col, width=1, dash=(2, 4))
                continue

            beh = bl[7] if len(bl) >= 8 else None
            travel = beh.get("travel", 0.0) if beh else 0.0
            brange = beh.get("range", 999.0) if beh else 999.0
            fade_start = brange * 0.78
            fade = 1.0 if travel <= fade_start else max(0.12, 1.0 - (travel - fade_start) / max(0.1, brange - fade_start))
            draw_r = max(1, int(round(r * CELL / DSC * fade)))
            c.create_image(cx, cy, image=bank.bullet("orb", col, draw_r))

    # ------------------------------------------------------------------ boss power / arena VFX
    def _boss_phase_color(self):
        b = self.boss
        phases = BOSSES[b["idx"]]["phases"]
        return phases[min(b.get("phase", 0), len(phases) - 1)]["color"]

    def _boss_arena_box(self):
        b = self.boss
        a = ARENAS[b["idx"]]
        return a, self.px(a["x1"]), self.py(a["y1"]), self.px(a["x2"] + 1), self.py(a["y2"] + 1)

    def draw_boss_arena_vfx(self):
        """Dynamic effects that make the whole chamber react to the active boss.

        Kept procedural and sparse so old integrated GPUs do not get buried in
        thousands of canvas items. Floor effects are drawn before entities.
        """
        b = self.boss
        if not self.boss_active() or not getattr(self, "in_dungeon", False):
            return
        c, t = self.canvas, self.time
        a, x1, y1, x2, y2 = self._boss_arena_box()
        col = self._boss_phase_color()
        idx = b["idx"]
        p = b.get("phase", 0)
        rage = b.get("rage", 0.0)
        pulse = 0.5 + 0.5 * math.sin(t * (4.0 + p * 0.65))

        # Chamber border: a living spell boundary, stronger as the boss enrages.
        bw = 1 + int(pulse * (1 + rage * 2))
        c.create_rectangle(x1 + 4, y1 + 4, x2 - 4, y2 - 4,
            outline=mix(col, C_BOARD, 0.35 + 0.25 * (1 - pulse)), width=bw,
            dash=(10, 6) if pulse < 0.55 else (4, 5))
        c.create_rectangle(x1 + 10, y1 + 10, x2 - 10, y2 - 10,
            outline=mix(col, C_BOARD, 0.78), width=1, dash=(2, 10))

        cx, cy = self.center(a["mx"], a["my"])
        span = min((x2 - x1) * 0.42, (y2 - y1) * 0.42)

        # Shared central pressure wave: every phase makes the chamber breathe.
        rr = span * (0.35 + 0.20 * pulse)
        c.create_oval(cx - rr, cy - rr * 0.68, cx + rr, cy + rr * 0.68,
            outline=mix(col, C_BOARD, 0.78), width=1, dash=(2, 9))
        rr2 = span * (0.60 + 0.10 * math.sin(t * 2.0 + p))
        c.create_oval(cx - rr2, cy - rr2 * 0.68, cx + rr2, cy + rr2 * 0.68,
            outline=mix(col, C_BOARD, 0.88), width=1, dash=(6, 12))

        # Character-specific arena response.
        if idx == 0:  # Cirno: frost crystal lattice and freezing rings
            rot = t * 0.35
            for k in range(6):
                ang = rot + k * math.pi / 3
                ex = cx + span * 0.84 * math.cos(ang)
                ey = cy + span * 0.60 * math.sin(ang)
                c.create_line(cx, cy, ex, ey, fill=mix("#7df9ff", C_BOARD, 0.82), width=1, dash=(3, 8))
                r = 5 + 4 * pulse
                c.create_polygon(ex, ey-r, ex+r*0.55, ey, ex, ey+r, ex-r*0.55, ey,
                    outline="#bfe9ff", width=1)
            for k in range(4):
                yy = y1 + 28 + k * max(20, (y2-y1-56)/3)
                c.create_line(x1 + 18, yy, x2 - 18, yy, fill=mix("#9fe8ff", C_BOARD, 0.88), width=1, dash=(2 + k, 9))
        elif idx == 1:  # Marisa: rotating orrery / magic circles
            rot = -t * (0.55 + rage * 0.25)
            for rr0, dash in ((span * 0.42, (4, 8)), (span * 0.68, (2, 11))):
                c.create_oval(cx - rr0, cy - rr0 * 0.66, cx + rr0, cy + rr0 * 0.66,
                    outline=mix("#ffd34d", C_BOARD, 0.78), width=1, dash=dash)
            for k in range(8):
                ang = rot + k * math.pi / 4
                ex = cx + span * 0.76 * math.cos(ang)
                ey = cy + span * 0.55 * math.sin(ang)
                c.create_line(cx, cy, ex, ey, fill=mix("#ffea92", C_BOARD, 0.86), width=1)
                c.create_text(ex, ey, text="+", fill="#ffd34d", font=("Segoe UI", 8, "bold"))
        elif idx == 2:  # Remilia: blood-moon pulses and bat gates
            for k in range(3):
                rr0 = span * (0.32 + k * 0.20 + pulse * 0.035)
                c.create_arc(cx - rr0, cy - rr0 * 0.68, cx + rr0, cy + rr0 * 0.68,
                    start=(t * 38 + k * 50) % 360, extent=250,
                    outline=mix("#ff4f6d", C_BOARD, 0.70), width=2)
            for k in range(6):
                ang = t * 0.9 + k * math.pi / 3
                ex = cx + span * 0.82 * math.cos(ang)
                ey = cy + span * 0.57 * math.sin(ang)
                c.create_oval(ex-4, ey-3, ex+4, ey+3, outline="#ff8a9a", width=1)
        elif idx == 3:  # Flandre: fractured crystal cage
            rot = t * 0.8
            for k in range(8):
                ang = rot + k * math.pi / 4
                ex = cx + span * 0.86 * math.cos(ang)
                ey = cy + span * 0.58 * math.sin(ang)
                q = 6 + 4 * pulse
                c.create_polygon(ex, ey-q, ex+q*0.55, ey, ex, ey+q, ex-q*0.55, ey,
                    outline=mix("#ff4f6d", C_BOARD, 0.36), width=2)
                if k % 2 == 0:
                    c.create_line(ex, ey, cx, cy, fill=mix("#ff7ad9", C_BOARD, 0.90), width=1, dash=(2, 7))
            # Four broken corner seams imply the arena itself is being torn open.
            seam = 18 + int(5 * pulse)
            for sx, sy, ex, ey in ((x1, y1, x1+seam, y1+seam), (x2, y1, x2-seam, y1+seam),
                                   (x1, y2, x1+seam, y2-seam), (x2, y2, x2-seam, y2-seam)):
                c.create_line(sx, sy, ex, ey, fill="#ff4f6d", width=2)
        else:  # Reimu: barrier seal geometry
            rot = -t * 0.25
            for k in range(8):
                ang = rot + k * math.pi / 4
                ex = cx + span * 0.88 * math.cos(ang)
                ey = cy + span * 0.58 * math.sin(ang)
                c.create_line(cx, cy, ex, ey, fill=mix("#ff9ac8", C_BOARD, 0.83), width=1)
                c.create_text(ex, ey, text="◇", fill="#ffd0e0", font=("Segoe UI", 8, "bold"))
            rr0 = span * (0.50 + pulse * 0.04)
            c.create_arc(cx-rr0, cy-rr0*0.66, cx+rr0, cy+rr0*0.66,
                start=rot * 90, extent=150, outline="#ff9ac8", width=2)
            c.create_arc(cx-rr0, cy-rr0*0.66, cx+rr0, cy+rr0*0.66,
                start=rot * 90 + 180, extent=150, outline="#ff9ac8", width=2)

    def draw_boss_power_vfx(self):
        """Layered aura, cast charge, orbiting motes and phase bursts around the boss sprite."""
        b = self.boss
        if not self.boss_active() or not getattr(self, "in_dungeon", False) or b.get("hidden"):
            return
        c, t = self.canvas, self.time
        col = self._boss_phase_color()
        a = ARENAS[b["idx"]]
        cx, cy = self.center(b["x"], b["y"])
        idx, phase = b["idx"], b.get("phase", 0)
        rage = b.get("rage", 0.0)
        power = min(1.0, max(0.0, b.get("power_t", 0.0)))
        cast = b.get("cast")
        cast_age = (t - cast[2]) if cast else 99.0
        pulse = 0.5 + 0.5 * math.sin(t * (5.0 + phase * 0.75))
        core_r = CELL * (2.3 + phase * 0.25 + pulse * 0.28 + rage * 0.3)

        # Ground shadow + vertical aura column under the boss.
        c.create_oval(cx-core_r*1.08, cy-core_r*0.45, cx+core_r*1.08, cy+core_r*0.45,
            outline=mix(col, C_BOARD, 0.78), width=2, dash=(8, 7))
        for j in range(3):
            rr = core_r * (0.75 + j * 0.28 + 0.04 * pulse)
            c.create_oval(cx-rr, cy-rr*0.78, cx+rr, cy+rr*0.78,
                outline=mix(col, C_BOARD, 0.55 + j*0.12), width=1 + (j == 0),
                dash=(3 + j*2, 7 + j*2))

        # Rotating power spokes. These intensify while a spell is being cast.
        spokes = 8 if self.quality > 0 else 5
        spin = t * (0.85 + rage * 0.55) * (1 if idx % 2 == 0 else -1)
        for k in range(spokes):
            ang = spin + k * (2 * math.pi / spokes)
            inner = core_r * 0.85
            outer = core_r * (1.15 + 0.16 * pulse + 0.20 * power)
            c.create_line(cx + math.cos(ang)*inner, cy + math.sin(ang)*inner*0.78,
                          cx + math.cos(ang)*outer, cy + math.sin(ang)*outer*0.78,
                          fill=mix(col, C_BOARD, 0.28), width=2 if power > 0.35 else 1)

        # Character-specific orbital motif.
        orbit_n = 6 if self.quality > 0 else 4
        for k in range(orbit_n):
            ang = spin * 1.2 + k * 2 * math.pi / orbit_n
            rr = core_r * (1.08 + 0.12 * math.sin(t*3 + k))
            ox = cx + math.cos(ang) * rr
            oy = cy + math.sin(ang) * rr * 0.76
            sz = 3 + 1.5 * pulse
            if idx == 0:
                c.create_polygon(ox, oy-sz, ox+sz*0.6, oy, ox, oy+sz, ox-sz*0.6, oy, outline="#bfe9ff", width=1)
            elif idx == 1:
                c.create_text(ox, oy, text="★", fill="#ffd34d", font=("Segoe UI", 8, "bold"))
            elif idx == 2:
                c.create_oval(ox-sz, oy-sz*0.7, ox+sz, oy+sz*0.7, outline="#ff7a9c", width=1)
            elif idx == 3:
                c.create_polygon(ox, oy-sz, ox+sz, oy, ox, oy+sz, ox-sz, oy, outline="#ff4f6d", width=2)
            else:
                c.create_text(ox, oy, text="◇", fill="#ffd0e0", font=("Segoe UI", 8, "bold"))

        # Character signature VFX layer: cheap procedural shapes with stronger identity per boss.
        if idx == 0:  # Cirno - snowflakes + frozen mist rings
            for k in range(6 if self.quality > 0 else 3):
                ang = -t*0.55 + k*math.pi/3
                rr0 = core_r*(1.35 + 0.22*math.sin(t*2+k))
                px, py = cx+math.cos(ang)*rr0, cy+math.sin(ang)*rr0*0.72
                s0 = 3 + 2*pulse
                c.create_polygon(px, py-s0, px+s0, py, px, py+s0, px-s0, py, outline="#dffcff", width=2)
        elif idx == 1:  # Marisa - star motes orbiting a magical core
            for k in range(7 if self.quality > 0 else 4):
                ang = t*(0.8 + 0.08*k) + k*2*math.pi/7
                rr0 = core_r*(0.9 + 0.18*math.sin(t*3+k))
                px, py = cx+math.cos(ang)*rr0, cy+math.sin(ang)*rr0*0.7
                c.create_text(px, py, text="✦", fill="#fff0a8", font=("Segoe UI", 9, "bold"))
        elif idx == 2:  # Remilia - bat crescent gates + blood sparks
            for k in range(5 if self.quality > 0 else 3):
                ang=t*0.75+k*2*math.pi/5
                rr0=core_r*(1.15+0.18*pulse)
                px,py=cx+math.cos(ang)*rr0,cy+math.sin(ang)*rr0*0.72
                c.create_arc(px-7,py-5,px+7,py+5,start=25+k*20,extent=235,outline="#ff7a9c",width=2)
        elif idx == 3:  # Flandre - fracture shards and unstable center flashes
            for k in range(8 if self.quality > 0 else 5):
                ang=t*1.0+k*math.pi/4
                rr0=core_r*(1.0+0.35*pulse)
                px,py=cx+math.cos(ang)*rr0,cy+math.sin(ang)*rr0*0.75
                s0=4+3*pulse
                c.create_line(px-s0,py+s0,px,py-s0,px+s0,py+s0,fill="#ff4f6d",width=2)
        else:  # Reimu - rotating ofuda / seal marks
            for k in range(8 if self.quality > 0 else 5):
                ang=-t*0.55+k*math.pi/4
                rr0=core_r*(1.2+0.1*pulse)
                px,py=cx+math.cos(ang)*rr0,cy+math.sin(ang)*rr0*0.72
                c.create_rectangle(px-4,py-7,px+4,py+7,outline="#ffd0e0",width=1)
                c.create_text(px,py,text="◇",fill="#ff9ac8",font=("Segoe UI",7,"bold"))

        # One-time final-phase signature indicator. Keep it light enough for Tk
        # while making the Last Word feel materially different from a normal cast.
        super_t = b.get("super_t", 0.0)
        if super_t > 0:
            pulse2 = 0.5 + 0.5 * math.sin(t * 9.0)
            c.create_text(cx, cy - core_r * 1.45, text="LAST WORD",
                          fill=mix("#ffffff", col, 0.2 + 0.3 * pulse2),
                          font=("Segoe UI", 11, "bold"))
            if idx == 0:  # Cirno: expanding frost crystal
                rr = core_r * (1.25 + 0.25 * pulse2)
                c.create_polygon(cx, cy-rr, cx+rr*0.55, cy, cx, cy+rr,
                                 cx-rr*0.55, cy, outline="#dffcff", width=2)
            elif idx == 1:  # Marisa: star + beam core
                c.create_line(cx - core_r*1.15, cy, cx + core_r*1.15, cy,
                              fill="#fff4c2", width=2)
                c.create_text(cx, cy, text="✦", fill="#ffffff", font=("Segoe UI", 16, "bold"))
            elif idx == 2:  # Remilia: blood crescent
                rr = core_r * 1.12
                c.create_arc(cx-rr, cy-rr*0.72, cx+rr, cy+rr*0.72,
                             start=20 + t*55, extent=250, outline="#ff4f6d", width=3)
            elif idx == 3:  # Flandre: fracture spokes
                for k in range(4):
                    ang = t*1.2 + k*math.pi/2
                    l = core_r * (1.0 + 0.25*pulse2)
                    c.create_line(cx-math.cos(ang)*l, cy-math.sin(ang)*l,
                                  cx+math.cos(ang)*l, cy+math.sin(ang)*l,
                                  fill="#ff7ad9", width=2)
            else:  # Reimu: nested barrier seal
                rr = core_r * (1.18 + 0.10*pulse2)
                c.create_oval(cx-rr, cy-rr, cx+rr, cy+rr, outline="#ffd0e0", width=2, dash=(3, 7))

        # Cast charging halo + convergence particles.
        if cast_age < 1.1:
            u = max(0.0, min(1.0, cast_age / 1.1))
            rr = core_r * (0.5 + 0.9 * u)
            c.create_oval(cx-rr, cy-rr*0.78, cx+rr, cy+rr*0.78,
                outline=mix("#ffffff", col, 0.35), width=2 if u < 0.75 else 3,
                dash=(2, 5))
            for k in range(10 if self.quality > 0 else 6):
                ang = t * (2.2 + phase*0.2) + k * 2 * math.pi / (10 if self.quality > 0 else 6)
                rr0 = core_r * (1.9 - 1.1 * u)
                px, py = cx + math.cos(ang)*rr0, cy + math.sin(ang)*rr0*0.75
                c.create_oval(px-2, py-2, px+2, py+2, fill=mix(col, "#ffffff", 0.55), outline="")

        # Phase / entrance burst.
        if power > 0:
            rr = core_r * (1.0 + (1.0 - power) * 1.9)
            c.create_oval(cx-rr, cy-rr*0.78, cx+rr, cy+rr*0.78,
                outline=mix("#ffffff", col, power*0.35), width=max(1, int(4*power)))
            for k in range(10 if self.quality > 0 else 6):
                ang = t*1.4 + k*2*math.pi/10
                d0, d1 = core_r*0.8, rr
                c.create_line(cx+math.cos(ang)*d0, cy+math.sin(ang)*d0*0.75,
                              cx+math.cos(ang)*d1, cy+math.sin(ang)*d1*0.75,
                              fill=mix(col, "#ffffff", power*0.5), width=2)

    # ------------------------------------------------------------------ skills
    def draw_boss_skills(self):
        b = self.boss
        if b.get("state") not in ("fight", "dying"):
            return
        c, t = self.canvas, self.time
        bank = self.bank
        a = ARENAS[b["idx"]]
        col = BOSSES[b["idx"]]["phases"][min(b["phase"], len(BOSSES[b["idx"]]["phases"]) - 1)]["color"]
        for s in b.get("sk", ()):
            k, age = s["k"], s["age"]
            if age < 0:
                continue
            if k == "lane":
                warn = age < s["warn"]
                top, bot = self.py(a["y1"]), self.py(a["y2"] + 1)
                for x in s["xs"]:
                    l, r = self.px(x + 0.5 - 0.95), self.px(x + 0.5 + 0.95)
                    c.create_rectangle(l, top, r, bot, fill="#9fe8ff" if warn else "#e8fbff", stipple="gray25" if warn else "gray50",
                        outline="#9fe8ff", width=1, dash=(5, 4) if warn else ())
                    if warn:
                        c.create_line((l + r) / 2, top, (l + r) / 2, bot, fill="#e8fbff", dash=(2, 8))
                    else:
                        img = bank.bullet("ice", "#7df9ff", 6, 4)
                        for n in range(5):
                            yy = top + (((age - s["warn"]) * 24 + n * 6.5) % (a["y2"] - a["y1"] + 1)) * CELL
                            c.create_image((l + r) / 2 + (n % 2 - 0.5) * 16, yy, image=img)
            elif k == "patch":
                x, y = self.center(s["x"], s["y"])
                r = s["r"] * CELL * (min(1.0, age / 0.6))
                fade = s["age"] > s["life"] - 1.0
                c.create_oval(x - r, y - r, x + r, y + r, fill="#7df9ff", stipple="gray12" if fade else "gray25", outline="#bfeeff",
                    width=2, dash=(6, 5))
                c.create_oval(x - r * 0.55, y - r * 0.55, x + r * 0.55, y + r * 0.55, outline="#e8fbff", width=1, dash=(2, 7))
            elif k == "ring":
                x, y = self.center(s["x"], s["y"])
                r = s.get("r", 0.6) * CELL
                gdeg = -math.degrees(s["gap"])
                gw = math.degrees(s["gapw"])
                start, ext = gdeg + gw / 2, 360 - gw
                c.create_arc(x - r, y - r, x + r, y + r, start=start, extent=ext, style="arc", outline="#7a4aa8", width=int(s["thick"] * CELL) + 4)
                c.create_arc(x - r, y - r, x + r, y + r, start=start, extent=ext, style="arc", outline=s["col"], width=int(s["thick"] * CELL * 0.6))
                c.create_arc(x - r, y - r, x + r, y + r, start=start, extent=ext, style="arc", outline="#ffffff", width=2)
            elif k == "beam":
                self._draw_beam(s, col)
            elif k == "spear":
                x, y = self.center(s["x"], s["y"])
                L = 30 * CELL
                ex, ey = x + math.cos(s["ang"]) * L, y + math.sin(s["ang"]) * L
                locked = age >= s["lock"]
                c.create_line(x, y, ex, ey, fill="#ff2040" if locked else "#ff9aa8", width=3 if locked else 1, dash=() if locked else (6, 5))
        m = b.get("move")
        if m and m["k"] in ("dash", "kiss") and m["t"] < m["warn"]:
            x, y = self.center(b["x"], b["y"])
            tx, ty = self.center(m["x1"], m["y1"])
            c.create_line(x, y, tx, ty, fill="#ff4f6d" if m["k"] == "kiss" else "#ffd34d", width=2, dash=(7, 5))
            r = CELL * (0.6 + 0.5 * (m["t"] / m["warn"]))
            c.create_oval(tx - r, ty - r, tx + r, ty + r, outline="#ffffff", width=2)

    def _draw_beam(self, s, col):
        c = self.canvas
        warn = s["age"] < s["warn"]
        ox, oy = self.center(s["x"], s["y"])
        ang = s["ang"]
        ca, sa = math.cos(ang), math.sin(ang)
        L = min(s["length"], 48) * CELL
        ex, ey = ox + ca * L, oy + sa * L
        bc = s["col"]
        if bc == "rainbow":
            bc = RAINBOW[int(self.time * 9) % len(RAINBOW)]
        if warn:
            u = s["age"] / s["warn"]
            c.create_line(ox, oy, ex, ey, fill=mix(C_BOARD, bc, 0.4 + 0.5 * u), width=1 + int(2 * u), dash=(8, 6))
            if s["col"] == "rainbow":                   # charging orb
                r = CELL * (0.3 + 1.1 * u)
                c.create_oval(ox - r, oy - r, ox + r, oy + r, fill=bc, outline="#ffffff", width=2)
            return
        w = s["width"] * CELL
        nx, ny = -sa * w / 2, ca * w / 2

        def quad(f, **kw):
            c.create_polygon(ox + nx * f, oy + ny * f, ex + nx * f, ey + ny * f, ex - nx * f, ey - ny * f, ox - nx * f, oy - ny * f, **kw)
        quad(1.25, fill=bc, stipple="gray50", outline="")
        quad(0.8, fill=bc, outline="")
        quad(0.38, fill="#ffffff", outline="")
        if s["col"] == "rainbow":
            r = w * 0.75
            c.create_oval(ox - r, oy - r, ox + r, oy + r, fill=bc, outline="#ffffff", width=3)

    # ------------------------------------------------------------------ vanish effect + cast banner
    def draw_boss_hidden(self, cx, cy):
        bank, t = self.bank, self.time
        for n in range(6):
            ang = t * 6 + n * math.pi / 3
            rr = CELL * (1.0 + 0.6 * math.sin(t * 7 + n))
            self.canvas.create_image(cx + math.cos(ang) * rr, cy + math.sin(ang) * rr * 0.7,
                image=bank.particle("bat", int(t * 10 + n) % 3))

    def draw_cast_banner(self):
        b = self.boss
        cast = b.get("cast")
        if not cast or not self.boss_active():
            return
        name, col, t0 = cast
        age = self.time - t0
        if age > 1.6:
            return
        c = self.canvas
        y = 76 + (0 if age < 0.15 else (age - 0.15) * 4)
        fade = max(0.0, min(1.0, (1.6 - age) / 0.5))
        bg = C_BOARD
        c.create_text(self.bw // 2 + 2, y + 2, text=name, fill=mix(bg, "#000000", fade), font=("Segoe UI", 18, "bold italic"))
        c.create_text(self.bw // 2, y, text=name, fill=mix(bg, col, fade), font=("Segoe UI", 18, "bold italic"))
