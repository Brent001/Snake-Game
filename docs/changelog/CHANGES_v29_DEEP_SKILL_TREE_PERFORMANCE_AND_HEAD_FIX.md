# v29 — Deep Active Skill Tree, Functional Transformations, Performance + Head Motion Fix

## Snake head animation
- Restored the original shared snake-head silhouette from v28.
- Removed the large lateral head bob that made the head appear detached from the first body segment.
- Reduced attack lunge displacement and slowed head-angle interpolation so the head follows the body smoothly.
- Animation remains intentionally rough/subtle instead of redesigning the art.

## Active Skill Tree
- Expanded every class from 228 to **336 skill sockets** across all 12 active skills.
- Each skill now has deeper paths: minors, notables, majors, mastery, cross-links, and capstones.
- Added 9 new build-defining nodes per skill (3 per specialization path).
- Added explicit transformation concepts such as:
  - multi-shot / double-shot / triple-shot
  - ricochet / bounce
  - elemental payload / explosion
  - split projectiles
  - chain / reaction upgrades
  - defensive pulse / reflect / afterimage / stealth variants
- Cobra STRIKE/Bolt now has working multi-shot, ricochet, split and elemental explosion behavior from skill allocations.
- Volley receives the same projectile transformation framework.
- Spit supports multi-lane, bounce, explosive and reaction-oriented upgrades.
- Dash, Coil, Shed, Heat Sense, Scent, Rattle, Camouflage, Bulwark and Signature V received additional functional branch effects.

## Skill-tree performance
- The active skill tree no longer rebuilds hundreds of Tk Canvas objects every frame.
- The full constellation is cached and only rebuilt when tree state changes (allocation, pan, zoom, hover, class, sidebar state).
- Mouse-following tooltip and allocation feedback are drawn as small dynamic overlays.
- Benchmark on 1366x730 virtual display:
  - initial skill-tree render: ~0.06s
  - cached render: ~0.001s/frame
  - hover rebuild: ~0.018s/change

## Validation
- 336 nodes per class, 4 classes.
- All skill roots reach every node in their skill graph.
- Python modules compile successfully.
- UI smoke test passes.
- Combat smoke test passes for Viper, Python, Cobra and Mamba.
