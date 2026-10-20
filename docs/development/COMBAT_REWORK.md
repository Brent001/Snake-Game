# Combat Rework — Snake x Touhou

## What changed
- 18 enemy species: three distinct behaviors per biome, including shielders, traps, swarms, knife maids, wraiths, and ambushers.
- Every normal enemy now uses a 4-frame procedural animation strip made from the existing pixel-art models.
- Snake-body contact can apply the currently selected element, so movement/coiling creates reactions rather than making elements a projectile-only system.
- Elemental auras continue to decay on both normal enemies and bosses; boss reactions create distinct gameplay events: Freeze, Overload knockback, Electro-Charged chaining, Superconduct resistance shred, Bloom cores, Burgeon, Hyperbloom, Swirl spread, and Crystallize shields.
- Each class has a distinct V signature skill and its own gated skill-tree lane.
- Skill tree now separates class identity from the nine-element build layer.
- Bosses have higher phase HP, rage-scaled projectile speed, stronger arena hazards, spell-specific attacks, boss elemental auras/reactions, and a cast-timing Spell Break window.
- Flandre remains the Netherworld replacement for the old Yuyuko slot and uses Lævateinn / Four of a Kind / Starbow Break / Ripples of 495 Years patterns.

## Class signatures
- Viper — Venom Trail: leave damaging poison pockets and set up reactions.
- Python — Colossal Coil: body-based crush/control and defensive stance.
- Cobra — Venom Barrage: aimed/ranged elemental volley and reaction setup.
- Mamba — Thundercoil: dash through targets and chain Electro.

## Element design principle
This uses the Genshin-style idea of elemental auras + reactions, but converts it to snake movement, body contact, melee strikes, aimed shots, and area control rather than character swapping. Bosses can also be primed and reacted for stagger, resistance breaks, damage windows, and Bloom cores.
