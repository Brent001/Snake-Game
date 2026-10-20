# v18 - Passive Tree + new class Skill Tree

## What changed
The old "Ascension Grid / skill tree" is a passive tree (stat nodes, keystones), so it is now called the **PASSIVE TREE**.
A brand new per-class **SKILL TREE** sits beside it: each class has two active skills that level up (5 tiers) into stronger,
renamed versions. Press **TAB** to open the trees, then **1** = Passive Tree, **2** = Skill Tree (or click the tabs).

## Two separate point pools
| Pool | Spent on | Earned |
|------|----------|--------|
| PASSIVE points | Passive tree nodes | level-up, Oculi, unique-enemy kills (as before) |
| SKILL points | Skill tree tiers | +1 per level-up, +1 per unique-enemy kill, 1 at the start |

Tier costs: Lv2 = 1, Lv3 = 1, Lv4 = 2, Lv5 = 2 (6 points per skill, 12 per class). Tiers are taken in order.
LMB = level up, RMB = refund the top tier (points returned).

## Skill lines (LMB = basic attack, V = signature skill)
| Class | LMB line | V line |
|-------|----------|--------|
| VIPER | Fang Bite > Deep Fang > Twin Fangs > Neurotoxin > Widow's Kiss | Venom Trail > Toxic Wake > Corrosive Trail > Blight Trail > Plague Nova |
| PYTHON | Tail Slam > Heavy Tail > Iron Tip > Earthshaker > World Breaker | Colossal Coil > Iron Grip > Crushing Coil > Titan Coil > World Coil |
| COBRA | Venom Bolt > Twin Bolt > Venom Lance > Triple Spit > Hydra Spit | Venom Barrage > Wide Barrage > Blast Barrage > Toxic Storm > Hydra Storm |
| MAMBA | Volt Slash > Long Blade > Chain Slash > Static Execution > Storm Cutter | Thundercoil > Static Coil > Stun Coil > Tempo Coil > Tempest Coil |

Every tier changes gameplay (extra bolts, more bite targets, wider slam, longer chains, extra V effects...). Each V tier also adds +1 to the
class-skill level (bigger radius/counts, shorter cooldown). The HUD hotbar and the V line show the evolved name.

## Code
- `game/data/skill_levels.py` (new): all skill lines, tier names, descriptions and stat bonuses. Add/tune tiers here.
- `game/systems/stats.py`: `recompute()` adds owned skill tiers to the stats; `skill_profile()` reads the new `sk_*` stats; new `bolt` profile.
- `game/systems/abilities.py`: basic attacks read the new profile fields; `v_evolve()` adds the per-tier extra V effects.
- `game/systems/skilltree.py`: tab switching, buy/refund tiers, click handling.
- `game/render/tree_view.py`: tab bar, renamed Passive Tree, new Skill Tree screen.
- `game/systems/input.py`, `game/render/hud.py`, `game/app.py`, menus: points display, keys, labels.
