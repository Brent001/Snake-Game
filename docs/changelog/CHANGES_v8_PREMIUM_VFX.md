# Repair Terminal V8 — Premium VFX / Show-Off Pass

## What changed

This pass makes combat effects intentionally layered instead of flat:

- Faux bloom built from multiple halo/core passes around attacks and projectiles.
- Element-specific signatures on hits and casts: Electro arcs, Pyro embers, Cryo shards/snow, Hydro droplets, Dendro leaves, Anemo spirals, Geo shards, Abyss void motes, and Light stars.
- Bright-hot cores on player and boss projectiles with multi-pass motion trails.
- Impact bursts with rings, shards, particles, and white-hot cores.
- Critical-hit feedback with stronger hit-stop, flash, shake, and extra particles.
- Boss-hit feedback and spell-cast feedback are substantially stronger.
- Boss spell/phase moments get large burst rings, particles, flash, and camera impact.
- Player damage gets an aggressive impact package instead of only a red flash.
- Enemy deaths now emit layered bursts and rings.
- Existing blast/slash/spit effects were redesigned with multiple depth passes.
- A lightweight particle system was added with caps for performance.
- Camera shake is now a decaying mixed-frequency shake instead of constant random jitter.
- Micro hit-stop was added for heavy/critical impacts.
- Screen flash and a subtle boss cinematic frame were added.

## Rendering approach

The game remains Tkinter/canvas-based. Tkinter does not provide a modern GPU HDR/bloom/post-processing pipeline, so the visual style is approximated with layered vectors, stipple transparency, bright cores, procedural particles, trails, and timed screen/camera effects. This keeps the build compatible with the existing lightweight renderer and older integrated GPUs.

## Performance safety

The premium particle layer is capped and scales with the existing quality adaptation system. Existing boss bullet limits remain in effect.
