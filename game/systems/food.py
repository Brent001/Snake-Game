"""Classic snake food, upgraded: every bite makes you LONGER and raises your MAX HP (life size)."""
import math
import random

from ..utils import SpatialDict
from ..config import (C_GOLD, C_MINT, FOOD_CAP, FOOD_COUNT, FOOD_HEAL, FOOD_HP, GRID_H, GRID_W, WORLD_H, MAX_LEN)
from ..world.layout import ARENA_ZONE, START_SNAKE
from ..world.level import SAVE_CELLS, WALLS

FOOD_SIZE = {"food": 1, "gold": 3}
from ..audio import play_sound


class FoodMixin:
    def food_cell_ok(self, c):
        return (0 < c[0] < GRID_W - 1 and 0 < c[1] < GRID_H - 1 and c not in WALLS and c not in self.nodes
            and c not in ARENA_ZONE and c not in self.pickups and c not in self.charges and c not in SAVE_CELLS
            and c not in self.remaining and c not in self.foods and c not in self.snake)

    def init_foods(self):
        rnd = random.Random()
        self.foods = SpatialDict()
        self.food_t = 0.0
        sx, sy = START_SNAKE[0]
        tries = 0
        while len(self.foods) < 8 and tries < 400:                 # a few snacks right next to the spawn
            tries += 1
            c = (sx + rnd.randint(-12, 14), sy + rnd.randint(-12, 8))
            if self.food_cell_ok(c) and abs(c[0] - sx) + abs(c[1] - sy) > 3:
                self.foods[c] = "food"
        tries = 0
        while len(self.foods) < FOOD_COUNT and tries < 20000:
            tries += 1
            c = (rnd.randint(1, GRID_W - 2), rnd.randint(1, WORLD_H - 2))
            if self.food_cell_ok(c):
                self.foods[c] = "gold" if rnd.random() < 0.07 else "food"

    def update_food(self, dt):
        """Keeps overworld food around the player; boss arenas use one-time fixed supplies."""
        if getattr(self, "boss", {}).get("state") in ("banner", "fight", "dying"):
            return
        self.food_t += dt
        if self.food_t < 2.0:
            return
        self.food_t = 0.0
        hx, hy = self.snake[0]
        if len(self.foods) > FOOD_COUNT + 80:                      # food spawned around the player used to pile up forever
            far = [c for c in self.foods if abs(c[0] - hx) > 70 or abs(c[1] - hy) > 50][:60]
            for c in far:
                del self.foods[c]
        near = sum(1 for _ in self.foods.near(hx - 21, hy - 15, hx + 21, hy + 15))
        if near >= 6:
            return
        for _ in range(12):
            ang, r = random.uniform(0, 2 * math.pi), random.uniform(6, 18)
            c = (int(hx + math.cos(ang) * r), int(hy + math.sin(ang) * r))
            if self.food_cell_ok(c):
                self.foods[c] = "gold" if random.random() < 0.06 else "food"
                break

    def eat_food(self, cell):
        kind = self.foods.pop(cell)
        play_sound("gold" if kind == "gold" else "eat", volume=0.7)
        size = FOOD_SIZE[kind]
        before_len = int(getattr(self, "_length_before_food", len(self.snake)))
        # Gold food is worth 3 units, but the snake can never exceed MAX_LEN.
        room = max(0, MAX_LEN - before_len - self.grow_q)
        gained_len = min(size, room)
        if gained_len > 1:
            self.grow_q += gained_len - 1                            # the current step already supplied 1 segment
        if len(self.snake) > MAX_LEN:
            del self.snake[MAX_LEN:]
            self.grow_q = 0
        self.food_eaten += size
        before = self.maxhp
        self.recompute()
        gained = self.maxhp - before
        self.hp = min(self.maxhp, self.hp + gained)
        self.heal((FOOD_HEAL + self.S["foodheal"]) * size)
        hx, hy = cell
        tag = (f"+{gained_len} LENGTH" if gained_len else "MAX LENGTH") + (f"   +{gained:.0f} MAX HP" if gained >= 1 else "")
        self.float_text(hx, hy - 0.7, tag, C_GOLD if kind == "gold" else C_MINT)
        self.effects.append([hx, hy, self.time, "hit"])
        self.update_hud()
