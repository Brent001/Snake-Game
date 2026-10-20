"""Class-exclusive PoE-inspired passive trees.

Each playable class owns a different constellation with a single always-active class
core at the exact center.  The core replaces the old separate origin socket so the
player starts directly at the class identity and can immediately route into the
passive network.  Large keystones are mutually exclusive build choices.
"""
from collections import defaultdict
import math
from .elements import LABEL


def N(name, kind, **stats):
    return (name, kind, stats)


KIND_NAME = {
    "c": "Class Core",
    "g": "Gateway",
    "m": "Minor",
    "n": "Notable",
    "a": "Major",
    "j": "Jewel Socket",
    "k": "Keystone",
}

# All class trees use the same spatial grammar but have different names, mechanics,
# affinities and keystone doctrines.  Coordinates are deliberately wide enough that
# the sockets remain legible on 1366x730 and still reward zoom/pan on larger screens.

TREE_DEFS = {
    "viper": dict(
        title="VIPER // VENOM ARCHITECT",
        role="DOT / SETUP / EXECUTE",
        col="#d6ff49",
        subtitle="Build poison zones, exploit camouflage, or turn venom into sustain.",
        branches=[
            ("TOXIC ALCHEMY", "Viper turns space into a hazard.", [
                ((-92, -154), N("Venom Sacs", "g", venom=3)),
                ((-178, -202), N("Caustic Glands", "m", venom=3, strike_venom=1)),
                ((-274, -174), N("Toxic Radius", "m", viper_pool_radius=0.45, viper_pool_dps=2)),
                ((-368, -226), N("Lingering Bile", "n", viper_pool_duration=1.8, strike_venom=2)),
                ((-474, -162), N("KEystone: TOXIC DOMINION", "k", viper_alchemist=1, class_skill=2, viper_pool_steps=3),
                 "V creates persistent venom pools that keep damaging enemies after the cast."),
                ((-226, -270), N("Venom Recall", "m", viper_pool_steps=1, scent_range=2)),
                ((-340, -112), N("Corrosive Fangs", "m", melee=8, strike_venom=2)),
            ]),
            ("SILENT HUNT", "Camouflage becomes a burst window.", [
                ((92, -154), N("Shadow Scales", "g", camo_time=1.2, camo_range=0.25)),
                ((178, -202), N("Patient Killer", "m", crit=4, cdmg=10)),
                ((274, -174), N("Close Quarters", "m", lunge=0.55, strike_width=0.12)),
                ((368, -226), N("First Fang", "n", dmg=10, strike_stun=0.12)),
                ((474, -162), N("KEystone: WIDOW'S SILENCE", "k", viper_fang=1, class_skill=2, viper_camo_burst=1),
                 "V grants camouflage and primes the next STRIKE for a brutal critical hit."),
                ((226, -270), N("Silent Step", "m", camo_range=0.35, speed=3)),
                ((340, -112), N("Execution Venom", "m", crit=3, strike_venom=3)),
            ]),
            ("PLAGUE FEAST", "Venom feeds health, area control and reactions.", [
                ((-45, 56), N("Blood Toxin", "g", steal=1, venom=2)),
                ((-112, 128), N("Carrion Feed", "m", shed_heal=0.04, regen=0.3)),
                ((0, 190), N("Rot Bloom", "m", aoe=0.45, viper_plague_bloom=1)),
                ((112, 128), N("Shed to Survive", "n", shed_iframe=0.18, shed_decoy=0.8)),
                ((0, 292), N("KEYSTONE: PLAGUE HEART", "k", viper_plague=1, class_skill=2, steal=2, viper_plague_bloom=2),
                 "Poisoned targets release a healing burst when the Viper lands the signature skill."),
                ((-152, 198), N("Virulent Mist", "m", aoe=0.5, viper_pool_radius=0.25)),
                ((152, 198), N("Hungry Venom", "m", steal=1.5, venom=2)),
            ]),
        ],
        masteries=[
            ((-150, -34), N("DENDRO: Bloom Fang", "n", elem_dendro=1, em=30, spit_damage=2)),
            ((150, -34), N("ABYSS: Venom Eclipse", "n", elem_abyss=1, em=30, strike_venom=2)),
            ((-118, 334), N("HYDRO: Cleansing Coil", "n", elem_hydro=1, shed_heal=0.04)),
            ((118, 334), N("CRYO: Cold Toxin", "n", elem_cryo=1, strike_stun=0.14, coil_slow=0.12)),
        ],
    ),
    "python": dict(
        title="PYTHON // COLOSSAL ENGINE",
        role="TANK / CONTROL / BODY SCALING",
        col="#ff9f2f",
        subtitle="Turn snake length into armor, crush zones, and fortress uptime.",
        branches=[
            ("COLOSSUS", "Every extra body segment becomes power.", [
                ((-92, -154), N("Dense Muscle", "g", hp=18, armor=3)),
                ((-178, -202), N("Heavy Scales", "m", armor=5, wallres=8)),
                ((-274, -174), N("Mass Conversion", "m", python_length_scale=1)),
                ((-368, -226), N("Bodyweight", "n", melee=9, python_body_damage=0.5)),
                ((-474, -162), N("KEYSTONE: TITAN BODY", "k", python_titan=1, class_skill=2, python_length_scale=2, hp=30),
                 "Damage and shielding scale hard with snake length. Short snakes are weaker but agile builds remain possible."),
                ((-226, -270), N("Long Frame", "m", hp=15, python_length_scale=0.7)),
                ((-340, -112), N("Shoulder Charge", "m", strike_width=0.2, strike_stun=0.14, melee=8)),
            ]),
            ("BASTION", "Bulwark becomes an active fortress.", [
                ((92, -154), N("Plated Hide", "g", armor=5, bulwark_shield=6)),
                ((178, -202), N("Brace", "m", bulwark_time=1.0, bulwark_shield=8)),
                ((274, -174), N("Guard Pulse", "m", bulwark_radius=0.5, bulwark_stun=0.15)),
                ((368, -226), N("Counterweight", "n", bulwark=12, melee=8)),
                ((474, -162), N("KEYSTONE: IRON CITADEL", "k", python_bastion=1, class_skill=2, bulwark=25, python_pulse=1),
                 "BULWARK gains repeated shock pulses and a much larger barrier while active."),
                ((226, -270), N("Fortified Core", "m", hp=20, armor=4)),
                ((340, -112), N("Last Stand", "m", bulwark_shield=10, wallres=10)),
            ]),
            ("CONSTRICTOR", "Own a zone with Coil and forced movement.", [
                ((-45, 56), N("Long Coil", "g", coil=4, coil_dps=2)),
                ((-112, 128), N("Crushing Wrap", "m", coil_guard=5, coil_slow=0.1)),
                ((0, 190), N("Lockdown", "m", python_root=1, coil_slow=0.16, strike_stun=0.1)),
                ((112, 128), N("Drag Under", "n", rattle_force=7, bulwark_radius=0.3)),
                ((0, 292), N("KEYSTONE: IRON CONSTRICTOR", "k", python_constrictor=1, class_skill=2, coil=6, coil_dps=4),
                 "COIL roots enemies and the signature crush slams the arena edge, turning routing into crowd control."),
                ((-152, 198), N("Pressure Point", "m", coil_dps=2, strike_stun=0.12)),
                ((152, 198), N("Ground Grip", "m", coil_guard=5, wallres=10)),
            ]),
        ],
        masteries=[
            ((-150, -34), N("GEO: Bedrock Frame", "n", elem_geo=1, armor=5, coil_guard=5)),
            ((150, -34), N("HYDRO: Flowing Bulk", "n", elem_hydro=1, hp=15, shed_heal=0.03)),
            ((-118, 334), N("CRYO: Glacier Grip", "n", elem_cryo=1, coil_slow=0.15, strike_stun=0.1)),
            ((118, 334), N("PYRO: Furnace Skin", "n", elem_pyro=1, heat_bonus=1.2, dmg=6)),
        ],
    ),
    "cobra": dict(
        title="COBRA // VENOM ARTILLERY",
        role="RANGED / REACTIONS / BURST",
        col="#ff5da2",
        subtitle="Choose between relentless barrages, precision artillery, or reaction overload.",
        branches=[
            ("MANY FANGS", "Convert every attack into a wider projectile pattern.", [
                ((-92, -154), N("Twin Fangs", "g", volley_count=1, spit_damage=1)),
                ((-178, -202), N("Forked Venom", "m", volley_count=1, volley_damage=0.05)),
                ((-274, -174), N("Wide Hood", "m", cobra_fan_width=0.06, spit_width=0.16)),
                ((-368, -226), N("Quick Load", "n", ammo=1, volley_cd=0.3)),
                ((-474, -162), N("KEYSTONE: HYDRA BARRAGE", "k", cobra_barrage=1, class_skill=2, cobra_fan_count=5, volley_count=2),
                 "VENOM BARRAGE becomes a huge multi-angle fan with chained afterbursts."),
                ((-226, -270), N("Extra Fangs", "m", volley_count=1, pierce=1)),
                ((-340, -112), N("Toxic Magazine", "m", volley_damage=0.06, spit_damage=2)),
            ]),
            ("SIEGE", "Trade rate for range, pierce and devastating aimed shots.", [
                ((92, -154), N("Long Hood", "g", rng=8, spit_reach=1.2)),
                ((178, -202), N("Piercing Tip", "m", pierce=1, volley_pierce=1)),
                ((274, -174), N("Marked Target", "m", cobra_mark=1, crit=3, cdmg=10)),
                ((368, -226), N("Deep Pressure", "n", spit_damage=4, spit_reach=1.6)),
                ((474, -162), N("KEYSTONE: SERPENT CANNON", "k", cobra_artillery=1, class_skill=2, rng=15, spit_reach=3.0, cobra_shot_scale=1),
                 "VENOM BARRAGE compresses into fewer, extremely fast artillery bolts with massive pierce."),
                ((226, -270), N("Dead Eye", "m", crit=4, cdmg=8)),
                ((340, -112), N("Puncture", "m", pierce=2, volley_pierce=1)),
            ]),
            ("REACTION LAB", "Treat elements as ammunition, not decoration.", [
                ((-45, 56), N("Catalyst Sacs", "g", em=35, charges=1)),
                ((-112, 128), N("Primer Venom", "m", cobra_reaction=1, venom=2)),
                ((0, 190), N("Element Mixer", "m", em=45, cobra_elemental=1)),
                ((112, 128), N("Reactive Burst", "n", aoe=0.5, cobra_reaction=1, dmg=5)),
                ((0, 292), N("KEYSTONE: PRISMATIC COBRA", "k", cobra_prism=1, class_skill=2, cobra_elemental=2, em=70),
                 "The signature volley cycles through unlocked elements, forcing reactions instead of repeating one element."),
                ((-152, 198), N("Charge Reservoir", "m", ammo=1, charges=1)),
                ((152, 198), N("Resonant Fang", "m", em=40, volley_damage=0.04)),
            ]),
        ],
        masteries=[
            ((-150, -34), N("DENDRO: Bloom Array", "n", elem_dendro=1, em=35, venom=3)),
            ((150, -34), N("PYRO: Overheat Array", "n", elem_pyro=1, dmg=8, heat_bonus=1.0)),
            ((-118, 334), N("HYDRO: Rain Arsenal", "n", elem_hydro=1, regen=0.6, spit_damage=2)),
            ((118, 334), N("LIGHT: Prism Pierce", "n", elem_light=1, pierce=2, volley_pierce=1)),
        ],
    ),
    "mamba": dict(
        title="MAMBA // THUNDER ASSASSIN",
        role="ASSASSIN / MOBILITY / CHAIN",
        col="#e6ff4a",
        subtitle="Dash through targets, chain lightning, and turn timing windows into resets.",
        branches=[
            ("VOLT RUSH", "Mobility is the damage engine.", [
                ((-92, -154), N("Live Wire", "g", speed=4, dashcd=0.12)),
                ((-178, -202), N("Flash Step", "m", dash_bonus=0.4, iframe=0.08)),
                ((-274, -174), N("Arc Through", "m", mamba_chain=1, rattle_radius=0.4)),
                ((-368, -226), N("Voltage Leak", "n", chain=5, rattle_stun=0.12)),
                ((-474, -162), N("KEYSTONE: LIGHTNING EXECUTIONER", "k", mamba_executioner=1, class_skill=2, mamba_chain=3, crit=6),
                 "THUNDERCOIL gains execution damage and kills feed a portion of the dash cooldown back."),
                ((-226, -270), N("Overdrive", "m", speed=4, dash_bonus=0.5)),
                ((-340, -112), N("Static Sweep", "m", rattle_radius=0.5, chain=3)),
            ]),
            ("VOIDSTEP", "Use camouflage and afterimages to choose your entry angle.", [
                ((92, -154), N("Shadow Current", "g", camo_time=1.2, camo_range=0.35)),
                ((178, -202), N("Blink Fang", "m", lunge=0.6, strike_width=0.1)),
                ((274, -174), N("Afterimage", "m", mamba_afterimage=1, camo_time=0.7)),
                ((368, -226), N("Killing Intent", "n", crit=5, cdmg=12)),
                ((474, -162), N("KEYSTONE: VOIDSTEP PREDATOR", "k", mamba_voidstep=1, class_skill=2, mamba_afterimage=2, camo_time=1.5),
                 "THUNDERCOIL cloaks the Mamba and drops a decoy trail while the true body cuts through the target line."),
                ((226, -270), N("Blind Spot", "m", camo_range=0.4, crit=3)),
                ((340, -112), N("Neck Breaker", "m", melee=10, strike_stun=0.16, cdmg=8)),
            ]),
            ("KILL TEMPO", "Build a rhythm: hit, rattle, reset, strike again.", [
                ((-45, 56), N("Rapid Pulse", "g", rattle_radius=0.35, rattle_stun=0.12, dash_bonus=0.25)),
                ((-112, 128), N("Tempo Mark", "m", mamba_tempo=1, crit=2)),
                ((0, 190), N("Chain Reaction", "m", chain=6, rattle_force=7, aoe=0.3)),
                ((112, 128), N("Adrenal Surge", "n", speed=4, regen=0.3)),
                ((0, 292), N("KEYSTONE: TEMPO REAPER", "k", mamba_tempo=2, class_skill=2, mamba_dash_reset=1, rattle_radius=0.8),
                 "Enemies hit by THUNDERCOIL can refresh dash and supercharge RATTLE, rewarding aggressive routing."),
                ((-152, 198), N("Electric Nerves", "m", crit=3, dashcd=0.1)),
                ((152, 198), N("Pulse Hunter", "m", speed=3, rattle_force=8)),
            ]),
        ],
        masteries=[
            ((-150, -34), N("ELECTRO: High Voltage", "n", elem_electro=1, em=35, chain=5)),
            ((150, -34), N("ANEMO: Wind Cut", "n", elem_anemo=1, dashlen=1, dash_bonus=0.4)),
            ((-118, 334), N("ABYSS: Void Fang", "n", elem_abyss=1, steal=2, melee=7)),
            ((118, 334), N("LIGHT: Flashpoint", "n", elem_light=1, crit=4, cdmg=12)),
        ],
    ),
}


TREE = {}
EDGES = []
CLASS_NODES = defaultdict(list)

for cid, info in TREE_DEFS.items():
    # The class core IS the starting socket.  It replaces the old shared origin
    # and is always allocated on a new run.
    core_id = f"{cid}:core"
    TREE[core_id] = dict(name=f"{cid.upper()} CORE", kind="c", stats={"class_skill": 1}, elem=None,
        x=0.0, y=0.0, col=info["col"], class_req=cid, info=info["subtitle"],
        core=True)
    CLASS_NODES[cid].append(core_id)

    # Three very visible archetype rails.
    for bi, (branch_name, branch_info, entries) in enumerate(info["branches"]):
        prev = core_id if bi < 2 else core_id
        ids = []
        for ni, item in enumerate(entries):
            pos, node = item[0], item[1]
            node_id = f"{cid}:b{bi}:{ni}"
            extra_info = item[2] if len(item) > 2 else ""
            x, y = pos
            TREE[node_id] = dict(name=node[0], kind=node[1], stats=node[2], elem=None,
                x=x, y=y, col=info["col"], class_req=cid, info=extra_info,
                branch=branch_name, branch_info=branch_info,
                choice_group="keystone" if node[1] == "k" else None)
            EDGES.append((prev, node_id))
            prev = node_id
            ids.append(node_id)
            CLASS_NODES[cid].append(node_id)
        # Secondary side sockets create POE-style little clusters without crossing the main rails.
        if ids[1] and len(ids) >= 7:
            EDGES.append((ids[1], ids[5]))
            EDGES.append((ids[2], ids[6]))

    # Class-exclusive elemental masteries around the lower half of the constellation.
    prev_anchor = f"{cid}:b2:4"
    for mi, (pos, node) in enumerate(info["masteries"]):
        node_id = f"{cid}:m:{mi}"
        elem = next((e for e in ("geo","dendro","hydro","pyro","cryo","electro","anemo","abyss","light") if f"elem_{e}" in node[2]), None)
        st = dict(node[2])
        if elem:
            st.pop(f"elem_{elem}", None)
        TREE[node_id] = dict(name=node[0], kind=node[1], stats=st, elem=elem,
            x=pos[0], y=pos[1], col=None, class_req=cid, info=f"Class-exclusive {elem.upper()} mastery for {info['title'].split(' // ')[0]}." if elem else "Class mastery.", branch="ELEMENT MASTERY", branch_info="Class-specific elemental adaptation.")
        # Masteries connect to nearby branch nodes rather than all meeting at one center.
        EDGES.append((f"{cid}:b0:2" if mi == 0 else f"{cid}:b1:2" if mi == 1 else prev_anchor, node_id))
        CLASS_NODES[cid].append(node_id)

# ---------------------------------------------------------------------------
# Deep passive-tree expansion.
#
# The original class trees were readable but still behaved like three mostly
# linear rails.  This layer adds the topology that makes an ARPG passive tree
# feel like a real build-space: starter spokes, cluster loops, major checkpoints,
# jewel sockets, cross-links and extra outer keystones.  Every class gets the same
# topology grammar but its node names / stat emphasis are different.
# ---------------------------------------------------------------------------

EXPANSION = {
    "viper": dict(
        starters=[
            ("Venom Initiation", {"venom": 2}), ("Predator's Pace", {"speed": 2}),
            ("Toxic Instinct", {"crit": 2}), ("Sickened Edge", {"strike_venom": 1}),
        ],
        clusters=[
            # name, anchor x/y, major, jewel, minor names, stat payloads
            ("Mire Cluster", -560, -315, "", [
                ("Mire Residue", {"venom": 2}), ("Acid Bloom", {"aoe": 0.18}),
                ("Rotting Trail", {"viper_pool_duration": 0.6}), ("Sour Blood", {"steal": 0.5}),
            ], "Mire Tyrant", {"viper_pool_radius": 0.55, "viper_pool_dps": 2, "venom": 4}, "Tainted Core"),
            ("Fang Cluster", 560, -315, "", [
                ("Needle Fangs", {"strike_venom": 1}), ("Razor Reflex", {"crit": 2}),
                ("Cold Read", {"cdmg": 5}), ("Throatseeker", {"lunge": 0.18}),
            ], "Execution Fang", {"crit": 5, "cdmg": 10, "strike_venom": 2}, "Hunter's Eye"),
            ("Shed Cluster", -520, 245, "", [
                ("Loose Skin", {"shed_heal": 0.02}), ("Afterimage Skin", {"camo_time": 0.4}),
                ("Baited Strike", {"camo_range": 0.2}), ("Regrown Scales", {"armor": 2, "regen": 0.2}),
            ], "Perfect Shedding", {"shed_iframe": 0.14, "shed_heal": 0.05, "regen": 0.4}, "Molting Jewel"),
            ("Plague Cluster", 520, 245, "", [
                ("Spore Veins", {"em": 12}), ("Rotting Breath", {"aoe": 0.2}),
                ("Leeching Spores", {"steal": 0.6}), ("Virulence", {"venom": 3}),
            ], "Plague Engine", {"viper_plague_bloom": 1, "steal": 2, "em": 20}, "Spore Jewel"),
            ("Corrosion Cluster", 0, -390, "", [
                ("Weakening Toxin", {"venom": 2}), ("Frayed Armor", {"dmg": 3}),
                ("Green Flame", {"em": 15}), ("Slow Poison", {"coil_slow": 0.06}),
            ], "Corrosive Mastery", {"dmg": 7, "venom": 5, "viper_pool_dps": 2}, "Acid Jewel"),
        ],
        keystones=[
            ((-690, -55), "KEYSTONE: MIASMA SOVEREIGN", {"viper_alchemist": 1, "viper_pool_radius": 0.8, "viper_pool_dps": 4}),
            ((690, -55), "KEYSTONE: BLOOD IN THE WATER", {"viper_fang": 1, "crit": 7, "steal": 2}),
        ],
    ),
    "python": dict(
        starters=[
            ("Reinforced Spine", {"hp": 12}), ("Heavy Footing", {"armor": 2}),
            ("Coiled Core", {"coil": 1}), ("Dense Scales", {"wallres": 4}),
        ],
        clusters=[
            ("Titan Cluster", -560, -315, "", [
                ("Massive Frame", {"hp": 10}), ("Dense Plates", {"armor": 3}),
                ("Long Muscle", {"python_length_scale": 0.35}), ("Impact Weight", {"melee": 3}),
            ], "Titan's Bulk", {"hp": 20, "armor": 5, "python_body_damage": 0.35}, "Colossus Jewel"),
            ("Bastion Cluster", 560, -315, "", [
                ("Shielded Neck", {"bulwark_shield": 5}), ("Braced Scales", {"armor": 3}),
                ("Guard Rhythm", {"bulwark_time": 0.35}), ("Fortress Echo", {"wallres": 5}),
            ], "Living Bastion", {"bulwark": 12, "bulwark_shield": 14, "armor": 4}, "Bastion Jewel"),
            ("Crushing Coil", -520, 245, "", [
                ("Tight Wrap", {"coil_guard": 4}), ("Squeeze", {"coil_dps": 2}),
                ("Anchor Body", {"hp": 8}), ("No Escape", {"coil_slow": 0.07}),
            ], "Unbreakable Coil", {"coil": 4, "coil_guard": 8, "coil_dps": 4}, "Anchor Jewel"),
            ("Reprisal Cluster", 520, 245, "", [
                ("Countermass", {"melee": 3}), ("Shock Hide", {"strike_stun": 0.08}),
                ("Rattleback", {"rattle_force": 4}), ("Stored Momentum", {"dmg": 4}),
            ], "Crushing Reprisal", {"melee": 7, "strike_stun": 0.15, "rattle_force": 8}, "Counterweight Jewel"),
            ("Iron Core", 0, -390, "", [
                ("Tempered Scales", {"armor": 3}), ("Stone Blood", {"hp": 10}),
                ("Weighted Nerves", {"stam": 4}), ("Stable Coil", {"coil_guard": 3}),
            ], "Impervious Core", {"hp": 24, "armor": 7, "wallres": 8}, "Iron Jewel"),
        ],
        keystones=[
            ((-690, -55), "KEYSTONE: UNMOVABLE GIANT", {"python_titan": 1, "hp": 38, "armor": 8}),
            ((690, -55), "KEYSTONE: FORTRESS WITHOUT WALLS", {"python_bastion": 1, "bulwark": 18, "bulwark_shield": 22}),
        ],
    ),
    "cobra": dict(
        starters=[
            ("Quick Fangs", {"spit_damage": 2}), ("Loaded Hood", {"ammo": 1}),
            ("Reactive Toxin", {"em": 12}), ("Needle Aim", {"crit": 2}),
        ],
        clusters=[
            ("Barrage Cluster", -560, -315, "", [
                ("Extra Volley", {"volley_count": 1}), ("Spread Practice", {"cobra_fan_width": 0.04}),
                ("Fast Reload", {"volley_cd": 0.18}), ("Venom Payload", {"volley_damage": 0.04}),
            ], "Barrage Doctrine", {"cobra_fan_count": 2, "volley_count": 2, "volley_damage": 0.08}, "Barrage Jewel"),
            ("Artillery Cluster", 560, -315, "", [
                ("Rangefinding", {"rng": 2}), ("Deep Pierce", {"pierce": 1}),
                ("Ballistic Venom", {"spit_damage": 3}), ("True Line", {"spit_reach": 0.8}),
            ], "Perfect Trajectory", {"rng": 5, "pierce": 2, "spit_damage": 6}, "Siege Jewel"),
            ("Reaction Cluster", -520, 245, "", [
                ("Primer Charge", {"charges": 1}), ("Element Bias", {"em": 18}),
                ("Catalytic Bite", {"venom": 2}), ("Chain Primer", {"cobra_reaction": 1}),
            ], "Catalyst Engine", {"em": 35, "cobra_elemental": 1, "cobra_reaction": 1}, "Catalyst Jewel"),
            ("Precision Cluster", 520, 245, "", [
                ("Dead Center", {"crit": 2}), ("Puncture Drill", {"pierce": 1}),
                ("Marked Weakness", {"cdmg": 5}), ("Execution Range", {"rng": 2}),
            ], "Predator's Ballistics", {"crit": 5, "cdmg": 12, "pierce": 2}, "Hunter Jewel"),
            ("Prism Cluster", 0, -390, "", [
                ("Light Charge", {"em": 15}), ("Color Split", {"cobra_elemental": 1}),
                ("Reaction Spark", {"cobra_reaction": 1}), ("Resonant Shell", {"charges": 1}),
            ], "Prismatic Engine", {"em": 45, "cobra_elemental": 2, "cobra_reaction": 1}, "Prism Jewel"),
        ],
        keystones=[
            ((-690, -55), "KEYSTONE: HYDRA MAGAZINE", {"cobra_barrage": 1, "cobra_fan_count": 7, "volley_count": 2}),
            ((690, -55), "KEYSTONE: PERFECT SIEGE", {"cobra_artillery": 1, "rng": 10, "spit_reach": 3.5, "pierce": 3}),
        ],
    ),
    "mamba": dict(
        starters=[
            ("Charged Muscles", {"speed": 2}), ("Live Reflex", {"crit": 2}),
            ("Flash Nerves", {"dashcd": 0.06}), ("Static Fang", {"chain": 2}),
        ],
        clusters=[
            ("Volt Cluster", -560, -315, "", [
                ("Hot Wire", {"speed": 2}), ("Arc Step", {"dash_bonus": 0.25}),
                ("Charged Heel", {"dashlen": 0.4}), ("Flash Current", {"chain": 2}),
            ], "Overvolt Drive", {"speed": 5, "dash_bonus": 0.6, "chain": 4}, "Volt Jewel"),
            ("Void Cluster", 560, -315, "", [
                ("Dark Current", {"camo_time": 0.4}), ("Ghost Step", {"iframe": 0.05}),
                ("Blind Angle", {"crit": 2}), ("Afterimage Echo", {"mamba_afterimage": 1}),
            ], "Perfect Vanish", {"mamba_voidstep": 1, "camo_time": 0.8, "camo_range": 0.4}, "Void Jewel"),
            ("Tempo Cluster", -520, 245, "", [
                ("Quick Beat", {"rattle_radius": 0.2}), ("Pulse Timing", {"dashcd": 0.05}),
                ("Kinetic Rhythm", {"speed": 2}), ("Chain Timing", {"rattle_force": 3}),
            ], "Killing Rhythm", {"mamba_tempo": 1, "dash_bonus": 0.4, "crit": 4}, "Tempo Jewel"),
            ("Execution Cluster", 520, 245, "", [
                ("Finish Line", {"crit": 2}), ("Neck Shock", {"strike_stun": 0.08}),
                ("Killer Instinct", {"cdmg": 6}), ("Cold Trigger", {"mamba_executioner": 0.2}),
            ], "Execution Protocol", {"mamba_executioner": 1, "crit": 6, "cdmg": 14}, "Execution Jewel"),
            ("Storm Core", 0, -390, "", [
                ("Voltage Skin", {"em": 15}), ("Static Blood", {"chain": 2}),
                ("Storm Nerves", {"speed": 2}), ("Electric Focus", {"crit": 2}),
            ], "Storm Conductor", {"em": 35, "chain": 5, "speed": 4}, "Storm Jewel"),
        ],
        keystones=[
            ((-690, -55), "KEYSTONE: ETERNAL AFTERIMAGE", {"mamba_voidstep": 1, "mamba_afterimage": 3, "camo_time": 1.0}),
            ((690, -55), "KEYSTONE: THUNDER REAPER", {"mamba_executioner": 1, "mamba_dash_reset": 1, "chain": 6, "crit": 8}),
        ],
    ),
}


def _add_expanded_node(cid, suffix, name, kind, x, y, stats=None, info="", elem=None, branch="DEEP CONSTELLATION"):
    nid = f"{cid}:x:{suffix}"
    TREE[nid] = dict(name=name, kind=kind, stats=dict(stats or {}), elem=elem, x=float(x), y=float(y),
                     col=TREE_DEFS[cid]["col"] if elem is None else None, class_req=cid, info=info,
                     branch=branch, branch_info="Expanded passive-tree cluster.",
                     choice_group="keystone" if kind == "k" else None)
    CLASS_NODES[cid].append(nid)
    return nid


for cid, ex in EXPANSION.items():
    # Four starter spokes around the core create early routing choices instead of
    # forcing every build through the same three branch entrances.
    starter_xy = [(-62, -46), (62, -46), (-72, 18), (72, 18)]
    starter_ids = []
    for i, ((name, stats), (x, y)) in enumerate(zip(ex["starters"], starter_xy)):
        nid = _add_expanded_node(cid, f"starter{i}", name, "m", x, y, stats, "Starter small passive.")
        starter_ids.append(nid)
        EDGES.append((f"{cid}:core", nid))
    # Feed the starter spokes into the existing first sockets.
    EDGES.extend([
        (starter_ids[0], f"{cid}:b0:0"), (starter_ids[1], f"{cid}:b1:0"),
        (starter_ids[2], f"{cid}:b2:0"), (starter_ids[3], f"{cid}:b2:3"),
    ])

    # Dense side clusters. Each cluster has a four-node minor ring, one major,
    # and a jewel socket, with two-way options into adjacent clusters.
    cluster_roots = []
    cluster_data = ex["clusters"]
    for ci, (label, ax, ay, _unused, minors, major_name, major_stats, jewel_name) in enumerate(cluster_data):
        anchor = _add_expanded_node(cid, f"cluster{ci}_gateway", label, "g", ax * 0.78, ay * 0.78,
                                    {"em": 4}, f"Gateway into the {label} cluster.", branch=label.upper())
        cluster_roots.append(anchor)
        # Cluster sockets are arranged as a small diamond/loop.
        offsets = [(-64, -12), (-22, -60), (38, -42), (64, 12)]
        minor_ids = []
        for mi, ((mn, mst), (ox, oy)) in enumerate(zip(minors, offsets)):
            nid = _add_expanded_node(cid, f"cluster{ci}_m{mi}", mn, "m", ax + ox, ay + oy, mst,
                                     f"Minor passive in the {label} cluster.", branch=label.upper())
            minor_ids.append(nid)
            EDGES.append((anchor if mi == 0 else minor_ids[mi-1], nid))
        EDGES.append((minor_ids[-1], minor_ids[0]))  # close the local loop
        major = _add_expanded_node(cid, f"cluster{ci}_major", major_name, "a", ax + 5, ay + 44, major_stats,
                                   "Major passive: a substantial build-defining checkpoint.", branch=label.upper())
        jewel = _add_expanded_node(cid, f"cluster{ci}_jewel", jewel_name, "j", ax - 12, ay + 94,
                                   {"dmg": 1}, "Jewel Socket: spend a point here to unlock a future jewel augment.", branch=label.upper())
        EDGES.extend([(minor_ids[1], major), (minor_ids[2], major), (major, jewel)])
        # Connect each cluster back to a nearby existing branch node.
        if ci == 0:
            EDGES.append((f"{cid}:b0:3", anchor))
        elif ci == 1:
            EDGES.append((f"{cid}:b1:3", anchor))
        elif ci == 2:
            EDGES.append((f"{cid}:b2:3", anchor))
        elif ci == 3:
            EDGES.append((f"{cid}:b2:1", anchor))
        else:
            EDGES.append((f"{cid}:core", anchor))

    # Cross-links: these are intentional shortcuts, so multiple build directions
    # can meet without every route turning into one huge straight line.
    EDGES += [
        (cluster_roots[0], cluster_roots[4]),
        (cluster_roots[4], cluster_roots[1]),
        (cluster_roots[0], cluster_roots[2]),
        (cluster_roots[2], cluster_roots[3]),
        (cluster_roots[3], cluster_roots[1]),
    ]

    # Two additional outer keystones. They share the keystone choice group with the
    # three original doctrine caps, so a player still commits to only one doctrine.
    for ki, (pos, name, stats) in enumerate(ex["keystones"]):
        kid = _add_expanded_node(cid, f"keystone{ki}", name, "k", pos[0], pos[1], stats,
                                 "Keystone: a radical rule-changing build choice. Only one keystone doctrine may be taken.",
                                 branch="KEYSTONE OUTER RING")
        # Attach to the left/right cluster gateway respectively.
        EDGES.append((cluster_roots[0 if ki == 0 else 1], kid))
        # Also give each side a second route through a major cluster.
        EDGES.append((cluster_roots[2 if ki == 0 else 3], kid))

    # Add four spoke-like minor nodes between outer ring and the core. They create
    # long routes and meaningful detours even before a keystone is reached.
    spoke_coords = [(-410, -82), (410, -82), (-330, 210), (330, 210)]
    targets = [cluster_roots[0], cluster_roots[1], cluster_roots[2], cluster_roots[3]]
    for si, ((x, y), target) in enumerate(zip(spoke_coords, targets)):
        a = _add_expanded_node(cid, f"spoke{si}a", ["Bitter Current", "Heavy Current", "Charged Current", "Killing Current"][si],
                               "m", x, y, {"dmg": 2 + si, "speed": 1 if si % 2 else 0}, "Long-route minor passive.")
        b = _add_expanded_node(cid, f"spoke{si}b", ["Bitter Reach", "Heavy Reach", "Charged Reach", "Killing Reach"][si],
                               "n", x + (34 if x > 0 else -34), y + 20, {"crit": 1 + si, "em": 4}, "Notable on a long outer route.")
        EDGES.extend([(target, a), (a, b)])



# ---------------------------------------------------------------------------
# FULL BUILD-CRAFTING LATTICE
# ---------------------------------------------------------------------------
# A second, much larger layer turns each class tree into a true end-game build
# space.  These are intentionally small stat nodes: the power comes from routing
# choices, clusters, loops, and deciding which outer major/keystone to reach.
# Stats added here are real runtime stats (see StatsMixin / CombatMixin), not
# tooltip-only decoration.

FULL_LATTICE = {
    "viper": {
        "prefix": ["Venom", "Mire", "Fang", "Molting", "Plague", "Scent", "Corrosion", "Predator"],
        "themes": [
            ("LIFE", {"hp": 3, "hp_pct": 1.2, "regen": 0.05, "life_on_hit": 0.2, "steal": 0.15}),
            ("SUSTAIN", {"regen": 0.12, "regen_pct": 0.05, "steal": 0.4, "life_on_kill": 1}),
            ("ENERGY", {"energy_recharge": 2.5, "energy_max": 1, "energy_on_kill": 6, "stamr": 0.8}),
            ("CRIT", {"crit": 1.2, "cdmg": 2.5, "dmg": 1.2}),
            ("STRIKE", {"melee": 1.8, "lunge": 0.06, "strike_venom": 0.35, "strike_width": 0.03}),
            ("VENOM", {"venom": 0.8, "aoe": 0.04, "viper_pool_duration": 0.08}),
            ("EVADE", {"speed": 0.8, "iframe": 0.02, "dashcd": 0.018}),
            ("DEFENSE", {"armor": 0.9, "wallres": 1.0, "less_damage": 0.35}),
        ],
        "names": [
            ["Green Blood", "Thick Venom", "Vital Ichor", "Toxic Heart", "Leeching Cells", "Enduring Flesh", "Feral Pulse", "Hungry Core"],
            ["Quiet Recovery", "Patient Coil", "Feeding Instinct", "Sustain", "Blood Scent", "Regrowth", "Carrion Vitality", "Unbroken Hunt"],
            ["Charged Venom", "Pulse Reserve", "Voltaic Glands", "Stored Toxin", "Deep Battery", "Rapid Refill", "Living Capacitor", "Everflow"],
        ],
        "major_names": ["Serpent's Vitality", "Toxic Battery", "Perfect Ambush", "Endless Venom"],
        "keystones": [
            ((-820, -520), "KEYSTONE: IMMORTAL VENOM", {"hp_pct": 8, "regen_pct": 0.35, "steal": 2.5, "less_damage": 3}),
            ((820, -520), "KEYSTONE: PREDATOR'S PACT", {"crit": 9, "cdmg": 18, "melee": 8, "life_on_kill": 6}),
            ((-820, 515), "KEYSTONE: INFINITE MIASMA", {"energy_recharge": 28, "energy_max": 2, "viper_pool_duration": 2.5, "venom": 7}),
            ((820, 515), "KEYSTONE: BLOOD-FED HUNT", {"steal": 6, "life_on_hit": 1.5, "life_on_kill": 10, "hp_pct": -8}),
        ],
    },
    "python": {
        "prefix": ["Iron", "Titan", "Bastion", "Colossus", "Anchor", "Stone", "Bulwark", "Breaker"],
        "themes": [
            ("LIFE", {"hp": 4, "hp_pct": 1.6, "regen": 0.06, "life_on_hit": 0.15}),
            ("SUSTAIN", {"regen": 0.16, "regen_pct": 0.06, "steal": 0.25, "life_on_kill": 1}),
            ("ENERGY", {"energy_recharge": 2.0, "energy_max": 1, "energy_on_kill": 5, "stam": 1.0, "stamr": 0.8}),
            ("FORTIFY", {"armor": 1.6, "wallres": 1.8, "less_damage": 0.55, "shield_pct": 1.3}),
            ("MELEE", {"melee": 2.0, "lunge": 0.04, "strike_stun": 0.04, "strike_width": 0.04}),
            ("COIL", {"coil_dps": 0.7, "coil_guard": 0.45, "coil_slow": 0.025}),
            ("LENGTH", {"python_length_scale": 0.12, "python_body_damage": 0.08, "hp": 2}),
            ("RESOLVE", {"stam": 2, "iframe": 0.018, "dashlen": 0.05, "bulwark_time": 0.06}),
        ],
        "names": [
            ["Vital Plates", "Core Mass", "Heavy Blood", "Dense Muscle", "Iron Organs", "Thick Skin", "Giant Heart", "Titan Blood"],
            ["Slow Recovery", "Battle Regeneration", "Leeching Scales", "Lasting Flesh", "Feeding Armor", "Patient Guard", "Deep Reserves", "Indomitable"],
            ["Stored Force", "Battery Coil", "Power Reserve", "Deep Capacitor", "Heavy Charge", "Quick Recharge", "Overflow Core", "War Engine"],
        ],
        "major_names": ["Titan's Constitution", "Fortress Engine", "Colossal Coil", "Unbroken Resolve"],
        "keystones": [
            ((-820, -520), "KEYSTONE: UNBREAKABLE MASS", {"hp_pct": 10, "armor": 10, "less_damage": 5, "speed": -5}),
            ((820, -520), "KEYSTONE: RAMPART HEART", {"shield_pct": 10, "bulwark": 20, "bulwark_shield": 26, "energy_recharge": -12}),
            ((-820, 515), "KEYSTONE: ENDLESS COIL", {"coil_guard": 10, "coil_dps": 8, "energy_recharge": 25, "energy_max": 2}),
            ((820, 515), "KEYSTONE: TITAN'S HUNGER", {"hp_pct": 6, "steal": 4, "life_on_hit": 2, "melee": 9, "armor": -6}),
        ],
    },
    "cobra": {
        "prefix": ["Venom", "Ballistic", "Prism", "Hunter", "Siege", "Catalyst", "Needle", "Volley"],
        "themes": [
            ("LIFE", {"hp": 3, "hp_pct": 1.0, "regen": 0.04, "life_on_hit": 0.15}),
            ("SUSTAIN", {"regen": 0.10, "regen_pct": 0.04, "steal": 0.35, "life_on_kill": 1}),
            ("ENERGY", {"energy_recharge": 3.0, "energy_max": 1, "energy_on_kill": 7, "stamr": 0.7}),
            ("PROJECTILE", {"rng": 1.8, "pierce": 0.08, "spit_reach": 0.05, "spit_damage": 0.4}),
            ("CRIT", {"crit": 1.4, "cdmg": 3.0, "rng": 0.5}),
            ("REACTION", {"em": 6, "cobra_reaction": 0.08, "cobra_elemental": 0.06, "charges": 0.04}),
            ("VOLLEY", {"volley_count": 0.12, "volley_damage": 0.012, "volley_pierce": 0.08, "volley_cd": 0.06}),
            ("MOBILITY", {"speed": 0.9, "dashcd": 0.02, "iframe": 0.02, "dashlen": 0.06}),
        ],
        "names": [
            ["Hunter's Blood", "Vital Scales", "Quickened Heart", "Field Medicine", "Hardy Hood", "Steady Pulse", "Breathing Room", "Deep Vitality"],
            ["Leeching Fang", "Combat Feeding", "Patient Aim", "Blood Reserve", "Toxic Recovery", "Rapid Mend", "Victory Feast", "Endless Pursuit"],
            ["Charged Hood", "Pulse Cache", "Deep Battery", "Stored Venom", "Overcharged Sacs", "Rapid Refill", "Power Reservoir", "Perpetual Charge"],
        ],
        "major_names": ["Ballistic Anatomy", "Prismatic Heart", "Siege Specialist", "Hydra Arsenal"],
        "keystones": [
            ((-820, -520), "KEYSTONE: HYDRA CORE", {"volley_count": 3, "volley_damage": 0.16, "energy_recharge": 15, "energy_max": 2, "rng": 4}),
            ((820, -520), "KEYSTONE: TRUE SIGHT", {"crit": 12, "cdmg": 24, "rng": 12, "hp_pct": -5}),
            ((-820, 515), "KEYSTONE: REACTION ENGINE", {"em": 100, "cobra_reaction": 1, "cobra_elemental": 2, "energy_recharge": 22}),
            ((820, 515), "KEYSTONE: GLASS FANG", {"rng": 15, "crit": 8, "cdmg": 18, "less_damage": -4, "hp_pct": -10}),
        ],
    },
    "mamba": {
        "prefix": ["Volt", "Storm", "Flash", "Tempo", "Void", "Reaper", "Spark", "Surge"],
        "themes": [
            ("LIFE", {"hp": 3, "hp_pct": 1.1, "regen": 0.05, "life_on_hit": 0.18}),
            ("SUSTAIN", {"regen": 0.11, "regen_pct": 0.05, "steal": 0.3, "life_on_kill": 1}),
            ("ENERGY", {"energy_recharge": 3.5, "energy_max": 1, "energy_on_kill": 8, "stamr": 1.0}),
            ("SPEED", {"speed": 1.2, "dashcd": 0.028, "dashlen": 0.08, "iframe": 0.025}),
            ("CRIT", {"crit": 1.6, "cdmg": 3.2, "dmg": 0.8}),
            ("CHAIN", {"chain": 0.55, "aoe": 0.04, "mamba_chain": 0.08}),
            ("EXECUTE", {"crit": 0.9, "cdmg": 2.8, "mamba_executioner": 0.06, "melee": 1.2}),
            ("DEFENSE", {"armor": 0.7, "wallres": 0.8, "less_damage": 0.3, "iframe": 0.018}),
        ],
        "names": [
            ["Static Blood", "Volt Heart", "Live Wire", "Charged Flesh", "Spark Veins", "Storm Blood", "Electric Pulse", "Conductive Core"],
            ["Rapid Recovery", "Feeding Current", "Killing Regen", "Sustain Circuit", "Blood Voltage", "Quick Mend", "Shock Feast", "Never Still"],
            ["Charged Coil", "Pulse Bank", "Storm Reserve", "Deep Capacitor", "Overload Cell", "Fast Recharge", "Voltage Core", "Perpetual Current"],
        ],
        "major_names": ["Storm Constitution", "Lightning Footwork", "Execution Circuit", "Living Conductor"],
        "keystones": [
            ((-820, -520), "KEYSTONE: PERFECT MOMENT", {"speed": 12, "dashcd": 0.18, "iframe": 0.16, "crit": 8}),
            ((820, -520), "KEYSTONE: STORM HARVEST", {"chain": 8, "energy_recharge": 28, "energy_max": 2, "speed": 6}),
            ((-820, 515), "KEYSTONE: VOID VELOCITY", {"camo_time": 1.6, "dashlen": 1.3, "dashcd": 0.16, "less_damage": 3, "hp_pct": -6}),
            ((820, 515), "KEYSTONE: EXECUTIONER'S EDGE", {"crit": 11, "cdmg": 22, "mamba_executioner": 1, "life_on_kill": 8, "hp_pct": -5}),
        ],
    },
}


def _add_full_node(cid, suffix, name, kind, x, y, stats, info, branch, choice_group=None):
    nid = f"{cid}:f:{suffix}"
    TREE[nid] = dict(name=name, kind=kind, stats=dict(stats), elem=None, x=float(x), y=float(y),
                     col=TREE_DEFS[cid]["col"], class_req=cid, info=info, branch=branch,
                     branch_info="Large passive-tree stat cluster.", choice_group=choice_group)
    CLASS_NODES[cid].append(nid)
    return nid

# Eight radial districts with ten sockets each.  Rings between equal stages create
# genuine alternate routes and loops.  The first socket in each district connects
# into the existing tree; the final sockets feed into outer majors/keystones.
for cid, spec in FULL_LATTICE.items():
    old_roots = [f"{cid}:x:cluster{i}_gateway" for i in range(5)]
    spokes = []
    district_count = 8
    angle_offset = math.radians(22.5)
    import math as _math
    # local import keeps the original module namespace compact
    for si in range(district_count):
        angle = angle_offset + si * (2 * _math.pi / district_count)
        theme_idx = si
        label, base_stats = spec["themes"][theme_idx]
        prefix = spec["prefix"][si]
        prev = None
        ids = []
        for stage in range(10):
            r = 190 + stage * 68
            x = _math.cos(angle) * r
            y = _math.sin(angle) * r
            if stage == 6:
                kind = "n"
                name = f"{prefix} {label.title()} Mastery"
                stats = {k: v * 2.5 for k, v in base_stats.items()}
                text = f"Notable: {label.title()} cluster specializing in multiple {label.lower()} stats."
            elif stage == 8:
                kind = "j"
                name = f"{prefix} {label.title()} Jewel"
                stats = {"dmg": 0.5, "hp": 2}
                text = "Jewel Socket: allocate here to unlock a socket for future augment data."
            elif stage == 9:
                kind = "a"
                mi = si // 2
                name = f"{spec['major_names'][mi]}"
                stats = {k: v * 2 for k, v in base_stats.items()}
                text = f"Major passive: a high-value {label.lower()} checkpoint at the edge of the district."
            else:
                kind = "m"
                mult = 1.0 if stage < 5 else 1.15
                names = spec["names"][stage % len(spec["names"])]
                name = f"{names[si]} {label.title()}"
                stats = {k: v * mult for k, v in base_stats.items()}
                text = f"Minor passive: {label.lower()} specialization."
            nid = _add_full_node(cid, f"s{si}_{stage}", name, kind, x, y, stats, text, f"{prefix.upper()} / {label}")
            ids.append(nid)
            if prev:
                EDGES.append((prev, nid))
            prev = nid
        # district entrance routing: alternate between existing clusters, starters,
        # and the class core so no single path is mandatory.
        anchors = [
            f"{cid}:x:starter{si % 4}",
            old_roots[si % len(old_roots)],
            f"{cid}:b{si % 3}:{2 + (si % 3)}",
        ]
        EDGES.append((anchors[si % 3], ids[0]))
        spokes.append(ids)

    # Radial ring links: connect neighbouring spokes at stages 2, 4, 6, 8. This
    # creates the signature POE-like web of loops and route shortcuts.
    for stage in (2, 4, 6, 8):
        for si in range(district_count):
            EDGES.append((spokes[si][stage], spokes[(si + 1) % district_count][stage]))

    # Two diagonal long bridges create alternate cross-tree routes.
    EDGES.extend([
        (spokes[0][5], spokes[3][5]), (spokes[2][7], spokes[6][7]),
        (spokes[1][4], spokes[5][4]), (spokes[4][6], spokes[7][6]),
    ])

    # Four remote keystones, each connected through two different major/route arms.
    for ki, (pos, name, stats) in enumerate(spec["keystones"]):
        kid = _add_full_node(cid, f"ks{ki}", name, "k", pos[0], pos[1], stats,
                             "Keystone: powerful rule-changing build choice. All class keystones share one doctrine group; only one may be allocated.",
                             "OUTER KEYSTONE RING", "keystone")
        # Attach to two distinct spokes so the keystone is reachable from either side.
        left_si = (ki * 2) % district_count
        right_si = (left_si + 1) % district_count
        EDGES.extend([(spokes[left_si][9], kid), (spokes[right_si][9], kid)])

    # Small satellite spokes around the middle of the lattice: these are cheap
    # bridges that let a player pivot from offense -> sustain -> defense without
    # walking all the way back to the core.
    for si in range(8):
        ids = spokes[si]
        label, base_stats = spec["themes"][si]
        a = ids[3]
        b = _add_full_node(cid, f"sat{si}_a", f"{spec['prefix'][si]} {label.title()} Link", "m",
                           TREE[a]["x"] * 0.72, TREE[a]["y"] * 0.72,
                           {k: v * 0.7 for k, v in base_stats.items()},
                           "Satellite minor passive: an alternate bridge between nearby districts.",
                           f"SATELLITE / {label}")
        c = _add_full_node(cid, f"sat{si}_n", f"{spec['prefix'][si]} {label.title()} Junction", "n",
                           TREE[a]["x"] * 0.60, TREE[a]["y"] * 0.60,
                           {k: v * 1.1 for k, v in base_stats.items()},
                           "Notable junction: a compact alternate route node.",
                           f"SATELLITE / {label}")
        EDGES.extend([(a, b), (b, c), (c, ids[2]), (c, spokes[(si + 1) % 8][3])])


# Build adjacency for allocation/refund connectivity.
# Collision-spread layout: all four classes share the same readable socket geometry.
# It preserves the large passive graph while guaranteeing a visible gap between sockets.
_PASSIVE_LAYOUT = {
    'b0:0': (-111.488, -69.55),
    'b0:1': (-190.7, -132.092),
    'b0:2': (-315.1, -98.9),
    'b0:3': (-423.2, -158.7),
    'b0:4': (-544.62, -83.849),
    'b0:5': (-254.525, -219.676),
    'b0:6': (-394.169, -24.313),
    'b1:0': (111.488, -69.55),
    'b1:1': (190.7, -132.092),
    'b1:2': (315.1, -98.9),
    'b1:3': (423.2, -158.7),
    'b1:4': (544.666, -83.419),
    'b1:5': (254.525, -219.676),
    'b1:6': (394.169, -24.313),
    'b2:0': (-51.231, 166.331),
    'b2:1': (-128.8, 248.4),
    'b2:2': (0.0, 319.7),
    'b2:3': (128.8, 248.4),
    'b2:4': (-0.0, 444.442),
    'b2:5': (-174.8, 328.9),
    'b2:6': (174.8, 328.9),
    'core': (0.0, 0.0),
    'f:ks0': (-943.0, -496.8),
    'f:ks1': (943.0, -496.8),
    'f:ks2': (-943.0, 693.45),
    'f:ks3': (943.0, 693.45),
    'f:s0_0': (201.868, 184.816),
    'f:s0_1': (274.115, 214.742),
    'f:s0_2': (346.362, 244.668),
    'f:s0_3': (418.61, 274.594),
    'f:s0_4': (503.591, 296.034),
    'f:s0_5': (566.409, 348.633),
    'f:s0_6': (628.606, 368.929),
    'f:s0_7': (719.109, 390.549),
    'f:s0_8': (779.847, 424.223),
    'f:s0_9': (852.094, 454.149),
    'f:s1_0': (83.616, 303.068),
    'f:s1_1': (113.542, 375.315),
    'f:s1_2': (146.364, 436.455),
    'f:s1_3': (177.076, 522.539),
    'f:s1_4': (203.32, 592.057),
    'f:s1_5': (233.246, 664.305),
    'f:s1_6': (263.171, 736.552),
    'f:s1_7': (293.097, 808.799),
    'f:s1_8': (323.023, 881.047),
    'f:s1_9': (352.949, 953.294),
    'f:s2_0': (-83.616, 303.068),
    'f:s2_1': (-113.542, 375.315),
    'f:s2_2': (-146.364, 436.455),
    'f:s2_3': (-177.076, 522.539),
    'f:s2_4': (-203.32, 592.057),
    'f:s2_5': (-233.246, 664.305),
    'f:s2_6': (-263.171, 736.552),
    'f:s2_7': (-293.097, 808.799),
    'f:s2_8': (-323.023, 881.047),
    'f:s2_9': (-352.949, 953.294),
    'f:s3_0': (-201.868, 184.816),
    'f:s3_1': (-274.115, 214.742),
    'f:s3_2': (-346.362, 244.668),
    'f:s3_3': (-418.61, 274.594),
    'f:s3_4': (-500.912, 292.148),
    'f:s3_5': (-581.326, 334.524),
    'f:s3_6': (-627.828, 365.964),
    'f:s3_7': (-713.941, 402.763),
    'f:s3_8': (-779.847, 424.223),
    'f:s3_9': (-852.094, 454.149),
    'f:s4_0': (-202.786, 16.192),
    'f:s4_1': (-274.115, -12.342),
    'f:s4_2': (-342.292, -43.792),
    'f:s4_3': (-419.511, -73.958),
    'f:s4_4': (-490.857, -102.12),
    'f:s4_5': (-564.544, -135.798),
    'f:s4_6': (-619.5, -161.642),
    'f:s4_7': (-707.944, -192.314),
    'f:s4_8': (-779.847, -221.823),
    'f:s4_9': (-852.094, -251.749),
    'f:s5_0': (-75.085, -110.193),
    'f:s5_1': (-113.542, -172.915),
    'f:s5_2': (-143.468, -245.162),
    'f:s5_3': (-173.394, -317.41),
    'f:s5_4': (-203.32, -389.657),
    'f:s5_5': (-233.246, -461.905),
    'f:s5_6': (-263.171, -534.152),
    'f:s5_7': (-293.097, -606.399),
    'f:s5_8': (-323.023, -678.647),
    'f:s5_9': (-352.949, -750.894),
    'f:s6_0': (75.085, -110.193),
    'f:s6_1': (113.542, -172.915),
    'f:s6_2': (143.468, -245.162),
    'f:s6_3': (173.394, -317.41),
    'f:s6_4': (203.32, -389.657),
    'f:s6_5': (233.246, -461.905),
    'f:s6_6': (263.171, -534.152),
    'f:s6_7': (293.097, -606.399),
    'f:s6_8': (323.023, -678.647),
    'f:s6_9': (352.949, -750.894),
    'f:s7_0': (202.786, 16.192),
    'f:s7_1': (274.115, -12.342),
    'f:s7_2': (342.292, -43.792),
    'f:s7_3': (419.511, -73.958),
    'f:s7_4': (490.857, -102.12),
    'f:s7_5': (557.76, -137.363),
    'f:s7_6': (657.013, -165.923),
    'f:s7_7': (707.599, -191.897),
    'f:s7_8': (779.847, -221.823),
    'f:s7_9': (852.094, -251.749),
    'f:sat0_a': (233.345, 334.545),
    'f:sat0_n': (275.772, 376.972),
    'f:sat1_a': (0.0, 391.972),
    'f:sat1_n': (0.0, 499.651),
    'f:sat2_a': (-233.345, 334.545),
    'f:sat2_n': (-275.772, 376.972),
    'f:sat3_a': (-330.0, 101.2),
    'f:sat3_n': (-390.0, 101.2),
    'f:sat4_a': (-244.642, -127.844),
    'f:sat4_n': (-279.811, -171.038),
    'f:sat5_a': (11.434, -200.787),
    'f:sat5_n': (-24.877, -288.393),
    'f:sat6_a': (244.642, -127.844),
    'f:sat6_n': (279.811, -171.038),
    'f:sat7_a': (330.0, 101.2),
    'f:sat7_n': (390.0, 101.2),
    'm:0': (-172.041, 62.796),
    'm:1': (172.041, 62.796),
    'm:2': (-132.411, 489.489),
    'm:3': (132.411, 489.489),
    'x:cluster0_gateway': (-502.32, -181.355),
    'x:cluster0_jewel': (-672.06, -149.292),
    'x:cluster0_m0': (-717.6, -274.85),
    'x:cluster0_m1': (-669.3, -330.05),
    'x:cluster0_m2': (-600.3, -309.35),
    'x:cluster0_m3': (-570.4, -247.25),
    'x:cluster0_major': (-639.385, -213.473),
    'x:cluster1_gateway': (502.32, -181.355),
    'x:cluster1_jewel': (613.047, -136.952),
    'x:cluster1_m0': (570.4, -274.85),
    'x:cluster1_m1': (618.7, -330.05),
    'x:cluster1_m2': (687.7, -309.35),
    'x:cluster1_m3': (717.6, -247.25),
    'x:cluster1_major': (648.802, -219.978),
    'x:cluster2_gateway': (-459.151, 326.863),
    'x:cluster2_jewel': (-611.8, 491.05),
    'x:cluster2_m0': (-681.674, 358.615),
    'x:cluster2_m1': (-630.508, 310.116),
    'x:cluster2_m2': (-529.125, 340.011),
    'x:cluster2_m3': (-524.4, 396.75),
    'x:cluster2_major': (-592.25, 433.55),
    'x:cluster3_gateway': (458.402, 326.118),
    'x:cluster3_jewel': (584.2, 491.05),
    'x:cluster3_m0': (517.128, 372.887),
    'x:cluster3_m1': (576.668, 296.026),
    'x:cluster3_m2': (647.787, 318.209),
    'x:cluster3_m3': (667.495, 407.824),
    'x:cluster3_major': (603.75, 433.55),
    'x:cluster4_gateway': (18.663, -254.325),
    'x:cluster4_jewel': (-31.551, -233.594),
    'x:cluster4_m0': (-73.6, -361.1),
    'x:cluster4_m1': (-25.3, -416.3),
    'x:cluster4_m2': (43.7, -395.6),
    'x:cluster4_m3': (74.149, -333.766),
    'x:cluster4_major': (23.861, -309.192),
    'x:keystone0': (-793.5, 37.95),
    'x:keystone1': (793.5, 37.95),
    'x:spoke0a': (-465.774, 3.532),
    'x:spoke0b': (-513.463, 31.584),
    'x:spoke1a': (465.774, 3.532),
    'x:spoke1b': (513.463, 31.584),
    'x:spoke2a': (-373.751, 339.231),
    'x:spoke2b': (-421.103, 367.836),
    'x:spoke3a': (373.757, 339.24),
    'x:spoke3b': (421.133, 367.808),
    'x:starter0': (-71.3, 48.3),
    'x:starter1': (71.3, 48.3),
    'x:starter2': (-83.579, 120.804),
    'x:starter3': (82.8, 121.9),
}
for _cid in CLASS_NODES:
    for _nid in CLASS_NODES[_cid]:
        TREE[_nid]["_id"] = _nid
        _key = _nid.split(":", 1)[1]
        if _key in _PASSIVE_LAYOUT:
            TREE[_nid]["x"], TREE[_nid]["y"] = _PASSIVE_LAYOUT[_key]
# Build adjacency for allocation/refund connectivity.
ADJ = defaultdict(set)
for a, b in EDGES:
    ADJ[a].add(b)
    ADJ[b].add(a)

# Human-readable list of the nodes a class can see.
CLASS_NODE_COUNT = {cid: len(ids) for cid, ids in CLASS_NODES.items()}


def nodes_for_class(cid):
    return CLASS_NODES.get(cid, ())


def describe(stats):
    out = []
    for k, v in stats.items():
        lab = LABEL.get(k, k.replace("_", " ").title())
        if isinstance(v, (int, float)) and abs(v) < 1e-9:
            continue
        if lab.startswith("%"):
            out.append(f"{v:+g}{lab}")
        elif isinstance(v, (int, float)):
            out.append(f"{v:+g} {lab}")
        else:
            out.append(f"{lab}: {v}")
    return out
