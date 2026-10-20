"""Fixed world layout: spawn point, biome centres, boss arenas, save points and biome noise."""
import math

from ..config import ARENA_H, ARENA_TOP, ARENA_W, BLEND_BAND, GRID_W, WORLD_H
from ..utils import rect

START_SNAKE = [(10, WORLD_H - 14), (10, WORLD_H - 13), (10, WORLD_H - 12)]
# biome centers (the world is 1.5x wider and taller than the previous build, so every border has room for a transition belt)
CENTERS = [(77, 333), (90, 77), (486, 77), (500, 315), (288, 329), (288, 189)]


def make_arena(i):
    """Boss dungeon i.  The room itself lives in a separate strip below the overworld (rows >= ARENA_TOP); in the
    overworld there is only a portal (a['portal']) on the old arena site (a['ow']).  Walking into the portal teleports
    the snake to a['entry'] inside the dungeon; the dungeon's exit door (a['door']) teleports it back to a['front']."""
    acx, acy = CENTERS[i + 1]
    x1 = 10 + i * 64
    x2, y1, y2 = x1 + ARENA_W - 1, ARENA_TOP, ARENA_TOP + ARENA_H - 1
    cx = (x1 + x2) // 2
    return dict(x1=x1, x2=x2, y1=y1, y2=y2, cx=cx, mx=(x1 + x2) / 2, my=(y1 + y2) / 2,
        door={(cx + d, y2 + 1) for d in range(-2, 3)}, entry=(cx, y2 - 3),
        ow=(acx, acy), portal={(acx + dx, acy + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)}, front=(acx, acy + 4),
        biome=i + 1, final=(i == 4))


ARENAS = [make_arena(i) for i in range(5)]
CORE = (ARENAS[4]["cx"], (ARENAS[4]["y1"] + ARENAS[4]["y2"]) // 2)
ARENA_ZONE = set()            # cells that enemies / food / decor must avoid: the dungeons and the portal plazas
for _a in ARENAS:
    ARENA_ZONE |= rect(_a["x1"] - 1, _a["y1"] - 1, _a["x2"] + 1, _a["y2"] + 1)
    ARENA_ZONE |= rect(_a["ow"][0] - 6, _a["ow"][1] - 6, _a["ow"][0] + 6, _a["ow"][1] + 6)
PORTAL_CELLS = {c: i for i, _a in enumerate(ARENAS) for c in _a["portal"]}


def arena_at(x, y):
    """Index of the dungeon whose room contains (x, y), else None (overworld)."""
    if y < WORLD_H:
        return None
    for i, a in enumerate(ARENAS):
        if a["x1"] - 4 <= x <= a["x2"] + 4:
            return i
    return None


def save_spots():
    spots = [START_SNAKE[0]]
    spots += [(a["ow"][0], a["ow"][1] + 9) for a in ARENAS]
    for cx, cy in CENTERS:
        spots.append((min(GRID_W - 8, max(8, cx + 26)), min(WORLD_H - 8, max(8, cy - 18))))
    # extra save points scattered across the bigger world
    spots += [(82, 204), (288, 77), (492, 195), (393, 321), (288, 258), (180, 180), (390, 150), (180, 300), (435, 240),
        (190, 70), (390, 60), (130, 270), (440, 150), (60, 150), (330, 220)]
    return [(x, y, 0, -1) for x, y in spots]


SAVES = save_spots()


def arena_walls(a):
    w = (rect(a["x1"] - 1, a["y1"] - 1, a["x2"] + 1, a["y1"] - 1) | rect(a["x1"] - 1, a["y1"] - 1, a["x1"] - 1, a["y2"] + 1)
        | rect(a["x2"] + 1, a["y1"] - 1, a["x2"] + 1, a["y2"] + 1) | rect(a["x1"] - 1, a["y2"] + 1, a["x2"] + 1, a["y2"] + 1))
    return w - a["door"]


def _warp_tables():
    """Domain-warp offsets: the border between two biomes wanders instead of being a straight line."""
    ax = [16 * math.sin(y * 0.045 + 1.3) + 7 * math.sin(y * 0.13) for y in range(WORLD_H + 2)]     # x offset, depends on y
    by = [16 * math.sin(x * 0.040 + 0.4) + 7 * math.sin(x * 0.12) for x in range(GRID_W + 2)]      # y offset, depends on x
    return ax, by


def compute_biome_fields():
    """Per-cell biome data for the overworld, built once.

      BMAP[y][x]   primary biome (nearest centre) - drives palette, enemies, music, ambience
      B2MAP[y][x]  the neighbouring biome that bleeds into this cell
      WMAP[y][x]   how strongly it bleeds, 0..8 (8 = 50 %: exactly on the border, where both sides look identical)

    The belt is BLEND_BAND cells wide.  It is evaluated on a 2x2 grid and replicated (the result is dithered anyway).
    """
    ax, by = _warp_tables()
    W, H = GRID_W, WORLD_H
    bmap = [[0] * W for _ in range(H)]
    b2map = [[0] * W for _ in range(H)]
    wmap = [[0] * W for _ in range(H)]
    cxs = [c[0] for c in CENTERS]
    cys = [c[1] for c in CENTERS]
    n = len(CENTERS)
    inv = 8.0 / BLEND_BAND                     # w (0..8) = 8 * 0.5*(1 - m/BAND)*2 -> see below
    sqrt = math.sqrt
    for y in range(0, H, 2):
        a = ax[y]
        rb, r2, rw = bmap[y], b2map[y], wmap[y]
        for x in range(0, W, 2):
            wx = x + a
            wy = y + by[x]
            d1 = d2 = 1e18
            i1 = i2 = 0
            for i in range(n):
                dx = wx - cxs[i]
                dy = wy - cys[i]
                d = dx * dx + dy * dy
                if d < d1:
                    d2, i2 = d1, i1
                    d1, i1 = d, i
                elif d < d2:
                    d2, i2 = d, i
            m = sqrt(d2) - sqrt(d1)            # 0 on the border, grows with the distance from it
            w = int(8 - m * inv * 0.5 * 2) if m < BLEND_BAND else 0
            if w < 0:
                w = 0
            rb[x] = i1
            r2[x] = i2
            rw[x] = w
        for x in range(1, W, 2):               # replicate to the odd columns
            rb[x], r2[x], rw[x] = rb[x - 1], r2[x - 1], rw[x - 1]
    for y in range(1, H, 2):                   # ...and to the odd rows
        bmap[y][:], b2map[y][:], wmap[y][:] = bmap[y - 1], b2map[y - 1], wmap[y - 1]
    return bmap, b2map, wmap


def biome_at(x, y):
    wx = x + 16 * math.sin(y * 0.045 + 1.3) + 7 * math.sin(y * 0.13)
    wy = y + 16 * math.sin(x * 0.040 + 0.4) + 7 * math.sin(x * 0.12)
    best, bd = 0, 1e18
    for i, (cx, cy) in enumerate(CENTERS):
        d = (wx - cx) ** 2 + (wy - cy) ** 2
        if d < bd:
            best, bd = i, d
    return best
