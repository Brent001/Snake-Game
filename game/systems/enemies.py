"""Enemy spawning, movement, AI behaviours, enemy bullets and status-effect ticking."""
import math
import random

from ..config import GRID_H, GRID_W, HEAD_HIT
from ..data.enemies import ENEMY_TYPES
from ..world.layout import ARENA_ZONE
from ..world.level import ENEMY_SPAWNS, WALLS
from ..audio import play_sound


class EnemyMixin:
    def init_enemies(self):
        self.enemies = []
        for x, y, t, elite in ENEMY_SPAWNS:
            hp = ENEMY_TYPES[t]["hp"] * (6 if elite == 2 else 3 if elite else 1)
            self.enemies.append(dict(x=float(x), y=float(y), t=t, elite=elite, hp=float(hp), maxhp=float(hp), aura=None,
                aura_t=0.0, burn=0.0, venom=0.0, venom_dps=0.0, stun=0.0, freeze=0.0, vuln=0.0, slow=0.0,
                shred=0.0, vv_t=0.0, vv_el=None, aura_g=0.0, shield=0.0, shield_cd=random.uniform(3.0, 5.0), touch_t=0.0,
                cd=random.uniform(0.5, 2.0), st="idle", st_t=0.0, dead=False, death_t=0.0, flash=0.0, ang=0.0, anim_t=random.random()*10.0))

    def efree(self, x, y):
        c = (int(math.floor(x + 0.5)), int(math.floor(y + 0.5)))
        return (c not in WALLS and c not in self.nodes and c not in ARENA_ZONE and 0 < c[0] < GRID_W - 1 and 0 < c[1] < GRID_H - 1)

    def move_enemy(self, e, ang, speed, dt, ghost=False):
        dx, dy = math.cos(ang) * speed * dt, math.sin(ang) * speed * dt
        if ghost or self.efree(e["x"] + dx, e["y"]):
            e["x"] += dx
        if ghost or self.efree(e["x"], e["y"] + dy):
            e["y"] += dy

    def efire(self, e, ang, speed, r, col, n=1, spread=0.0):
        for k in range(n):
            a = ang + (k - (n - 1) / 2) * spread
            travel_range = max(14.0, min(38.0, speed * 4.8 + 8.0))
            beh = {"travel": 0.0, "range": travel_range, "max_age": max(2.0, travel_range / max(speed, 0.2) + 1.0), "born_r": r}
            self.ebullets.append([e["x"], e["y"], math.cos(a) * speed, math.sin(a) * speed, r, col, 0.0, beh])
        play_sound("enemy_shot", volume=0.55)

    def active_enemies(self):
        """Enemies near the player / camera, refreshed ~4x per second.  update_enemies() and the renderer used to walk
        all ~1000 enemies (dict lookups + a method call each) every frame; now they walk the handful that matter."""
        t = self.time
        src = self.enemies
        if self.__dict__.get("_act_src") is not src or t < self.__dict__.get("_act_t", -9.0) or t - self._act_t >= 0.25:
            hx, hy = self.snake[0]
            rx = max(50.0, self.vw / 2 + 14.0)
            ry = max(36.0, self.vh / 2 + 14.0)
            self._act = [e for e in src if abs(e["x"] - hx) <= rx and abs(e["y"] - hy) <= ry]
            self._act_src, self._act_t = src, t
        return self._act

    def update_enemies(self, dt):
        pts = self.snake_points()
        hx, hy = pts[0]
        tx, ty = hx, hy
        if self.decoy:
            tx, ty = self.decoy["x"], self.decoy["y"]
        for e in self.active_enemies():
            if e["dead"]:
                e["death_t"] = max(0.0, e.get("death_t", 0.0) - dt)
                continue
            if abs(e["x"] - hx) > 38 or abs(e["y"] - hy) > 26:
                continue
            info = ENEMY_TYPES[e["t"]]
            e["flash"] = max(0.0, e["flash"] - dt)
            e["touch_t"] = max(0.0, e.get("touch_t", 0.0) - dt)
            if e["aura_t"] > 0:
                e["aura_t"] -= dt
                if e["aura_t"] <= 0:
                    e["aura"] = None
                e["aura_g"] = 0.0
            dps = 0.0
            if e["burn"] > 0:
                e["burn"] -= dt
                dps += 6 + self.S["burn"]
            if e["venom"] > 0:
                e["venom"] -= dt
                dps += e["venom_dps"]
            if self.coil_t > 0 and any(math.hypot(px - e["x"], py - e["y"]) < 1.35 for px, py in pts):
                prof = self.skill_profile("coil")
                dps += prof["dps"]
                e["slow"] = prof["slow"]
            if dps:
                e["hp"] -= dps * dt
                if e["hp"] <= 0:
                    self.kill_enemy(e)
                    continue
            for k in ("stun", "freeze", "vuln", "slow", "shred", "vv_t"):
                e[k] = max(0.0, e[k] - dt)
            e["cd"] -= dt
            if e["freeze"] > 0 or e["stun"] > 0:
                continue
            spd = info["spd"] * (0.4 if e["slow"] > 0 else 1.0)
            d = math.hypot(tx - e["x"], ty - e["y"])
            ang = math.atan2(ty - e["y"], tx - e["x"])
            if self.camo_t > 0 and d > self.skill_profile("camo")["proximity"]:         # camouflaged: enemies lose track of you
                e["st"] = "idle"
                continue
            ai = info["ai"]
            if ai in ("leap", "guard"):
                wind, rush, rt = (0.55, 9.0, 0.35) if ai == "leap" else (0.8, 7.0, 0.6)
                if e["st"] == "wind":
                    e["st_t"] -= dt
                    if e["st_t"] <= 0:
                        e["st"], e["st_t"], e["ang"] = "dash", rt, ang
                elif e["st"] == "dash":
                    self.move_enemy(e, e["ang"], rush, dt)
                    e["st_t"] -= dt
                    if e["st_t"] <= 0:
                        e["st"], e["cd"] = "idle", 1.6
                else:
                    if d < 14:
                        self.move_enemy(e, ang, spd, dt)
                    if d < 5.5 and e["cd"] <= 0:
                        e["st"], e["st_t"] = "wind", wind
            elif ai == "shoot":
                if d < 13:
                    if d > 6:
                        self.move_enemy(e, ang, spd, dt)
                    elif d < 4:
                        self.move_enemy(e, ang + math.pi, spd, dt)
                    else:
                        self.move_enemy(e, ang + math.pi / 2, spd * 0.6, dt)
                    if e["cd"] <= 0:
                        e["cd"] = 1.7
                        self.efire(e, ang, 4.5, 0.16, "#9fefff", 3, 0.28)
            elif ai == "turret":
                if d < 13 and e["cd"] <= 0:
                    e["cd"] = 2.3
                    for k in range(8):
                        self.efire(e, k * math.pi / 4 + e["ang"], 2.2, 0.2, "#b8ff7a")
                    e["ang"] += 0.2
            elif ai == "strafe":
                if d < 14:
                    if d > 5.5:
                        self.move_enemy(e, ang, spd, dt)
                    elif d < 4:
                        self.move_enemy(e, ang + math.pi, spd, dt)
                    self.move_enemy(e, ang + math.pi / 2, spd * 0.7, dt)
                    if e["cd"] <= 0:
                        e["cd"] = 1.3
                        self.efire(e, ang, 4.2, 0.16, "#ff8a4a", 3, 0.25)
            elif ai == "ghost":
                if d < 16:
                    self.move_enemy(e, ang, spd, dt, ghost=True)
            elif ai == "sniper":                    # keeps its distance, shows a red laser, then fires a fast shot
                if e["st"] == "aim":
                    e["st_t"] -= dt
                    if e["st_t"] > 0.3:
                        e["ang"] = ang
                    if e["st_t"] <= 0:
                        self.efire(e, e["ang"], 10.0, 0.2, info["col"])
                        e["st"], e["cd"] = "idle", 2.4
                elif d < 15:
                    if d > 10:
                        self.move_enemy(e, ang, spd, dt)
                    elif d < 6:
                        self.move_enemy(e, ang + math.pi, spd, dt)
                    if e["cd"] <= 0:
                        e["st"], e["st_t"] = "aim", 0.9
                        play_sound("enemy_charge", volume=0.7)
            elif ai == "bomber":                    # rushes you, flashes a fuse, then detonates
                if e["st"] == "wind":
                    e["st_t"] -= dt
                    if e["st_t"] <= 0:
                        self.effects.append([e["x"], e["y"], self.time, "blast", (2.6, info["col"])])
                        play_sound("enemy_bomb", volume=0.8)
                        if any(math.hypot(px - e["x"], py - e["y"]) < 2.6 for px, py in pts):
                            self.hurt(info["dmg"] * (1.8 if e["elite"] == 2 else 1.4 if e["elite"] else 1.0))
                        self.kill_enemy(e)
                        continue
                elif d < 16:
                    self.move_enemy(e, ang, spd, dt)
                    if d < 2.4:
                        e["st"], e["st_t"] = "wind", 0.7
            elif ai == "orbit":                     # circles you while firing aimed volleys
                if d < 15:
                    if d > 7:
                        self.move_enemy(e, ang, spd, dt)
                    elif d < 5:
                        self.move_enemy(e, ang + math.pi, spd, dt)
                    self.move_enemy(e, ang + math.pi / 2, spd * 0.9, dt)
                    if e["cd"] <= 0:
                        e["cd"] = 1.6
                        self.efire(e, ang, 4.0, 0.16, info["col"], 2, 0.3)

            elif ai == "shield":
                # A short shield window makes these enemies gate burst damage rather than simply taking longer to die.
                if e["shield"] <= 0 and e["shield_cd"] <= 0:
                    e["shield"] = 28 + info["hp"] * 0.55
                    e["shield_cd"] = 6.5
                    e["st"] = "shield"
                elif e["shield"] > 0:
                    e["shield"] = max(0.0, e["shield"] - 2.0 * dt)
                e["shield_cd"] -= dt
                if d < 10:
                    self.move_enemy(e, ang + math.pi / 2, spd * 0.65, dt)
                if e["cd"] <= 0:
                    e["cd"] = 2.0
                    self.efire(e, ang, 3.6, 0.18, info["col"], 3, 0.24)

            elif ai == "trap":
                # Plants a slow field ahead of the player's path, then retreats.
                if e["st"] == "wind":
                    e["st_t"] -= dt
                    if e["st_t"] <= 0:
                        # Enemy fields reuse the normal 7-value projectile record.  A tagged color keeps rendering and collision compatible.
                        self.ebullets.append([e["x"], e["y"], 0.0, 0.0, 2.8, "field:" + info["col"], 0.0])
                        e["st"] = "idle"
                        e["cd"] = 3.8
                    continue
                if d < 13 and e["cd"] <= 0:
                    e["st"], e["st_t"] = "wind", 0.8
                    play_sound("enemy_charge", volume=0.5)
                if d < 8:
                    self.move_enemy(e, ang + math.pi, spd * 0.7, dt)

            elif ai == "swarm":
                # Never sits still: fast orbiting projectiles make it dangerous near the tail, not only at the head.
                if d < 16:
                    tang = ang + (math.pi / 2 if int(e["x"] + e["y"]) % 2 else -math.pi / 2)
                    self.move_enemy(e, tang, spd, dt)
                    if d > 8:
                        self.move_enemy(e, ang, spd * 0.35, dt)
                    if e["cd"] <= 0:
                        e["cd"] = 1.45
                        self.efire(e, ang, 3.8, 0.13, info["col"], 4, 0.15)

            elif ai == "knife":
                if e["st"] == "aim":
                    e["st_t"] -= dt
                    if e["st_t"] <= 0:
                        self.efire(e, e["ang"], 7.0, 0.14, info["col"], 5, 0.17)
                        e["st"], e["cd"] = "idle", 2.5
                elif d < 15:
                    if d > 9:
                        self.move_enemy(e, ang, spd, dt)
                    elif d < 6:
                        self.move_enemy(e, ang + math.pi, spd, dt)
                    self.move_enemy(e, ang + math.pi / 2, spd * 0.35, dt)
                    if e["cd"] <= 0:
                        e["st"], e["st_t"], e["ang"] = "aim", 0.75, ang
                        play_sound("knife_attack", volume=0.45)

            elif ai == "ambush":
                if e["st"] == "hidden":
                    e["st_t"] -= dt
                    if e["st_t"] <= 0:
                        e["st"] = "wind"
                        e["x"] = max(2.0, min(198.0, hx + math.cos(ang) * 5.0))
                        e["y"] = max(2.0, min(198.0, hy + math.sin(ang) * 5.0))
                elif e["st"] == "wind":
                    e["st_t"] -= dt
                    if e["st_t"] <= 0:
                        self.efire(e, math.atan2(hy-e["y"], hx-e["x"]), 5.5, 0.18, info["col"], 7, 0.20)
                        self.effects.append([e["x"], e["y"], self.time, "blast", (2.4, info["col"])])
                        e["st"], e["cd"] = "idle", 3.8
                elif d < 12 and e["cd"] <= 0:
                    e["st"], e["st_t"] = "hidden", 0.9
                elif d < 14:
                    self.move_enemy(e, ang, spd, dt)

            # Snake-body contact is now part of the combat loop: touching an enemy is risky, but
            # the selected element is also applied through the snake's body, enabling reactions without aiming.
            rad = 0.5 + (0.5 if e["elite"] == 2 else 0.25 if e["elite"] else 0.0)
            if any(math.hypot(px - e["x"], py - e["y"]) < rad for px, py in pts):
                if e["touch_t"] <= 0:
                    self.hit_enemy(e, (3.2 + (2.0 if self.coil_t > 0 else 0.0)) * self.dmgm(), self.elem, melee=True)
                    e["touch_t"] = 0.55
                if self.invincible <= 0:
                    self.hurt(info["dmg"] * (1.8 if e["elite"] == 2 else 1.4 if e["elite"] else 1.0))
                    if ai == "ghost":
                        self.stam = max(0.0, self.stam - 25)

    def update_ebullets(self, dt):
        hx, hy = self.snake_points()[0]
        alive = []
        for bl in self.ebullets:
            # Stationary enemy fields keep their legacy 7-value format.
            if isinstance(bl[5], str) and bl[5].startswith("field:"):
                bl[6] += dt
                if bl[6] > 5.0:
                    continue
                rr = bl[4] * (0.88 + 0.08 * math.sin(self.time * 5 + bl[0]))
                if self.invincible <= 0 and math.hypot(hx - bl[0], hy - bl[1]) < rr:
                    self.slow_t = max(self.slow_t, 0.9)
                    if int(self.time * 9) % 2 == 0:
                        self.hurt(4, "You crossed a youkai trap")
                alive.append(bl)
                continue
            bl[0] += bl[2] * dt
            bl[1] += bl[3] * dt
            bl[6] += dt
            if len(bl) >= 8:
                beh = bl[7]
                speed = math.hypot(bl[2], bl[3])
                beh["travel"] = beh.get("travel", 0.0) + speed * dt
                if beh["travel"] >= beh.get("range", 999.0) or bl[6] >= beh.get("max_age", 8.0):
                    continue
            cell = (int(math.floor(bl[0] + 0.5)), int(math.floor(bl[1] + 0.5)))
            if bl[6] > 6 or cell in WALLS or cell in ARENA_ZONE or not (0 < cell[0] < GRID_W - 1 and 0 < cell[1] < GRID_H - 1):
                continue
            if self.invincible <= 0 and math.hypot(bl[0] - hx, bl[1] - hy) < HEAD_HIT + bl[4] * 0.75:
                self.hurt(8)
                continue
            alive.append(bl)
        self.ebullets = alive
