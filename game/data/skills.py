"""Player abilities shown on the hotbar.

V is the class signature ability.  It is intentionally separate from elemental
selection: the signature skill always uses the class identity while inheriting the
currently selected element when it makes contact.
"""

SKILLS = [
    ("dash", "SHIFT", "DASH", "#6fffd0"),
    ("strike", "LMB", "STRIKE", "#ffb347"),
    ("coil", "Q", "COIL", "#f5c542"),
    ("shed", "E", "SHED", "#4aa8ff"),
    ("heat", "R", "HEAT", "#ff6a3a"),
    ("scent", "T", "SCENT", "#c18bff"),
    ("spit", "Y", "SPIT", "#7ddb4a"),
    ("rattle", "F", "RATTLE", "#ffd34d"),
    ("camo", "G", "CAMO", "#9aa8c8"),
    ("volley", "Z", "VOLLEY", "#ff5da2"),
    ("bulwark", "C", "BULWARK", "#ffa23c"),
    ("class_skill", "V", "CLASS", "#ffffff"),
]
