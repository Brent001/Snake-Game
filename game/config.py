"""Global tuning constants and the UI colour palette."""

# ---------------------------------------------------------------- world / window
CELL = 30
GRID_W = 576           # whole map width (cells) - 2.25x the old area so every biome has room for a transition belt
WORLD_H = 396          # the open overworld occupies rows 0 .. WORLD_H-1
ARENA_W = 56           # boss dungeon interior (cells) - several screens big
ARENA_H = 36
ARENA_TOP = WORLD_H + 10   # first interior row of every dungeon; the dungeons live in a strip BELOW the overworld
GRID_H = ARENA_TOP + ARENA_H + 8   # full grid = overworld + dungeon strip (never visible from the overworld)
BOARD_W = 960          # starting canvas size - the window is resizable (F11 = fullscreen)
BOARD_H = 600
MMS = 3                # each minimap pixel covers MMS x MMS world cells
MM = 1.0 / MMS         # minimap pixels per cell
DAY_LEN = 240.0         # seconds for one full day (sunrise -> noon -> sunset -> midnight -> sunrise)
DAY_START = 0.04        # where in the cycle a new run begins: 0 = sunrise, .25 = noon, .5 = sunset, .75 = midnight
DAY_GRADE_STIPPLE = True    # dithered warm / cool colour wash over the world at dawn, dusk and night (Windows / X11 only)

# ---------------------------------------------------------------- timing
STEP_MS = 150
STEP_S = STEP_MS / 1000
FRAME_MS = 16
EFFECT_TIME = 0.4
ELEMENT_FX_TIME = 0.72
REACTION_FX_TIME = 0.95

# ---------------------------------------------------------------- combat / movement
SHOTS_PER_CHARGE = 3
SHOT_COOLDOWN = 0.18
SHOT_SPEED = 24
HIT_IFRAMES = 2.0
HIT_SHRINK_SEGMENTS = 5
RUN_MULT = 1.6         # right-click run speed
RUN_DRAIN = 24.0       # stamina per second while running
RESON_NODES = 5        # allocated nodes of one element needed for its Elemental Resonance

HEAD_HIT = 0.2
BOSS_R = 1.15
AMMO_CAP = 8
AMMO_REGEN_S = 0.45
MAX_BULLETS = 300
BOSS_PRESSURE_MIN = 0.34
BOSS_PRESSURE_MAX = 0.62
NUM_FRAGMENTS = 4

# ---------------------------------------------------------------- food / growth / impacts
FOOD_HP = 2.0          # max HP gained per food unit eaten (on top of the +1 length)
FOOD_HEAL = 8.0        # instant heal per food unit
FOOD_CAP = 60          # food units that still add max HP
MAX_LEN = 70           # longest the snake can grow
FOOD_COUNT = 560       # food scattered over the world at the start of a run
BUMP_FRAC = dict(wall=0.15, self=0.10, node=0.20, door=0.12)   # max-HP fraction lost per impact (before reductions)

# ---------------------------------------------------------------- colours
C_PAGE = "#080e1c"
C_BOARD = "#0b1426"
C_ZONE_EDGE = "#ff7a30"
C_GOLD = "#ffd34d"
C_GOLD_DIM = "#6b5514"
C_MINT = "#5dffb0"
C_MINT_DIM = "#1a5a40"
C_CYAN = "#7df9ff"
C_PINK = "#ff7a9c"
C_TEXT = "#cfe2ff"
C_MUTED = "#6f8ab5"

SNAKE_BODY = "#17120a"
SNAKE_EDGE_LO = "#e8892f"
SNAKE_EDGE_HI = "#ffe28a"
SNAKE_GLOW_LO = "#3d1d07"
SNAKE_GLOW_HI = "#a85a14"
SNAKE_CORE = "#fff1c2"

# ---------------------------------------------------------------- biome transitions
BLEND_BAND = 46.0      # width (cells) of the belt in which two neighbouring biomes mix (floor, foliage, walls)
CHUNK = 16             # baked terrain chunk side, in cells


# ---------------------------------------------------------------- optional GPU effects pipeline
# VFX are rendered by a ModernGL OpenGL 3.3+ compositor when pyglet + moderngl are installed.
# The full Tk UI/world remains as a compatibility layer; the GPU stage owns bloom/particles/rings.
GPU_VFX_TARGET_FPS = 120
GPU_VFX_HALF_RES_BLOOM = True
GPU_VFX_MAX_PARTICLES = 760
