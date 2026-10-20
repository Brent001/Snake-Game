"""Player stats: build recompute from the skill tree, XP/levelling, Genshin-style damage numbers."""
from collections import defaultdict

from ..config import AMMO_CAP, C_GOLD, FOOD_CAP, FOOD_HP, RESON_NODES, RUN_MULT, STEP_S
from ..data.classes import CLASSES
from ..data.elements import ELEMS
from ..data.tree_nodes import TREE
from ..data.active_skill_tree import SKILL_NODES, skill_nodes_for_line, skill_level
from ..audio import play_sound


class StatsMixin:
    def recompute(self):
        S = defaultdict(float)
        cnt = defaultdict(int)
        for nid in self.alloc:
            for k, v in TREE[nid]["stats"].items():
                S[k] += v
            if TREE[nid]["elem"]:
                cnt[TREE[nid]["elem"]] += 1
        for k, v in CLASSES[self.run_class]["stats"].items():       # class bonuses
            S[k] += v
        # ACTIVE SKILL TREE: every allocated node adds both its authored stat package
        # and a small, explicit per-skill combat multiplier. This makes even utility
        # nodes visibly matter in the actual cast instead of being tooltip-only.
        skill_power_weights = {"r": 0.0, "m": 1.50, "n": 3.00, "a": 5.00, "j": 4.00, "k": 8.00}
        active_alloc = getattr(self, "skill_alloc", set())
        for nid in active_alloc:
            n = SKILL_NODES.get(nid)
            if not n or not nid.startswith(self.run_class + ":"):
                continue
            for k, v in n["stats"].items():
                S[k] += v
            line = n.get("line")
            if line:
                S[f"skill_power_{line}"] += skill_power_weights.get(n.get("kind"), 0.0)
                S[f"skill_nodes_{line}"] += 1

        for line in ("basic", "v"):
            lv = skill_level(self.run_class, active_alloc, line)
            S["sk_%s_lv" % line] = lv
            if hasattr(self, "skill_lv"):
                self.skill_lv[line] = lv

        # Helpful HUD/inspector totals.
        S["skill_power_total"] = sum(v for k, v in S.items() if k.startswith("skill_power_") and k != "skill_power_total")
        # Elemental Resonance (needs RESON_NODES nodes of one element)
        self.reson = {e for e in ELEMS if cnt[e] >= RESON_NODES}
        if "abyss" in self.reson:
            S["steal"] += 3
        if "light" in self.reson:
            S["xp"] += 10
        if "anemo" in self.reson:
            S["speed"] += 10
        self.S = S
        self.unlocked = [e for e in ELEMS if cnt[e] > 0]
        food_hp = min(self.food_eaten, FOOD_CAP) * (FOOD_HP + S["foodhp"])      # every food you eat makes you sturdier
        hp_base = 100 + 8 * (self.level - 1) + S["hp"] + food_hp
        self.maxhp = max(30.0, hp_base * (1 + S["hp_pct"] / 100) * (1.25 if "hydro" in self.reson else 1.0))
        self.maxstam = 100 + S["stam"]
        self.energy_cap = max(1, (AMMO_CAP if getattr(self, "boss", {}).get("state") == "fight" else 5) + int(S["ammo"]) + int(S["energy_max"]))
        if hasattr(self, "hp"):
            self.hp = min(self.hp, self.maxhp)
            self.stam = min(self.stam, self.maxstam)
        if self.elem != "pulse" and self.elem not in self.unlocked:
            self.elem = "pulse"

    def res_dmg(self):
        return 1.25 if "pyro" in self.reson else 1.0

    def dmgm(self):
        return max(0.2, 1 + self.S["dmg"] / 100) * (1.5 if self.buff_dmg > 0 else 1.0) * self.res_dmg()

    def rngm(self):
        """Ranged bolt damage multiplier."""
        return max(0.3, 1 + self.S["rng"] / 100) * (1.5 if self.buff_dmg > 0 else 1.0) * self.res_dmg()

    def speedf(self):
        return max(0.5, 1 + (self.S["speed"] + (30 if self.buff_speed > 0 else 0)) / 100)

    def step_s(self):
        return (STEP_S / self.speedf() * (0.28 if self.dash_t > 0 else 1.0) / (RUN_MULT if self.running else 1.0)
            * (1.55 if getattr(self, "slow_t", 0.0) > 0 else 1.0))      # Cirno's frost slows you

    def need(self):
        return int(45 * self.level ** 1.45)

    # ---- Genshin-style numbers
    def get_em(self):
        return self.S["em"] + (50 if "dendro" in self.reson else 0) + (100 if self.buff_em > 0 else 0)

    def amp_bonus(self):
        em = self.get_em()
        return 1 + 2.78 * em / (em + 1400)

    def trans_base(self):
        return 12 * 1.04 ** (self.level - 1)

    def trans_dmg(self, coef):
        em = self.get_em()
        return self.trans_base() * coef * (1 + 16 * em / (em + 2000))

    def crit_rate(self):
        return 5 + self.S["crit"] + (25 if self.buff_crit > 0 else 0)

    def skill_amp(self, skill):
        """Direct multiplier earned from allocated nodes in that skill's tree."""
        return 1.0 + max(0.0, self.S[f"skill_power_{skill}"]) / 100.0

    def skill_profile(self, skill):
        """Return final runtime parameters after class + tree modifiers.

        Every field in this profile is read by the actual ability implementation,
        so allocating a skill-affinity node changes gameplay rather than only the tooltip.
        """
        s = self.S
        if skill == "dash":
            amp = self.skill_amp("dash")
            return dict(length=(3 + int(s["dashlen"]) + s["dash_bonus"] + s["dash_len"]) * amp,
                        cooldown=max(0.30, (1.3 - s["dashcd"] - 0.08 * s["dash_reset"]) / amp),
                        reset_on_kill=s["mamba_dash_reset"] > 0 or s["dash_reset"] > 0,
                        iframes=0.18 + s["iframe"] + s["dash_iframes"],
                        explode=s["dash_explode"], afterimage=s["dash_afterimage"], speed=s["dash_speed"],
                        lifesteal=s["dash_lifesteal"])
        if skill == "strike":
            amp = self.skill_amp("strike")
            return dict(reach=(2.4 + s["lunge"]) * (0.94 + 0.06 * amp),
                        width=0.95 + (0.8 if s["form_tank"] > 0 else 0.0) + s["strike_width"] + s["strike_arc"],
                        stun=0.5 + (0.4 if s["form_tank"] > 0 else 0.0) + s["strike_stun"],
                        venom=3 + s["venom"] + s["strike_venom"],
                        cooldown=0.35 if s["form_mamba"] > 0 else max(0.28, 0.7 - s["strike_cd"] - 0.03 * s["strike_reset"]),
                        execute=(1 + s["mamba_executioner"] * 0.35) * amp,
                        crit_window=s["viper_camo_burst"] > 0, power=amp, multi=1 + int(s["strike_multi"]),
                        repeat=s["strike_repeat"], explode=s["strike_explode"], wave=s["strike_wave"],
                        element=s["strike_element"], mark=s["strike_mark"])
        if skill == "fang":        # VIPER basic attack: short, fast, venom-stacking bite
            amp = self.skill_amp("strike")
            return dict(reach=(1.9 + s["lunge"] * 0.6) * (0.96 + 0.04 * amp), width=0.7 + s["strike_width"] * 0.7, targets=2 + int(s["sk_targets"]),
                        damage=0.7 * (1 + s["sk_dmg"]) * amp, stun=0.12 + s["strike_stun"] * 0.5,
                        venom=4 + s["venom"] + s["strike_venom"], stack_dps=1.5 + s["strike_venom"] * 0.4, venom_time=5.0,
                        cooldown=max(0.16, (0.42 - s["strike_cd"]) * (1 - s["sk_cd"])), ambush=s["viper_fang"] > 0,
                        poison_bonus=1.3 + s["sk_poison"], spread=s["sk_spread"] > 0)
        if skill == "slam":        # PYTHON basic attack: slow 360-degree tail slam
            amp = self.skill_amp("strike")
            return dict(radius=(2.5 + s["lunge"] * 0.5 + s["strike_width"] * 1.5 + s["sk_radius"]) * (0.97 + 0.03 * amp), damage=0.95 * (1 + s["sk_dmg"]) * amp,
                        stun=0.9 + s["strike_stun"], knock=18.0 + s["sk_knock"],
                        cooldown=max(0.4, (0.95 - s["strike_cd"]) * (1 - s["sk_cd"])),
                        tip=1.25 + s["sk_tip"], shield=1.5 + s["sk_shield"], cap=4 + int(s["sk_cap"]))
        if skill == "volt":        # MAMBA basic attack: wide aim-assisted lightning slash
            amp = self.skill_amp("strike")
            return dict(reach=(3.8 + s["lunge"] * 0.8 + s["sk_reach"]) * (0.97 + 0.03 * amp), arc=0.72 + s["strike_width"] * 0.5, assist=0.55,
                        damage=1.1 * (1 + s["sk_dmg"]) * amp,
                        cooldown=max(0.12, (0.36 - s["strike_cd"] * 0.5) * (1 - s["sk_cd"])), execute=1 + s["mamba_executioner"] * 0.35,
                        arcs=3 + int(s["sk_arcs"]), weak=0.35 + s["sk_exec"], refund=1 + s["sk_refund"])
        if skill == "bolt":        # COBRA basic attack (and any class in the Ranged form): aimed elemental bolt
            amp = self.skill_amp("strike")
            return dict(count=1 + int(s["sk_bolts"]) + int(s["strike_multi"]),
                        pierce=int(s["pierce"]) + int(s["sk_pierce"]) + int(s["class_pierce"]),
                        mul=0.9 * self.rngm() * (1 + s["sk_dmg"]) * amp,
                        cooldown=max(0.10, (0.30 * (1 - s["sk_cd"]) - s["strike_cd"]) / amp),
                        gap=0.13 + s["strike_arc"] * 0.15, bounce=int(s["strike_bounce"]),
                        explode=int(s["strike_explode"]), split=int(s["strike_split"]),
                        explode_reaction=s["strike_reaction"], repeat=int(s["strike_repeat"]))
        if skill == "coil":
            amp = self.skill_amp("coil")
            return dict(duration=(4.0 + s["coil"] * 0.1 + s["python_constrictor"] * 1.5) * (0.98 + 0.02 * amp),
                        dps=(8 + s["coil"] + s["coil_dps"] + s["python_root"] * 4) * amp,
                        slow=0.3 + s["coil_slow"] + s["python_root"] * 0.15,
                        guard=30 + s["coil_guard"] + s["coil_shield"],
                        cooldown=max(3.0, 12.0 - s["coil_cd"]),
                        root=s["python_root"] > 0 or s["python_constrictor"] > 0,
                        radius=4.2 + s["coil_radius"], echo=s["coil_echo"], pulse=s["coil_pulse"],
                        explode=s["coil_explode"], burst=s["coil_burst"], reflect=s["coil_reflect"], execute=s["coil_execute"])
        if skill == "shed":
            amp = self.skill_amp("shed")
            return dict(heal=(0.25 + s["shed"] / 100 + s["shed_heal"]) * amp, iframe=(1.2 + s["shed_iframe"]) * (0.98 + 0.02 * amp), decoy=(6.0 + s["shed_decoy"]) * (0.98 + 0.02 * amp),
                        burst=s["shed_burst"], copies=1 + int(s["shed_copies"]), guard=s["shed_guard"],
                        thorns=s["shed_thorns"], overheal=s["shed_overheal"], reset=s["shed_reset"])
        if skill == "heat":
            amp = self.skill_amp("heat")
            return dict(duration=(8.0 + s["heat"] + s["heat_bonus"]) * (0.98 + 0.02 * amp), multiplier=(1.2 + s["heat_mult"] + 0.03 * s["heat_mark"]) * amp,
                        pulse=s["heat_pulse"], repeat=s["heat_repeat"], crit=s["heat_crit"], fast=s["heat_fast"], energy=s["heat_energy"], burst=s["heat_burst"])
        if skill == "scent":
            amp = self.skill_amp("scent")
            return dict(duration=(5.0 + s["scent_time"]) * (0.98 + 0.02 * amp), range=(12.0 + s["scent_range"]) * (0.98 + 0.02 * amp),
                        multi=1 + int(s["scent_multi"]), mark=s["scent_mark"], magnet=s["scent_magnet"], damage=s["scent_damage"], speed=s["scent_speed"], reset=s["scent_reset"])
        if skill == "spit":
            amp = self.skill_amp("spit")
            return dict(reach=(9.0 + s["spit_reach"]) * (0.98 + 0.02 * amp), stun=(1.0 + s["spit_stun"]) * (0.98 + 0.02 * amp), damage=(8.0 + s["spit_damage"]) * amp, width=1.0 + s["spit_width"] + s["spit_spread"],
                        count=1 + int(s["spit_count"]), bounce=int(s["spit_bounce"]), explode=int(s["spit_explode"]), chain=int(s["spit_chain"]), element=s["spit_element"], venom=s["spit_venom"], reaction=s["spit_reaction"])
        if skill == "rattle":
            amp = self.skill_amp("rattle")
            return dict(radius=(5.5 + s["rattle_radius"]) * (0.97 + 0.03 * amp), stun=(1.6 + s["rattle_stun"]) * (0.98 + 0.02 * amp), force=(20.0 + s["rattle_force"]) * amp, clear=3.5 + s["rattle_radius"] * 0.55 + s["rattle_clear"],
                        pulses=1 + int(s["rattle_pulses"]), wave=s["rattle_wave"], guard=s["rattle_guard"], energy=s["rattle_energy"], on_kill=s["rattle_on_kill"])
        if skill == "camo":
            amp = self.skill_amp("camo")
            return dict(duration=(6.0 + s["camo_time"]) * (0.98 + 0.02 * amp), proximity=max(1.2, (3.0 - s["camo_range"]) * (1.02 - min(0.10, amp-1.0))),
                        shot=s["camo_shot"], crit=s["camo_crit"], explode=s["camo_explode"], dash=s["camo_dash"], reset=s["camo_reset"], clone=s["camo_clone"], pulse=s["camo_pulse"])
        if skill == "volley":
            amp = self.skill_amp("volley")
            return dict(count=3 + int(s["volley"]) + int(s["volley_count"]) + int(s["volley_multi"]) + (2 if s["form_ranged"] > 0 else 0) + int((amp-1)*2.5),
                        damage=0.7 * self.rngm() * (1 + s["volley_damage"]) * amp,
                        pierce=int(s["pierce"]) + int(s["volley_pierce"]) + (1 if s["form_ranged"] > 0 else 0),
                        fan_width=0.17 + s["cobra_fan_width"], artillery=s["cobra_artillery"] > 0,
                        bounce=int(s["volley_bounce"]), explode=int(s["volley_explode"]), split=int(s["volley_split"]),
                        element=s["volley_element"], chain=int(s["volley_chain"]))
        if skill == "bulwark":
            amp = self.skill_amp("bulwark")
            return dict(duration=(5.0 + s["bulwark_time"] + 0.7 * s["bulwark_extend"]) * (0.98 + 0.02 * amp),
                        shield=(30 + s["bulwark"] + s["bulwark_shield"] + s["bulwark_hp"] + (18 if s["python_bastion"] else 0)) * amp * (1 + 0.06 * s["bulwark_scale"]),
                        radius=4.5 + s["bulwark_radius"] + (0.8 if s["python_bastion"] else 0),
                        stun=1.2 + s["bulwark_radius"] * 0.08 + (0.25 if s["python_bastion"] else 0),
                        pulse=s["python_pulse"] > 0 or s["bulwark_pulse"] > 0, reflect=s["bulwark_reflect"],
                        wave=s["bulwark_wave"], damage=s["bulwark_damage"], laststand=s["bulwark_laststand"], regen=s["bulwark_regen"])
        return {}

    def add_shield(self, n):
        gain = n * (1 + self.S["shield_pct"] / 100) * (1.15 if "geo" in self.reson else 1.0)
        cap = 100.0 + self.S["shield_pct"] * 1.5
        self.shield = min(cap, self.shield + gain)

    def add_xp(self, n):
        n *= 1 + self.S["xp"] / 100
        self.xp += n
        hx, hy = self.snake[0]
        self.float_text(hx, hy - 0.8, f"+{int(n)} XP", C_GOLD)
        while self.xp >= self.need():
            self.xp -= self.need()
            self.level += 1
            self.points += 1
            self.skill_pts += 1
            self.recompute()
            self.hp, self.stam = self.maxhp, self.maxstam
            self.float_text(hx, hy - 1.4, f"LEVEL UP! {self.level}", "#ffffff")
            play_sound("levelup", volume=0.9)
            self.set_message(f"LEVEL {self.level}!  +1 passive point  +1 skill point    |    TAB = passive tree / skill tree")
        self.update_hud()

    def heal(self, n):
        before = self.hp
        self.hp = min(self.maxhp, self.hp + n)
        if self.hp - before >= 1:
            hx, hy = self.snake[0]
            self.float_text(hx, hy - 0.6, f"+{int(self.hp - before)}", "#5dffb0")

    def float_text(self, x, y, text, col):
        self.floats.append([x, y, text, col, self.time])
        if len(self.floats) > 50:
            self.floats.pop(0)


# Bosses are deliberately more durable than normal mobs, but the multiplier stays in the readable 0.45-0.75 range.
def _boss_damage_factor(self):
    b = getattr(self, "boss", {})
    if b.get("state") != "fight":
        return 1.0
    phase = int(b.get("phase", 0))
    return max(0.45, 0.74 - phase * 0.05)

StatsMixin.boss_damage_factor = _boss_damage_factor
