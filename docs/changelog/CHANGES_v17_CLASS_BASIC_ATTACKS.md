# v17 - Distinct basic attack per class

Before: Viper, Python and Mamba all used the same STRIKE (a forward thrust). Only the Cobra (aimed venom bolt) was different.
Now every class has its own LEFT-CLICK attack with its own mechanic, visual, sound, cooldown and tree scaling.

| Class  | Basic attack | How it works |
|--------|--------------|--------------|
| VIPER  | **FANG BITE**  | Short, narrow, fast bite (hits the 2 closest enemies). Low direct damage, but each bite adds a venom stack (max x5, more DPS per stack). Bites on already-poisoned enemies deal +30%. Widow's Silence keystone: +60% bite damage while camouflaged. |
| PYTHON | **TAIL SLAM**  | Slow 360-degree sweep around the body. Big stun and knock-back, the outer ring ("tail tip") hits +25% harder, and every enemy caught feeds your shield (up to 4 enemies). |
| COBRA  | **VENOM BOLT** | Unchanged: aimed ranged elemental bolt. |
| MAMBA  | **VOLT SLASH** | Wide (~90 degree), long-reach lightning slash with aim assist. Stunned, frozen or <35% HP enemies take a guaranteed crit at double damage (EXECUTE). Every enemy hit arcs Electro to a nearby enemy (max 3 arcs). Kills refund stamina and shave dash cooldown; brief invulnerability while slashing. |

## Code
- `game/systems/abilities.py`: `primary_attack()` dispatches per class -> `fang_bite()`, `tail_slam()`, `blitz_jab()` (cobra bolt kept). The old `strike()` stays as a fallback.
- `game/systems/stats.py`: new skill profiles `fang`, `slam`, `jab`. They still read the existing tree stats (`lunge`, `strike_width`, `strike_stun`, `strike_venom`, `strike_cd`, `melee`, `mamba_executioner`, `viper_fang`), so existing skill-tree nodes keep working.
- `game/systems/combat.py`: `hit_enemy(..., force_crit=False)` (used by the Mamba finisher).
- `game/render/entities.py`: new effects `fang_bite`, `tail_slam`, `blitz_jab`, `blitz_arc`.
- `game/data/classes.py`: each class has a `basic` entry (name/label/colour/description); class-select text updated.
- `game/render/hud.py`: hotbar label (FANG / SLAM / BOLT / JAB) and crosshair colour follow the class.
- `game/render/tree_view.py`: LIVE SKILL ENGINE shows the class's own basic attack stats.
- `game/app.py`: Mamba combo state + effect timings.

## VFX pass 2
Attack effects redrawn to match the original strike's crisp pixel look (solid shapes + hard offset shadow + bright spine + pixel impact marks); no smooth curves, big rings or flickering random lightning.
- Fang Bite: two solid tapered fangs closing, white tips, green pixel drips.
- Tail Slam: one thick tapering tail-arc whipping 360 degrees, then a thin ground ring and dust blocks (slightly less shake).
- Blitz Jab: thin long thrust needle with a fixed zig-zag crackle; finisher is longer, wider and forked. Arc is a fixed zig-zag.

## Pass 3
- **Mamba basic attack replaced**: BLITZ JAB (thin, narrow, weak) -> VOLT SLASH (see table). New profile `volt` in `skill_profile()`; `blitz_jab` and its combo state were removed.
- **Tail Slam VFX rebuilt**: white-hot impact flash, thick shockwave ring with bright leading edge + trailing ring, glowing floor cracks, stone-spike crown, flying rubble and pixel dust. More hit-stop and shake plus a faint screen flash.
- **Volt Slash VFX**: wide crescent blade sweeping the whole arc with an echo crescent, crackling afterimage line, X impact and sparks; chained arcs are fixed zig-zags.
