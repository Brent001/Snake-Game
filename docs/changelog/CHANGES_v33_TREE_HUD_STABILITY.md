# v33 — Tree + HUD Stability Fixes

## Runtime crash fixes
- Imported `describe()` into the skill-tree system so node allocation feedback no longer raises `NameError`.
- Made legacy/compact `slash` effect payloads safe in the renderer so boss melee effects cannot raise a tuple-unpack `ValueError`.

## Tree performance
- Passive and active skill tree static graphs are retained and are no longer rebuilt every animation frame.
- Hover/tooltip layers only rebuild when the pointer/target changes.
- Mouse dragging moves the cached graph with a Canvas tag instead of redrawing hundreds of nodes/edges per motion event.
- Hit-test ordering for large node sets is cached.
- Removed duplicate passive-tree toolbar rendering that was accumulating Canvas items every frame.
- Tree tab/fit transitions invalidate the appropriate retained layers.

## HUD layout
- Bottom status and signature displays use dedicated pixel-art plates above the hotbar, with fixed footprints so they do not overlap the skill bar.
