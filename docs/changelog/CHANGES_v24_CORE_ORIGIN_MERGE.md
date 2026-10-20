# v24 — Passive Core / Origin Merge

- Removed the separate passive-tree `SERPENT ORIGIN` socket from the player-facing graph.
- The class core is now the real starting socket and is automatically allocated on NEW GAME.
- Moved every class core to exact world center `(0, 0)` so the build starts in the visual center.
- Core now uses the old origin diamond language plus a class-color ring and elemental rays.
- Passive refund connectivity treats the class core as the immutable root of the graph.
- Updated hitboxes, labels, legend, and node-kind rendering for the new `CORE` node type.
- Active skill-tree roots are unchanged; this change only merges the passive origin into the passive class core.
