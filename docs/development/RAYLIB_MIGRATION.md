# Moving Repair Terminal from Tkinter to raylib

This kit is a **drop-in drawing layer**, a benchmark, and a plan.  Nothing in your game logic has to change.

## Files

| File | What it is |
|---|---|
| `game/render/gfx_raylib.py` | `RaylibCanvas`: a `tk.Canvas` look-alike (create_rectangle / oval / line / polygon / arc / text / image) drawing through raylib on the GPU. Also `additive()`, `glow()`, `draw_sprite()` for things Tk cannot do. |
| `tools/bench/raylib_poc.py` | Same boss-fight-like scene on Tk and on raylib. |

Install: `pip install raylib` (provides the `raylib` and `pyray` modules; tested with raylib 6.0.1).

## Why this fits your code

Your render code only uses the *drawing* half of `tk.Canvas`. Counts across `game/`:
`coords()` 0, `itemconfig()` 0, `move()` 1, `tag_raise()` 1, `find_*` 4, `bind()` 15, `PhotoImage()` 20.
Because you rebuild the frame from scratch every tick, you already work in immediate mode, which is what raylib is.
The retained-mode features that are missing from the shim are the ones you barely use.

## Measured (sandbox, 800 bullets, 1734 items/frame)

The sandbox has **no GPU** (software OpenGL under Xvfb), so frame times for raylib are not meaningful here; Python-side
submit time is. Run `python tools/bench/raylib_poc.py both --frames 600` on your own machine for real numbers.

| Scene | Python submit per frame |
|---|---|
| Tk canvas, items rebuilt every frame (today) | 15.4 ms (+ Tk's own rendering on top) |
| raylib, 1:1 port of the same primitives | 16.3 ms |
| raylib, bullets as atlas sprites (`draw_sprite`) | 5.1 ms |

Take-aways:

1. **A literal port moves the rendering to the GPU but does not shrink the Python-side cost.** Every primitive is still one
   Python call (about 1-10 us each).  The win of the literal port is that Tk's own work (item creation in Tcl, GDI
   rasterisation on Windows, `after()` timer jitter) disappears and there is no second overlay window.
2. **The big CPU win comes from drawing fewer, bigger things.** Replacing a bullet's polygon + outline + trail with one
   textured quad cut submit time about 3x.  You already ship hue/rotation atlases in `game/assets/bullets/`.
3. Python cost per call matters: `pyray`'s convenience functions allocate a struct per argument and were 5-8x slower than
   calling the low-level `raylib` module with reused structs, which is what `gfx_raylib.py` does.

## Migration plan

1. **Swap the canvas.** In `app.py` create `RaylibCanvas(960, 600)` instead of `FastCanvas`, and turn `animate()` into
   `while c.frame_begin(): update(dt); draw(); c.frame_end()`.  Replace `c.delete("all")` calls (they are no-ops).
2. **Port `PhotoImage` code** (`pixelart.py`, `sprites.py`, the 20 call sites). Load PNGs with `c.load_texture()`;
   for procedurally generated pixel art build an `Image` with raylib or Pillow, then upload it once as a texture.
3. **Port input.** Replace the 15 `bind()` calls with polling: `lib.IsKeyDown`, `lib.IsKeyPressed`, `lib.GetMouseX/Y`,
   `lib.IsMouseButtonDown`, `lib.GetMouseWheelMove`.
4. **Hot paths to sprites/instancing, biggest first:** bullets, then particles/rings (your existing ModernGL shaders in
   `gpu_pipeline.py` can be reused inside raylib's render loop), then terrain tiles (draw once to a `RenderTexture`).
5. **Audio.** raylib has `LoadMusicStream` / `LoadSound`, which replaces the pygame / MCI / afplay fallback chain.
6. **Delete** the overlay thread in `gpu_pipeline.py` and the Windows timer hack in `main.py` (`timeBeginPeriod`); raylib
   uses vsync / `SetTargetFPS`.

## Known gaps in the shim

* `dash`, `capstyle`, `smooth` are ignored; `stipple` becomes alpha (gray50 = 50 %).
* Text uses Segoe UI (Windows) or DejaVu Sans (Linux) if found, otherwise raylib's default font; ASCII glyphs only.
  Load a font with a wider codepoint list if you need other scripts.
* Filled polygons are triangulated in Python (cached by shape); very large animated concave polygons should become sprites.
* Triangles must be wound counter-clockwise on screen or raylib culls them; the shim handles this for you.
