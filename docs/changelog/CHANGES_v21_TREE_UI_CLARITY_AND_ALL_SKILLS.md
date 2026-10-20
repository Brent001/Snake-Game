# v21 — Tree UI Clarity + Complete Active Skill Tree

## PASSIVE TREE
- Added a responsive **FIT TREE** view. The full 175-node passive constellation is centered and scaled to the current window instead of opening zoomed into the middle and clipping outer districts.
- Compressed the passive constellation vertically during rendering so the large graph can use a useful zoom on 1366×730/laptop-sized windows.
- Removed the old radial background spokes that looked like extra passive links and made routes difficult to follow. Only subtle elliptical guides remain behind the actual graph connections.
- Reduced low-zoom socket silhouettes slightly and kept forgiving hitboxes, preventing nearby major/keystone sockets from visually touching.
- Kept route emphasis interactive: hovering a socket highlights a two-step neighborhood and its connecting edges while de-emphasizing unrelated routes.
- Added clearer directional chevrons on available allocation edges.
- The sidebar is independently collapsible and its optional sections can be shown/hidden without covering the graph.
- **KEYSTONE DOCTRINES** are now displayed as compact 3-column cards when opened, with descriptions moved to the node inspector rather than stacked in the sidebar.
- **BUILD STATS** are hidden by default and open as a compact numeric ledger (HP, lifesteal, regen, energy recharge, life on hit/kill, damage taken, armor).
- **LIVE COMBAT DETAILS** stays optional and never occupies the tree unless explicitly enabled.
- Toolbar now exposes `H SIDEBAR`, `J STATS`, `K KEYSTONES`, `L DETAILS`, and `F FIT TREE` on the passive tab.

## SKILL TREE
- Confirmed the active **SKILL TREE** contains every hotbar skill, not just the primary and V skills.
- The global overview contains all **12 active skills**: SHIFT Dash, LMB Strike/Fang Bite, Q Coil, E Shed, R Heat Sense, T Tongue/Scent, Y Spit, F Rattle, G Camouflage, Z Volley, C Bulwark, and V Signature.
- Every active skill has its own complete branching graph: free root, 3 specialization routes, Minor → Notable → Major progression, Mastery socket, cross-links, and 2 mutually-exclusive capstones.
- The complete active tree is **228 sockets per class (19 per skill × 12 skills)**.
- Added **FIT ALL SKILLS** so the 4×3 overview is centered and all skill clusters remain visible.
- Skill sidebar continues to index all 12 skills and their current socket levels.

## CONTROLS
- `1` / `P` = Passive Tree
- `2` / `S` = Skill Tree
- `H` = collapse/expand sidebar
- `J` = show/hide passive build stats
- `K` = show/hide passive keystone doctrines
- `L` = show/hide passive live details
- `F` / `HOME` = fit current tree
- Mouse drag = pan; mouse wheel = zoom
