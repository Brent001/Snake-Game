"""SnakeTerminal: window setup, game state, main loop. Behaviour lives in the mixins it inherits."""
import math
import time
import tkinter as tk
from collections import defaultdict

import random

from .config import (AMMO_CAP, AMMO_REGEN_S, BOARD_H, BOARD_W, C_BOARD, C_CYAN, C_GOLD, C_MINT, C_MUTED, C_PAGE,
    C_PINK, C_TEXT, CELL, DAY_LEN, DAY_START, EFFECT_TIME, ELEMENT_FX_TIME, REACTION_FX_TIME, FRAME_MS, GRID_H, GRID_W, NUM_FRAGMENTS, RUN_DRAIN, WORLD_H, MAX_LEN)
from .data.classes import CLASSES
from .data.biomes import STYLES
from .data.skills import SKILLS
from .utils import SpatialDict, SpatialSet, mix
from .world.layout import ARENAS, START_SNAKE, arena_at
from .world.level import BMAP, CHARGES, NODES, PICKUPS

from .audio import configure_audio, play_music, play_sound, stop_music
from .settings import load_settings, save_settings
from .systems.abilities import AbilitiesMixin
from .systems.bosses import BossMixin
from .systems.combat import CombatMixin
from .systems.enemies import EnemyMixin
from .systems.food import FoodMixin
from .systems.menu import FULL_MENUS, MenuMixin
from .systems.input import InputMixin
from .systems.movement import MovementMixin
from .systems.reactions import ReactionsMixin
from .systems.skilltree import SkillTreeMixin
from .systems.stats import StatsMixin
from .render.entities import EntityRenderMixin
from .render.fastcanvas import FastCanvas
from .render.hud import HudMixin
from .render.menu_view import MenuViewMixin
from .render.minimap import MinimapMixin
from .render.tree_view import TreeViewMixin
from .render.world_draw import WorldRenderMixin
from .render.world_scene import SceneMixin
from .render.boss_fx import BossFxMixin
from .render.vfx import VfxMixin


class SnakeTerminal(StatsMixin, SkillTreeMixin, InputMixin, MenuMixin, AbilitiesMixin, CombatMixin, ReactionsMixin,
        BossMixin, EnemyMixin, MovementMixin, FoodMixin,
        WorldRenderMixin, SceneMixin, BossFxMixin, VfxMixin, EntityRenderMixin, HudMixin, TreeViewMixin, MinimapMixin, MenuViewMixin):
    def __init__(self, root):
        self.root = root
        self.root.title("Repair Terminal")
        self.root.resizable(True, True)
        self.root.minsize(760, 560)
        self.root.configure(bg=C_PAGE)
        self.bw, self.bh = BOARD_W, BOARD_H
        self.vw, self.vh = self.bw / CELL, self.bh / CELL
        self.fullscreen = False

        header = self.header = tk.Frame(root, bg=C_PAGE, padx=18, pady=10)
        header.pack(fill="x", side="top")
        tk.Label(header, text="REPAIR TERMINAL", font=("Segoe UI", 16, "bold"), fg=C_TEXT, bg=C_PAGE).pack(side="left")
        self.biome_label = tk.Label(header, text="", font=("Segoe UI", 10, "bold"), fg=C_CYAN, bg=C_PAGE)
        self.biome_label.pack(side="left", padx=(18, 0))
        self.core_label = tk.Label(header, text="", font=("Segoe UI", 10, "bold"), fg=C_MUTED, bg=C_PAGE)
        self.core_label.pack(side="right", padx=(16, 0))
        self.ammo_label = tk.Label(header, text="", font=("Segoe UI", 10, "bold"), fg=C_MINT, bg=C_PAGE)
        self.ammo_label.pack(side="right", padx=(16, 0))
        self.lives_label = tk.Label(header, text="", font=("Segoe UI", 10, "bold"), fg=C_PINK, bg=C_PAGE)
        self.lives_label.pack(side="right", padx=(16, 0))
        self.frag_label = tk.Label(header, text="", font=("Segoe UI", 10, "bold"), fg=C_GOLD, bg=C_PAGE)
        self.frag_label.pack(side="right")
        self.len_label = tk.Label(header, text="", font=("Segoe UI", 10, "bold"), fg=C_CYAN, bg=C_PAGE)
        self.len_label.pack(side="right", padx=(16, 0))

        footer = self.footer = tk.Frame(root, bg=C_PAGE, padx=18, pady=8)
        footer.pack(fill="x", side="bottom")
        self.message_label = tk.Label(footer, text="", font=("Segoe UI", 9), fg=C_MUTED, bg=C_PAGE)
        self.message_label.pack(side="left")

        self.canvas = FastCanvas(root, width=self.bw, height=self.bh, bg=C_BOARD, highlightthickness=0)
        self._ret = {}                    # retained HUD layers: name -> signature (see HudMixin.retained)
        self.canvas.pack(padx=12, fill="both", expand=True)
        self.canvas.bind("<Configure>", self.on_resize)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        # right-click: hold to RUN in the game, refund a node in the skill tree (Button-2 = right-click on macOS)
        self.canvas.bind("<ButtonPress-3>", self.on_rpress)
        self.canvas.bind("<ButtonRelease-3>", self.on_rrelease)
        self.canvas.bind("<ButtonPress-2>", self.on_rpress)
        self.canvas.bind("<ButtonRelease-2>", self.on_rrelease)
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<MouseWheel>", self.on_wheel)
        self.canvas.bind("<Button-4>", self.on_wheel)
        self.canvas.bind("<Button-5>", self.on_wheel)

        self.show_minimap = True
        self.time = 0.0
        self.dl = 0.0
        self.mouse = (0, 0)
        self.press = None
        self.moved = False
        self.tree_pan = [0.0, 0.0]
        self.tree_zoom = 0.75
        self.last_time = time.perf_counter()
        self.held_keys = set()
        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.bind("<KeyRelease>", self.on_key_release)
        self.root.bind("<FocusOut>", self.on_focus_out)
        self.pclass = "viper"
        self.chrome = True
        self.cursor = ""
        self.settings = load_settings()
        self.settings_sel = 0
        self.credits_scroll = 0.0
        self.menu_sel = 0
        self.class_sel = 0
        self.menu_back = "menu"
        self.menu_rects = []
        self.resume_state = "none"
        self.menu_t0 = 0.0
        self.quality = int(self.settings.get("vfx_quality", 2))
        self.fps_cap = int(self.settings.get("fps_cap", 60))
        self._user_quality_lock = False
        self._lag_ema = 1 / 60
        self._q_hold = 0.0
        self.apply_user_settings()
        self.reset_game()
        self.resume_state = "none"
        self.go_menu()
        self.root.protocol("WM_DELETE_WINDOW", self.close_game)
        self.animate()


    def apply_user_settings(self):
        """Apply persisted settings to rendering, audio and window state."""
        s = self.settings
        configure_audio(s["master_volume"], s["music_volume"], s["sfx_volume"], s["mute_audio"])
        self._user_quality_lock = not s["auto_quality"]
        self.fps_cap = int(s.get("fps_cap", 60))
        if self._user_quality_lock:
            self.quality = int(s["vfx_quality"])
        if bool(s["fullscreen"]) != bool(self.fullscreen):
            self.fullscreen = bool(s["fullscreen"])
            try:
                self.root.attributes("-fullscreen", self.fullscreen)
            except Exception:
                pass

    def play_zone_music(self):
        """Boss theme during a boss fight, otherwise the theme of the biome the snake is in."""
        if self.boss_active():
            play_music(f"boss{self.boss['idx']}", 0.6)
        else:
            play_music(f"biome{self.cur_biome}", 0.5)

    def close_game(self):
        try:
            self.shutdown_gpu_fx()
        except Exception:
            pass
        stop_music()
        self.root.destroy()

    def on_focus_out(self, _e=None):
        self.held_keys.clear()
        self.run_held = self.lmb_held = False
        if self.state == "playing":
            self.pause()

    def set_chrome(self, visible):
        """The tk header/footer bars are hidden on the full-screen menus."""
        if visible == self.chrome:
            return
        self.chrome = visible
        if visible:
            self.header.pack(fill="x", side="top", before=self.canvas)
            self.footer.pack(fill="x", side="bottom", before=self.canvas)
        else:
            self.header.pack_forget()
            self.footer.pack_forget()

    def on_resize(self, event):
        self.bw, self.bh = max(300, event.width), max(200, event.height)
        self.vw, self.vh = self.bw / CELL, self.bh / CELL

    # ------------------------------------------------------------ game state
    def reset_game(self):
        self.in_game = False
        self.resume_state = "ready"
        self.blocked = False
        self.lmb_held = False
        self.aim_ok = False
        self.shake = self.hurt_flash = 0.0
        self.init_vfx()
        self.shake_t = 0.0
        self.hit_stop = 0.0
        self.food_eaten = 0
        self.grow_q = 0
        self.bulwark_t = 0.0
        self.bulwark_pulse_t = 0.0
        self.skill_zones = []
        self.slow_t = 0.0
        self.lunge_dir = (0.0, -1.0)
        self.run_class = self.pclass
        self.cls = CLASSES[self.run_class]
        self.skill_set = 0  # Every new run starts on the primary skill bar.
        self.level = 1
        self.xp = 0.0
        self.points = 1                # PASSIVE points (passive tree)
        self.alloc = {f"{self.run_class}:core"}
        self.skill_pts = 1             # SKILL points shared by every active-skill tree branch
        # Every hotbar skill owns a free root socket in the global SKILL TREE.
        self.skill_alloc = {f"{self.run_class}:{key}:root" for key, _slot, _name, _col in SKILLS}
        self.skill_lv = {"basic": 1, "v": 1}
        self.tree_tab = "passive"      # "passive" | "skill"
        self.tree_tab_rects = []
        self.tree_control_rects = []
        self.skill_hits = []
        self.tree_sidebar_collapsed = False
        # Start with the optional inspection sections collapsed so the tree itself
        # is unobstructed. They can be opened from the visible toolbar.
        self.tree_show_keystones = False
        self.tree_show_stats = False
        self.tree_show_live = False
        self.tree_feedback = "BUILD ONLINE  •  allocate nodes to change combat"
        self.tree_feedback_t = 0.0
        self._tree_cursor = "arrow"
        self._passive_tree_static_key = None
        self._skill_tree_static_key = None
        self.portal_fx = None
        self.elem = "pulse"
        self.oculi = 0
        self.S = defaultdict(float)
        self.reson = set()
        self.unlocked = []
        self.snake = list(START_SNAKE)
        self.prev = list(START_SNAKE)
        self.direction = (0, -1)
        self.queue = []
        self.head_angle = -math.pi / 2
        self.acc = 0.0
        self.alpha = 1.0
        self.remaining = set()
        self.charges = SpatialSet(CHARGES)
        self.nodes = SpatialSet(NODES)
        self.pickups = SpatialDict(PICKUPS)
        self.defeated = set()
        self.collected = 0
        self.ammo = 0
        self.shots = []
        self.effects = []
        self.bullets = []
        self.ebullets = []
        self.floats = []
        self.timers = {}
        self.regen = 0.0
        self.invincible = 0.0
        self.death_t = 0.0
        self.boss_acc = 0.0
        self.boss = {"state": "dormant", "idx": 0, "phase": 0, "hp": 1, "t": 0.0, "timer": 0.0,
            "x": 0.0, "y": 0.0, "flash": 0.0, "spin": 0.0, "dir": 1, "flip": False}
        self.last_shot = -100.0
        self.state = "ready"
        self.tree_prev = "ready"
        self.cd = {k[0]: 0.0 for k in SKILLS}
        self.cdmax = {"dash": 1.3, "strike": 0.7, "coil": 12.0, "shed": 30.0, "heat": 20.0, "scent": 3.0,
            "spit": 4.0, "rattle": 14.0, "camo": 25.0, "volley": 7.0, "bulwark": 16.0, "class_skill": 12.0}
        self.dash_t = self.coil_t = self.heat_t = self.lunge_t = self.scent_t = 0.0
        self.class_skill_t = 0.0
        self.buff_dmg = self.buff_speed = 0.0
        self.buff_crit = self.buff_em = self.regen_t = self.camo_t = 0.0
        self.cores = []                # Bloom dendro cores [x, y, fuse]
        self.missiles = []             # Hyperbloom homing missiles [x, y, dmg, life]
        self.run_held = False
        self.running = False
        self.exhausted = False
        self.stam_delay = 0.0
        self.shield = 0.0
        self.decoy = None
        self.scent = []
        self.save = dict(cells=list(START_SNAKE), dir=(0, -1))
        self.visited_saves = set()
        self.recompute()
        self.hp = self.maxhp
        self.stam = self.maxstam
        self.init_enemies()
        self.init_foods()
        self.cur_biome = BMAP[START_SNAKE[0][1]][START_SNAKE[0][0]]
        self.banner_b = self.cur_biome
        self.banner_t = 1.0
        self.biome_transition = dict(active=False, t=1.0, dur=1.05, from_biome=self.cur_biome, to_biome=self.cur_biome)
        self.minimap_img = self.build_minimap_image()
        self.build_pal()
        self.play_zone_music()
        self.update_camera(0, instant=True)
        self.update_hud()
        self.set_message("WASD move | LMB attack | RMB run | Shift dash | Q E R F C skills | X switch skill set | 1-9 / wheel element | TAB trees | ESC pause")

    def respawn(self):
        cells = list(self.save["cells"])
        self.snake, self.prev = cells, list(cells)
        self.snake = list(self.snake[:MAX_LEN])
        self.grow_q = min(max(0, self.food_eaten), max(0, MAX_LEN - len(self.snake)))
        self.blocked = False
        self.bulwark_t = 0.0
        self.bulwark_pulse_t = 0.0
        self.skill_zones = []
        self.direction = self.save["dir"]
        self.queue = []
        self.head_angle = math.atan2(self.direction[1], self.direction[0])
        self.hp, self.stam, self.shield = self.maxhp, self.maxstam, 0.0
        self.bullets, self.ebullets, self.shots = [], [], []
        self.cores, self.missiles = [], []
        self.boss["state"] = "dormant"
        self.boss["death_t"] = 0.0
        self.dash_t = self.coil_t = self.lunge_t = self.camo_t = self.slow_t = 0.0
        self.running = self.exhausted = False
        self.invincible = 1.5
        self.decoy = None
        self.init_enemies()
        self.state = "ready"
        self.acc, self.alpha = 0.0, 1.0
        self.update_camera(0, instant=True)
        self.update_hud()
        self.resume_state = "ready"
        self.set_message("Respawned at your last save point    |    Press a direction key to continue")

    @property
    def boss_defeated(self):
        return 4 in self.defeated

    def set_message(self, text):
        self.message_label.config(text=text)

    def update_hud(self):
        self.frag_label.config(text=f"DATA FRAGMENTS  {self.collected} / {NUM_FRAGMENTS}")
        self.ammo_label.config(text=f"PULSE CHARGES  {self.ammo}")
        self.lives_label.config(text=f"LV {self.level}   PASSIVE {self.points}   SKILL {self.skill_pts}")
        self.len_label.config(text=f"LENGTH {len(self.snake)} / {MAX_LEN}   FOOD {self.food_eaten}")
        self.biome_label.config(text="\u25c8 " + STYLES[self.cur_biome]["name"], fg=STYLES[self.cur_biome]["tcol"])
        if self.state == "won":
            self.core_label.config(text="CORE DATA  COLLECTED", fg=C_CYAN)
        elif self.boss_defeated:
            self.core_label.config(text="CORE DATA  READY", fg=C_CYAN)
        elif self.collected == NUM_FRAGMENTS:
            self.core_label.config(text="CORE DATA  GUARDED", fg=C_PINK)
        else:
            self.core_label.config(text="CORE DATA  LOCKED", fg=C_MUTED)

    # ------------------------------------------------------------ day / night cycle
    def sun_state(self):
        """Continuous time-of-day model.

        phase 0 = sunrise, .25 = noon, .5 = sunset, .75 = midnight.  `elev` is the sun's height (-1 .. 1); daylight is a
        smoothstep of it, so dawn and dusk are long, gentle ramps instead of the old clamped sine (which was flat for
        most of the day and flipped between two sky images).  `tw` peaks while the sun is at the horizon."""
        ph = (self.time / DAY_LEN + DAY_START) % 1.0
        elev = math.sin(2 * math.pi * ph)
        x = max(0.0, min(1.0, (elev + 0.28) / 0.70))
        dl = x * x * (3 - 2 * x)
        tw = math.exp(-((elev - 0.04) / 0.20) ** 2)
        return ph, elev, dl, tw

    def daylight(self):
        return self.sun_state()[2]

    def day_label(self):
        ph, elev, dl, tw = self.sun_state()
        rising = ph < 0.25 or ph >= 0.75
        if tw > 0.55:
            return "SUNRISE" if rising else "SUNSET"
        if dl > 0.93:
            return "NOON" if abs(elev) > 0.93 else "DAY"
        if dl < 0.07:
            return "MIDNIGHT" if elev < -0.93 else "NIGHT"
        return "DAWN" if rising else "DUSK"

    def build_pal(self):
        ph, elev, dl, tw = self.sun_state()
        self.sun_phase, self.sun_elev, self.sun_tw = ph, elev, tw
        self.sun_rising = ph < 0.25 or ph >= 0.75
        dl = round(dl * 48) / 48        # quantised: palette (and every cache keyed on it) changes ~every 0.5 s
        if dl == self.dl and getattr(self, "pal", None):
            return
        self.dl = dl
        self.pal = [{k: mix(v[0], v[1], 0.0 if i == 0 else self.dl) for k, v in s["pal"].items()}
            for i, s in enumerate(STYLES)]

    # ------------------------------------------------------------ main loop
    def update_camera(self, dt, instant=False):
        hx, hy = self.snake_points()[0]
        ai = arena_at(hx, hy)
        if ai is not None:                       # inside a boss dungeon: follow the snake, never show past the walls
            a = ARENAS[ai]
            bx0, bx1, by0, by1 = a["x1"] - 3, a["x2"] + 4, a["y1"] - 3, a["y2"] + 4
        else:
            bx0, bx1, by0, by1 = 0, GRID_W, 0, WORLD_H

        def fit(v, lo, hi, view):
            return (lo + hi - view) / 2 if hi - lo <= view else max(lo, min(hi - view, v))
        tx = fit(hx + 0.5 - self.vw / 2, bx0, bx1, self.vw)
        ty = fit(hy + 0.5 - self.vh / 2, by0, by1, self.vh)
        if instant:
            self.cam_x, self.cam_y = tx, ty
        else:
            k = 1 - math.exp(-dt * 9)
            self.cam_x += (tx - self.cam_x) * k
            self.cam_y += (ty - self.cam_y) * k

    def tick_timers(self, dt):
        if self.hp < self.maxhp * 0.25 and self.state == "playing":
            play_sound("hp_low", volume=0.5, min_interval=1.8)
        for k in self.cd:
            self.cd[k] = max(0.0, self.cd[k] - dt)
        self.invincible = max(0.0, self.invincible - dt)
        for attr in ("dash_t", "coil_t", "heat_t", "buff_dmg", "buff_speed", "lunge_t", "scent_t",
                "camo_t", "buff_crit", "buff_em", "regen_t", "bulwark_t", "slow_t", "class_skill_t"):

            setattr(self, attr, max(0.0, getattr(self, attr) - dt))
        if self.decoy:
            self.decoy["t"] -= dt
            if self.decoy["t"] <= 0:
                self.decoy = None
        # right-click running burns stamina; running stops when you are exhausted
        if self.run_held and self.stam > 0 and not self.exhausted:
            self.running = True
            self.stam = max(0.0, self.stam - RUN_DRAIN * dt)
            self.stam_delay = 0.5
            if self.stam <= 0:
                self.exhausted = True
        else:
            self.running = False
        if self.exhausted and self.stam >= 20:
            self.exhausted = False
        if self.stam_delay > 0:
            self.stam_delay -= dt
        else:
            self.stam = min(self.maxstam, self.stam + 28 * max(0.2, 1 + self.S["stamr"] / 100) * dt)
        self.hp = min(self.maxhp, self.hp + (0.4 + self.S["regen"] + self.maxhp * self.S["regen_pct"] / 100 + (4.0 if self.regen_t > 0 else 0.0)) * dt)
        # Python's Bastion keystone turns BULWARK into a repeating defensive pulse.
        if self.bulwark_t > 0 and self.S["python_pulse"] > 0 and self.state == "playing":
            self.bulwark_pulse_t -= dt
            if self.bulwark_pulse_t <= 0:
                self.bulwark_pulse_t = 0.9
                prof = self.skill_profile("bulwark")
                hx, hy = self.snake_points()[0]
                for e in self.enemies:
                    if not e["dead"] and math.hypot(e["x"] - hx, e["y"] - hy) <= prof["radius"]:
                        self.hit_enemy(e, 10 * self.dmgm(), "geo", melee=True)
                        e["stun"] = max(e["stun"], prof["stun"] + 0.25)
                self.add_shield(6)
                self.effects.append([hx, hy, self.time, "blast", (prof["radius"], "#ffa23c")])
        self.regen += dt
        boss = self.boss_active()
        recharge_base = AMMO_REGEN_S if boss else 2.5
        recharge_rate = max(0.15, 1 + self.S["energy_recharge"] / 100)
        if self.regen >= recharge_base / recharge_rate:
            self.regen = 0.0
            if self.ammo < getattr(self, "energy_cap", (AMMO_CAP if boss else 5) + int(self.S["ammo"])):
                self.ammo += 1
                self.update_hud()

    def adapt_quality(self, real_dt):
        """Lower cosmetic detail automatically only when AUTO QUALITY is enabled."""
        if not self.settings.get("auto_quality", True):
            self.quality = int(self.settings.get("vfx_quality", 2))
            return
        self._lag_ema += (min(real_dt, 0.25) - self._lag_ema) * 0.08
        self._q_hold -= real_dt
        if self._q_hold > 0:
            return
        if self._lag_ema > 0.034 and self.quality > 0:          # under ~30 fps
            self.quality -= 1
            self._q_hold = 1.5
        elif self._lag_ema < 0.021 and self.quality < 2:        # comfortably above ~48 fps
            self.quality += 1
            self._q_hold = 4.0

    def animate(self):
        now = time.perf_counter()
        real_dt = now - self.last_time
        dt = min(real_dt, 0.1)
        self.last_time = now
        if self.state not in FULL_MENUS:
            self.adapt_quality(real_dt)
        else:
            self.warm_scenery()
        self.time += dt
        self.vfx_update(dt)
        bt = getattr(self, "biome_transition", None)
        if bt and bt.get("active"):
            bt["t"] += dt
            if bt["t"] >= bt["dur"]:
                bt["t"] = bt["dur"]
                bt["active"] = False
        self.build_pal()
        self.hurt_flash = max(0.0, self.hurt_flash - dt)
        self.tree_feedback_t = max(0.0, getattr(self, "tree_feedback_t", 0.0) - dt)
        self.death_t = max(0.0, getattr(self, "death_t", 0.0) - dt)
        pf = getattr(self, "portal_fx", None)
        if pf and pf.get("active"):
            pf["t"] += dt
            if pf["t"] >= pf["dur"]:
                pf["t"] = pf["dur"]
                pf["active"] = False
        if self.__dict__.get("shake_t", 0.0) <= 0:
            self.shake = max(0.0, self.shake - dt * 2.2)
        # Gameplay, trees and menu screens all use the canvas pixel UI; the old Tk header/footer no longer mix with the HUD art.
        self.set_chrome(False)
        # The old tree used the normal mouse pointer.  Crosshair is reserved for
        # gameplay aiming; trees and menus use a normal arrow/hand pointer.
        if self.state == "playing":
            want = "crosshair"
        elif self.state == "tree":
            want = getattr(self, "_tree_cursor", "arrow")
        else:
            want = "arrow"
        if want != self.cursor:
            self.cursor = want
            self.canvas.config(cursor=want)

        portal_busy = bool(getattr(self, "portal_fx", None) and self.portal_fx.get("active"))
        if self.state == "playing" and self.hit_stop <= 0 and not portal_busy:
            if self.lmb_held:
                self.primary_attack()
            self.update_food(dt)
            self.tick_timers(dt)
            self.acc += dt
            ss = self.step_s()
            while self.acc >= ss and self.state == "playing":
                self.acc -= ss
                self.step()
                ss = self.step_s()
            if self.state == "playing":
                self.alpha = min(1.0, self.acc / ss)
                self.banner_t -= dt
                self.update_shots(dt)
                self.update_boss(dt)
                self.update_skill_zones(dt)
                self.update_enemies(dt)
                self.update_cores(dt)
                self.update_missiles(dt)
                self.update_ebullets(dt)
                if self.state == "playing":
                    self.update_bullets(dt)
                hx, hy = self.snake[0]
                nb = BMAP[hy][hx]
                if nb != self.cur_biome:
                    old_biome = self.cur_biome
                    self.cur_biome = nb
                    self.banner_b = nb
                    self.banner_t = 1.15
                    self.biome_transition = dict(active=True, t=0.0, dur=1.05,
                        from_biome=old_biome, to_biome=nb)
                    if not self.boss_active():
                        self.play_zone_music()
                    self.update_hud()

        target = math.atan2(self.direction[1], self.direction[0])
        diff = (target - self.head_angle + math.pi) % (2 * math.pi) - math.pi
        # The head should follow the body smoothly rather than snapping around the
        # first segment.  A slower angular response preserves the rough animation.
        self.head_angle += diff * min(1.0, dt * 9)

        fx_limits = {"save": EFFECT_TIME * 2, "element_cast": 0.52, "element_hit": ELEMENT_FX_TIME, "reaction_burst": REACTION_FX_TIME,
                     "boss_hit": 0.55, "boss_cast": 1.05, "blast": 0.6, "slash": 0.38, "fang_bite": 0.30, "tail_slam": 0.62, "volt_slash": 0.30, "volt_arc": 0.25, "spit": 0.45, "death_boss": 1.7, "death_enemy": 0.8, "death_player": 1.5}
        self.effects = [fx for fx in self.effects if self.time - fx[2] <= fx_limits.get(fx[3], EFFECT_TIME)]
        self.floats = [f for f in self.floats if self.time - f[4] < 0.9]
        self.update_camera(dt)
        sx = sy = 0.0
        if self.settings.get("screen_shake", True) and self.shake > 0 and self.state == "playing":
            # Directionless random shake plus a deterministic low-frequency wobble feels heavier than a constant jitter.
            amp = self.shake * 0.70
            phase = self.time * 47.0
            sx = (math.sin(phase) * 0.55 + random.uniform(-1, 1) * 0.45) * amp
            sy = (math.cos(phase * 0.83) * 0.55 + random.uniform(-1, 1) * 0.45) * amp
        self.cam_x += sx
        self.cam_y += sy
        self.draw()
        self.cam_x -= sx
        self.cam_y -= sy
        # Frame pacing: honor the user-selected cap everywhere. 60 FPS is the default target.
        # Menus used to be hard-capped at 30 FPS while still performing a full canvas redraw; the combination
        # made the title page feel both laggy and inconsistent.
        spent = int((time.perf_counter() - now) * 1000)
        cap = int(getattr(self, "fps_cap", 60))
        frame_ms = max(1, int(round(1000.0 / cap))) if cap > 0 else 1
        self.root.after(max(1, frame_ms - spent), self.animate)
