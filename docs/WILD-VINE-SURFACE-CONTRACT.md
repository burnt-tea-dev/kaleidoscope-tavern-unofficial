# Wild grapevine source surfaces

The active shared owner is `runtime/RP/models/entity/wild_grapevine.geo.json`,
identifier `geometry.kt_assets_a2.wild_grapevine`. Both growing head and body
select this model for placed blocks and native item visuals, with distinct
source textures. Age/sheared states do not change those routes. Cultivation,
loot, selection/collision, held transforms and pack/module identities are not
geometry-generation inputs and are preserved.

The retained `wild_grapevine_plant.geo.json` a3 model has no active runtime
geometry selector. It remains an art source asset: `art/interfaces/asset-registry.json`
records both A3 visual-lab bindings as `runtime_connected: false`, with source,
editor, texture and language metadata. It is not a second functioning cultivation
implementation. This repair does not delete it or reconnect it. The historical
`history/pre-release-0.6.29/tools/sync_post12_visuals.py` is not a current generator.

## Source contract

`data/wild-vine-surfaces/` preserves the bounded Forge 1.20.1 models and
blockstates at `c4ec1880bd44cf3139d3ba744ab30bb379cf1416`, and the official
`minecraft:block/cross` parent. Source paths and hashes are in `source.json`.
NeoForge 1.21.1 children/textures match; the official 1.20.1 and 1.21.1 parents
are byte-identical. Complete official client archives are not repository inputs
and must not be published. The 26.1.2 parent and renderer have not been checked.
The locked uploaded mod's individual members were checked against source;
this does not newly establish the complete uploaded archive's identity.

Java uses two zero-thickness rescaled planes. Their X/Z span is 14.4 model
units. The old two 16×16×0.1 slabs spanned approximately 11.3844191771, a
visible narrowing independent of texture sampling. The repaired center planes
match the source within 0.000000050914 units from seven-decimal rounding.
The native 0.16-unit thickness is an explicit centered adaptation: surfaces are
±0.08 from the source planes and total X/Z span is approximately 14.513137157.
This is not exact zero-thickness surface parity or a proven minimum thickness.
No cap faces are added. Each of the four authored directed faces has its own
source UV mapping, rather than the old box-UV representation.

`tools/cultivation_source_contract.py` owns the current behavior/resource domain
and now includes the active shared geometry. Its `wild_vine_surfaces.py` helper
independently transforms the original source with complex-number rotations,
checks 16 UV corners and 1024 texel centers, and validates both world/item
routes, source single-sided cutout policy, unchanged AO/dimming, textures and effective
permutation overrides.
It never imports the historical converter or reverses a runtime diff.
`tools/test_cultivation_source_contract.py` rejects lost rescale, shifted planes,
wrong pivot/rotation, mirrored or box UVs, missing/extra faces, unmapped materials,
changed slab thickness, hidden/disconnected geometry and texture routes.

No geometry entries existed in the old reconciliation/launch dictionaries.
The shared current owner replaces its former aggregate-preservation treatment;
no inverse ledger, version exception or runtime hash exemption is introduced.
Frozen identity/history remain separate. Actual cultivation adapter behavior is
covered by `tools/board-farm-interaction.test.mjs`, not asserted by a geometry check.

## Culling policy

The two wild BP files change only their world/item wildcard `render_method`:
`alpha_test` becomes `alpha_test_single_sided`, four scalar fields in total.
[Microsoft's material documentation](https://learn.microsoft.com/en-us/minecraft/creator/reference/content/blockreference/examples/blockcomponents/minecraftblock_material_instances?view=minecraft-bedrock-stable)
distinguishes disabled versus enabled backface culling. Official 1.20.1 and
1.21.1 client class bytes, parsed as data with verified official mappings,
confirm vanilla `cutout` retains default `CULL`. Forge's documented model route
selects that world render type. Pinned maintained Forge 1.20.x and NeoForge
1.21.1 named cutout/item sources also keep default culling. Exact-47.3.0 source archive retrieval was unavailable;
the pinned maintained Forge source is supporting evidence, not that exact
loader archive verification.

All four directed source faces remain. Culling removes the reverse face from a
viewpoint, not the authored forward face on the other side. Without it, mirrored
opposing-face pixels can contribute through transparent front pixels. This is
separate from neighboring-block `cullface` removal, which the source does not
request. Both world and item routes keep AO=0, face_dimming=false and the same
textures/geometry. Tests reject restoration of double-sided alpha_test, on
either head/body route, and any AO/dimming drift. Other crop/trellis materials
are outside this repair.

## Evidence boundaries

Free review scenes explicitly set texture `render_sides=front`; direct native
Bedrock imports default to Auto/DoubleSide. A blank or narrow South sprite in
the original Free BEFORE scene is therefore **not** evidence of a missing-back
runtime defect. Direct native BEFORE South shows a full mirrored sprite. The
width mismatch is independent and remains the repair rationale. Opposing-face
contribution, native renderer sampling, alpha-test sidedness, lighting and held
item appearance require separate evidence. Static mapping checks do not prove
rendered parity. Original screenshots/scenes and diagnostic exclusions must be
preserved alongside the final bounded GUI review; GUI acceptance is not an
engine, BDS, saved-world or LIVE acceptance.
