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
