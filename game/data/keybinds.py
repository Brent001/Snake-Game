"""Class-aware, PoE-inspired skill bars and shared keyboard slot bindings."""
SKILL_SLOT_IDS = ("slot_1", "slot_2", "slot_3", "slot_4", "slot_5")
CLASS_SKILL_PRESETS = {
    "viper": (("class_skill", "shed", "spit", "camo", "coil"),
              ("heat", "scent", "rattle", "volley", "bulwark")),
    "python": (("class_skill", "shed", "bulwark", "coil", "rattle"),
               ("heat", "scent", "spit", "camo", "volley")),
    "cobra": (("class_skill", "shed", "volley", "spit", "heat"),
              ("coil", "scent", "rattle", "camo", "bulwark")),
    "mamba": (("class_skill", "shed", "camo", "rattle", "volley"),
              ("coil", "heat", "scent", "spit", "bulwark")),
}
SKILL_LABELS = {
    "coil": "COIL", "shed": "SHED", "heat": "HEAT", "scent": "SCENT",
    "spit": "SPIT", "rattle": "RATTLE", "camo": "CAMO", "volley": "VOLLEY",
    "bulwark": "BULWARK", "class_skill": "CLASS",
}
SKILL_ACTION_METHODS = {
    "coil": "coil", "shed": "shed", "heat": "heat_sense", "scent": "tongue",
    "spit": "spit", "rattle": "rattle", "camo": "camo", "volley": "volley",
    "bulwark": "bulwark", "class_skill": "class_skill",
}
def skill_ids_for_bar(class_id, bar_index):
    """Return the five ability IDs for bar 1 or bar 2."""
    bars = CLASS_SKILL_PRESETS.get(class_id, CLASS_SKILL_PRESETS["viper"])
    return bars[1 if int(bar_index) else 0]
def skill_for_key(class_id, bar_index, slot_keys, pressed_key):
    """Resolve a pressed key to the ability on the currently active bar."""
    pressed_key = str(pressed_key).lower()
    for slot_id, skill_id in zip(SKILL_SLOT_IDS, skill_ids_for_bar(class_id, bar_index)):
        if str(slot_keys.get(slot_id, "")).lower() == pressed_key:
            return skill_id
    return None

# Every non-starter skill is earned at a class-specific level. Levels 2 and 3
# teach recovery and the signature move; levels 4-11 add one new combat option
# per level so the full kit is not available at character creation.
CLASS_SKILL_UNLOCK_LEVELS = {
    "viper": {
        "shed": 2, "class_skill": 3, "spit": 4, "camo": 5, "coil": 6,
        "rattle": 7, "heat": 8, "scent": 9, "volley": 10, "bulwark": 11,
    },
    "python": {
        "shed": 2, "class_skill": 3, "bulwark": 4, "coil": 5, "rattle": 6,
        "spit": 7, "heat": 8, "scent": 9, "volley": 10, "camo": 11,
    },
    "cobra": {
        "shed": 2, "class_skill": 3, "volley": 4, "spit": 5, "heat": 6,
        "coil": 7, "rattle": 8, "scent": 9, "bulwark": 10, "camo": 11,
    },
    "mamba": {
        "shed": 2, "class_skill": 3, "camo": 4, "rattle": 5, "volley": 6,
        "spit": 7, "coil": 8, "heat": 9, "bulwark": 10, "scent": 11,
    },
}


def skill_unlock_level(class_id, skill_id):
    """Return the first character level at which a skill can be used/upgraded."""
    aliases = {"basic": "strike", "v": "class_skill"}
    skill_id = aliases.get(skill_id, skill_id)
    if skill_id in ("dash", "strike"):
        return 1
    return CLASS_SKILL_UNLOCK_LEVELS.get(class_id, CLASS_SKILL_UNLOCK_LEVELS["viper"]).get(skill_id, 99)


def is_skill_unlocked(class_id, skill_id, level):
    return int(level) >= skill_unlock_level(class_id, skill_id)


def skills_unlocked_at_level(class_id, level):
    """Return skill IDs newly unlocked at this level, in deterministic table order."""
    rules = CLASS_SKILL_UNLOCK_LEVELS.get(class_id, CLASS_SKILL_UNLOCK_LEVELS["viper"])
    return tuple(skill_id for skill_id, required in rules.items() if required == int(level))
