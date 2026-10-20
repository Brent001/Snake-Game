# v20 - True Passive Tree + branching Active Skill Tree

## Naming

The pause-menu **SKILL TREE** entry now opens the tree screen, where the two systems are clearly separated:

- **PASSIVE TREE** = permanent character build/stat routing.
- **SKILL TREE** = active skill customization for LMB and V abilities.

The old passive grid is no longer presented as the general Skill Tree.

## Active Skill Tree

The former five-step linear skill evolution rows were replaced with actual branching skill constellations.
Every class has two skill constellations (LMB + V). Each constellation contains:

- a free skill root;
- three independent specialization paths;
- minor nodes and notables;
- a major checkpoint on each path;
- cross-links between paths for alternate routing;
- a shared mastery/jewel socket;
- two mutually-exclusive capstones.

Cobra's **VENOM BOLT** is the reference shape: players can route into barrage, piercing, or poison specializations instead of simply buying Bolt II, III, IV and V.

## Live gameplay

Allocated active-skill sockets feed directly into `StatsMixin.recompute()` and therefore modify the live ability profiles. Existing ability mechanics consume these values for bolt count/pierce/damage/cooldown, Fang reach/venom/targets, Python slam radius/shield/stun, and Mamba chain/execute effects. V-skill milestone levels are derived from the deepest allocated socket and remain compatible with the existing evolved-V effects.

Skill points are spent one at a time per socket. Roots are free. RMB refunds a node only when the remaining graph is still connected to its skill root. Capstones are mutually exclusive.

## Passive Tree clarity

The passive renderer now has stronger cable/line hierarchy, a dark connector underlay, directional chevrons on the next allocatable frontier, cluster halos around notables/majors, clearer district guide patterns, and a highlighted route when a node is hovered. Unrelated lines become visually quieter while tracing a route.

## Navigation

Both trees support the same interaction model:

- LMB = allocate
- RMB = refund
- drag = pan
- wheel = zoom
- 1 = Passive Tree
- 2 = Skill Tree
- TAB/K = open/close
