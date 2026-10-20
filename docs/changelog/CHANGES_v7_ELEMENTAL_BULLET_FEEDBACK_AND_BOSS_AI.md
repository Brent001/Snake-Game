# Repair Terminal v7 — Elemental Combat Feedback & Aggressive Touhou-Style Bosses

## Elemental system

The Genshin-inspired elemental system remains active for the player and bosses:
Pyro/Hydro Vaporize, Pyro/Cryo Melt, Hydro/Cryo Freeze, Pyro/Electro Overload,
Hydro/Electro Electro-Charged, Cryo/Electro Superconduct, Dendro/Pyro Burning,
Dendro/Hydro Bloom, Dendro/Electro Quicken -> Spread/Aggravate, Anemo Swirl,
Geo Crystallize, and Abyss/Light Eclipse.

Every ranged bolt now visibly carries the selected element and uses distinct motion/readability cues.
Elemental hits produce contact VFX, status labels, aura rings, and larger reaction bursts.
Boss hits use the same reaction system and now show elemental/reaction feedback.

## Player attack feedback

- Player bolts have elongated trails and element-specific projectile accents.
- Elemental contact creates an impact ring/particles at the target.
- Reactions create a larger named burst (e.g. OVERLOAD, VAPORIZE, QUicken/AGGRAVATE).
- Enemy elemental auras are shown as animated rings instead of only a small dot.
- Boss elemental hits use dedicated flash/ring feedback.

## Boss encounter redesign

The guardian movement now deliberately biases toward the player's current lane instead of following a passive center-only orbit.
As HP falls, bosses become more aggressive and launch short aimed pressure clusters more frequently.
The pressure pattern also occasionally leads the player's movement, creating an intercept that rewards routing instead of standing still.

Generic arena hazards are now secondary and significantly less frequent; the character-specific danmaku/signature patterns are the primary threat.

Each boss retains character-specific signature attacks and spell-card names, while the new pressure layer acts like a non-spell baseline attack.

The presentation follows classic Touhou boss encounter ideas: repeated normal pressure, named spell-card phases,
readable attack cadence, deliberate gaps/routing, increasingly dense patterns, and a clear cast/break moment.

## Performance

MAX_BULLETS was reduced from 380 to 300 while adding lightweight bullet trails and bounded VFX,
so the denser visuals do not grow without limit on low-end hardware.
