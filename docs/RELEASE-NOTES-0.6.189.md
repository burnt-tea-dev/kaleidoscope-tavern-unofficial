# Tavern 0.6.189

Fix wild grapevine detachment and drops. Head/body share the native grapevine loot table; direct player destruction and detached segments no longer produce different item identities. Existing break routing and component callbacks refresh the adjoining vine cells, including a new head above a cut. Preserve all existing block/item/state/UUID identities.

Isolated BDS1.26.60.6 tests cover stone and birch-leaf support, middle cuts, 26-cell chains, overlapping support notifications and disabled tile drops. Source tests cover empty hand, held dirt, tools, Creative and disabled tile drops. See [targeted evidence](evidence/wild-grapevine-20261029.json) for exact scope and remaining limits. Full-family admission and human acceptance remain separate.

S1 remains incomplete: client rendering/audio, C04 inventory stacks, normal-play performance and the final 48-hour S1 observation are not certified by this repair.
