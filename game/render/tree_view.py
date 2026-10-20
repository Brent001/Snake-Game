"""Readable passive + full active-skill tree renderer.

The passive tree is a large character-stat constellation. The active SKILL TREE is
one overview containing every hotbar skill, each with its own branching build.
The renderer intentionally hides most labels until interaction/zoom so lines and
nodes never turn into a wall of text.
"""
import math
import textwrap

from ..config import C_CYAN, C_GOLD, C_MUTED, C_TEXT
from ..data.elements import ECOL
from ..data.tree_nodes import ADJ, EDGES, KIND_NAME, TREE, TREE_DEFS, describe
from ..data.active_skill_tree import SKILL_ADJ, SKILL_DEFS as ACTIVE_SKILL_DEFS, SKILL_EDGES, SKILL_NODES
from ..data.skills import SKILLS
from ..utils import mix
from .ambient import STARS


class TreeViewMixin:
    # ------------------------------------------------------------------ shared UI
    def _basic_attack_line(self):
        cid = self.run_class
        if cid == "viper":
            p = self.skill_profile("fang")
            return f"{p['reach']:.1f} reach  •  {p['venom']:.0f}+ venom DPS  •  x{p['targets']} targets"
        if cid == "python":
            p = self.skill_profile("slam")
            return f"{p['radius']:.1f} radius  •  {p['stun']:.1f}s stun  •  {p['knock']:.0f} force"
        if cid == "mamba":
            p = self.skill_profile("volt")
            return f"{p['reach']:.1f} reach  •  {math.degrees(p['arc'])*2:.0f}° arc  •  {p['arcs']} arcs"
        p = self.skill_profile("bolt")
        return f"{p['count']} bolts  •  {p['pierce']} pierce  •  {p['mul']:.2f}x damage"

    def _tree_side_width(self):
        if getattr(self, "tree_sidebar_collapsed", False):
            return 48
        # Keep the inspector/sidebar narrow enough that the graph owns most of
        # the screen, while still leaving room for the 12-skill index.
        return min(282, max(264, self.bw * 0.205))

    # The passive tree is deliberately shaped like a themed constellation instead
    # of an undirected spider-web. Eight outer districts form a creature/sigil
    # silhouette and the important route is carried by the bright backbone.
    # Cross-links still exist mechanically, but are de-emphasized until hovered.
    _PASSIVE_BODY = {
        # Cubic Bezier control points for the creature's backbone. The 8 passive
        # districts are cross-sections (scales/ribs) along this backbone.
        "viper": [(-500,-170),(-250,-500),(180,480),(500,110)],
        "python": [(-500,-120),(-300,-390),(190,390),(500,80)],
        "cobra": [(-500,-185),(-330,-520),(45,-500),(500,120)],
        "mamba": [(-500,-180),(-250,430),(190,-430),(500,145)],
    }

    _PASSIVE_AFFINITY = {
        "viper": ["dendro","hydro","abyss","dendro","cryo","anemo","hydro","abyss","dendro"],
        "python": ["geo","pyro","geo","hydro","geo","pyro","cryo","geo","hydro"],
        "cobra": ["dendro","hydro","cryo","electro","dendro","hydro","abyss","electro","dendro"],
        "mamba": ["electro","anemo","abyss","electro","pyro","anemo","hydro","electro","abyss"],
    }

    def _passive_district(self, nid):
        if not isinstance(nid, str):
            return None, None
        import re
        m = re.match(r"[^:]+:f:s(\d+)_(\d+)$", nid)
        if m:
            return int(m.group(1)), int(m.group(2))
        m = re.match(r"[^:]+:f:sat(\d+)_(?:a|n)$", nid)
        if m:
            return int(m.group(1)), 3.5 if nid.endswith("_a") else 2.7
        return None, None

    def _passive_world(self, n):
        nid = n.get("_id", "")
        cid = self.run_class
        district, stage = self._passive_district(nid)
        if district is not None:
            p0,p1,p2,p3=self._PASSIVE_BODY.get(cid,self._PASSIVE_BODY["viper"])
            # Stage is the longitudinal coordinate; district is the cross-section.
            t=max(0.0,min(1.0,(stage+0.35)/9.35))
            u=1.0-t
            bx=u*u*u*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t*t*t*p3[0]
            by=u*u*u*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t*t*t*p3[1]
            tx=3*u*u*(p1[0]-p0[0])+6*u*t*(p2[0]-p1[0])+3*t*t*(p3[0]-p2[0])
            ty=3*u*u*(p1[1]-p0[1])+6*u*t*(p2[1]-p1[1])+3*t*t*(p3[1]-p2[1])
            ln=max(1.0,math.hypot(tx,ty)); nx,ny=-ty/ln,tx/ln
            width={"viper":31,"python":38,"cobra":43 if stage<3 else 29,"mamba":29}.get(cid,31)
            # Subtle taper makes the outer stages read like a head-to-tail creature.
            taper=1.0 - (stage/18.0)
            offset=(district-3.5)*width*taper
            return bx+nx*offset, by+ny*offset

        # Existing core clusters become recognizable features around the head/body.
        if nid.endswith(":core"):
            return 0.0, 0.0
        import re
        m = re.match(r"[^:]+:b(\d+):(\d+)$", nid)
        if m:
            bi, si = int(m.group(1)), int(m.group(2))
            if bi == 0:
                return -145 - si*48, -100 - (si%2)*34
            if bi == 1:
                return 145 + si*48, -100 - (si%2)*34
            return -90 + si*60, 120 + si*43
        m = re.match(r"[^:]+:m:(\d+)$", nid)
        if m:
            mi=int(m.group(1)); return [(-205,-12),(205,-12),(-110,245),(110,245)][mi%4]
        m = re.match(r"[^:]+:x:cluster(\d+)_", nid)
        if m:
            i=int(m.group(1))
            spots=[(-375,-210),(375,-210),(-385,210),(385,210),(0,-315)]
            return spots[i%len(spots)]
        m = re.match(r"[^:]+:f:ks(\d+)$", nid)
        if m:
            i=int(m.group(1))
            p0,p1,p2,p3=self._PASSIVE_BODY.get(cid,self._PASSIVE_BODY["viper"])
            if i<2:
                bx,by=p0; tx,ty=p1[0]-p0[0],p1[1]-p0[1]
            else:
                bx,by=p3; tx,ty=p3[0]-p2[0],p3[1]-p2[1]
            ln=max(1.0,math.hypot(tx,ty)); nx,ny=-ty/ln,tx/ln
            side=(1 if i%2==0 else -1)*(125 if i<2 else 115)
            return bx+nx*side,by+ny*side
        return n["x"] * 0.70, n["y"] * 0.42

    def _tree_fit_view(self, tab=None):
        """Fit the active tree inside the visible graph area and center it.

        The passive tree intentionally has a lot of nodes, so the default view
        should never start zoomed so far in that outer clusters are clipped.
        The fit also recenters after collapsing the sidebar.
        """
        tab = tab or self.tree_tab
        side = self._tree_side_width()
        tree_left = side + 8
        tree_w = max(420, self.bw - tree_left - 10)
        if tab == "passive":
            pts = [self._passive_world(TREE[nid]) for nid in self.class_tree_ids() if nid in TREE]
            pad_x, pad_y = 62.0, 72.0
            min_z, max_z = 0.38, 0.66
            extra_top = 92.0
        else:
            pts = [self._skill_world(SKILL_NODES[nid])
                   for nid in SKILL_NODES if nid.startswith(self.run_class + ":")]
            pad_x, pad_y = 72.0, 60.0
            min_z, max_z = 0.46, 0.92
            extra_top = 82.0
        if not pts:
            self.tree_zoom = 0.55 if tab == "passive" else 0.68
            self.tree_pan = [0.0, 0.0]
            return
        if tab == "passive":
            minx = min(p[0] for p in pts) - pad_x
            maxx = max(p[0] for p in pts) + pad_x
            miny = min(p[1] for p in pts) - pad_y
            maxy = max(p[1] for p in pts) + pad_y
        else:
            minx = min(p[0] for p in pts) - pad_x
            maxx = max(p[0] for p in pts) + pad_x
            miny = min(p[1] for p in pts) - pad_y
            maxy = max(p[1] for p in pts) + pad_y
        avail_w = max(360.0, tree_w - 24.0)
        avail_h = max(300.0, self.bh - extra_top - 18.0)
        z = min(avail_w / max(1.0, maxx - minx), avail_h / max(1.0, maxy - miny)) * 0.96
        z = max(min_z, min(max_z, z))
        cx = (minx + maxx) * 0.5
        cy = (miny + maxy) * 0.5
        # tree_xy adds pan in screen pixels, therefore center the world bbox by
        # moving its midpoint back to the graph origin.
        self.tree_zoom = z
        self.tree_pan = [-cx * z, -cy * z]

    def _tree_node_color(self, n, fallback):
        elem = n.get("elem")
        if elem and elem in ECOL:
            return ECOL[elem]
        cid = self.run_class
        nid = n.get("_id", "")
        district, _stage = self._passive_district(nid)
        if district is not None:
            aff = self._PASSIVE_AFFINITY.get(cid, self._PASSIVE_AFFINITY["viper"])[district % len(self._PASSIVE_AFFINITY.get(cid, self._PASSIVE_AFFINITY["viper"]))]
            return ECOL.get(aff, fallback)
        branch = str(n.get("branch", ""))
        tokens = {
            "TOXIC": "dendro", "SILENT": "abyss", "PLAGUE": "hydro",
            "COLOSSUS": "geo", "BASTION": "geo", "CONSTRICTOR": "hydro",
            "MANY": "dendro", "SIEGE": "pyro", "REACTION": "electro",
            "LIGHTNING": "electro", "TEMPO": "anemo", "VOID": "abyss",
            "EXECUTION": "electro",
        }
        for k, e in tokens.items():
            if k in branch.upper():
                return ECOL.get(e, fallback)
        return n.get("col") or fallback

    def _tree_line_color(self, kind, fallback):
        return {
            "c": fallback,
            "g": fallback,
            "m": mix(fallback, "#5f799a", 0.28),
            "n": fallback,
            "a": C_GOLD,
            "j": "#9fb5d3",
            "k": "#ffffff",
        }.get(kind, fallback)

    def draw_tree(self):
        if self.tree_tab == "skill":
            self.draw_skill_tree()
            return
        self.draw_passive_tree()

    def _draw_tree_tabs(self):
        c = self.canvas
        left = self._tree_side_width() + 14
        self.tree_tab_rects = []
        tabs = (("passive", "1  PASSIVE TREE", self.points), ("skill", "2  SKILL TREE", self.skill_pts))
        x = left
        for tab, label, pts in tabs:
            w = 205
            active = self.tree_tab == tab
            col = self.cls["col"] if active else "#4a6488"
            c.create_rectangle(x, 8, x + w, 36, fill="#0d1d33" if active else "#07101d", outline=col, width=2 if active else 1)
            c.create_text(x + 12, 22, anchor="w", text=label, fill="#ffffff" if active else "#7f97b8", font=("Segoe UI", 9, "bold"))
            c.create_text(x + w - 10, 22, anchor="e", text=f"{pts} pt", fill=C_GOLD if pts else "#4a6488", font=("Segoe UI", 8, "bold"))
            self.tree_tab_rects.append((x, 8, x + w, 36, tab))
            x += w + 8

    def _draw_tree_toolbar(self):
        c = self.canvas
        self.tree_control_rects = []
        side = self._tree_side_width()
        if self.tree_tab == "passive":
            items = [
                ("sidebar", "H  SIDEBAR", not getattr(self, "tree_sidebar_collapsed", False)),
                ("stats", "J  STATS", getattr(self, "tree_show_stats", False)),
                ("keystones", "K  KEYSTONES", getattr(self, "tree_show_keystones", False)),
                ("live", "L  DETAILS", getattr(self, "tree_show_live", False)),
                ("fit", "F  FIT TREE", False),
            ]
        else:
            items = [
                ("sidebar", "H  SIDEBAR", not getattr(self, "tree_sidebar_collapsed", False)),
                ("fit", "F  FIT ALL SKILLS", False),
            ]
        w, h, gap = (86, 24, 5) if len(items) >= 4 else (126, 24, 6)
        x = self.bw - (w + gap) * len(items) - 10
        if x < side + 270 and len(items) > 2:
            # Keep every control available, but compact the buttons instead of
            # silently hiding them on smaller laptop resolutions.
            w = 76
            x = self.bw - (w + gap) * len(items) - 10
        for action, label, on in items:
            outline = self.cls["col"] if on else "#334c6b"
            fill = "#0b1727" if on else "#06101b"
            # Dedicated toolbar row below the tabs prevents hitbox overlap.
            c.create_rectangle(x, 42, x + w, 66, fill=fill, outline=outline, width=1)
            c.create_text(x + w / 2, 54, anchor="center", text=label,
                          fill="#dfe9ff" if on else "#7189aa", font=("Segoe UI", 6, "bold"))
            self.tree_control_rects.append((x, 42, x + w, 66, action))
            x += w + gap

    # ------------------------------------------------------------------ passive
    def tree_xy(self, n):
        z = self.tree_zoom
        side = self._tree_side_width()
        tree_w = max(420, self.bw - side - 12)
        center_x = side + 6 + tree_w / 2
        wx, wy = self._passive_world(n)
        return center_x + self.tree_pan[0] + wx * z, self.bh / 2 + self.tree_pan[1] + wy * z

    def _tree_hot_region(self, hover):
        if not hover:
            return set(), set()
        # Highlight a two-step neighborhood, not only the single connector. This makes
        # the route readable even when a build has many nearby loops.
        seen = {hover}
        frontier = {hover}
        for _ in range(2):
            nxt = set()
            for nid in frontier:
                nxt.update(ADJ[nid])
            nxt -= seen
            seen |= nxt
            frontier = nxt
        hot_edges = set()
        for a, b in EDGES:
            if a in seen and b in seen:
                hot_edges.add((a, b))
        return seen, hot_edges

    def node_at(self, mx, my):
        # Prefer visually important sockets, then minor nodes, so dense but non-overlapping
        # layouts still feel forgiving to click.
        order = {"c": 0, "k": 1, "a": 2, "j": 3, "n": 4, "g": 5, "m": 6}
        ordered = sorted(self.class_tree_ids(), key=lambda nid: order.get(TREE[nid]["kind"], 9))
        for nid in ordered:
            n = TREE[nid]
            x, y = self.tree_xy(n)
            r = {"c": 23, "g": 13, "m": 8, "n": 12, "a": 16, "j": 13, "k": 21}[n["kind"]] * self.tree_zoom + 7
            if (mx - x) ** 2 + (my - y) ** 2 <= r * r:
                return nid
        return None

    def _section_button(self, y, label, action, on, class_col):
        """Draw a compact sidebar section button and make it clickable."""
        c = self.canvas
        side = self._tree_side_width()
        x0, x1, h = 14, side - 14, 24
        c.create_rectangle(x0, y, x1, y + h, fill="#081426", outline="#17304c", width=1)
        mark = "−" if on else "+"
        c.create_text(x0 + 9, y + h / 2, anchor="center", text=mark,
                      fill=class_col if on else "#5a7394", font=("Segoe UI", 9, "bold"))
        c.create_text(x0 + 21, y + h / 2, anchor="w", text=label,
                      fill="#d8e5fb" if on else "#7189aa", font=("Segoe UI", 6, "bold"))
        c.create_text(x1 - 9, y + h / 2, anchor="e", text="HIDE" if on else "SHOW",
                      fill=class_col if on else "#506987", font=("Segoe UI", 5, "bold"))
        self.tree_control_rects.append((x0, y, x1, y + h, action))
        return y + h

    def _draw_passive_sidebar(self, class_col, info):
        c, bw, bh = self.canvas, self.bw, self.bh
        side = self._tree_side_width()
        self.tree_sidebar_rect = (0, 0, side, bh)
        if getattr(self, "tree_sidebar_collapsed", False):
            c.create_rectangle(0, 0, side, bh, fill="#06101d", outline="#183251", width=2)
            c.create_rectangle(7, 12, side - 7, 50, fill="#09182a", outline=class_col, width=1)
            c.create_text(side / 2, 30, text="»", fill=class_col, font=("Segoe UI Symbol", 14, "bold"))
            c.create_text(side / 2, 76, text="TREE", fill="#5f799b", font=("Segoe UI", 6, "bold"))
            c.create_text(side / 2, 91, text="H", fill=C_GOLD, font=("Segoe UI", 8, "bold"))
            c.create_text(side / 2, 114, text="F", fill="#546e8e", font=("Segoe UI", 7, "bold"))
            # Critical: the collapsed control remains a real mouse target.
            self.tree_control_rects.append((7, 12, side - 7, 50, "sidebar"))
            return

        c.create_rectangle(0, 0, side, bh, fill="#06101d", outline="#183251", width=2)
        c.create_rectangle(12, 12, side - 12, 88, fill="#081426", outline=mix(class_col, "#06101d", 0.55), width=2)
        c.create_text(20, 27, anchor="w", text="PASSIVE TREE", fill="#ffffff", font=("Segoe UI", 13, "bold"))
        c.create_text(20, 46, anchor="w", text=info["title"], fill=class_col, font=("Segoe UI", 7, "bold"))
        c.create_text(20, 61, anchor="w", text=f"LV {self.level}  •  {self.points} POINTS", fill=C_GOLD, font=("Segoe UI", 6, "bold"))
        c.create_text(20, 75, anchor="w", text="Character stats only  •  nodes are routed", fill="#6680a3", font=("Segoe UI", 5))

        y = 101
        y = self._section_button(y, "KEYSTONE DOCTRINES", "keystones", getattr(self, "tree_show_keystones", False), class_col) + 5
        if getattr(self, "tree_show_keystones", False):
            ks = [(nid, TREE[nid]) for nid in self.class_tree_ids() if TREE[nid]["kind"] == "k"]
            # 3-column cards prevent long names/descriptions from colliding.
            cols = 3
            gap = 4
            x0 = 14
            card_w = (side - 28 - gap * (cols - 1)) / cols
            row_h = 29
            selected = self.tree_choice_state()
            for i, (nid, n) in enumerate(ks):
                r, col = divmod(i, cols)
                xx = x0 + col * (card_w + gap)
                yy = y + r * row_h
                picked = nid == selected
                outline = class_col if picked else "#17304c"
                c.create_rectangle(xx, yy, xx + card_w, yy + row_h - 3,
                                   fill="#101e32" if picked else "#071220", outline=outline, width=1)
                c.create_text(xx + 6, yy + 8, anchor="w", text="◆", fill=class_col if picked else "#536f92", font=("Segoe UI", 6, "bold"))
                c.create_text(xx + 15, yy + 7, anchor="w", text=n["name"].replace("KEYSTONE: ", "")[:13],
                              fill="#ffffff" if picked else "#7892b5", font=("Segoe UI", 4, "bold"))
                c.create_text(xx + 15, yy + 19, anchor="w", text="TAKEN" if picked else "AVAILABLE",
                              fill=class_col if picked else "#485f7e", font=("Segoe UI", 3, "bold"))
                # clicking a doctrine card focuses its node; choosing still happens through the graph
                self.tree_control_rects.append((xx, yy, xx + card_w, yy + row_h - 3, "keystone_focus:" + nid))
            y += ((len(ks) + cols - 1) // cols) * row_h + 5

        y = self._section_button(y, "BUILD STATS", "stats", getattr(self, "tree_show_stats", False), class_col) + 5
        if getattr(self, "tree_show_stats", False):
            ledger = [
                ("MAX HP", f"{self.maxhp:.0f}  ({self.S['hp_pct']:+.1f}%)"),
                ("LIFESTEAL", f"{self.S['steal']:.1f}%"),
                ("HP REGEN", f"{self.S['regen'] + self.maxhp * self.S['regen_pct'] / 100:.2f}/s"),
                ("ENERGY", f"{int(self.S['energy_max'])}  • {self.S['energy_recharge']:+.1f}%"),
                ("LIFE ON HIT", f"{self.S['life_on_hit']:.1f}"),
                ("LIFE ON KILL", f"{self.S['life_on_kill']:.1f}"),
                ("DMG TAKEN", f"-{self.S['less_damage']:.1f}%"),
                ("ARMOR", f"{self.S['armor']:.1f}"),
            ]
            row_h = 17
            for i, (lab, val) in enumerate(ledger):
                yy = y + i * row_h
                c.create_text(20, yy + 7, anchor="w", text=lab, fill="#7189aa", font=("Segoe UI", 4, "bold"))
                c.create_text(side - 20, yy + 7, anchor="e", text=val,
                              fill=class_col if i < 4 else "#9ab0cf", font=("Segoe UI", 4, "bold"))
            y += len(ledger) * row_h + 5

        # The detailed skill ledger stays off the passive tree by default. It can be
        # opened only when needed; the graph never gets covered by permanent text.
        if getattr(self, "tree_show_live", False):
            y = self._section_button(y, "LIVE COMBAT DETAILS", "live", True, class_col) + 5
            live = [
                ("LMB", self._basic_attack_line()),
                ("COIL", f"{self.skill_profile('coil')['dps']:.0f} DPS  •  {self.skill_profile('coil')['slow']:.1f}s slow"),
                ("SPIT", f"{self.skill_profile('spit')['reach']:.1f} range  •  {self.skill_profile('spit')['damage']:.0f} dmg"),
                ("VOLLEY", f"{self.skill_profile('volley')['count']:.0f} bolts  •  {self.skill_profile('volley')['pierce']} pierce"),
            ]
            for lab, val in live:
                if y + 27 > bh - 85:
                    break
                c.create_text(20, y + 5, anchor="w", text=lab, fill=C_TEXT, font=("Segoe UI", 4, "bold"))
                c.create_text(20, y + 15, anchor="w", text=val[:42], fill="#7189a9", font=("Segoe UI", 4))
                y += 22

        c.create_rectangle(12, bh - 76, side - 12, bh - 10, fill="#07111f", outline="#132b47", width=1)
        c.create_text(20, bh - 62, anchor="w", text="LMB allocate  •  RMB refund", fill=C_CYAN, font=("Segoe UI", 5, "bold"))
        c.create_text(20, bh - 47, anchor="w", text="DRAG pan  •  WHEEL zoom", fill="#6781a4", font=("Segoe UI", 5))
        c.create_text(20, bh - 32, anchor="w", text="H sidebar  •  J stats  •  K keystones", fill="#526c8b", font=("Segoe UI", 4, "bold"))
        c.create_text(20, bh - 18, anchor="w", text="F fit • hover = route + effect", fill="#526c8b", font=("Segoe UI", 4, "bold"))

    def draw_passive_tree(self):
        """Retained passive-tree renderer: heavy graph work only on actual changes."""
        c = self.canvas
        hover = self.node_at(*self.mouse)
        key = (
            self.run_class, self.bw, self.bh, round(self.tree_zoom, 3),
            tuple(sorted(self.alloc)), self.points, self.level,
            bool(getattr(self, "tree_sidebar_collapsed", False)),
            bool(getattr(self, "tree_show_keystones", False)),
            bool(getattr(self, "tree_show_stats", False)),
            bool(getattr(self, "tree_show_live", False)),
        )
        if getattr(self, "_passive_tree_static_key", None) != key:
            c.delete("all")
            self._render_passive_tree_static()
            self._draw_tree_tabs()
            self._draw_tree_toolbar()
            self._passive_tree_static_key = key
            self._passive_dynamic_sig = None
        dyn_sig = (hover, round(self.mouse[0]), round(self.mouse[1]), bool(getattr(self, "tree_show_live", False)))
        if getattr(self, "_passive_dynamic_sig", None) != dyn_sig:
            c.delete("passive_dynamic")
            self._draw_passive_dynamic(hover)
            self._passive_dynamic_sig = dyn_sig

    def _draw_passive_dynamic(self, hover):
        """Small hover-only layer; never rebuilds the 175-node graph."""
        c, bw, bh = self.canvas, self.bw, self.bh
        class_col = TREE_DEFS[self.run_class]["col"]
        tree_left = self._tree_side_width() + 8
        if hover and hover in TREE:
            _hot_nodes, hot_edges = self._tree_hot_region(hover)
            active_ids = set(self.class_tree_ids())
            for a, b in hot_edges:
                if a not in active_ids or b not in active_ids:
                    continue
                na, nb = TREE[a], TREE[b]
                xa, ya = self.tree_xy(na); xb, yb = self.tree_xy(nb)
                col = self._tree_node_color(na, class_col)
                c.create_line(xa, ya, xb, yb, fill="#03070e", width=max(4, int(6*self.tree_zoom)), tags="passive_dynamic")
                c.create_line(xa, ya, xb, yb, fill="#f8fcff", width=max(2, int(3*self.tree_zoom)), tags="passive_dynamic")
            n = TREE[hover]
            x, y = self.tree_xy(n)
            r = {"c":23,"g":13,"m":8,"n":11,"a":15,"j":11,"k":18}.get(n["kind"],10)*self.tree_zoom
            c.create_oval(x-r-5, y-r-5, x+r+5, y+r+5, outline=class_col, width=2, tags="passive_dynamic")
            # Fixed-above-node info card, bounded to the graph area.
            lines=[n["name"], KIND_NAME[n["kind"]]]
            if n.get("branch"): lines.append(n["branch"])
            lines += describe(n.get("stats", {}))
            if n.get("elem"): lines.append(f"ELEMENT: {n['elem'].upper()}")
            if n.get("info"): lines.append(n["info"])
            if n.get("choice_group"): lines.append("KEYSTONE: choose one doctrine")
            status = "ALLOCATED — RMB to refund" if hover in self.alloc else ("AVAILABLE — LMB to allocate" if self.can_alloc(hover) else "LOCKED — connect a nearby socket")
            lines.append(status)
            lines = [x[:54] for x in lines]
            w=min(310,max(215,max(len(t) for t in lines)*5.0+26)); h=min(bh-76,len(lines)*13+20)
            mx,my=self.mouse
            tx=mx+18; ty=my+18
            if tx+w>bw-8: tx=mx-w-18
            if ty+h>bh-8: ty=my-h-18
            tx=max(tree_left+8,min(tx,bw-w-8)); ty=max(40,min(ty,bh-h-8))
            c.create_rectangle(tx+3,ty+4,tx+w+3,ty+h+4,fill="#02050a",outline="",tags="passive_dynamic")
            c.create_rectangle(tx,ty,tx+w,ty+h,fill="#081525",outline=class_col,width=2,tags="passive_dynamic")
            for i,line in enumerate(lines):
                c.create_text(tx+10,ty+9+i*13,anchor="w",text=line,fill="#ffffff" if i==0 else C_TEXT,font=("Segoe UI",7,"bold" if i==0 else "normal"),tags="passive_dynamic")

    def _render_passive_tree_static(self):
        c, bw, bh = self.canvas, self.bw, self.bh
        cid = self.run_class
        info = TREE_DEFS[cid]
        class_col = info["col"]
        side = self._tree_side_width()
        tree_left = side + 8
        tree_w = max(420, bw - tree_left - 10)
        z = self.tree_zoom
        mx, my = self.mouse
        hover = None

        c.create_rectangle(0, 0, bw, bh, fill="#04070d", outline="")
        for sx, sy, ph, sz in STARS[:50]:
            x = sx % bw; y = sy % bh
            tw = 0.05 + 0.08 * (math.sin(self.time + ph) + 1) / 2
            c.create_rectangle(x, y, x + sz, y + sz, fill=mix("#04070d", "#9bb8df", tw), outline="")

        cx0 = tree_left + tree_w / 2
        cy0 = bh / 2 + 2
        self._passive_graph_item_start = c.find_all()[-1] if c.find_all() else 0
        # Real-sky constellation backdrop (Serpens / the Snake): the background is
        # deliberately attached to EXISTING passive-node positions.  The node graph
        # itself is untouched; these stars/lines are decoration only.  The selected
        # stars are real Serpens stars (J2000 identities/magnitudes) and are remapped
        # one-for-one to the existing backbone sockets so alignment remains exact
        # through every class, zoom level, and pan position.
        serpen_anchor_ids = [
            f"{cid}:f:s3_4", f"{cid}:f:s4_4", f"{cid}:f:s5_4",
            f"{cid}:f:s6_4", f"{cid}:core", f"{cid}:f:s7_4",
            f"{cid}:f:s0_4", f"{cid}:f:s1_4", f"{cid}:f:s2_4",
        ]
        # Source reference: Serpens notable-star catalog, coordinates for equinox
        # J2000.0.  These identities are only used for the visual star treatment.
        serpens_stars = [
            ("delta Ser", 15+34/60+48.19/3600, 10+32/60+19.9/3600, 3.80),
            ("beta Ser", 15+46/60+11.21/3600, 15+25/60+18.9/3600, 3.65),
            ("kappa Ser", 15+48/60+44.41/3600, 18+8/60+30.4/3600, 4.09),
            ("alpha Ser / Unukalhai", 15+44/60+16.00/3600, 6+25/60+31.9/3600, 2.63),
            ("gamma Ser", 15+56/60+26.99/3600, 15+39/60+53.0/3600, 5.20),
            ("epsilon Ser", 15+50/60+48.89/3600, 4+28/60+39.3/3600, 3.71),
            ("mu Ser", 15+49/60+37.27/3600, -(3+25/60+48.5/3600), 3.54),
            ("xi Ser", 17+37/60+35.23/3600, -(15+23/60+54.3/3600), 3.54),
            ("eta Ser", 18+21/60+18.92/3600, -(2+53/60+49.6/3600), 3.23),
        ]
        star_pts=[]
        for nid, star in zip(serpen_anchor_ids, serpens_stars):
            n=TREE.get(nid)
            if not n:
                continue
            sx, sy = self.tree_xy(n)
            star_pts.append((sx, sy, star[0], star[3]))
        # Keep a faint star-field behind the constellation; deterministic and cheap.
        for idx, (sx, sy, _name, mag) in enumerate(star_pts):
            tw = max(1.6, min(4.5, 4.9 - mag*0.55)) * max(0.72, z)
            halo = tw * 2.15
            scol = "#8ec5ff" if idx % 3 else "#d5e9ff"
            c.create_oval(sx-halo, sy-halo, sx+halo, sy+halo,
                          outline=mix("#07111f", scol, 0.30), width=1)
            c.create_rectangle(sx-tw*.30, sy-tw*.30, sx+tw*.30, sy+tw*.30,
                               fill=scol, outline="")
        # Constellation stick-lines use the SAME exact node centers.  This keeps
        # every segment perfectly married to the existing passive tree routing.
        serp_edges = [(0,1),(1,2),(1,3),(2,4),(3,5),(5,6),(6,7),(7,8)]
        for ia, ib in serp_edges:
            if ia >= len(star_pts) or ib >= len(star_pts):
                continue
            xa, ya = star_pts[ia][0], star_pts[ia][1]
            xb, yb = star_pts[ib][0], star_pts[ib][1]
            c.create_line(xa, ya, xb, yb,
                          fill="#3d648e", width=max(1, int(1.2*z)),
                          dash=(2, max(4, int(7*z))))
        # A subtle constellation-name watermark replaces the old creature-eyes/tail
        # decoration without competing with the real node graph.
        c.create_text(cx0+self.tree_pan[0], cy0+self.tree_pan[1]-255*z,
                      text="SERPENS • J2000 CONSTELLATION BACKBONE",
                      fill="#2a587f", font=("Segoe UI", 6, "bold"))
        active_ids = set(self.class_tree_ids())
        hot_nodes, hot_edges = self._tree_hot_region(hover)
        for a, b in EDGES:
            if a not in active_ids or b not in active_ids: continue
            na, nb = TREE[a], TREE[b]
            xa, ya = self.tree_xy(na); xb, yb = self.tree_xy(nb)
            if max(xa, xb) < tree_left - 100 or min(xa, xb) > bw + 100 or max(ya, yb) < -100 or min(ya, yb) > bh + 100:
                continue
            both = a in self.alloc and b in self.alloc
            one = a in self.alloc or b in self.alloc
            hot = hover is not None and (a, b) in hot_edges
            da,sa = self._passive_district(a); db,sb = self._passive_district(b)
            same_route = da is not None and da == db and sa is not None and sb is not None and abs(sa-sb) <= 1.05
            branch_col = self._tree_node_color(na, class_col)
            if same_route:
                base = branch_col if both or one else mix(branch_col, "#16273a", 0.28)
                width = max(1, int((3.2 if (both or one) else 1.8) * z))
                dash = None
            else:
                # Alternate links are still functional, but hidden at rest so the
                # player sees a readable main route. Hovering a node reveals the
                # alternate bridges and their direction.
                if not hot and not (both or one):
                    continue
                base = mix(branch_col, "#ffffff", 0.24) if hot else branch_col
                width = max(1, int((2.4 if hot else 1.5) * z))
                dash = None if hot or (both or one) else (3,6)
            c.create_line(xa, ya, xb, yb, fill="#01040a", width=max(3, int(5*z)))
            if hot:
                c.create_line(xa, ya, xb, yb, fill="#f6fbff", width=max(3, int(5*z)))
            if dash:
                c.create_line(xa, ya, xb, yb, fill=base, width=width, dash=dash)
            else:
                c.create_line(xa, ya, xb, yb, fill=base, width=width)

            # Clear chevron showing exactly which direction is currently available.
            next_id = b if a in self.alloc and b not in self.alloc else (a if b in self.alloc and a not in self.alloc else None)
            if next_id and self.can_alloc(next_id):
                ax, ay = (xa, ya) if a in self.alloc else (xb, yb)
                bx, by = (xb, yb) if a in self.alloc else (xa, ya)
                t = 0.66
                px, py = ax + (bx-ax)*t, ay + (by-ay)*t
                ang = math.atan2(by-ay, bx-ax)
                sz = 4 + 2*z
                pts = [(px + math.cos(ang)*sz, py + math.sin(ang)*sz),
                       (px + math.cos(ang+2.55)*sz, py + math.sin(ang+2.55)*sz),
                       (px + math.cos(ang-2.55)*sz, py + math.sin(ang-2.55)*sz)]
                c.create_polygon(*sum(([p[0], p[1]] for p in pts), []), fill=class_col, outline="")

        # Nodes, deliberately label-light.
        # Slightly compact low-zoom socket silhouettes keep even the closest
        # junctions visually separated. Hitboxes remain forgiving in node_at().
        sizes = {"c": 23, "g": 13, "m": 7, "n": 11, "a": 15, "j": 11, "k": 18}
        for nid in active_ids:
            n = TREE[nid]
            if n["kind"] == "c":
                continue
            x, y = self.tree_xy(n)
            r = sizes[n["kind"]] * z
            if x < tree_left - 65 or x > bw + 65 or y < -65 or y > bh + 65:
                continue
            allocated = nid in self.alloc
            available = self.can_alloc(nid)
            node_col = self._tree_node_color(n, class_col)
            state_col = node_col if available or allocated else mix(node_col, "#04070d", 0.68)
            hot = not hover or nid in hot_nodes
            fill_dim = "#060d17" if hover and nid not in hot_nodes else "#081421"
            # cluster halos only for meaningful sockets
            if n["kind"] in ("n", "a", "k") and z >= 0.48:
                hr = {"n": 21, "a": 30, "k": 39}[n["kind"]] * z
                c.create_oval(x-hr, y-hr, x+hr, y+hr, outline=mix(node_col, "#04070d", 0.72), width=1, dash=(2, 7))

            if n["kind"] == "c":
                # The class core inherits the old origin's diamond silhouette,
                # but becomes the actual living center of the passive tree.
                rr = r + 5
                pts = []
                for k in range(4):
                    a = math.pi / 4 + k * math.pi / 2
                    pts.extend((x + rr * math.cos(a), y + rr * math.sin(a)))
                elem_col = ECOL.get(self._PASSIVE_AFFINITY.get(cid, ["dendro"])[0], node_col)
                c.create_oval(x-rr-7, y-rr-7, x+rr+7, y+rr+7, outline=mix(elem_col, node_col, 0.4), width=2)
                c.create_polygon(*pts, fill=node_col if allocated else "#0b1525",
                                  outline="#ffffff" if allocated else state_col, width=3)
                c.create_oval(x-r*.55, y-r*.55, x+r*.55, y+r*.55,
                              fill="#091323", outline=elem_col, width=2)
                # Four small elemental rays make the center read as a source/origin
                # without needing a separate ORIGIN socket.
                for k in range(4):
                    a = k * math.pi / 2
                    p0 = (x + math.cos(a) * (r+5), y + math.sin(a) * (r+5))
                    p1 = (x + math.cos(a) * (r+13), y + math.sin(a) * (r+13))
                    c.create_line(*p0, *p1, fill=elem_col, width=max(1, int(2*z)))
            elif n["kind"] == "k":
                rr = r + 4
                pts=[]
                for k in range(8):
                    a = -math.pi/8 + k*math.pi/4
                    pts.extend((x+rr*math.cos(a), y+rr*math.sin(a)))
                c.create_polygon(*pts, fill=node_col if allocated else fill_dim,
                                  outline="#ffffff" if allocated else state_col, width=3 if allocated else 2)
                rr2 = r*.53
                c.create_oval(x-rr2,y-rr2,x+rr2,y+rr2,fill="#0b1424",outline=state_col,width=2)
            elif n["kind"] == "a":
                rr = r + 3
                pts=[]
                for k in range(6):
                    a=-math.pi/2+k*math.pi/3
                    pts.extend((x+rr*math.cos(a), y+rr*math.sin(a)))
                c.create_polygon(*pts, fill=node_col if allocated else fill_dim, outline="#ffffff" if allocated else state_col, width=3 if allocated else 2)
                c.create_oval(x-r*.40,y-r*.40,x+r*.40,y+r*.40,fill="#0b1424",outline=state_col,width=1)
            elif n["kind"] == "j":
                rr=r+2
                pts=[]
                for k in range(4):
                    a=math.pi/4+k*math.pi/2
                    pts.extend((x+rr*math.cos(a), y+rr*math.sin(a)))
                c.create_polygon(*pts, fill="#06101b", outline="#ffffff" if allocated else "#9fb5d3", width=2)
                c.create_oval(x-r*.35,y-r*.35,x+r*.35,y+r*.35, fill=class_col if allocated else "#101e32", outline=state_col, width=1)
            elif n["kind"] == "n":
                c.create_oval(x-r-2,y-r-2,x+r+2,y+r+2,outline=mix(state_col,"#04070d",0.35),width=2)
                c.create_oval(x-r,y-r,x+r,y+r,fill=node_col if allocated else fill_dim,outline="#ffffff" if allocated else state_col,width=2)
                c.create_rectangle(x-2.5,y-2.5,x+2.5,y+2.5,fill="#ffffff" if allocated else state_col,outline="")
            else:
                c.create_oval(x-r,y-r,x+r,y+r,fill=node_col if allocated else fill_dim,outline="#ffffff" if allocated else state_col,width=2 if n["kind"]=="g" else 1)
                if available:
                    pulse=2+2*self.pulse(3.2)
                    c.create_oval(x-r-pulse,y-r-pulse,x+r+pulse,y+r+pulse,outline=node_col,width=1)

            show = (
                n["kind"] == "k" or
                nid == hover or
                allocated or
                (available and n["kind"] in ("c", "g", "a"))
            )
            if show:
                lab = n["name"].replace("KEYSTONE: ", "")
                if n["kind"] == "k":
                    c.create_text(x, y+r+9, anchor="n", text=lab[:23], fill="#ffffff" if allocated else state_col,
                                  font=("Segoe UI", 6, "bold"))
                elif n["kind"] == "c":
                    c.create_text(x, y+r+7, anchor="n", text=lab[:25], fill="#ffffff" if allocated else state_col,
                                  font=("Segoe UI", 6, "bold"))
                elif n["kind"] == "a":
                    c.create_text(x, y+r+7, anchor="n", text=lab[:25], fill="#ffffff" if allocated else state_col,
                                  font=("Segoe UI", 5, "bold"))
                elif n["kind"] in ("n", "m") and (nid == hover or allocated):
                    c.create_text(x, y+r+6, anchor="n", text=lab[:25], fill="#d7e5ff" if allocated else state_col,
                                  font=("Segoe UI", 5, "bold"))

        # The class core is the actual starting point.  There is no separate
        # ORIGIN node anymore; the old origin visual language is merged into this core.
        core = TREE.get(f"{cid}:core")
        if core:
            cx, cy = self.tree_xy(core); cr=23*z
            elem_col = ECOL.get(self._PASSIVE_AFFINITY.get(cid, ["dendro"])[0], class_col)
            c.create_oval(cx-cr-9, cy-cr-9, cx+cr+9, cy+cr+9,
                          outline=mix(elem_col, class_col, 0.25), width=max(1, int(2*z)))
            c.create_text(cx, cy+cr+10, text=f"{self.cls['name'].upper()} CORE",
                          fill="#ffffff" if core.get("_id") in self.alloc else class_col,
                          font=("Segoe UI", 7, "bold"))
            c.create_text(cx, cy+cr+23, text="STARTING CORE • ALWAYS ACTIVE",
                          fill=C_GOLD, font=("Segoe UI", 5, "bold"))

        for item in c.find_all():
            if item > getattr(self, "_passive_graph_item_start", 0):
                c.addtag_withtag("passive_graph", item)

        # Sidebar is fully separated from the graph.
        self._draw_passive_sidebar(class_col, info)

        # Hover inspector is drawn in _draw_passive_dynamic().

        c.create_text(tree_left+12, 80, anchor="w", text=f"// {info['title']}   •   CREATURE ROUTING • ELEMENTAL PATHS",
                      fill="#607a9d", font=("Segoe UI", 7, "bold"))
        total=len(active_ids); keystones=sum(1 for nid in active_ids if TREE[nid]["kind"]=="k")
        majors=sum(1 for nid in active_ids if TREE[nid]["kind"]=="a"); jewels=sum(1 for nid in active_ids if TREE[nid]["kind"]=="j")
        c.create_text(bw-14, 80, anchor="e", text=f"{total} NODES  •  {majors} MAJORS  •  {jewels} JEWELS  •  {keystones} KEYSTONES",
                      fill=class_col, font=("Segoe UI", 7, "bold"))

        lx, ly = tree_left+14, 98
        legend=(("c","CORE"),("m","MINOR"),("n","NOTABLE"),("a","MAJOR"),("j","JEWEL"),("k","KEYSTONE"))
        for i,(kind,label) in enumerate(legend):
            xx=lx+i*72
            c.create_oval(xx,ly-4,xx+9,ly+5,fill="#08111f",outline=self._tree_line_color(kind,class_col),width=2)
            c.create_text(xx+14,ly,anchor="w",text=label,fill="#597493",font=("Segoe UI",5,"bold"))

    # ------------------------------------------------------------------ active skill tree
    # The active skill tree is its own constellation: one central skill core with
    # twelve radial skill branches.  Each branch still contains the full
    # ROOT -> 3 PATHS -> MASTERY -> 2 CAPSTONES graph from active_skill_tree.py,
    # but the screen no longer reads like a grid of unrelated boxes.
    def _skill_ring_anchor(self, line):
        order = [key for key, _slot, _name, _col in SKILLS]
        try:
            idx = order.index(line)
        except ValueError:
            idx = 0
        angle = math.radians(-90 + idx * 30.0)
        # Slightly elliptical ring: enough separation for 12 full skill graphs
        # while leaving a clear central core.
        rx, ry = 360.0, 252.0
        return rx * math.cos(angle), ry * math.sin(angle), angle

    def _skill_original_center(self, line):
        # The data file keeps compact local coordinates.  Translate them into the
        # radial layout here so gameplay/node IDs remain unchanged.
        order = [key for key, _slot, _name, _col in SKILLS]
        idx = order.index(line) if line in order else 0
        cols = [-465, -155, 155, 465]
        rows = [-245, 0, 245]
        return cols[idx % 4], rows[idx // 4]

    def _skill_world(self, n):
        line = n.get("line", "dash")
        ax, ay, angle = self._skill_ring_anchor(line)
        ox, oy = self._skill_original_center(line)
        # Compress each local graph slightly so neighbouring radial branches have
        # breathing room at the default overview zoom.
        lx = (n["x"] - ox) * 0.76
        ly = (n["y"] - oy) * 0.76
        ca, sa = math.cos(angle), math.sin(angle)
        return ax + lx * ca - ly * sa, ay + lx * sa + ly * ca

    def _skill_xy(self, n):
        z = self.tree_zoom
        side = self._tree_side_width()
        tree_w = max(420, self.bw - side - 12)
        cx = side + 6 + tree_w / 2
        cy = self.bh / 2 + 6
        wx, wy = self._skill_world(n)
        return cx + self.tree_pan[0] + wx * z, cy + self.tree_pan[1] + wy * z

    def _skill_hitboxes(self):
        sig=(self.run_class, self.bw, self.bh, round(self.tree_zoom, 3), round(self.tree_pan[0], 1), round(self.tree_pan[1], 1))
        if getattr(self, "_skill_hit_sig", None) == sig:
            return self._skill_hit_cache
        cid = self.run_class
        ids = [nid for nid in SKILL_NODES if nid.startswith(cid + ":")]
        order = {"k":0,"a":1,"j":2,"n":3,"r":4,"m":5}
        ids.sort(key=lambda nid: order.get(SKILL_NODES[nid]["kind"],9))
        sizes={"r":22,"m":8,"n":12,"a":15,"j":14,"k":19}
        hit=[]
        for nid in ids:
            n=SKILL_NODES[nid]; x,y=self._skill_xy(n); r=sizes[n["kind"]]*self.tree_zoom+7
            hit.append((x-r, y-r, x+r, y+r, nid))
        self._skill_hit_sig=sig
        self._skill_hit_cache=hit
        return hit

    def _skill_node_at(self, mx, my):
        for x0,y0,x1,y1,nid in self._skill_hitboxes():
            if x0 <= mx <= x1 and y0 <= my <= y1:
                return nid
        return None

    def _skill_region(self, line):
        roots=[n for n in SKILL_NODES.values() if n["line"]==line and n["id"].startswith(self.run_class+":") and n["kind"]=="r"]
        if not roots: return (0,0)
        n=roots[0]
        return n["x"]+125, n["y"]

    def _skill_node_icon(self, n, x, y, r, col):
        """Draw a tiny pixel-glyph inside important skill nodes.

        The skill tree deliberately has no permanent labels, so important sockets
        need a visual language of their own.  Glyphs are derived from the node's
        effect name/description and stay small enough to preserve the constellation.
        """
        c = self.canvas
        text = f"{n.get('name','')} {n.get('desc','')}".upper()
        kind = n.get("kind")
        line = n.get("line", "")
        ink = "#f4fbff" if kind in ("k", "a", "j") else col
        w = max(2, int(1.6 * max(0.8, self.tree_zoom)))
        # Multi-shot / fan / split: three projectiles.
        if any(t in text for t in ("DOUBLE", "TRIPLE", "MULTI", "FAN", "SPLIT", "TWINS")):
            for dx, dy in ((-0.48, 0.18), (0, -0.08), (0.48, 0.18)):
                px, py = x + dx * r, y + dy * r
                c.create_rectangle(px-1.5, py-1.5, px+1.5, py+1.5, fill=ink, outline="")
                c.create_line(px, py+1, px, py+r*0.32, fill=ink, width=w)
            return
        # Bounce / ricochet / chain: linked corners and arrow.
        if any(t in text for t in ("BOUNCE", "RICOCHET", "CHAIN", "ECHO")):
            c.create_line(x-r*.52, y+r*.28, x, y-r*.36, x+r*.52, y+r*.28,
                          fill=ink, width=w, smooth=False)
            c.create_line(x+r*.10, y-r*.36, x+r*.48, y-r*.36,
                          fill=ink, width=w)
            c.create_line(x+r*.48, y-r*.36, x+r*.34, y-r*.54,
                          fill=ink, width=w)
            return
        # Explosion / burst / cataclysm: 8-bit starburst.
        if any(t in text for t in ("EXPLODE", "EXPLOSION", "BURST", "CATA", "SHOCKWAVE", "BLAST")):
            for ang in (0, math.pi/4, math.pi/2, 3*math.pi/4):
                ax, ay = math.cos(ang), math.sin(ang)
                c.create_line(x-ax*r*.55, y-ay*r*.55, x+ax*r*.55, y+ay*r*.55, fill=ink, width=w)
            c.create_rectangle(x-2, y-2, x+2, y+2, fill=ink, outline="")
            return
        # Elemental / reaction / prismatic: four tiny element sparks.
        if any(t in text for t in ("ELEMENT", "REACTION", "PRISM", "CATALYST", "TOXIN", "VENOM", "POISON")):
            cols = [ECOL.get(e, ink) for e in ("pyro", "hydro", "electro", "cryo")]
            for i, ang in enumerate((0, math.pi/2, math.pi, 3*math.pi/2)):
                px = x + math.cos(ang) * r*.42
                py = y + math.sin(ang) * r*.42
                c.create_rectangle(px-2, py-2, px+2, py+2, fill=cols[i], outline="")
            c.create_rectangle(x-2, y-2, x+2, y+2, fill=ink, outline="")
            return
        # Pierce / lance / artillery: a compact spear.
        if any(t in text for t in ("PIERCE", "LANCE", "CANNON", "ARTILLERY", "SHELL", "SIEGE")):
            c.create_line(x-r*.52, y+r*.30, x+r*.46, y-r*.30, fill=ink, width=w)
            c.create_polygon(x+r*.46, y-r*.30,
                             x+r*.20, y-r*.46,
                             x+r*.26, y-r*.08,
                             fill=ink, outline="")
            return
        # Defense / shield / fortress.
        if any(t in text for t in ("SHIELD", "GUARD", "FORTRESS", "AEGIS", "BULWARK", "WARD", "BARRIER")):
            pts=[(x, y-r*.52), (x+r*.42, y-r*.22), (x+r*.30, y+r*.38),
                 (x, y+r*.56), (x-r*.30, y+r*.38), (x-r*.42, y-r*.22)]
            flat=[v for pt in pts for v in pt]
            c.create_polygon(*flat, outline=ink, fill="", width=w)
            return
        # Sustain / heal / rebirth.
        if any(t in text for t in ("HEAL", "RENEW", "REBIRTH", "RECOVERY", "FLESH", "LIFE")):
            c.create_rectangle(x-r*.12, y-r*.46, x+r*.12, y+r*.46, fill=ink, outline="")
            c.create_rectangle(x-r*.46, y-r*.12, x+r*.46, y+r*.12, fill=ink, outline="")
            return
        # Speed / dash / motion.
        if any(t in text for t in ("SPEED", "DASH", "STEP", "MOTION", "MOMENTUM", "TEMPO")):
            c.create_polygon(x-r*.48, y-r*.22, x+r*.14, y-r*.22,
                             x+r*.14, y-r*.46, x+r*.50, y,
                             x+r*.14, y+r*.46, x+r*.14, y+r*.22,
                             x-r*.48, y+r*.22, fill=ink, outline="")
            return
        # Critical / execution / precision.
        if any(t in text for t in ("CRIT", "EXECUTION", "LETHAL", "PRECISION", "FOCUS", "WEAK POINT")):
            c.create_oval(x-r*.45, y-r*.45, x+r*.45, y+r*.45, outline=ink, width=w)
            c.create_line(x-r*.60, y, x+r*.60, y, fill=ink, width=w)
            c.create_line(x, y-r*.60, x, y+r*.60, fill=ink, width=w)
            c.create_rectangle(x-1.5, y-1.5, x+1.5, y+1.5, fill=ink, outline="")
            return
        # Fall back to the skill's identity: a tiny key glyph for roots/masteries,
        # a diamond spark for majors/notables, and a dot for minors.
        if kind == "r":
            c.create_rectangle(x-r*.15, y-r*.42, x+r*.15, y+r*.42, outline=ink, width=w)
            c.create_rectangle(x-r*.42, y-r*.05, x+r*.42, y+r*.28, outline=ink, width=w)
        elif kind == "j":
            pts=[(x,y-r*.55),(x+r*.55,y),(x,y+r*.55),(x-r*.55,y)]
            c.create_polygon(*[v for p in pts for v in p], outline=ink, fill="", width=w)
            c.create_rectangle(x-2,y-2,x+2,y+2,fill=ink,outline="")
        elif kind == "k":
            for ang in (0, math.pi/3, 2*math.pi/3):
                ax, ay = math.cos(ang), math.sin(ang)
                c.create_line(x-ax*r*.46, y-ay*r*.46, x+ax*r*.46, y+ay*r*.46, fill=ink, width=w)
            c.create_oval(x-2,y-2,x+2,y+2,fill=ink,outline="")
        elif kind == "a":
            c.create_polygon(x, y-r*.45, x+r*.45, y, x, y+r*.45, x-r*.45, y,
                             outline=ink, fill="", width=w)
            c.create_rectangle(x-1.5,y-1.5,x+1.5,y+1.5,fill=ink,outline="")
        elif kind == "n":
            c.create_rectangle(x-2,y-2,x+2,y+2,fill=ink,outline="")

    def _draw_skill_tooltip(self, tree_left, hover, defs):
        """Mouse-following node card for the active skill tree.

        Unlike the old bottom/sidebar inspector, the card is offset from the node and
        auto-flips away from screen edges so node labels never sit on top of the text.
        """
        c, bw, bh = self.canvas, self.bw, self.bh
        if not hover or hover not in SKILL_NODES:
            return
        n = SKILL_NODES[hover]
        col = defs[n["line"]]["color"]
        stats = describe(n.get("stats", {}))
        state = "ALLOCATED" if hover in self.skill_alloc else ("AVAILABLE" if self.can_skill_alloc(hover) else "LOCKED")
        lines = [n["name"], f'{defs[n["line"]]["name"]}  •  {KIND_NAME.get(n["kind"], "SKILL")}', *stats[:4]]
        desc = textwrap.wrap(n.get("desc", "Combat upgrade."), width=34)[:3]
        lines.extend(desc)
        lines.append(state + ("  •  RMB to refund" if state == "ALLOCATED" else ("  •  LMB to upgrade" if state == "AVAILABLE" else "  •  connect a path")))
        w = min(292, max(190, max(len(x) for x in lines) * 5.2 + 24))
        h = 16 + len(lines) * 14
        mx, my = self.mouse
        tx = mx + 18
        ty = my + 18
        if tx + w > bw - 8:
            tx = mx - w - 18
        if ty + h > bh - 8:
            ty = my - h - 18
        tx = max(tree_left + 6, min(tx, bw - w - 8))
        ty = max(38, min(ty, bh - h - 8))
        c.create_rectangle(tx+4, ty+5, tx+w+4, ty+h+5, fill="#02050a", outline="", tags="skill_dynamic")
        c.create_rectangle(tx, ty, tx+w, ty+h, fill="#081524", outline=col, width=2, tags="skill_dynamic")
        c.create_rectangle(tx+7, ty+7, tx+w-7, ty+25, fill="#0c2035", outline="", tags="skill_dynamic")
        c.create_text(tx+12, ty+16, anchor="w", text=lines[0][:32], fill="#ffffff", font=("Segoe UI", 8, "bold"), tags="skill_dynamic")
        yy = ty + 34
        for i, line in enumerate(lines[1:]):
            fill = col if i == 0 else ("#d8e5fb" if i == len(lines)-2 else "#9ab1cc")
            font = ("Segoe UI", 6, "bold" if i in (0, len(lines)-2) else "normal")
            c.create_text(tx+12, yy, anchor="w", text=line[:46], fill=fill, font=font, tags="skill_dynamic")
            yy += 14

    def _draw_skill_feedback(self):
        # Details are shown exclusively by the mouse-following floating inspector.
        return

    def _draw_skill_dynamic(self, hover):
        """Hover-only route highlight for the active skill constellation."""
        if not hover or hover not in SKILL_NODES:
            return
        c = self.canvas
        active_ids = {nid for nid in SKILL_NODES if nid.startswith(self.run_class + ":")}
        hot = {hover}
        frontier = {hover}
        for _ in range(2):
            nxt=set()
            for nid in frontier:
                nxt.update(SKILL_ADJ[nid])
            nxt -= hot; hot |= nxt; frontier=nxt
        for a,b in SKILL_EDGES:
            if a not in active_ids or b not in active_ids or a not in hot or b not in hot:
                continue
            xa,ya=self._skill_xy(SKILL_NODES[a]); xb,yb=self._skill_xy(SKILL_NODES[b])
            col=ACTIVE_SKILL_DEFS[self.run_class][SKILL_NODES[a]["line"]]["color"]
            c.create_line(xa, ya, xb, yb, fill="#f7fbff", width=max(2,int(3*self.tree_zoom)), tags="skill_dynamic")
        x,y=self._skill_xy(SKILL_NODES[hover])
        r={"r":22,"m":8,"n":12,"a":15,"j":14,"k":19}.get(SKILL_NODES[hover]["kind"],10)*self.tree_zoom
        c.create_oval(x-r-6,y-r-6,x+r+6,y+r+6,outline=ACTIVE_SKILL_DEFS[self.run_class][SKILL_NODES[hover]["line"]]["color"],width=2,tags="skill_dynamic")

    def draw_skill_tree(self):
        # The skill tree used to rebuild hundreds of Canvas objects every frame.
        # Cache the whole constellation and only rebuild when something that
        # actually changes it changes (zoom/pan/hover/allocation/sidebar).
        c, bw, bh = self.canvas, self.bw, self.bh
        mx, my = self.mouse
        hover = self._skill_node_at(mx, my)
        key = (self.run_class, self.bw, self.bh, round(self.tree_zoom, 3),
               tuple(sorted(self.skill_alloc)),
               bool(getattr(self, "tree_sidebar_collapsed", False)),
               bool(getattr(self, "tree_show_live", False)))
        if getattr(self, "_skill_tree_static_key", None) != key:
            c.delete("all")
            self._skill_hit_sig = None
            self._render_skill_tree_static()
            self._skill_tree_static_key = key
            self._skill_dynamic_sig = None
        # Only rebuild the small hover/tooltip layer when the pointer or hover
        # target actually changed; this avoids 60 full tooltip rebuilds per second.
        dyn_sig = (hover, round(mx), round(my))
        if getattr(self, "_skill_dynamic_sig", None) != dyn_sig:
            c.delete("skill_dynamic")
            self._draw_skill_dynamic(hover)
            self._draw_skill_tooltip(self._tree_side_width() + 8, hover, ACTIVE_SKILL_DEFS[self.run_class])
            self._draw_skill_feedback()
            self._skill_dynamic_sig = dyn_sig

    def _render_skill_tree_static(self):
        c, bw, bh = self.canvas, self.bw, self.bh
        cid = self.run_class
        defs = ACTIVE_SKILL_DEFS[cid]
        side = self._tree_side_width()
        tree_left = side + 8
        mx, my = self.mouse
        hover = None
        active_ids = {nid for nid in SKILL_NODES if nid.startswith(cid + ":")}
        self.skill_hits = self._skill_hitboxes()

        c.create_rectangle(0, 0, bw, bh, fill="#04070d", outline="")
        # Blueprint grid stays very subtle so the constellation itself carries the
        # visual hierarchy.
        grid = 28
        for x in range(int(tree_left), int(bw), grid):
            c.create_line(x, 40, x, bh, fill="#07101b", width=1)
        for y in range(48, bh, grid):
            c.create_line(tree_left, y, bw, y, fill="#07101b", width=1)

        def screen_world(wx, wy):
            z = self.tree_zoom
            tree_w = max(420, bw - side - 12)
            cx = side + 6 + tree_w / 2
            cy = bh / 2 + 6
            return cx + self.tree_pan[0] + wx * z, cy + self.tree_pan[1] + wy * z

        # Central skill core: a clean anchor for the 12 skill routes.
        self._skill_graph_item_start = c.find_all()[-1] if c.find_all() else 0
        core_r = 58 * self.tree_zoom
        ccx, ccy = screen_world(0, 0)
        if tree_left < ccx < bw:
            halo = core_r * 1.55 + 5 * self.pulse(1.8)
            c.create_oval(ccx - halo, ccy - halo, ccx + halo, ccy + halo,
                          outline=mix(self.cls["col"], "#07101c", 0.65), width=1)
            pts = []
            for k in range(6):
                a = -math.pi / 2 + k * math.pi / 3
                pts.extend((ccx + core_r * 1.12 * math.cos(a), ccy + core_r * 1.12 * math.sin(a)))
            c.create_polygon(*pts, fill="#091628", outline=self.cls["col"], width=2)
            inner = core_r * 0.58
            c.create_oval(ccx-inner, ccy-inner, ccx+inner, ccy+inner,
                          fill=mix(self.cls["col"], "#050a12", 0.78), outline=self.cls["col"], width=1)

        # Each skill is a radial "branch".  A faint socket halo identifies the
        # cluster, while the actual node graph supplies the strong readable lines.
        for key, slot, display, _col in SKILLS:
            d = defs[key]
            ax, ay, angle = self._skill_ring_anchor(key)
            sx, sy = screen_world(ax, ay)
            col = d["color"]
            line_w = max(1, int(1.0 + self.tree_zoom))
            # Ring anchor
            halo_w = 28 * self.tree_zoom
            halo_h = 16 * self.tree_zoom
            c.create_oval(sx - halo_w, sy - halo_h, sx + halo_w, sy + halo_h,
                          outline=mix(col, "#0a1421", 0.18), width=1)
            # radial guide from the core to this skill root
            ids = [nid for nid in active_ids if SKILL_NODES[nid]["line"] == key]
            root_id = next((nid for nid in ids if SKILL_NODES[nid]["kind"] == "r"), None)
            if root_id:
                rx, ry = self._skill_xy(SKILL_NODES[root_id])
                core_col = mix(col, self.cls["col"], 0.35)
                c.create_line(ccx, ccy, rx, ry, fill="#02060b", width=5)
                c.create_line(ccx, ccy, rx, ry, fill=core_col, width=line_w)
                # small midpoint gem, visually separating the skill branch from
                # the internal three-path graph.
                mx2 = ccx + (rx - ccx) * 0.72
                my2 = ccy + (ry - ccy) * 0.72
                rr = 4.5 * self.tree_zoom + 2
                c.create_oval(mx2-rr, my2-rr, mx2+rr, my2+rr,
                              fill="#07101d", outline=col, width=1)


        # Draw the skill graph as compact branch polylines instead of one Canvas
        # object per edge.  The data still keeps every edge for allocation, but the
        # renderer collapses the three long branch runs into a handful of line items.
        for key, _slot, _display, _col in SKILLS:
            col = defs[key]["color"]
            for pi in range(3):
                chain = [f"{cid}:{key}:root"] + [f"{cid}:{key}:p{pi}_{j}" for j in range(8)] + [f"{cid}:{key}:mastery"]
                pts = [(x,y) for nid in chain if nid in SKILL_NODES for x,y in [self._skill_xy(SKILL_NODES[nid])]]
                if len(pts) < 2:
                    continue
                flat = [v for pt in pts for v in pt]
                c.create_line(*flat, fill="#1c3047", width=max(1, int(1.1 + self.tree_zoom)))
                # Brightly paint only the portion the player has actually built.
                owned_idx = [i for i,nid in enumerate(chain) if nid in self.skill_alloc]
                if owned_idx:
                    last = max(owned_idx)
                    owned_pts = pts[:max(2, last+1)]
                    if len(owned_pts) >= 2:
                        flat2=[v for pt in owned_pts for v in pt]
                        c.create_line(*flat2, fill=col, width=max(2, int(2.0 + self.tree_zoom)))
            # Mastery -> capstone choices are separate sockets at the end.
            mastery = f"{cid}:{key}:mastery"
            for cap in (f"{cid}:{key}:cap0", f"{cid}:{key}:cap1"):
                if mastery in SKILL_NODES and cap in SKILL_NODES:
                    xa,ya=self._skill_xy(SKILL_NODES[mastery]); xb,yb=self._skill_xy(SKILL_NODES[cap])
                    c.create_line(xa,ya,xb,yb,fill=col if (mastery in self.skill_alloc or cap in self.skill_alloc) else "#1c3047",width=max(1,int(1.1+self.tree_zoom)))

            # The six cross-path bridges remain visible as faint guidance; they become
            # bright only once the mouse inspector highlights their neighbourhood.
            prefix=f"{cid}:{key}:"
            for a,b in SKILL_EDGES:
                if not (a.startswith(prefix) and b.startswith(prefix)):
                    continue
                la=a.split(":")[-1]; lb=b.split(":")[-1]
                same_main = (la == lb) or (la == "root") or (lb == "root") or (la == "mastery") or (lb == "mastery") or (la.startswith("cap") or lb.startswith("cap"))
                if same_main:
                    continue
                xa,ya=self._skill_xy(SKILL_NODES[a]); xb,yb=self._skill_xy(SKILL_NODES[b])
                hot = a in self.skill_alloc or b in self.skill_alloc
                c.create_line(xa,ya,xb,yb,fill=col if hot else "#102033",width=max(1,int(1.0+self.tree_zoom)))

        # Nodes themselves.
        sizes = {"r": 22, "m": 8, "n": 12, "a": 15, "j": 14, "k": 19}
        for nid in active_ids:
            n = SKILL_NODES[nid]
            x, y = self._skill_xy(n)
            r = sizes[n["kind"]] * self.tree_zoom
            owned = nid in self.skill_alloc
            avail = self.can_skill_alloc(nid)
            blocked = bool(n.get("choice")) and any(
                aid != nid and SKILL_NODES.get(aid, {}).get("choice") == n.get("choice")
                for aid in self.skill_alloc
            )
            col = defs[n["line"]]["color"]
            state = "#ffffff" if owned else (col if avail and not blocked else ("#445e7d" if not blocked else "#24354a"))
            kind = n["kind"]
            if kind == "r":
                # Diamond root = entry point of the skill branch.
                pts = [(x, y-r*1.18), (x+r*1.18, y), (x, y+r*1.18), (x-r*1.18, y)]
                c.create_polygon(*sum(([p[0], p[1]] for p in pts), []),
                                 fill=col if owned else "#0b1828", outline="#ffffff" if owned else col,
                                 width=2)
            elif kind == "k":
                pts=[]
                for k in range(8):
                    a=-math.pi/8+k*math.pi/4
                    pts.extend((x+(r+3)*math.cos(a), y+(r+3)*math.sin(a)))
                c.create_polygon(*pts, fill=col if owned else "#081320",
                                 outline="#ffffff" if owned else state, width=3 if owned else 2)
            elif kind == "a":
                pts=[]
                for k in range(6):
                    a=-math.pi/2+k*math.pi/3
                    pts.extend((x+(r+2)*math.cos(a), y+(r+2)*math.sin(a)))
                c.create_polygon(*pts, fill=col if owned else "#091523",
                                 outline="#ffffff" if owned else state, width=2)
            elif kind == "j":
                # Mastery socket: square/diamond hybrid.
                pts=[]
                for k in range(4):
                    a=math.pi/4+k*math.pi/2
                    pts.extend((x+(r+2)*math.cos(a), y+(r+2)*math.sin(a)))
                c.create_polygon(*pts, fill=col if owned else "#07111d", outline="#ffffff" if owned else "#95abc8", width=2)
            elif kind == "n":
                c.create_oval(x-r, y-r, x+r, y+r,
                              fill=col if owned else "#091523", outline="#ffffff" if owned else state, width=2)
            else:
                c.create_oval(x-r, y-r, x+r, y+r,
                              fill=col if owned else "#081521", outline="#ffffff" if owned else state,
                              width=2 if kind == "m" else 1)

            # Tiny visual glyphs keep major sockets from looking empty; all text remains hover-only.
            if kind in ("r", "n", "a", "j", "k"):
                self._skill_node_icon(n, x, y, r, col)

            # No permanent text on skill sockets. Hovering opens the floating inspector.

        for item in c.find_all():
            if item > getattr(self, "_skill_graph_item_start", 0):
                c.addtag_withtag("skill_graph", item)

        # Sidebar remains an explicit all-skill index.  Clicking/cursoring it is
        # handled by the same mouse hitboxes as the passive tree controls.
        if getattr(self, "tree_sidebar_collapsed", False):
            c.create_rectangle(0, 0, side, bh, fill="#06101d", outline="#183251", width=2)
            c.create_rectangle(8, 12, side-8, 48, fill="#09182a", outline=self.cls["col"], width=1)
            c.create_text(side/2, 30, text="»", fill=self.cls["col"], font=("Segoe UI Symbol", 14, "bold"))
            self.tree_control_rects.append((8, 12, side-8, 48, "sidebar"))
        else:
            c.create_rectangle(0, 0, side, bh, fill="#06101d", outline="#183251", width=2)
            c.create_rectangle(12, 12, side-12, 90, fill="#081426", outline=self.cls["col"], width=2)
            c.create_text(22, 28, anchor="w", text="SKILL TREE", fill="#ffffff", font=("Segoe UI", 14, "bold"))
            c.create_text(22, 48, anchor="w", text=f"{self.cls['name']}  •  ALL ACTIVE SKILLS", fill=self.cls["col"], font=("Segoe UI", 7, "bold"))
            c.create_text(22, 66, anchor="w", text=f"{self.skill_pts} SKILL POINTS LEFT  •  roots are free", fill=C_GOLD, font=("Segoe UI", 7, "bold"))
            c.create_text(22, 82, anchor="w", text="12 skill constellations • each has 3 paths + 2 capstones", fill="#6680a3", font=("Segoe UI", 5))
            c.create_text(20, 108, anchor="w", text="ALL SKILLS", fill="#7f97b8", font=("Segoe UI", 7, "bold"))
            rows = self.skill_lines(); row_h = 29
            for i, line in enumerate(rows):
                yy = 121 + i*row_h
                level = self.skill_level(line["id"])
                owned = sum(1 for nid in self.skill_nodes_for_line(line["id"]) if nid in self.skill_alloc)
                c.create_rectangle(18, yy, side-18, yy+row_h-4, fill="#091726", outline="#132a43", width=1)
                c.create_text(25, yy+7, anchor="w", text=f"{line['slot']:<5} {line['name'][:24]}", fill=line["col"], font=("Segoe UI", 5, "bold"))
                c.create_text(side-24, yy+7, anchor="e", text=f"LV {level}", fill=C_GOLD if level>1 else "#556f91", font=("Segoe UI", 5, "bold"))
                c.create_text(25, yy+18, anchor="w", text=f"{owned:02d} owned  •  3 paths  •  2 caps", fill="#5e789a", font=("Segoe UI", 4))
            y = 121 + len(rows)*row_h + 7
            c.create_text(20, y, anchor="w", text="NODE LANGUAGE", fill="#7f97b8", font=("Segoe UI", 6, "bold"))
            c.create_text(20, y+17, anchor="w", text="MINOR → NOTABLE → MAJOR → MASTERY", fill="#5d799b", font=("Segoe UI", 5, "bold"))
            c.create_text(20, y+31, anchor="w", text="CAPSTONE = permanent branch choice", fill="#5d799b", font=("Segoe UI", 5, "bold"))
            c.create_text(20, bh-57, anchor="w", text="LMB allocate  •  RMB refund", fill=C_CYAN, font=("Segoe UI", 6, "bold"))
            c.create_text(20, bh-41, anchor="w", text="DRAG pan  •  WHEEL zoom", fill="#6781a4", font=("Segoe UI", 6))
            c.create_text(20, bh-25, anchor="w", text="H sidebar  •  F fit all  •  TAB switch trees", fill="#526d8e", font=("Segoe UI", 5, "bold"))

        # No persistent graph labels; the floating node inspector is the text layer.
        self._draw_tree_tabs()
        self._draw_tree_toolbar()

