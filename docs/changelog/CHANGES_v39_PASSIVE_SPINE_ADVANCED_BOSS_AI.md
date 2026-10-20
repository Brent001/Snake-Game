# v39 — Passive Spine Alignment + Advanced Character Boss AI

## Passive tree
- Replaced the independent decorative Bezier S/backbone with a spline generated from the passive tree's actual backbone nodes.
- The creature spine now passes through the same node coordinates used by rendering, panning, zooming, fitting, and hit testing.
- Applied the fix to Viper, Python, Cobra, and Mamba.
- Core is included as a real anchor in the central bend so the visual creature route reads as one connected form.

## Boss AI
- Added bounded tactical movement for all five Touhou-inspired bosses.
- Bosses choose short movement destinations instead of continuously chasing or teleporting to the player.
- Movement speed is capped per frame to prevent snapping; later phases become faster without becoming instantaneous.
- Character movement styles are distinct:
  - Cirno: playful ice-dance lane swaps and altitude changes.
  - Marisa: wide sweeping movement with a small player-lane bias.
  - Remilia: alternating fencing lanes and elegant corner pressure.
  - Flandre: unstable triangular/lemniscate motion.
  - Reimu: measured shrine sweep with modest tracking.
- Added sparse, character-specific aimed interludes layered between authored spell patterns. These are intentionally restrained so difficulty rises through pattern layering rather than bullet spam.
- Existing multi-pattern phase structure and one-time final signature/Last Word attacks are preserved.

## Design reference
Taisei describes Touhou-style STG gameplay as fast-paced and focused on pattern recognition and mastery; this implementation therefore keeps the boss's movement authored/bounded while making danmaku patterns the main source of challenge. See https://github.com/taisei-project/taisei
