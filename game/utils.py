"""Small, dependency-free helper functions."""
from functools import lru_cache


def rect(x1, y1, x2, y2):
    """Set of every grid cell inside the inclusive rectangle."""
    return {(x, y) for x in range(x1, x2 + 1) for y in range(y1, y2 + 1)}


@lru_cache(maxsize=16384)
def _mix(c1, c2, tq):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    t = tq / 128.0
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def mix(c1, c2, t):
    """Blend two '#rrggbb' colours (t = 0 -> c1, t = 1 -> c2). Cached; t is quantised to 1/128 (invisible)."""
    return _mix(c1, c2, int(round(max(0.0, min(1.0, t)) * 128)))


def same(c):
    """A palette entry that is identical by day and by night."""
    return (c, c)


def rounded_rect(x1, y1, x2, y2, r):
    """Point list for a smooth rounded rectangle polygon."""
    return [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
        x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]


# ------------------------------------------------------------------ spatial containers (cheap view culling)
SB = 4      # bucket side = 2**SB cells


class SpatialDict(dict):
    """dict keyed by (x, y) that also keeps a bucket index, so the renderer can ask for the items near the camera
    instead of testing every one of the thousands of items in the world on every frame."""

    def __init__(self, *a, **k):
        super().__init__()
        self._b = {}
        self.update(*a, **k)

    def __setitem__(self, key, val):
        if key not in self:
            self._b.setdefault((key[0] >> SB, key[1] >> SB), set()).add(key)
        super().__setitem__(key, val)

    def __delitem__(self, key):
        super().__delitem__(key)
        self._drop(key)

    def _drop(self, key):
        b = self._b.get((key[0] >> SB, key[1] >> SB))
        if b is not None:
            b.discard(key)

    def pop(self, key, *default):
        if key in self:
            self._drop(key)
        return super().pop(key, *default)

    def popitem(self):
        key, val = super().popitem()
        self._drop(key)
        return key, val

    def clear(self):
        super().clear()
        self._b.clear()

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]

    def update(self, *a, **k):
        for key, val in dict(*a, **k).items():
            self[key] = val

    def near(self, x0, y0, x1, y1):
        """(cell, value) pairs whose cell lies inside the rectangle (inclusive)."""
        for by in range(int(y0) >> SB, (int(y1) >> SB) + 1):
            for bx in range(int(x0) >> SB, (int(x1) >> SB) + 1):
                for key in self._b.get((bx, by), ()):
                    if x0 <= key[0] <= x1 and y0 <= key[1] <= y1:
                        yield key, self[key]


class SpatialSet(set):
    """set of (x, y) cells with the same bucket index as SpatialDict."""

    def __init__(self, items=()):
        super().__init__()
        self._b = {}
        for it in items:
            self.add(it)

    def add(self, key):
        if key not in self:
            self._b.setdefault((key[0] >> SB, key[1] >> SB), set()).add(key)
        super().add(key)

    def discard(self, key):
        if key in self:
            b = self._b.get((key[0] >> SB, key[1] >> SB))
            if b is not None:
                b.discard(key)
        super().discard(key)

    def remove(self, key):
        if key not in self:
            raise KeyError(key)
        self.discard(key)

    def pop(self):
        key = super().pop()
        b = self._b.get((key[0] >> SB, key[1] >> SB))
        if b is not None:
            b.discard(key)
        return key

    def clear(self):
        super().clear()
        self._b.clear()

    def update(self, *others):
        for o in others:
            for key in o:
                self.add(key)

    def near(self, x0, y0, x1, y1):
        for by in range(int(y0) >> SB, (int(y1) >> SB) + 1):
            for bx in range(int(x0) >> SB, (int(x1) >> SB) + 1):
                for key in self._b.get((bx, by), ()):
                    if x0 <= key[0] <= x1 and y0 <= key[1] <= y1:
                        yield key
