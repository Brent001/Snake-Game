"""HUD rendering: boss bar, biome banner, vitals, hotbar, floating text, scent arrows, clock and state overlays."""
import math

from ..config import C_BOARD, C_CYAN, C_GOLD, C_MUTED, C_TEXT, DAY_LEN, GRID_W, MM
from ..data.biomes import STYLES
from ..data.bosses import BOSSES
from ..data.elements import ECOL, ELEMS, RESON
from ..data.skills import SKILLS
from ..data.keybinds import SKILL_LABELS, SKILL_SLOT_IDS, skill_ids_for_bar
from ..utils import mix


class HudMixin:
    def retained(self, name, sig, build):
        """Draw `build()` once and keep its canvas items alive while `sig` is unchanged (a HUD that is rebuilt every frame
        costs hundreds of text/rect creations; this one costs a single tag_raise).  Items are tagged `name` + `keep`."""
        c = self.canvas
        if self._ret.get(name) != sig:
            c.delete(name)
            c.deftag = (name, "keep")
            try:
                build()
            finally:
                c.deftag = None
            self._ret[name] = sig
        c.tag_raise(name)                       # stay above the world items created after the last frame's delete

    def draw_boss_ui(self):
        b = self.boss
        if not self.boss_active():
            return
        c = self.canvas
        info = BOSSES[b["idx"]]
        phase = info["phases"][b["phase"]]
        x0 = 18
        x1 = self.bw - 18 - (int(GRID_W * MM * 1.25) + 24 if self.show_minimap else 0)
        c.create_rectangle(x0, 14, x1, 24, fill="#05080f", outline="#2a4a80")
        frac = max(0.0, b["hp"] / phase["hp"])
        if frac > 0:
            c.create_rectangle(x0 + 1, 15, x0 + 1 + (x1 - x0 - 2) * frac, 23, fill=phase["color"], outline="")
        stars = "\u2605" * (len(info["phases"]) - b["phase"] - 1)
        c.create_text(x0, 38, anchor="w", fill=C_TEXT, font=("Segoe UI", 10, "bold"), text=f"{info['name']}   {stars}")
        c.create_text(x1, 38, anchor="e", fill=phase["color"], font=("Segoe UI", 10, "bold"), text=phase["name"])
        if b["state"] == "banner":
            y = self.bh * 0.55
            head = "BOSS BATTLE" if b["phase"] == 0 else "SPELL CARD"
            c.create_rectangle(0, y - 50, self.bw, y + 50, fill=C_BOARD, stipple="gray50", outline="")
            self.draw_touhou_boss_sprite(info["sprite"], 130, y, 5, flash=False, dim=0.0, anim="walk", direction="down")
            c.create_text(self.bw // 2 + 2, y - 12 + 2, text=phase["name"], fill="#000000", font=("Segoe UI", 20, "bold"))
            c.create_text(self.bw // 2, y - 12, text=phase["name"], fill=phase["color"], font=("Segoe UI", 20, "bold"))
            c.create_text(self.bw // 2, y + 22, text=head, fill=C_MUTED, font=("Segoe UI", 10, "bold"))

    def draw_biome_transition(self):
        """Hide the biome data swap behind a staged fade/wipe so terrain never visibly pops."""
        bt = getattr(self, "biome_transition", None)
        if not bt or not bt.get("active"):
            return
        t = max(0.0, min(1.0, bt["t"] / max(0.01, bt["dur"])))
        out = min(1.0, t / 0.42)
        inn = min(1.0, max(0.0, (t - 0.46) / 0.54))
        darkness = out if t < 0.46 else (1.0 - inn)
        c = self.canvas
        # Coarse-to-solid pixel fade. The dense patterns read as a purposeful wipe rather than a popup.
        if darkness > 0.03:
            if darkness < 0.22:
                stip = "gray12"
            elif darkness < 0.45:
                stip = "gray25"
            elif darkness < 0.70:
                stip = "gray50"
            elif darkness < 0.92:
                stip = "gray75"
            else:
                stip = None
            kw = dict(fill="#03050b", outline="")
            if stip:
                kw["stipple"] = stip
            c.create_rectangle(0, 0, self.bw, self.bh, **kw)

        # Directional energy band sweeps across the playfield at the midpoint.
        if 0.18 < t < 0.84:
            u = (t - 0.18) / 0.66
            x = -90 + (self.bw + 180) * u
            st = STYLES[bt["to_biome"]]
            col = st["tcol"]
            c.create_rectangle(x - 18, 0, x + 18, self.bh, fill=col, stipple="gray50", outline="")
            c.create_line(x, 0, x, self.bh, fill=col, width=2)
            c.create_line(x - 26, 0, x - 26, self.bh, fill=col, width=1, dash=(3, 12))
            c.create_line(x + 26, 0, x + 26, self.bh, fill=col, width=1, dash=(3, 12))

        # Center announcement only during the actual transition, not a lingering popup.
        if 0.22 < t < 0.82:
            u = (t - 0.22) / 0.60
            fade = min(1.0, u * 2.0, (1.0 - u) * 2.0)
            st = STYLES[bt["to_biome"]]
            y = self.bh * 0.20
            c.create_text(self.bw // 2 + 2, y + 2, text=st["name"], fill=mix("#03050b", "#000000", 0.15),
                font=("Segoe UI", 25, "bold"))
            c.create_text(self.bw // 2, y, text=st["name"], fill=mix("#03050b", st["tcol"], fade),
                font=("Segoe UI", 25, "bold"))
            c.create_text(self.bw // 2, y + 34, text=st["sub"], fill=mix("#03050b", C_TEXT, fade * 0.85),
                font=("Segoe UI", 11, "italic"))

    def draw_biome_banner(self):
        t = self.banner_t
        if t <= 0 or self.state in ("ready", "paused") or getattr(self, "biome_transition", {}).get("active", False):
            return
        a = max(0.0, min(1.0, (1.15 - t) * 2, t))
        st = STYLES[self.banner_b]
        bg = self.pal[self.cur_biome]["floor"]
        c = self.canvas
        y = self.bh * 0.2
        c.create_text(self.bw // 2 + 2, y + 2, text=st["name"], fill=mix(bg, "#000000", a), font=("Segoe UI", 25, "bold"))
        c.create_text(self.bw // 2, y, text=st["name"], fill=mix(bg, st["tcol"], a), font=("Segoe UI", 25, "bold"))
        c.create_text(self.bw // 2, y + 34, text=st["sub"], fill=mix(bg, C_TEXT, a * 0.8), font=("Segoe UI", 11, "italic"))

    def bar(self, x, y, w, h, frac, col):
        c = self.canvas
        c.create_rectangle(x, y, x + w, y + h, fill="#05080f", outline="#2a4a80")
        if frac > 0:
            c.create_rectangle(x + 1, y + 1, x + 1 + (w - 2) * min(1.0, frac), y + h - 1, fill=col, outline="")

    def _buff_list(self):
        buffs = []
        if self.running:
            buffs.append("RUN")
        if self.buff_dmg > 0:
            buffs.append(f"DMG x1.5 {int(self.buff_dmg)}s")
        if self.buff_speed > 0:
            buffs.append(f"HASTE {int(self.buff_speed)}s")
        if self.buff_crit > 0:
            buffs.append(f"CRIT {int(self.buff_crit)}s")
        if self.buff_em > 0:
            buffs.append(f"MASTERY {int(self.buff_em)}s")
        if self.regen_t > 0:
            buffs.append(f"REGEN {int(self.regen_t)}s")
        if self.camo_t > 0:
            buffs.append(f"CAMO {self.camo_t:.0f}s")
        if self.coil_t > 0:
            buffs.append(f"COIL {self.coil_t:.0f}s")
        if self.bulwark_t > 0:
            buffs.append(f"BULWARK {self.bulwark_t:.0f}s")
        if self.heat_t > 0:
            buffs.append(f"HEAT {self.heat_t:.0f}s")
        return buffs

    def _pixel_panel(self, x0, y0, x1, y1, col):
        """Small low-cost pixel-art HUD frame; avoids font/UI widgets during gameplay."""
        c = self.canvas
        c.create_rectangle(x0, y0, x1, y1, fill="#050913", outline="#0e2642", width=2)
        c.create_rectangle(x0 + 4, y0 + 4, x1 - 4, y1 - 4, fill="#081224", outline=col, width=1)
        # stepped pixel corners
        c.create_rectangle(x0, y0, x0 + 14, y0 + 3, fill=col, outline="")
        c.create_rectangle(x0, y0, x0 + 3, y0 + 14, fill=col, outline="")
        c.create_rectangle(x1 - 14, y1 - 3, x1, y1, fill=col, outline="")
        c.create_rectangle(x1 - 3, y1 - 14, x1, y1, fill=col, outline="")
        c.create_rectangle(x0 + 12, y1 - 5, x0 + 56, y1 - 3, fill="#163553", outline="")

    def _pixel_bar(self, x, y, w, h, frac, col, blocks=24):
        c = self.canvas
        blocks = max(4, min(blocks, int(w / 7)))
        gap = 2
        bw = max(2, (w - (blocks - 1) * gap) / blocks)
        c.create_rectangle(x - 2, y - 2, x + w + 2, y + h + 2, fill="#02050b", outline="#1a3c5d")
        filled = int(round(max(0.0, min(1.0, frac)) * blocks))
        for i in range(blocks):
            xx = x + i * (bw + gap)
            c.create_rectangle(xx, y, xx + bw, y + h, fill=col if i < filled else "#0b1830", outline="")

    def draw_hud(self):
        sig = (self.bw, self.bh, int(self.hp), int(self.maxhp), int(100 * self.hp / max(1, self.maxhp)),
            int(self.shield), int(self.stam), int(self.maxstam), int(100 * self.xp / max(1, self.need())), self.level, self.points, self.skill_pts,
            self.cls["name"], self.run_class, len(self.snake), self.food_eaten, tuple(self._buff_list()),
            tuple(sorted(self.reson)) if self.reson else (), self.ammo, self.elem, self.skill_lv.get("basic", 1), self.skill_lv.get("v", 1),
            round(self.S["dmg"], 1), round(self.S["steal"], 1), round(self.S["energy_recharge"], 1))
        self.retained("hud", sig, self._hud_items)
        # Only a handful of dynamic pixels are redrawn every frame.
        c = self.canvas
        pulse = 0.5 + 0.5 * math.sin(self.time * 5.0)
        col = self.cls["col"]
        # The old top-right five-dot decoration is intentionally removed; it
        # competed with the map/resource stack and read like an unfinished widget.
        # Tiny status heartbeat / build-online marker.
        if self.tree_feedback_t > 0:
            c.create_rectangle(16, self.bh - 126, 20, self.bh - 122, fill=mix("#07101e", col, pulse), outline="")

    def _hud_items(self):
        c = self.canvas
        col = self.cls["col"]

        # Normal play uses the very top edge to maximize arena space. Boss fights
        # reserve a little headroom for the boss bar only while the boss UI is active.
        y = 48 if self.boss_active() else 8
        self._pixel_panel(16, y, 296, y + 70, col)
        self.draw_pix("snake_head", 42, y + 34, 3, dict(G=self.cls["pal"][0], H=self.cls["pal"][1]))
        self.ptext(66, y + 9, self.cls["name"].upper(), 2, "#ffffff", shadow=("#03060c", 1, 1))
        self.ptext(66, y + 25, self.cls["role"].upper(), 1, col)
        self.ptext(66, y + 41, f"LV {self.level}   LEN {len(self.snake):02d}", 1, C_TEXT)
        self.ptext(66, y + 54, f"P {self.points:02d}   S {self.skill_pts:02d}", 1, "#85a9d4")

        # BOTTOM LEFT = vitals only. No other panel is allowed in this footprint.
        by = self.bh - 106
        self._pixel_panel(16, by, 296, self.bh - 14, col)
        self.ptext(28, by + 9, "VITALS", 1, col)
        self.ptext(28, by + 21, f"HP {int(self.hp):03d}/{int(self.maxhp):03d}", 1, "#ffffff")
        self._pixel_bar(28, by + 34, 250, 7, self.hp / max(1, self.maxhp), "#e0465e", 28)
        self.ptext(28, by + 48, f"STAM {int(self.stam):03d}/{int(self.maxstam):03d}", 1, "#b8f5ae")
        self._pixel_bar(28, by + 60, 250, 5, self.stam / max(1, self.maxstam), "#70d48a", 28)
        self.ptext(28, by + 74, f"XP {int(self.xp):03d}/{int(self.need()):03d}", 1, "#d9bd57")

        # Dedicated status plate sits above the hotbar and never shares its footprint.
        buffs = self._buff_list()
        txt = " / ".join(buffs[:3]) if buffs else self.message_label.cget("text").upper()
        panel_w = min(420, max(250, self.bw - 610))
        panel_x = max(304, (self.bw - panel_w) / 2)
        panel_y = self.bh - 122
        self._pixel_panel(panel_x, panel_y, panel_x + panel_w, panel_y + 26, "#ffd34d" if buffs else "#274a73")
        self.ptext(panel_x + panel_w / 2, panel_y + 13, txt[:64], 1, "#ffd34d" if buffs else "#7ea7d5", anchor="c")

        # Dedicated signature plate on the lower-right keeps the hotbar center clear.
        vname = self.skill_tier("v")["short"].upper()
        sig_w = min(250, max(190, self.bw - 980))
        sig_x = self.bw - sig_w - 16
        self._pixel_panel(sig_x, self.bh - 122, self.bw - 16, self.bh - 92, self.cls["skill"]["color"])
        sig_key = self.settings.get("skill_slot_keys", {}).get("slot_1", "q").upper()
        self.ptext(sig_x + 10, self.bh - 113, f"{sig_key} //", 1, "#7b91ae")
        self.ptext(sig_x + 38, self.bh - 113, vname[:24], 1, self.cls["skill"]["color"])
        self.ptext(self.bw - 28, self.bh - 113, f"LV {self.skill_lv.get('v',1)}", 1, "#d7e6ff", anchor="e")

    def hotbar_entries(self):
        """Return movement/primary actions plus five slots on the active bar."""
        colors = {skill_id: color for skill_id, _key, _label, color in SKILLS}
        entries = [
            ("dash", "SHIFT", "DASH", colors["dash"]),
            ("strike", "LMB", self.skill_tier("basic")["short"].upper(), self.cls["basic"]["col"]),
        ]
        slot_keys = self.settings.get("skill_slot_keys", {})
        for slot_id, skill_id in zip(SKILL_SLOT_IDS,
                                     skill_ids_for_bar(self.run_class, getattr(self, "skill_set", 0))):
            key = str(slot_keys.get(slot_id, "?")).upper()
            label = self.skill_tier("v")["short"].upper() if skill_id == "class_skill" else SKILL_LABELS[skill_id]
            color = self.cls["skill"]["color"] if skill_id == "class_skill" else colors[skill_id]
            entries.append((skill_id, key, label, color))
        return entries

    def draw_hotbar(self):
        entries = self.hotbar_entries()
        sig = (self.bw, self.bh, tuple((k, key, label, self.cd[k] <= 0) for k, key, label, _col in entries),
               self.elem, tuple(self.unlocked), self.S["form_ranged"] > 0, self.cls["skill"]["name"],
               self.run_class, self.skill_lv["basic"], self.skill_lv["v"], getattr(self, "skill_set", 0),
               tuple(self.settings.get("skill_slot_keys", {}).items()), self.settings.get("skill_set_toggle_key", "x"))
        self.retained("hotbar", sig, self._hotbar_items)
        c = self.canvas
        count = len(entries)
        w = min(58, (self.bw - 220) / max(1, count))
        total = count * w
        x0 = max(294, self.bw / 2 - total / 2)
        y = self.bh - 66
        for i, (k, key, label, col) in enumerate(entries):
            cd = self.cd[k]
            if cd > 0:
                x = x0 + i * w
                frac = min(1.0, cd / self.cdmax[k])
                c.create_rectangle(x + 2, y + 44 * (1 - frac), x + w - 2, y + 44, fill="#000000", stipple="gray50", outline="")

    def _hotbar_items(self):
        c = self.canvas
        entries = self.hotbar_entries()
        count = len(entries)
        w = min(58, (self.bw - 220) / max(1, count))
        total = count * w
        x0 = max(294, self.bw / 2 - total / 2)
        y = self.bh - 66
        for i, (k, key, shown, col) in enumerate(entries):
            x = x0 + i * w
            cd = self.cd[k]
            active_col = col if cd <= 0 else "#28405d"
            c.create_rectangle(x + 2, y, x + w - 2, y + 40, fill="#060d1a", outline="#18324f", width=2)
            c.create_rectangle(x + 4, y + 2, x + w - 4, y + 5, fill=active_col, outline="")
            # Pixel diamond icon.
            cx = x + w / 2
            c.create_rectangle(cx - 3, y + 10, cx + 3, y + 16, fill=active_col, outline="")
            c.create_rectangle(cx - 1, y + 8, cx + 1, y + 18, fill=active_col, outline="")
            self.ptext(cx, y + 21, shown[:9].upper(), 1, active_col, anchor="c")
            self.ptext(cx, y + 32, key.upper(), 1, "#7c99bb", anchor="c")
            if cd > 0:
                frac = min(1.0, cd / max(0.01, self.cdmax[k]))
                c.create_rectangle(x + 4, y + 7, x + w - 4, y + 36, fill="#02050a", stipple="gray50", outline="")
                self.ptext(cx, y + 23, f"{cd:.1f}", 1, "#9ab0c9", anchor="c")

        # Element chips, selected element gets a pulsing pixel frame.
        es = ["pulse"] + self.unlocked
        ex0 = self.bw / 2 - len(es) * 24 / 2
        ey = y - 28
        toggle_key = str(self.settings.get("skill_set_toggle_key", "x")).upper()
        self.ptext(x0 + 4, ey + 12, f"SET {getattr(self, 'skill_set', 0) + 1} / {toggle_key}", 1,
                   "#7c99bb")
        for i, e in enumerate(es):
            x = ex0 + i * 24 + 12
            sel = e == self.elem
            ec = ECOL[e]
            r = 7 + (1.5 if sel else 0) * (0.5 + 0.5 * math.sin(self.time * 6))
            c.create_rectangle(x - r, ey - r, x + r, ey + r, fill="#060c18", outline=ec, width=2 if sel else 1)
            self.ptext(x, ey - 2, "*" if e == "pulse" else str(ELEMS.index(e) + 1), 1, ec, anchor="c")

    def draw_crosshair(self):
        """Aiming reticle: left click uses the class basic attack toward it."""
        if not self.aim_ok or self.state not in ("playing", "ready"):
            return
        c = self.canvas
        mx, my = self.mouse
        ranged = self.S["form_ranged"] > 0
        col = "#ff5da2" if ranged else self.cls["basic"]["col"]
        if ranged and self.state == "playing":
            hx, hy = self.center(*self.snake_points()[0])
            c.create_line(hx, hy, mx, my, fill=mix(C_BOARD, col, 0.35), dash=(3, 6))
        r = 11 + 2 * self.pulse(5)
        c.create_oval(mx - r, my - r, mx + r, my + r, outline=col, width=2)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            c.create_line(mx + dx * (r + 2), my + dy * (r + 2), mx + dx * (r + 8), my + dy * (r + 8), fill=col, width=2)
        c.create_rectangle(mx - 1, my - 1, mx + 1, my + 1, fill="#ffffff", outline="")

    def draw_hurt_flash(self):
        if self.hurt_flash <= 0:
            return
        a = min(1.0, self.hurt_flash / 0.4)
        for i in range(3):
            c = mix(C_BOARD, "#ff2040", a * (1 - i * 0.28))
            self.canvas.create_rectangle(i * 5 + 2, i * 5 + 2, self.bw - i * 5 - 2, self.bh - i * 5 - 2, outline=c, width=5)

    def draw_floats(self):
        c = self.canvas
        for x, y, text, col, t0 in self.floats:
            age = self.time - t0
            if not self.visible(x, y):
                continue
            cx, cy = self.center(x, y)
            c.create_text(cx, cy - age * 30, text=text, fill=col, font=("Segoe UI", 10, "bold"))

    def draw_scent(self):
        if self.scent_t <= 0:
            return
        c = self.canvas
        hx, hy = self.snake_points()[0]
        scx, scy = self.center(hx, hy)
        for x, y, col, label in self.scent:
            dx, dy = x - hx, y - hy
            dist = math.hypot(dx, dy)
            if dist < 0.1:
                continue
            ang = math.atan2(dy, dx)
            c.create_line(scx + math.cos(ang) * 30, scy + math.sin(ang) * 30, scx + math.cos(ang) * 70, scy + math.sin(ang) * 70,
                fill=col, width=3, arrow="last")
            c.create_text(scx + math.cos(ang) * 92, scy + math.sin(ang) * 92, text=f"{label} {int(dist)}", fill=col,
                font=("Segoe UI", 8, "bold"))
            if self.visible(x, y):
                ex, ey = self.center(x, y)
                c.create_oval(ex - 16, ey - 16, ex + 16, ey + 16, outline=col, width=2)

    def draw_clock(self):
        cb = self.cur_biome
        if cb == 0:
            label = "ETERNAL NIGHT"
        else:
            label = self.day_label()
        sun_up = cb != 0 and self.sun_elev > -0.02
        self.retained("clock", (self.bw, self.bh, cb, label, sun_up, self.sun_tw > 0.45, self.pal[cb]["floor"]), self._clock_items)

    def _clock_items(self):
        c = self.canvas
        cb = self.cur_biome
        x, y = self.bw - 110, self.bh - 24
        floor = self.pal[cb]["floor"]
        if cb == 0:
            label = "ETERNAL NIGHT"
        else:
            label = self.day_label()
        if cb == 0 or self.sun_elev <= -0.02:
            c.create_oval(x - 8, y - 8, x + 8, y + 8, fill="#dfe9ff", outline="")
            c.create_oval(x - 3, y - 10, x + 11, y + 4, fill=floor, outline="")
        else:
            sun = "#ff9a4a" if self.sun_tw > 0.45 else "#ffd34d"
            c.create_oval(x - 6, y - 6, x + 6, y + 6, fill=sun, outline="")
            for k in range(8):
                a = k * math.pi / 4
                c.create_line(x + 9 * math.cos(a), y + 9 * math.sin(a), x + 13 * math.cos(a), y + 13 * math.sin(a), fill=sun)
        c.create_text(x + 18, y, anchor="w", text=label, fill=mix(floor, "#ffffff", 0.75), font=("Segoe UI", 9, "bold"))

    def draw_overlay(self):
        if self.state == "paused":
            self.draw_pause_menu()
            return
        titles = {
            "ready": ("READY", "Press an arrow key / WASD to start    |    LEFT CLICK attacks    |    TAB opens your passive tree + skill tree - you have 1 point in each", C_TEXT),
            "failed": ("YOU DIED", "ENTER = respawn at last save point    |    N = new game    |    ESC = menu", "#ff6b8a"),
            "won": ("CORE DATA COLLECTED", "Press N to play again    |    ESC = menu", C_CYAN),
        }
        if self.state not in titles:
            return
        title, sub, color = titles[self.state]
        c = self.canvas
        c.create_rectangle(0, self.bh // 2 - 46, self.bw, self.bh // 2 + 46, fill=C_BOARD, stipple="gray50", outline="")
        c.create_text(self.bw // 2, self.bh // 2 - 12, text=title, fill=color, font=("Segoe UI", 20, "bold"))
        c.create_text(self.bw // 2, self.bh // 2 + 22, text=sub, fill=C_MUTED, font=("Segoe UI", 10))
