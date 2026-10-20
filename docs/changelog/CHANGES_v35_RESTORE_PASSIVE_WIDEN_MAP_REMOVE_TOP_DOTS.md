# v35 — Restore Passive Tree / Widen Minimap / Clean Top HUD

- Restored the passive-tree renderer to the v33 layout and visual behavior while keeping the v34 optimized active Skill Tree renderer.
- Restored the passive-safe tree coordinate path; the v34 passive transform override is not used.
- Widened the top-right minimap to 1.25x using a cached PhotoImage zoom/subsample path.
- Kept the PULSE/ENERGY/DMG/LEECH/FOOD panel directly below the map at the same width.
- Removed the five animated decorative dots from the top of the gameplay HUD.
- Increased boss-bar right-side reservation to match the wider minimap.
