"""Boss arenas: door locking, encounter trigger, movement, spell-card bullet patterns and phases."""
import math
import random

from ..config import C_CYAN, C_GOLD, HEAD_HIT, MAX_BULLETS, NUM_FRAGMENTS, BOSS_PRESSURE_MIN, BOSS_PRESSURE_MAX

PI = math.pi

def _ang_diff(a, b):
    return abs((a - b + math.pi) % (2 * math.pi) - math.pi)

from ..data.bosses import BOSSES
from ..data.elements import ECOL, REACT
from ..world.layout import ARENAS, PORTAL_CELLS, arena_at
from ..world.level import NODES, WALLS
from ..audio import play_sound
from .boss_skills import BossSkillMixin


class BossMixin(BossSkillMixin):
    def boss_active(self):
        return self.boss["state"] in ("banner", "fight", "dying")

    def is_locked(self, cell):
        i = PORTAL_CELLS.get(cell)
        if i is not None:                                   # overworld portal: Reimu's gate needs all fragments
            return ARENAS[i]["final"] and self.collected < NUM_FRAGMENTS
        for i, a in enumerate(ARENAS):
            if cell in a["door"] and self.boss_active() and self.boss["idx"] == i:
                return True                                 # the dungeon exit is sealed during the fight
        return False

    # ------------------------------------------------------------------ portals (overworld <-> boss dungeon)
    @staticmethod
    def lay_snake(head, back, length, half_w, free):
        """Snake body laid out as a compact serpentine behind `head` (back = unit vector from head toward the tail)."""
        bx, by = back
        sx, sy = abs(by), abs(bx)                          # sideways unit vector

        def at(depth, off):
            return (head[0] + bx * depth + sx * off, head[1] + by * depth + sy * off)

        k = 2
        cells = [at(d, 0) for d in range(0, k + 1)]        # head + a straight neck
        cells += [at(k, o) for o in range(-1, -half_w - 1, -1)]
        r = 1
        while len(cells) < length and r < 9:
            offs = range(-half_w, half_w + 1) if r % 2 else range(half_w, -half_w - 1, -1)
            cells += [at(k + r, o) for o in offs]
            r += 1
        out = []
        for c in cells[:length]:
            if c in WALLS or c in NODES or c in out:
                break
            out.append(c)
        return out

    def teleport_snake(self, head, direction, back, half_w):
        length = len(self.snake)
        cells = self.lay_snake(head, back, length, half_w, None)
        if len(cells) < length:
            self.grow_q += length - len(cells)             # short of room: the missing segments regrow
        self.snake, self.prev = cells, list(cells)
        self.direction = direction
        self.queue = []
        self.head_angle = math.atan2(direction[1], direction[0])
        self.acc, self.alpha = 0.0, 1.0
        self.blocked = False
        self.dash_t = 0.0
        self.bullets, self.ebullets, self.shots = [], [], []
        self.effects.append([head[0], head[1], self.time, "save"])
        self.update_camera(0, instant=True)

    def check_portal(self, cell):
        """Called after every snake step.  True when the snake was teleported."""
        i = PORTAL_CELLS.get(cell)
        if i is not None:
            self.enter_arena(i)
            return True
        for i, a in enumerate(ARENAS):
            if cell in a["door"]:
                self.leave_arena(i)
                return True
        return False

    def enter_arena(self, i):
        a = ARENAS[i]
        ex, ey = a["entry"]
        play_sound("portal_enter")
        play_sound("descend", volume=0.6)
        self.teleport_snake((ex, ey - 4), (0, -1), (0, 1), 12)
        self.portal_fx = {"active": True, "mode": "enter", "t": 0.0, "dur": 1.0,
                          "color": BOSSES[i]["phases"][0]["color"], "label": BOSSES[i]["name"]}
        self.lmb_held = self.run_held = False
        self.update_hud()
        if i in self.defeated:
            self.set_message(f"{BOSSES[i]['name']}'s dungeon (cleared)    |    The exit door is at the bottom of the hall")
        self.check_boss_trigger()

    def leave_arena(self, i):
        a = ARENAS[i]
        ox, oy = a["ow"]
        play_sound("portal_exit")
        play_sound("door_open", volume=0.6)
        self.boss["hazards"] = []
        self.teleport_snake((ox, oy + 10), (0, 1), (0, -1), 8)
        self.portal_fx = {"active": True, "mode": "exit", "t": 0.0, "dur": 1.0,
                          "color": BOSSES[i]["phases"][0]["color"], "label": "OVERWORLD"}
        self.lmb_held = self.run_held = False
        self.update_hud()
        self.set_message("You stepped back through the portal    |    The overworld")

    def check_boss_trigger(self):
        if self.boss_active():
            return
        for i, a in enumerate(ARENAS):
            if i in self.defeated or (a["final"] and self.collected < NUM_FRAGMENTS):
                continue
            if all(a["x1"] <= x <= a["x2"] and a["y1"] <= y <= a["y2"] for x, y in self.snake):
                self.start_boss(i)
                return

    def start_boss(self, i):
        a, b = ARENAS[i], self.boss
        b.update(state="banner", idx=i, phase=0, hp=BOSSES[i]["phases"][0]["hp"], timer=2.2, t=0.0,
            x=a["mx"], y=a["y1"] + 4.2, flash=0.0, spin=0.0, dir=1, flip=False, mech_t=0.0, mech_cd=5.5, mech_kind=0, hazards=[], death_t=0.0,
            aura=None, aura_t=0.0, aura_g=0.0, power_t=1.2, slow_t=0.0, stagger_t=0.0, shock_t=0.0, res_break_t=0.0, burn_t=0.0, quicken_t=0.0, burn_dps=0.0,
            aggression=0.0, pressure_t=2.8, greed_t=0.0, pattern_cycle=0,
            brain_t=0.0, motion_t=0.0, motion_x=a["mx"], motion_y=a["y1"]+4.5,
            motion_phase=0.0, last_player_x=a["mx"], last_player_y=a["y2"] - 5,
            advanced_t=1.05, advanced_cycle=0, move_burst=0.0)
        self.skills_reset()
        self.setup_boss_supplies(a)
        self.ammo = min(getattr(self, "energy_cap", 9), max(self.ammo, 4))
        self.timers = {}
        self.bullets = []
        self.ebullets = []
        self.update_hud()
        self.set_message("The arena door sealed shut    |    Dash through bullets - shoot or strike the guardian")
        play_sound("boss_start")
        play_sound("challenge", volume=0.6)
        self.play_zone_music()

    def every(self, key, interval, dt):
        self.timers[key] = self.timers.get(key, 0.0) + dt
        n = 0
        while self.timers[key] >= interval:
            self.timers[key] -= interval
            n += 1
        return n

    def setup_boss_supplies(self, a):
        """Finite encounter safety net: supplies are placed once and never respawn."""
        food_cells = [
            (int(a["x1"] + 5), int(a["y1"] + 5)),
            (int(a["x2"] - 5), int(a["y1"] + 5)),
            (int(a["mx"]), int(a["my"] + 5)),
        ]
        charge_cells = [
            (int(a["x1"] + 4), int(a["my"])),
            (int(a["x2"] - 4), int(a["my"])),
        ]
        for cell in food_cells:
            if cell not in self.snake and cell not in self.foods and cell not in self.nodes:
                self.foods[cell] = "food"
        for cell in charge_cells:
            if cell not in self.snake and cell not in self.charges and cell not in self.nodes:
                self.charges.add(cell)
        self.boss["supply_food"] = len(food_cells)
        self.boss["supply_energy"] = len(charge_cells)
        self.set_message("Arena supplies: 3 FOOD  •  2 PULSE CHARGES  •  no respawns")

    def fire(self, x, y, ang, speed, radius, color, beh=None):
        """Spawn a boss bullet. `beh` (optional dict) selects the sprite (`kind`) and special behaviour:
        freeze=(t_stop, t_thaw), ghost=(period, duty), home=dict(wait, rate, until, spd), accel=k, split=(t, n), dmg=n."""
        if len(self.bullets) < MAX_BULLETS:
            rage = float(self.boss.get("rage", 0.0)) if self.boss.get("state") == "fight" else 0.0
            phase = float(self.boss.get("phase", 0)) if self.boss.get("state") == "fight" else 0.0
            # Small phase ramp: later lives are faster, but never enough to turn a
            # readable opening into an unavoidable bullet wall.
            speed *= (1.0 + 0.035 * phase + 0.14 * rage)
            self.bullets.append([x, y, math.cos(ang) * speed, math.sin(ang) * speed, radius, color, beh])

    def update_boss(self, dt):
        b = self.boss
        if not self.boss_active():
            return
        a = ARENAS[b["idx"]]
        b["t"] += dt
        b["flash"] = max(0.0, b["flash"] - dt)
        b["slow_t"] = max(0.0, b.get("slow_t", 0.0) - dt)
        b["stagger_t"] = max(0.0, b.get("stagger_t", 0.0) - dt)
        b["shock_t"] = max(0.0, b.get("shock_t", 0.0) - dt)
        b["res_break_t"] = max(0.0, b.get("res_break_t", 0.0) - dt)
        b["burn_t"] = max(0.0, b.get("burn_t", 0.0) - dt)
        b["quicken_t"] = max(0.0, b.get("quicken_t", 0.0) - dt)
        b["power_t"] = max(0.0, b.get("power_t", 0.0) - dt)
        if b.get("super_t", 0.0) > 0:
            b["super_t"] = max(0.0, b.get("super_t", 0.0) - dt)
            if b["super_t"] <= 0:
                b["pause_pat"] = False
                b["hold"] = False
        if b.get("aura_t", 0.0) > 0:
            b["aura_t"] -= dt
            if b["aura_t"] <= 0:
                b["aura"], b["aura_g"] = None, 0.0
        if b.get("burn_t", 0.0) > 0 and b["state"] == "fight":
            b["burn_dps"] = 4.0 + self.S.get("burn", 0.0)
            b["hp"] -= b["burn_dps"] * dt
            if b["hp"] <= 0:
                self.phase_clear(); return
        if b.get("shock_t", 0.0) > 0 and b["state"] == "fight" and int(b["t"] * 8) != int((b["t"] - dt) * 8):
            b["hp"] -= max(1.0, self.trans_dmg(0.35))
            if b["hp"] <= 0:
                self.phase_clear(); return
        if b["state"] == "fight":
            maxhp = BOSSES[b["idx"]]["phases"][b["phase"]]["hp"]
            b["rage"] = max(0.0, min(1.0, 1.0 - b["hp"] / maxhp))
            b["aggression"] = min(1.0, 0.25 + 0.70 * b["rage"] + 0.08 * b.get("phase", 0))
            b["pressure_t"] = max(0.0, b.get("pressure_t", 0.0) - dt)
            b["greed_t"] = max(0.0, b.get("greed_t", 0.0) - dt)
        # Arena mechanics: telegraphed danger zones that force movement instead of pure bullet dodging.
        for hz in b.get("hazards", []):
            hz["age"] += dt
        b["hazards"] = [hz for hz in b.get("hazards", []) if hz["age"] < hz["life"]]
        if b["state"] == "fight":
            b["mech_cd"] -= dt
            if b["mech_cd"] <= 0:
                self.spawn_arena_mechanic(a)
                b["mech_cd"] = max(8.5, 11.0 - b["phase"] * 0.6 - b.get("rage", 0.0) * 1.5)     # keep arena mechanics secondary to spell-card patterns
            hx, hy = self.snake_points()[0]
            for hz in b["hazards"]:
                if hz["age"] < hz["warn"] or hz.get("hit", False):
                    continue
                hit = False
                if hz["kind"] == "sweep":
                    dx, dy = hx - hz["x"], hy - hz["y"]
                    dist = math.hypot(dx, dy)
                    if dist < 9.0:
                        beam_ang = hz.get("ang", 0.0) + self.time * 0.85
                        da = abs((math.atan2(dy, dx) - beam_ang + math.pi) % (2 * math.pi) - math.pi)
                        hit = da < 0.10 or abs(da - math.pi) < 0.10
                else:
                    hit = math.hypot(hx - hz["x"], hy - hz["y"]) <= hz["r"]
                if hit:
                    hz["hit"] = True
                    self.hurt(16 + 5 * b["phase"] + 5 * b.get("rage", 0.0), "The arena hazard struck you")
                    break
        if b["state"] == "dying":
            b["death_t"] -= dt
            b["x"] += math.sin(b["t"] * 8) * dt * 0.6
            b["y"] -= dt * 0.7
            if b["death_t"] <= 0:
                self.finish_boss_defeat()
            return
        t, p = b["t"], b["phase"]
        top = a["y1"] + 4.5
        if b["state"] == "fight":
            self.update_skills(dt, a)
            if self.skill_motion(dt, a):
                return                                  # a dash / warp is in control of the boss this frame
        if b["state"] == "banner":
            tx, ty = a["mx"], top
            b["motion_x"], b["motion_y"] = tx, ty
        elif b.get("hold"):
            tx, ty = b["x"], b["y"]                     # channeling (Master Spark): stand still
        else:
            # Advanced authored movement: bosses never hard-snap or continuously chase.
            # They choose short tactical destinations, then travel toward them at a
            # bounded speed. Each character uses a distinct movement language while
            # the danmaku remains the primary threat.
            b["brain_t"] = b.get("brain_t", 0.0) + dt
            b["motion_t"] = b.get("motion_t", 0.0) - dt
            hx, hy = self.snake_points()[0]
            if b["motion_t"] <= 0.0:
                # Re-plan frequently so the boss sweeps through the arena instead of
                # drifting in one long, predictable loop. Destinations remain bounded
                # and movement itself is always continuous (never a teleport).
                b["motion_t"] = max(0.36, 0.60 - 0.035 * p - 0.10 * b.get("rage", 0.0))
                style_t = b["brain_t"] * (1.05 + 0.10 * p)
                idx = b["idx"]
                if idx == 0:  # CIRNO: playful ice-dance, side swaps and small altitude changes
                    lane = -1 if int(style_t * 0.72) % 2 == 0 else 1
                    tx = a["mx"] + lane * (4.0 + 0.35 * p) + 2.0 * math.sin(style_t * 1.9)
                    ty = top + 1.4 + 1.1 * (0.5 + 0.5 * math.sin(style_t * 1.3))
                elif idx == 1:  # MARISA: wide sweeps with controlled player-lane bias
                    sweep = math.sin(style_t * 0.85 + 0.35 * p)
                    tx = a["mx"] + sweep * (6.0 + 0.45 * p) + (hx - a["mx"]) * 0.26
                    ty = top + 2.0 + 0.9 * math.cos(style_t * 1.2)
                elif idx == 2:  # REMILIA: elegant corner-to-corner fencing lanes
                    side = -1 if int(style_t * 0.58) % 2 == 0 else 1
                    tx = a["mx"] + side * (5.0 + 0.25 * p) + (hx - a["mx"]) * 0.18
                    ty = top + 2.8 + 1.15 * math.sin(style_t * 1.05)
                elif idx == 3:  # FLANDRE: unstable triangular/lemniscate orbit
                    tx = a["mx"] + 6.1 * math.sin(style_t * 0.92) + 1.4 * math.sin(style_t * 2.4)
                    ty = top + 2.2 + 2.1 * abs(math.sin(style_t * 0.74))
                else:  # REIMU: measured shrine sweep with a modest tracking bias
                    tx = a["mx"] + 4.8 * math.sin(style_t * 0.64 + 0.7) + (hx - a["mx"]) * 0.30
                    ty = top + 2.4 + 1.3 * math.cos(style_t * 0.91)
                b["motion_x"] = max(a["x1"] + 3.2, min(a["x2"] - 3.2, tx))
                b["motion_y"] = max(top, min(a["y2"] - 4.0, ty))
            tx, ty = b.get("motion_x", a["mx"]), b.get("motion_y", top + 2.0)
        # Fast, continuous movement: the boss should feel alive and dangerous, but
        # it still travels through the space rather than snapping to a destination.
        speed = 9.0 + 0.90 * p + 1.65 * b.get("rage", 0.0)
        speed += (0.9, 1.35, 1.55, 1.10, 0.8)[b["idx"]]
        if b.get("move_burst", 0.0) > 0:
            speed *= 1.18
            b["move_burst"] = max(0.0, b["move_burst"] - dt)
        dx, dy = tx - b["x"], ty - b["y"]
        dist = math.hypot(dx, dy)
        if dist > 1e-6:
            step = min(dist, speed * dt)
            move_k = step / dist
            if b.get("slow_t", 0.0) > 0 or b.get("stagger_t", 0.0) > 0:
                move_k *= 0.45 if b.get("stagger_t", 0.0) > 0 else 0.68
            b["x"] += dx * move_k
            b["y"] += dy * move_k
        if b["state"] == "banner":
            b["timer"] -= dt
            if b["timer"] <= 0:
                b["state"] = "fight"
                b["t"] = 0.0
                b["mech_cd"] = 8.0
                self.timers = {}
                self.skills_phase_start()
        elif not b.get("pause_pat"):
            # Touhou-style rhythm: authored spell/normal patterns plus a restrained
            # character-specific aimed interlude. The interlude is intentionally sparse
            # so the fight gets harder through pattern layering, not bullet spam.
            self.run_pattern(dt)
            self.run_advanced_pattern(dt, a)
            self.run_pressure_pattern(dt, a)

    def run_advanced_pattern(self, dt, a):
        """Fast character-specific interleaves layered between the authored spell-card skills.

        Touhou's boss attacks often alternate a recognizable normal cadence with a more
        elaborate spell pattern. This keeps that rhythm while making each guardian feel
        mechanically distinct: Cirno freezes/redirects ice, Marisa uses fast star streams
        and laser sweeps, Remilia uses aimed trail bullets and alternating fans, Flandre
        mixes corner fire with bouncing destruction, and Reimu uses charms/barrier geometry.
        """
        b = self.boss
        if b.get("state") != "fight" or b.get("hold") or b.get("move") is not None or b.get("super_t", 0.0) > 0:
            return
        b["advanced_t"] = b.get("advanced_t", 0.0) - dt
        rage, phase = b.get("rage", 0.0), b.get("phase", 0)
        if b["advanced_t"] > 0:
            return
        # Faster cadence on later lives without creating an unbounded bullet wall.
        b["advanced_t"] = max(0.72, 1.36 - 0.11 * phase - 0.36 * rage)
        b["advanced_cycle"] = b.get("advanced_cycle", 0) + 1
        cyc = b["advanced_cycle"]
        hx, hy = self.snake_points()[0]
        bx, by = b["x"], b["y"]
        aim = math.atan2(hy - by, hx - bx)
        pi = math.pi

        def burst(angles, speed, color, kind, radius=0.14, beh=None):
            for ang in angles:
                self.fire(bx, by, ang, speed, radius, color, beh=dict({"kind": kind}, **(beh or {})))

        idx = b["idx"]
        if idx == 0:  # CIRNO — freeze-and-release rhythm
            mode = cyc % 3
            if mode == 1:
                spread = 0.16 + 0.025 * phase
                burst([aim + k * spread for k in (-2, -1, 0, 1, 2)], 4.6 + 0.22 * phase,
                      "#dffcff", "ice", beh={"freeze": (0.55, 1.65)})
                for k in range(6):
                    ang = (k * pi / 3) + b["t"] * 0.42
                    self.fire(bx, by, ang, 2.35 + 0.1 * phase, 0.15, "#9fe8ff",
                              beh=dict(kind="ice", accel=0.22))
            elif mode == 2:
                # Falling icicles appear above several x-lanes while a 3-way aimed shot
                # keeps the player from camping under the boss.
                for k in range(5):
                    x = max(a["x1"] + 1.5, min(a["x2"] - 1.5, hx + (k - 2) * 2.1))
                    self.fire(x, a["y1"] + 0.8, pi / 2, 3.9 + 0.12 * phase, 0.14, "#bfe9ff",
                              beh=dict(kind="ice", pressure=True))
                burst([aim - 0.16, aim, aim + 0.16], 4.9, "#ffffff", "ice")
            else:
                # Small circular burst, then freeze a few existing bullets in place.
                for k in range(12):
                    ang = k * 2 * pi / 12 + b["t"] * 0.34
                    self.fire(bx, by, ang, 2.7, 0.14, "#e7fbff",
                              beh=dict(kind="ice", freeze=(0.7, 1.9)))

        elif idx == 1:  # MARISA — fast parallel star streams + occasional laser sweep
            mode = cyc % 3
            if mode == 1:
                # Parallel streams from both sides, inspired by Stardust-style crossing lanes.
                for side in (-1, 1):
                    x = a["x1"] + 0.7 if side < 0 else a["x2"] - 0.7
                    base = 0.20 if side < 0 else pi - 0.20
                    for k in range(5):
                        ang = base + (k - 2) * 0.055
                        self.fire(x, by + (k - 2) * 1.25, ang, 4.25 + 0.12 * phase, 0.13,
                                  "#ffd34d", beh=dict(kind="star"))
            elif mode == 2:
                # Orrery-like orbiting emitters, each releasing a short radial volley.
                rot = b["t"] * 0.9
                for j in range(3):
                    aa = rot + j * 2 * pi / 3
                    ox = bx + math.cos(aa) * (2.8 + j * 0.35)
                    oy = by + math.sin(aa) * (1.9 + j * 0.22)
                    for k in (-1, 0, 1):
                        self.fire(ox, oy, aim + k * 0.10, 4.1, 0.12, "#fff0a8", beh=dict(kind="star"))
            else:
                # Briefly lock a sweeping beam to the player's lane, then let it rotate.
                b["sk"].append(dict(k="beam", age=0.0, life=1.7, warn=0.55, lock=0.34,
                    follow=True, x=bx, y=by, ang=aim, omega=0.35 if cyc % 2 else -0.35,
                    length=42.0, width=1.0, dmg=20, col="rainbow", track=True, hit=False))
                burst([aim - 0.24, aim + 0.24], 4.7, "#ffd34d", "star")
            b["move_burst"] = 0.30

        elif idx == 2:  # REMILIA — aimed trails, alternating fans, spear pressure
            mode = cyc % 3
            if mode == 1:
                for k in range(6):
                    off = (k - 2.5) * 0.085
                    self.fire(bx, by, aim + off, 5.05 + 0.10 * phase, 0.16, "#ff4f6d",
                              beh=dict(kind="knife", split=(0.82, 2)))
            elif mode == 2:
                sign = -1 if cyc % 2 else 1
                rot = b["t"] * 0.38 * sign
                for k in range(10):
                    ang = rot + k * 2 * pi / 10
                    self.fire(bx, by, ang, 3.25 + 0.15 * phase, 0.15, "#ff9aa8", beh=dict(kind="knife"))
                burst([aim - 0.10, aim, aim + 0.10], 5.4, "#c91f45", "knife")
            else:
                # Narrow spear lane: fast, readable center threat.
                b["sk"].append(dict(k="beam", age=0.0, life=1.35, warn=0.55, lock=0.24,
                    follow=True, x=bx, y=by, ang=aim, omega=0.0, length=48.0, width=0.72,
                    dmg=19, col="#ff9aa8", track=True, hit=False))
                for k in (-1, 1):
                    self.fire(bx, by, aim + k * 0.22, 4.0, 0.14, "#ff4f6d", beh=dict(kind="knife"))
            b["move_burst"] = 0.34

        elif idx == 3:  # FLANDRE — corner geometry, rainbow split, wall-bounce destruction
            mode = cyc % 3
            if mode == 1:
                for edge in range(4):
                    if edge == 0:
                        ex, ey = a["x1"] + 1.0, a["y1"] + 1.0
                    elif edge == 1:
                        ex, ey = a["x2"] - 1.0, a["y1"] + 1.0
                    elif edge == 2:
                        ex, ey = a["x2"] - 1.0, a["y2"] - 1.0
                    else:
                        ex, ey = a["x1"] + 1.0, a["y2"] - 1.0
                    aa = math.atan2(hy - ey, hx - ex)
                    for k in (-1, 0, 1):
                        self.fire(ex, ey, aa + k * 0.13, 3.15 + 0.12 * phase, 0.15,
                                  ("#ff4f6d", "#ffd34d", "#7df9ff", "#c78bff")[edge],
                                  beh=dict(kind="orb", split=(0.9, 2)))
            elif mode == 2:
                cols = ("#ff4f6d", "#ffd34d", "#7dff9a", "#7df9ff", "#8ab4ff", "#c78bff")
                for k, col in enumerate(cols):
                    ang = aim + (k - 2.5) * 0.12 + b["t"] * 0.15
                    self.fire(bx, by, ang, 3.45 + 0.12 * k, 0.15, col,
                              beh=dict(kind="star", split=(0.88, 3)))
            else:
                for k in range(14):
                    ang = k * 2 * pi / 14 + b["t"] * 0.44
                    self.fire(bx, by, ang, 2.65 + 0.11 * (k % 3), 0.15,
                              ("#f0d9ff", "#ff6a8a", "#8ab4ff", "#ffd34d")[k % 4],
                              beh=dict(kind="orb", bounce=True))
            b["move_burst"] = 0.30

        else:  # REIMU — homing charms, safe-gap barriers, crossing seals
            mode = cyc % 3
            if mode == 1:
                for k in range(7):
                    aa = aim + (k - 3) * 0.16
                    self.fire(bx, by, aa, 3.55 + 0.10 * phase, 0.15, "#ff7a9c",
                              beh=dict(kind="amulet", home=dict(wait=0.45, rate=1.55, until=2.8, spd=3.8)))
            elif mode == 2:
                gap = aim + (0.42 if cyc % 2 else -0.42)
                n = 20
                for k in range(n):
                    ang = k * 2 * pi / n
                    if _ang_diff(ang, gap) < 0.44:
                        continue
                    self.fire(bx, by, ang, 2.6 + 0.15 * phase, 0.16, "#ffd0e0", beh=dict(kind="amulet"))
                burst([aim, aim + pi], 4.15, "#ffb347", "amulet")
            else:
                # Crossing seal beams create a moving safe pocket rather than a static wall.
                for sign in (-1, 1):
                    b["sk"].append(dict(k="beam", age=0.0, life=1.9, warn=0.55, lock=0.0,
                        follow=False, x=a["x1" if sign < 0 else "x2"], y=a["my"],
                        ang=(0.0 if sign < 0 else pi), omega=sign * 0.45, length=34.0,
                        width=0.78, dmg=18, col="#ffb347", track=False, hit=False))
                for k in range(5):
                    self.fire(bx, by, aim + (k - 2) * 0.10, 4.3, 0.13, "#ff7a9c",
                              beh=dict(kind="amulet"))

        # A light shot sound is intentionally rate-limited by the audio subsystem.
        play_sound("enemy_shot", volume=0.11, min_interval=0.08)

    def run_pressure_pattern(self, dt, a):
        """Sparse character-specific aimed interludes between authored spell patterns."""
        b = self.boss
        if b.get("state") != "fight" or b.get("hold") or b.get("move") is not None or b.get("super_t", 0.0) > 0:
            return
        b["pressure_t"] = b.get("pressure_t", 0.0) - dt
        rage = b.get("rage", 0.0)
        phase = b.get("phase", 0)
        interval = max(2.55, 4.15 - 0.34 * phase - 0.78 * rage)
        if b["pressure_t"] > 0:
            return
        b["pressure_t"] = interval
        b["pattern_cycle"] = b.get("pattern_cycle", 0) + 1
        hx, hy = self.snake_points()[0]
        bx, by = b["x"], b["y"]
        lead = 0.45 + 0.25 * rage
        hx2, hy2 = hx + self.direction[0] * lead, hy + self.direction[1] * lead
        aim = math.atan2(hy2 - by, hx2 - bx)
        idx = b["idx"]
        if idx == 0:  # Cirno: narrow ice fan with delayed outer flakes
            for k in (-1, 0, 1):
                self.fire(bx, by, aim + k * (0.12 + 0.02 * phase), 3.7 + 0.18 * phase, 0.13, "#dffcff", beh=dict(kind="ice", pressure=True))
            for k in (-1, 1):
                self.fire(bx + k * 2.5, by - 1.6, PI / 2, 3.0, 0.12, "#9fe8ff", beh=dict(kind="ice", pressure=True, accel=0.28))
        elif idx == 1:  # Marisa: lead fan plus two slow orbital stars
            for k in (-1, 0, 1):
                self.fire(bx, by, aim + k * 0.10, 4.1 + 0.18 * phase, 0.12, "#ffd34d", beh=dict(kind="star", pressure=True))
            for k in (-1, 1):
                ang = b["brain_t"] * 0.9 + k * PI / 2
                self.fire(bx + math.cos(ang) * 2.2, by + math.sin(ang) * 1.4, ang + PI / 2, 2.8, 0.12, "#fff0a8", beh=dict(kind="star", pressure=True))
        elif idx == 2:  # Remilia: blood-knife fan with a delayed split pair
            for k in (-2, -1, 0, 1, 2):
                self.fire(bx, by, aim + k * 0.095, 4.0 + 0.15 * phase, 0.13, "#ff4f6d", beh=dict(kind="knife", pressure=True))
            self.fire(bx, by, aim - 0.42, 3.0, 0.13, "#ff9aa8", beh=dict(kind="knife", pressure=True, split=(0.72, 2)))
            self.fire(bx, by, aim + 0.42, 3.0, 0.13, "#c91f45", beh=dict(kind="knife", pressure=True, split=(0.72, 2)))
        elif idx == 3:  # Flandre: destructive cross followed by two split shards
            for k in range(4):
                self.fire(bx, by, aim + k * PI / 2, 2.9 + 0.15 * phase, 0.14, ("#ff4f6d", "#ffd34d", "#7df9ff", "#c78bff")[k], beh=dict(kind="orb", pressure=True, split=(0.95, 2)))
        else:  # Reimu: guided amulets with a gentle cardinal cross
            for k in (-1, 0, 1):
                self.fire(bx, by, aim + k * 0.11, 3.6 + 0.15 * phase, 0.13, "#ff7a9c", beh=dict(kind="amulet", pressure=True, home=dict(wait=0.55, rate=0.95, until=2.0, spd=3.2)))
            for k in range(4):
                self.fire(bx, by, aim + k * PI / 2, 2.7, 0.12, "#ffb347", beh=dict(kind="amulet", pressure=True))
        play_sound("enemy_shot", volume=0.16, min_interval=0.06)

    def spawn_arena_mechanic(self, a):
        b = self.boss
        rng = random.Random(int(self.time * 1000) + b["idx"] * 91 + b["phase"] * 17)
        kind = (b["mech_kind"] + 1) % 3
        b["mech_kind"] = kind
        b["hazards"] = []
        if kind == 0:
            # Three delayed impact circles: readable warning, then a short active window.
            for _ in range(6):
                x = rng.uniform(a["x1"] + 4, a["x2"] - 4)
                y = rng.uniform(a["y1"] + 4, a["y2"] - 4)
                b["hazards"].append(dict(x=x, y=y, r=2.0, age=0.0, warn=0.9, life=2.0, hit=False, kind="blast"))
            self.set_message("DANGER SIGILS!  Move out of the glowing circles!")
        elif kind == 1:
            # Four rotating beam sectors leave one moving safe gap.
            for k in range(4):
                b["hazards"].append(dict(x=a["mx"], y=a["my"], r=7.0, age=0.0, warn=0.45, life=2.5, hit=False, kind="sweep", ang=k * math.pi / 2))
            self.set_message("SWEEPING SIGILS!  Follow the opening between the beams!")
        else:
            # Falling lunar/elemental shards: small warning circles distributed across the room.
            for _ in range(13):
                x = rng.uniform(a["x1"] + 2, a["x2"] - 2)
                y = rng.uniform(a["y1"] + 2, a["y2"] - 2)
                b["hazards"].append(dict(x=x, y=y, r=0.8, age=0.0, warn=0.7, life=1.7, hit=False, kind="shard"))
            self.set_message("FALLING SHARDS!  Keep moving!")
        play_sound("boss_warning", volume=0.45)

    def finish_boss_defeat(self):
        b = self.boss
        i = b["idx"]
        a = ARENAS[i]
        if i in self.defeated:
            return
        b["state"] = "defeated"
        b["death_t"] = 0.0
        self.defeated.add(i)
        self.bullets = []
        self.timers = {}
        self.add_xp(600 if a["final"] else 150)
        play_sound("boss_defeat")
        play_sound("spellclear", volume=0.8)
        self.play_zone_music()
        if a["final"]:
            self.set_message("REIMU defeated!    |    Grab the core data in the center")
        else:
            self.remaining.add((a["cx"], a["y2"] - 4))
            self.set_message(f"{BOSSES[i]['name']} defeated!    |    Collect the data fragment dropped in the arena")
        self.update_hud()


    def run_pattern(self, dt):
        """Low-intensity movement pattern. Signature spell cards do the main damage work.

        Each guardian has a different baseline rhythm so bosses no longer feel like the
        same ring/fan emitter wearing different costumes.
        """
        b = self.boss
        if b.get("super_t", 0.0) > 0:
            return
        i, p = b["idx"], b["phase"]
        bx, by = b["x"], b["y"]
        hx, hy = self.snake_points()[0]
        aim = math.atan2(hy - by, hx - bx)
        pi = math.pi
        def ev(key, iv): return range(self.every(key, iv, dt))

        if i == 0:  # Cirno: falling ice and diamond shards
            if p == 0:
                for _ in ev("flake", 0.52):
                    self.fire(bx + random.uniform(-8,8), by - 8.0, pi/2, 3.3, 0.15, "#dffcff", beh=dict(kind="ice"))
            elif p == 1:
                for _ in ev("diamond", 0.72):
                    self.fire(bx, by, aim + random.uniform(-0.9,0.9), 3.0, 0.15, "#7df9ff", beh=dict(kind="ice", accel=0.4))
            else:
                for _ in ev("freeze_rain", 0.44):
                    for k in range(3):
                        ang = aim + (k-1)*0.22 + b["t"]*0.35
                        self.fire(bx,by,ang,3.6,0.14,"#ffffff",beh=dict(kind="ice",freeze=(1.1,2.1)))

        elif i == 1:  # Marisa: star trails and sweeping magic
            if p == 0:
                for _ in ev("star", 0.48):
                    ang=b["t"]*0.9
                    for k in range(3): self.fire(bx,by,ang+k*2*pi/3,3.2,0.14,"#ffd34d",beh=dict(kind="star"))
            elif p == 1:
                for _ in ev("orbital", 0.55):
                    a=b["t"]*1.4
                    self.fire(bx+math.cos(a)*3.0,by+math.sin(a)*2.0,a,3.7,0.15,"#ff7ad9",beh=dict(kind="star"))
            else:
                for _ in ev("spark", 0.30):
                    self.fire(bx,by,aim + random.uniform(-0.18,0.18),4.6,0.13,"#fff4a8",beh=dict(kind="rice"))

        elif i == 2:  # Remilia: radial blood knives
            if p == 0:
                for _ in ev("knives", 0.72):
                    for k in (-1,0,1): self.fire(bx,by,aim+k*0.18,4.1,0.14,"#ff4f6d",beh=dict(kind="knife"))
            elif p == 1:
                for _ in ev("cross", 0.85):
                    for k in range(8): self.fire(bx,by,k*pi/4+b["t"]*0.25,2.9,0.18,"#ffcf5a",beh=dict(kind="knife"))
            else:
                for _ in ev("moon", 0.45):
                    a=b["t"]*1.3
                    self.fire(bx,by,a,3.4,0.15,"#ff4f6d",beh=dict(kind="knife"))
                    self.fire(bx,by,a+pi,3.4,0.15,"#c91f45",beh=dict(kind="knife"))

        elif i == 3:  # Flandre: deliberately irregular destructive fragments
            if p == 0:
                for _ in ev("fragments", 0.78):
                    for off in (-0.42,0.42):
                        self.fire(bx,by,aim+off+random.uniform(-0.08,0.08),3.8,0.15,"#ff4f6d",beh=dict(kind="star"))
            elif p == 1:
                for _ in ev("cloneshot", 0.70):
                    base=b["t"]*0.45
                    for k in range(4): self.fire(bx,by,base+k*pi/2,2.7,0.16,("#ff6a6a","#ffd34d","#7df9ff","#c78bff")[k],beh=dict(kind="orb"))
            elif p == 2:
                for _ in ev("rainbow", 0.43):
                    cols=("#ff4f6d","#ffd34d","#7dff9a","#7df9ff","#8ab4ff","#c78bff")
                    for k,col in enumerate(cols):
                        a=b["t"]*0.5+(k-2.5)*0.18
                        self.fire(bx,by,a,3.0+0.12*k,0.14,col,beh=dict(kind="star",gravity=3.0))
            else:
                for _ in ev("ripples", 0.60):
                    for k in range(4):
                        self.fire(bx,by,b["t"]*0.35+k*pi/2,2.1+0.2*p,0.16,("#f0d9ff","#ff6a8a","#8ab4ff","#ffd34d")[k],beh=dict(kind="orb",bounce=True))

        else:  # Reimu: disciplined seals, orbs, and cardinal firing
            if p == 0:
                for _ in ev("seal", 0.68):
                    self.fire(bx,by,aim,3.9,0.16,"#ff3c5f",beh=dict(kind="amulet",home=dict(wait=0.8,rate=1.3,until=3.0,spd=3.2)))
            elif p == 1:
                for _ in ev("ring", 1.0):
                    n=14
                    for k in range(n): self.fire(bx,by,2*pi*k/n+b["t"]*0.12,2.4,0.17,"#ff7a9c",beh=dict(kind="amulet"))
            elif p == 2:
                for _ in ev("cardinal", 0.50):
                    for k in range(4): self.fire(bx,by,k*pi/2+aim,3.5,0.15,"#ffb347",beh=dict(kind="amulet"))
            else:
                for _ in ev("dream", 0.30):
                    self.fire(bx,by,b["t"]*0.9,3.0,0.14,"#c78bff",beh=dict(kind="amulet"))
                    self.fire(bx,by,b["t"]*0.9+pi,3.0,0.14,"#ffd34d",beh=dict(kind="amulet"))


    def bullet_behave(self, bl, beh, dt, hx, hy):
        """Special bullet behaviours. Returns False when the bullet is spent."""
        beh["a"] = t = beh.get("a", 0.0) + dt
        fz = beh.get("freeze")
        if fz:                                     # Cirno: hang in the air as ice, then shatter in random directions
            st = beh.get("st")
            if st is None and t >= fz[0]:
                beh["st"], beh["col"], beh["kind"] = "frozen", "#ffffff", "ice"
                bl[2] = bl[3] = 0.0
            elif st == "frozen" and t >= fz[1]:
                beh["st"], beh["kind"], beh["col"] = "thaw", "rice", bl[5]
                ang, sp = random.uniform(0, 2 * math.pi), random.uniform(2.6, 4.4)
                bl[2], bl[3] = math.cos(ang) * sp, math.sin(ang) * sp
        gh = beh.get("ghost")
        if gh:                                     # Legacy ghost bullets: fades to a harmless outline, then comes back
            beh["dead"] = (t % gh[0]) > gh[0] * gh[1]
        grav = beh.get("gravity")
        if grav:
            bl[3] += grav * dt                   # Flandre Starbow Break: jump up, then fall into rainbow arcs
        if beh.get("bounce"):
            a = ARENAS[self.boss["idx"]]
            pad = 0.35
            if bl[0] <= a["x1"] + pad and bl[2] < 0:
                bl[0] = a["x1"] + pad
                bl[2] *= -1
            elif bl[0] >= a["x2"] - pad and bl[2] > 0:
                bl[0] = a["x2"] - pad
                bl[2] *= -1
            if bl[1] <= a["y1"] + pad and bl[3] < 0:
                bl[1] = a["y1"] + pad
                bl[3] *= -1
            elif bl[1] >= a["y2"] - pad and bl[3] > 0:
                bl[1] = a["y2"] - pad
                bl[3] *= -1
        hm = beh.get("home")
        if hm and hm["wait"] <= t < hm["until"]:   # Reimu: lock on to the player, turning at a limited rate
            cur = math.atan2(bl[3], bl[2]) if (bl[2] or bl[3]) else math.atan2(hy - bl[1], hx - bl[0])
            want = math.atan2(hy - bl[1], hx - bl[0])
            d = (want - cur + math.pi) % (2 * math.pi) - math.pi
            cur += max(-hm["rate"] * dt, min(hm["rate"] * dt, d))
            bl[2], bl[3] = math.cos(cur) * hm["spd"], math.sin(cur) * hm["spd"]
        ac = beh.get("accel")
        if ac:
            f = 1 + ac * dt
            bl[2] *= f
            bl[3] *= f
        sp = beh.get("split")
        if sp and t >= sp[0]:
            for k in range(sp[1]):
                self.fire(bl[0], bl[1], k * 2 * math.pi / sp[1], 2.4, bl[4], bl[5], beh=dict(kind="orb"))
            return False
        return True

    def update_bullets(self, dt):
        if not self.boss_active():
            self.bullets = []
            return
        a = ARENAS[self.boss["idx"]]
        hx, hy = self.snake_points()[0]
        alive, dmg = [], 0
        for bl in self.bullets:
            beh = bl[6]
            if beh is not None and not self.bullet_behave(bl, beh, dt, hx, hy):
                continue
            bl[0] += bl[2] * dt
            bl[1] += bl[3] * dt
            if not (a["x1"] - 0.5 <= bl[0] <= a["x2"] + 0.5 and a["y1"] - 0.5 <= bl[1] <= a["y2"] + 0.5):
                continue
            if not dmg and self.invincible <= 0 and not (beh and beh.get("dead")) \
                    and math.hypot(bl[0] - hx, bl[1] - hy) < HEAD_HIT + bl[4] * 0.75:
                dmg = beh.get("dmg", 16) if beh else 16
                if beh and beh.get("dmg"):
                    alive.append(bl)               # the spear survives the hit
                    continue
            alive.append(bl)
        self.bullets = alive
        if dmg:
            self.hurt(dmg)
            self.bullets = [bl for bl in self.bullets if bl[6] and bl[6].get("dmg")]

    def apply_boss_aura(self, el):
        if el in ("pulse", "anemo", "geo"):
            return None
        b = self.boss
        aur = b.get("aura")
        if not aur or aur == el:
            b["aura"], b["aura_t"], b["aura_g"] = el, 5.0, 1.0
            return None
        if aur == "quicken" and el in ("dendro", "electro"):
            return "spread" if el == "dendro" else "aggravate"
        reaction = REACT.get(frozenset((aur, el)))
        if reaction:
            b["aura"], b["aura_t"], b["aura_g"] = None, 0.0, 0.0
            return reaction
        b["aura"], b["aura_t"], b["aura_g"] = el, 5.0, 1.0
        return None

    def boss_reaction(self, name, aur, el):
        b = self.boss
        x, y = b["x"], b["y"]
        col = ECOL.get(el, "#ffffff")
        self.float_text(x, y - 2.2, name.upper(), col)
        if name == "freeze":
            b["slow_t"] = max(b.get("slow_t", 0.0), 1.4)
            b["stagger_t"] = max(b.get("stagger_t", 0.0), 0.45)
        elif name == "overload":
            b["stagger_t"] = max(b.get("stagger_t", 0.0), 0.85)
            b["flash"] = 0.16
            self.effects.append([x, y, self.time, "blast", (2.8, ECOL["pyro"])])
        elif name == "electro-charged":
            b["shock_t"] = max(b.get("shock_t", 0.0), 1.8)
        elif name == "superconduct":
            b["res_break_t"] = max(b.get("res_break_t", 0.0), 4.0)
        elif name == "burning":
            b["burn_t"] = max(b.get("burn_t", 0.0), 4.0)
        elif name == "bloom":
            if len(self.cores) < 8:
                self.cores.extend([[x + 2.0, y, 5.0], [x - 2.0, y, 5.0]])
        elif name == "swirl":
            for o in self.enemies:
                if not o["dead"] and math.hypot(o["x"] - x, o["y"] - y) <= 4.5 and aur:
                    o["aura"], o["aura_t"], o["aura_g"] = aur, 4.0, 0.75
        elif name == "crystallize":
            self.add_shield(28)
        elif name in ("quicken", "spread", "aggravate"):
            b["quicken_t"] = max(b.get("quicken_t", 0.0), 5.0)
        elif name == "eclipse":
            self.effects.append([x, y, self.time, "blast", (3.0, ECOL["light"])])

    def boss_hit(self, x, y, hits=None):
        b = self.boss
        if b.get("untarget") or b.get("state") != "fight":
            return
        raw_hits = max(1, int(round(self.dmgm()))) if hits is None else max(1, int(hits))
        b["flash"] = 0.1
        play_sound("boss_hit", volume=0.5, min_interval=0.08)
        self.effects.append([x, y, self.time, "boss_hit", (self.elem,)])
        self.vfx_impact(x, y, ECOL.get(self.elem, "#ffffff"), 1.2, element=self.elem, critical=False, boss=True)

        reaction = None
        react_mult = 1.0
        if self.elem not in ("pulse", "anemo", "geo"):
            old_aura = b.get("aura")
            reaction = self.apply_boss_aura(self.elem)
            if reaction in ("vaporize", "melt"):
                strong = (self.elem, old_aura) in (("hydro", "pyro"), ("pyro", "cryo"))
                react_mult *= (2.0 if strong else 1.5) * self.amp_bonus()
            elif reaction in ("spread", "aggravate"):
                react_mult *= 1.25 + 0.55 * self.get_em() / (self.get_em() + 1000)
            elif reaction in ("overload", "electro-charged", "superconduct", "burning", "swirl", "bloom", "crystallize", "eclipse"):
                coef = {"overload":1.6, "electro-charged":1.0, "superconduct":0.55, "burning":0.8, "swirl":0.65, "bloom":1.8, "crystallize":0.25, "eclipse":2.3}.get(reaction, 0.0)
                raw_hits += max(0, int(round(self.trans_dmg(coef) / 8.0)))
            if reaction:
                self.boss_reaction(reaction, old_aura, self.elem)
                self.effects.append([b["x"], b["y"], self.time, "reaction_burst", (reaction, self.elem, old_aura)])
            rcol = ECOL.get(self.elem, "#ffffff")
            self.vfx_impact(b["x"], b["y"], rcol, 2.1, element=self.elem, critical=True, boss=True)
            self.vfx_flash_screen(rcol, 0.22, 0.13)
            self.vfx_shake(0.34, 0.28)

        if self.elem in ECOL and self.elem != "pulse":
            self.float_text(b["x"], b["y"] - 2.2, self.elem.upper(), ECOL[self.elem])
        factor = self.boss_damage_factor()
        if b.get("res_break_t", 0.0) > 0:
            factor *= 1.20
        if b.get("quicken_t", 0.0) > 0 and self.elem in ("dendro", "electro"):
            factor *= 1.18
        cast = b.get("cast")
        if cast is not None and self.time - cast[2] < 0.45:
            factor *= 1.55
            self.float_text(b["x"], b["y"] - 1.8, "SPELL BREAK!", "#ffffff")
            b["flash"] = 0.16

        final_hits = max(1, int(round(raw_hits * react_mult * factor)))
        for _ in range(final_hits):
            if b["state"] != "fight":
                break
            b["hp"] -= 1
            if b["hp"] <= 0:
                self.phase_clear()
                break
        steal = self.S["steal"] + (3 if self.elem == "abyss" else 0)
        if steal > 0:
            self.heal(final_hits * steal * 0.5)

    def phase_clear(self):
        b = self.boss
        i = b["idx"]
        a = ARENAS[i]
        phases = BOSSES[i]["phases"]
        self.bullets = []
        self.timers = {}
        b["sk"], b["move"] = [], None
        b["hidden"] = b["untarget"] = b["hold"] = False
        self.effects.append([b["x"], b["y"], self.time, "boom"])
        phase_col = phases[b["phase"]]["color"]
        self.vfx_burst(b["x"], b["y"], phase_col, 34, 8.5, 0.13, 1.1, "shard")
        self.vfx_burst(b["x"], b["y"], "#ffffff", 18, 5.0, 0.08, 0.75, "star")
        self.vfx_arc(b["x"], b["y"], phase_col, 2.5 + 0.4 * b["phase"], 0.85, 4, 0, 360)
        self.vfx_flash_screen(phase_col, 0.32, 0.18)
        self.vfx_shake(0.44, 0.38)
        self.vfx_hitstop(0.07)
        if b["phase"] < len(phases) - 1:
            b["phase"] += 1
            b["hp"] = phases[b["phase"]]["hp"]
            b["state"] = "banner"
            b["timer"] = 2.0
            b["spin"] = 0.0
            b["dir"] = 1
            b["power_t"] = 1.45
            self.set_message("Spell card broken!")
            play_sound("spell_break")
            play_sound("timeout", volume=0.5)
            return
        b["state"] = "dying"
        b["death_t"] = 1.45
        b["hazards"] = []
        self.bullets = []
        self.timers = {}
        self.effects.append([b["x"], b["y"], self.time, "death_boss", (phases[-1]["color"],)])
        self.set_message(f"{BOSSES[i]['name']} is defeated!  Finish the spell-card break...")
