"""Procedural background ambience: twinkling stars and drifting biome particles."""
import random

_r = random.Random(7)
STARS = [(_r.random() * 2400, _r.random() * 1400, _r.random() * 6, _r.choice((1, 1, 2, 3))) for _ in range(90)]
PARTS = [(_r.random() * 2400, _r.random() * 1400, 0.5 + _r.random(), _r.random() * 6) for _ in range(60)]
