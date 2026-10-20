# v41 — Advanced Character-Specific Danmaku AI

- Boss movement speed increased substantially while remaining continuous and bounded.
- Movement destinations are replanned more frequently for lively tactical motion; no teleport snapping.
- Later phases shorten spell-card opening/cooldown windows slightly to raise pressure.
- Added a separate fast character-specific interleave layer that cycles through multiple attack styles per boss.
- Cirno: freeze/release volleys, icicle lanes, radial frozen bursts.
- Marisa: parallel star streams, orrery-style emitters, sweeping laser interludes.
- Remilia: aimed knife-trail bursts, alternating spinning fans, spear lanes.
- Flandre: corner volleys, rainbow split shards, wall-bouncing ripples.
- Reimu: homing amulet volleys, safe-gap barrier rings, crossing seal beams.
- Existing named spell cards and final signature/Last Word attacks are preserved.

Design reference: Taisei separates boss play into normal attacks and unusually hard spell-card patterns; the implementation here uses that rhythm and character motifs while keeping projectile implementations original.
