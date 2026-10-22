"""Tk canvas vs raylib, same scene, same canvas-style calls.

    python tools/bench/raylib_poc.py raylib            # interactive window, close it or press Esc
    python tools/bench/raylib_poc.py tk
    python tools/bench/raylib_poc.py both --frames 600 --bullets 800     # prints a comparison table
    python tools/bench/raylib_poc.py raylib --frames 120 --shot out.png

The scene mimics a boss fight: 32x20 terrain tiles, a 40-segment snake, bullets (orbs with glow, rice, stars, trails),
rings/arcs and ~40 HUD texts.  Tk rebuilds every item every frame exactly like game/render/* does today.
submit = time spent issuing draw calls from Python; frame = whole frame including the backend actually presenting it.
"""
import argparse
import math
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

W, H, CELL = 960, 600, 30
HUES = ["#ff5d73", "#7df9ff", "#ffd166", "#b388ff", "#6bff95", "#ff9f43"]
STAR = [(0, -1), (0.22, -0.3), (0.95, -0.3), (0.36, 0.12), (0.59, 0.81), (0, 0.38), (-0.59, 0.81), (-0.36, 0.12),
        (-0.95, -0.3), (-0.22, -0.3)]                       # concave 10-point star: stresses polygon filling


def draw_scene(c, t, nb, glow, sprites=None):
    # terrain
    for ty in range(H // CELL):
        for tx in range(W // CELL):
            v = (tx * 7 + ty * 13) % 5
            c.create_rectangle(tx * CELL, ty * CELL, tx * CELL + CELL, ty * CELL + CELL,
                               fill=("#0c1730", "#0e1b38", "#0a142b", "#101f40", "#0d1a34")[v], outline="")
    # snake
    for i in range(40):
        a = t * 2 - i * 0.18
        x, y = W / 2 + math.cos(a) * (180 + i), H / 2 + math.sin(a * 1.3) * (110 + i * 0.5)
        c.create_oval(x - 9, y - 9, x + 9, y + 9, fill="#2fe6a8" if i else "#b9fff0", outline="#06352a", width=2)
    # bullets
    if glow and hasattr(c, "additive"):
        c.additive(True)
        for i in range(nb):
            a = i * 0.37 + t * (0.4 + (i % 7) * 0.05)
            r = 40 + (i * 13 % 260) + 20 * math.sin(t * 2 + i)
            c.glow(W / 2 + math.cos(a) * r * 1.5, H / 2 + math.sin(a) * r * 0.9, 16, HUES[i % 6], 70)
        c.additive(False)
    for i in range(nb):
        a = i * 0.37 + t * (0.4 + (i % 7) * 0.05)
        r = 40 + (i * 13 % 260) + 20 * math.sin(t * 2 + i)
        x, y = W / 2 + math.cos(a) * r * 1.5, H / 2 + math.sin(a) * r * 0.9
        col = HUES[i % 6]
        k = i % 4
        if sprites:                                          # one textured quad per bullet instead of 1-10 primitives
            # game/assets/bullets/orb_18.png and star_18.png are 324x18 strips: 18 cells of 18px, one per hue
            c.draw_sprite(sprites[k], ((i % 18) * 18, 0, 18, 18), (x - 9, y - 9, 18, 18))
        elif k == 0:
            c.create_oval(x - 5, y - 5, x + 5, y + 5, fill=col, outline="#ffffff", width=1)
        elif k == 1:
            c.create_line(x, y, x - math.cos(a) * 14, y - math.sin(a) * 9, fill=col, width=3)   # trail
            c.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#ffffff", outline="")
        elif k == 2:
            c.create_polygon([(x + px * 8, y + py * 8) for px, py in STAR], fill=col, outline="#ffffff")
        else:
            c.create_arc(x - 8, y - 8, x + 8, y + 8, start=int(t * 180 + i * 20) % 360, extent=200, outline=col, width=2,
                         style="arc")
    # rings + translucent panel
    for i in range(12):
        rr = 30 + ((t * 60 + i * 40) % 260)
        c.create_oval(W / 2 - rr, H / 2 - rr, W / 2 + rr, H / 2 + rr, outline=HUES[i % 6], width=1)
    c.create_rectangle(10, 10, 330, 96, fill="#000000", outline="#7df9ff", stipple="gray50")
    # HUD
    for i in range(40):
        c.create_text(20 + (i % 4) * 78, 20 + (i // 4) * 8, text=f"HP {100 - i}", anchor="w", fill="#e8f7ff",
                      font=("Segoe UI", 6, "bold"))
    c.create_text(W // 2, H - 24, text="REPAIR TERMINAL  -  boss: CIRNO", fill="#ffd166", font=("Segoe UI", 14, "bold"))


def run_tk(frames, nb, glow, interactive):
    import tkinter as tk
    root = tk.Tk()
    root.geometry(f"{W}x{H}")
    c = tk.Canvas(root, width=W, height=H, bg="#080e1c", highlightthickness=0)
    c.pack()
    submit = total = 0.0
    n = 0
    t0 = time.perf_counter()
    while (interactive or n < frames):
        f0 = time.perf_counter()
        c.delete("all")
        draw_scene(c, f0 - t0, nb, glow)
        s1 = time.perf_counter()
        try:
            root.update()
        except tk.TclError:
            break
        f1 = time.perf_counter()
        submit += s1 - f0
        total += f1 - f0
        n += 1
    items = len(c.find_all())
    root.destroy()
    return submit / max(n, 1) * 1000, total / max(n, 1) * 1000, items


def run_raylib(frames, nb, glow, interactive, shot=None, window=(W, H), use_sprites=False):
    import pyray as rl
    from game.render.gfx_raylib import RaylibCanvas
    c = RaylibCanvas(window[0], window[1], "Repair Terminal - raylib PoC", vsync=interactive, fps=60)
    sprites = None
    if use_sprites:
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "game", "assets", "bullets")
        names = ["orb_18.png", "star_18.png", "orb_18.png", "star_18.png"]      # the 18px-tall hue strips
        if all(os.path.exists(os.path.join(base, nm)) for nm in names):
            sprites = [c.load_texture(os.path.join(base, nm)) for nm in names]
        else:
            print("(game/assets/bullets not found - running without sprites)")
    submit = total = 0.0
    n = 0
    t0 = time.perf_counter()
    while c.frame_begin():
        f0 = time.perf_counter()
        draw_scene(c, f0 - t0, nb, glow, sprites)
        rl.draw_text(f"{rl.get_fps()} fps  {c.items} draws", W - 190, 8, 18, rl.YELLOW)
        s1 = time.perf_counter()
        c.frame_end()
        f1 = time.perf_counter()
        submit += s1 - f0
        total += f1 - f0
        n += 1
        if shot and n == min(frames, 30):
            rl.take_screenshot(shot)
        if not interactive and n >= frames:
            break
        if rl.is_key_pressed(rl.KeyboardKey.KEY_ESCAPE):
            break
    items = c.items
    c.close()
    return submit / max(n, 1) * 1000, total / max(n, 1) * 1000, items


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("backend", choices=["tk", "raylib", "both"])
    ap.add_argument("--frames", type=int, default=0, help="0 = run until the window is closed")
    ap.add_argument("--bullets", type=int, default=800)
    ap.add_argument("--no-glow", action="store_true")
    ap.add_argument("--sprites", action="store_true", help="raylib only: draw bullets as textures from game/assets/bullets")
    ap.add_argument("--shot", help="save a screenshot (relative file name) after ~30 frames")
    ap.add_argument("--window", default=f"{W}x{H}", help="raylib window size; use 64x64 to measure CPU-side submit cost only")
    a = ap.parse_args()
    interactive = a.frames == 0 and a.backend != "both"
    frames = a.frames or 600
    res = {}
    if a.backend in ("tk", "both"):
        res["tk"] = run_tk(frames, a.bullets, False, interactive)
    if a.backend in ("raylib", "both"):
        res["raylib"] = run_raylib(frames, a.bullets, not a.no_glow, interactive, a.shot, tuple(int(v) for v in a.window.split("x")), a.sprites)
    if not interactive:
        print(f"{a.bullets} bullets, {frames} frames")
        print(f"{'backend':8} {'submit ms':>10} {'frame ms':>10} {'fps':>8} {'items/draws':>12}")
        for k, (s, f, it) in res.items():
            print(f"{k:8} {s:10.2f} {f:10.2f} {1000 / f:8.1f} {it:12d}")
