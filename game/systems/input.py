"""Keyboard and mouse handlers.

Mouse: LEFT = attack (aimed), RIGHT (hold) = run, WHEEL = switch element.
Keys: WASD/arrows move - SHIFT dash - Q/E/R/F/C active skill slots - X switch skill set - 1-9 element - TAB trees - ESC pause.
"""
from ..data.elements import ELEMS
from ..data.tree_nodes import TREE
from ..data.keybinds import (skill_for_key, SKILL_ACTION_METHODS, SKILL_LABELS,
    is_skill_unlocked, skill_unlock_level)
from .menu import FULL_MENUS, MENU_STATES
from ..audio import play_sound


class InputMixin:
    def on_key_release(self, event):
        getattr(self, "held_keys", set()).discard(event.keysym.lower())

    # ---- mouse
    def on_press(self, e):
        self.mouse, self.aim_ok = (e.x, e.y), True
        if self.state in MENU_STATES:
            self.menu_click(e.x, e.y)
            return
        self.press = (e.x, e.y)
        self.pan0 = list(self.tree_pan)
        self._tree_drag_last = (e.x, e.y)
        self.moved = False
        if self.state == "playing":
            self.lmb_held = True
            self.primary_attack()

    def on_drag(self, e):
        self.mouse, self.aim_ok = (e.x, e.y), True
        if self.state == "tree" and self.press:
            dx, dy = e.x - self.press[0], e.y - self.press[1]
            if abs(dx) + abs(dy) > 4:
                self.moved = True
            last = getattr(self, "_tree_drag_last", self.press)
            ddx, ddy = e.x - last[0], e.y - last[1]
            self.tree_pan = [self.pan0[0] + dx, self.pan0[1] + dy]
            if self.moved and (ddx or ddy):
                tag = "skill_graph" if self.tree_tab == "skill" else "passive_graph"
                self.canvas.move(tag, ddx, ddy)
            self._tree_drag_last = (e.x, e.y)

    def on_release(self, e):
        self.lmb_held = False
        if self.state != "tree" or self.moved:
            return
        if self.tree_tab_click(e.x, e.y):
            return
        if self.tree_tab == "skill":
            self.skill_click(e.x, e.y)
            self.update_hud()
            return
        nid = self.node_at(e.x, e.y)
        if nid and self.can_alloc(nid):
            play_sound("node_alloc", volume=0.7)
            self.alloc.add(nid)
            self.points -= 1
            self.recompute()
            node = TREE[nid]
            if hasattr(self, "_tree_feedback"):
                self._tree_feedback("PASSIVE", node, True)
            self.update_hud()

    def on_rclick(self, e):
        if self.state != "tree":
            return
        if self.tree_tab == "skill":
            self.skill_click(e.x, e.y, refund=True)
            return
        nid = self.node_at(e.x, e.y)
        if nid and self.can_refund(nid):
            play_sound("debuff", volume=0.5)
            self.alloc.discard(nid)
            self.points += 1
            self.recompute()
            node = TREE[nid]
            if hasattr(self, "_tree_feedback"):
                self._tree_feedback("PASSIVE", node, False)
            self.update_hud()

    def on_rpress(self, e):
        if self.state == "tree":
            self.on_rclick(e)
        elif self.state not in MENU_STATES:
            self.run_held = True

    def on_rrelease(self, e):
        self.run_held = False

    def on_motion(self, e):
        self.mouse, self.aim_ok = (e.x, e.y), True
        if self.state in MENU_STATES:
            self.menu_hover(e.x, e.y)
            return
        if self.state == "tree":
            # Restore the old, familiar pointer behavior: hand over clickable
            # tabs/buttons/nodes, arrow over the canvas, never a plus crosshair.
            hand = False
            for x0,y0,x1,y1,_action in getattr(self, "tree_tab_rects", []):
                if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                    hand = True; break
            if not hand:
                for x0,y0,x1,y1,_action in getattr(self, "tree_control_rects", []):
                    if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                        hand = True; break
            if not hand:
                if self.tree_tab == "skill":
                    for x0,y0,x1,y1,nid in (self._skill_hitboxes() if hasattr(self, "_skill_hitboxes") else getattr(self, "skill_hits", [])):
                        if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                            hand = True; break
                else:
                    hand = self.node_at(e.x, e.y) is not None
            self._tree_cursor = "hand2" if hand else "arrow"
            return

    def on_wheel(self, e):
        up = getattr(e, "delta", 0) > 0 or getattr(e, "num", 0) == 4
        if self.state == "credits":
            self.credits_scroll = max(0.0, self.credits_scroll - (70 if up else -70))
            return
        if self.state == "settings":
            self._settings_change(self.settings_sel, 1 if up else -1)
            return
        if self.state == "tree":
            self.tree_zoom = max(0.28, min(1.55, self.tree_zoom * (1.1 if up else 0.9)))
        elif self.state in ("playing", "ready"):
            self.cycle_element(-1 if up else 1)

    def cycle_element(self, step):
        opts = ["pulse"] + self.unlocked
        self.elem = opts[(opts.index(self.elem) + step) % len(opts)]

    # ---- keyboard
    def on_key_press(self, event):
        key = event.keysym.lower()
        was_held = key in getattr(self, "held_keys", set())
        if hasattr(self, "held_keys"):
            self.held_keys.add(key)
        directions = {"up": (0, -1), "w": (0, -1), "down": (0, 1), "s": (0, 1),
            "left": (-1, 0), "a": (-1, 0), "right": (1, 0), "d": (1, 0)}
        if key == "f11":
            self.fullscreen = not self.fullscreen
            self.root.attributes("-fullscreen", self.fullscreen)
            return
        if self.state in MENU_STATES:
            self.menu_key(key)
            return
        if key == "escape":
            if self.state == "tree":
                self.toggle_tree()
            elif self.state == "playing":
                self.pause()
            elif self.state in ("ready", "failed", "won"):
                self.resume_state = self.state if self.state == "ready" else "dead"
                self.go_menu()
            return
        if key == "tab" or (key == "k" and self.state != "tree"):
            self.toggle_tree()
            return
        if key == "n":
            self.reset_game()
            return
        if self.state == "failed":
            if key in ("return", "r", "space", "enter", "kp_enter"):
                self.respawn()
            return
        if self.state == "tree":
            if key in ("1", "p"):
                self.set_tree_tab("passive")
            elif key in ("2", "s"):
                self.set_tree_tab("skill")
            elif key == "h":
                self.tree_control("sidebar")
            elif key == "j":
                self.tree_control("stats")
            elif key == "k":
                self.tree_control("keystones")
            elif key == "l":
                self.tree_control("live")
            elif key == "f":
                self.tree_control("fit")
            elif key == "home":
                self.tree_control("fit")
            self.update_hud()
            return
        if key == "m":
            self.show_minimap = not self.show_minimap
            return
        if key == "p" and self.state == "playing":
            self.pause()
            return
        if key == "space":
            self.shoot()
            return
        if key in ("shift_l", "shift_r"):
            self.dash()
            return
        toggle_key = str(self.settings.get("skill_set_toggle_key", "x")).lower()
        if key == toggle_key:
            if was_held:
                return
            self.skill_set = 1 - int(getattr(self, "skill_set", 0))
            if hasattr(self, "_ret"):
                self._ret.pop("hotbar", None)
            self.set_message(f"SKILL SET {self.skill_set + 1} ACTIVE")
            self.update_hud()
            return
        if key in ("bracketleft", "bracketright"):
            self.cycle_element(1 if key == "bracketright" else -1)
            return
        if key.isdigit() and key != "0":
            idx = int(key) - 1
            if idx < len(ELEMS) and ELEMS[idx] in self.unlocked:
                self.elem = ELEMS[idx]
            return
        slot_keys = self.settings.get("skill_slot_keys", {})
        skill_id = skill_for_key(self.run_class, getattr(self, "skill_set", 0), slot_keys, key)
        action_name = SKILL_ACTION_METHODS.get(skill_id)
        if action_name:
            if not is_skill_unlocked(self.run_class, skill_id, self.level):
                required = skill_unlock_level(self.run_class, skill_id)
                self.set_message(f"{SKILL_LABELS.get(skill_id, skill_id).upper()} unlocks at Level {required}")
                return
            getattr(self, action_name)()
            return
        requested = directions.get(key)
        if not requested or self.state in ("failed", "won", "paused"):
            return
        last = self.queue[-1] if self.queue else self.direction
        if requested == (-last[0], -last[1]) and self.blocked and not self.queue and self.state == "playing":
            self.reverse_snake()                 # blocked: flip the snake around instead of dying
            return
        if requested != last and requested != (-last[0], -last[1]) and len(self.queue) < 2:
            self.queue.append(requested)
        if self.state == "ready" and (self.queue or requested == self.direction):
            self.state = "playing"
            self.in_game = True
            self.acc = self.step_s()
            self.set_message("Defeat the 4 guardians in their dungeons, then challenge the Shrine Maiden    |    LMB attack")

    def pause(self):
        self.state = "paused"
        self.menu_sel = 0
        self.lmb_held = self.run_held = False
