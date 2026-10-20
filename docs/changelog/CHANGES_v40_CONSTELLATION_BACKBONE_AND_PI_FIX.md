# v40 — Real Constellation Passive Background + Boss PI Fix

- Passive nodes and their positions are unchanged.
- Replaced the decorative S-creature backbone artwork with a Serpens constellation backdrop.
- Real Serpens star identities/magnitudes and J2000 coordinates are used as the reference; the visual star points are pinned one-for-one to the existing backbone/core node centers for exact alignment in every class, zoom and pan state.
- Constellation segments are drawn behind the nodes, so the existing passive tree remains the authoritative graph.
- No passive node IDs, coordinates, edges, stats, or allocation rules were changed.
- Fixed `PI` NameError in boss pressure patterns by defining `PI = math.pi`.

Source reference: Wikimedia Commons Serpens constellation map notes that the map covers both parts of Serpens and uses equinox J2000.0 coordinates; notable-star catalog values were cross-checked against the public Serpens star list.
