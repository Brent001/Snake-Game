# Repair Terminal V10 — Stylized Lighting & Combat Readability

## Visual direction
- Removed dark/black faux-bloom outlines from player and boss projectiles.
- Player Bolt is now a shaped elemental projectile: tapered head, segmented trail, elemental motif, white-hot center.
- Melee Slash was redesigned as a hard-edged ink/pixel cut with directional arc + cut fragments, with no bloom halo.
- Primary melee no longer spawns generic bloom particles; hit-stop + camera shake carry the impact weight.

## Dynamic lighting
- Day: animated sun direction controls stylized cast shadows under player, enemies and boss. Shadow length responds to daylight.
- Night: player, projectiles, boss and dungeon torches receive interactive local light pools.
- CPU fallback uses layered stippled light pools; GPU mode uses a real radial-light shader.

## GPU changes
- Added ModernGL radial-light instances to the existing OpenGL compositor.
- Lights are composited additively and blurred with the existing half-resolution post pass, with no black outline.
- Projectile light follows its actual projectile position each frame.

## Compatibility
- Tkinter remains the gameplay/UI surface.
- V9 GPU effects remain optional; `--cpu` still forces the CPU fallback.
