"""Player actions: shooting, dash, per-class basic attacks (fang bite / tail slam / bolt / volt slash) and the snake skills (coil, shed, heat sense, scent, spit, rattle, camo)."""
import math

from ..config import BOSS_R, C_GOLD, C_MINT, C_PINK, C_CYAN, CELL, NUM_FRAGMENTS, SHOT_COOLDOWN
from ..data.elements import ECOL
from ..world.layout import ARENAS
from ..world.level import SAVE_CELLS
from ..audio import play_sound


ELEM_SND = dict(pyro="burning", electro="zap", hydro="water", anemo="puff", dendro="gas", cryo="ice_attack", abyss="ghost", light="laser", geo="bump")


class AbilitiesMixin:
    def ready_for(self, skill, stam):
        return self.state == "playing" and self.cd[skill] <= 0 and self.stam >= stam

    def spend(self, stam, skill, cd):
        self.stam -= stam * (0.85 if "anemo" in self.reson else 1.0)
        self.stam_delay = 0.7
        self.cd[skill] = cd
        self.cdmax[skill] = cd

    def shoot(self):
        if self.state != "playing":
            return
        if self.ammo <= 0:
            self.set_message("No pulse charge    |    Find green hexagons (they also regenerate slowly)")
            return
        if self.time - self.last_shot < SHOT_COOLDOWN:
            return
        self.last_shot = self.time
        self.ammo -= 1
        play_sound(ELEM_SND.get(self.elem, "player_shot"), volume=0.45)
        hx, hy = self.snake_points()[0]
        dx, dy = self.direction
        pierce = int(self.S["pierce"]) + (1 if self.elem == "light" else 0)
        self.shots.append({"x": hx, "y": hy, "dx": dx, "dy": dy, "cell": self.snake[0], "el": self.elem,
            "pierce": pierce, "hit": set(), "born": self.time})
        self.vfx_burst(hx + dx * 0.35, hy + dy * 0.35, ECOL.get(self.elem, C_CYAN), 6, 2.6, 0.06, 0.28, "spark")
        self.vfx_flash_screen(ECOL.get(self.elem, C_CYAN), 0.055, 0.07)
        self.update_hud()

    def dash(self):
        if not self.ready_for("dash", 28):
            return
        prof = self.skill_profile("dash")
        self.spend(28, "dash", prof["cooldown"])
        play_sound("dash", volume=0.65)
        self.dash_t = 0.04 * prof["length"]
        self.invincible = max(self.invincible, self.dash_t + prof.get("iframes", 0.18))
        self.acc = max(self.acc, self.step_s())
        hx, hy = self.snake_points()[0]
        if prof.get("speed", 0):
            self.buff_speed = max(self.buff_speed, 0.65 + 0.05 * prof["speed"])
        if prof.get("lifesteal", 0):
            self.heal(2.0 + 1.5 * prof["lifesteal"])
        if prof.get("explode", 0):
            self.blast(hx + self.direction[0] * 0.9, hy + self.direction[1] * 0.9,
                       0.9 + 0.45 * prof["explode"], self.trans_dmg(0.35 * prof["explode"]), ECOL.get(self.elem, C_CYAN))
        if prof.get("afterimage", 0):
            self.decoy = {"x": float(hx), "y": float(hy), "t": 0.8 + 0.35 * prof["afterimage"]}
        self.vfx_burst(hx, hy, ECOL["anemo"], 14, 4.5, 0.08, 0.46, "shard")
        self.vfx_shake(0.18)

    # ---- aiming + primary attack (left click)
    def aim_vector(self):
        """Unit vector from the snake's head to the mouse cursor (falls back to the facing direction)."""
        hx, hy = self.snake_points()[0]
        if self.aim_ok:
            mx, my = self.mouse
            dx = self.cam_x + (mx - CELL / 2) / CELL - hx
            dy = self.cam_y + (my - CELL / 2) / CELL - hy
            d = math.hypot(dx, dy)
            if d > 0.35:
                return dx / d, dy / d
        return float(self.direction[0]), float(self.direction[1])

    def primary_attack(self):
        """LEFT CLICK: every class has its own basic attack.

        VIPER  - FANG BITE : short, fast, precise bite that stacks venom.
        PYTHON - TAIL SLAM : slow 360-degree crush with heavy knock-back and stun.
        COBRA  - VENOM BOLT: aimed ranged shot (unchanged).
        MAMBA  - VOLT SLASH: wide aim-assisted lightning slash, executes weak enemies, chains Electro.
        """
        if self.state != "playing":
            return
        cid = self.run_class
        if self.S["form_ranged"] > 0 or cid == "cobra":
            prof = self.skill_profile("bolt")
            if not self.ready_for("strike", 5 + 2 * (prof["count"] - 1)):
                return
            self.spend(5 + 2 * (prof["count"] - 1), "strike", prof["cooldown"])
            ax, ay = self.aim_vector()
            base = math.atan2(ay, ax)
            n = prof["count"]
            for i in range(n):                       # TWIN / TRIPLE / HYDRA / RICOCHET / PAYLOAD
                self.fire_bolt(base + (i - (n - 1) / 2) * prof["gap"], prof["mul"], prof["pierce"],
                               bounce=prof.get("bounce", 0), explode=prof.get("explode", 0),
                               split=prof.get("split", 0), reaction=prof.get("explode_reaction", 0))
            if prof.get("repeat", 0) > 0:
                self.effects.append([hx, hy, self.time, "blast", (1.0, ECOL.get(self.elem, "#7ddb4a"))])
            return
        if cid == "viper":
            self.fang_bite()
        elif cid == "python":
            self.tail_slam()
        elif cid == "mamba":
            self.volt_slash()
        else:
            self.strike()

    def fire_bolt(self, ang, mul, pierce=0, life=0.95, bounce=0, explode=0, split=0, reaction=0):
        hx, hy = self.snake_points()[0]
        self.shots.append({"x": hx, "y": hy, "dx": math.cos(ang), "dy": math.sin(ang), "cell": self.snake[0],
            "el": self.elem, "pierce": pierce, "hit": set(), "mul": mul, "life": life,
            "bounce": int(bounce), "explode": int(explode), "split": int(split), "reaction": int(reaction)})
        sx, sy = hx + math.cos(ang) * 0.8, hy + math.sin(ang) * 0.8
        self.effects.append([sx, sy, self.time, "element_cast", (self.elem, ang)])
        self.vfx_burst(sx, sy, ECOL.get(self.elem, C_CYAN), 8, 3.8, 0.07, 0.34, "spark")

    def strike(self):
        if not self.ready_for("strike", 22):
            return
        mamba = self.S["form_mamba"] > 0
        tank = self.S["form_tank"] > 0
        prof = self.skill_profile("strike")
        self.spend(22, "strike", prof["cooldown"])
        play_sound("player_strike", volume=0.7)
        self.lunge_t = 0.22
        hx, hy = self.snake_points()[0]
        dx, dy = self.aim_vector()
        self.lunge_dir = (dx, dy)
        reach = prof["reach"] + (1.2 if mamba else 0.0)
        width = prof["width"]
        base = 26 * (1 + self.S["melee"] / 100) * self.res_dmg() * prof.get("execute", 1.0)
        if self.buff_dmg > 0:
            base *= 1.5
        for e in self.enemies:
            if e["dead"]:
                continue
            rx = (e["x"] - hx) * dx + (e["y"] - hy) * dy
            ry = -(e["x"] - hx) * dy + (e["y"] - hy) * dx
            if 0 <= rx <= reach and abs(ry) <= width:
                self.hit_enemy(e, base, self.elem, melee=True)
                e["stun"] = max(e["stun"], prof["stun"])
                e["venom"] = 4.0
                e["venom_dps"] = prof["venom"]
                if tank and not e["dead"]:
                    self.move_enemy(e, math.atan2(dy, dx), 15.0, 0.1)          # shoulder charge knock-back
        b = self.boss
        if b["state"] == "fight" and math.hypot(hx + dx * reach * 0.6 - b["x"], hy + dy * reach * 0.6 - b["y"]) < BOSS_R + 1.0:
            self.boss_hit(b["x"], b["y"], max(1, int(round(base / 18))))
        self.effects.append([hx + dx * 1.2, hy + dy * 1.2, self.time, "slash", (ECOL[self.elem], dx, dy, 1.4 if tank else 1.0)])
        # Melee deliberately avoids bloom/particle halos. The slash renderer provides the stylized
        # weapon silhouette, while hit-stop and shake provide weight.
        self.vfx_hitstop(0.032)
        self.vfx_shake(0.16)

    def _melee_base(self, mul=1.0):
        base = 26 * (1 + self.S["melee"] / 100) * self.res_dmg() * mul
        if self.buff_dmg > 0:
            base *= 1.5
        return base

    def fang_bite(self):
        """VIPER basic attack: a short, narrow, fast bite. Low direct damage, but every bite adds a venom stack
        (up to 5) and bites on already-poisoned enemies hit harder."""
        if not self.ready_for("strike", 12):
            return
        prof = self.skill_profile("fang")
        self.spend(12, "strike", prof["cooldown"])
        play_sound("knife_attack", volume=0.6)
        self.lunge_t = 0.22
        hx, hy = self.snake_points()[0]
        dx, dy = self.aim_vector()
        self.lunge_dir = (dx, dy)
        reach, width = prof["reach"], prof["width"]
        base = self._melee_base(prof["damage"])
        if prof["ambush"] and self.camo_t > 0:
            base *= 1.6                                         # Widow's Silence: bite from camouflage
        cands = []
        for e in self.enemies:
            if e["dead"]:
                continue
            rx = (e["x"] - hx) * dx + (e["y"] - hy) * dy
            ry = -(e["x"] - hx) * dy + (e["y"] - hy) * dx
            if 0 <= rx <= reach and abs(ry) <= width:
                cands.append((rx, e))
        cands.sort(key=lambda t: t[0])
        for _, e in cands[:prof["targets"]]:
            poisoned = e["venom"] > 0
            self.hit_enemy(e, base * (prof["poison_bonus"] if poisoned else 1.0), self.elem, melee=True)
            if e["dead"]:
                continue
            if not poisoned:
                e["venom_stack"] = 0
            stacks = min(5, int(e.get("venom_stack", 0)) + 1)
            e["venom_stack"] = stacks
            new_dps = prof["venom"] + (stacks - 1) * prof["stack_dps"]
            e["venom_dps"] = new_dps if not poisoned else max(e["venom_dps"], new_dps)
            e["venom"] = max(e["venom"], prof["venom_time"])
            e["stun"] = max(e["stun"], prof["stun"])
            if stacks >= 2:
                self.float_text(e["x"], e["y"] - 1.5, f"VENOM x{stacks}", ECOL["dendro"])
            if prof["spread"] and stacks >= 3:       # WIDOW'S KISS: heavy venom jumps to neighbours
                for o in self.enemies:
                    if not o["dead"] and o is not e and math.hypot(o["x"] - e["x"], o["y"] - e["y"]) < 2.5:
                        o["venom"] = max(o["venom"], 4.0)
                        o["venom_dps"] = max(o["venom_dps"], new_dps * 0.7)
        b = self.boss
        if b["state"] == "fight" and math.hypot(hx + dx * reach * 0.6 - b["x"], hy + dy * reach * 0.6 - b["y"]) < BOSS_R + 0.8:
            self.boss_hit(b["x"], b["y"], max(1, int(round(base / 22))))
        self.effects.append([hx + dx * 0.9, hy + dy * 0.9, self.time, "fang_bite", (ECOL[self.elem], dx, dy)])
        self.vfx_hitstop(0.018)
        self.vfx_shake(0.07)

    def tail_slam(self):
        """PYTHON basic attack: a heavy 360-degree tail sweep around the whole body. Slow, huge stun and knock-back,
        the outer ring (the tail tip) hits harder, and every enemy caught feeds a little shield."""
        if not self.ready_for("strike", 26):
            return
        prof = self.skill_profile("slam")
        self.spend(26, "strike", prof["cooldown"])
        play_sound("bump", volume=0.9)
        play_sound("player_strike", volume=0.45)
        hx, hy = self.snake_points()[0]
        radius = prof["radius"]
        base = self._melee_base(prof["damage"])
        caught = 0
        for e in self.enemies:
            if e["dead"]:
                continue
            d = math.hypot(e["x"] - hx, e["y"] - hy)
            if d > radius:
                continue
            ang = math.atan2(e["y"] - hy, e["x"] - hx)
            self.hit_enemy(e, base * (prof["tip"] if d >= radius * 0.6 else 1.0), self.elem, melee=True)
            if e["dead"]:
                caught += 1
                continue
            e["stun"] = max(e["stun"], prof["stun"])
            self.move_enemy(e, ang, prof["knock"], 0.1)          # knock-back away from the body
            caught += 1
        if caught:
            self.add_shield(prof["shield"] * min(caught, prof["cap"]))
        b = self.boss
        if b["state"] == "fight" and math.hypot(hx - b["x"], hy - b["y"]) < radius + BOSS_R:
            self.boss_hit(b["x"], b["y"], max(1, int(round(base / 14))))
        self.effects.append([hx, hy, self.time, "tail_slam", (ECOL[self.elem], radius)])
        self.vfx_flash_screen("#ffffff", 0.07, 0.08)
        self.vfx_hitstop(0.055)
        self.vfx_shake(0.36)

    def volt_slash(self):
        """MAMBA basic attack: a wide, fast lightning slash with aim assist.
        - Forgiving ~90 degree arc, long reach, snaps toward the nearest enemy near your cursor.
        - Assassin rules: enemies that are stunned, frozen or below 35% HP take a guaranteed critical hit
          and double damage (EXECUTE).
        - Every enemy you hit arcs Electro to a nearby enemy (up to 3 arcs per slash).
        - Kills refund stamina and shave time off DASH, so you can chain slash -> dash -> slash.
        - Brief invulnerability while you cut."""
        if not self.ready_for("strike", 12):
            return
        prof = self.skill_profile("volt")
        self.spend(12, "strike", prof["cooldown"])
        hx, hy = self.snake_points()[0]
        dx, dy = self.aim_vector()
        reach, half = prof["reach"], prof["arc"]
        # aim assist: snap to the nearest enemy that is roughly where the cursor points
        aim_ang = math.atan2(dy, dx)
        best, best_score = None, 1e9
        for e in self.enemies:
            if e["dead"]:
                continue
            ex, ey = e["x"] - hx, e["y"] - hy
            d = math.hypot(ex, ey)
            if d < 0.2 or d > reach + 0.8:
                continue
            da = abs((math.atan2(ey, ex) - aim_ang + math.pi) % math.tau - math.pi)
            if da <= prof["assist"] and d + da * 3.0 < best_score:
                best, best_score = e, d + da * 3.0
        if best is not None:
            aim_ang = math.atan2(best["y"] - hy, best["x"] - hx)
            dx, dy = math.cos(aim_ang), math.sin(aim_ang)
        self.lunge_t = 0.22
        self.lunge_dir = (dx, dy)
        self.invincible = max(self.invincible, 0.14)
        play_sound("lightning", volume=0.55)
        base = self._melee_base(prof["damage"]) * prof["execute"]
        hit, kills, arcs = [], 0, 0
        for e in self.enemies:
            if e["dead"]:
                continue
            ex, ey = e["x"] - hx, e["y"] - hy
            d = math.hypot(ex, ey)
            if d > reach or d < 0.01:
                continue
            da = abs((math.atan2(ey, ex) - aim_ang + math.pi) % math.tau - math.pi)
            if da > half and not (d < 1.2 and da < half * 1.8):
                continue
            weak = e["stun"] > 0 or e["freeze"] > 0 or e["hp"] < e.get("maxhp", e["hp"]) * prof["weak"]
            self.hit_enemy(e, base * (2.0 if weak else 1.0), self.elem, melee=True, force_crit=weak)
            hit.append(e)
            if e["dead"]:
                kills += 1
                if weak:
                    self.float_text(e["x"], e["y"] - 1.5, "EXECUTE", ECOL["electro"])
        for src in list(hit):
            if arcs >= prof["arcs"]:
                break
            others = [e for e in self.enemies if not e["dead"] and e not in hit
                      and math.hypot(e["x"] - src["x"], e["y"] - src["y"]) < 3.8]
            if others:
                tgt = min(others, key=lambda e: math.hypot(e["x"] - src["x"], e["y"] - src["y"]))
                self.hit_enemy(tgt, self.trans_dmg(0.8) + self.S["chain"], "electro")
                hit.append(tgt)
                arcs += 1
                self.effects.append([src["x"], src["y"], self.time, "volt_arc", (tgt["x"], tgt["y"])])
        if kills:
            self.stam = min(self.maxstam, self.stam + 10 * prof["refund"] * min(kills, 3))
            self.cd["dash"] = max(0.0, self.cd["dash"] - 0.6 * prof["refund"] * min(kills, 2))
        b = self.boss
        if b["state"] == "fight" and math.hypot(hx + dx * reach * 0.5 - b["x"], hy + dy * reach * 0.5 - b["y"]) < BOSS_R + 1.2:
            self.boss_hit(b["x"], b["y"], max(2, int(round(base / 12))))
        self.effects.append([hx, hy, self.time, "volt_slash", (ECOL[self.elem], dx, dy, reach, half, len(hit) > 0)])
        self.vfx_hitstop(0.035 if hit else 0.015)
        self.vfx_shake(0.15 if hit else 0.07)

    def coil(self):
        if not self.ready_for("coil", 25):
            return
        prof = self.skill_profile("coil")
        self.spend(25, "coil", prof["cooldown"])
        play_sound("skill", volume=0.6)
        self.coil_t = prof["duration"]
        hx, hy = self.snake[0]
        if prof.get("root"):
            for e in self.enemies:
                if not e["dead"] and math.hypot(e["x"] - hx, e["y"] - hy) <= prof.get("radius", 4.2) + self.S["coil"] * 0.08:
                    e["stun"] = max(e["stun"], 0.9 + self.S["python_root"] * 0.3)
        if prof.get("explode") or prof.get("burst"):
            self.blast(hx, hy, prof.get("radius", 4.2) * (0.7 if prof.get("explode") else 0.45),
                       self.trans_dmg(0.55 + 0.25 * prof.get("burst", 0)), ECOL.get(self.elem, C_GOLD))
        if prof.get("pulse") or prof.get("echo"):
            self.effects.append([hx, hy, self.time, "blast", (prof.get("radius", 4.2), ECOL.get(self.elem, C_GOLD))])
        if prof.get("reflect"):
            self.invincible = max(self.invincible, 0.12)
        if prof.get("coil_shield", 0):
            self.add_shield(4 + prof["guard"] * 0.35)
        self.set_message(f"COIL - {prof['dps']:.0f} DPS, {prof['slow']:.1f}s slow, +{prof['guard']:.0f}% guard")

    def shed(self):
        if not self.ready_for("shed", 0):
            return
        prof = self.skill_profile("shed")
        self.spend(0, "shed", max(12.0, 30.0 - self.S["shed_cd"]))
        self.heal(self.maxhp * prof["heal"])
        self.invincible = max(self.invincible, prof["iframe"])
        tx, ty = self.snake[-1]
        self.decoy = {"x": float(tx), "y": float(ty), "t": prof["decoy"]}
        if prof.get("burst"):
            for e in self.enemies:
                if not e["dead"] and math.hypot(e["x"]-tx, e["y"]-ty) <= 2.2:
                    self.hit_enemy(e, 8 * self.dmgm(), self.elem)
            self.effects.append([tx, ty, self.time, "blast", (2.2, ECOL.get(self.elem, ECOL["hydro"]))])
        if prof.get("overheal"):
            self.add_shield(self.maxhp * 0.04)
        if prof.get("guard"):
            self.add_shield(6 + prof["guard"] * 2)
        self.float_text(tx, ty - 0.6, "SHED SKIN", ECOL["hydro"])
        self.set_message("SHED SKIN - you healed, and the old skin distracts enemies")

    def heat_sense(self):
        if not self.ready_for("heat", 0):
            return
        prof = self.skill_profile("heat")
        self.spend(0, "heat", max(8.0, 20.0 - self.S["heat_cd"]))
        self.heat_t = prof["duration"]
        self.cd["heat"] = max(0.0, self.cd["heat"] - 0.5 * prof.get("fast", 0))
        if prof.get("crit", 0):
            self.buff_crit = max(self.buff_crit, 1.0 + 0.35 * prof["crit"])
        if prof.get("energy", 0):
            self.ammo = min(getattr(self, "energy_cap", 5), self.ammo + int(prof["energy"]))
        if prof.get("pulse") or prof.get("burst"):
            hx, hy = self.snake_points()[0]
            for e in self.enemies:
                if not e["dead"] and math.hypot(e["x"]-hx, e["y"]-hy) <= 4.0:
                    e["vuln"] = max(e.get("vuln", 0.0), 1.2 + 0.4 * prof.get("burst", 0))
            self.effects.append([hx, hy, self.time, "blast", (4.0, "#ff6a3a")])
        self.set_message("HEAT SENSE - enemies revealed on the minimap, +20% damage to them")

    def tongue(self):
        if not self.ready_for("scent", 0):
            return
        prof = self.skill_profile("scent")
        self.spend(0, "scent", max(1.0, 3.0 - self.S["scent_cd"]))
        hx, hy = self.snake[0]
        targets = []
        max_range = prof["range"]

        def nearest(cells, col, label):
            cells = [p for p in cells if math.hypot(p[0]-hx, p[1]-hy) <= max_range]
            if cells:
                c = min(cells, key=lambda p: (p[0] - hx) ** 2 + (p[1] - hy) ** 2)
                targets.append((c[0], c[1], col, label))

        nearest(self.charges, C_MINT, "CHARGE")
        nearest([p for p, k in self.pickups.items() if k.startswith("oc_")], C_GOLD, "OCULUS")
        nearest([c for c in SAVE_CELLS if c not in self.visited_saves], "#fff1a0", "SAVE")
        nearest([a["front"] for i, a in enumerate(ARENAS) if i not in self.defeated
            and not (a["final"] and self.collected < NUM_FRAGMENTS)], C_PINK, "BOSS")
        self.scent = targets
        self.scent_t = prof["duration"]
        if prof.get("damage", 0):
            for e in self.enemies:
                if not e["dead"] and math.hypot(e["x"]-hx, e["y"]-hy) <= max_range:
                    e["vuln"] = max(e.get("vuln", 0.0), 1.0 + 0.25 * prof["damage"])
        if prof.get("speed", 0):
            self.buff_speed = max(self.buff_speed, 0.7 + 0.04 * prof["speed"])
        if prof.get("reset"):
            self.cd["scent"] = 0.0

    def spit(self):
        """Elemental venom jet.  Tree upgrades can turn the line into a fan and chain."""
        if not self.ready_for("spit", 20):
            return
        prof = self.skill_profile("spit")
        self.spend(20, "spit", max(1.6, 4.0 - self.S["spit_cd"]))
        play_sound("player_spit", volume=0.6)
        hx, hy = self.snake_points()[0]
        ax, ay = self.aim_vector()
        base = math.atan2(ay, ax)
        count = max(1, int(prof.get("count", 1)))
        hit_set = []
        for i in range(count):
            ang = base + (i - (count - 1) / 2) * (prof.get("width", 1.0) * 0.06)
            dx, dy = math.cos(ang), math.sin(ang)
            reach = prof["reach"]
            for e in self.enemies:
                if e["dead"]:
                    continue
                rx = (e["x"] - hx) * dx + (e["y"] - hy) * dy
                ry = -(e["x"] - hx) * dy + (e["y"] - hy) * dx
                if 0 <= rx <= reach and abs(ry) <= prof["width"]:
                    e["venom"] = max(e["venom"], 5.0 + prof.get("venom", 0))
                    e["venom_dps"] = max(e["venom_dps"], prof["damage"] - 4 + self.S["venom"] + prof.get("venom", 0))
                    e["stun"] = max(e["stun"], prof["stun"])
                    self.float_text(e["x"], e["y"] - 1.2, "BLINDED", ECOL["dendro"])
                    self.hit_enemy(e, prof["damage"] * self.dmgm(), self.elem)
                    if e not in hit_set:
                        hit_set.append(e)
                    if prof.get("explode"):
                        for o in self.enemies:
                            if o is e or o["dead"] or math.hypot(o["x"]-e["x"], o["y"]-e["y"]) > 1.6:
                                continue
                            self.hit_enemy(o, prof["damage"] * 0.35 * self.dmgm(), self.elem)
            b = self.boss
            if b["state"] == "fight":
                rx = (b["x"] - hx) * dx + (b["y"] - hy) * dy
                ry = -(b["x"] - hx) * dy + (b["y"] - hy) * dx
                if 0 <= rx <= reach and abs(ry) <= BOSS_R:
                    self.boss_hit(b["x"], b["y"], 1)
            self.effects.append([hx + dx * 0.8, hy + dy * 0.8, self.time, "spit", (dx, dy, reach, prof["width"])])
        if prof.get("bounce") and hit_set:
            src = hit_set[0]
            near = sorted((e for e in self.enemies if not e["dead"] and e is not src and math.hypot(e["x"]-src["x"], e["y"]-src["y"]) < 5.0),
                          key=lambda e: math.hypot(e["x"]-src["x"], e["y"]-src["y"]))[:int(prof["bounce"])]
            for e in near:
                self.hit_enemy(e, prof["damage"] * 0.55 * self.dmgm(), self.elem)
        if prof.get("chain") and hit_set:
            self.stam = min(self.maxstam, self.stam + 4 * prof["chain"])
        if prof.get("reaction") or prof.get("element"):
            self.buff_em = max(self.buff_em, 1.5 + 0.5 * prof.get("reaction", 0))
    def rattle(self):
        """Rattlesnake warning: stuns and shoves back nearby enemies and wipes close bullets."""
        if not self.ready_for("rattle", 20):
            return
        prof = self.skill_profile("rattle")
        self.spend(20, "rattle", max(5.0, 14.0 - self.S["rattle_cd"]))
        play_sound("rattle", volume=0.7)
        hx, hy = self.snake_points()[0]
        for e in self.enemies:
            if e["dead"]:
                continue
            d = math.hypot(e["x"] - hx, e["y"] - hy)
            if d <= prof["radius"]:
                e["stun"] = max(e["stun"], prof["stun"])
                if d > 0.1:
                    self.move_enemy(e, math.atan2(e["y"] - hy, e["x"] - hx), prof["force"], 0.1)
        self.bullets = [b for b in self.bullets if math.hypot(b[0] - hx, b[1] - hy) > prof["clear"]]
        self.ebullets = [b for b in self.ebullets if math.hypot(b[0] - hx, b[1] - hy) > prof["clear"]]
        for pulse_i in range(max(1, prof.get("pulses", 1))):
            rr = prof["radius"] * (1.0 + 0.12 * pulse_i)
            self.effects.append([hx, hy, self.time, "blast", (rr, "#ffd34d")])
        if prof.get("guard", 0):
            self.invincible = max(self.invincible, 0.18 + 0.05 * prof["guard"])
        if prof.get("energy", 0):
            self.ammo = min(getattr(self, "energy_cap", 5), self.ammo + int(prof["energy"] // 3))
        self.set_message(f"RATTLE - {prof['radius']:.1f} radius, {prof['stun']:.1f}s stun, bullets cleared")


    def update_skill_zones(self, dt):
        """Tick persistent class- or tree-created hazards."""
        if not getattr(self, "skill_zones", None):
            return
        alive = []
        hx, hy = self.snake_points()[0]
        for z in self.skill_zones:
            z["t"] -= dt
            z["tick"] = z.get("tick", 0.0) - dt
            if z["t"] <= 0:
                continue
            if z["tick"] <= 0:
                z["tick"] = 0.38
                for e in self.enemies:
                    if e["dead"] or math.hypot(e["x"] - z["x"], e["y"] - z["y"]) > z["r"]:
                        continue
                    self.hit_enemy(e, z["dps"] * 0.38 * self.dmgm(), z.get("el", "dendro"))
                b = self.boss
                if b.get("state") == "fight" and math.hypot(b["x"] - z["x"], b["y"] - z["y"]) <= z["r"] + 0.8:
                    self.boss_hit(z["x"], z["y"], max(1, int(z["dps"] / 20)))
            alive.append(z)
        self.skill_zones = alive

    # ---- class signatures -------------------------------------------------
    def class_skill(self):
        """V: class-defining skill. The selected keystone changes its pattern, not just its numbers."""
        if not self.ready_for("class_skill", 35):
            return
        self.spend(35, "class_skill", max(4.0, 12.0 - self.S["class_skill"] * 1.1 - self.S["class_cd"]))
        lvl = int(self.S["class_skill"])
        hx, hy = self.snake_points()[0]
        ax, ay = self.aim_vector()
        col = self.cls["skill"]["color"]

        if self.run_class == "viper":
            if self.S["viper_alchemist"] > 0:
                # Toxic Dominion: V paints persistent zones along the route.
                length = 5.5 + lvl * 0.6
                for n in range(5 + lvl + int(self.S["viper_pool_steps"])):
                    px = hx + ax * (0.9 + n * length / (4 + lvl))
                    py = hy + ay * (0.9 + n * length / (4 + lvl))
                    self.skill_zones.append(dict(x=px, y=py, r=1.15 + self.S["viper_pool_radius"],
                        t=5.5 + self.S["viper_pool_duration"] + lvl * 0.25, tick=0.0, dps=7 + self.S["venom"] + self.S["viper_pool_dps"] + lvl * 2, el="dendro", col=col))
                self.invincible = max(self.invincible, 0.18)
                self.effects.append([hx + ax * 2.2, hy + ay * 2.2, self.time, "slash", (col, ax, ay, 1.5)])
                self.set_message("TOXIC DOMINION - route enemies through persistent venom pools")
            elif self.S["viper_fang"] > 0:
                # Widow's Silence: the V cast is the setup for a single surgical hit.
                self.camo_t = max(self.camo_t, 2.8 + lvl * 0.25)
                self.buff_crit = max(self.buff_crit, 2.6)
                self.buff_dmg = max(self.buff_dmg, 1.1)
                self.invincible = max(self.invincible, 0.25)
                self.effects.append([hx + ax * 2.0, hy + ay * 2.0, self.time, "slash", (col, ax, ay, 2.2)])
                self.set_message("WIDOW'S SILENCE - camouflage on V; your next strike becomes lethal")
            elif self.S["viper_plague"] > 0:
                # Plague Heart: V still damages immediately, but converts venom kills into sustain.
                radius = 2.0 + self.S["aoe"] * 0.45 + lvl * 0.18
                healed = 0
                for e in self.enemies:
                    if e["dead"] or math.hypot(e["x"] - hx, e["y"] - hy) > radius:
                        continue
                    e["venom"] = max(e["venom"], 5.5)
                    e["venom_dps"] = max(e["venom_dps"], 8 + self.S["venom"] + lvl * 2)
                    self.hit_enemy(e, 16 * self.dmgm(), "dendro")
                    if e["dead"]:
                        healed += 1
                self.heal(self.maxhp * (0.08 + 0.03 * healed + 0.02 * self.S["viper_plague_bloom"]))
                self.effects.append([hx, hy, self.time, "blast", (radius, col)])
                self.set_message("PLAGUE HEART - venom bursts restore health")
            else:
                # Fallback for a fresh Viper before a keystone is chosen.
                for n in range(5 + lvl):
                    px = hx + ax * (0.9 + n * 1.2)
                    py = hy + ay * (0.9 + n * 1.2)
                    self.effects.append([px, py, self.time, "blast", (1.15, col)])
                self.set_message("VENOM TRAIL - choose a Viper keystone to specialize it")

        elif self.run_class == "python":
            radius = 3.3 + min(2.8, len(self.snake) / 24.0) + lvl * 0.22 + self.S["python_length_scale"] * max(0, len(self.snake) - 8) * 0.018
            base = 34 * (1 + self.S["melee"] / 100) * self.res_dmg()
            if self.S["python_titan"] > 0:
                base *= 1 + min(1.2, max(0, len(self.snake) - 12) * 0.018 * max(1, self.S["python_length_scale"]))
                self.add_shield(20 + len(self.snake) * 0.8)
                self.set_message(f"TITAN BODY - {len(self.snake)} segments converted into force and shielding")
            elif self.S["python_bastion"] > 0:
                self.bulwark_t = max(self.bulwark_t, 4.0 + lvl * 0.5)
                self.bulwark_pulse_t = 0.0
                self.add_shield(45 + self.S["bulwark_shield"])
                self.set_message("IRON CITADEL - V activates a mobile fortress pulse")
            elif self.S["python_constrictor"] > 0:
                radius += 1.0
                base *= 1.15
                for e in self.enemies:
                    if not e["dead"] and math.hypot(e["x"] - hx, e["y"] - hy) <= radius:
                        e["stun"] = max(e["stun"], 2.2 + lvl * 0.25)
                self.add_shield(30)
                self.set_message("IRON CONSTRICTOR - crush and lock the arena")
            for e in self.enemies:
                if not e["dead"] and math.hypot(e["x"] - hx, e["y"] - hy) <= radius:
                    self.hit_enemy(e, base, self.elem, melee=True)
                    if self.S["python_constrictor"] > 0:
                        e["stun"] = max(e["stun"], 1.5 + lvl * 0.18)
                    self.move_enemy(e, math.atan2(e["y"] - hy, e["x"] - hx), 24.0, 0.13)
            self.effects.append([hx, hy, self.time, "blast", (radius, col)])
            if self.S["python_titan"] <= 0 and self.S["python_bastion"] <= 0 and self.S["python_constrictor"] <= 0:
                self.set_message("COLOSSAL COIL - choose a Python keystone to specialize it")

        elif self.run_class == "cobra":
            base_ang = math.atan2(ay, ax)
            if self.S["cobra_artillery"] > 0:
                n = max(3, 5 + lvl // 2)
                gap = 0.055
                for i in range(n):
                    self.fire_bolt(base_ang + (i - (n - 1) / 2) * gap, 1.8 * self.rngm(), int(self.S["pierce"]) + 2 + int(self.S["volley_pierce"]), life=1.35)
                self.set_message("SERPENT CANNON - dense armor-piercing artillery volley")
            elif self.S["cobra_prism"] > 0:
                choices = [e for e in self.unlocked if e != "pulse"] or [self.elem]
                n = 5 + lvl + int(self.S["cobra_elemental"])
                for i in range(n):
                    el = choices[i % len(choices)]
                    ang = base_ang + (i - (n - 1) / 2) * 0.10
                    self.shots.append({"x": hx, "y": hy, "dx": math.cos(ang), "dy": math.sin(ang), "cell": self.snake[0],
                        "el": el, "pierce": int(self.S["pierce"]) + 1, "hit": set(), "mul": 1.0 + 0.06 * self.S["cobra_elemental"], "life": 1.2})
                self.buff_em = max(self.buff_em, 2.0)
                self.set_message("PRISMATIC COBRA - signature volleys cycle through your unlocked elements")
            elif self.S["cobra_barrage"] > 0:
                n = 9 + lvl + int(self.S["cobra_fan_count"])
                gap = 0.10 + self.S["cobra_fan_width"]
                for i in range(n):
                    ang = base_ang + (i - (n - 1) / 2) * gap
                    self.fire_bolt(ang, 1.15 * self.rngm(), int(self.S["pierce"]) + 1, life=1.2)
                self.blast(hx + ax * 3.0, hy + ay * 3.0, 2.0 + lvl * 0.25, self.trans_dmg(1.1), ECOL.get(self.elem, col))
                self.set_message("HYDRA BARRAGE - wide poison fan with an impact burst")
            else:
                n = 7 + lvl
                for i in range(n):
                    ang = base_ang + (i - (n - 1) / 2) * 0.12
                    self.fire_bolt(ang, 1.0 * self.rngm(), int(self.S["pierce"]) + 1, life=1.15)
                self.set_message("VENOM BARRAGE - choose a Cobra keystone to specialize it")

        else:
            reach = 5.2 + lvl * 0.5 + self.S["lunge"]
            hit_targets = []
            self.dash_t = max(self.dash_t, 0.14)
            self.invincible = max(self.invincible, 0.34 + self.S["iframe"])
            self.lunge_t = 0.28
            self.lunge_dir = (ax, ay)
            for e in self.enemies:
                if e["dead"]:
                    continue
                rx = (e["x"] - hx) * ax + (e["y"] - hy) * ay
                ry = -(e["x"] - hx) * ay + (e["y"] - hy) * ax
                if 0 <= rx <= reach and abs(ry) <= 1.25:
                    pre = e["hp"]
                    self.hit_enemy(e, 42 * self.dmgm() * (1.15 if self.S["mamba_executioner"] > 0 else 1.0), "electro", melee=True)
                    if not e["dead"] and self.S["mamba_executioner"] > 0 and e["hp"] < pre * 0.22:
                        self.damage_enemy(e, e["hp"] + 1, True)
                    if not e["dead"] or pre > e["hp"]:
                        hit_targets.append(e)
            for src in hit_targets:
                near = sorted((e for e in self.enemies if not e["dead"] and e is not src and math.hypot(e["x"]-src["x"], e["y"]-src["y"]) < 4.8),
                              key=lambda e: math.hypot(e["x"]-src["x"], e["y"]-src["y"]))[:2 + min(2, lvl) + int(self.S["mamba_chain"])]
                for e in near:
                    self.hit_enemy(e, self.trans_dmg(1.1) + self.S["chain"], "electro")
            if self.S["mamba_executioner"] > 0 and any(e["dead"] for e in hit_targets):
                self.cd["dash"] = 0.0
            if self.S["mamba_voidstep"] > 0:
                self.camo_t = max(self.camo_t, 2.4 + lvl * 0.2)
                self.decoy = {"x": float(hx + ax * 2.5), "y": float(hy + ay * 2.5), "t": 2.8}
            if self.S["mamba_tempo"] > 0 and hit_targets:
                self.cd["rattle"] = 0.0
                self.cd["dash"] = 0.0
            self.effects.append([hx + ax * 2.4, hy + ay * 2.4, self.time, "slash", (col, ax, ay, 2.0)])
            self.set_message("THUNDERCOIL - chain Electro through the pack")
        # Generic deep V-tree upgrades apply on top of every class signature.
        extra_multi = int(self.S["class_multi"])
        if extra_multi:
            if self.run_class == "cobra":
                for i in range(extra_multi):
                    off = (i - (extra_multi - 1) / 2) * 0.22
                    self.fire_bolt(math.atan2(ay, ax) + off, 0.82 * self.rngm(),
                                   int(self.S["pierce"]) + int(self.S["class_pierce"]), life=1.15,
                                   bounce=int(self.S["volley_bounce"]), explode=int(self.S["class_explode"]))
            else:
                for e in sorted((e for e in self.enemies if not e["dead"]),
                                key=lambda e: math.hypot(e["x"]-hx, e["y"]-hy))[:extra_multi]:
                    self.hit_enemy(e, self.trans_dmg(0.55), self.elem)
        if self.S["class_explode"]:
            self.blast(hx + ax * 2.2, hy + ay * 2.2, 1.2 + 0.45 * self.S["class_explode"],
                       self.trans_dmg(0.45 * self.S["class_explode"]), ECOL.get(self.elem, col))
        if self.S["class_energy"]:
            self.ammo = min(getattr(self, "energy_cap", 5), self.ammo + int(self.S["class_energy"]))
        if self.S["class_chain"]:
            near = sorted((e for e in self.enemies if not e["dead"] and math.hypot(e["x"]-hx, e["y"]-hy) <= 5.5),
                          key=lambda e: math.hypot(e["x"]-hx, e["y"]-hy))[:int(self.S["class_chain"])]
            for e in near:
                self.hit_enemy(e, self.trans_dmg(0.45), self.elem)
        self.v_evolve(hx, hy, ax, ay, col)

    def v_evolve(self, hx, hy, ax, ay, col):
        """SKILL TREE: allocated V-skill milestones add evolved effects on top of the cast."""
        lv = int(self.S["sk_v_lv"])
        vpow = max(0.0, self.S["skill_power_class_skill"])
        if vpow > 0:
            lv = min(5, lv + int(vpow / 12.0))
        sig_amp = 1.0 + vpow / 100.0
        if lv < 2:
            return
        cid = self.run_class
        near = lambda r: [e for e in self.enemies if not e["dead"] and math.hypot(e["x"] - hx, e["y"] - hy) <= r]
        ang = math.atan2(ay, ax)
        if cid == "viper":
            self.skill_zones.append(dict(x=hx, y=hy, r=1.7, t=5.0, tick=0.0, dps=(7 + lv * 2) * sig_amp, el="dendro", col=col))   # tier 2
            if lv >= 3:
                for e in near(4.0):
                    e["venom"] = max(e["venom"], 5.0)
                    e["venom_dps"] = max(e["venom_dps"], 7 + lv * 1.5)
            if lv >= 4:
                poisoned = [e for e in near(5.0) if e["venom"] > 0]
                if poisoned:
                    self.heal(self.maxhp * 0.04 * min(5, len(poisoned)))
            if lv >= 5:
                self.blast(hx, hy, 4.5, self.trans_dmg(1.6) * sig_amp, ECOL["dendro"])
        elif cid == "python":
            self.add_shield(25 * sig_amp)                                                                                       # tier 2
            if lv >= 3:
                for e in near(4.5 + len(self.snake) / 30.0):
                    e["stun"] = max(e["stun"], 1.5)
            if lv >= 4:
                r2 = 5.5 + len(self.snake) / 30.0
                self.blast(hx, hy, r2, self._melee_base(0.6), ECOL[self.elem] if self.elem in ECOL else col)
                for e in near(r2):
                    self.move_enemy(e, math.atan2(e["y"] - hy, e["x"] - hx), 14.0, 0.1)
            if lv >= 5:
                self.bulwark_t = max(self.bulwark_t, 3.0)
                self.add_shield(40 * sig_amp)
        elif cid == "cobra":
            for i in (-1, 1):                                                                                         # tier 2: +2 bolts
                self.fire_bolt(ang + i * 0.30, 1.0 * self.rngm() * sig_amp, int(self.S["pierce"]) + 1, life=1.2)
            if lv >= 3:
                self.blast(hx + ax * 4.0, hy + ay * 4.0, 2.6, self.trans_dmg(1.2), ECOL.get(self.elem, col))
            if lv >= 4:
                self.buff_dmg = max(self.buff_dmg, 4.0)
                self.buff_em = max(self.buff_em, 4.0)
            if lv >= 5:
                for i in range(12):
                    self.fire_bolt(i * math.tau / 12, 0.9 * self.rngm() * sig_amp, int(self.S["pierce"]), life=0.9)
        else:
            tg = sorted(self.enemies, key=lambda e: math.hypot(e["x"] - hx, e["y"] - hy))                             # tier 2: chain lightning
            hit = 0
            for e in tg:
                if e["dead"] or hit >= 2 or math.hypot(e["x"] - hx, e["y"] - hy) > 7.0:
                    continue
                self.hit_enemy(e, (self.trans_dmg(1.0) + self.S["chain"]) * sig_amp, "electro")
                self.effects.append([hx, hy, self.time, "volt_arc", (e["x"], e["y"])])
                hit += 1
            if lv >= 3:
                for e in near(5.0):
                    e["stun"] = max(e["stun"], 1.5)
            if lv >= 4:
                self.cd["dash"] = 0.0
                self.stam = min(self.maxstam, self.stam + 30)
            if lv >= 5:
                self.invincible = max(self.invincible, 0.9)
                self.blast(hx, hy, 4.2, self.trans_dmg(1.5) * sig_amp, ECOL["electro"])

    def camo(self):
        """Camouflage: enemies lose track of you unless you are right next to them."""
        if not self.ready_for("camo", 15):
            return
        prof = self.skill_profile("camo")
        self.spend(15, "camo", max(9.0, 25.0 - self.S["camo_cd"]))
        self.camo_t = prof["duration"]
        if prof.get("shot"):
            ax, ay = self.aim_vector()
            self.fire_bolt(math.atan2(ay, ax), 1.15 * self.rngm(), int(self.S["pierce"]) + 1, life=1.05,
                           bounce=max(0, int(self.S["volley_bounce"])), explode=int(prof.get("explode", 0)))
        if prof.get("dash"):
            self.dash_t = max(self.dash_t, 0.10)
        if prof.get("pulse"):
            hx, hy = self.snake_points()[0]
            self.effects.append([hx, hy, self.time, "blast", (2.0, "#9aa8c8")])
        if prof.get("crit"):
            self.buff_crit = max(self.buff_crit, 1.2)
        self.set_message("CAMOUFLAGE - enemies lose track of you unless you get close")

    def volley(self):
        """Fan of venom bolts toward the cursor (wider with the Ranged form and its tree nodes)."""
        if not self.ready_for("volley", 25):
            return
        prof = self.skill_profile("volley")
        self.spend(25, "volley", max(2.5, 7.0 - self.S["volley_cd"]))
        play_sound("player_volley", volume=0.65)
        ax, ay = self.aim_vector()
        base = math.atan2(ay, ax)
        n = prof["count"]
        gap = prof.get("fan_width", 0.17)
        if prof.get("artillery"):
            n = max(3, n - 2)
            gap *= 0.45
        for i in range(n):
            mul = prof["damage"] * (1.35 if prof.get("artillery") else 1.0)
            self.fire_bolt(base + (i - (n - 1) / 2) * gap, mul, prof["pierce"], life=1.25,
                           bounce=prof.get("bounce", 0), explode=prof.get("explode", 0), split=prof.get("split", 0),
                           reaction=prof.get("chain", 0))
        self.set_message(f"VOLLEY - {n} bolts  •  +{prof['pierce']} pierce")

    def bulwark(self):
        """Tank stance: damage reduction + a barrier. Tank form also stuns everything nearby."""
        if not self.ready_for("bulwark", 30):
            return
        prof = self.skill_profile("bulwark")
        self.spend(30, "bulwark", max(6.0, 16.0 - self.S["bulwark_cd"]))
        play_sound("skill", volume=0.6)
        self.bulwark_t = prof["duration"]
        self.bulwark_pulse_t = 0.15 if prof.get("pulse") else 999.0
        self.add_shield(prof["shield"] * (1.35 if prof.get("laststand") and self.hp < self.maxhp * 0.35 else 1.0))
        hx, hy = self.snake_points()[0]
        if prof.get("wave"):
            self.blast(hx, hy, 2.3 + prof["wave"] * 0.4, 12 + prof.get("damage", 0) * 2, "#ffa23c")
        if self.S["form_tank"] > 0:
            for e in self.enemies:
                if not e["dead"] and math.hypot(e["x"] - hx, e["y"] - hy) <= prof["radius"]:
                    e["stun"] = max(e["stun"], prof["stun"])
            self.effects.append([hx, hy, self.time, "blast", (prof["radius"], "#ffa23c")])
        self.float_text(hx, hy - 0.8, "BULWARK", "#ffa23c")
        self.set_message("BULWARK - 35% less damage for 5s and a barrier")
