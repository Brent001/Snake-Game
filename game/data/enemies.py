"""Enemy species, biome assignment and named champions.

The base roster now has three species per biome.  New species emphasize different
readable behaviours instead of being simple HP bags: shielders, ambushers, swarms,
spellcasters, trap throwers and ricochet attackers.
"""

ENEMY_TYPES = [
    # Frost Moon
    dict(name="Moon Rabbit", sprite="rabbit", hp=34, spd=2.4, ai="leap", dmg=10, xp=14, weak="electro", col="#ffffff"),
    dict(name="Ice Fairy", sprite="fairy", hp=30, spd=1.8, ai="shoot", dmg=8, xp=16, weak="pyro", col="#7df9ff"),
    dict(name="Frost Kappa", sprite="kappa", hp=58, spd=1.3, ai="shield", dmg=11, xp=23, weak="pyro", col="#6fdfff"),
    # Misty Lake
    dict(name="Kodama", sprite="kodama", hp=48, spd=0.0, ai="turret", dmg=8, xp=18, weak="pyro", col="#7ddb4a"),
    dict(name="Water Wisp", sprite="wisp", hp=22, spd=2.8, ai="bomber", dmg=14, xp=18, weak="electro", col="#4aa8ff"),
    dict(name="Kappa Mine", sprite="kappa", hp=42, spd=1.5, ai="trap", dmg=12, xp=24, weak="electro", col="#5ed8c2"),
    # Forest of Magic
    dict(name="Mushroom Imp", sprite="shroom", hp=36, spd=1.5, ai="orbit", dmg=8, xp=20, weak="pyro", col="#d98aff"),
    dict(name="Star Sprite", sprite="star", hp=26, spd=1.4, ai="sniper", dmg=12, xp=18, weak="geo", col="#ffe55a"),
    dict(name="Doll Swarm", sprite="doll", hp=18, spd=3.0, ai="swarm", dmg=7, xp=17, weak="hydro", col="#d6a5ff"),
    # Scarlet Mansion Grounds
    dict(name="Fire Maid", sprite="maid", hp=40, spd=2.2, ai="strafe", dmg=9, xp=20, weak="hydro", col="#ff6a3a"),
    dict(name="Scarlet Bat", sprite="bat", hp=24, spd=3.2, ai="leap", dmg=9, xp=22, weak="light", col="#ff5d8f"),
    dict(name="Knife Maid", sprite="maid_blue", hp=30, spd=2.4, ai="knife", dmg=11, xp=25, weak="geo", col="#a9c4ff"),
    # Netherworld
    dict(name="Phantom", sprite="phantom", hp=44, spd=1.6, ai="ghost", dmg=9, xp=24, weak="light", resist="abyss", col="#bcd8ff"),
    dict(name="Soul Lantern", sprite="lantern", hp=40, spd=1.2, ai="sniper", dmg=12, xp=26, weak="light", resist="abyss", col="#9fd8ff"),
    dict(name="Yin-Yang Wraith", sprite="wraith", hp=36, spd=2.0, ai="orbit", dmg=12, xp=28, weak="light", col="#c78bff"),
    # Hakurei Shrine
    dict(name="Komainu", sprite="komainu", hp=90, spd=1.6, ai="guard", dmg=14, xp=34, weak="anemo", col="#f5c542"),
    dict(name="Fox Spirit", sprite="fox", hp=52, spd=2.0, ai="orbit", dmg=10, xp=30, weak="abyss", col="#ff9a5a"),
    dict(name="Umbrella Youkai", sprite="umbrella", hp=50, spd=1.9, ai="ambush", dmg=13, xp=32, weak="hydro", col="#ff77bb"),
]

BIOME_ENEMIES = {
    0: [0, 1, 2],
    1: [3, 4, 5],
    2: [6, 7, 8],
    3: [9, 10, 11],
    4: [12, 13, 14],
    5: [15, 16, 17],
}

UNIQUE_NAMES = [
    "Rabbit Queen", "Frost Matron", "Elder Kodama", "Tidal Wisp Lord", "Forest Dollmaster", "Comet Warden",
    "Scarlet Maid Captain", "Crimson Bat Lord", "Knife Hall Mistress", "Restless Phantom", "Soul Beacon", "Yin-Yang Reaper",
    "Great Komainu", "Nine-Tail Fox", "Shrine Trickster", "Moonlit Champion", "Barrier Breaker", "Spellbound Youkai",
]
