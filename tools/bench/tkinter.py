"""Minimal headless tkinter stub: counts canvas calls so the game can be profiled without a display."""
from collections import Counter

STATS = Counter()

class _W:
    def __init__(self, *a, **k): self._k = dict(k)
    def pack(self, *a, **k): pass
    def pack_forget(self): pass
    def config(self, **k): self._k.update(k)
    configure = config
    def bind(self, *a, **k): pass

class Tk(_W):
    def title(self, *a): pass
    def resizable(self, *a): pass
    def minsize(self, *a): pass
    def after(self, *a, **k): pass
    def destroy(self): pass
    def attributes(self, *a, **k): pass
    def protocol(self, *a, **k): pass
    def geometry(self, *a, **k): pass
    def update(self, *a, **k): pass
    def winfo_width(self): return 960
    def winfo_height(self): return 600

class Frame(_W): pass
class Label(_W): pass

class PhotoImage:
    def __init__(self, *a, **k): self.w = k.get("width", 1); self.h = k.get("height", 1)
    def put(self, *a, **k): pass
    def zoom(self, *a, **k): return PhotoImage(width=self.w, height=self.h)
    def copy(self): return PhotoImage(width=self.w, height=self.h)
    def blank(self): pass
    def width(self): return self.w
    def height(self): return self.h

class Canvas(_W):
    _n = 0
    def _mk(self, kind):
        STATS[kind] += 1
        Canvas._n += 1
        return Canvas._n
    def create_rectangle(self, *a, **k): return self._mk("rect")
    def create_oval(self, *a, **k): return self._mk("oval")
    def create_line(self, *a, **k): return self._mk("line")
    def create_polygon(self, *a, **k): return self._mk("poly")
    def create_text(self, *a, **k): return self._mk("text")
    def create_arc(self, *a, **k): return self._mk("arc")
    def create_image(self, *a, **k): return self._mk("image")
    def find_all(self): return ()
    def delete(self, *a): STATS["delete"] += 1
    def coords(self, *a, **k): STATS["coords"] += 1
    def itemconfig(self, *a, **k): STATS["itemconfig"] += 1
    itemconfigure = itemconfig
    def move(self, *a): STATS["move"] += 1
    def tag_raise(self, *a): STATS["raise"] += 1
    def tag_lower(self, *a): STATS["lower"] += 1
