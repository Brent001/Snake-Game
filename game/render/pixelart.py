"""Tiny pure-Python pixel painter.

Everything that used to be thousands of canvas items per frame (scenery, decor, arena floors, bullets) is now
painted ONCE into an RGBA buffer, encoded as a PNG and handed to Tk as a single PhotoImage.  Binary-alpha
(0 / 255) images are almost free for Tk to draw (a full-screen one costs < 1 ms), which is why every soft
gradient here is an *ordered dither* - it also happens to look exactly like 8-bit art.

No Tk is touched in this module, so painting can run on a worker thread.
"""
import base64
import math
import re
import struct
import zlib
from functools import lru_cache

BAYER = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))


@lru_cache(maxsize=4096)
def rgba(c, a=255):
    """'#rrggbb' -> 4 bytes."""
    if isinstance(c, tuple):
        return bytes(c) if len(c) == 4 else bytes(c) + bytes((a,))
    if not isinstance(c, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", c):
        raise ValueError(f"Invalid pixel-art colour {c!r}; expected '#rrggbb'")
    return bytes((int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16), a))


def blend(c1, c2, t):
    """Mix two '#rrggbb' colours (t=0 -> c1)."""
    t = max(0.0, min(1.0, t))
    a, b = rgba(c1), rgba(c2)
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class Art:
    """RGBA pixel buffer with a handful of fast primitives. Optional horizontal wrap for seamless parallax layers."""

    def __init__(self, w, h, wrapx=False, fill=None):
        self.w, self.h, self.wrapx = int(w), int(h), wrapx
        self.buf = bytearray(self.w * self.h * 4)
        if fill is not None:
            self.buf[:] = rgba(fill) * (self.w * self.h)

    # ------------------------------------------------------------------ primitives
    def span(self, x1, x2, y, col):
        """Fill pixels x1 <= x < x2 on row y with a 4-byte colour."""
        if y < 0 or y >= self.h or x2 <= x1:
            return
        w = self.w
        if self.wrapx:
            if x2 - x1 >= w:
                x1, x2 = 0, w
            else:
                x1m = x1 % w
                x2m = x1m + (x2 - x1)
                if x2m > w:
                    self._span(x1m, w, y, col)
                    self._span(0, x2m - w, y, col)
                    return
                x1, x2 = x1m, x2m
        self._span(x1, x2, y, col)

    def _span(self, x1, x2, y, col):
        if x1 < 0:
            x1 = 0
        if x2 > self.w:
            x2 = self.w
        if x2 <= x1:
            return
        o = (y * self.w + x1) * 4
        self.buf[o:o + (x2 - x1) * 4] = col * (x2 - x1)

    def pset(self, x, y, col):
        x, y = int(x), int(y)
        if self.wrapx:
            x %= self.w
        if 0 <= x < self.w and 0 <= y < self.h:
            o = (y * self.w + x) * 4
            self.buf[o:o + 4] = col

    def rect(self, x1, y1, x2, y2, c, a=255):
        """Filled rectangle, x1<=x<x2, y1<=y<y2."""
        col = rgba(c, a)
        for y in range(max(0, int(y1)), min(self.h, int(y2))):
            self.span(int(x1), int(x2), y, col)

    def frame(self, x1, y1, x2, y2, c, a=255, t=1):
        self.rect(x1, y1, x2, y1 + t, c, a)
        self.rect(x1, y2 - t, x2, y2, c, a)
        self.rect(x1, y1, x1 + t, y2, c, a)
        self.rect(x2 - t, y1, x2, y2, c, a)

    def ellipse(self, cx, cy, rx, ry, c, a=255, ring=0.0):
        """Filled ellipse (or a ring `ring` pixels thick)."""
        col = rgba(c, a)
        rx, ry = max(0.5, rx), max(0.5, ry)
        for y in range(int(math.floor(cy - ry)), int(math.ceil(cy + ry)) + 1):
            dy = (y + 0.5 - cy) / ry
            if abs(dy) > 1:
                continue
            half = rx * math.sqrt(1 - dy * dy)
            if ring > 0:
                inner = 1 - ring / max(rx, ry)
                ih = rx * math.sqrt(max(0.0, inner * inner - dy * dy)) if abs(dy) < inner else 0
                if ih > 0:
                    self.span(int(round(cx - half)), int(round(cx - ih)), y, col)
                    self.span(int(round(cx + ih)), int(round(cx + half)), y, col)
                    continue
            self.span(int(round(cx - half)), int(round(cx + half)), y, col)

    def poly(self, pts, c, a=255):
        """Filled polygon (even-odd scanline)."""
        col = rgba(c, a)
        n = len(pts)
        ys = [p[1] for p in pts]
        for y in range(max(0, int(math.floor(min(ys)))), min(self.h, int(math.ceil(max(ys))) + 1)):
            yy = y + 0.5
            xs = []
            for i in range(n):
                (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % n]
                if (y1 <= yy < y2) or (y2 <= yy < y1):
                    xs.append(x1 + (yy - y1) * (x2 - x1) / (y2 - y1))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.span(int(round(xs[i])), int(round(xs[i + 1])), y, col)

    def line(self, x1, y1, x2, y2, c, a=255, t=1):
        col = rgba(c, a)
        x1, y1, x2, y2 = int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2))
        dx, dy = abs(x2 - x1), -abs(y2 - y1)
        sx, sy = (1 if x1 < x2 else -1), (1 if y1 < y2 else -1)
        err = dx + dy
        for _ in range(4096):
            for k in range(t):
                self.pset(x1, y1 + k, col)
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x1 += sx
            if e2 <= dx:
                err += dx
                y1 += sy

    # ------------------------------------------------------------------ dither (the soft-gradient trick)
    def dither_rows(self, x1, x2, y1, y2, c, level_fn, a=255):
        """Ordered-dither a colour over a band. level_fn(y) -> 0..1 coverage for that row (cheap: whole rows at a time)."""
        col = rgba(c, a)
        clear = b"\x00\x00\x00\x00"
        w = x2 - x1
        if w <= 0:
            return
        for y in range(max(0, y1), min(self.h, y2)):
            lv = level_fn(y)
            if lv <= 0:
                continue
            thr = int(lv * 16 + 0.5)
            if thr >= 16:
                self.span(x1, x2, y, col)
                continue
            pat = b"".join(col if BAYER[y & 3][i] < thr else clear for i in range(4))
            reps = (w + 3) // 4 + 1
            row = (pat * reps)
            off = (x1 & 3) * 4
            row = row[off:off + w * 4]
            if not self.wrapx and x1 >= 0 and x2 <= self.w:
                o = (y * self.w + x1) * 4
                seg = self.buf[o:o + w * 4]
                # only paint the ON pixels (leave what is underneath alone where the pattern is clear)
                for i in range(0, w * 4, 4):
                    if row[i + 3]:
                        seg[i:i + 4] = col
                self.buf[o:o + w * 4] = seg
            else:
                for i in range(w):
                    if row[i * 4 + 3]:
                        self.pset(x1 + i, y, col)

    def dither_fn(self, x1, y1, x2, y2, c, fn, a=255):
        """Per-pixel ordered dither: fn(x, y) -> coverage 0..1 (use for radial glows; keep the area small)."""
        col = rgba(c, a)
        for y in range(max(0, y1), min(self.h, y2)):
            br = BAYER[y & 3]
            for x in range(x1, x2):
                lv = fn(x, y)
                if lv > 0 and br[x & 3] < lv * 16 + 0.5:
                    self.pset(x, y, col)

    def glow(self, cx, cy, r, c, strength=1.0, a=255):
        """Dithered radial glow."""
        r2 = r * r

        def fn(x, y):
            d = ((x - cx) ** 2 + (y - cy) ** 2) / r2
            return 0.0 if d >= 1 else (1 - d) ** 1.6 * strength
        self.dither_fn(int(cx - r), int(cy - r), int(cx + r) + 1, int(cy + r) + 1, c, fn, a)

    # ------------------------------------------------------------------ export
    def png(self):
        w, h = self.w, self.h
        stride = w * 4
        raw = bytearray()
        for y in range(h):
            raw.append(0)
            raw += self.buf[y * stride:(y + 1) * stride]

        def chunk(tag, data):
            b = tag + data
            return struct.pack(">I", len(data)) + b + struct.pack(">I", zlib.crc32(b) & 0xffffffff)
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 1)) + chunk(b"IEND", b""))

    def b64(self):
        return base64.b64encode(self.png())

    def crop(self, x, y, w, h):
        o = Art(w, h)
        for j in range(h):
            sy = y + j
            if 0 <= sy < self.h:
                a, b = max(0, x), min(self.w, x + w)
                if b > a:
                    o.buf[(j * w + (a - x)) * 4:(j * w + (b - x)) * 4] = self.buf[(sy * self.w + a) * 4:(sy * self.w + b) * 4]
        return o


def photo(tk, master, b64, zoom=1):
    """PNG bytes (base64) -> tk.PhotoImage, optionally nearest-neighbour zoomed (pixel-art upscaling)."""
    img = tk.PhotoImage(master=master, data=b64)
    return img.zoom(zoom) if zoom > 1 else img
