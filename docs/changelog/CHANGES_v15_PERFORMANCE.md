# v15 - performance + leak pass

Measured headless (Tk under Xvfb), same scenario before/after: ~40% less CPU time per frame when calm,
~45% less during combat; canvas items per frame 252 -> 171.

## Leaks / unbounded growth
- `reset_game()` (every NEW GAME) created a new GPU overlay object -> a new OpenGL thread + window each run that was never
  stopped. The overlay is now created once per process.
- Food spawned around the player was never removed; far-away food is now despawned.
- Terrain chunk cache cap now follows the window size (was a fixed 120 chunks ~ 110 MB; fullscreen thrashed it).
- Removed a PhotoImage allocated and thrown away on every boss-sprite cache miss.

## Speed
- `main.py`: Windows timer resolution 15.6 ms -> 1 ms (`timeBeginPeriod`), above-normal priority, `gc.freeze()` after
  world generation + larger GC thresholds. Without this Tk's `after(16)` fired every 15.6/31 ms.
- Enemy loops (update + draw) walk a ~4 Hz "active enemies" list instead of all ~1000 enemies every frame.
- Enemy animation sheets: no `Path.resolve()` / `exists()` per enemy per frame.
- Baked pixel-shadow sprites replace stippled polygons/rectangles (3-4 items -> 1 per entity).
- CPU particle glow baked into a cached sprite (10 items -> 1 per particle).
- GPU overlay: no per-frame dict copies, window only moved when it actually moved, and no snapshot is built at all
  when the overlay is not running.
- Vignette image reused between frames.
