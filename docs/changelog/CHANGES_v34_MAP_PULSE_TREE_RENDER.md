# v34 — Map/Pulse HUD + Tree Render Cleanup

- Restored the old gameplay map placement: minimap is top-right.
- Moved PULSE / ENERGY / DMG / LEECH / element readout directly below the minimap, matching its width.
- Removed the duplicate top-right resource chip from the main HUD.
- Added a contact shadow under every visible snake body segment instead of only the head.
- Removed permanent active-skill node labels and skill names from the constellation; details are hover-only in the floating inspector.
- Reduced active-skill graph Canvas item count by collapsing long branch runs into polyline segments and removing duplicate connector shadows.
- Cached active-skill hitboxes so cursor/click handling remains responsive while panning.
- Removed viewport clipping that could silently omit tree nodes near the graph bounds.
- Adjusted passive-tree fit scale so the full creature-shaped tree stays inside the graph viewport.
