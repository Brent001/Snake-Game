Touhou Snake Dungeon - Gameplay/Visual Upgrade

This build expands the boss chambers and adds animated biome presentation.

Major changes:
- Boss arenas expanded from 24x18 to 34x24 cells.
- Larger, more decorative dungeon rooms with more floor space and props.
- Three arena mechanics: delayed danger sigils, rotating sweep beams, and falling shards.
- Mechanics are telegraphed before damage to keep them readable/fair.
- Enemy death animations now persist briefly with expanding particles.
- Player death has a burst/particle animation.
- Boss final defeats now use a spell-card-break death sequence before the reward state.
- All six biome backgrounds receive animated atmosphere layers.
- Forest and outdoor biomes have more grass/ground cover.
- Frost Moon has lunar ground details: frost blades, ice shards, exposed ore, craters, pylons and drifting lunar dust.
- Frost Moon remains a moon-surface setting; no second moon is shown in its sky.


=== v2: baked scenery, themed arenas, signature boss skills ===

PERFORMANCE (measured with real Tk under Xvfb; canvas items per frame / python build time per frame)
  outdoors            850-1290 items, 12-16 ms   ->   310-440 items,  9 ms
  boss arena (idle)  1930-2480 items, 17-22 ms   ->   135-150 items,  8-11 ms
  boss fight frame   2180-2620 items, 21 ms      ->   240-270 items,  9-10 ms (p95 14-18 ms)
How: scenery is painted ONCE into pixel-art images (pure python PNG encoder, still tkinter-only) and drawn as a few
create_image calls. Binary-alpha (dithered) images are nearly free for Tk; full-screen translucent ones cost ~8 ms, so
none are used. New files: render/pixelart.py, render/scenery.py, render/world_scene.py, render/boss_fx.py.
Assets are pre-baked while a menu is open (warm_scenery) so nothing is painted mid-fight.

BIOMES  Each biome has its own dithered horizon (parallax sky + silhouette layers, day/night variants), drifting mist,
  edge vignette, baked ground decor (16x16-cell chunks) and ambience particles: lunar dust + shooting stars (Frost Moon),
  snow (Misty Lake), fireflies + spores (Forest of Magic), embers + bats (Scarlet Mansion), spirit flames + petals
  (Netherworld), sakura (Hakurei Shrine).

ARENAS  Rebuilt as one themed image each: frozen-lake snowflake sigil, Marisa's hexagram + mushroom ring, red-carpet
  hall with a throne dais and stained-glass light, Netherworld spirit rings, shrine yin-yang courtyard. Brick walls,
  door frame, torches (animated flames). Resized 34x24 -> 30x16 so the whole room fits a 960x600 window (the old room
  was cropped by the camera). Outdoor decor no longer draws on top of the arena. Spell cards add an animated
  background aura and tint the vignette, as in the series.

BOSS SKILLS (game/systems/boss_skills.py, data in data/bosses.py) - all telegraphed
  Cirno    Icicle Fall (falling icicle lanes) . Frozen Ground (slowing ice patches) . Perfect Freeze (bullets freeze in
           mid-air, then shatter in random directions)
  Marisa   Broom Dash (dash with a star trail) . MASTER SPARK (charge, lock, sweeping mega-laser)
  Remilia  Bat Transformation (vanishes - untargetable - and reappears) . Spear the Gungnir (aim line, fast spear) .
           Vampire Kiss (lunge; a hit drains you and heals her)
  Yuyuko   Ghostly Veil (expanding death rings with a safe arc) . Fan Dance (rotating fans) . ghost butterflies that
           fade to harmless outlines and revive
  Reimu    Fantasy Seal (orbs that lock on) . Evil-Sealing Circle (closing amulet ring with a gap) .
           Oni-Binding Circle (crossing seal lines) . Hakurei Warp
  Bullets are now Touhou-style baked sprites (orb, rice, knife, amulet, ice, star, butterfly). Frost applies a new
  `slow_t` status (movement x1.55 slower).

Also: tools/bench stub tkinter was missing methods and crashed on the original zip; fixed.
Not changed: wall edge drawing (still ~100-200 items in wall-heavy views) - the next hotspot if you want more FPS.

=== v3: boss dungeons behind portals, new SFX, lighter edge ===
- Boss arenas are no longer on the overworld. Each biome has a portal (old arena site); stepping in teleports you to a
  56x36 dungeon in a separate map strip. After the fight the exit door is a return portal. Reimu's portal needs 4 fragments.
- Sound effects from Taisei + Touhou Pixel Dungeon; audio.py now overlaps effects and keeps the ambience loop
  (pygame if installed, else Windows MCI, else winsound). Optional: pip install pygame.
- Screen-edge dither (the x/+ marks) is off in daylight and only a thin rim at night.
- Danmaku-pack bullet sprites replace the hand-drawn orb/star/rice/knife/amulet/ice/butterfly shapes.
