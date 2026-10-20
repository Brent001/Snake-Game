# Repair Terminal v36 — Top HUD Space + Skill Node Glyphs

## Gameplay HUD
- Normal gameplay HUD now starts at the top edge instead of leaving a 40px reserve band.
- Player/class panel moves to y=8 during normal gameplay.
- Minimap moves to y=8 during normal gameplay and remains at y=48 only during boss fights so the boss bar keeps a clear lane.
- Pulse/resource panel remains directly below the minimap and uses the same map width.
- Existing removal of the old top decorative dot row is preserved.

## Skill Tree
- Added small pixel glyphs inside important sockets so the graph communicates function without permanent text.
- Major, Mastery, Notable, Root and Keystone nodes can show visual symbols for:
  - Multi-shot / fan / split
  - Bounce / ricochet / chain / echo
  - Explosion / burst / shockwave
  - Elemental / reaction / prism / toxin
  - Pierce / lance / artillery
  - Defense / shield / fortress / barrier
  - Healing / recovery / rebirth
  - Speed / dash / momentum
  - Critical / precision / execution
- Permanent skill-node labels remain disabled; details continue to use the floating hover inspector.

## Validation
- Python compileall passed.
- Tkinter tree render test passed under Xvfb at 1366x730.
