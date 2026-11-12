# Machine ingredient-card geometry

## Current bounded broad-face repair (2026-11-12)

The existing pressing and barrel card geometries still contain only two broad
faces per slot. Their north UV now starts at `[16,0]` with size `[-16,16]`;
south remains `[0,0]` with size `[16,16]`. This makes both faces sample the same
texel at the same local X/Y, as Java `ItemModelGenerator` does. It corrects the
mirrored reverse silhouette without changing any face vertices, normal, pose,
pivot, animation, slot position, visibility bound or scale. This is a local
relative-UV contract. It does not establish an external engine-to-world basis,
absolute world orientation or full Java rendering equivalence. No V flip or
pose compensation is introduced.

`data/machine-ingredient-source/` contains the original 57 routed sprite IDs
(68 frames, including the sugar-cane alias and all 12 ice-grape frames), source
provenance, and official 1.20.1/1.21.1 ItemModelGenerator bytecode. The independent
`check_machine_ingredient_broadfaces.py` decoder audits both actual card owners.
The pre-repair UV has 17,408 wrong texel correspondences, 3,240 alpha mismatches
and 6,592 visible RGBA mismatches over those frames; the repaired UV has zero.
Mutation tests retain the actual pre-repair failure and reject V flips, south
reorientation, disconnected helpers and changed source pixels. Both face normals
are preserved. Source algorithm equivalence is separate from client acceptance.

Two ingredient-only texture aliases now use original Java PNGs: honeycomb
removes eight nonzero-alpha residual pixels, and lilac corrects 36 visible RGB
pixels. Their original native PNG/TGA witnesses are retained with the source
fixtures. No global vanilla texture is overridden. The ordinary entity material
and existing conservative nonmetal/nonemissive roughness-200 profile remain in
use. Pitcher plant's differently named native texture is RGBA-identical to the
Java item texture and is not replaced. Pink petals retain the existing Forge
1.20.1 pixel baseline: 1.21.1 changes alpha values, but not nonzero-alpha spans.
The ten Cookery sprite PNGs match both maintained official Java branches.

The current source owner covers both cards, all twelve helper definitions and
the four new PNG/texture-set files. The eight superseded pressing-helper inverse
projections are retired; their unchanged controller/clock remains separately
owned. The barrel generator exposes its complete helper definition to the same
validator. No new historical hash exception or release-specific postimage is
introduced.

The repair retains exactly two geometry IDs: pressing has 27 bones/eight cubes
(192 conservatively allocated vertices), barrel has nine bones/nine cubes (216).
Each helper still has one render-controller pass. The fully extruded alternative
was evaluated only in an isolated candidate: 67 models, up to 8,640/11,448
allocated vertices per pressing/barrel helper. It is not installed in runtime
and does not enlarge the existing family geometry budget.

**Alpha-edge extrusion remains missing.** No Minecraft/BDS runtime, material,
world-frame, culling or gameplay parity acceptance is claimed by this repair.

## Retained size correction and earlier evidence

The shared card owner is `runtime/RP/models/entity/runtime_pressing_card.geo.json`.
Its eight centered cubes are 8×8×0.5 model pixels, with origins [-4,-4,-0.25].
Java's generated model is 16×16×1, the reviewed FIXED parent scale is 1, and the
pressing renderer applies scale 0.5. The prior 4×4×0.25 card accidentally applied
an extra half scale. No animation scale is introduced because it would also
risk scaling ingredient positions.

`tools/machine_ingredient_geometry.py` validates current native resources against
raw pinned Forge/NeoForge renderer and official generated-parent inputs under
`data/pressing-ingredient-source/`. The 1.20.1 ItemModelGenerator bytecode gives
the broad slab [0,0,7.5]→[16,16,8.5]. That earlier fixture did not establish the
1.21.1 extrusion algorithm; the newer source inputs above are separate evidence.
Both maintained renderers and both generated parents agree on scale.

## Shared ownership and preserved routes

Canonical runtime JSON is the active authoring source. The former generator in
`history/pre-release-0.6.29/tools/pressing_tub_visual.py` is archived and no active
tool invokes it. It is retained as historical evidence, including its incorrect
old comment, not used to rebuild this release. No second geometry generator or
release-specific postimage is added.

Historical launch comparison delegates the currently owned resources to the
source-backed validator. Tests reject returning these paths to reconciliation,
reverse-delta or launch postimage guards. The generic source-view and historical
entry points use that same contract. Release identity/history remains separate.

The full current resource census must find exactly eight pressing helpers.
They share eight card cubes per helper and 64 global slots. There are 27 routed
food IDs: 22 card IDs (21 card kinds plus the existing sour-cherry alias) and
five cube kinds. The five cube kinds
remain 4×4×4; all nine barrel cards remain 8×8×0.5. Every bone, local center,
parent chain, material, helper route, part visibility,
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

Native cards still approximate source alpha-edge extrusion with two broad faces;
the new relative-UV repair does not fill those missing edges.
Ordinary ice alpha/material behavior is not newly accepted. The raw decoded
Blockbench tilted AABBs exceed declared visible bounds both before and after,
for the one audited seed/count over 320 poses. The external engine/model-to-world
and culling contract is unproven, so bounds, pivots and Y signs are not changed.
Body clearance, world-facing and native material rendering are not certified.
No Minecraft, BDS, LIVE, saved-world or full addon parity acceptance is claimed.
