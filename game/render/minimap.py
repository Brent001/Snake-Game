"""Minimap: pixel image (each pixel = 2x2 world cells), live overlay and node removal."""
import tkinter as tk

from ..config import C_BOARD, C_CYAN, C_GOLD, C_MINT, GRID_H, GRID_W, MM, MMS, NUM_FRAGMENTS, WORLD_H
from ..data.bosses import BOSSES
from ..data.biomes import STYLES
from ..data.elements import ECOL
from ..utils import mix
from ..world.layout import ARENAS, CORE
from ..world.level import B2MAP, BMAP, SAVE_CELLS, WALLS, WMAP

MM_VIEW_SCALE = 1.25

MM_FLOOR = [mix(s["pal"]["floor"][0], s["pal"]["edge"][0], 0.2) for s in STYLES]
MM_WALL = [mix(s["pal"]["edge"][0], "#000000", 0.15) for s in STYLES]
MM_NODE = "#ff4f7d"


class MinimapMixin:
    def mm_color(self, bx, by):
        cells = [(bx * MMS + i, by * MMS + j) for i in range(MMS) for j in range(MMS) if bx * MMS + i < GRID_W and by * MMS + j < WORLD_H]
        b = BMAP[cells[len(cells) // 2][1]][cells[len(cells) // 2][0]]
        if sum(1 for c in cells if c in WALLS) >= 2:
            return MM_WALL[b]
        w = WMAP[cells[len(cells) // 2][1]][cells[len(cells) // 2][0]]
        if w:                                           # transition belts fade between the two biomes
            return mix(MM_FLOOR[b], MM_FLOOR[B2MAP[cells[len(cells) // 2][1]][cells[len(cells) // 2][0]]], w / 16.0)
        return MM_FLOOR[b]

    def kill_node(self, cell):
        self.nodes.discard(cell)
        bx, by = cell[0] // MMS, cell[1] // MMS
        self.minimap_img.put(self.mm_color(bx, by), to=(bx, by, bx + 1, by + 1))

    def build_minimap_image(self):
        hw, hh = -(-GRID_W // MMS), -(-WORLD_H // MMS)
        img = tk.PhotoImage(width=hw, height=hh)
        rows = []
        for by in range(hh):
            rows.append("{" + " ".join(self.mm_color(bx, by) for bx in range(hw)) + "}")
        img.put(" ".join(rows))
        return img

    def minimap_overlay(self):
        """Base minimap + all static markers baked into one image; rebuilt only when something is collected / defeated."""
        sig = (len(self.nodes), len(self.charges), len(self.pickups), len(self.remaining), len(self.visited_saves),
            tuple(sorted(self.defeated)), self.boss_defeated)
        if self.__dict__.get("_mm_sig") != sig or self.__dict__.get("_mm_base") is not self.minimap_img:
            ov = self.minimap_img.copy()
            hw, hh = -(-GRID_W // MMS), -(-WORLD_H // MMS)

            def bake(cell, color, size=MM + 1):
                x1, y1 = max(0, int(round(cell[0] * MM - 1))), max(0, int(round(cell[1] * MM - 1)))
                n = max(1, int(round(size)))
                if x1 < hw and y1 < hh:
                    ov.put(color, to=(x1, y1, min(hw, x1 + n), min(hh, y1 + n)))

            for cell in SAVE_CELLS:
                bake(cell, "#fff1a0" if cell in self.visited_saves else "#a08830", MM + 2)
            for cell in self.charges:
                bake(cell, C_MINT)
            for cell, k in self.pickups.items():
                if k.startswith("oc_"):
                    bake(cell, ECOL[k[3:]], MM + 2)
            for cell in self.remaining:
                bake(cell, C_GOLD, MM + 2)
            if self.boss_defeated:
                bake(ARENAS[4]["ow"], C_CYAN, MM + 2)
            self._mm_sig, self._mm_base, self._mm_img = sig, self.minimap_img, ov
        return self._mm_img

    def draw_minimap(self):
        c = self.canvas
        # Keep the familiar top-right placement, but restore a little more of the
        # old map footprint so the minimap is easier to read at 1366x768.
        scale = MM_VIEW_SCALE
        w, h = GRID_W * MM * scale, WORLD_H * MM * scale
        top_pad = 48 if getattr(self, "boss_active", lambda: False)() else 8
        ox, oy = self.bw - w - 16, top_pad
        overlay = self.minimap_overlay()
        # PhotoImage only supports integer zoom/subsample; 5/4 gives a clean 1.25x
        # map without rebuilding pixels every frame.
        if getattr(self, "_mm_display_src", None) is not overlay:
            self._mm_display_src = overlay
            self._mm_display_img = overlay.zoom(5, 5).subsample(4, 4)
        if not getattr(self, "in_dungeon", False) and self.show_minimap:
            c.create_rectangle(ox - 3, oy - 3, ox + w + 3, oy + h + 3, fill=C_BOARD, outline="#2a4a80", width=2)
            c.create_rectangle(ox, oy, ox + w, oy + h, outline="#143451", width=1)
            c.create_image(ox, oy, image=self._mm_display_img, anchor="nw")

            def dot(cell, color, size=MM + 1):
                x, y = cell
                ds = size * scale
                c.create_rectangle(ox + x * MM * scale - 1, oy + y * MM * scale - 1,
                                   ox + x * MM * scale + ds - 1, oy + y * MM * scale + ds - 1, fill=color, outline="")

            for i, a in enumerate(ARENAS):
                if i in self.defeated:
                    continue
                locked = a["final"] and self.collected < NUM_FRAGMENTS
                px, py = a["ow"]
                c.create_oval(ox + px * MM * scale - 6, oy + py * MM * scale - 6,
                              ox + px * MM * scale + 6, oy + py * MM * scale + 6,
                              outline="#ff7a30" if locked else BOSSES[i]["phases"][0]["color"], width=2)
            if self.heat_t > 0:
                for e in self.enemies:
                    if not e["dead"]:
                        dot((int(e["x"]), int(e["y"])), C_GOLD if e["elite"] == 2 else "#ff4040", MM + 2 if e["elite"] == 2 else MM + 1)
            dot(self.snake[0], "#ffffff", MM + 2)
            c.create_rectangle(ox + self.cam_x * MM * scale, oy + self.cam_y * MM * scale,
                ox + (self.cam_x + self.vw) * MM * scale, oy + (self.cam_y + self.vh) * MM * scale, outline="#ffffff")

        # Resource panel lives directly below the map and matches its widened width.
        py0 = oy + h + 8
        self._pixel_panel(ox, py0, ox + w, py0 + 70, C_CYAN)
        self.ptext(ox + 10, py0 + 10, "PULSE", 1, C_CYAN)
        self.ptext(ox + w - 10, py0 + 10, f"{self.ammo:02d}", 2, "#ffffff", anchor="e")
        self.ptext(ox + 10, py0 + 28, "ENERGY", 1, "#6fe2ff")
        self.ptext(ox + w - 10, py0 + 28, f"+{self.S['energy_recharge']:.0f}%", 1, "#c8f6ff", anchor="e")
        self.ptext(ox + 10, py0 + 46, f"DMG {self.S['dmg']:+.0f}%", 1, "#b9d7ff")
        self.ptext(ox + 92, py0 + 46, f"LEECH {self.S['steal']:.1f}%", 1, "#ff9ab0")
        self.ptext(ox + w - 10, py0 + 64, f"{self.elem.upper()}  FOOD {self.food_eaten:02d}", 1, ECOL.get(self.elem, C_CYAN), anchor="e")
