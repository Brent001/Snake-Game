# Boss VFX + Biome Transition Pass

This pass adds stronger procedural boss presentation and hides biome data swaps behind a staged transition.

## Boss VFX
- Reactive arena borders and center pressure waves.
- Character-specific arena geometry for Cirno, Marisa, Remilia, Flandre and Reimu.
- Multi-ring boss aura, rotating spokes, orbiting motifs and spell charging convergence.
- Phase break / entrance power burst via `boss["power_t"]`.
- Casts trigger a short aura surge without changing the source sprites.

## Biome transitions
- The biome value still changes immediately for gameplay correctness.
- Rendering is masked by a 1.05s pixel fade with a moving energy wipe.
- The new biome announcement is shown during the transition rather than as a standalone popup.
- The old 4-second banner was shortened to prevent repeated popups while crossing borders.

The VFX are canvas primitives and therefore remain compatible with the existing Tkinter + pixel-art renderer.
