# v4 changes
- Performance: ~39 ms -> ~10 ms per frame in the same scene. Walls, ground tint and foliage are baked into chunk images;
  hazards/pickups/food are culled with a spatial index; hotbar/HUD/clock are retained between frames.
- Foliage: it vanished whenever the auto-quality dropped to 0 (lag). Foliage, grid and walls are now always drawn.
- Map: 576x396 (2.25x area) with 46-cell biome transition belts (dithered floor, mixed foliage, blended wall colours, mixed enemies).
- Walls: generated as structures (rooms with doorways, ruins, rings, ponds, colonnades, torii avenues, hedge mazes) - game/world/structures.py.
- Audio: +35 sound effects (tools/assets/make_sfx2.py) and 14 music tracks (menu, 6 biomes, 5 bosses, game over, victory).
  Music needs pygame (pip install pygame) or Windows (MCI); otherwise only effects/ambience play.

# Boss models
- Cirno, Marisa, Remilia, Reimu: animated Code-Farmer sprite sheets (game/assets/bosses/*.png). Poses: idle, walk, swing, charge, ready, down.
- game/render/entities.py: boss_pose() picks pose + facing from boss state; frames are cut from the sheet with Tk `copy -from -zoom` (no PIL needed).
