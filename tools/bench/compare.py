"""Headless benchmark: counts canvas items per frame (the real cost driver in Tk) without needing a display.

    python tools/bench/compare.py            # run from the repo root
The bundled tkinter.py is a stub that is ONLY put on the path by this script - it never affects the real game.
"""
import os, sys, time, random
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(1, ROOT)
import tkinter as tk
clock = [0.0]
time.perf_counter = lambda: clock[0]
from game.app import SnakeTerminal
from game.world.level import WALLS

random.seed(2)
g = SnakeTerminal(tk.Tk())


def measure(label, n=180):
    tk.STATS.clear()
    t0 = time.process_time()
    for _ in range(n):
        clock[0] += 1 / 60
        g.animate()
    el = time.process_time() - t0
    items = sum(v for k, v in tk.STATS.items() if k in ("rect", "oval", "line", "poly", "text", "arc", "image"))
    print(f"{label:34s} {items / n:6.0f} items/frame  {el / n * 1000:5.2f} ms python/frame")


for st in ("menu", "classes", "controls"):
    g.state = st
    measure("menu screen: " + st, 60)
g.menu_activate("new")
g.state = "playing"
g.invincible = 1e9
measure("warm", 40)
measure("gameplay, start area")
x, y = 190, 130
while (x, y) in WALLS:
    x += 1
g.snake = [(x - i, y) for i in range(60)]
g.prev = list(g.snake)
g.update_camera(0, instant=True)
measure("gameplay, 60-segment snake")
g.state = "tree"
measure("skill tree screen", 60)
