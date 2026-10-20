"""Menu state machine: main menu, class select, controls, settings, credits and pause."""
from ..data.classes import CLASSES, CLASS_ORDER
from ..audio import configure_audio, play_music, play_sound
from ..settings import save_settings

FULL_MENUS = ("menu", "classes", "controls", "settings", "credits")
MENU_STATES = FULL_MENUS + ("paused",)

SETTINGS_ROWS = [
    ("master_volume", "MASTER VOLUME", "Audio output"),
    ("music_volume", "MUSIC", "Background music"),
    ("sfx_volume", "SOUND FX", "Gameplay + UI sounds"),
    ("mute_audio", "MUTE AUDIO", "Silence all audio"),
    ("vfx_quality", "VFX QUALITY", "Low / Medium / High"),
    ("auto_quality", "AUTO QUALITY", "Adaptive performance"),
    ("screen_shake", "SCREEN SHAKE", "Combat camera shake"),
    ("damage_numbers", "DAMAGE NUMBERS", "Floating combat text"),
    ("fullscreen", "FULLSCREEN", "Window / fullscreen"),
    ("fps_cap", "FPS CAP", "30 / 60 / 90 / 120 / UNLIMITED"),
]

SETTINGS_HELP = [
    "LEFT / RIGHT changes the selected setting.",
    "MOUSE: click < or > beside a setting.",
    "AUTO QUALITY reduces VFX when the frame time rises.",
    "60 FPS is the recommended target. UNLIMITED follows the renderer as fast as it can.",
]

CREDITS_LINES = [
    ("TEAM", "Brent Kenneth Abrazaldo", "Developer / Game Creator"),
    ("TEAM", "Prof. Jay Vila", "Professor / Project Adviser"),
    ("TEAM", "Zac Villeno", "Co-Developer"),
    ("", "", ""),
    ("AUDIO", "Taisei Project", "SFX + BGM source; MIT-licensed project"),
    ("AUDIO", "Tuck V", "Taisei original soundtrack; CC BY 4.0"),
    ("AUDIO", "Touhou Pixel Dungeon: Reloaded", "Music + SFX source; GPLv3"),
    ("AUDIO", "Repair Terminal Team", "Trimming, normalization and original game-specific audio"),
    ("", "", ""),
    ("ART", "Majstek", "Touhou Mini 16x16 Pack; non-commercial license in bundled LICENSE.txt"),
    ("ART", "code farmer", "Touhou Pixel Characters; editable, non-resell terms per asset page"),
    ("ART", "Danmaku Shot_01", "Bullet sprite source credited; license was not identified in the source archive"),
    ("ART", "Touhou Project / ZUN", "Characters, themes and fan-work inspiration"),
    ("", "", ""),
    ("TECH", "Python + Tkinter", "Game runtime / UI"),
    ("TECH", "Optional pygame.mixer", "Audio mixing backend"),
    ("", "", ""),
    ("NOTICE", "Repair Terminal", "Unofficial Touhou-inspired fan project; not affiliated with ZUN / Team Shanghai Alice."),
    ("NOTICE", "Third-party licenses", "See bundled asset/license files and the project CREDITS.txt for full notices."),
]


class MenuMixin:
    def menu_items(self):
        """-> list of (action, label, sub-label) for the current list menu."""
        if self.state == "paused":
            return [
                ("resume", "RESUME", ""),
                ("tree", "SKILL TREE", "TAB"),
                ("controls", "CONTROLS", ""),
                ("settings", "SETTINGS", ""),
                ("credits", "CREDITS", ""),
                ("menu", "MAIN MENU", ""),
            ]
        items = []
        if self.state_alive():
            items.append(("continue", "CONTINUE", ""))
        items += [
            ("new", "NEW GAME", ""),
            ("class", "CLASS", CLASSES[self.pclass]["name"]),
            ("controls", "CONTROLS", ""),
            ("settings", "SETTINGS", ""),
            ("credits", "CREDITS", ""),
            ("quit", "QUIT", ""),
        ]
        return items

    def state_alive(self):
        return self.resume_state in ("playing", "ready", "paused")

    def go_menu(self):
        self.state = "menu"
        self.menu_sel = 0
        self.menu_t0 = self.time
        self.lmb_held = self.run_held = False
        play_music("menu", 0.55)

    def menu_activate(self, action):
        play_sound("menu_select")
        if action == "new":
            self.reset_game()
        elif action == "continue":
            self.state = self.resume_state if self.resume_state != "paused" else "playing"
            self.play_zone_music()
        elif action == "class":
            self.state = "classes"
            self.class_sel = CLASS_ORDER.index(self.pclass)
        elif action == "controls":
            self.menu_back = self.state
            self.state = "controls"
        elif action == "settings":
            self.menu_back = self.state
            self.state = "settings"
            self.settings_sel = 0
        elif action == "credits":
            self.menu_back = self.state
            self.state = "credits"
            self.credits_scroll = 0.0
        elif action == "quit":
            self.root.destroy()
        elif action == "resume":
            self.state = "playing"
        elif action == "tree":
            self.toggle_tree()
        elif action == "menu":
            self.resume_state = "paused"
            self.go_menu()
        self.menu_sel = 0

    def pick_class(self, idx):
        self.class_sel = idx
        self.pclass = CLASS_ORDER[idx]
        self.state = "menu"
        self.menu_sel = 0
        self.set_message(f"Class set to {CLASSES[self.pclass]['name']} - choose NEW GAME to play with it")

    def _settings_change(self, idx, step):
        key = SETTINGS_ROWS[idx][0]
        s = self.settings
        if key.endswith("_volume"):
            s[key] = max(0.0, min(1.0, round(float(s[key]) + 0.1 * step, 2)))
        elif key == "vfx_quality":
            s[key] = (int(s[key]) + step) % 3
        elif key == "fps_cap":
            caps = [30, 60, 90, 120, 0]
            cur = int(s.get(key, 60))
            try:
                pos = caps.index(cur)
            except ValueError:
                pos = 1
            s[key] = caps[(pos + (1 if step >= 0 else -1)) % len(caps)]
        else:
            s[key] = not bool(s[key]) if step else bool(s[key])
        save_settings(s)
        self.apply_user_settings()
        play_sound("menu_move", volume=0.7, min_interval=0.02)

    def _settings_toggle(self, idx):
        key = SETTINGS_ROWS[idx][0]
        if key.endswith("_volume"):
            self._settings_change(idx, 1)
        else:
            self._settings_change(idx, 1)

    def menu_key(self, key):
        """Keyboard handling for every menu state. Returns True when the key was consumed."""
        st = self.state
        if st == "controls":
            if key in ("escape", "return", "space", "backspace", "enter", "kp_enter"):
                self.state = self.menu_back
            return True
        if st == "settings":
            n = len(SETTINGS_ROWS)
            if key in ("up", "w"):
                self.settings_sel = (self.settings_sel - 1) % n
                play_sound("menu_move")
            elif key in ("down", "s"):
                self.settings_sel = (self.settings_sel + 1) % n
                play_sound("menu_move")
            elif key in ("left", "a"):
                self._settings_change(self.settings_sel, -1)
            elif key in ("right", "d"):
                self._settings_change(self.settings_sel, 1)
            elif key in ("return", "space", "enter", "kp_enter"):
                self._settings_toggle(self.settings_sel)
            elif key in ("escape", "backspace"):
                self.state = self.menu_back
            return True
        if st == "credits":
            if key in ("up", "w"):
                self.credits_scroll = max(0.0, self.credits_scroll - 34)
            elif key in ("down", "s"):
                self.credits_scroll += 34
            elif key in ("pageup",):
                self.credits_scroll = max(0.0, self.credits_scroll - 180)
            elif key in ("pagedown",):
                self.credits_scroll += 180
            elif key in ("escape", "return", "space", "backspace", "enter", "kp_enter"):
                self.state = self.menu_back
            return True
        if st == "classes":
            n = len(CLASS_ORDER)
            if key in ("left", "a"):
                self.class_sel = (self.class_sel - 1) % n
            elif key in ("right", "d"):
                self.class_sel = (self.class_sel + 1) % n
            elif key in ("return", "space", "enter", "kp_enter"):
                self.pick_class(self.class_sel)
            elif key in ("escape", "backspace"):
                self.state = "menu"
            return True
        items = self.menu_items()
        if key in ("up", "w"):
            play_sound("menu_move")
            self.menu_sel = (self.menu_sel - 1) % len(items)
        elif key in ("down", "s"):
            play_sound("menu_move")
            self.menu_sel = (self.menu_sel + 1) % len(items)
        elif key in ("return", "space", "enter", "kp_enter"):
            self.menu_activate(items[self.menu_sel][0])
        elif key in ("escape", "p") and st == "paused":
            self.state = "playing"
        elif key == "escape" and st == "menu" and self.in_game and self.state_alive():
            self.menu_activate("continue")
        return True

    def menu_click(self, x, y):
        for x1, y1, x2, y2, kind, idx in self.menu_rects:
            if x1 <= x <= x2 and y1 <= y <= y2:
                if kind == "item":
                    self.menu_sel = idx
                    self.menu_activate(self.menu_items()[idx][0])
                elif kind == "class":
                    self.pick_class(idx)
                elif kind == "back":
                    self.state = self.menu_back
                elif kind == "settings_prev":
                    self.settings_sel = idx
                    self._settings_change(idx, -1)
                elif kind == "settings_next":
                    self.settings_sel = idx
                    self._settings_change(idx, 1)
                return

    def menu_hover(self, x, y):
        for x1, y1, x2, y2, kind, idx in self.menu_rects:
            if x1 <= x <= x2 and y1 <= y <= y2:
                if kind == "item":
                    self.menu_sel = idx
                elif kind == "class":
                    self.class_sel = idx
                elif kind in ("settings_prev", "settings_next"):
                    self.settings_sel = idx
                return
