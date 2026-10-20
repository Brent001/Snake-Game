# v33 — Tree Performance + HUD Stability Fixes

- Fixed SkillTreeMixin NameError by importing `describe`.
- Fixed compact boss slash payload crash (`ValueError: expected 4, got 1`).
- Active skill tree is now retained while hovering; hover route + tooltip use a tiny dynamic layer.
- Tooltip text is tagged so it cannot accumulate hundreds of canvas items.
- Passive tree now uses the same retained static/dynamic split; mouse movement no longer redraws 175 nodes.
- Added cache invalidation on tree mode/resize changes.
- Reworked gameplay HUD footprints to prevent overlap: top player/resource strip, bottom vitals, dedicated status lane, centered skill signature, lowered hotbar.
- Moved minimap below the top resource panel.
