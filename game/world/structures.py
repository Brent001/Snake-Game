"""Structured wall generation.

The old generator dropped thousands of random 1-wide lines and 2x3 blobs, which read as noise.  This one places whole
*structures* - walled rooms with real doorways, crater rings, ponds, colonnades, hedge mazes, torii avenues, ruins - each
with a footprint, a clear margin around it and openings that are always wide enough for the snake.  Which structures
appear depends on the biome (see TABLES), and inside a transition belt both neighbouring biomes contribute, so a
border between the Forest and the Scarlet Mansion really does grow hedge-rooms out of the groves.

Everything is pure Python and deterministic for a given random.Random.
"""
import math

GAP = 3          # width of every doorway / opening (the head is 1 cell wide, but the body needs room to turn)
PAD = 3          # free cells kept around every structure


# ------------------------------------------------------------------------------------------ small helpers
def _box(x, y, w, h):
    return {(i, j) for i in range(x, x + w) for j in range(y, y + h)}


def _outline(x, y, w, h, t=1):
    cells = set()
    for k in range(t):
        for i in range(x + k, x + w - k):
            cells.add((i, y + k))
            cells.add((i, y + h - 1 - k))
        for j in range(y + k, y + h - k):
            cells.add((x + k, j))
            cells.add((x + w - 1 - k, j))
    return cells


def _cut(cells, doors, side, x, y, w, h, t, rng, gw=GAP, at=None):
    """Open a doorway of width gw in the given side (0 N, 1 E, 2 S, 3 W) of an outlined box."""
    if side in (0, 2):
        lo, hi = x + 2, x + w - 2 - gw
        if hi < lo:
            return
        g = at if at is not None else rng.randint(lo, hi)
        for i in range(g, g + gw):
            for k in range(t):
                c = (i, y + k) if side == 0 else (i, y + h - 1 - k)
                cells.discard(c)
                doors.add(c)
    else:
        lo, hi = y + 2, y + h - 2 - gw
        if hi < lo:
            return
        g = at if at is not None else rng.randint(lo, hi)
        for j in range(g, g + gw):
            for k in range(t):
                c = (x + k, j) if side == 3 else (x + w - 1 - k, j)
                cells.discard(c)
                doors.add(c)


# ------------------------------------------------------------------------------------------ structures
# every builder returns (cells, doors, w, h) with cells expressed in absolute coordinates for the top-left (x, y)
def room(rng, x, y, style="plain"):
    """A walled room with 1-3 doorways, optional corner towers and an inner partition (Scarlet Mansion) or a gate (shrine)."""
    w, h = rng.randint(13, 24), rng.randint(10, 18)
    t = 2 if (style == "mansion" and rng.random() < 0.5) else 1
    cells, doors = _outline(x, y, w, h, t), set()
    n = rng.choice((1, 2, 2, 3))
    sides = rng.sample((0, 1, 2, 3), n)
    for s in sides:
        _cut(cells, doors, s, x, y, w, h, t, rng)
    if style == "mansion":
        for cx, cy in ((x, y), (x + w - 3, y), (x, y + h - 3), (x + w - 3, y + h - 3)):      # corner towers
            cells |= _box(cx, cy, 3, 3)
        if w >= 18 and rng.random() < 0.7:                                                 # inner partition with a door
            px = x + w // 2
            part = {(px, j) for j in range(y + t, y + h - t)}
            mid = rng.randint(y + 3, y + h - 3 - GAP)
            for j in range(mid, mid + GAP):
                part.discard((px, j))
            cells |= part
    elif style == "shrine":
        cells = _outline(x, y, w, h, 1)                                                    # courtyard: one wide torii gate
        doors = set()
        s = rng.choice((0, 2))
        _cut(cells, doors, s, x, y, w, h, 1, rng, gw=5, at=x + w // 2 - 2)
        gx = x + w // 2
        gy = y if s == 0 else y + h - 1
        for dx in (-3, 2):                                                                 # gate posts
            cells |= _box(gx + dx, gy - 1 if s == 0 else gy, 1, 2)
        for i in range(x + 3, x + w - 3, 4):                                               # lanterns inside
            cells.add((i, y + 3))
            cells.add((i, y + h - 4))
    return cells, doors, w, h


def ruin(rng, x, y):
    """A broken-down room: long aligned stretches of wall are missing, rubble lies around it."""
    w, h = rng.randint(12, 22), rng.randint(9, 16)
    cells, doors = _outline(x, y, w, h, 1), set()
    for s in rng.sample((0, 1, 2, 3), rng.choice((1, 2))):
        _cut(cells, doors, s, x, y, w, h, 1, rng)
    for _ in range(rng.randint(2, 4)):                                                       # collapsed stretches
        if rng.random() < 0.5:
            sx, sy, l = rng.randint(x + 1, x + w - 6), rng.choice((y, y + h - 1)), rng.randint(3, 6)
            for i in range(sx, sx + l):
                cells.discard((i, sy))
                doors.add((i, sy))
        else:
            sx, sy, l = rng.choice((x, x + w - 1)), rng.randint(y + 1, y + h - 6), rng.randint(3, 6)
            for j in range(sy, sy + l):
                cells.discard((sx, j))
                doors.add((sx, j))
    for _ in range(rng.randint(3, 6)):                                                       # rubble pillars
        cells.add((rng.randint(x + 2, x + w - 3), rng.randint(y + 2, y + h - 3)))
    return cells, doors, w, h


def ring(rng, x, y, r=None, centre=True):
    """A crater / fairy ring: a circular wall with 2-3 wide openings and (sometimes) a stone at the middle."""
    r = r or rng.randint(6, 10)
    d = 2 * r + 1
    cx, cy = x + r, y + r
    cells, doors = set(), set()
    gaps = [rng.uniform(0, 2 * math.pi) for _ in range(rng.choice((2, 3)))]
    half = GAP / (2 * r) * 1.15
    for i in range(x, x + d):
        for j in range(y, y + d):
            dist = math.hypot(i - cx, j - cy)
            if r - 1.0 <= dist <= r + 0.35:
                a = math.atan2(j - cy, i - cx)
                if any(abs((a - g + math.pi) % (2 * math.pi) - math.pi) < half for g in gaps):
                    doors.add((i, j))
                else:
                    cells.add((i, j))
    if centre:
        cells |= _box(cx - 1, cy - 1, 2, 2)
    return cells, doors, d, d


def blob(rng, x, y, r=None, squash=1.0):
    """Organic rock / grove / pond made with a cellular automaton, so edges are rounded and smooth."""
    r = r or rng.randint(3, 7)
    rx, ry = r, max(2, int(r * squash))
    w, h = 2 * rx + 3, 2 * ry + 3
    cx, cy = rx + 1, ry + 1
    g = [[False] * w for _ in range(h)]
    for j in range(h):
        for i in range(w):
            d = math.hypot((i - cx) / rx, (j - cy) / ry)
            g[j][i] = d < 0.55 or (d < 1.0 and rng.random() < 0.72 - 0.35 * d)
    for _ in range(3):                                                                       # smoothing passes
        n = [[False] * w for _ in range(h)]
        for j in range(1, h - 1):
            for i in range(1, w - 1):
                c = sum(g[j + b][i + a] for a in (-1, 0, 1) for b in (-1, 0, 1))
                n[j][i] = c >= 5
        g = n
    # keep only the biggest connected piece
    seen, best = set(), []
    for j in range(h):
        for i in range(w):
            if g[j][i] and (i, j) not in seen:
                comp, stack = [], [(i, j)]
                seen.add((i, j))
                while stack:
                    a, b = stack.pop()
                    comp.append((a, b))
                    for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        q = (a + da, b + db)
                        if 0 <= q[0] < w and 0 <= q[1] < h and g[q[1]][q[0]] and q not in seen:
                            seen.add(q)
                            stack.append(q)
                if len(comp) > len(best):
                    best = comp
    return {(x + a, y + b) for a, b in best}, set(), w, h


def colonnade(rng, x, y, style="pillar"):
    """Two rows of pillars along a lane (a temple avenue).  'lantern' = 1x1 stone lanterns, 'pillar' = 2x2 columns."""
    horiz = rng.random() < 0.5
    n = rng.randint(5, 9)
    sp = rng.choice((4, 5))
    lane = rng.choice((4, 5))
    size = 1 if style == "lantern" else 2
    length = n * sp
    cells = set()
    for k in range(n):
        o = k * sp
        if horiz:
            cells |= _box(x + o, y, size, size) | _box(x + o, y + lane + size, size, size)
        else:
            cells |= _box(x, y + o, size, size) | _box(x + lane + size, y + o, size, size)
    w, h = (length, lane + 2 * size) if horiz else (lane + 2 * size, length)
    return cells, set(), w, h


def torii_avenue(rng, x, y):
    """A shrine approach: lanterns down both sides and a big gate (two thick posts) at the entrance."""
    cells, doors, w, h = colonnade(rng, x, y, "lantern")
    horiz = w > h
    lane = (h if horiz else w) - 2
    if horiz:
        cells |= _box(x - 2, y - 1, 2, 3) | _box(x - 2, y + lane, 2, 3)
        w += 2
        x0, y0 = x - 2, y - 1
    else:
        cells |= _box(x - 1, y - 2, 3, 2) | _box(x + lane, y - 2, 3, 2)
        h += 2
        x0, y0 = x - 1, y - 2
    return cells, doors, w + 1, h + 1


def wall_line(rng, x, y, thick=1, gap_every=11):
    """A long straight wall (hedge row / fence / quay) broken by regular openings and capped by blocks."""
    horiz = rng.random() < 0.5
    length = rng.randint(14, 30)
    gaps, k = set(), rng.randint(4, gap_every)
    while k + GAP < length - 3:
        gaps.update(range(k, k + GAP))
        k += gap_every + GAP
    cells, doors = set(), set()
    for k in range(length):
        for t in range(thick):
            c = (x + k, y + t) if horiz else (x + t, y + k)
            (doors if k in gaps else cells).add(c)
    cap = thick + 2
    if horiz:
        cells |= _box(x - 1, y - 1, 3, cap) | _box(x + length - 2, y - 1, 3, cap)
    else:
        cells |= _box(x - 1, y - 1, cap, 3) | _box(x - 1, y + length - 2, cap, 3)
    return cells, doors, length, cap


def maze(rng, x, y):
    """A small hedge maze: 2-wide passages between 1-wide hedges, with two entrances."""
    nx, ny = rng.randint(4, 6), rng.randint(4, 5)
    w, h = nx * 3 + 1, ny * 3 + 1
    cells = _box(x, y, w, h)
    doors = set()

    def carve(i, j):
        for a in (0, 1):
            for b in (0, 1):
                cells.discard((x + 1 + 3 * i + a, y + 1 + 3 * j + b))

    seen = {(0, 0)}
    stack = [(0, 0)]
    carve(0, 0)
    while stack:
        i, j = stack[-1]
        opts = [(i + a, j + b) for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))
                if 0 <= i + a < nx and 0 <= j + b < ny and (i + a, j + b) not in seen]
        if not opts:
            stack.pop()
            continue
        ni, nj = rng.choice(opts)
        seen.add((ni, nj))
        carve(ni, nj)
        for q in (0, 1):                       # open the 2-wide connector between the two cells
            if ni != i:
                cells.discard((x + 1 + 3 * min(i, ni) + 2, y + 1 + 3 * j + q))
            else:
                cells.discard((x + 1 + 3 * i + q, y + 1 + 3 * min(j, nj) + 2))
        stack.append((ni, nj))
    for _ in range(2):                         # entrances (2 wide, into a corridor cell)
        if rng.random() < 0.5:
            j = rng.randrange(ny)
            xx = x if rng.random() < 0.5 else x + w - 1
            for b in (0, 1):
                cells.discard((xx, y + 1 + 3 * j + b))
                doors.add((xx, y + 1 + 3 * j + b))
        else:
            i = rng.randrange(nx)
            yy = y if rng.random() < 0.5 else y + h - 1
            for a in (0, 1):
                cells.discard((x + 1 + 3 * i + a, yy))
                doors.add((x + 1 + 3 * i + a, yy))
    return cells, doors, w, h


# ------------------------------------------------------------------------------------------ biome tables
# (builder, weight): builders take (rng, x, y) and return (cells, doors, w, h)
def _lake(rng, x, y):
    return blob(rng, x, y, rng.randint(6, 10), squash=rng.choice((0.55, 0.7, 0.85)))


TABLES = [
    # 0 FROST MOON - lunar ruins: craters, broken halls, boulders, monoliths
    [(lambda r, x, y: ring(r, x, y), 34), (ruin, 24), (lambda r, x, y: blob(r, x, y, r.randint(2, 4)), 22),
     (lambda r, x, y: colonnade(r, x, y, "pillar"), 12), (lambda r, x, y: wall_line(r, x, y, 1, 12), 8)],
    # 1 MISTY LAKE - ponds, ice floes, a few ridges
    [(_lake, 42), (lambda r, x, y: blob(r, x, y, r.randint(2, 4)), 22), (lambda r, x, y: ring(r, x, y, r.randint(5, 7), False), 14),
     (lambda r, x, y: wall_line(r, x, y, 1, 10), 12), (ruin, 10)],
    # 2 FOREST OF MAGIC - groves, hedgerows, fairy rings, little mazes
    [(lambda r, x, y: blob(r, x, y, r.randint(4, 8), 0.9), 46), (lambda r, x, y: wall_line(r, x, y, 1, 9), 20),
     (lambda r, x, y: ring(r, x, y, r.randint(5, 8)), 16), (maze, 8), (ruin, 10)],
    # 3 SCARLET MANSION - architecture: rooms, halls, hedge-maze courts, colonnades
    [(lambda r, x, y: room(r, x, y, "mansion"), 38), (maze, 14), (lambda r, x, y: colonnade(r, x, y, "pillar"), 18),
     (lambda r, x, y: wall_line(r, x, y, 2, 12), 22), (ruin, 8)],
    # 4 NETHERWORLD - graveyard ruins and long stairs
    [(ruin, 36), (lambda r, x, y: colonnade(r, x, y, "pillar"), 22), (lambda r, x, y: wall_line(r, x, y, 2, 14), 14),
     (lambda r, x, y: ring(r, x, y, r.randint(5, 8)), 12), (lambda r, x, y: blob(r, x, y, r.randint(2, 4)), 16)],
    # 5 HAKUREI SHRINE - torii avenues, courtyards, lantern rows, mossy rocks
    [(torii_avenue, 28), (lambda r, x, y: room(r, x, y, "shrine"), 26), (lambda r, x, y: colonnade(r, x, y, "lantern"), 18),
     (lambda r, x, y: blob(r, x, y, r.randint(2, 4)), 16), (lambda r, x, y: wall_line(r, x, y, 1, 10), 12)],
]
DENSITY = (0.95, 0.85, 1.0, 1.0, 0.8, 0.7)      # how readily each biome accepts a new structure


def _pick(rng, table):
    tot = sum(w for _, w in table)
    r = rng.random() * tot
    for fn, w in table:
        r -= w
        if r <= 0:
            return fn
    return table[-1][0]


class Builder:
    """Places structures at random spots, keeping PAD free cells around each and out of the protected areas."""

    def __init__(self, rng, width, height, blocked, bmap, b2map, wmap):
        self.rng, self.W, self.H = rng, width, height
        self.res = [bytearray(width) for _ in range(height)]                 # 1 = reserved (footprint + pad)
        for (x, y) in blocked:
            if 0 <= x < width and 0 <= y < height:
                self.res[y][x] = 1
        self.walls, self.doors = set(), set()
        self.bmap, self.b2map, self.wmap = bmap, b2map, wmap
        self.count = 0

    def _free(self, x, y, w, h):
        if x - PAD < 2 or y - PAD < 2 or x + w + PAD > self.W - 2 or y + h + PAD > self.H - 2:
            return False
        for j in range(y - PAD, y + h + PAD):
            if self.res[j][x - PAD:x + w + PAD].count(1):
                return False
        return True

    def _reserve(self, x, y, w, h):
        for j in range(y - PAD, y + h + PAD):
            row = self.res[j]
            row[x - PAD:x + w + PAD] = b"\x01" * (w + 2 * PAD)

    def pick_table(self, x, y):
        b, b2, w = self.bmap[y][x], self.b2map[y][x], self.wmap[y][x]
        if w and self.rng.random() < w / 16.0:                               # inside a belt: borrow from the neighbour
            b = b2
        return b, TABLES[b]

    def try_at(self, x, y):
        rng = self.rng
        if self.res[y][x]:
            return False
        b, table = self.pick_table(x, y)
        if rng.random() > DENSITY[b]:
            return False
        cells, doors, _w, _h = _pick(rng, table)(rng, x, y)
        if not cells:
            return False
        pts = cells | doors
        xs = [c[0] for c in pts]
        ys = [c[1] for c in pts]
        bx0, by0 = min(xs), min(ys)
        bw, bh = max(xs) - bx0 + 1, max(ys) - by0 + 1
        if not self._free(bx0, by0, bw, bh):
            return False
        self._reserve(bx0, by0, bw, bh)
        self.walls |= cells
        self.doors |= doors
        self.count += 1
        return True

    def fill(self, passes=3, step=9):
        """Visit a jittered grid of candidate spots (a few passes, in random order) - far fewer wasted tries than
        uniform random placement, and it spreads structures evenly over the world."""
        rng = self.rng
        for _ in range(passes):
            spots = [(x + rng.randint(-4, 4), y + rng.randint(-4, 4))
                for x in range(6, self.W - 6, step) for y in range(6, self.H - 6, step)]
            rng.shuffle(spots)
            for x, y in spots:
                if 4 <= x < self.W - 4 and 4 <= y < self.H - 4:
                    self.try_at(x, y)
