# v16 - smooth day/night cycle + GPU overlay shutdown fix

## 1. pyglet `MissingFunctionException: glDeleteBuffers / glDeleteProgram` on exit
Cause: `close_game()` only *flagged* the GPU thread to stop and the process exited straight away. pyglet's `BufferObject`
and `ShaderProgram` finalizers (`__del__`) then ran after the OpenGL context was gone, `wglGetProcAddress` could not
resolve `glDeleteBuffers` / `glDeleteProgram`, and pyglet only swallows `AttributeError` / `ImportError` there.
(`gc.freeze()` in main.py makes that late collection certain.) It was harmless noise, not a driver problem.

Fix (`game/render/gpu_pipeline.py`):
- `stop()` now joins the GL thread; it is also registered with `atexit`.
- New `_teardown()` runs on the GL thread with the context current: releases every ModernGL object, `gc.collect()`s,
  then closes the window.
- `_harden_pyglet_finalizers()` makes the pyglet `__del__` methods ignore a failing delete as a last line of defence.

## 2. Smooth day / night cycle with sunrise and sunset
- **Time model** (`app.py: sun_state`): sun elevation drives everything. Daylight is a smoothstep of elevation, so dawn
  and dusk are long gentle ramps (the old clamped sine was flat most of the day and hard-switched between two sky images).
- `DAY_LEN` 150 -> 240 s. `DAY_START = 0.04` starts a run just after sunrise (0 sunrise, .25 noon, .5 sunset, .75 midnight).
- **Sky** (`world_scene.draw_dynamic_sky`): a live gradient (night ramp -> day ramp, warmed with rose/gold at sunrise and
  red/amber at sunset), a **sun** and **moon** travelling along an arc and rising out from behind the silhouettes, a
  dithered horizon glow under the sun, and stars that fade in one by one as the sky darkens.
- Silhouettes (mountains, mansion, ridge...) are baked for 5 light levels (pre-baked while a menu is open); they are
  transparent above the skyline, so nothing pops when the sky changes.
- Terrain chunk light steps 5 -> 9, re-bake budget 2 -> 3 chunks/frame.
- **Colour wash** (`draw_grade`): one stippled rectangle - warm at sunrise/sunset, faint deep blue at night.
  Windows/X11 only (macOS Tk ignores stipple). Disable with `DAY_GRADE_STIPPLE = False` in `config.py`.
- HUD clock: SUNRISE / DAWN / DAY / NOON / SUNSET / DUSK / NIGHT / MIDNIGHT with a sun or moon icon.
- The Frost Moon stays in eternal night with its original baked sky.

Tuning: `DAY_LEN`, `DAY_START`, `DAY_GRADE_STIPPLE` in `game/config.py`; sunrise/sunset colours are `TW_RISE` / `TW_SET`
in `game/render/scenery.py`.
