"""Playable snake classes and their signature V skills.

Every class has a clear combat identity.  The element system is shared by all classes,
while the class skill gives each snake a different way to exploit that system.
"""

CLASSES = {
    "viper": dict(
        name="VIPER", role="DOT / SETUP", col="#ffd34d",
        desc=["Poisons enemies and leaves traps.", "LMB: FANG BITE - STACKING VENOM", "V: VENOM TRAIL"],
        basic=dict(name="FANG BITE", label="FANG", col="#7ddb4a", desc="Short, fast bite that stacks venom (x5)."),
        stats=dict(speed=4, crit=5, melee=8, dmg=8, class_skill=1),
        bars=dict(HP=3, SPD=3, ATK=3, RNG=3),
        skill=dict(name="VENOM TRAIL", key="V", desc="Dash a short distance and leave venom pools behind.", color="#7ddb4a"),
        pal=("#e8892f", "#ffe28a", "#3d1d07", "#a85a14", "#fff1c2")),
    "python": dict(
        name="PYTHON", role="TANK / CONTROL", col="#ffa23c",
        desc=["Armoured constrictor.", "LMB: TAIL SLAM - 360 DEG KNOCKBACK", "V: COLOSSAL COIL"],
        basic=dict(name="TAIL SLAM", label="SLAM", col="#ffa23c", desc="Slow 360-degree sweep: stun, knock-back, shield."),
        stats=dict(hp=70, armor=14, wallres=50, speed=-8, melee=15, form_tank=1, bulwark=10, class_skill=1),
        bars=dict(HP=5, SPD=1, ATK=3, RNG=1),
        skill=dict(name="COLOSSAL COIL", key="V", desc="Brace, crush nearby enemies, then slam outward.", color="#ffa23c"),
        pal=("#5a8fd6", "#d6ecff", "#10243f", "#2f5a9a", "#f0fbff")),
    "cobra": dict(
        name="COBRA", role="RANGED / REACTIONS", col="#ff5da2",
        desc=["Spitting hooded cobra.", "LMB: VENOM BOLT - RANGED SHOT", "V: VENOM BARRAGE"],
        basic=dict(name="VENOM BOLT", label="BOLT", col="#ff5da2", desc="Aimed ranged elemental bolt."),
        stats=dict(rng=25, ammo=4, pierce=1, hp=-15, volley=1, form_ranged=1, class_skill=1),
        bars=dict(HP=2, SPD=3, ATK=2, RNG=5),
        skill=dict(name="VENOM BARRAGE", key="V", desc="Fire a wide elemental fan with a lingering poison burst.", color="#7ddb4a"),
        pal=("#2fbf7a", "#b8ffdf", "#0c3a24", "#1f8a58", "#eafff5")),
    "mamba": dict(
        name="MAMBA", role="ASSASSIN / BURST", col="#e6ff4a",
        desc=["Lightning-fast striker.", "LMB: VOLT SLASH - EXECUTE + CHAIN", "V: THUNDERCOIL"],
        basic=dict(name="VOLT SLASH", label="SLASH", col="#c18bff", desc="Wide slash: executes weak foes, chains Electro."),
        stats=dict(speed=16, crit=10, cdmg=25, melee=22, dashcd=0.2, hp=-25, form_mamba=1, class_skill=1),
        bars=dict(HP=1, SPD=5, ATK=5, RNG=1),
        skill=dict(name="THUNDERCOIL", key="V", desc="Dash through enemies and arc Electro between them.", color="#c18bff"),
        pal=("#b44dff", "#f1c9ff", "#2a0a45", "#7a2fc0", "#ffffff")),
}
CLASS_ORDER = ["viper", "python", "cobra", "mamba"]
