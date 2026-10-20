# GPU rendering pipeline

Repair Terminal now has an optional **GPU VFX compositor**. The current game keeps Tkinter for the mature HUD, menus, skill tree and compatibility layer, but expensive combat effects are rendered in a transparent OpenGL overlay. This is the safe first step toward a complete renderer port.

## Architecture

```text
Game simulation / elemental reactions
            |
            v
     CPU VFX event state
            |
            v
  world -> canvas-space snapshot
            |
            v
   ModernGL instanced particles
            |
            v
      HDR-ish effect FBO
            |
            v
 horizontal Gaussian blur
            |
            v
   vertical Gaussian blur
            |
            v
 transparent overlay composite
```

The overlay uses a pyglet `WINDOW_STYLE_OVERLAY` window, which is designed for transparent, topmost, click-through rendering, and a ModernGL 3.3 context. ModernGL can attach to a windowing library's current OpenGL context, including pyglet.

## Enable

```powershell
pip install -r requirements-gpu.txt
python main.py --gpu
```

Normal `python main.py` will auto-use GPU VFX when the optional packages are available. Force the old renderer with:

```powershell
python main.py --cpu
```

## What moves to the GPU

Particles, radial glow, impact rings, screen-flash compositing and the bloom blur are GPU-rasterised. The existing game state, collision, elemental reaction logic, skill tree and boss AI remain unchanged. If the GPU stack fails to initialize, the game automatically falls back to the existing Tk VFX implementation instead of refusing to start.

## Full-renderer roadmap

The next architectural step would be to port scenery, sprites, terrain chunks, bullets and HUD to GPU texture atlases and batched draw calls, leaving Tk only as an optional editor/debug UI. That is a much larger renderer migration; the current VFX compositor deliberately avoids breaking the working gameplay layer.
