"""Damage model: player damage intake, hitting/killing enemies, drops, and player shots."""
import math
import random

from ..config import BOSS_R, C_GOLD, C_CYAN, HIT_IFRAMES, HIT_SHRINK_SEGMENTS, SHOT_SPEED, ELEMENT_FX_TIME, REACTION_FX_TIME
from ..data.elements import ECOL
from ..data.enemies import ENEMY_TYPES, UNIQUE_NAMES
from ..world.level import BMAP, SAVE_CELLS, WALLS
from ..audio import play_music, play_sound


class CombatMixin:
    def hurt(self, amount, why="You were overwhelmed", impact=False):
        if self.invincible > 0 or self.state != "playing":
            return
        amount *= 1 - min(0.90, (self.S["armor"] + (self.skill_profile("coil")["guard"] if self.coil_t > 0 else 0) + (35 if self.bulwark_t > 0 else 0)) / 100)
        reflect = self.skill_profile("bulwark").get("reflect", 0) if self.bulwark_t > 0 else 0
        amount *= max(0.35, 1 - self.S["less_damage"] / 100)
        if self.shield > 0:
            ab = min(self.shield, amount)
            self.shield -= ab
            amount -= ab
        if reflect:
            near = [e for e in self.enemies if not e["dead"] and math.hypot(e["x"]-self.snake[0][0], e["y"]-self.snake[0][1]) <= 5.0]
            if near:
                target = min(near, key=lambda e: math.hypot(e["x"]-self.snake[0][0], e["y"]-self.snake[0][1]))
                self.hit_enemy(target, amount * min(0.65, 0.16 * reflect), self.elem)
        self.hp -= amount
        # Mario-style damage grace period: bullets/enemies cannot damage the player for 2 seconds.
        self.invincible = HIT_IFRAMES
        # Visually shorten the snake on impact, but keep food_eaten/max HP/max capacity unchanged.
        # The removed segments are queued back as normal growth so the snake can recover naturally.
        if len(self.snake) > 6:
            lost = min(HIT_SHRINK_SEGMENTS, len(self.snake) - 6)
            del self.snake[-lost:]
            self.grow_q += lost
        self.hurt_flash = 0.4
        self.shake = 0.32 if impact else 0.15
        hx, hy = self.snake_points()[0]
        self.effects.append([hx, hy, self.time, "boom"])
        self.vfx_burst(hx, hy, "#ff5d6c", 24, 6.5, 0.12, 0.78, "shard")
        self.vfx_burst(hx, hy, "#ffffff", 10, 3.5, 0.07, 0.42, "star")
        self.vfx_flash_screen("#ff5d6c", 0.20, 0.12)
        self.vfx_shake(0.30, 0.24)
        play_sound("player_hurt", volume=0.8)
        self.float_text(hx, hy - 0.6, f"-{int(amount)}", "#ff5d6c")
        if self.hp <= 0:
            self.hp = 0
            self.die(why)

    def die(self, why):
        self.state = "failed"
        self.prev = list(self.snake)
        self.alpha = 1.0
        self.running = False
        self.death_t = 1.35
        hx, hy = self.snake_points()[0]
        self.effects.append([hx, hy, self.time, "death_player", ("#ff6b6b",)])
        play_sound("player_death", volume=1.0)
        play_music("gameover", 0.55)
        self.set_message(f"{why}    |    ENTER = respawn at your last save point    |    N = new game")

    # ---- enemy damage + Genshin-style element reactions
    def hit_enemy(self, e, base, el, melee=False, force_crit=False):
        info = ENEMY_TYPES[e["t"]]
        play_sound("enemy_hit", volume=0.5, min_interval=0.06)
        if e.get("shield", 0.0) > 0:
            blocked = min(e["shield"], base)
            e["shield"] -= blocked
            base = max(0.0, base - blocked)
            if base <= 0:
                e["flash"] = 0.06
                self.effects.append([e["x"], e["y"], self.time, "element_hit", (el, 0.7, True)])
                self.float_text(e["x"], e["y"] - 0.9, "BLOCK", ECOL.get(el, "#ffffff"))
                return
        m = 1.0
        if el == info["weak"]:
            m *= 1.5
        if info.get("resist") == el:
            m *= 0.5
        if info["ai"] == "guard":
            m *= 1.5 if melee else (1.0 if e["stun"] > 0 else 0.5)
        if e["vuln"] > 0:
            m *= 1.3
        if self.heat_t > 0:
            m *= self.skill_profile("heat")["multiplier"]
        if e["shred"] > 0 and el == "pulse":
            m *= 1.4                                    # Superconduct: -40% physical resistance
        if e["vv_t"] > 0 and el == e["vv_el"]:
            m *= 1.4                                    # Swirl (Viridescent style): -40% resistance to the swirled element
        if self.shield > 0 and "geo" in self.reson:
            m *= 1.15                                   # Enduring Rock
        aur = e["aura"]
        frozen = e["freeze"] > 0
        react = self.apply_aura(e, el)
        # Every elemental contact gets a visible signature even before a reaction occurs.
        self.effects.append([e["x"], e["y"], self.time, "element_hit", (el, 1.0, False)])
        flat = 0.0
        if react in ("vaporize", "melt"):
            # amplifying: Hydro>Pyro and Pyro>Cryo are the strong x2.0 side, the reverse is x1.5
            strong = (el, aur) in (("hydro", "pyro"), ("pyro", "cryo"))
            m *= (2.0 if strong else 1.5) * self.amp_bonus()
        elif react in ("spread", "aggravate"):
            em = self.get_em()
            flat = self.trans_base() * (1.25 if react == "spread" else 1.15) * (1 + 5 * em / (em + 1200))
            self.float_text(e["x"], e["y"] - 0.9, react.upper(), ECOL["quicken"])
        if react:
            self.effects.append([e["x"], e["y"], self.time, "reaction_burst", (react, el, aur)])
        if frozen and e["freeze"] > 0 and (melee or el == "geo"):
            e["freeze"] = 0.0                           # SHATTER: heavy hits break frozen enemies
            self.float_text(e["x"], e["y"] - 0.9, "SHATTER", ECOL["cryo"])
            self.damage_enemy(e, self.trans_dmg(1.5))
        if el == "pyro":
            e["burn"] = 3.0
        elif el == "dendro":
            e["venom"] = max(e["venom"], 3.0)
            e["venom_dps"] = max(e["venom_dps"], 3 + self.S["venom"])
        elif el == "cryo":
            e["slow"] = 1.2
        dmg = base * m + flat
        rate = self.crit_rate()
        if "cryo" in self.reson and (aur == "cryo" or frozen):
            rate += 15                                  # Shattering Ice
        crit = force_crit or random.random() * 100 < rate
        if crit:
            dmg *= 1.5 + self.S["cdmg"] / 100
            self.vfx_impact(e["x"], e["y"], C_GOLD, 1.35, element=el, critical=True, boss=False)
        steal = self.S["steal"] + (3 if el == "abyss" else 0)
        if steal > 0:
            self.heal(dmg * steal / 100)
        if self.S["life_on_hit"] > 0:
            self.heal(self.S["life_on_hit"])
        self.damage_enemy(e, dmg, crit)
        if el in ECOL and not react:
            self.float_text(e["x"], e["y"] - 1.25, el.upper(), ECOL[el])

    def damage_enemy(self, e, dmg, crit=False):
        if e["dead"]:
            return
        e["hp"] -= dmg
        e["flash"] = 0.1
        self.float_text(e["x"] + random.uniform(-0.3, 0.3), e["y"] - 0.5, f"{int(dmg)}!" if crit else str(int(dmg)),
            C_GOLD if crit else "#ffffff")
        if not crit:
            self.vfx_burst(e["x"], e["y"], ECOL.get(e.get("aura") or "pulse", "#ffffff"), 5, 2.7, 0.055, 0.26, "spark")
        if e["hp"] <= 0:
            self.kill_enemy(e)

    def kill_enemy(self, e):
        if e["dead"]:
            return
        e["dead"] = True
        e["death_t"] = 0.62
        info = ENEMY_TYPES[e["t"]]
        self.effects.append([e["x"], e["y"], self.time, "death_enemy", (info["col"], 1.0 + 0.35 * e["elite"])])
        self.vfx_burst(e["x"], e["y"], info["col"], 18 if e["elite"] else 10, 5.6 if e["elite"] else 4.2, 0.09, 0.62, "shard")
        self.vfx_arc(e["x"], e["y"], info["col"], 0.7 if e["elite"] else 0.45, 0.55, 2.5 if e["elite"] else 1.8, 0, 360)
        play_sound("enemy_die", volume=0.65 if e["elite"] else 0.45)
        if BMAP[int(e["y"])][int(e["x"])] == 4:
            play_sound("ghost", volume=0.4, min_interval=0.3)             # the Netherworld's dead sigh on their way out
        self.add_xp(info["xp"] * (10 if e["elite"] == 2 else 4 if e["elite"] else 1))
        if self.S["life_on_kill"] > 0:
            self.heal(self.S["life_on_kill"])
        if self.S["energy_on_kill"] > 0 and random.random() * 100 < self.S["energy_on_kill"]:
            cap = getattr(self, "energy_cap", 5)
            if self.ammo < cap:
                self.ammo += 1
                self.float_text(e["x"], e["y"] - 1.1, "+ENERGY", C_CYAN)
        if getattr(self, "S", {}).get("mamba_dash_reset", 0) > 0:
            self.cd["dash"] = 0.0
        if e["elite"] == 2:
            self.points += 1
            self.skill_pts += 1
            self.heal(30)
            self.float_text(e["x"], e["y"] - 1.4, "UNIQUE SLAIN  +1 PASSIVE +1 SKILL POINT", C_GOLD)
            self.set_message(f"{UNIQUE_NAMES[e['t']]} defeated!   |   +1 passive +1 skill point   |   TAB = trees")
            self.update_hud()
        cell = (int(round(e["x"])), int(round(e["y"])))
        if cell in WALLS or cell in self.nodes or cell in self.pickups or cell in SAVE_CELLS or cell in self.foods:
            return
        if not e["elite"] and random.random() < 0.35:
            self.foods[cell] = "food"
            return
        r = random.random()
        if e["elite"]:
            self.pickups[cell] = random.choice(("heal", "dmg", "shield", "speed", "regen", "crit", "elixir", "emorb"))
        elif r < 0.2:
            self.pickups[cell] = "heal"
        elif r < 0.38:
            self.pickups[cell] = "xp"
        elif r < 0.55:
            self.charges.add(cell)

    # ----------------------------------------------------------------- player shots
    def update_shots(self, dt):
        alive = []
        b = self.boss
        for s in self.shots:
            if "life" in s:
                s["life"] -= dt
                if s["life"] <= 0:
                    continue
            remaining = SHOT_SPEED * dt
            dead = False
            while remaining > 0 and not dead:
                d = min(0.5, remaining)
                remaining -= d
                s["x"] += s["dx"] * d
                s["y"] += s["dy"] * d
                if b["state"] == "fight" and math.hypot(s["x"] - b["x"], s["y"] - b["y"]) < BOSS_R:
                    self.boss_hit(s["x"], s["y"])
                    dead = True
                    break
                if self.cores and self.shot_hits_core(s):
                    dead = True
                    break
                for e in self.enemies:
                    if e["dead"] or id(e) in s["hit"]:
                        continue
                    if abs(e["x"] - s["x"]) < 0.7 and abs(e["y"] - s["y"]) < 0.7:
                        self.hit_enemy(e, 10 * self.dmgm() * s.get("mul", 1.0), s["el"])
                        self.effects.append([s["x"], s["y"], self.time, "hit"])
                        self.vfx_burst(s["x"], s["y"], ECOL.get(s.get("el", "pulse"), C_CYAN), 7, 3.2, 0.06, 0.30, "spark")
                        s["hit"].add(id(e))
                        # Skill-tree payload: elemental explosion around the impact.
                        if s.get("explode", 0):
                            rr = 0.75 + 0.55 * int(s["explode"]) + self.S["aoe"] * 0.03
                            for o in self.enemies:
                                if o["dead"] or o is e or math.hypot(o["x"] - s["x"], o["y"] - s["y"]) > rr:
                                    continue
                                self.hit_enemy(o, 5.5 * int(s["explode"]) * self.dmgm() * s.get("mul", 1.0), s["el"])
                            self.effects.append([s["x"], s["y"], self.time, "blast", (rr, ECOL.get(s.get("el", "pulse"), "#ffffff"))])
                        # Split creates two short-lived side projectiles.  Their own
                        # hit sets keep the extra damage bounded.
                        if s.get("split", 0) and int(s["split"]) > 0:
                            a = math.atan2(s["dy"], s["dx"])
                            for da in (-0.42, 0.42):
                                self.shots.append({"x": s["x"], "y": s["y"], "dx": math.cos(a+da), "dy": math.sin(a+da),
                                    "cell": (int(round(s["x"])), int(round(s["y"]))), "el": s["el"], "pierce": 0,
                                    "hit": set(s["hit"]), "mul": s.get("mul", 1.0) * 0.48, "life": 0.48,
                                    "bounce": 0, "explode": 0, "split": 0, "reaction": 0})
                        # Ricochet chooses a fresh nearby target instead of freezing
                        # the projectile when pierce is exhausted.
                        if s.get("bounce", 0) > 0:
                            candidates = [o for o in self.enemies if not o["dead"] and id(o) not in s["hit"]
                                          and math.hypot(o["x"] - s["x"], o["y"] - s["y"]) <= 6.0]
                            if candidates:
                                tgt = min(candidates, key=lambda o: math.hypot(o["x"] - s["x"], o["y"] - s["y"]))
                                ddx, ddy = tgt["x"] - s["x"], tgt["y"] - s["y"]
                                dd = math.hypot(ddx, ddy) or 1.0
                                s["dx"], s["dy"] = ddx / dd, ddy / dd
                                s["bounce"] -= 1
                                continue
                        if s["pierce"] > 0:
                            s["pierce"] -= 1
                        else:
                            dead = True
                            break
                if dead:
                    break
                cell = (int(math.floor(s["x"] + 0.5)), int(math.floor(s["y"] + 0.5)))
                if cell == s["cell"]:
                    continue
                if cell in self.nodes:
                    self.kill_node(cell)
                    self.effects.append([cell[0], cell[1], self.time, "boom"])
                    dead = True
                elif cell in WALLS or self.is_locked(cell):
                    self.effects.append([s["cell"][0], s["cell"][1], self.time, "spark"])
                    dead = True
                s["cell"] = cell
            if not dead:
                alive.append(s)
        self.shots = alive
