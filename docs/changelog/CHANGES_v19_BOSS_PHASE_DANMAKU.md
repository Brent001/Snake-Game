# v19 - Boss phase pattern rework + character Last Words

## Goal

Boss fights now have a clear difficulty ramp. Every life/phase introduces a new pattern
rather than only increasing HP or bullet count. Final phases gain a **one-time Last Word**
at 55% HP so the signature attack feels like a climax without making the entire phase
Lunatic-level from the start.

## Boss progression

| Boss | Early phase | Middle phase | Final phase / climax |
|---|---|---|---|
| Cirno | Icicle Fall + Frostblade Fan | Diamond Blizzard + Crystal Prism | Frozen Starfall + **ULTIMATE: Absolute Zero** |
| Marisa | Stardust Wheel | Orrery Crossfire | Meteoric Streak + **FINAL MASTER SPARK** |
| Remilia | Scarlet Fan | Fate Chain | Red the Nightless Castle + **LAST WORD: Scarlet Destiny** |
| Flandre | Crumbling Edge | Clone Prism | Rainbow Sawtooth → Clockwork Prism + **Q.E.D.: 495 Years of Destruction** |
| Reimu | Ofuda Spiral | Barrier Shuffle → Binding Cross | Yin-Yang Maze + **LAST WORD: Dream of Hakurei** |

## Difficulty philosophy

- Phase bullet speed receives only a small global phase ramp.
- Individual patterns become more complex through movement requirements, delayed shots,
  orbiting emitters, gaps, redirects, bouncing bullets and controlled beams.
- Every new dangerous attack has a visible telegraph or predictable rhythm.
- Last Words are one-time events at roughly 55% of the final phase HP.
- The existing player damage grace period remains in place, so a mistake is punishing
  but does not chain-stunlock the player.

## Character inspiration

The design uses Touhou's established spell-card language as inspiration:
Cirno's ice/falling-shard patterns; Marisa's stars, orbiting Orrery-style familiars and
large laser attacks; Remilia's spear/knife/blood and vampire-drain identity; Flandre's
copies, rainbow arcs and increasingly destructive geometry; and Reimu's ofuda, barriers,
Yin-Yang Orbs and Innate Dream.

## Open-source research

Gameplay structure was cross-checked against:

- **Taisei Project** (MIT-licensed open-source Touhou fangame): its manual describes
  normal attacks as a lower-pressure break between unusual spell-card patterns, and
  spell cards as the boss's concentrated, unusual attack phases.
- **Touhou Pixel Dungeon: Reloaded** (GPL): its boss implementations were used only as
  inspiration for telegraphed charge/release attacks, short cooldown windows and
  character-specific effects. No source code or assets from that repository were copied
  into this project.

The actual pattern implementations in this game are original Python/tkinter gameplay code.
