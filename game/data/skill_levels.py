"""Compatibility notes for the old linear skill-level data.

The game no longer uses a five-tier linear skill tree. Active skills now live in
``game/data/active_skill_tree.py`` as branching graphs. Stats are granted by the
allocated sockets there, while ``StatsMixin`` still exposes ``sk_basic_lv`` and
``sk_v_lv`` as milestone levels for existing V-skill evolution code.
"""
from .active_skill_tree import BLUEPRINTS

MAX_TIER = 5
TIER_COST = (0, 1, 1, 1, 1)
SKILL_LINES = {}

