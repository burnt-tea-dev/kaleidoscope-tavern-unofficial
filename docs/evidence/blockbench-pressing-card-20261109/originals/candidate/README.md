# Pressing ingredient-card size repair: offline candidate review

**Candidate only. No runtime/worktree modification, GUI operation, game, Minecraft, BDS, LIVE, deployment, version freeze, commit, PR, merge or Release was performed.**

## Minimal repair

The single candidate owner is `candidate/runtime/RP/models/entity/runtime_pressing_card.geo.json`.

- All eight `item_z_0` through `item_z_7` cubes change origin **[-2,-2,-0.125] → [-4,-4,-0.25]** and size **[4,4,0.25] → [8,8,0.5]**.
- This is 16 vector fields / 48 scalar values. All local centers stay exactly **[0,0,0]**. Every other JSON field is equal.
- No animation scale is added, because that would also risk scaling slot placement. Bone hierarchy/pivots, slot transforms, yaw, root pitch, controller timing, material, UV, texture, state and food routing remain unchanged.
- Barrel card, pressing cube and all accepted held assets are unchanged. Tilted rack **+6 means the accepted first-person Y lift**, not six poses.
- SHA256: **d93249923210a8711fa038105816380407b9d70811c23313d4ddb56d68b83eea**.

`changed-field-proposal.json` provides the exact before/after fields and hashes. There is only one file beneath `candidate/`; it is not an installable pack and must not be applied until the parent assigns integration after candidate GUI review.

## Canonical and source identities

Pinned Tavern **0.6.214** main is `682a9dd01cc8d5ad26b714c0b279d04cbafeb205`. Its full tree is `dd322fc23aca7beb1f36650ba5dc6cb674c412b9`. The shared read-only checkout's HEAD `e4209276dab846dc6689d5760bc9e1809261d58d` has that exact tree. No plant, version or metadata edits are included. Integration must recheck this geometry and its routes against the then-current canonical main without overwriting the separate 0.6.215 plant work.

Forge source is `c4ec1880bd44cf3139d3ba744ab30bb379cf1416`; NeoForge 1.21.1 source is `a1afba34981a00e89d57130d3dc8f1e64f1820a2`. Their actual pressing-renderer pose calls agree. Both apply renderer scale **0.5**, `FIXED` display context, root X rotation and the same seeded slot transforms. Official Java 1.20.1 and 1.21.1 `item/generated` FIXED display parents both use scale **1** and Y rotation **180°**. The generated model's **16×16×1** therefore becomes **8×8×0.5**. Original card dimensions were **4×4×0.25** and have no compensating scale.

This offline task reuses N03's recorded upstream refresh; it does not claim a fresh network check. `manifest.json` pins 248 exact inputs and source archive identities. Relevant N03 current inputs were re-read from the 0.6.214 commit and verified byte-identical before reuse. `provenance/canonical-runtime-tree.txt` records the canonical runtime Git blobs. Original helpers and source-extrusion bytecode proof are preserved under `provenance/`.

## All consumers and preserved controls

The audit enumerates all canonical RP client entities and attachables for this geometry ID. Exactly eight pressing helper definitions reference it; all eight matched BP helpers have no compensating scale. They cover global indices **0–63**, eight local cards per helper. The animation, render-controller selection, helper creation/configuration, packing, visibility and frozen texture-clock route are checked from their original inputs.

The current food map has 27 IDs: **22 IDs / 21 unique card kinds** share this corrected owner, including the existing `amw:sour_cherry` alias. Five kinds **21–25** retain the separate cube owner. `independent-audit.json` lists all IDs, texture aliases and helper ranges. This establishes route coverage, not independent source/texture parity for every external subtype or addon. Unknown/custom item models are not newly accepted.

The exact N02 `prior-evidence-reuse.json` is copied and rechecked for the four shaker controls and the tilted-rack geometry SHA256 `93030bd4f8289be846eea898052b36ed81c33626355c8e42fbcac95a73968ff7`. These are preserved historical held controls, not new held-view acceptance. The single-file candidate leaves unrelated poses and the existing unresolved allium held/FOV issue untouched.

## Six bounded scenes, seven suggested captures

All scenes are self-contained `.bbmodel` files. SOURCE is placed at X=-24, BEFORE at X=0, AFTER at X=24. Read group names rather than screen-left/right. No machine bodies are attached, so no source/current body-clearance inference is invited.

1. `01-upright-isolated.bbmodel`: grape global index 0, count 64. Clearest 8-versus-4-versus-8 size comparison; two captures, Top and near-side oblique.
2. `02-upright-helper-boundaries.bbmodel`: indices 0/7/8/63, exposing lower/upper layers and helper boundaries.
3. `03-north-tilt-layers.bbmodel`: indices 0/63, original source and native north pose chains.
4. `04-east-tilt-layers.bbmodel`: indices 0/63, original source and native east pose chains.
5. `05-animated-ice-grape-tick1.bbmodel`: frozen tick 1, exact original RGB interpolation/current-alpha pixels.
6. `06-unchanged-controls.bbmodel`: barrel grape remains 8×8×0.5 and pressing stone remains 4×4×4. Stone uses the original explicitly neutral official Java texture control.

`capture-queue.json` gives view intent and expected distinctions. Candidate GUI review is **pending**. The parent will provide the final N03 baseline GUI receipt separately; this preparation does not reuse incomplete GUI flags or claim any capture was performed.

## Independent verification

The scene writer reuses the current N03 explicit mesh and generated-item helpers, including per-texture UV dimensions and original PNG bytes, rather than the older fixed-128 Java cube decoder. Exact evaluated matrices are baked into directed vertices. Original transform chains remain recorded; this is not a running ModelPart/animation/controller simulation.

The independent reader does not import the builder. It uses the separately audited N03 restricted Molang evaluator, source float32/RNG reconstruction, SciPy rotation construction and independent directed-face/alpha-span generation. Native verification traverses the **actual selected local bone's ancestor chain**, including local 7; it does not substitute the first cube for every slot.

Current audit results:

- **248** original input hashes, **36** saved meshes, **455** directed faces and **1,820** corresponding vertices checked.
- Maximum matrix error **7.11e-15**, vertex error **1.42e-14** model pixels, bounded as floating-point reconstruction error rather than source/current parity tolerance.
- **320** native poses checked: 64 global indices × upright plus four cardinal tilt states. All maintain the original rigid transforms and centered 8×8×0.5 geometry.
- Eight negative controls reject candidate size, center, UV and tilt-pivot tampering and saved mesh size, center, UV and matrix tampering.
- All 24 frozen animated tick PNGs match the independent source interpolation; zero pixel mismatches. Every embedded texture retains its designated original or explicitly derived PNG bytes. Original UVs are checked after explicit 128-unit scene normalization.

## New bounded advisory: declared visibility bounds

The selected seed's raw decoded tilted-card vertex union already exceeds the existing declared visibility box before repair. Existing bounds are X/Z **±24**, Y **[-8,40]** model pixels. Before: X **±25.51**, minimum Y **-12.86**. Candidate: X **±27.55**, minimum Y **-14.61**. The audit records full before/after AABBs.

This is an **engine-frame/culling verification advisory**, not proof of an actual native disappearance. Source world coordinates and raw Blockbench-native reference coordinates intentionally differ. No guessed coordinate sign, body-clearance, origin, placement or visibility metadata change was added. The baseline already exceeds these bounds, and this candidate extends the raw envelope by the justified card-size correction. Keep this concern explicit for integration/native review rather than expanding this repair speculatively.

Exact inputs and coordinate definitions:

- The unchanged description fields are `visible_bounds_width: 3`, `visible_bounds_height: 3`, `visible_bounds_offset: [0,1,0]`, expressed in **blocks**. The advisory interprets width as the X/Z diameter and height as Y diameter, with 16 model pixels per block, giving the box above. No independent native culling implementation is present in these offline inputs.
- Geometry cube origin/size, bone pivots and animation position channels use **model pixels**. Before posing, each native card is centered at zero with min/max [-2,-2,-0.125]/[2,2,0.125], changing to [-4,-4,-0.25]/[4,4,0.25]. Both unposed cards fit the declared box.
- The **320 evaluated poses** are global indices 0–63, count=64, source block location **{x:3,y:64,z:-5}**, and tilt states **upright, north=0, east=1, south=2, west=3**. Every helper 0–7 and local bone 0–7 is evaluated. This is one deterministic seed and count, not an exhaustive bound over all seeds/counts.
- Native packed properties are reconstructed from the actual layout/configuration expressions. The audited Blockbench decoder reflects geometry/pivot/translation X, negates native X/Y Euler angles, preserves Z angle and follows the actual bone hierarchy with **T(pivot−parentPivot+position) · Rz · Ry · Rx**, ending with T(−cube-bone pivot). Native `tilt_yaw → tilt → offset → ingredient_i → item_y_i → item_z_i` is preserved. These definitions describe the **BB-decoded animated model-reference frame** only.
- `pose-bounds-audit.json` records every pose's native properties, decoded matrix, before/after AABB and exact sample scope. All envelope values exclude scene column offsets and are in model pixels. The source meshes separately use centered Java PoseStack world coordinates; no fit between those coordinate frames is used.
- BP helper spawn location is **{core.x+0.5, core.y, core.z+0.5} blocks** with ingredient initial rotation 0. External native entity/model-to-world and renderer/culling transforms are **not simulated or proven** here. That missing runtime contract is why raw decoded overhang alone does not establish a native culling failure or justify changing metadata.

No minimal bounds change is proposed. The existing offline schema/source set is sufficient to read the fields and reproduce the editor-space advisory, but not independently sufficient to prove the engine-space culling transformation, nor bound all allowed seeds/counts. The single-file eight-cube correction remains the requested candidate; a bounds change would need its own supported runtime/contract analysis.

## Deliberate boundaries

- Source grape retains **35 generated quads**, and animated ice-grape retains **43** over its frame union. Native before and after retain only **two broad faces**. No edge geometry was added. The original generated-item algorithm is proven against official **1.20.1** bytecode, not generalized to 1.21.1.
- `render_sides: front` is only a Blockbench preview hint. It does not verify BP/controller execution, engine culling, shader/material semantics, sorting or native blending.
- Ordinary ice's active alpha/material difference remains unproven native behavior and out of scope. No material/opacity fix is proposed.
- Source/world and raw BB-native pose frames remain different. Size is basis-invariant; body clearance, world-facing and Y alignment are not accepted or altered.
- No gameplay, live animation, reconnect/reload, Minecraft/BDS, full addon visual parity, release or deployment acceptance is claimed.

## Reproduce locally

All writes stay inside this prep directory. Run sequentially with Python's `-B` option:

1. `python -B prepare_review.py`
2. `python -B build_review.py`
3. `python -B audit_review.py`
4. `python -B finalize_review.py`

Preparation reads the pinned existing checkout and N03/N02 inputs. The builders never run the prior scripts' scene-generation loops. Do not run broad test suites alongside the shared GUI. Full runtime checks and publication remain a separate, explicitly assigned integration task.
