# Pressing ingredient-card geometry

The shared card owner is `runtime/RP/models/entity/runtime_pressing_card.geo.json`.
Its eight centered cubes are 8×8×0.5 model pixels, with origins [-4,-4,-0.25].
Java's generated model is 16×16×1, the reviewed FIXED parent scale is 1, and the
pressing renderer applies scale 0.5. The prior 4×4×0.25 card accidentally applied
an extra half scale. No animation scale is introduced because it would also
risk scaling ingredient positions.

`tools/machine_ingredient_geometry.py` validates current native resources against
raw pinned Forge/NeoForge renderer and official generated-parent inputs under
`data/pressing-ingredient-source/`. The 1.20.1 ItemModelGenerator bytecode gives
the broad slab [0,0,7.5]→[16,16,8.5]. It does not establish the 1.21.1 extrusion
algorithm. Both maintained renderers and both generated parents agree on scale.

## Shared ownership and preserved routes

Canonical runtime JSON is the active authoring source. The former generator in
`history/pre-release-0.6.29/tools/pressing_tub_visual.py` is archived and no active
tool invokes it. It is retained as historical evidence, including its incorrect
old comment, not used to rebuild this release. No second geometry generator or
release-specific postimage is added.

The current contract owns exactly the repaired card resource. Historical launch
comparison delegates that exact path to this source-backed validator. The file
has no entry in existing reconciliation/reverse-delta/launch hash ledgers and
is not part of a historical aggregate group. Those ledgers are unchanged; tests
reject adding the card back to them. The generic source-view and historical-file
entry points use the same current contract. Release identity/history remains
separate. Unchanged route/control resources retain their existing ownership.

The full current resource census must find exactly eight pressing helpers.
They share eight card cubes per helper, 64 global slots, and 22 food IDs
(21 card kinds, including the existing sour-cherry alias). The five cube kinds
remain 4×4×4; all nine barrel cards remain 8×8×0.5. Every bone, local center,
parent chain, UV direction, texture alias, material, helper route, part visibility,
animation expression and frozen-frame selector is retained.

The actual pressing adapter is unchanged. The focused JavaScript tests execute
its helper selection/configuration across all current food IDs and counts 1–64,
compare all 64 packed slot properties with independent source-derived samples,
and check that cardinal tilt only changes the existing frame flags. Existing
machine native-storage/callback and texture-clock tests remain applicable.

## Scope of acceptance

The [portable evidence](evidence/blockbench-pressing-card-20261109/README.md)
preserves the original baseline and candidate scenes, independent audits and
raw GUI JPEGs. SOURCE and AFTER agree in isolated broad-face scale; BEFORE is
half the linear size. The candidate changes only 16 vector fields, 48 scalars,
in eight cubes. No PNG, material, shader, helper lifecycle, gameplay, body or
held-pose change is made, including the rack's accepted +6 first-person Y lift.

Native cards still approximate source alpha-edge extrusion with two broad faces.
Ordinary ice alpha/material behavior is not newly accepted. The raw decoded
Blockbench tilted AABBs exceed declared visible bounds both before and after,
for the one audited seed/count over 320 poses. The external engine/model-to-world
and culling contract is unproven, so bounds, pivots and Y signs are not changed.
Body clearance, world-facing and native material rendering are not certified.
No Minecraft, BDS, LIVE, saved-world or full addon parity acceptance is claimed.
