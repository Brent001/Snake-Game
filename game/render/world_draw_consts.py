"""Shared constant: the walls that are drawn by the generic terrain layer (the boss-arena rings are baked into the arena art)."""
from ..world.layout import ARENAS, arena_walls
from ..world.level import WALLS

RENDER_WALLS = WALLS - set().union(*(arena_walls(_a) for _a in ARENAS))
