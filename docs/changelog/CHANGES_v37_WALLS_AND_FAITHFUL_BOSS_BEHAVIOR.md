# v37 — Stable walls + faithful Touhou-style boss behavior

- Restored the known-stable wall/terrain/world-generation modules from the v25 baseline.
- Removed the v36 direct-attack/chase AI that could make the boss run or snap around the arena.
- Removed continuous pressure firing from the per-frame boss loop; authored normal/spell patterns now carry the combat.
- Baseline boss movement is upper-field, smooth, bounded sway instead of tracking the player every frame.
- Character-specific movement inside authored patterns (e.g. Marisa dash / Remilia warp) remains available where it is part of a spell.
- Kept the finite boss food/pulse supply and portal transition FX from later versions.
- Kept the v36 UI, settings, credits, skill/passive trees, and pixel HUD.

Design reference: Taisei's manual describes normal attacks and Spell Cards as timed boss attacks, with Spell Cards being concentrated, unusual danmaku patterns; this version keeps that rhythm instead of making bosses behave like chasing action-game enemies.
