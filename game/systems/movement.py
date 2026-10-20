"""Snake movement step, impacts, food, pickups, save points and win condition."""
import math

from ..config import BUMP_FRAC, C_CYAN, C_GOLD, C_MINT, NUM_FRAGMENTS, SHOTS_PER_CHARGE, MAX_LEN
from ..data.elements import ECOL, ELEMS
from ..world.layout import CORE
from ..world.level import BMAP, OCULI_PER_ELEM, SAVE_CELLS, WALLS
from ..audio import play_music, play_sound


class MovementMixin:
    def step(self):
        if self.queue:
            self.direction = self.queue.pop(0)
        old = list(self.snake)
        hx, hy = old[0]
        new = (hx + self.direction[0], hy + self.direction[1])
        eat = new in self.foods
        can_grow = len(old) < MAX_LEN
        grow = can_grow and (new in self.remaining or eat or self.grow_q > 0)
        body = old if grow else old[:-1]
        kind = ("wall" if new in WALLS else "node" if new in self.nodes else "door" if self.is_locked(new)
            else "self" if new in body else None)

        if kind:
            if self.dash_t > 0:             # a dash safely stops before obstacles
                self.dash_t = 0.0
                self.acc = 0.0
                self.prev = list(self.snake)
                return
            self.bump(new, kind)
            return
        self.blocked = False

        if self.grow_q > 0 and not eat and new not in self.remaining:
            self.grow_q -= 1
        self.snake.insert(0, new)
        if grow:
            self.prev = [old[0]] + old
            if new in self.remaining:
                self.remaining.discard(new)
                self.collected += 1
                play_sound("extra_life", volume=0.8)
                if self.collected < NUM_FRAGMENTS:
                    self.set_message(f"Data fragment recovered ({self.collected}/{NUM_FRAGMENTS})")
                else:
                    self.set_message("All fragments recovered    |    The Hakurei Shrine gate (map center) is open")
            self.update_hud()
        else:
            self.snake.pop()
            self.prev = old

        if eat:
            self._length_before_food = len(old)
            self.eat_food(new)
        if self.dash_t > 0 and self.S["form_mamba"] > 0:
            self.dash_slash()
        if new in self.charges:
            self.charges.discard(new)
            play_sound("charge_get", volume=0.7)
            self.ammo += SHOTS_PER_CHARGE + int(self.S["charges"])
            self.set_message("Pulse charge acquired    |    Space to shoot - 1-9 / mouse wheel to switch element")
            self.update_hud()
        if new in self.pickups:
            self.collect_pickup(new)
        if new in SAVE_CELLS:
            self.do_save(new)

        if self.check_portal(new):
            return
        self.check_boss_trigger()

        if new == CORE and self.boss_defeated:
            self.state = "won"
            play_music("victory", 0.6)
            play_sound("spellclear")
            self.prev = list(self.snake)
            self.alpha = 1.0
            self.set_message("Core data collected    |    Press N to play again")
            self.update_hud()

    def bump(self, cell, kind):
        """Hitting an obstacle hurts but no longer kills outright: you stop, take damage and must steer away."""
        self.prev = list(self.snake)
        self.blocked = True
        self.acc = 0.0
        self.effects.append([cell[0], cell[1], self.time, "spark"])
        play_sound("bump", volume=0.6, min_interval=0.2)
        if self.invincible > 0:
            return                                          # still recovering from the last hit: just stay put
        dmg = (self.maxhp * BUMP_FRAC[kind] + 5) * (1 - min(0.9, self.S["wallres"] / 100))
        if kind == "node":
            play_sound("trap", volume=0.7, min_interval=0.2)
            self.kill_node(cell)                            # ramming a hazard node destroys it
            self.effects.append([cell[0], cell[1], self.time, "boom"])
        if kind == "door":
            play_sound("portal_locked", volume=0.8, min_interval=0.3)
        what = {"wall": "wall", "node": "hazard", "door": "sealed gate", "self": "your own body"}[kind]
        self.hurt(dmg, f"You crashed into {what}", impact=True)
        if self.state == "playing":
            self.set_message(f"IMPACT! You hit {what} - turn away (press the opposite key to reverse the snake)")

    def reverse_snake(self):
        """When blocked the snake can flip around: the tail becomes the head."""
        if len(self.snake) < 2:
            return False
        self.snake.reverse()
        self.prev = list(self.snake)
        a, b = self.snake[0], self.snake[1]
        self.direction = (a[0] - b[0], a[1] - b[1])
        self.queue = []
        self.blocked = False
        self.head_angle = math.atan2(self.direction[1], self.direction[0])
        b = BMAP[self.snake[0][1]][self.snake[0][0]]
        play_sound("water" if b == 1 else "step_grass" if b in (2, 5) else "step_stone", volume=0.16, min_interval=0.12)
        return True

    def dash_slash(self):
        hx, hy = self.snake[0]
        for e in self.enemies:
            if not e["dead"] and e.get("dh", -9) < self.time - 0.5 and math.hypot(e["x"] - hx, e["y"] - hy) < 1.5:
                e["dh"] = self.time
                self.hit_enemy(e, 16 * self.dmgm() * (1 + self.S["melee"] / 100), self.elem, melee=True)

    def collect_pickup(self, cell):
        k = self.pickups.pop(cell)
        hx, hy = cell
        snd = {"heal": "heal", "regen": "heal", "stam": "puff", "elixir": "drink", "shield": "evoke", "xp": "extend", "ammo": "beacon",
            "dmg": "powersurge", "crit": "powersurge", "speed": "powersurge", "emorb": "zap"}
        play_sound("oculus" if k.startswith("oc_") else snd.get(k, "pickup"), volume=0.7)
        if k == "heal":
            self.heal(40)
        elif k == "xp":
            self.add_xp(45)
        elif k == "stam":
            self.stam = self.maxstam
            self.ammo += 1
            self.float_text(hx, hy - 0.6, "ENERGY", C_CYAN)
        elif k == "dmg":
            self.buff_dmg = 25.0
            self.float_text(hx, hy - 0.6, "DAMAGE x1.5", "#ff5d6c")
        elif k == "speed":
            self.buff_speed = 20.0
            self.float_text(hx, hy - 0.6, "HASTE", "#6fffd0")
        elif k == "shield":
            self.add_shield(40)
            self.float_text(hx, hy - 0.6, "BARRIER", C_GOLD)
        elif k == "regen":
            self.regen_t = 12.0
            self.float_text(hx, hy - 0.6, "REGENERATION", C_MINT)
        elif k == "crit":
            self.buff_crit = 20.0
            self.float_text(hx, hy - 0.6, "CRIT RATE +25%", C_GOLD)
        elif k == "elixir":
            for key in self.cd:
                self.cd[key] = 0.0
            self.stam = self.maxstam
            self.float_text(hx, hy - 0.6, "ELIXIR - COOLDOWNS RESET", "#e0a0ff")
        elif k == "ammo":
            self.ammo += 6
            self.float_text(hx, hy - 0.6, "+6 PULSE", C_MINT)
        elif k == "emorb":
            self.buff_em = 20.0
            self.float_text(hx, hy - 0.6, "MASTERY +100", ECOL["electro"])
        elif k.startswith("oc_"):
            el = k[3:]
            self.points += 1
            self.oculi += 1
            self.float_text(hx, hy - 0.8, f"{el.upper()}CULUS", ECOL[el])
            self.set_message(f"{el.capitalize()}culus collected ({self.oculi}/{len(ELEMS) * OCULI_PER_ELEM})   |   +1 passive point   |   TAB = passive tree")
        self.update_hud()

    def do_save(self, cell):
        x, y, dx, dy = SAVE_CELLS[cell]
        self.save = dict(cells=[(x, y), (x - dx, y - dy), (x - 2 * dx, y - 2 * dy)], dir=(dx, dy))
        first = cell not in self.visited_saves
        play_sound("save", volume=0.8)
        play_sound("secret", volume=0.5)
        self.visited_saves.add(cell)
        self.hp, self.stam = self.maxhp, self.maxstam
        self.effects.append([x, y, self.time, "save"])
        self.float_text(x, y - 1.0, "SAVED", "#fff1a0")
        self.set_message("* The darkness fades.  You are filled with DETERMINATION.    (HP restored, respawn point set)"
            if first else "* You are filled with DETERMINATION.    (HP restored, respawn point set)")

    def snake_points(self):
        a = self.alpha
        return [(px + (x - px) * a, py + (y - py) * a) for (x, y), (px, py) in zip(self.snake, self.prev)]
