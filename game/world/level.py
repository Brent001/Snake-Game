"""Procedural level generation (walls, hazard nodes, pickups, enemy spawns) and the built world."""
import random
from collections import deque

from ..config import GRID_W, GRID_H, WORLD_H
from ..utils import rect
from ..data.biomes import STYLES
from ..data.elements import ELEMS
from ..data.enemies import BIOME_ENEMIES
from .layout import ARENAS, ARENA_ZONE, SAVES, START_SNAKE, arena_walls, compute_biome_fields
from .structures import Builder


def reach_from(start, walls, nodes):
    seen = {start}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n in seen or n in walls or n in nodes:
                continue
            if not (0 <= n[0] < GRID_W and 0 <= n[1] < GRID_H):
                continue
            seen.add(n)
            queue.append(n)
    return seen


OC_BIOME = dict(cryo=0, anemo=0, hydro=1, electro=1, dendro=2, pyro=3, abyss=4, light=5, geo=5)
OCULI_PER_ELEM = 3
PICKUP_COUNTS = (("heal", 225), ("xp", 200), ("stam", 135), ("dmg", 68), ("speed", 68), ("shield", 80),
    ("regen", 68), ("crit", 45), ("elixir", 45), ("ammo", 90), ("emorb", 45))
NODE_COUNT = 4600          # spike hazards scattered over the (2.25x bigger) overworld
ENEMIES_PER_BIOME = 174
CHARGES_PER_BIOME = 30


def build_level():
    fixed = (rect(0, 0, GRID_W - 1, 0) | rect(0, WORLD_H - 1, GRID_W - 1, WORLD_H - 1)
        | rect(0, 0, 0, WORLD_H - 1) | rect(GRID_W - 1, 0, GRID_W - 1, WORLD_H - 1))
    for a in ARENAS:
        fixed |= arena_walls(a)
    bmap, b2map, wmap = compute_biome_fields()           # overworld rows; the dungeon strip below carries its own biome
    for _ in range(WORLD_H, GRID_H):
        bmap.append([0] * GRID_W)
        b2map.append([0] * GRID_W)
        wmap.append([0] * GRID_W)
    for a in ARENAS:
        for x in range(a["x1"] - 4, a["x2"] + 5):
            for y in range(WORLD_H, GRID_H):
                bmap[y][x] = a["biome"]
    keep_clear = rect(1, WORLD_H - 24, 22, WORLD_H - 2)
    for a in ARENAS:                       # open plaza around every overworld portal
        ox, oy = a["ow"]
        keep_clear |= rect(ox - 8, oy - 8, ox + 8, oy + 12)
    save_cells = set()
    for x, y, _dx, _dy in SAVES:
        keep_clear |= rect(x - 2, y - 2, x + 2, y + 3)
        save_cells |= {(x, y), (x, y + 1), (x, y + 2)}
    near_save = set()                      # enemies never spawn within 12 cells of a save point
    for sx, sy, _, _ in SAVES:
        for dy in range(-12, 13):
            span = 12 - abs(dy)
            for dx in range(-span, span + 1):
                near_save.add((sx + dx, sy + dy))

    base = random.randrange(1, 10 ** 6)
    for attempt in range(40):
        rng = random.Random(base + attempt)
        # ---- walls: whole structures (rooms with doorways, rings, ponds, colonnades, mazes ...), never random noise
        builder = Builder(rng, GRID_W, WORLD_H, keep_clear | fixed, bmap, b2map, wmap)
        builder.fill(passes=7, step=6)
        walls = set(fixed) | builder.walls
        door_zone = set()
        for dx, dy in builder.doors:           # hazards never plug a doorway
            door_zone |= {(dx + i, dy + j) for i in (-1, 0, 1) for j in (-1, 0, 1)}

        nodes = set()
        while len(nodes) < NODE_COUNT:
            p = (rng.randint(1, GRID_W - 2), rng.randint(1, WORLD_H - 2))
            if p in walls or p in keep_clear or p in nodes or p in door_zone:
                continue
            nodes.add(p)
            if rng.random() < 0.3:
                q = (p[0] + rng.choice((-1, 1)), p[1])
                if 1 <= q[0] <= GRID_W - 2 and q not in walls and q not in keep_clear and q not in door_zone:
                    nodes.add(q)

        reach = reach_from(START_SNAKE[0], walls, nodes)
        if not all(a["front"] in reach for a in ARENAS) or not all((x, y) in reach for x, y, _, _ in SAVES):
            continue

        free = [p for p in sorted(reach) if p not in ARENA_ZONE and p not in save_cells]
        by_b = {}
        for p in free:
            by_b.setdefault(bmap[p[1]][p[0]], []).append(p)
        taken = set()

        def pick(pool, n):
            pool = [p for p in pool if p not in taken]
            got = rng.sample(pool, min(n, len(pool)))
            taken.update(got)
            return got

        charges = []
        near = [p for p in by_b.get(0, []) if 2 <= p[0] <= 90 and WORLD_H - 66 <= p[1] <= WORLD_H - 4]
        charges += pick(near, 2)
        for b in range(6):
            charges += pick(by_b.get(b, []), CHARGES_PER_BIOME)

        # enemies: 2 species per biome, 10% elites, and 2 named UNIQUE champions per biome
        spawns = []
        for b in range(6):
            pool = [p for p in by_b.get(b, []) if p not in near_save]
            for k, p in enumerate(pick(pool, ENEMIES_PER_BIOME)):
                # inside a transition belt the neighbouring biome's creatures wander over the border too
                src = b2map[p[1]][p[0]] if (wmap[p[1]][p[0]] and rng.random() < wmap[p[1]][p[0]] / 16.0) else b
                t = rng.choice(BIOME_ENEMIES[src])
                elite = 2 if k < 2 else (1 if rng.random() < 0.1 else 0)
                spawns.append((p[0], p[1], t, elite))

        pickups = {}
        allfree = [p for p in free]
        for kind, n in PICKUP_COUNTS:
            for p in pick(allfree, n):
                pickups[p] = kind
        for e in ELEMS:
            for p in pick(by_b.get(OC_BIOME[e], []), OCULI_PER_ELEM):
                pickups[p] = "oc_" + e
        return walls, nodes, sorted(charges), bmap, b2map, wmap, spawns, pickups
    return set(fixed), set(), [(14, WORLD_H - 16)], bmap, b2map, wmap, [], {}


# The world is generated once, at import time, and shared (read-only) by the whole game.
WALLS, NODES, CHARGES, BMAP, B2MAP, WMAP, ENEMY_SPAWNS, PICKUPS = build_level()
SAVE_CELLS = {(x, y): (x, y, dx, dy) for x, y, dx, dy in SAVES}
