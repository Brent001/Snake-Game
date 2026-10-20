# v27 — Boss Supplies, Projectile Lifetimes, Direct Boss Pressure & Portal Travel

## Boss arena supplies
- Boss rooms now receive a one-time emergency cache at encounter start.
- 3 food pickups are placed at fixed readable positions.
- 2 pulse-energy charges are placed at fixed side positions.
- Supplies do not respawn between boss phases.
- Random overworld food spawning is paused while the boss encounter is active.

## Boss behaviour
- Added a direct lunge attack that predicts the player's current lane, telegraphs briefly, rushes toward the player and deals contact damage once per lunge.
- The lunge finishes with a targeted ranged projectile, so bosses alternate between direct pressure and ranged/danmaku pressure.
- Normal boss positioning now biases more strongly toward the player's lane instead of simply orbiting around the arena.
- Existing character-specific spell-card patterns remain active.

## Boss projectile reliability
- Boss projectiles now have a finite travel-distance budget and maximum age.
- Projectiles scale down during their final 22% of travel range and disappear cleanly.
- Special behaviours retain their intended movement (including Cirno's deliberate freeze), while non-frozen bullets cannot remain at zero velocity indefinitely.
- Aimed projectile bursts continue to use the live player's position and movement lead.

## Enemy projectile reliability
- Enemy ranged shots now carry the same finite-range / scale-down animation behaviour.
- Enemy bullets visibly shrink before their travel budget expires instead of simply blinking out.
- Existing stationary trap fields remain stationary and are rendered separately.

## Portal travel
- Entering a boss portal now has a short snake-travel portal animation.
- Returning from a dungeon uses the reverse animation.
- Player input/attacks are temporarily paused during the one-second travel effect so the transition reads as a deliberate action.

## Skill tree UI
- Skill node details now use a mouse-following floating tooltip like the passive-tree inspector.
- The tooltip automatically flips away from the window edge and is rendered after the nodes so text is never hidden underneath a node.
- Persistent node-name clutter on skill clusters was reduced; details appear on hover/ownership/important capstones.

## Passive tree camera/background
- The creature-shaped elemental backdrop now moves with the passive-tree pan instead of remaining pinned to the screen.
- Head, tail, elemental markers and title all follow the tree center when dragging.

## Validation
- Python compilation: PASS
- Tree UI smoke test: PASS
- Passive/skill render under virtual X display: PASS
- Portal transition render smoke test: PASS
- Boss supply and projectile simulation: PASS
