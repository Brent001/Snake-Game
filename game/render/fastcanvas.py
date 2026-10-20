"""A tk.Canvas that can tag every item it creates (used to keep HUD pieces alive between frames)."""
import tkinter as tk


class FastCanvas(tk.Canvas):
    deftag = None          # when set, every new item gets these tags unless it already names its own

    def _create(self, itemType, args, kw):
        if self.deftag is not None and "tags" not in kw:
            kw = dict(kw, tags=self.deftag)
        return super()._create(itemType, args, kw)
