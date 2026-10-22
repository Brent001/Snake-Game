# Repair Terminal

Snake action-RPG built with Python 3.10+ and tkinter: open world, 6 biomes, Touhou-style boss spell cards,
Genshin-style element reactions and a 9-element skill tree.

## Run

    python -m pip install -r requirements.txt
    python main.py          # Python 3.10+; Tkinter is included with standard Python installs

### Touhou boss assets

Cirno, Marisa, Remilia and Reimu now use the **animated Touhou Pixel Characters by Code-Farmer** (`game/assets/bosses/`):
idle, walk, sword/broom swing, charge-up and ready poses in 4 directions, chosen from what the boss is doing
(standing, moving, dashing, casting, channelling) and facing the player. Defeated bosses lie down. Flandre is the Netherworld guardian replacement so the boss uses an animated model.

The five guardian bosses use the supplied **Touhou Mini 16x16 Pack by Majstek**: Cirno (Misty Lake), Marisa Kirisame (Forest of Magic), Remilia Scarlet (Scarlet Mansion Grounds), Flandre Scarlet (Netherworld replacement), and Reimu Hakurei (Hakurei Shrine). The original asset license is included at `game/assets/touhou/LICENSE.txt`.

The assets are licensed for non-commercial projects only and require credit to Majstek.


## Build and package

See [`docs/BUILDING.md`](docs/BUILDING.md) for the full setup and packaging guide. Quick commands:

- Windows executable: `scripts/build.ps1` (creates `dist/windows/RepairTerminal.exe`)
- Debian/Ubuntu package: `./scripts/build.sh deb` (creates a `.deb` under `dist/linux/`)
- Flatpak bundle: `./scripts/build.sh flatpak` (creates a `.flatpak` under `dist/linux/`)

Core gameplay uses the Python standard library plus Tkinter; `requirements.txt` documents the runtime setup, while packaging and optional GPU dependencies are kept separate.

## Controls

| Input | Action |
|---|---|
| W A S D / arrows | Move |
| **Left click** | Aim and repeat the class primary attack |
| Right click (hold) | Run |
| Shift | Dash |
| Space | Fire a pulse charge |
| **Q E R F C** | Five close-reach skill slots on the active bar |
| **X** | Switch between two class-specific skill bars |
| 1-9 / mouse wheel / [ ] | Switch element |
| Tab | Open passive / active skill trees |
| Esc / P | Pause menu |
| Enter | Respawn after dying |
| M / N / F11 | Minimap / restart / fullscreen |

The default skill slots are **Q, E, R, F, C** on both bars; each class has different skill assignments. Open **Settings → Key Bindings** to remap slots or the bar-switch key. Duplicate bindings and movement/global shortcuts are rejected.

## Gameplay additions

* **Home screen**: animated 8-bit synthwave menu (pixel font, neon grid, striped sun, blinking skyline, crawling snake),
  class select, controls screen and a futuristic pause menu. All mouse + keyboard driven.
* **Classes**: Viper (damage-over-time/setup), Python (tank/control), Cobra (ranged/reactions), Mamba (assassin/burst). Every class now has a unique V skill and a gated class lane in the skill tree.
* **Combat rework**: bosses now have larger spell-card HP pools, distinct attack rhythms, stronger arena hazards, rage scaling at low HP, and character-specific signature spells. The enemy roster is now 18 types / 3 per biome with shields, ambushes, traps, swarms and knife casters.

* **Elemental combat**: elemental attacks leave readable auras, reactions are the payoff, and transformative reactions scale from level + Elemental Mastery while amplifying reactions scale the triggering hit.

* **Evolutions** (skill tree, outer end of the Geo / Dendro / Electro spokes): Titan Python (tank), Spitting Cobra (ranged),
  Black Mamba (assassin). Forms change how LMB, Volley, Bulwark and Dash behave.
* **Impacts no longer kill**: hitting a wall / hazard / door / your own body costs a % of max HP and stops you. Press the
  opposite direction while blocked to reverse the snake. Dashes still stop safely. Tank gets -50% impact damage.
* **Food**: classic snake food (apples, gold apples). Each unit makes you longer *and* raises max HP (+ a small heal).
  Enemies drop food; food respawns around you. Tweak in `config.py` (FOOD_*, MAX_LEN, BUMP_FRAC).

## Performance notes

The old renderer deleted and re-created ~1,400 Tk canvas items every frame (up to ~2,000 on the menus). Each item is a
Tcl call plus a repaint, so the item count - not the game logic - was the bottleneck. What changed:

* **Merged geometry**: wall cells are merged into a few rectangles and collinear wall edges into long lines (cached per
  cell window); the floor is merged the same way. ~570 wall items -> ~100.
* **Cached images instead of vector spam**: 8-bit sprites, snake body segments, pixel-font text, menu art, panel
  scanlines, the grid, the menu sky/skyline and the minimap's static markers are rasterised once into `PhotoImage`s.
* **Adaptive quality** (`app.adapt_quality`): if the frame rate drops below ~30 fps the game sheds cosmetic layers
  (wall glow -> grid/decor + half the particles; stars and biome particles otherwise always stay on) and restores them when there is headroom.
* **Stars and biome particles** are tiny cached images (brightness quantised to a few steps), one cheap item each
  instead of an oval with a freshly mixed colour.
* **Cached colour mixing** (`utils.mix`) and a palette that is only rebuilt when the daylight level actually changes.
* **Frame pacing**: the loop sleeps only for the *remaining* frame budget instead of a fixed 16 ms after the work.
* **Threaded start-up**: world generation runs on a worker thread behind a loading screen (`main.py`).

`python tools/bench/compare.py` counts canvas items per frame headlessly (uses a stub `tkinter`, no display needed).

Why not GPU / more threads? Tk's canvas is a CPU/GDI renderer with no GPU path, Tk must be driven from the main thread,
and CPython's GIL stops threads from running Python code in parallel - so neither helps this architecture. A true GPU
renderer means porting the drawing layer to pygame-ce / moderngl / pyglet.

## Project structure

    repair_terminal/
    ├── main.py                  # entry point (creates the Tk window and starts the game)
    └── game/
        ├── app.py               # SnakeTerminal: window, game state, reset/respawn, main loop (composes all mixins)
        ├── config.py            # tuning constants (grid size, timings, combat numbers) + colour palette
        ├── utils.py             # rect(), mix(), same(), rounded_rect()
        │
        ├── data/                # STATIC DATA - no logic, safe to tweak
        │   ├── keybinds.py      # class-specific dual skill bars and key dispatch/balance
        │   ├── elements.py      # ELEMS, colours, reaction table, resonances, stat labels
        │   ├── tree_nodes.py    # skill tree nodes, positions, edges (TREE / EDGES / ADJ) + evolution FORM_NODES
        │   ├── classes.py       # Viper / Python / Cobra / Mamba (stats, colours, descriptions)
        │   ├── pixelfont.py     # 5x7 bitmap font for the 8-bit menus
        │   ├── biomes.py        # 6 biome styles + day/night palettes
        │   ├── bosses.py        # boss roster + spell-card phases
        │   ├── enemies.py       # enemy species, biome spawn table, UNIQUE champion names
        │   ├── skills.py        # hotbar skill definitions (keys shown on the hotbar)
        │   └── sprites.py       # 8-bit sprite grids + run-length compiler
        │
        ├── world/               # THE MAP
        │   ├── layout.py        # spawn, biome centres, boss arenas, save points, biome noise
        │   └── level.py         # procedural generation (walls, hazard nodes, pickups, spawns) -> WALLS, NODES, ...
        │
        ├── systems/             # GAMEPLAY LOGIC (mixins used by SnakeTerminal)
        │   ├── stats.py         # build recompute, XP/levelling, Genshin-style damage formulas
        │   ├── skilltree.py     # allocate/refund rules, node hit-testing
        │   ├── input.py         # keyboard + mouse handlers (LMB attack, Q/E/R/T/Y... skills)
        │   ├── menu.py          # menu state machine: main / classes / controls / pause
        │   ├── food.py          # food spawning + eating (length + max HP)
        │   ├── abilities.py     # primary attack, bolts, shoot, dash, strike, coil, shed, heat, scent, spit, rattle, camo, volley, bulwark
        │   ├── combat.py        # damage intake, hit/kill enemies, drops, player shots
        │   ├── reactions.py     # auras, reactions, Bloom cores, Hyperbloom missiles
        │   ├── bosses.py        # arena locks, encounter flow, bullet patterns
        │   ├── enemies.py       # spawning, AI behaviours, enemy bullets, status ticking
        │   └── movement.py      # snake step, collisions, pickups, saves, win condition
        │
        └── render/              # DRAWING (mixins used by SnakeTerminal)
            ├── world_draw.py    # draw() pipeline, camera helpers, floor/sky/decor/walls/pickups
            ├── entities.py      # sprites, enemies, bosses, bullets, effects, the snake
            ├── hud.py           # boss bar, vitals, hotbar, scent arrows, clock, overlays
            ├── tree_view.py     # skill tree screen
            ├── menu_view.py     # 8-bit synthwave home screen, class select, controls, pause menu
            ├── minimap.py       # minimap image + overlay
            └── ambient.py       # stars + drifting particles

## Where do I change...?

| I want to...                         | Edit                                  |
|--------------------------------------|---------------------------------------|
| Rebalance numbers (speed, ammo, ...) | `game/config.py`                      |
| Add/modify an enemy or its stats     | `game/data/enemies.py` (+ `sprites.py`)|
| Add a new enemy AI behaviour         | `game/systems/enemies.py`             |
| Add a boss or spell card             | `game/data/bosses.py` + `systems/bosses.py` (`run_pattern`) |
| Add skill-tree nodes / stats         | `game/data/tree_nodes.py` (+ `elements.py` LABEL) |
| Add a new element reaction           | `game/data/elements.py` REACT + `systems/reactions.py` |
| Add a new snake ability              | `data/skills.py`, `systems/abilities.py`, `systems/input.py` |
| Add / rebalance a class              | `game/data/classes.py`                |
| Add an evolution form                | `FORM_NODES` in `data/tree_nodes.py` + the `form_*` checks in `systems/abilities.py` |
| Tune food / wall-impact damage       | `game/config.py` (FOOD_*, MAX_LEN, BUMP_FRAC) |
| Change the menus                     | `render/menu_view.py` + `systems/menu.py` |
| Change map size / biome layout       | `config.py`, `world/layout.py`        |
| Change how something looks           | the matching file in `game/render/`   |

## Design notes

* `SnakeTerminal` is assembled from mixins, so every method still uses plain `self.` state exactly as in
  the original single-file version - behaviour is unchanged, only the code is organised.
* `data/` imports nothing from `systems/` or `render/`; `world/` only imports `data/` and `config`.
  Dependency direction: `config/utils -> data -> world -> systems/render -> app -> main`.


### Fairness + biome ambience update
- Player hits grant 2 seconds of invulnerability.
- Taking damage shortens the visible snake by 5 segments, while max HP and food progression are preserved. Removed segments regrow naturally.
- Each biome has an original procedural looping ambience. Frost Moon uses a cold lunar pad/wind-like texture inspired by its moonlit, turbulent Archaeolune atmosphere, without using Genshin audio.


### Pixel-art + chiptune overhaul
- Added dense biome-specific scenery: lunar craters/crystals, lake reeds/ice, magic forest trees/mushrooms, Scarlet fences/lamps/roses, Netherworld cherry trees/tombs/wisps, and shrine lanterns/prayer ropes/sakura.
- Replaced the previous ambience and SFX with original synthesized pulse/triangle/noise WAVs at a deliberately low-resolution retro-game character, inspired by the technical feel of 8-bit/GBA audio rather than copying any game's recordings or music.


## v7 combat feedback
The Genshin-inspired elemental reaction system remains active. Player bolts visibly carry their chosen element, apply elemental auras, and create dedicated hit/reaction VFX. Boss encounters now use more aggressive player-lane pressure and less frequent generic arena hazards so character-specific danmaku patterns are the focus. See `docs/changelog/CHANGES_v7_ELEMENTAL_BULLET_FEEDBACK_AND_BOSS_AI.md`.


## v18 - Passive Tree + Skill Tree
The old skill tree is now the PASSIVE TREE. A new class SKILL TREE levels your LMB attack and V skill into evolved versions. TAB opens the trees, 1 / 2 switches. See `docs/changelog/CHANGES_v18_PASSIVE_AND_SKILL_TREES.md`.

## Settings + credits

The title screen and pause menu now expose a SETTINGS screen for master/music/SFX/ambience volume,
VFX quality, automatic quality adjustment, screen shake, damage numbers, mute, and fullscreen. Settings
persist to `game/settings.json`.

The CREDITS screen includes the project team plus third-party audio, music, sprite, and technology
attributions. Third-party asset licenses remain bundled or referenced in `CREDITS.txt`.

## Upload this project to GitHub

The cleaned source archive can be pushed from your own computer with Git installed and signed in to GitHub. From the extracted `repair_terminal` folder:

- **Windows PowerShell:** `./scripts/upload_to_github.ps1`
- **Linux/macOS:** `./scripts/upload_to_github.sh`

These helpers initialize the local Git repository when needed, verify the `origin` URL, commit the cleaned project, and push to `https://github.com/Brentph505/snake-game`. They will stop if `origin` points to a different repository. If your GitHub repository has already received commits, reconcile those changes before retrying the push. GitHub authentication is handled by Git's normal credential manager; never paste a token into the script.
