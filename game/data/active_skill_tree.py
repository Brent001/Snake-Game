"""Full branching ACTIVE SKILL TREE.

The passive tree is the large character-stat constellation. This file is the
separate active-skill tree: every skill on the hotbar has its own branching
mini-constellation inside one global skill map.

Each skill has:
    ROOT -> 3 specialization paths -> mastery junction -> 2 exclusive capstones
plus cross-links between the three paths. Every root is free; the player spends
SKILL points on the upgrades. Stats use the same live fields consumed by the
ability implementations, so the nodes are functional rather than cosmetic.
"""
from collections import defaultdict

from .skills import SKILLS
from .classes import CLASSES

LINE_ALIASES = {"basic": "strike", "v": "class_skill"}

SKILL_NODES = {}
SKILL_EDGES = []
SKILL_ADJ = defaultdict(set)
SKILL_DEFS = {}


def canonical_line(line):
    return LINE_ALIASES.get(line, line)


def node(nid, name, kind, line, x, y, stats=None, desc="", evolve=0, choice=None, color=None):
    return dict(id=nid, name=name, kind=kind, line=line, x=float(x), y=float(y),
                stats=dict(stats or {}), desc=desc or "Skill passive.", evolve=int(evolve),
                choice=choice, color=color)


def add(cid, line, slug, name, kind, x, y, stats=None, desc="", evolve=0, choice=None):
    nid = f"{cid}:{line}:{slug}"
    col = SKILL_DEFS[cid][line]["color"]
    SKILL_NODES[nid] = node(nid, name, kind, line, x, y, stats, desc, evolve, choice, col)
    return nid


def edge(a, b):
    SKILL_EDGES.append((a, b))
    SKILL_ADJ[a].add(b)
    SKILL_ADJ[b].add(a)


# Skill descriptions shown in the sidebar / cluster headers.
GENERIC = {
    "dash": ("DASH", "Mobility, invulnerability and movement rhythm."),
    "strike": ("PRIMARY ATTACK", "Improve your class's LMB attack."),
    "coil": ("COIL", "Duration, crush damage and defensive control."),
    "shed": ("SHED", "Healing, iframe timing and decoys."),
    "heat": ("HEAT SENSE", "Reveal targets and convert information into damage."),
    "scent": ("TONGUE / SCENT", "Longer detection, tracking and resource hunting."),
    "spit": ("SPIT", "Range, venom payload and control."),
    "rattle": ("RATTLE", "A panic pulse that clears projectiles and controls space."),
    "camo": ("CAMOUFLAGE", "Stealth, ambush and escape routing."),
    "volley": ("VOLLEY", "Projectile count, piercing and elemental saturation."),
    "bulwark": ("BULWARK", "Barrier size, uptime and retaliation."),
    "class_skill": ("SIGNATURE V", "The class-defining signature skill and its evolution."),
}

# Each tuple: (path title, path subtitle, [minor, minor, notable, major], capstone A, capstone B)
# The stats intentionally use fields already consumed by the combat/ability systems.
BASE_PATHS = {
    "dash": [
        ("VELOCITY", "move faster and chain movement", [
            ("Quick Step", "m", {"speed": 2}, "Smoother movement after every dash."),
            ("Long Stride", "m", {"dashlen": 0.35}, "Dash farther."),
            ("Momentum", "n", {"speed": 4, "dashcd": 0.04}, "NOTABLE: movement speed and dash recovery scale together."),
            ("Relentless Motion", "a", {"speed": 7, "dashlen": 0.65, "dashcd": 0.08}, "MAJOR: fast, long dashes with a noticeably shorter cooldown."),
        ]),
        ("PHASE", "turn the dash into a defensive tool", [
            ("Slip Frame", "m", {"iframe": 0.03}, "A little more invulnerability."),
            ("Ghost Step", "m", {"less_damage": 1.0}, "Take less damage briefly while moving."),
            ("Phase Window", "n", {"iframe": 0.07, "dashlen": 0.18}, "NOTABLE: longer safety window and dash."),
            ("Untouchable", "a", {"iframe": 0.14, "less_damage": 3, "dashcd": 0.04}, "MAJOR: commit to evasive dashes."),
        ]),
        ("RESET", "turn kills and stamina into mobility", [
            ("Fresh Legs", "m", {"stamr": 1.5}, "Recover stamina faster."),
            ("Blood Rush", "m", {"life_on_kill": 2}, "Kills restore a little life."),
            ("Killing Rhythm", "n", {"life_on_kill": 3, "dashcd": 0.03}, "NOTABLE: every takedown feeds your next escape."),
            ("Chain Reaction", "a", {"life_on_kill": 6, "dashcd": 0.09, "stamr": 2}, "MAJOR: kills fuel repeated movement."),
        ]),
    ],
    "strike": [
        ("IMPACT", "raw attack power and reach", [
            ("Heavy Hand", "m", {"dmg": 2, "melee": 2}, "More primary damage."),
            ("Long Reach", "m", {"lunge": 0.20, "strike_width": 0.03}, "Longer attack reach."),
            ("Crushing Form", "n", {"dmg": 5, "melee": 4, "strike_stun": 0.08}, "NOTABLE: stronger hits with a small stun bonus."),
            ("Overpower", "a", {"dmg": 9, "melee": 8, "lunge": 0.45}, "MAJOR: a heavy primary-attack route."),
        ]),
        ("PRECISION", "critical and attack speed", [
            ("Keen Edge", "m", {"crit": 1.8}, "More critical chance."),
            ("Quick Cut", "m", {"strike_cd": 0.03}, "Attack more often."),
            ("Vital Opening", "n", {"crit": 3, "cdmg": 7, "strike_cd": 0.04}, "NOTABLE: punish exposed targets with critical hits."),
            ("Perfect Timing", "a", {"crit": 6, "cdmg": 14, "strike_cd": 0.08}, "MAJOR: critical primary attacks become the core of the build."),
        ]),
        ("CONTROL", "stun, width and class identity", [
            ("Wide Arc", "m", {"strike_width": 0.10}, "Wider primary attack."),
            ("Stagger", "m", {"strike_stun": 0.10}, "More stun."),
            ("Class Technique", "n", {"strike_width": 0.12, "strike_stun": 0.08, "venom": 1}, "NOTABLE: reinforces each class's unique attack identity."),
            ("Master Technique", "a", {"strike_width": 0.18, "strike_stun": 0.18, "dmg": 6, "venom": 2}, "MAJOR: the primary attack becomes a specialist tool."),
        ]),
    ],
    "coil": [
        ("DURATION", "keep the field active", [
            ("Long Coil", "m", {"coil": 2}, "Longer Coil."),
            ("Persistent Bind", "m", {"coil": 2.5, "coil_slow": 0.04}, "Longer slow."),
            ("Lingering Coil", "n", {"coil": 4, "coil_slow": 0.08}, "NOTABLE: a wider window for control."),
            ("Endless Coil", "a", {"coil": 7, "coil_slow": 0.12, "coil_guard": 5}, "MAJOR: Coil is a persistent arena tool."),
        ]),
        ("CRUSH", "turn Coil into damage", [
            ("Pressure", "m", {"coil_dps": 2}, "More crush DPS."),
            ("Tight Wrap", "m", {"coil_dps": 2, "melee": 2}, "More damage while enemies are trapped."),
            ("Crushing Point", "n", {"coil_dps": 5, "strike_stun": 0.08}, "NOTABLE: trapped targets are easier to finish."),
            ("Constriction", "a", {"coil_dps": 9, "melee": 7, "python_root": 1}, "MAJOR: prioritize crushing damage and control."),
        ]),
        ("GUARD", "trade offense for safety", [
            ("Coil Guard", "m", {"coil_guard": 4}, "More guard while Coil is active."),
            ("Anchor", "m", {"armor": 2, "less_damage": 0.8}, "More resistance."),
            ("Living Brace", "n", {"coil_guard": 6, "bulwark_shield": 4}, "NOTABLE: Coil starts behaving like a defensive stance."),
            ("Immovable Coil", "a", {"coil_guard": 12, "armor": 6, "less_damage": 3}, "MAJOR: stay in the danger zone and survive it."),
        ]),
    ],
    "shed": [
        ("RECOVERY", "heal and regenerate", [
            ("Warm Blood", "m", {"regen": 0.25}, "More health regeneration."),
            ("Clean Shedding", "m", {"shed_heal": 0.025}, "Shed heals more."),
            ("Second Skin", "n", {"shed_heal": 0.05, "regen_pct": 0.03}, "NOTABLE: healing scales with maximum HP."),
            ("Rebirth", "a", {"shed_heal": 0.10, "regen": 0.8, "life_on_kill": 4}, "MAJOR: Shed becomes your primary sustain button."),
        ]),
        ("PHASE", "use the shed as an escape", [
            ("Slip Skin", "m", {"shed_iframe": 0.05}, "More invulnerability."),
            ("Afterimage", "m", {"shed_decoy": 1.5}, "A longer-lived decoy."),
            ("False Death", "n", {"shed_iframe": 0.11, "shed_decoy": 2.0}, "NOTABLE: Shed buys a real escape window."),
            ("Untethered", "a", {"shed_iframe": 0.20, "shed_decoy": 4, "speed": 5}, "MAJOR: leave danger behind immediately."),
        ]),
        ("FORTIFY", "convert healing into durability", [
            ("Thick Hide", "m", {"hp": 7}, "More maximum life."),
            ("Scaled Core", "m", {"hp_pct": 1.4, "armor": 2}, "More maximum HP and armor."),
            ("Renewed Flesh", "n", {"hp_pct": 2.2, "regen_pct": 0.04}, "NOTABLE: maximum HP and regeneration scale together."),
            ("Phoenix Skin", "a", {"hp_pct": 5, "armor": 5, "regen_pct": 0.08}, "MAJOR: a durable regeneration route."),
        ]),
    ],
    "heat": [
        ("REVEAL", "make information last", [
            ("Warm Vision", "m", {"heat": 1.0}, "Reveal enemies longer."),
            ("Thermal Map", "m", {"heat": 1.5}, "Extend Heat Sense."),
            ("True Sight", "n", {"heat": 2.5, "rng": 2}, "NOTABLE: revealed targets are easier to engage from range."),
            ("Omniscience", "a", {"heat": 4, "rng": 5}, "MAJOR: nearly constant tactical information."),
        ]),
        ("AMPLIFY", "convert revealed targets into damage", [
            ("Marked Flesh", "m", {"heat_mult": 0.04}, "More damage to revealed targets."),
            ("Weak Point", "m", {"crit": 1.5}, "Critical chance against tracked targets."),
            ("Hunter's Focus", "n", {"heat_mult": 0.08, "crit": 2}, "NOTABLE: revelation becomes offense."),
            ("Predator Scan", "a", {"heat_mult": 0.16, "crit": 4, "cdmg": 8}, "MAJOR: Heat Sense becomes a damage amplifier."),
        ]),
        ("OVERCLOCK", "reduce cooldown and improve energy", [
            ("Hot Circuit", "m", {"heat_cd": 0.8}, "Lower Heat Sense cooldown."),
            ("Stored Signal", "m", {"energy_recharge": 2}, "Recover energy faster."),
            ("Thermal Battery", "n", {"heat_cd": 1.5, "energy_recharge": 4, "energy_max": 1}, "NOTABLE: more uptime with a larger energy pool."),
            ("Overclock", "a", {"heat_cd": 3, "energy_recharge": 7, "energy_max": 2}, "MAJOR: information on demand."),
        ]),
    ],
    "scent": [
        ("REVEAL", "broaden detection", [
            ("Long Tongue", "m", {"scent_range": 1.5}, "Detect farther away."),
            ("Clear Scent", "m", {"scent_time": 0.6}, "Keep marked locations visible longer."),
            ("Wide Search", "n", {"scent_range": 3, "scent_time": 1}, "NOTABLE: reveal more of the nearby map."),
            ("All Seeing", "a", {"scent_range": 6, "scent_time": 2.5}, "MAJOR: TONGUE becomes a map-wide scout."),
        ]),
        ("TRACK", "make movement support tracking", [
            ("Hunter Pace", "m", {"speed": 2}, "Move more quickly toward objectives."),
            ("Marked Trail", "m", {"rng": 2}, "Longer engagement range."),
            ("Predator Route", "n", {"speed": 4, "crit": 1.5}, "NOTABLE: tracking naturally feeds offense."),
            ("Relentless Hunter", "a", {"speed": 7, "crit": 4, "dashlen": 0.4}, "MAJOR: convert tracking into pursuit."),
        ]),
        ("HUNGER", "turn discovery into resources", [
            ("Scented Blood", "m", {"life_on_kill": 1}, "Kills return a little life."),
            ("Resource Instinct", "m", {"energy_on_kill": 3}, "Kills restore energy."),
            ("Feast Signal", "n", {"life_on_kill": 2, "energy_on_kill": 4}, "NOTABLE: objectives become sustain opportunities."),
            ("Hunter's Feast", "a", {"life_on_kill": 5, "energy_on_kill": 8, "steal": 1.5}, "MAJOR: kills feed both resource systems."),
        ]),
    ],
    "spit": [
        ("RANGE", "precision projectile", [
            ("Long Jet", "m", {"spit_reach": 1.0}, "Spit farther."),
            ("Focused Jet", "m", {"spit_width": -0.10, "spit_reach": 0.7}, "Tighten the line for precision."),
            ("Sniper Venom", "n", {"spit_reach": 2.5, "pierce": 1}, "NOTABLE: longer and more penetrating."),
            ("Serpent Lance", "a", {"spit_reach": 4, "pierce": 2, "spit_damage": 5}, "MAJOR: turn Spit into artillery."),
        ]),
        ("TOXIN", "push venom damage", [
            ("Bitter Fluid", "m", {"spit_damage": 2}, "More poison payload."),
            ("Venom Glands", "m", {"venom": 2}, "Stronger poison follow-up."),
            ("Concentrated Toxin", "n", {"spit_damage": 4, "venom": 3, "em": 12}, "NOTABLE: a dedicated poison route."),
            ("Plague Jet", "a", {"spit_damage": 8, "venom": 6, "em": 28}, "MAJOR: make every Spit hit matter."),
        ]),
        ("CONTROL", "blind and stun enemies", [
            ("Blinding Jet", "m", {"spit_stun": 0.15}, "Longer blind/stun."),
            ("Wide Saliva", "m", {"spit_width": 0.15}, "Wider hit lane."),
            ("Disrupting Spray", "n", {"spit_stun": 0.35, "aoe": 0.12}, "NOTABLE: more reliable control."),
            ("Suppression", "a", {"spit_stun": 0.7, "spit_width": 0.25, "aoe": 0.25}, "MAJOR: Spit doubles as crowd control."),
        ]),
    ],
    "rattle": [
        ("BLAST", "larger panic radius", [
            ("Deep Rattle", "m", {"rattle_radius": 0.5}, "Larger pulse."),
            ("Forceful Pulse", "m", {"rattle_force": 3}, "More knockback."),
            ("Resonant Body", "n", {"rattle_radius": 1.0, "rattle_force": 5}, "NOTABLE: knock enemies out of danger zones."),
            ("Earthquake Rattle", "a", {"rattle_radius": 1.8, "rattle_force": 10, "strike_stun": 0.12}, "MAJOR: command the space around you."),
        ]),
        ("STUN", "turn control into safety", [
            ("Sharp Warning", "m", {"rattle_stun": 0.12}, "More stun."),
            ("Concussive Cry", "m", {"less_damage": 1}, "Take less damage during the panic."),
            ("Shock Fear", "n", {"rattle_stun": 0.35, "less_damage": 1.5}, "NOTABLE: stun buys time."),
            ("Mass Panic", "a", {"rattle_stun": 0.65, "less_damage": 3, "rattle_radius": 0.8}, "MAJOR: a defensive crowd-control pulse."),
        ]),
        ("PURGE", "clear bullets and recover", [
            ("Clean Air", "m", {"rattle_radius": 0.3}, "The projectile-clear zone reaches farther."),
            ("Feedback", "m", {"energy_recharge": 2}, "Recover energy faster."),
            ("Pulse Feast", "n", {"energy_on_kill": 3, "life_on_hit": 0.3}, "NOTABLE: close-range control feeds resources."),
            ("Silent Arena", "a", {"energy_on_kill": 8, "life_on_hit": 1.2, "rattle_radius": 1.2}, "MAJOR: erase danger and immediately rebuild resources."),
        ]),
    ],
    "camo": [
        ("VEIL", "longer stealth", [
            ("Thin Shadow", "m", {"camo_time": 0.5}, "Camouflage lasts longer."),
            ("Deep Veil", "m", {"camo_range": 0.25}, "Enemies must get closer to detect you."),
            ("Ghost Skin", "n", {"camo_time": 1.2, "camo_range": 0.35}, "NOTABLE: stronger stealth."),
            ("Perfect Vanish", "a", {"camo_time": 2.4, "camo_range": 0.8}, "MAJOR: disappear from normal enemy pursuit."),
        ]),
        ("AMBUSH", "burst after stealth", [
            ("Patient Fang", "m", {"crit": 2}, "More critical chance."),
            ("Predator Mind", "m", {"cdmg": 5, "dmg": 2}, "More burst damage."),
            ("Ambush", "n", {"crit": 4, "cdmg": 8}, "NOTABLE: opening attacks hit harder."),
            ("First Strike", "a", {"crit": 7, "cdmg": 16, "dmg": 6}, "MAJOR: make every stealth exit dangerous."),
        ]),
        ("ESCAPE", "mobility and survival", [
            ("Slip Away", "m", {"dashlen": 0.25}, "Longer dash after Camouflage."),
            ("Fading Step", "m", {"speed": 2, "iframe": 0.03}, "Move safer."),
            ("Escape Artist", "n", {"speed": 4, "dashcd": 0.04, "iframe": 0.05}, "NOTABLE: stealth and mobility reinforce each other."),
            ("Now You See Me", "a", {"speed": 7, "dashlen": 0.6, "dashcd": 0.10, "iframe": 0.10}, "MAJOR: become extremely difficult to pin down."),
        ]),
    ],
    "volley": [
        ("BARRAGE", "more projectiles", [
            ("Extra Chamber", "m", {"volley_count": 1}, "One more bolt."),
            ("Rapid Load", "m", {"volley_cd": 0.12}, "Lower Volley cooldown."),
            ("Fan Pattern", "n", {"volley_count": 2, "volley_damage": 0.04}, "NOTABLE: a denser fan."),
            ("Hydra Arsenal", "a", {"volley_count": 4, "volley_damage": 0.10, "volley_cd": 0.4}, "MAJOR: turn Volley into sustained projectile pressure."),
        ]),
        ("ARTILLERY", "range and penetration", [
            ("Long Sight", "m", {"rng": 2}, "More ranged reach."),
            ("Piercing Shell", "m", {"volley_pierce": 1, "pierce": 1}, "More penetration."),
            ("Ballistic Focus", "n", {"rng": 4, "volley_pierce": 2, "cdmg": 5}, "NOTABLE: shots stay useful at range."),
            ("Serpent Cannon", "a", {"rng": 8, "volley_pierce": 4, "pierce": 2, "volley_damage": 0.08, "cobra_artillery": 1}, "MAJOR: compress the volley into powerful artillery."),
        ]),
        ("ELEMENTAL", "reactions and mastery", [
            ("Charged Hood", "m", {"em": 10}, "More Elemental Mastery."),
            ("Primer Bolt", "m", {"cobra_reaction": 0.3, "venom": 1}, "Improve reactions."),
            ("Catalyst Array", "n", {"em": 24, "cobra_elemental": 0.5, "cobra_reaction": 0.5}, "NOTABLE: make the fan feed reactions."),
            ("Prismatic Volley", "a", {"em": 50, "cobra_elemental": 1.0, "cobra_reaction": 1, "volley_damage": 0.06}, "MAJOR: specialize in elemental saturation."),
        ]),
    ],
    "bulwark": [
        ("FORTIFY", "bigger barrier", [
            ("Thick Plate", "m", {"armor": 2}, "More armor."),
            ("Barrier Mass", "m", {"bulwark": 4, "bulwark_shield": 3}, "More barrier."),
            ("Iron Ward", "n", {"bulwark": 7, "bulwark_shield": 6}, "NOTABLE: a larger shield."),
            ("Fortress", "a", {"bulwark": 14, "bulwark_shield": 14, "armor": 6}, "MAJOR: Bulwark becomes a full defensive stance."),
        ]),
        ("AEGIS", "uptime and mitigation", [
            ("Long Brace", "m", {"bulwark_time": 0.4}, "Stay protected longer."),
            ("Steady Core", "m", {"less_damage": 1.2}, "Take less damage."),
            ("Aegis Protocol", "n", {"bulwark_time": 0.8, "less_damage": 2.0, "shield_pct": 2}, "NOTABLE: defense compounds while Bulwark is active."),
            ("Unbreakable", "a", {"bulwark_time": 1.6, "less_damage": 5, "shield_pct": 5}, "MAJOR: maximum defensive uptime."),
        ]),
        ("RETRIBUTION", "turn defense into offense", [
            ("Reinforced Blow", "m", {"melee": 2}, "More close damage."),
            ("Countershock", "m", {"strike_stun": 0.08}, "Stun enemies that enter your barrier."),
            ("Spiteful Guard", "n", {"melee": 4, "strike_stun": 0.14, "bulwark_radius": 0.3}, "NOTABLE: the barrier punishes nearby enemies."),
            ("Iron Reprisal", "a", {"melee": 8, "strike_stun": 0.25, "bulwark_radius": 0.8, "bulwark": 6}, "MAJOR: turn Bulwark into an offensive bunker."),
        ]),
    ],
    "class_skill": [
        ("FOCUS", "lower cost and more signature uptime", [
            ("Signature Training", "m", {"class_skill": 0.4}, "Higher signature skill rank."),
            ("Stored Power", "m", {"energy_recharge": 2}, "Recover resources faster."),
            ("Signature Circuit", "n", {"class_skill": 0.8, "energy_recharge": 4}, "NOTABLE: signature rank and resource recovery."),
            ("Master Circuit", "a", {"class_skill": 1.5, "energy_recharge": 7, "energy_max": 1}, "MAJOR: your signature is available more often."),
        ]),
        ("POWER", "directly amplify the V identity", [
            ("Charged Signature", "m", {"dmg": 2, "em": 8}, "More signature impact."),
            ("Lethal Pattern", "m", {"crit": 2, "cdmg": 5}, "More burst."),
            ("Signature Force", "n", {"dmg": 5, "em": 18, "crit": 2}, "NOTABLE: direct V power."),
            ("Transcendent V", "a", {"dmg": 10, "em": 35, "crit": 4, "cdmg": 8}, "MAJOR: make the class signature your centerpiece."),
        ]),
        ("EVOLUTION", "defense, speed and kill momentum", [
            ("Surging Form", "m", {"speed": 2}, "More movement during signature play."),
            ("Aftercast", "m", {"less_damage": 1}, "Safer after the signature."),
            ("Evolved Instinct", "n", {"speed": 4, "less_damage": 1.5, "life_on_kill": 2}, "NOTABLE: signature kills feed momentum."),
            ("Apex Evolution", "a", {"speed": 7, "less_damage": 3, "life_on_kill": 5, "class_skill": 0.8}, "MAJOR: evolve the whole class around V."),
        ]),
    ],
}

# Extra branch-defining nodes.  These sit after the first Notable on each
# specialization so every active skill has a deeper progression and more genuine
# build-changing choices rather than four generic upgrades per lane.
EXTRA_PATH_NODES = {
    "dash": [
        [("Sidewinder Step", "m", {"dash_len": 0.18}, "Slightly longer lateral movement."),
         ("Afterimage Trail", "m", {"dash_afterimage": 1}, "Leave a brief decoy trail."),
         ("Turbo Coil", "n", {"dash_speed": 4}, "Gain movement speed after dashing.")],
        [("Blink Frame", "m", {"dash_iframes": 0.05}, "Extend the safe part of the dash."),
         ("Slip Burst", "m", {"dash_explode": 1}, "A short wind burst follows the dash."),
         ("Ghost Route", "n", {"dash_chain": 1}, "Kills can briefly feed the next dash." )],
        [("Bloodstep", "m", {"dash_lifesteal": 1}, "Dash hits restore a little life."),
         ("Kill Switch", "m", {"dash_reset": 1}, "A takedown can refresh Dash."),
         ("Hunt Momentum", "n", {"dash_speed": 6, "dash_reset": 1}, "Aggressive movement becomes self-sustaining.")],
    ],
    "strike": [
        [("Twin Fang", "m", {"strike_multi": 1}, "Primary attacks produce an extra strike."),
         ("Triple Pressure", "m", {"strike_multi": 2}, "A second upgrade adds another hit lane."),
         ("Fracture Bite", "n", {"strike_explode": 1}, "The main target releases a small elemental burst.")],
        [("Double Tap", "m", {"strike_repeat": 1}, "A clean hit repeats a fraction of the attack."),
         ("Marked Core", "m", {"strike_mark": 1}, "Critical hits mark the target for follow-up damage."),
         ("Execution Rhythm", "n", {"strike_reset": 1, "strike_repeat": 1}, "Finishing a marked target accelerates the next attack.")],
        [("Arc Bite", "m", {"strike_arc": 0.16}, "Widen the attack's active arc."),
         ("Shockwave Fang", "m", {"strike_wave": 1}, "A heavy primary hit sends a short wave."),
         ("Elemental Fang", "n", {"strike_element": 1, "strike_split": 1, "strike_reaction": 1, "em": 8}, "Primary attacks carry stronger elemental payloads and can split on impact.")],
    ],
    "coil": [
        [("Second Coil", "m", {"coil_echo": 1}, "A second pulse lingers after Coil ends."),
         ("Wide Loop", "m", {"coil_radius": 0.45}, "Increase the control radius."),
         ("Lingering Pulse", "n", {"coil_pulse": 1, "coil_echo": 1}, "Coil pulses again before fading.")],
        [("Implosion", "m", {"coil_explode": 1}, "Ending Coil pulls damage inward."),
         ("Rupture", "m", {"coil_burst": 1}, "Crushed enemies release a burst."),
         ("Predator Clamp", "n", {"coil_execute": 1}, "Very low-health trapped enemies take extra damage.")],
        [("Return Damage", "m", {"coil_reflect": 1}, "Part of nearby incoming damage is returned."),
         ("Iron Spiral", "m", {"coil_guard_pulse": 1}, "Coil briefly hardens you on pulse."),
         ("Bastion Coil", "n", {"coil_shield": 5}, "Gain a small barrier while Coil persists.")],
    ],
    "shed": [
        [("Burst Renewal", "m", {"shed_burst": 1}, "Shed also releases a healing pulse."),
         ("Cleanse", "m", {"shed_cleanse": 1}, "Shed clears harmful states."),
         ("Overflow", "n", {"shed_burst": 1, "shed_overheal": 1}, "Excess healing becomes temporary shield.")],
        [("Ghost Copies", "m", {"shed_copies": 1}, "Leave an extra decoy."),
         ("Reverse Trail", "m", {"shed_warp": 1}, "The escape path gains a stronger reposition."),
         ("Skin Fragment", "n", {"shed_shards": 1}, "Nearby enemies are punished when the skin breaks.")],
        [("Hardened Shed", "m", {"shed_guard": 3}, "Gain armor after shedding."),
         ("Return Venom", "m", {"shed_thorns": 1}, "Enemies hitting the shed are poisoned."),
         ("Recast Shell", "n", {"shed_reset": 1}, "A takedown can partially refresh Shed.")],
    ],
    "heat": [
        [("Heat Pulse", "m", {"heat_pulse": 1}, "Revealing emits a short-range damage pulse."),
         ("Broad Scan", "m", {"heat_range": 2}, "Reach farther targets."),
         ("Thermal Echo", "n", {"heat_repeat": 1}, "A second reveal pulse follows the first.")],
        [("Expose Weakness", "m", {"heat_mark": 1}, "Revealed enemies take more damage."),
         ("Scorch Mark", "m", {"heat_element": 1}, "Heat marks carry elemental pressure."),
         ("Hunter's Lens", "n", {"heat_crit": 3}, "Revealed targets are easier to critically hit.")],
        [("Fast Scan", "m", {"heat_fast": 1}, "Reduce Heat Sense recovery."),
         ("Stored Signal", "m", {"heat_energy": 1}, "Heat Sense helps restore energy."),
         ("Overclock Burst", "n", {"heat_burst": 1, "heat_fast": 1}, "Repeated scans build momentum.")],
    ],
    "scent": [
        [("Twin Scent", "m", {"scent_multi": 1}, "Track an extra target."),
         ("Long Tongue", "m", {"scent_range": 2}, "Extend detection range."),
         ("Trail Lock", "n", {"scent_mark": 1}, "Keep tracked targets marked longer.")],
        [("Charge Sense", "m", {"scent_charge": 1}, "Sense energy pickups more reliably."),
         ("Pickup Draw", "m", {"scent_magnet": 1}, "Nearby pickups drift toward you."),
         ("Cache Finder", "n", {"scent_xp": 1}, "Tracking hidden resources yields bonus XP.")],
        [("Mark Prey", "m", {"scent_damage": 3}, "Tracked enemies take more damage."),
         ("Hunt Speed", "m", {"scent_speed": 4}, "Move faster after sensing prey."),
         ("Kill Echo", "n", {"scent_reset": 1}, "A takedown extends the next scent window.")],
    ],
    "spit": [
        [("Double Spit", "m", {"spit_count": 1}, "Fire an additional venom jet."),
         ("Triple Spit", "m", {"spit_count": 2}, "Fire a third lane."),
         ("Fan Spray", "n", {"spit_spread": 0.24}, "Spread the jets into a wider fan.")],
        [("Bounce Saliva", "m", {"spit_bounce": 1}, "The jet can rebound once."),
         ("Sticky Venom", "m", {"spit_venom": 2}, "Venom lasts longer and stacks harder."),
         ("Caustic Pool", "n", {"spit_explode": 1}, "A hit creates a small damaging pool.")],
        [("Elemental Spit", "m", {"spit_element": 1, "em": 8}, "Spit carries stronger elemental reactions."),
         ("Reaction Primer", "m", {"spit_reaction": 1}, "Prime enemies for a follow-up reaction."),
         ("Chain Reaction", "n", {"spit_chain": 2, "spit_element": 1}, "Reactions can jump to a nearby foe.")],
    ],
    "rattle": [
        [("Double Pulse", "m", {"rattle_pulses": 1}, "Emit a second panic ring."),
         ("Wide Ring", "m", {"rattle_radius": 0.55}, "Increase the pulse radius."),
         ("Resonant Wave", "n", {"rattle_wave": 1}, "The pulse travels farther as a wave.")],
        [("Echo Fear", "m", {"rattle_stun": 0.18}, "Stun lasts longer."),
         ("Pulse Armor", "m", {"rattle_guard": 2}, "Gain a brief damage reduction after the pulse."),
         ("Lockdown", "n", {"rattle_hold": 1}, "Strongly stunned enemies move more slowly afterward.")],
        [("Projectile Sweep", "m", {"rattle_clear": 1}, "Wipe projectiles from farther away."),
         ("Energy Feedback", "m", {"rattle_energy": 2}, "Clearing danger restores energy."),
         ("Shock Harvest", "n", {"rattle_on_kill": 1, "rattle_energy": 3}, "Deaths inside the pulse refund resources.")],
    ],
    "camo": [
        [("Long Veil", "m", {"camo_time": 0.8}, "Extend Camouflage."),
         ("Shadow Radius", "m", {"camo_range": 0.35}, "Become harder to reveal."),
         ("Fade Pulse", "n", {"camo_pulse": 1}, "Entering stealth briefly disrupts enemies.")],
        [("Opening Volley", "m", {"camo_shot": 1}, "Leaving Camouflage fires an opening shot."),
         ("Critical Exit", "m", {"camo_crit": 3}, "Your first attack from stealth is more critical."),
         ("Predator Break", "n", {"camo_explode": 1}, "The stealth exit creates an elemental burst.")],
        [("Shadow Dash", "m", {"camo_dash": 1}, "Gain a short dash window after entering stealth."),
         ("Vanish Reset", "m", {"camo_reset": 1}, "Takedowns shorten Camouflage recovery."),
         ("Afterimage", "n", {"camo_clone": 1, "camo_dash": 1}, "Leave a moving shadow copy.")],
    ],
    "volley": [
        [("Double Volley", "m", {"volley_multi": 1}, "Fire an extra projectile pair."),
         ("Triple Fan", "m", {"volley_multi": 2}, "Add a third layer to the fan."),
         ("Hydra Split", "n", {"volley_split": 1}, "Projectiles split after impact.")],
        [("Piercing Array", "m", {"volley_pierce": 1}, "More enemies can be pierced."),
         ("Ricochet Shell", "m", {"volley_bounce": 1}, "Shots can bounce to another target."),
         ("Siege Payload", "n", {"volley_explode": 1}, "Impacts cause a small elemental explosion.")],
        [("Elemental Payload", "m", {"volley_element": 1, "em": 10}, "Shots interact more strongly with elements."),
         ("Reaction Burst", "m", {"volley_reaction": 1}, "Elemental impacts create stronger reactions."),
         ("Prismatic Chain", "n", {"volley_chain": 2, "volley_element": 1}, "Elemental shots can jump between marked targets.")],
    ],
    "bulwark": [
        [("Thick Wall", "m", {"bulwark_hp": 6}, "Increase barrier durability."),
         ("Barrier Regen", "m", {"bulwark_regen": 1}, "Recover barrier while Bulwark is active."),
         ("Fortress Core", "n", {"bulwark_scale": 1}, "Bulwark scales better with your maximum HP.")],
        [("Reflective Shield", "m", {"bulwark_reflect": 1}, "Part of ranged damage is reflected."),
         ("Pulse Ward", "m", {"bulwark_pulse": 1}, "Bulwark periodically staggers nearby enemies."),
         ("Time Barrier", "n", {"bulwark_extend": 1}, "Taking heavy damage briefly extends Bulwark.")],
        [("Shock Guard", "m", {"bulwark_wave": 1}, "Entering Bulwark sends a shockwave."),
         ("Spite Aura", "m", {"bulwark_damage": 3}, "Nearby enemies take more retaliation damage."),
         ("Last Stand", "n", {"bulwark_laststand": 1}, "Low health greatly strengthens the barrier.")],
    ],
    "class_skill": [
        [("Twin Signature", "m", {"class_multi": 1}, "Add an extra signature projectile or pulse."),
         ("Faster Signature", "m", {"class_cd": 0.6}, "Recover V faster."),
         ("Stored V", "n", {"class_energy": 1}, "V can recover a little energy on impact.")],
        [("Signature Pierce", "m", {"class_pierce": 1}, "Signature projectiles penetrate further."),
         ("Signature Burst", "m", {"class_explode": 1}, "Signature impacts create an elemental burst."),
         ("Elemental V", "n", {"class_element": 1, "em": 16}, "V strongly reinforces the selected element.")],
        [("V Afterimage", "m", {"class_clone": 1}, "Leave a brief signature afterimage."),
         ("V Echo", "m", {"class_echo": 1}, "A smaller delayed copy follows the cast."),
         ("Apex Tempo", "n", {"class_chain": 2, "class_multi": 1}, "Signature hits chain into a second target.")],
    ],
}

CLASS_CAPSTONES = {
    "viper": (("Miasma Sovereign", {"viper_alchemist": 1, "viper_pool_duration": 2, "venom": 6, "class_skill": 1.2}, "CAPSTONE: signature V paints persistent venom territory."),
               ("Blood-Fed Serpent", {"viper_fang": 1, "steal": 4, "life_on_kill": 8, "class_skill": 1.0}, "CAPSTONE: the Viper converts damage into sustained healing.")),
    "python": (("Titan's Apex", {"python_titan": 1, "hp_pct": 8, "armor": 8, "class_skill": 1.2}, "CAPSTONE: enormous body scaling and durable signature hits."),
                ("World Coil", {"python_constrictor": 1, "coil_guard": 10, "bulwark": 12, "class_skill": 1.0}, "CAPSTONE: V locks down space with a crushing fortress.")),
    "cobra": (("Hydra Arsenal", {"cobra_barrage": 1, "volley_count": 4, "volley_damage": 0.12, "class_skill": 1.2}, "CAPSTONE: signature V becomes a devastating projectile fan."),
               ("Prismatic Cataclysm", {"cobra_prism": 1, "em": 80, "cobra_elemental": 2, "cobra_reaction": 1, "class_skill": 1.0}, "CAPSTONE: cycle unlocked elements through the signature pattern.")),
    "mamba": (("Thunder Reign", {"mamba_tempo": 1, "chain": 8, "energy_recharge": 8, "class_skill": 1.2}, "CAPSTONE: signature V chains through enemies and resets momentum."),
               ("Void Execution", {"mamba_voidstep": 1, "mamba_executioner": 1, "crit": 7, "cdmg": 16, "class_skill": 1.0}, "CAPSTONE: become an execution-focused lightning assassin.")),
}


# ---------- skill definitions + graph -----------------------------------
for cid in CLASSES:
    defs = {}
    # Per-class name and colour for the primary/signature entries.
    basic_name = CLASSES[cid]["basic"]["name"]
    sig_name = CLASSES[cid]["skill"]["name"]
    basic_color = CLASSES[cid]["basic"]["col"]
    sig_color = CLASSES[cid]["skill"]["color"]
    slot_map = {key: slot for key, slot, _name, _col in SKILLS}
    color_map = {key: col for key, _slot, _name, col in SKILLS}
    names = {"strike": basic_name, "class_skill": sig_name}
    for key, _slot, name, _col in SKILLS:
        defs[key] = {
            "name": names.get(key, GENERIC.get(key, (name, ""))[0]),
            "slot": slot_map[key],
            "color": basic_color if key == "strike" else (sig_color if key == "class_skill" else color_map[key]),
            "desc": GENERIC.get(key, (name, ""))[1],
        }
    # Compatibility aliases for older HUD/ability code.
    defs["basic"] = defs["strike"]
    defs["v"] = defs["class_skill"]
    SKILL_DEFS[cid] = defs

    # 4 x 3 cluster field. The whole active tree fits into a zoomable overview.
    cols = [-465, -155, 155, 465]
    rows = [-245, 0, 245]
    skill_order = [key for key, _slot, _name, _col in SKILLS]

    for idx, line in enumerate(skill_order):
        col_i = idx % 4
        row_i = idx // 4
        cx, cy = cols[col_i], rows[row_i]
        paths = BASE_PATHS[line]
        # Every skill starts at a free root.  Each specialization now has a much
        # deeper route: 5 minors -> notable -> minor -> notable -> major.
        root = add(cid, line, "root", defs[line]["name"], "r", cx - 145, cy,
                   {}, f"ROOT: free starting socket for {defs[line]['name']}.")
        entries = []
        extra = EXTRA_PATH_NODES[line]
        for pi, (pname, pdesc, nodes) in enumerate(paths):
            py = cy + (-62 + pi * 62)
            ent = add(cid, line, f"p{pi}_0", pname, "m", cx - 104, py,
                      {k: v * 0.25 for k, v in nodes[0][2].items()},
                      f"Enter the {pname.title()} specialization: {pdesc}.", 1)
            entries.append(ent)
            edge(root, ent)
            prev = ent
            # Existing first 3 authored nodes, then three new build-defining nodes,
            # then the authored major as the path cap.
            authored = list(nodes[:3])
            new_nodes = extra[pi]
            path_nodes = authored + new_nodes + [nodes[3]]
            xvals = [cx - 62, cx - 24, cx + 14, cx + 52, cx + 90, cx + 128, cx + 166]
            for ni, (nm, kind, stats, desc) in enumerate(path_nodes, start=1):
                bend = (pi - 1) * (5 if ni >= 4 else 3)
                nd = add(cid, line, f"p{pi}_{ni}", nm, kind, xvals[ni-1], py + bend,
                         stats, desc, ni)
                edge(prev, nd)
                prev = nd

        mastery = add(cid, line, "mastery", f"{defs[line]['name']} MASTERY", "j", cx + 208, cy,
                      {"dmg": 0.7}, "MASTERY SOCKET: small all-purpose increase for this skill.", 3)
        for pi in range(3):
            edge(f"{cid}:{line}:p{pi}_7", mastery)
        # Cross-links between paths make it possible to weave instead of taking a
        # perfectly straight lane, without making the graph unreadable.
        edge(f"{cid}:{line}:p0_2", f"{cid}:{line}:p1_1")
        edge(f"{cid}:{line}:p1_3", f"{cid}:{line}:p2_2")
        edge(f"{cid}:{line}:p2_4", f"{cid}:{line}:p0_3")
        edge(f"{cid}:{line}:p0_5", f"{cid}:{line}:p1_4")
        edge(f"{cid}:{line}:p1_5", f"{cid}:{line}:p2_5")
        edge(f"{cid}:{line}:p2_6", f"{cid}:{line}:p0_6")

        cap_a, cap_b = CLASS_CAPSTONES[cid] if line == "class_skill" else (
            (f"{defs[line]['name']} Mastery", {"dmg": 5, "class_skill": 0}, "CAPSTONE: commit to a specialist version of this skill."),
            (f"{defs[line]['name']} Ascendant", {"dmg": 3, "energy_recharge": 4}, "CAPSTONE: commit to a utility-heavy version of this skill."),
        )
        for ci, cap in enumerate((cap_a, cap_b)):
            cname, stats, desc = cap
            kid = add(cid, line, f"cap{ci}", cname, "k", cx + 215, cy + (-38 if ci == 0 else 38),
                      stats, desc, 4, f"{cid}:{line}:capstone")
            edge(mastery, kid)


def nodes_for_class(cid):
    return [nid for nid in SKILL_NODES if nid.startswith(cid + ":")]


def skill_nodes_for_line(cid, line):
    line = canonical_line(line)
    return [nid for nid in nodes_for_class(cid) if SKILL_NODES[nid]["line"] == line]


def skill_level(cid, alloc, line):
    """Legacy 1..5 milestone used by the V-skill evolution code."""
    line = canonical_line(line)
    best = 0
    for nid in skill_nodes_for_line(cid, line):
        if nid in alloc:
            best = max(best, int(SKILL_NODES[nid]["evolve"]))
    return max(1, min(5, 1 + best))


def current_node(cid, alloc, line):
    line = canonical_line(line)
    owned = [SKILL_NODES[nid] for nid in skill_nodes_for_line(cid, line) if nid in alloc]
    return max(owned, key=lambda n: (n["evolve"], n["id"])) if owned else SKILL_NODES[f"{cid}:{line}:root"]


def skill_nodes_for_class(cid):
    return nodes_for_class(cid)
