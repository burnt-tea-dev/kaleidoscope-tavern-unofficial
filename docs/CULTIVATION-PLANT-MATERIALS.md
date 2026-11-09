# Cultivation plant material policy

The shared `tools/cultivation_source_contract.py` owns the four crop/ordinary
filled-vine BP resources alongside its existing wild-vine owners. The repair
changes exactly 36 scalar material methods from `alpha_test` to
`alpha_test_single_sided`:

- Each of grape, gold-grape and ice-grape crops: base world, base item, and six
  age permutations, eight fields each.
- Ordinary filled grapevine: wildcard and unshaded in base world/item and four
  single-shape age permutations, twelve fields.

The ordinary vine's 24 connected-shape permutations / 48 material fields and
both gold/ice A3 filled-vines are already single-sided and remain unchanged.
The shared contract also checks these controls without transferring their
historical ownership. Four affected entries in each old reconciliation/launch
ledger are retired. The existing motion aggregate handoff also retires those
four paths, preserving the untouched 159-file original aggregate and their
historical beforeProjected digests; 145 remaining block paths stay guarded.
There is no inverse ledger, release-specific runtime
postimage, or extra generator. Frozen release identity remains separate.

## Source and route checks

`data/cultivation-plants/` contains 48 raw Java models, six blockstates and six
source textures from Forge commit `c4ec1880bd44cf3139d3ba744ab30bb379cf1416`.
`source.json` binds exact paths/bytes and NeoForge commit
`a1afba34981a00e89d57130d3dc8f1e64f1820a2` equivalents. Models, authored directed
faces, UVs and decoded PNG pixels agree across branches; some PNG encodings
differ. No entire mod/client archive is vendored.

The current validator resolves every source model and all 1,026 declared native
states (including waterlogged and six block-face trait values). It requires
exactly one winning permutation and source-matching geometry/material routes,
checks all 108 base/permutation declarations and their inherited item fallback,
and retains 660 directed faces across 48 models. Texture bindings, source PNG
bytes, per-face shaded/unshaded ownership and existing AO=0 are checked.

All models specify cutout. The bounded semantic evidence uses official Java
1.20.1/1.21.1 class data and pinned maintained Forge/NeoForge sources to establish
default CULL. The exact Forge 47.3.0 archive request previously returned 403 and
was not retried. Exact loader-release archives and 26.1.2 renderer behavior are
not established. Missing neighbour `cullface` does not disable backface culling.
Microsoft documents that `alpha_test` disables backface culling and
`alpha_test_single_sided` enables it. Both explicit directions remain authored;
the material no longer adds reverse-facing texels through transparent pixels.

The source has no same-name item model for these crops/filled vines. Their
native stage-zero `minecraft:item_visual` fallback is kept consistent with the
source-backed block geometry policy. This does not establish Java inventory,
ordinary fruit/bare-trellis icons, held-pose or acquisition parity.

## Preservation and verification limits

No geometry, UV, PNG, AO, dimming, transform, collision/selection, loot, growth,
connection, waterlogged or state-routing value changes. The previously reviewed
336 faces retain the centered ±0.08 displacement / 0.16-thickness adaptation,
not exact zero-thickness parity. PR613 wild-vine rescale/materials, accepted
+6 tilted-rack transform and the known Allium clipping limitation are retained.

The negative tests call the actual shared validator. They reject double-sided
regression at every one of 204 material declarations, route loss/duplication,
wrong state domains and geometry, material/texture disconnection, item overrides,
AO/dimming/pose changes, missing opposite faces and unwanted cap faces. Existing
wild-vine negatives remain. `board-farm-interaction.test.mjs` runs actual source
adapters with the existing test loader; it is not a gameplay session.

The bounded Front/Double Blockbench controls use Free-format texture hints,
not execution of native BP materials. Neither those editor controls nor the
static checks certify Minecraft client rendering, BDS, saved worlds, LIVE,
all inventory/held contexts or full-family deployment. See the
[portable review evidence](evidence/blockbench-plant-culling-20261109/README.md).
