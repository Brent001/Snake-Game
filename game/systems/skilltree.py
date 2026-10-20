"""Tree logic: the PASSIVE TREE (class constellations, class core starts active) and the branching SKILL TREE."""
from collections import deque

from ..audio import play_sound
from ..data.tree_nodes import ADJ, TREE, nodes_for_class, TREE_DEFS, describe
from ..data.active_skill_tree import (SKILL_NODES, SKILL_ADJ, SKILL_DEFS as ACTIVE_SKILL_DEFS,
                                       LINE_ALIASES, canonical_line, skill_nodes_for_class, skill_nodes_for_line,
                                       skill_level, current_node as current_skill_node)
from ..data.skills import SKILLS


class SkillTreeMixin:
    def toggle_tree(self):
        if self.state == "tree":
            play_sound("ui_close", volume=0.7)
            self.state = self.tree_prev
        elif self.state in ("ready", "playing", "paused"):
            play_sound("ui_open", volume=0.7)
            self.tree_prev = self.state
            self.state = "tree"
            self.run_held = False
            self.running = False
            # Start with the graph clean; optional side sections stay collapsed
            # until the player explicitly opens them.
            self.tree_pan = [0.0, 0.0]
            self.tree_zoom = 0.55 if self.tree_tab == "passive" else 0.68
            # Preserve sidebar/section preferences between openings.
            if not hasattr(self, "tree_sidebar_collapsed"):
                self.tree_sidebar_collapsed = False
            if not hasattr(self, "tree_show_keystones"):
                self.tree_show_keystones = False
            if not hasattr(self, "tree_show_stats"):
                self.tree_show_stats = False
            if not hasattr(self, "tree_show_live"):
                self.tree_show_live = False
            if hasattr(self, "_tree_fit_view"):
                self._tree_fit_view(self.tree_tab)

    def class_tree_ids(self):
        return nodes_for_class(self.run_class)

    def node_is_active_class(self, nid):
        return nid in self.class_tree_ids()

    def passive_core_id(self):
        return f"{self.run_class}:core"

    def can_alloc(self, nid):
        if nid not in TREE or not self.node_is_active_class(nid):
            return False
        if nid in self.alloc or self.points <= 0:
            return False
        n = TREE[nid]
        req = n.get("class_req")
        if req and req != self.run_class:
            return False
        if not any(neighbour in self.alloc for neighbour in ADJ[nid]):
            return False
        # Large keystones are doctrine choices: only one class-defining capstone can be owned.
        group = n.get("choice_group")
        if group:
            for aid in self.alloc:
                if aid != nid and TREE.get(aid, {}).get("choice_group") == group:
                    return False
        return True

    def can_refund(self, nid):
        core = self.passive_core_id()
        if nid == core or nid not in self.alloc or not self.node_is_active_class(nid):
            return False
        rest = self.alloc - {nid}
        seen, queue = {core}, deque([core])
        while queue:
            cur = queue.popleft()
            for nxt in ADJ[cur]:
                if nxt in rest and nxt not in seen and self.node_is_active_class(nxt):
                    seen.add(nxt)
                    queue.append(nxt)
        return rest <= seen

    def tree_xy(self, n):
        z = self.tree_zoom
        side = self._tree_side_width() if hasattr(self, "_tree_side_width") else 48
        center_x = side + 6 + max(420, self.bw - side - 12) / 2
        return center_x + self.tree_pan[0] + n["x"] * z, self.bh / 2 + self.tree_pan[1] + n["y"] * z

    def tree_control(self, action):
        if action == "sidebar":
            self.tree_sidebar_collapsed = not self.tree_sidebar_collapsed
        elif action == "keystones":
            self.tree_show_keystones = not self.tree_show_keystones
        elif action == "stats":
            self.tree_show_stats = not self.tree_show_stats
        elif action == "live":
            self.tree_show_live = not self.tree_show_live
        elif action == "fit":
            if hasattr(self, "_tree_fit_view"):
                self._tree_fit_view(self.tree_tab)
            self._passive_tree_static_key = None
            self._skill_tree_static_key = None
            return True
        elif isinstance(action, str) and action.startswith("keystone_focus:"):
            nid = action.split(":", 1)[1]
            if nid in TREE:
                self.tree_show_keystones = True
                self.tree_zoom = max(0.34, min(0.90, self.tree_zoom))
                n = TREE[nid]
                self.tree_pan = [-n["x"] * self.tree_zoom, -n["y"] * self.tree_zoom]
                self._passive_tree_static_key = None
            return True
        else:
            return False
        # Section toggles do not disturb the graph. Sidebar width does, so refit
        # after that change to keep every outer node visible.
        if action == "sidebar" and hasattr(self, "_tree_fit_view"):
            self._tree_fit_view(self.tree_tab)
        return True

    def tree_tab_click(self, x, y):
        """Handle tree controls and tabs; controls win if a hitbox ever touches."""
        for x0, y0, x1, y1, action in getattr(self, "tree_control_rects", []):
            if x0 <= x <= x1 and y0 <= y <= y1:
                return self.tree_control(action)
        for x0, y0, x1, y1, tab in getattr(self, "tree_tab_rects", []):
            if x0 <= x <= x1 and y0 <= y <= y1:
                self.set_tree_tab(tab)
                return True
        return False

    def node_at(self, mx, my):
        # Cache hit-test ordering; mouse movement should not sort the full tree.
        cache_key = (self.run_class,)
        if getattr(self, "_passive_hit_order_key", None) != cache_key:
            ordered = list(self.class_tree_ids())
            ordered.sort(key=lambda nid: 0 if TREE[nid]["kind"] == "k" else 1)
            self._passive_hit_order = ordered
            self._passive_hit_order_key = cache_key
        else:
            ordered = self._passive_hit_order
        for nid in ordered:
            n = TREE[nid]
            x, y = self.tree_xy(n)
            r = {"c": 23, "g": 13, "m": 8, "n": 12, "a": 15, "j": 13, "k": 19}[n["kind"]] * self.tree_zoom + 6
            if (mx - x) ** 2 + (my - y) ** 2 <= r * r:
                return nid
        return None

    def tree_choice_state(self):
        selected = None
        for nid in self.alloc:
            if TREE.get(nid, {}).get("choice_group") == "keystone":
                selected = nid
                break
        return selected

    def tree_class_info(self):
        return TREE_DEFS[self.run_class]

    # ---- branching ACTIVE SKILL TREE -------------------------------------
    def set_tree_tab(self, tab):
        if tab in ("passive", "skill") and tab != self.tree_tab:
            self.tree_tab = tab
            # Each constellation gets its own clean starting view.  The user can
            # then pan/zoom just like the passive tree.
            self.tree_pan = [0.0, 0.0]
            self.tree_zoom = 0.55 if tab == "passive" else 0.68
            self._passive_tree_static_key = None
            self._skill_tree_static_key = None
            if hasattr(self, "_tree_fit_view"):
                self._tree_fit_view(tab)
            play_sound("ui_open", volume=0.5)

    def skill_nodes_for_class(self):
        return skill_nodes_for_class(self.run_class)

    def skill_nodes_for_line(self, line):
        return skill_nodes_for_line(self.run_class, line)

    def skill_line_defs(self):
        return ACTIVE_SKILL_DEFS[self.run_class]

    def skill_lines(self):
        """Return every hotbar skill, not only the old LMB/V pair."""
        defs = ACTIVE_SKILL_DEFS[self.run_class]
        out = []
        for key, slot, _display, _col in SKILLS:
            d = defs[key]
            out.append(dict(id=key, slot=d["slot"], title=d["name"] + " TREE",
                            name=d["name"], short=d["name"], col=d["color"], desc=d["desc"]))
        return out

    def skill_tier(self, line_id):
        """Legacy HUD-facing summary; aliases basic/v map to strike/class_skill."""
        line_id = canonical_line(line_id)
        defs = ACTIVE_SKILL_DEFS[self.run_class][line_id]
        cur = current_skill_node(self.run_class, self.skill_alloc, line_id)
        lv = skill_level(self.run_class, self.skill_alloc, line_id)
        return dict(name=cur["name"], short=cur["name"], desc=cur["desc"], level=lv, stats=cur["stats"])

    def skill_level(self, line_id):
        return skill_level(self.run_class, self.skill_alloc, line_id)

    def can_skill_alloc(self, nid):
        if nid not in SKILL_NODES or not nid.startswith(self.run_class + ":"):
            return False
        if nid in self.skill_alloc or self.skill_pts <= 0:
            return False
        n = SKILL_NODES[nid]
        if not any(nb in self.skill_alloc for nb in SKILL_ADJ[nid]):
            return False
        group = n.get("choice")
        if group:
            for aid in self.skill_alloc:
                if SKILL_NODES.get(aid, {}).get("choice") == group and aid != nid:
                    return False
        return True

    def can_skill_refund(self, nid):
        if nid not in self.skill_alloc:
            return False
        n = SKILL_NODES[nid]
        if n["kind"] == "r":
            return False
        rest = self.skill_alloc - {nid}
        seen = {rid for rid in self.skill_nodes_for_class() if SKILL_NODES[rid]["kind"] == "r"}
        queue = list(seen)
        while queue:
            cur = queue.pop()
            for nxt in SKILL_ADJ[cur]:
                if nxt in rest and nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        return rest <= seen

    def _tree_feedback(self, title, node, allocated=True):
        stats = node.get("stats", {}) if node else {}
        pieces = describe(stats)[:3] if stats else []
        status = "ONLINE" if allocated else "REFUNDED"
        detail = "  •  ".join(pieces) if pieces else node.get("desc", "Combat effect updated")[:72]
        self.tree_feedback = f"{title}  [{status}]  •  {detail}"
        self.tree_feedback_t = 3.5
        self.set_message(self.tree_feedback)
        try:
            hx, hy = self.snake_points()[0]
            self.float_text(hx, hy - 1.0, status + "  " + node.get("name", "NODE"), self.cls["col"] if allocated else "#9fb2c8")
        except Exception:
            pass

    def skill_click(self, x, y, refund=False):
        """Allocate/refund a branching skill node. Returns True if the graph changed."""
        hitboxes = self._skill_hitboxes() if hasattr(self, "_skill_hitboxes") else self.skill_hits
        for x0, y0, x1, y1, nid in hitboxes:
            if x0 <= x <= x1 and y0 <= y <= y1:
                node = SKILL_NODES[nid]
                if not refund and self.can_skill_alloc(nid):
                    self.skill_alloc.add(nid)
                    self.skill_pts -= 1
                    self.recompute()
                    self._tree_feedback(f"{ACTIVE_SKILL_DEFS[self.run_class][node['line']]['name']} UPGRADE", node, True)
                    play_sound("node_alloc", volume=0.8)
                    return True
                if refund and self.can_skill_refund(nid):
                    self.skill_alloc.remove(nid)
                    self.skill_pts += 1
                    self.recompute()
                    self._tree_feedback(f"{ACTIVE_SKILL_DEFS[self.run_class][node['line']]['name']} UPGRADE", node, False)
                    play_sound("debuff", volume=0.5)
                    return True
        return False

