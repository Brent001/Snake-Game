"""Elemental auras and reactions (amplifying, transformative, quicken) plus Bloom cores and Hyperbloom missiles."""
import math
import random

from ..data.elements import ECOL, REACT


class ReactionsMixin:
    def apply_aura(self, e, el):
        if el == "pulse":
            return None
        aur = e["aura"]
        e.setdefault("aura_g", 0.0)
        if aur == "quicken":
            if el == "dendro":
                return "spread"
            if el == "electro":
                return "aggravate"
            if el in ("anemo", "geo"):
                return None
            e["aura"], e["aura_t"], e["aura_g"] = el, 5.0, 1.0
            return None
        if aur and aur != el:
            r = "swirl" if el == "anemo" else "crystallize" if el == "geo" else REACT.get(frozenset((aur, el)))
            if r == "quicken":
                e["aura"], e["aura_t"], e["aura_g"] = "quicken", 7.0, 1.0
                self.float_text(e["x"], e["y"] - 0.9, "QUICKEN", ECOL["quicken"])
                return "quicken"
            if r:
                e["aura"], e["aura_t"] = None, 0.0
                self.reaction(r, e, aur)
                return r
        elif el == "anemo" and not aur:
            return None
        if el not in ("anemo", "geo"):
            e["aura"], e["aura_t"], e["aura_g"] = el, 5.0, 1.0
        return None

    def blast(self, x, y, radius, dmg, col, aura=None):
        self.effects.append([x, y, self.time, "blast", (radius, col)])
        for o in self.enemies:
            if not o["dead"] and math.hypot(o["x"] - x, o["y"] - y) <= radius:
                if aura:
                    o["aura"], o["aura_t"], o["aura_g"] = aura, 4.0, 0.65
                self.damage_enemy(o, dmg)

    def reaction(self, name, e, aur):
        S = self.S
        x, y = e["x"], e["y"]
        col = {"vaporize": "#4aa8ff", "melt": "#ff9a3a", "freeze": "#9fefff", "overload": "#ff6a3a",
            "electro-charged": "#c18bff", "superconduct": "#c18bff", "burning": "#ff6a3a", "bloom": "#7ddb4a",
            "swirl": "#6fffd0", "crystallize": "#f5c542", "eclipse": "#ffffff"}[name]
        self.float_text(x, y - 0.9, name.upper(), col)
        self.vfx_impact(x, y, col, 1.6, element=aur or "pulse", critical=True, boss=False)
        self.vfx_flash_screen(col, 0.16, 0.11)
        if "electro" in self.reson and name in ("overload", "electro-charged", "superconduct"):
            self.stam = min(self.maxstam, self.stam + 12)   # High Voltage
        if name == "freeze":
            e["freeze"] = 1.6 + S["freeze"]
        elif name == "overload":
            r = 2.2 + S["aoe"]
            self.blast(x, y, r, self.trans_dmg(2.0), "#ff6a3a")
            for o in self.enemies:                          # knockback
                if not o["dead"] and o is not e and 0.1 < math.hypot(o["x"] - x, o["y"] - y) <= r:
                    self.move_enemy(o, math.atan2(o["y"] - y, o["x"] - x), 15.0, 0.1)
        elif name == "electro-charged":
            near = sorted((o for o in self.enemies if not o["dead"] and o is not e and math.hypot(o["x"] - x, o["y"] - y) < 3.4),
                key=lambda o: math.hypot(o["x"] - x, o["y"] - y))[:3]
            for o in near:
                self.damage_enemy(o, self.trans_dmg(1.2) + S["chain"])
                self.effects.append([o["x"], o["y"], self.time, "hit"])
        elif name == "superconduct":
            r = 2.0 + S["aoe"]
            self.blast(x, y, r, self.trans_dmg(0.5), "#c18bff")
            for o in self.enemies:
                if not o["dead"] and math.hypot(o["x"] - x, o["y"] - y) <= r + 0.4:
                    o["shred"] = 12.0                       # -40% physical resistance for 12s
        elif name == "burning":
            e["burn"] = 5.0
        elif name == "bloom":
            self.heal(3 + S["bloom"] * 4)
            for _ in range(2):                              # dendro cores: pyro -> Burgeon, electro -> Hyperbloom
                if len(self.cores) < 8:
                    self.cores.append([x + random.uniform(-1.2, 1.2), y + random.uniform(-1.2, 1.2), 6.0])
        elif name == "swirl":
            r = 1.8 + S["aoe"]
            self.blast(x, y, r, self.trans_dmg(0.6) * (1 + S["swirl"] * 0.5), ECOL[aur], aura=aur)
            for o in self.enemies:
                if not o["dead"] and math.hypot(o["x"] - x, o["y"] - y) <= r:
                    o["vv_el"], o["vv_t"] = aur, 10.0       # swirled element resistance shred
        elif name == "crystallize":
            self.add_shield(20 + S["crystal"] * 20)
        elif name == "eclipse":
            self.blast(x, y, 3.0 + S["aoe"], self.trans_dmg(3.3) * (1 + S["eclipse"] * 0.5), ECOL["light"])

    def bloom_dmg(self):
        return self.trans_dmg(2.0) * (1 + self.S["bloom"] * 0.25)

    def shot_hits_core(self, s):
        if s["el"] not in ("pyro", "electro"):
            return False
        for core in self.cores:
            if math.hypot(core[0] - s["x"], core[1] - s["y"]) < 0.8:
                self.cores.remove(core)
                if s["el"] == "pyro":
                    r = 3.0 + self.S["aoe"]
                    self.blast(core[0], core[1], r, self.trans_dmg(3.0), ECOL["pyro"])
                    self.float_text(core[0], core[1] - 0.9, "BURGEON", ECOL["pyro"])
                    hx, hy = self.snake[0]
                    if math.hypot(hx - core[0], hy - core[1]) < r * 0.8:
                        self.hurt(5)                        # Burgeon also scorches you
                else:
                    self.missiles.append([core[0], core[1], self.trans_dmg(3.0), 4.0])
                    self.float_text(core[0], core[1] - 0.9, "HYPERBLOOM", ECOL["electro"])
                return True
        return False

    def update_cores(self, dt):
        keep = []
        for core in self.cores:
            core[2] -= dt
            if core[2] <= 0:
                self.blast(core[0], core[1], 1.8 + self.S["aoe"], self.bloom_dmg(), ECOL["dendro"])
            else:
                keep.append(core)
        self.cores = keep

    def update_missiles(self, dt):
        keep = []
        for m in self.missiles:
            m[3] -= dt
            targets = [o for o in self.enemies if not o["dead"] and math.hypot(o["x"] - m[0], o["y"] - m[1]) < 22]
            if m[3] <= 0 or not targets:
                continue
            t = min(targets, key=lambda o: math.hypot(o["x"] - m[0], o["y"] - m[1]))
            ang = math.atan2(t["y"] - m[1], t["x"] - m[0])
            m[0] += math.cos(ang) * 13 * dt
            m[1] += math.sin(ang) * 13 * dt
            if math.hypot(t["x"] - m[0], t["y"] - m[1]) < 0.7:
                self.damage_enemy(t, m[2])
                self.effects.append([t["x"], t["y"], self.time, "hit"])
                continue
            keep.append(m)
        self.missiles = keep
