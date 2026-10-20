"""Signature boss skills - the abilities each Touhou character is known for.

Skills are small state machines kept in boss["sk"] (area attacks, beams, rings, lanes) and boss["move"] (dashes and
warps that take control of the boss). Every dangerous thing is telegraphed first (a warning phase) and the player's
2-second damage grace (HIT_IFRAMES) means one mistake costs one hit, never a shredding.

  Cirno    icicle_fall . frost_patch . perfect_freeze        (cold: slows you, bullets freeze mid-air then shatter)
  Marisa   star_dash . master_spark                          (broom dash with a star trail, charged sweeping mega-laser)
  Remilia  bat_warp . gungnir . vampire_kiss                 (vanishes into bats, telegraphed spear, draining lunge)
  Flandre  direct patterns in bosses.py                       (Lævateinn, Four of a Kind, Starbow Break, Q.E.D.)
  Reimu    fantasy_seal . barrier_ring . binding_net . warp  (locking orbs, closing amulet circle, seal lines, teleport)
"""
import math
import random

from ..config import HEAD_HIT
from ..data.bosses import BOSSES, SKILL_NAMES
from ..audio import play_sound

PI = math.pi
MASTER_COLS = ("#ff5d8f", "#ffd34d", "#7df9ff", "#b8ff8a", "#c78bff")


def _ang_diff(a, b):
    return abs((a - b + PI) % (2 * PI) - PI)


class BossSkillMixin:
    # ------------------------------------------------------------------ lifecycle
    def skills_reset(self):
        b = self.boss
        b.update(sk=[], sk_cd={}, move=None, hold=False, untarget=False, hidden=False, cast=None, pause_pat=False, super_used=False, super_t=0.0)

    def skills_phase_start(self):
        b = self.boss
        b["sk"] = []
        b["move"] = None
        b["hold"] = b["untarget"] = b["hidden"] = b["pause_pat"] = False
        b["super_used"] = False
        b["super_t"] = 0.0
        b["sk_cd"] = {}
        # Shorten the opening telegraph as the encounter progresses. Every phase still
        # gets a readable start, but later lives begin their second/third motif sooner.
        for name, _cd, first in BOSSES[b["idx"]]["phases"][b["phase"]]["skills"]:
            b["sk_cd"][name] = max(0.72, first - 0.28 * b["phase"])
        b["advanced_t"] = max(0.55, 1.30 - 0.16 * b["phase"])
        b["advanced_cycle"] = 0

    def _rng(self):
        return random.Random(int(self.time * 997) + self.boss["idx"] * 31 + self.boss["phase"] * 7)

    def cast_banner(self, skill):
        b = self.boss
        col = BOSSES[b["idx"]]["phases"][b["phase"]]["color"]
        b["cast"] = (SKILL_NAMES.get(skill, skill), col, self.time)
        b["power_t"] = max(b.get("power_t", 0.0), 0.72)
        self.float_text(b["x"], b["y"] - 1.8, SKILL_NAMES.get(skill, skill), col)

    # ------------------------------------------------------------------ main update
    def update_skills(self, dt, a):
        b = self.boss
        if b["state"] != "fight":
            return
        phase = BOSSES[b["idx"]]["phases"][b["phase"]]
        normal_casts = b.get("super_t", 0.0) <= 0.0

        # Final-phase Last Word is a one-time signature burst. It only starts
        # once the player has already burned through roughly half of the phase.
        if normal_casts:
            for name, cd, _first in phase["skills"]:
                b["sk_cd"][name] = b["sk_cd"].get(name, cd) - dt
                if b["sk_cd"][name] <= 0 and b["move"] is None and not b["hold"]:
                    if self.cast_skill(name, a):
                        late = 1.0 - 0.085 * min(4, b["phase"]) - 0.10 * b.get("rage", 0.0)
                        b["sk_cd"][name] = max(1.10, cd * late)
                    else:
                        b["sk_cd"][name] = 0.5

            super_name = phase.get("super")
            if super_name and not b.get("super_used", False):
                maxhp = max(1.0, float(phase["hp"]))
                threshold = float(phase.get("super_threshold", 0.55))
                if b["hp"] / maxhp <= threshold and b["move"] is None and not b["hold"]:
                    if self.cast_skill(super_name, a):
                        b["super_used"] = True
                        b["super_t"] = 4.8
                        b["pause_pat"] = True

        hx, hy = self.snake_points()[0]
        keep = []
        for s in b["sk"]:
            s["age"] += dt
            if s["age"] < s["life"]:
                keep.append(s)
                getattr(self, "_sk_" + s["k"])(s, dt, a, hx, hy)
        b["sk"] = keep

        if b.get("hold") and not any(s["k"] == "beam" for s in keep):
            b["hold"] = False

    def cast_skill(self, name, a):
        self.cast_banner(name)
        b = self.boss
        # A signature burst is consumed by the renderer for an extra character-specific pulse.
        b["power_t"] = max(b.get("power_t", 0.0), 0.75 + 0.1 * b.get("phase", 0))
        col = BOSSES[b["idx"]]["phases"][b["phase"]]["color"]
        if name == BOSSES[b["idx"]]["phases"][b["phase"]].get("super"):
            self.set_message("LAST WORD!  Survive the signature attack!")
            b["pause_pat"] = True
            self.bullets = []
        self.effects.append([b["x"], b["y"], self.time, "boss_cast", (b["idx"], name, col)])
        self.effects.append([b["x"], b["y"], self.time, "blast", (2.0 + 0.35 * b.get("phase", 0), col)])
        self.vfx_burst(b["x"], b["y"], col, 22, 6.0, 0.11, 0.85, "shard")
        self.vfx_arc(b["x"], b["y"], col, 1.5 + 0.3 * b.get("phase", 0), 0.8, 3.2, 0, 320)
        self.vfx_flash_screen(col, 0.15, 0.12)
        self.vfx_shake(0.20, 0.22)
        return getattr(self, "_cast_" + name)(a)

    # ------------------------------------------------------------------ movement overrides (dash / warp)
    def skill_motion(self, dt, a):
        """Returns True while a skill controls the boss position (normal sway is skipped)."""
        b = self.boss
        m = b["move"]
        if m is None:
            return False
        m["t"] += dt
        k = m["k"]
        if k in ("dash", "kiss"):
            if m["t"] < m["warn"]:
                b["flash"] = 0.05
            elif m["t"] < m["warn"] + m["dur"]:
                u = (m["t"] - m["warn"]) / m["dur"]
                u = u * u * (3 - 2 * u)
                px, py = b["x"], b["y"]
                b["x"] = m["x0"] + (m["x1"] - m["x0"]) * u
                b["y"] = m["y0"] + (m["y1"] - m["y0"]) * u
                if k == "dash":
                    m["acc"] += dt
                    while m["acc"] >= 0.07:
                        m["acc"] -= 0.07
                        ang = PI / 2 + random.uniform(-0.9, 0.9)
                        self.fire(b["x"], b["y"], ang, 1.6, 0.17, "#ffd34d", beh=dict(kind="star", accel=0.9))
                else:
                    hx, hy = self.snake_points()[0]
                    if not m.get("hit") and math.hypot(hx - b["x"], hy - b["y"]) < 1.15:
                        m["hit"] = True
                        self.hurt(20, "Remilia drained you")
                        b["hp"] = min(BOSSES[b["idx"]]["phases"][b["phase"]]["hp"], b["hp"] + 2)
                        self.float_text(b["x"], b["y"] - 1.2, "DRAIN", "#ff4f6d")
            elif m["t"] >= m["warn"] + m["dur"] + 0.35:
                if k == "kiss":
                    for n in range(16):
                        self.fire(b["x"], b["y"], n * PI / 8 + 0.2, 2.7, 0.17, "#ff4f6d", beh=dict(kind="orb"))
                b["move"] = None
                b["pause_pat"] = False
            return True
        if k == "warp":
            if m["stage"] == "out" and m["t"] >= m["out"]:
                m["stage"] = "in"
                b["x"], b["y"] = m["nx"], m["ny"]
                b["hidden"] = False
                b["untarget"] = False
                hx, hy = self.snake_points()[0]
                aim = math.atan2(hy - b["y"], hx - b["x"])
                kind, col = m["kind"], m["col"]
                for n in range(-3, 4):
                    self.fire(b["x"], b["y"], aim + n * 0.17, 4.3, 0.16, col, beh=dict(kind=kind))
                play_sound(m["snd"])
            elif m["stage"] == "in" and m["t"] >= m["out"] + 0.45:
                b["move"] = None
                b["pause_pat"] = False
            return True
        return False

    # ------------------------------------------------------------------ CIRNO
    def _cast_icicle_fall(self, a):
        rng, b = self._rng(), self.boss
        hx = self.snake_points()[0][0]
        xs = [min(a["x2"] - 1.5, max(a["x1"] + 1.5, hx + rng.uniform(-1.2, 1.2)))]
        for _ in range(60):
            if len(xs) >= 4 + b["phase"]:
                break
            x = rng.uniform(a["x1"] + 1.5, a["x2"] - 1.5)
            if all(abs(x - o) > 3.0 for o in xs):
                xs.append(x)
        b["sk"].append(dict(k="lane", age=0.0, life=2.0, warn=1.0, xs=xs, hit=False, a=a))
        play_sound("ice_attack")
        return True

    def _sk_lane(self, s, dt, a, hx, hy):
        if 1.0 <= s["age"] <= 1.6 and not s["hit"] and any(abs(hx - x) < 0.95 for x in s["xs"]):
            s["hit"] = True
            self.hurt(20, "Cirno's icicles struck you")

    def _cast_frost_patch(self, a):
        rng, b = self._rng(), self.boss
        hx, hy = self.snake_points()[0]
        for n in range(2):
            x = hx + rng.uniform(-3, 3) if n == 0 else rng.uniform(a["x1"] + 3, a["x2"] - 3)
            y = hy + rng.uniform(-2, 2) if n == 0 else rng.uniform(a["y1"] + 3, a["y2"] - 3)
            b["sk"].append(dict(k="patch", age=0.0, life=7.0, x=min(a["x2"] - 2, max(a["x1"] + 2, x)),
                y=min(a["y2"] - 2, max(a["y1"] + 2, y)), r=2.7))
        play_sound("freeze_ring")
        return True

    def _sk_patch(self, s, dt, a, hx, hy):
        if s["age"] > 0.6 and math.hypot(hx - s["x"], hy - s["y"]) < s["r"]:
            if self.slow_t <= 0.1:
                self.float_text(hx, hy - 0.8, "FROZEN", "#9fe8ff")
            self.slow_t = max(self.slow_t, 0.9)

    def _cast_perfect_freeze(self, a):
        b, rng = self.boss, self._rng()
        for n in range(30):
            ang = n * 2 * PI / 30 + rng.uniform(-0.04, 0.04)
            self.fire(b["x"], b["y"], ang, rng.uniform(2.0, 3.0), 0.19, "#bfe9ff",
                beh=dict(kind="orb", freeze=(rng.uniform(0.85, 1.35), 2.7)))
        play_sound("freeze_ring")
        return True

    # ------------------------------------------------------------------ MARISA
    def _cast_star_dash(self, a):
        b, rng = self.boss, self._rng()
        side = -1 if b["x"] > a["mx"] else 1
        tx = a["mx"] + side * rng.uniform(8.0, 11.0)
        ty = a["y1"] + rng.uniform(3.0, 7.0)
        b["move"] = dict(k="dash", t=0.0, warn=0.75, dur=0.6, x0=b["x"], y0=b["y"], x1=tx, y1=ty, acc=0.0)
        b["pause_pat"] = False
        play_sound("dash")
        return True

    def _cast_master_spark(self, a):
        b, rng = self.boss, self._rng()
        hx, hy = self.snake_points()[0]
        ang = math.atan2(hy - b["y"], hx - b["x"])
        b["hold"] = True
        b["sk"].append(dict(k="beam", age=0.0, life=2.75, warn=1.2, lock=0.7, follow=True, x=b["x"], y=b["y"], ang=ang,
            omega=rng.choice((-1, 1)) * 0.34, length=40.0, width=2.1, dmg=26, col="rainbow", track=True, hit=False))
        play_sound("master_spark")
        play_sound("bomb_marisa", volume=0.5)
        return True

    # ------------------------------------------------------------------ REMILIA
    def _cast_bat_warp(self, a, kind="knife", col="#ff4f6d", snd="knife_attack"):
        b, rng = self.boss, self._rng()
        for n in range(12):
            self.fire(b["x"], b["y"], n * PI / 6, 3.0, 0.14, col, beh=dict(kind=kind))
        for _ in range(60):
            nx = rng.uniform(a["x1"] + 4, a["x2"] - 4)
            ny = rng.uniform(a["y1"] + 2.5, a["y1"] + (a["y2"] - a["y1"]) * 0.45)
            if math.hypot(nx - b["x"], ny - b["y"]) > 6:
                break
        b["move"] = dict(k="warp", t=0.0, out=0.6, stage="out", nx=nx, ny=ny, kind=kind, col=col, snd=snd)
        b["hidden"] = b["untarget"] = b["pause_pat"] = True
        play_sound("skill")
        return True

    def _cast_gungnir(self, a):
        b = self.boss
        b["sk"].append(dict(k="spear", age=0.0, life=1.05, warn=0.95, lock=0.5, x=b["x"], y=b["y"], ang=0.0, fired=False))
        play_sound("boss_warning")
        return True

    def _sk_spear(self, s, dt, a, hx, hy):
        b = self.boss
        s["x"], s["y"] = b["x"], b["y"]
        if s["age"] < s["lock"]:
            s["ang"] = math.atan2(hy - s["y"], hx - s["x"])
        if s["age"] >= s["warn"] and not s["fired"]:
            s["fired"] = True
            self.fire(s["x"], s["y"], s["ang"], 15.0, 0.44, "#ff2040", beh=dict(kind="knife", dmg=28, big=2))
            for off in (-0.28, 0.28):
                self.fire(s["x"], s["y"], s["ang"] + off, 9.0, 0.16, "#ff9aa8", beh=dict(kind="knife"))
            play_sound("knife_attack")

    def _cast_vampire_kiss(self, a):
        b = self.boss
        hx, hy = self.snake_points()[0]
        tx = min(a["x2"] - 2, max(a["x1"] + 2, hx))
        ty = min(a["y2"] - 2, max(a["y1"] + 2, hy))
        b["move"] = dict(k="kiss", t=0.0, warn=0.85, dur=0.38, x0=b["x"], y0=b["y"], x1=tx, y1=ty, hit=False, lockdone=False)
        b["pause_pat"] = True
        play_sound("enemy_charge")
        return True

    # ------------------------------------------------------------------ NEW PHASE PATTERNS
    # Original patterns inspired by the characters' established danmaku motifs.
    # They are intentionally telegraphed and leave routes instead of creating
    # an unreactable wall of bullets.

    # CIRNO
    def _cast_frost_fan(self, a):
        b = self.boss
        hx, hy = self.snake_points()[0]
        aim = math.atan2(hy - b["y"], hx - b["x"])
        for k in range(7):
            off = (k - 3) * 0.11
            self.fire(b["x"], b["y"], aim + off, 3.1 + 0.10 * abs(k - 3), 0.15, "#dffcff",
                      beh=dict(kind="ice", freeze=(1.0 + 0.05 * k, 2.5)))
        for k in range(4):
            self.fire(b["x"], b["y"], -PI / 2 + (k - 1.5) * 0.25, 2.3, 0.14, "#9fe8ff",
                      beh=dict(kind="ice", accel=0.38))
        play_sound("ice_attack")
        return True

    def _cast_crystal_prism(self, a):
        b = self.boss
        rot = b["t"] * 0.42
        for ring in range(2):
            n = 12
            for k in range(n):
                ang = rot + ring * PI / n + k * 2 * PI / n
                self.fire(b["x"], b["y"], ang, 2.4 + ring * 0.55, 0.145, "#bfe9ff",
                          beh=dict(kind="ice", accel=0.22 + ring * 0.08))
        hx, hy = self.snake_points()[0]
        aim = math.atan2(hy - b["y"], hx - b["x"])
        for k in (-1, 0, 1):
            self.fire(b["x"], b["y"], aim + k * 0.20, 3.7, 0.16, "#ffffff",
                      beh=dict(kind="ice", freeze=(0.8, 2.1)))
        play_sound("freeze_ring")
        return True

    def _cast_frozen_stars(self, a):
        b = self.boss
        for k in range(16):
            ang = k * 2 * PI / 16 + b["t"] * 0.23
            self.fire(b["x"], b["y"], ang, 2.1 + (k % 4) * 0.24, 0.15, "#e8fbff",
                      beh=dict(kind="ice", accel=0.34, freeze=(1.0, 2.7)))
        hx, hy = self.snake_points()[0]
        aim = math.atan2(hy - b["y"], hx - b["x"])
        for k in range(4):
            self.fire(b["x"], b["y"], aim + (k - 1.5) * 0.15, 4.2, 0.13, "#ffffff",
                      beh=dict(kind="ice"))
        play_sound("ice_attack")
        return True

    def _cast_absolute_zero(self, a):
        b = self.boss
        b["hold"] = True
        for i, gap in enumerate((0.2, 2.1, 3.8, 5.2)):
            b["sk"].append(dict(k="ring", age=-0.32 * i, life=4.5, x=b["x"], y=b["y"],
                                speed=2.2 + 0.25 * i, thick=0.72, gap=gap, gapw=0.95,
                                hit=False, col="#dffcff"))
        for k in range(12):
            ang = k * 2 * PI / 12
            self.fire(b["x"], b["y"], ang, 2.1, 0.15, "#ffffff",
                      beh=dict(kind="ice", freeze=(0.65 + 0.05 * (k % 3), 2.2)))
        play_sound("freeze_ring")
        play_sound("laser_charge", volume=0.35)
        return True

    # MARISA
    def _cast_stardust_wheel(self, a):
        b = self.boss
        rot = b["t"] * 0.65
        for k in range(18):
            ang = rot + k * 2 * PI / 18
            self.fire(b["x"], b["y"], ang, 2.6 + 0.10 * (k % 3), 0.14, "#ffd34d",
                      beh=dict(kind="star", accel=0.16))
        hx, hy = self.snake_points()[0]
        aim = math.atan2(hy - b["y"], hx - b["x"])
        for k in (-2, -1, 0, 1, 2):
            self.fire(b["x"], b["y"], aim + k * 0.16, 4.0, 0.13, "#fff0a8",
                      beh=dict(kind="star"))
        play_sound("star_attack")
        return True

    def _cast_orrery_crossfire(self, a):
        b = self.boss
        for k in range(4):
            ang = b["t"] * (0.46 + k * 0.06) + k * PI / 2
            ox = b["x"] + math.cos(ang) * (2.8 + k * 0.4)
            oy = b["y"] + math.sin(ang) * (1.9 + k * 0.25)
            hx, hy = self.snake_points()[0]
            aim = math.atan2(hy - oy, hx - ox)
            for j in (-1, 0, 1):
                self.fire(ox, oy, aim + j * 0.12, 3.0 + 0.12 * k, 0.14, "#ffd34d",
                          beh=dict(kind="star"))
        play_sound("star_attack")
        return True

    def _cast_meteor_streak(self, a):
        b, rng = self.boss, self._rng()
        for k in range(12):
            side = -1 if k % 2 == 0 else 1
            x = a["x1"] + 1.5 if side < 0 else a["x2"] - 1.5
            y = a["y1"] + 1.0 + (k % 6) * 1.2
            ang = (0.30 if side < 0 else PI - 0.30) + rng.uniform(-0.08, 0.08)
            self.fire(x, y, ang, 3.0 + 0.12 * (k % 4), 0.15, "#fff0a8",
                      beh=dict(kind="star", accel=0.26))
        play_sound("star_attack")
        return True

    def _cast_final_master_spark(self, a):
        b, rng = self.boss, self._rng()
        hx, hy = self.snake_points()[0]
        ang = math.atan2(hy - b["y"], hx - b["x"])
        b["hold"] = True
        b["sk"].append(dict(k="beam", age=0.0, life=3.9, warn=1.35, lock=0.78, follow=True,
                            x=b["x"], y=b["y"], ang=ang, omega=rng.choice((-1, 1)) * 0.16,
                            length=50.0, width=3.1, dmg=28, col="rainbow", track=True, hit=False))
        for off in (-0.42, 0.42):
            self.fire(b["x"], b["y"], ang + off, 2.8, 0.14, "#ffd34d",
                      beh=dict(kind="star", accel=0.35))
        for k in range(10):
            self.fire(b["x"], b["y"], ang + PI + (k - 4.5) * 0.10, 2.2, 0.13, "#fff0a8",
                      beh=dict(kind="star"))
        play_sound("master_spark")
        play_sound("bomb_marisa", volume=0.75)
        return True

    # REMILIA
    def _cast_scarlet_fan(self, a):
        b = self.boss
        hx, hy = self.snake_points()[0]
        aim = math.atan2(hy - b["y"], hx - b["x"])
        for wave in range(2):
            for k in range(5):
                off = (k - 2) * (0.13 + 0.02 * wave)
                self.fire(b["x"], b["y"], aim + off, 4.4 - wave * 0.35, 0.15, "#ff4f6d",
                          beh=dict(kind="knife", split=(0.75 + 0.1 * wave, 2)))
        play_sound("knife_attack")
        return True

    def _cast_fate_chains(self, a):
        b = self.boss
        hx, hy = self.snake_points()[0]
        aim = math.atan2(hy - b["y"], hx - b["x"])
        for k in range(7):
            off = (k - 3) * 0.17
            self.fire(b["x"], b["y"], aim + off, 2.7 + 0.14 * abs(k - 3), 0.17, "#ff9aa8",
                      beh=dict(kind="knife", split=(1.05, 3)))
        for k in range(5):
            ang = k * PI / 2.5 + b["t"] * 0.3
            self.fire(b["x"], b["y"], ang, 2.1, 0.15, "#c91f45", beh=dict(kind="knife"))
        play_sound("knife_attack")
        return True

    def _cast_nightless_castle(self, a):
        b, rng = self.boss, self._rng()
        for i in range(2):
            b["sk"].append(dict(k="ring", age=-0.25 * i, life=4.0, x=b["x"], y=b["y"],
                                speed=2.55 + i * 0.5, thick=0.82, gap=rng.uniform(0, 2 * PI),
                                gapw=0.92, hit=False, col=("#ff4f6d", "#c91f45")[i]))
        for k in range(10):
            ang = k * 2 * PI / 10 + b["t"] * 0.55
            self.fire(b["x"], b["y"], ang, 3.2, 0.16, "#ff7a9c", beh=dict(kind="knife"))
        play_sound("knife_attack")
        return True

    def _cast_scarlet_destiny(self, a):
        b = self.boss
        hx, hy = self.snake_points()[0]
        aim = math.atan2(hy - b["y"], hx - b["x"])
        b["hold"] = True
        b["sk"].append(dict(k="spear", age=0.0, life=1.25, warn=1.0, lock=0.62,
                            x=b["x"], y=b["y"], ang=aim, fired=False))
        for i in range(3):
            b["sk"].append(dict(k="ring", age=-0.4 * i, life=4.8, x=b["x"], y=b["y"],
                                speed=2.0 + i * 0.38, thick=0.70, gap=aim + (i - 1) * 0.9,
                                gapw=0.85, hit=False, col=("#ff4f6d", "#ff9aa8", "#c91f45")[i]))
        for k in range(12):
            off = (k - 5.5) * 0.09
            self.fire(b["x"], b["y"], aim + off, 3.5, 0.15, "#ff4f6d",
                      beh=dict(kind="knife", split=(0.9, 2)))
        play_sound("laser_charge")
        play_sound("knife_attack")
        return True

    # FLANDRE
    def _cast_crumbling_edges(self, a):
        b, rng = self.boss, self._rng()
        for k in range(10):
            edge = k % 4
            if edge == 0:
                x, y = rng.uniform(a["x1"] + 2, a["x2"] - 2), a["y1"] + 0.8
            elif edge == 1:
                x, y = a["x2"] - 0.8, rng.uniform(a["y1"] + 2, a["y2"] - 2)
            elif edge == 2:
                x, y = rng.uniform(a["x1"] + 2, a["x2"] - 2), a["y2"] - 0.8
            else:
                x, y = a["x1"] + 0.8, rng.uniform(a["y1"] + 2, a["y2"] - 2)
            aim = math.atan2(a["my"] - y, a["mx"] - x) + rng.uniform(-0.20, 0.20)
            self.fire(x, y, aim, 2.5, 0.15, "#ff4f6d",
                      beh=dict(kind="orb", accel=0.30, split=(1.1, 3)))
        play_sound("spell_attack")
        return True

    def _cast_clone_prism(self, a):
        b = self.boss
        centers = ((-5.0, 0.8), (5.0, 0.8), (0.0, 4.2))
        cols = ("#ff6a6a", "#7df9ff", "#ffd34d")
        for idx, (ox, oy) in enumerate(centers):
            cx, cy = b["x"] + ox, b["y"] + oy
            for k in range(8):
                ang = b["t"] * (0.45 + idx * 0.10) + k * PI / 4
                self.fire(cx, cy, ang, 2.35 + idx * 0.22, 0.16, cols[idx],
                          beh=dict(kind="orb"))
        hx, hy = self.snake_points()[0]
        aim = math.atan2(hy - b["y"], hx - b["x"])
        self.fire(b["x"], b["y"], aim, 4.2, 0.14, "#ffffff", beh=dict(kind="orb"))
        play_sound("enemy_bomb")
        return True

    def _cast_rainbow_sawtooth(self, a):
        b = self.boss
        cols = ("#ff4f6d", "#ffd34d", "#7dff9a", "#7df9ff", "#8ab4ff", "#c78bff")
        for wave in range(3):
            side = -1 if wave % 2 == 0 else 1
            for k, col in enumerate(cols):
                u = k / (len(cols) - 1)
                x = a["x1"] + (a["x2"] - a["x1"]) * u
                y = a["y2"] - 0.6 - wave * 1.0
                ang = -PI / 2 + side * (0.20 + 0.15 * (u - 0.5))
                self.fire(x, y, ang, 2.4 + 0.30 * wave, 0.16, col,
                          beh=dict(kind="star", gravity=3.4))
        play_sound("star_attack")
        return True

    def _cast_clockwork_prism(self, a):
        b = self.boss
        rot = -b["t"] * 0.34
        for arm in range(4):
            center = rot + arm * PI / 2
            for k in range(4):
                ang = center + (k - 1.5) * 0.09
                self.fire(b["x"], b["y"], ang, 2.5 + 0.25 * k, 0.15,
                          ("#ff4f6d", "#ffd34d", "#7df9ff", "#c78bff")[arm],
                          beh=dict(kind="orb", bounce=True))
        play_sound("spell_attack")
        return True

    def _cast_destruction_495(self, a):
        b = self.boss
        for i, gap in enumerate((0.2, 1.8, 3.35, 4.95)):
            b["sk"].append(dict(k="ring", age=-0.28 * i, life=5.0, x=b["x"], y=b["y"],
                                speed=1.85 + 0.28 * i, thick=0.64, gap=gap, gapw=0.90,
                                hit=False, col=("#ff4f6d", "#ffd34d", "#7df9ff", "#c78bff")[i]))
        hx, hy = self.snake_points()[0]
        aim = math.atan2(hy - b["y"], hx - b["x"])
        for off in (-0.58, 0.58):
            b["sk"].append(dict(k="beam", age=0.0, life=3.8, warn=1.15, lock=0.6,
                                 follow=True, x=b["x"], y=b["y"], ang=aim + off,
                                 omega=-0.18 if off < 0 else 0.18, length=42.0, width=1.15,
                                 dmg=22, col="#ff7ad9", track=True, hit=False))
        for k in range(16):
            ang = k * 2 * PI / 16 + b["t"] * 0.38
            self.fire(b["x"], b["y"], ang, 2.6 + 0.05 * k, 0.14,
                      ("#ff4f6d", "#ffd34d", "#7dff9a", "#7df9ff", "#8ab4ff", "#c78bff")[k % 6],
                      beh=dict(kind="star", bounce=True))
        play_sound("enemy_bomb")
        play_sound("spell_attack")
        return True

    # REIMU
    def _cast_ofuda_spiral(self, a):
        b = self.boss
        for k in range(14):
            ang = b["t"] * 0.52 + k * 2 * PI / 14
            self.fire(b["x"], b["y"], ang, 2.45, 0.15, "#ff9ac8",
                      beh=dict(kind="amulet", home=dict(wait=0.65, rate=1.15, until=3.1, spd=3.4)))
        play_sound("amulet_attack")
        return True

    def _cast_barrier_shuffle(self, a):
        b, rng = self.boss, self._rng()
        for i in range(2):
            gap = rng.uniform(0, 2 * PI) + i * PI / 2
            n = 20
            for k in range(n):
                ang = k * 2 * PI / n
                if _ang_diff(ang, gap) < 0.48:
                    continue
                self.fire(b["x"], b["y"], ang, 2.2 + 0.25 * i, 0.16, "#ff7a9c",
                          beh=dict(kind="amulet"))
        play_sound("amulet_attack")
        return True

    def _cast_binding_cross(self, a):
        b = self.boss
        specs = (
            (a["x1"], a["my"], 0.0, 0.52),
            (a["x2"], a["my"], PI, -0.52),
            (a["mx"], a["y1"], PI / 2, -0.52),
            (a["mx"], a["y2"], -PI / 2, 0.52),
        )
        for x, y, ang, omega in specs:
            b["sk"].append(dict(k="beam", age=0.0, life=3.3, warn=1.0, lock=0.0,
                                 follow=False, x=x, y=y, ang=ang, omega=omega,
                                 length=24.0, width=0.85, dmg=18, col="#ffb347",
                                 track=False, hit=False))
        play_sound("spell_attack")
        return True

    def _cast_yin_yang_maze(self, a):
        b = self.boss
        for orb_idx in range(2):
            base = b["t"] * (0.55 if orb_idx == 0 else -0.42) + orb_idx * PI
            for k in range(8):
                ang = base + k * PI / 4
                self.fire(b["x"] + math.cos(base) * 2.5,
                          b["y"] + math.sin(base) * 1.8,
                          ang, 2.35 + 0.1 * orb_idx, 0.17, "#ffb347",
                          beh=dict(kind="amulet", bounce=True))
        play_sound("amulet_attack")
        return True

    def _cast_dream_of_hakurei(self, a):
        b = self.boss
        b["hold"] = True
        hx, hy = self.snake_points()[0]
        aim = math.atan2(hy - b["y"], hx - b["x"])
        for i in range(3):
            b["sk"].append(dict(k="ring", age=-0.34 * i, life=4.7, x=b["x"], y=b["y"],
                                speed=2.0 + 0.34 * i, thick=0.68,
                                gap=aim + (i - 1) * 0.82, gapw=0.86,
                                hit=False, col=("#c78bff", "#ff7a9c", "#ffd34d")[i]))
        for k in range(18):
            ang = aim + (k - 8.5) * 0.12
            self.fire(b["x"], b["y"], ang, 3.1 + 0.08 * (k % 3), 0.15, "#ffd0e0",
                      beh=dict(kind="amulet", home=dict(wait=0.75, rate=1.4, until=3.2, spd=3.7)))
        play_sound("amulet_attack")
        play_sound("bomb_reimu", volume=0.75)
        return True

    # ------------------------------------------------------------------ LEGACY GHOST SKILLS (kept for compatibility with old saves/mods)
    def _cast_ghost_veil(self, a):
        b, rng = self.boss, self._rng()
        hx, hy = self.snake_points()[0]
        aim = math.atan2(hy - b["y"], hx - b["x"])
        for n in range(2 + (b["phase"] > 0)):
            b["sk"].append(dict(k="ring", age=-0.7 * n, life=5.2, x=b["x"], y=b["y"], speed=3.5, thick=0.95,
                gap=aim + rng.choice((-1, 1)) * rng.uniform(0.9, 1.5), gapw=1.05, hit=False, col="#e6c8ff"))
        play_sound("spell_attack")
        return True

    def _sk_ring(self, s, dt, a, hx, hy):
        if s["age"] < 0:
            return
        r = s["age"] * s["speed"] + 0.6
        s["r"] = r
        if s["hit"]:
            return
        d = math.hypot(hx - s["x"], hy - s["y"])
        if abs(d - r) < s["thick"] / 2 + HEAD_HIT:
            if _ang_diff(math.atan2(hy - s["y"], hx - s["x"]), s["gap"]) > s["gapw"] / 2:
                s["hit"] = True
                self.hurt(18, "The ghostly veil claimed you")

    def _cast_fan_sweep(self, a):
        b, rng = self.boss, self._rng()
        sg = rng.choice((-1, 1))
        for n in range(3):
            b["sk"].append(dict(k="beam", age=0.0, life=4.4, warn=1.0, lock=0.0, follow=True, x=b["x"], y=b["y"],
                ang=n * 2 * PI / 3 + rng.uniform(0, 1), omega=sg * 0.5, length=22.0, width=1.0, dmg=16, col="#ffb7e8",
                track=False, hit=False, fan=True))
        play_sound("butterfly_attack")
        return True

    # ------------------------------------------------------------------ REIMU
    def _cast_fantasy_seal(self, a):
        b = self.boss
        play_sound("bomb_reimu", volume=0.6)
        n = 8 if b["phase"] < 3 else 6
        for k in range(n):
            ang = k * 2 * PI / n + b["t"]
            self.fire(b["x"] + math.cos(ang) * 1.6, b["y"] + math.sin(ang) * 1.6, ang, 1.2, 0.34,
                ("#ff3c5f", "#ffd34d", "#5d8bff", "#7dff9a")[k % 4], beh=dict(kind="orb", home=dict(wait=0.95, rate=1.75, until=3.8, spd=3.7)))
        play_sound("amulet_attack")
        return True

    def _cast_barrier_ring(self, a):
        hx, hy = self.snake_points()[0]
        rng = self._rng()
        gap = rng.uniform(0, 2 * PI)
        n = 24
        for k in range(n):
            ang = k * 2 * PI / n
            if _ang_diff(ang, gap) < 0.42:
                continue
            x, y = hx + math.cos(ang) * 6.5, hy + math.sin(ang) * 6.5
            if not (a["x1"] + 0.3 < x < a["x2"] - 0.3 and a["y1"] + 0.3 < y < a["y2"] - 0.3):
                continue
            self.fire(x, y, ang + PI, 1.7, 0.2, "#ffffff", beh=dict(kind="amulet", col="#ff5d8f"))
        play_sound("amulet_attack")
        return True

    def _cast_binding_net(self, a):
        b, rng = self.boss, self._rng()
        hx, hy = self.snake_points()[0]
        for n in range(5):
            if n == 0:
                px, py = hx, hy
            else:
                px, py = rng.uniform(a["x1"] + 3, a["x2"] - 3), rng.uniform(a["y1"] + 2, a["y2"] - 2)
            ang = rng.uniform(0, PI) if n else math.atan2(hy - a["my"], hx - a["mx"]) + PI / 2
            b["sk"].append(dict(k="beam", age=-0.12 * n, life=2.3 + 0.12 * n, warn=1.15, lock=0.0, follow=False,
                x=px - math.cos(ang) * 24, y=py - math.sin(ang) * 24, ang=ang, omega=0.0, length=48.0, width=0.95,
                dmg=20, col="#ff5d8f", track=False, hit=False, seal=True))
        play_sound("spell_attack")
        return True

    def _cast_warp(self, a):
        return self._cast_bat_warp(a, kind="amulet", col="#ff7a9c", snd="amulet_attack")


    # ------------------------------------------------------------------ CIRNO extras
    def _cast_diamond_blizzard(self, a):
        b, rng = self.boss, self._rng()
        for k in range(22):
            ang = k * 2 * PI / 22 + b["t"] * 0.35
            self.fire(b["x"], b["y"], ang, 2.4 + (k % 3) * 0.25, 0.16, "#dffcff", beh=dict(kind="ice", accel=0.65))
        play_sound("ice_attack")
        return True

    def _cast_ice_prison(self, a):
        b, rng = self.boss, self._rng()
        hx, hy = self.snake_points()[0]
        gap = math.atan2(hy-b["y"], hx-b["x"])
        for n in range(20):
            ang = n * 2*PI/20
            if _ang_diff(ang, gap) < 0.45:
                continue
            self.fire(b["x"], b["y"], ang, 1.8, 0.22, "#bfe9ff", beh=dict(kind="ice", freeze=(2.2, 2.9)))
        play_sound("freeze_ring")
        return True

    # ------------------------------------------------------------------ MARISA extras
    def _cast_orrery_sun(self, a):
        b = self.boss
        for k in range(3):
            ang = b["t"] * (0.55 + k*0.12) + k * 2*PI/3
            cx = b["x"] + math.cos(ang) * (3.0 + k)
            cy = b["y"] + math.sin(ang) * (2.0 + k*0.65)
            for j in range(7):
                aa = ang + j * 2*PI/7
                self.fire(cx, cy, aa, 2.8 + 0.2*k, 0.14, ("#ffd34d", "#ff7ad9", "#ffffff")[k], beh=dict(kind="star"))
        play_sound("star_attack")
        return True

    # ------------------------------------------------------------------ REMILIA extras
    def _cast_scarlet_shoot(self, a):
        b = self.boss
        hx, hy = self.snake_points()[0]
        aim = math.atan2(hy-b["y"], hx-b["x"])
        for sign in (-1,1):
            for k in range(5):
                ang = aim + sign * (k-2)*0.13
                self.fire(b["x"], b["y"], ang, 6.2 - k*0.35, 0.15, "#ff4f6d", beh=dict(kind="knife", split=(0.7,2)))
        play_sound("knife_attack")
        return True

    # ------------------------------------------------------------------ Flandre signature actions
    def _cast_laevateinn(self, a):
        b, rng = self.boss, self._rng()
        hx, hy = self.snake_points()[0]
        ang = math.atan2(hy-b["y"], hx-b["x"])
        b["sk"].append(dict(k="beam", age=0.0, life=2.5, warn=0.9, lock=0.4, follow=True, x=b["x"], y=b["y"], ang=ang,
            omega=rng.choice((-1,1))*0.75, length=50.0, width=2.2, dmg=30, col="#ff4f6d", track=True, hit=False))
        for k in (-1,1):
            self.fire(b["x"], b["y"], ang+k*0.42, 3.6, 0.17, "#ffd34d", beh=dict(kind="star"))
        play_sound("laser_charge")
        return True

    def _cast_four_of_a_kind(self, a):
        b, rng = self.boss, self._rng()
        offs = [(-6,-2),(6,-2),(-6,4),(6,4)]
        for idx,(ox,oy) in enumerate(offs):
            ex,ey=b["x"]+ox,b["y"]+oy
            aim = math.atan2(self.snake_points()[0][1]-ey, self.snake_points()[0][0]-ex)
            for k in range(5):
                self.fire(ex,ey,aim+(k-2)*0.13,2.7+idx*0.2,0.16,("#ff6a6a","#ffd34d","#7df9ff","#c78bff")[idx],beh=dict(kind="orb"))
        self.fire(b["x"], b["y"], b["t"]*0.6, 2.1, 0.2, "#ffffff", beh=dict(kind="orb", split=(1.0,4)))
        play_sound("enemy_bomb", volume=0.65)
        return True

    def _cast_starbow_break(self, a):
        b = self.boss
        cols=("#ff4f6d","#ffd34d","#7dff9a","#7df9ff","#8ab4ff","#c78bff")
        for k in range(12):
            u=k/11
            x=a["x1"]+u*(a["x2"]-a["x1"])
            y=a["y2"]-1.0-(math.sin(u*PI)*5.0)
            self.fire(x,y,-PI/2+(u-0.5)*0.65,2.4+u*1.8,0.17,cols[k%len(cols)],beh=dict(kind="star",gravity=5.0))
        play_sound("star_attack")
        return True

    def _cast_ripples_495(self, a):
        b, rng = self.boss, self._rng()
        hpmax = BOSSES[b["idx"]]["phases"][b["phase"]]["hp"]
        ratio = max(0.0, min(1.0, b["hp"]/hpmax))
        cx,cy=b["x"],b["y"]
        gap=rng.uniform(0,2*PI)
        count=22+int((1-ratio)*8)
        for k in range(count):
            ang=gap+k*2*PI/count
            self.fire(cx,cy,ang,2.0+(1-ratio)*1.7,0.16,("#f0d9ff","#ff6a8a","#8ab4ff")[k%3],beh=dict(kind="orb",bounce=True))
        play_sound("spell_attack")
        return True

    # ------------------------------------------------------------------ REIMU extras
    def _cast_yin_yang_orbit(self, a):
        b=self.boss
        for k in range(2):
            ang=b["t"]*(0.7+0.2*k)+k*PI
            for j in range(8):
                aa=ang+j*2*PI/8
                self.fire(b["x"]+math.cos(ang)*3.0*(1+k), b["y"]+math.sin(ang)*2.1*(1+k), aa, 2.6, 0.18, "#ffb347", beh=dict(kind="amulet", bounce=True))
        play_sound("amulet_attack")
        return True

    def _cast_innate_dream(self, a):
        b=self.boss
        hx,hy=self.snake_points()[0]
        aim=math.atan2(hy-b["y"],hx-b["x"])
        for ring_i in range(3):
            n=16+ring_i*4
            for k in range(n):
                ang=2*PI*k/n + b["t"]*(0.25+ring_i*0.14)
                self.fire(b["x"],b["y"],ang,2.0+0.35*ring_i,0.16,("#c78bff","#ff7a9c","#ffd34d")[ring_i],beh=dict(kind="amulet"))
            self.fire(b["x"],b["y"],aim+(ring_i-1)*0.22,5.0,0.14,"#ffffff",beh=dict(kind="amulet"))
        play_sound("amulet_attack")
        return True


    # ------------------------------------------------------------------ shared beam logic
    def _sk_beam(self, s, dt, a, hx, hy):
        b = self.boss
        if s["age"] < 0:
            return
        if s["follow"]:
            s["x"], s["y"] = b["x"], b["y"]
        if s["track"] and s["age"] < s["lock"]:
            s["ang"] = math.atan2(hy - s["y"], hx - s["x"])
        if s["age"] >= s["warn"]:
            if not s.get("started"):
                s["started"] = True
                play_sound("star_attack" if s["col"] == "rainbow" else "spell_attack")
            s["ang"] += s["omega"] * dt
            if not s["hit"]:
                dx, dy = hx - s["x"], hy - s["y"]
                al = dx * math.cos(s["ang"]) + dy * math.sin(s["ang"])
                pe = abs(-dx * math.sin(s["ang"]) + dy * math.cos(s["ang"]))
                if 0 <= al <= s["length"] and pe < s["width"] / 2 + HEAD_HIT:
                    s["hit"] = True
                    self.hurt(s["dmg"], "The beam burned you")
                    if s["col"] == "rainbow":
                        s["hit"] = True
        elif s["col"] == "rainbow":
            b["flash"] = 0.04
