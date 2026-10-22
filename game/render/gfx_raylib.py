"""Immediate-mode, GPU-batched drawing surface with a tk.Canvas-compatible API (raylib backend).

Why: Repair Terminal builds ~600 retained Tk canvas items every frame (create_oval / create_line / ...), deletes them
and repeats.  raylib draws straight to the GPU (rlgl batches triangles/lines automatically), so the same calls get much
cheaper and no overlay window / second thread is needed.

Usage (drop-in for the code in game/render/*):

    from game.render.gfx_raylib import RaylibCanvas
    c = RaylibCanvas(960, 600, "Repair Terminal")
    while c.frame_begin():              # polls the window, begins drawing, clears the background
        c.create_rectangle(10, 10, 100, 40, fill="#112233", outline="#7df9ff", width=2)
        c.create_text(20, 25, text="HP 100", anchor="w", fill="#ffffff", font=("Segoe UI", 10, "bold"))
        c.frame_end()

Supported kwargs: fill, outline, width, text, font, anchor, start, extent, style, image, stipple (-> alpha), tags/dash (ignored).
NOT supported (retained-mode features of tk.Canvas): coords(), itemconfig(), move(), find_*().  They only exist to keep
items alive between frames; in immediate mode you simply redraw.  delete()/tag_raise()/tag_lower() are no-ops.

Performance note: this module talks to raylib through the low-level cffi module and reuses its structs.  The high-level
`pyray` wrappers allocate a fresh struct (plus weakref bookkeeping) for every Vector2/Color argument, which measured
5-8x slower per draw call.  Use `pyray` only for non-hot calls (input, screenshots, ...).
"""
import math
import os

from raylib import ffi
from raylib import rl as lib

_STIPPLE_ALPHA = {"gray12": 32, "gray25": 64, "gray50": 128, "gray75": 192}
_NAMED = {"white": (255, 255, 255), "black": (0, 0, 0), "red": (255, 0, 0), "green": (0, 128, 0), "blue": (0, 0, 255),
          "yellow": (255, 255, 0), "cyan": (0, 255, 255), "magenta": (255, 0, 255), "gray": (190, 190, 190),
          "grey": (190, 190, 190), "orange": (255, 165, 0)}
_FONT_PATHS = {
    True: [r"C:\Windows\Fonts\segoeuib.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
           "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"],
    False: [r"C:\Windows\Fonts\segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf", "/usr/share/fonts/TTF/DejaVuSans.ttf"],
}
_MONO_PATHS = [r"C:\Windows\Fonts\consolab.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"]

# Reused argument structs - mutate fields, pass X[0]; no allocation per draw call.
_A, _B, _C, _D = (ffi.new("Vector2 *") for _ in range(4))
_R, _R2 = ffi.new("Rectangle *"), ffi.new("Rectangle *")

_DrawLineV, _DrawLineEx = lib.DrawLineV, lib.DrawLineEx
_DrawTriangle = lib.DrawTriangle
_DrawCircleV, _DrawCircleLinesV, _DrawRing = lib.DrawCircleV, lib.DrawCircleLinesV, lib.DrawRing
_DrawRectV, _DrawRectLinesEx = lib.DrawRectangleV, lib.DrawRectangleLinesEx


class RaylibCanvas:
    """tk.Canvas look-alike.  One instance per window."""

    _grad_vec = None

    def __init__(self, width=960, height=600, title="Repair Terminal", bg="#080e1c", fps=60, vsync=True, resizable=True,
                 msaa=False):
        flags = 0
        if vsync:
            flags |= lib.FLAG_VSYNC_HINT
        if resizable:
            flags |= lib.FLAG_WINDOW_RESIZABLE
        if msaa:
            flags |= lib.FLAG_MSAA_4X_HINT
        lib.SetConfigFlags(flags)
        lib.SetTraceLogLevel(lib.LOG_WARNING)
        lib.InitWindow(width, height, title.encode())
        if not vsync:
            lib.SetTargetFPS(fps)
        lib.SetExitKey(0)                        # Esc belongs to the game (pause menu), not to the window
        self._colors, self._fonts, self._tex, self._measure, self._tris = {}, {}, {}, {}, {}
        self._keep = []                          # keeps cffi memory alive
        self.bg = self._rgb(bg)
        self.items = 0                           # draw calls this frame (handy for profiling)

    # ------------------------------------------------------------------ frame control
    def frame_begin(self):
        if lib.WindowShouldClose():
            return False
        lib.BeginDrawing()
        lib.ClearBackground(self.bg)
        self.items = 0
        return True

    def frame_end(self):
        lib.EndDrawing()

    def close(self):
        for f in self._fonts.values():
            lib.UnloadFont(f)
        lib.CloseWindow()

    def winfo_width(self):
        return lib.GetScreenWidth()

    def winfo_height(self):
        return lib.GetScreenHeight()

    # ------------------------------------------------------------------ colours
    def _rgb(self, spec, alpha=255):
        key = (spec, alpha)
        col = self._colors.get(key)
        if col is None:
            s = spec
            if isinstance(s, str) and s.startswith("#"):
                h = s[1:]
                if len(h) == 3:
                    h = "".join(ch * 2 for ch in h)
                rgb = (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
            else:
                rgb = _NAMED.get(str(s).lower(), (255, 0, 255))
            p = ffi.new("Color *", [rgb[0], rgb[1], rgb[2], alpha])
            self._keep.append(p)
            col = self._colors[key] = p[0]
        return col

    def _col(self, spec, kw):
        if not spec:
            return None
        return self._rgb(spec, _STIPPLE_ALPHA.get(kw.get("stipple"), 255))

    # ------------------------------------------------------------------ tk.Canvas no-ops (immediate mode)
    def delete(self, *a): pass
    def tag_raise(self, *a): pass
    def tag_lower(self, *a): pass
    def update_idletasks(self): pass

    def configure(self, **kw):
        if "bg" in kw:
            self.bg = self._rgb(kw["bg"])
    config = configure

    # ------------------------------------------------------------------ primitives
    def create_rectangle(self, x0, y0, x1, y1, **kw):
        self.items += 1
        if x1 < x0: x0, x1 = x1, x0
        if y1 < y0: y0, y1 = y1, y0
        fill = self._col(kw.get("fill"), kw)
        outline = kw.get("outline", None if "fill" in kw else "#000000")
        if fill is not None:
            _A.x, _A.y, _B.x, _B.y = x0, y0, x1 - x0, y1 - y0
            _DrawRectV(_A[0], _B[0], fill)
        if outline:
            _R.x, _R.y, _R.width, _R.height = x0, y0, x1 - x0, y1 - y0
            _DrawRectLinesEx(_R[0], max(1, int(kw.get("width", 1))), self._col(outline, kw))
        return self.items

    def create_oval(self, x0, y0, x1, y1, **kw):
        self.items += 1
        cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, abs(x1 - x0) / 2, abs(y1 - y0) / 2
        fill = self._col(kw.get("fill"), kw)
        outline = kw.get("outline", None if "fill" in kw else "#000000")
        out = self._col(outline, kw) if outline else None
        w = max(1, int(kw.get("width", 1)))
        if abs(rx - ry) < 0.5:                                   # circle: native fast paths
            _A.x, _A.y = cx, cy
            if fill is not None:
                _DrawCircleV(_A[0], rx, fill)
            if out is not None:
                if w <= 1:
                    _DrawCircleLinesV(_A[0], rx, out)
                else:
                    _DrawRing(_A[0], max(0.0, rx - w / 2), rx + w / 2, 0, 360, 24, out)
        else:                                                    # ellipse
            if fill is not None:
                lib.DrawEllipse(int(cx), int(cy), rx, ry, fill)
            if out is not None:
                self._polyline(self._ellipse_pts(cx, cy, rx, ry, 0, 360), w, out)
        return self.items

    @staticmethod
    def _ellipse_pts(cx, cy, rx, ry, start, extent):
        # segment count from a 0.3 px flatness tolerance: small bullets need ~6 segments, big rings ~40
        r = max(rx, ry, 1.0)
        step = max(6.0, min(45.0, math.degrees(2 * math.acos(max(-1.0, 1 - 0.3 / r)))))
        n = max(3, int(abs(extent) / step) + 1)
        a0 = math.radians(start)
        da = math.radians(extent) / n
        # Tk angles run counter-clockwise from 3 o'clock; screen y points down
        return [(cx + rx * math.cos(a0 + da * i), cy - ry * math.sin(a0 + da * i)) for i in range(n + 1)]

    def create_arc(self, x0, y0, x1, y1, **kw):
        self.items += 1
        cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, abs(x1 - x0) / 2, abs(y1 - y0) / 2
        pts = self._ellipse_pts(cx, cy, rx, ry, float(kw.get("start", 0)), float(kw.get("extent", 90)))
        style = kw.get("style", "pieslice")
        fill = self._col(kw.get("fill"), kw)
        outline = kw.get("outline", None if style == "arc" else "#000000")
        out = self._col(outline, kw) if outline else None
        w = max(1, int(kw.get("width", 1)))
        if style != "arc" and fill is not None:
            self._fill_poly(pts + ([(cx, cy)] if style == "pieslice" else []), fill)
        if out is not None:
            line = pts if style == "arc" else (pts + [(cx, cy), pts[0]] if style == "pieslice" else pts + [pts[0]])
            self._polyline(line, w, out)
        elif style == "arc" and fill is not None:                # tolerate fill= on style="arc"
            self._polyline(pts, w, fill)
        return self.items

    def create_line(self, *coords, **kw):
        self.items += 1
        self._polyline(self._points(coords), max(1, float(kw.get("width", 1))), self._col(kw.get("fill", "#000000"), kw))
        return self.items

    def create_polygon(self, *coords, **kw):
        self.items += 1
        pts = self._points(coords)
        fill = self._col(kw["fill"], kw) if kw.get("fill", "x") else None
        if "fill" not in kw:
            fill = self._rgb("#000000")
        if fill is not None:
            self._fill_poly(pts, fill)
        if kw.get("outline"):
            self._polyline(pts + [pts[0]], max(1, float(kw.get("width", 1))), self._col(kw["outline"], kw))
        return self.items

    @staticmethod
    def _points(coords):
        """Accept tk's spellings: (x0,y0,x1,y1,...), ([x0,y0,...],) and ([(x0,y0),...],)."""
        if len(coords) == 1:
            coords = coords[0]
        if coords and isinstance(coords[0], (tuple, list)):
            return [(p[0], p[1]) for p in coords]
        return [(coords[i], coords[i + 1]) for i in range(0, len(coords) - 1, 2)]

    # ------------------------------------------------------------------ text
    def _font(self, spec):
        family, size, style = ("Segoe UI", 10, "")
        if isinstance(spec, (tuple, list)):
            family = spec[0]
            size = spec[1] if len(spec) > 1 else 10
            style = " ".join(str(x) for x in spec[2:]) if len(spec) > 2 else ""
        px = max(6, int(round(abs(size) * (1.0 if size < 0 else 96 / 72))))      # Tk: positive = points, negative = pixels
        bold = "bold" in style
        mono = family.lower() in ("consolas", "courier", "courier new", "monospace")
        key = (px, bold, mono)
        f = self._fonts.get(key)
        if f is None:
            path = next((p for p in (_MONO_PATHS if mono else []) + _FONT_PATHS[bold] if os.path.exists(p)), None)
            if path:
                f = lib.LoadFontEx(path.encode(), px, ffi.NULL, 0)
                lib.SetTextureFilter(f.texture, lib.TEXTURE_FILTER_BILINEAR)
            else:
                f = lib.GetFontDefault()
            self._fonts[key] = f
        return key, f, px

    def create_text(self, x, y, **kw):
        self.items += 1
        text = str(kw.get("text", ""))
        if not text:
            return self.items
        fkey, font, px = self._font(kw.get("font"))
        anchor = kw.get("anchor", "center")
        mk = (fkey, text)
        wh = self._measure.get(mk)
        if wh is None:
            if len(self._measure) > 8192:
                self._measure.clear()
            m = lib.MeasureTextEx(font, text.encode(), px, 0)
            wh = self._measure[mk] = (m.x, m.y)
        w, h = wh
        _A.x = x + (0.0 if "w" in anchor else (-w if "e" in anchor else -w / 2))
        _A.y = y + (0.0 if "n" in anchor else (-h if "s" in anchor else -h / 2))
        lib.DrawTextEx(font, text.encode(), _A[0], px, 0, self._col(kw.get("fill", "#000000"), kw))
        return self.items

    # ------------------------------------------------------------------ images (replace tk.PhotoImage with textures)
    def load_texture(self, path):
        t = self._tex.get(path)
        if t is None:
            t = lib.LoadTexture(path.encode())
            lib.SetTextureFilter(t, lib.TEXTURE_FILTER_POINT)    # crisp pixel art
            self._tex[path] = t
        return t

    def create_image(self, x, y, **kw):
        self.items += 1
        tex = kw["image"]
        anchor = kw.get("anchor", "center")
        w, h = tex.width, tex.height
        _A.x = x + (0 if "w" in anchor else (-w if "e" in anchor else -w / 2))
        _A.y = y + (0 if "n" in anchor else (-h if "s" in anchor else -h / 2))
        lib.DrawTextureV(tex, _A[0], self._rgb("#ffffff"))
        return self.items

    def draw_sprite(self, tex, src, dst, rotation=0.0, tint="#ffffff"):
        """Draw one cell of an atlas: src=(x,y,w,h) in the texture, dst=(x,y,w,h) on screen (rotation about its centre)."""
        self.items += 1
        _R.x, _R.y, _R.width, _R.height = src
        _R2.x, _R2.y, _R2.width, _R2.height = dst[0] + dst[2] / 2, dst[1] + dst[3] / 2, dst[2], dst[3]
        _A.x, _A.y = dst[2] / 2, dst[3] / 2
        lib.DrawTexturePro(tex, _R[0], _R2[0], _A[0], rotation, self._rgb(tint))

    # ------------------------------------------------------------------ GPU extras that tk can't do
    def additive(self, on=True):
        """Glow: draw bullets/particles between additive(True) and additive(False) - one blend switch, not one per item."""
        if on:
            lib.BeginBlendMode(lib.BLEND_ADDITIVE)
        else:
            lib.EndBlendMode()

    def glow(self, x, y, r, color, alpha=90):
        """Soft radial glow in a single draw call (no bloom pass needed for small effects)."""
        c, edge = self._rgb(color, alpha), self._rgb(color, 0)
        _A.x, _A.y = x, y
        if self._grad_vec is None:                       # raylib 6 takes a Vector2 centre, raylib <= 5.5 takes ints
            try:
                lib.DrawCircleGradient(_A[0], r, c, edge)
                self._grad_vec = True
                return
            except TypeError:
                self._grad_vec = False
        if self._grad_vec:
            lib.DrawCircleGradient(_A[0], r, c, edge)
        else:
            lib.DrawCircleGradient(int(x), int(y), r, c, edge)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _polyline(pts, width, col):
        if col is None or len(pts) < 2:
            return
        if width <= 1:
            for i in range(len(pts) - 1):
                _A.x, _A.y = pts[i]
                _B.x, _B.y = pts[i + 1]
                _DrawLineV(_A[0], _B[0], col)
        else:
            for i in range(len(pts) - 1):
                _A.x, _A.y = pts[i]
                _B.x, _B.y = pts[i + 1]
                _DrawLineEx(_A[0], _B[0], width, col)

    @staticmethod
    def _tri(a, b, c, col):
        """raylib culls clockwise triangles (verified empirically); screen y points down, so we need cross < 0."""
        if (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) > 0:
            b, c = c, b
        _A.x, _A.y, _B.x, _B.y, _C.x, _C.y = a[0], a[1], b[0], b[1], c[0], c[1]
        _DrawTriangle(_A[0], _B[0], _C[0], col)

    def _fill_poly(self, pts, col):
        """Fill any simple polygon.  Triangulation (fan if convex, ear clipping if concave) is cached by shape, so a
        moving bullet of a fixed shape pays for it once; the cache key is position-independent."""
        n = len(pts)
        if n < 3:
            return
        x0, y0 = pts[0]
        key = tuple((round(x - x0, 1), round(y - y0, 1)) for x, y in pts)
        tris = self._tris.get(key)
        if tris is None:
            if len(self._tris) > 2048:
                self._tris.clear()
            tris = self._tris[key] = self._triangulate(pts)
        for i, j, k in tris:
            self._tri(pts[i], pts[j], pts[k], col)

    @staticmethod
    def _triangulate(pts):
        n = len(pts)
        def cross(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
        area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
        idx = list(range(n)) if area > 0 else list(range(n - 1, -1, -1))
        if all(cross(pts[idx[i]], pts[idx[(i + 1) % n]], pts[idx[(i + 2) % n]]) >= 0 for i in range(n)):
            return [(idx[0], idx[i], idx[i + 1]) for i in range(1, n - 1)]
        def inside(p, a, b, c):
            return cross(a, b, p) >= 0 and cross(b, c, p) >= 0 and cross(c, a, p) >= 0
        out, guard = [], 0
        while len(idx) > 3 and guard < 4 * n:
            guard += 1
            m = len(idx)
            for i in range(m):
                a, b, c = idx[i - 1], idx[i], idx[(i + 1) % m]
                if cross(pts[a], pts[b], pts[c]) <= 0:
                    continue
                if any(inside(pts[j], pts[a], pts[b], pts[c]) for j in idx if j not in (a, b, c)):
                    continue
                out.append((a, b, c))
                del idx[i]
                break
            else:
                break
        if len(idx) == 3:
            out.append(tuple(idx))
        return out
