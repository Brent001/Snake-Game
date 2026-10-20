# v31 — Performance, FPS Caps, and Pixel HUD

## Performance
- Target frame cap defaults to 60 FPS.
- FPS CAP setting supports 30 / 60 / 90 / 120 / UNLIMITED (0).
- Frame pacing is applied consistently to title, menus, trees, and gameplay instead of hard-capping menus at 30 FPS.
- The title page now bakes the expensive skyline / floor / sun background into a cached PhotoImage per window size and class palette.
- Only a small pixel-star, spark, window-light, scan-beam, and crawler layer is animated each frame.
- Removed per-glyph title wobble as a per-frame image creation hotspot; the title now uses one cached pixel image with low-amplitude whole-title motion and occasional glitch.

## HUD redesign
- Removed the old Tk header/footer from gameplay so the art is no longer mixed with modern text widgets.
- Rebuilt gameplay HUD with pixel-art frames, stepped health/stamina/XP bars, pixel-font labels, class plate, resource chip, buff chip, signature readout, and redesigned 12-skill hotbar.
- Added lightweight animated pixel accents without re-rendering the entire HUD every frame.

## Validation
- Python compilation passes for modified modules.
- Tree rendering smoke test passes for passive and skill trees.
- UI smoke test passes including sidebar toggle and all 12 active-skill trees.
- Title benchmark under Xvfb: ~2.3 ms average draw/update per frame after warm-up (~440 FPS equivalent before the configured cap).
- Settings screen benchmark: ~15.6 ms average (~64 FPS equivalent).
