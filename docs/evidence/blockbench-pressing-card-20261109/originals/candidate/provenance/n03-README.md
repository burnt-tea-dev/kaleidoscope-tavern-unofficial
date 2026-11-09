# N03 machine contents: source/current review fixtures

**Preparation only. No GUI, Minecraft, BDS, LIVE, deployment, application/process management, runtime repair or publication was performed.**

Canonical Tavern **0.6.213**, main `1bd3d70f94d142630b05a655008a296bc0bcd387`, runtime tree `38c5977dd6bfe14b1824734612e3c601e1e41028`.

Upstream refs were refreshed during preparation and still resolve to Forge `c4ec1880bd44cf3139d3ba744ab30bb379cf1416` and NeoForge 1.21.1 `a1afba34981a00e89d57130d3dc8f1e64f1820a2`. See `upstream-refresh.txt` and `manifest.json`.

## Useful result

The **active pressing-tub card is half the source size in each dimension**. This is not a conclusion from an isolated geometry width:

- Both official Java 1.20.1 and 1.21.1 `item/generated` parents specify FIXED scale **1** and Y rotation **180°**.
- Both maintained Tavern renderers apply an additional uniform scale **0.5**.
- Java generated faces span 16 × 16 with thickness 1 before these transforms, giving **8 × 8 × 0.5**.
- The active pressing geometry is **4 × 4 × 0.25**. All eight pressing BP helpers and eight RP helper definitions, their animation/controller route, bone hierarchy and spawn/configure path have no compensating scale.
- Independent final transformed vertex measurements give source face edges **8** and current face edges **4**. Translation, rotation, slot layout and entity-facing basis cannot change these lengths.
- The barrel card already has dimensions **8 × 8 × 0.5**. Cube ingredients are **4 × 4 × 4**, because their separate block-model FIXED scale is **0.5**.

This is a source-backed size discrepancy. **No runtime repair or GUI acceptance is claimed.**

Two other differences remain separately bounded:

- The original generated grape has 35 quads (front/back plus 33 merged boundary strips); animated ice-grape has 43 (front/back plus 41 strips across its frame union). Current cards retain two broad faces only. This is an explicit representation difference, not a claim that every edge is a new gameplay defect or that it has been repaired.
- Pressing ordinary ice uses `entity_alphatest`, while barrel ordinary ice selects `entity_alphablend`. Official Java ice PNG alpha is 190. The current ice texture is inherited from the engine/family and is not present locally, so this is an **active material-route difference**, not a proven native transparency defect. Both sides of the cube fixture deliberately use the official Java PNG as a neutral control.

The unused `controller.render.kt_runtime.machine_liquid` declares alpha 0.85, but **no client entity at the pinned canonical main references it**. The twelve built-in fruit-fluid helpers use the static controller and opaque PNG alpha 255. Do not report the unused controller as a live fruit-fluid opacity defect.

## Eight self-contained scenes

Source is negative world X; current is positive world X. Screen-left/right depends on camera and is not identity evidence. Original body groups retain their names. `capture-queue.json` suggests **11 discriminating captures**, not an exhaustive sweep.

| Scene | Purpose |
| --- | --- |
| `scenes/barrel-liquids.bbmodel` | Water 1000/4000, lava 4000/4000, opaque grape 4000/4000; frame 0. |
| `scenes/pressing_tub-liquids.bbmodel` | Water 250/1000, lava 1000/1000, opaque grape 1000/1000; frame 0. |
| `scenes/barrel-card-edge-slots.bbmodel` | Grape slot 0 indices 0/8 and slot 3 indices 9/17; each populated slot count 16. |
| `scenes/pressing-card-upright.bbmodel` | Count 64 with indices 0/7/8/63, crossing helper 0→1 and reaching helper 7. Select index 0 alone for the clearest size comparison. |
| `scenes/pressing-card-tilt-north.bbmodel` | Same edge indices, north tilt source and current hierarchy. |
| `scenes/pressing-card-tilt-east.bbmodel` | East tilt **contents-only** control. It does not attach the north-facing body to east-facing contents. |
| `scenes/cube-material-controls.bbmodel` | Stone and ordinary ice on both machines; explicitly neutral official Java textures. |
| `scenes/animated-card-frame-controls.bbmodel` | Frozen ice-grape tick 1 on both machines. All 24 generated tick textures are separately pixel-checked. |

Other built-in fruit liquids factor into the grape representative: their active geometry, controller/material and level route are the same, and all six fruit sprites are opaque 16 × 16 PNGs. Water and lava remain separate because they have different sprite-strip heights, controller tint and animation expressions. Ordinary ice and animated ice-grape remain separate from opaque static cards/cubes. Third-party externally registered fluid visuals and arbitrary addon ingredient models are not accepted by this finite built-in fixture set.

## Actual sources and exact representation

The source contents come from `BarrelBlockEntityRender`, `PressingTubBlockEntityRender` and `RenderUtils`, not machine item JSON. N02's already audited barrel/open and pressing bodies are reused. The current side reads the active RP entity, controller, geometry and animation inputs plus BP helper/configuration/layout logic.

Content meshes bake the complete evaluated transform matrices directly into their directed vertices. They preserve original local face UVs, source parent/FIXED transforms, source float32 calculations, stable-random seed, selected slots, and native property quantization. Each mesh records its original route and matrix in `_review`. This avoids Euler fitting, affine decomposition, scaled-cube substitution or zero-plane inflation. Body hierarchy stays as actual nested groups. **Content hierarchy is recorded and matrix-baked, not presented as a running animation.**

The independent reader uses original bone pivots/parents and a restricted expression evaluator for the actual animation channels. It separately reconstructs Java float operations and pose matrices. Its code does not import the builder. The source east-tub pose uses the real Java direction data value (east=3), including the resulting positive 90° Y pose; no broad sign correction is applied to make it resemble the current helper.

`review_codec.py` in N02 and the earlier decor task was inspected. Its basic decoder does not evaluate helper properties, animation position, controller tint, generated-item extrusion or general multi-axis affine transforms. It is **not** silently used as an all-purpose source converter here. Native face decoding follows its audited sign/UV convention, but contents are explicit meshes and independently checked. Every scene uses 128-unit virtual UV dimensions while keeping original PNG bytes; the copied N02 body UVs are explicitly normalized and audited.

### Generated-item provenance

The front/back thickness, mirrored north UV and span merging were inspected in the **official Java 1.20.1** `ItemModelGenerator` bytecode (`fkz` and nested classes), read with the installed JDK's `javap` module. No Minecraft class was executed. The 1.20.1 official client JAR SHA-1 is `0c3ec587af28e5a785c0b4a7b8a30f9a8f78f838`; its SHA-256 and extracted class hashes are recorded.

The 1.21.1 official client JAR and item/block display parents were independently read and hashed. **The extrusion algorithm itself is verified only against 1.20.1, not generalized to 1.21.1.** This limitation does not weaken the separate factor-two result: both versions' display parents and Tavern renderer scale calls were checked. UVs are the original pre-atlas face contract; atlas shrink/inset, sampling and filtering remain engine-specific.

## Frame, tint, material and coordinate boundaries

- Water fixtures use a labelled derived frame-0 crop with the actual source/controller RGB tint baked to an 8-bit PNG. Source water uses `(63,118,228)/255`; current uses `(0.247,0.463,0.894)`. Alpha is unchanged. This is a static color control, not shader execution.
- Water/lava original strip bytes and animation metadata remain in the inputs. UV animation is frozen to frame 0. Native animation timing, global phase, atlas interpolation, reload/reconnect behavior and helper replacement are untested.
- The frozen ice-grape tick 1 uses RGB interpolation while retaining the current frame's alpha. All 24 current tick PNGs match that source calculation exactly. Clock execution is not tested.
- Source barrel fluid height uses Java float32 multiplication. Native level formulas are evaluated mathematically as written. Tiny source/native floating-point differences are retained, not rounded away.
- Preview textures explicitly request **front-sided** rendering. Free-mode preview does not establish Java translucent/no-cull semantics or Bedrock material alpha/culling. A native `.geo` preview using Auto/DoubleSide may show opposite faces through cutouts. Do not treat that editor behavior as engine acceptance.
- Current content coordinates are the explicit **Blockbench Bedrock decoded model-reference frame**. Source coordinates are centered Java PoseStack world coordinates. No unverified Bedrock entity-to-world frame conversion is inserted to make their positions or orientations agree. In-world facing, placement, body clearance and controller/bone execution are therefore not accepted. Scale comparisons are basis-invariant.
- Blending, sorting, selection, lighting, tint precision, PBR, no-cull behavior and actual engine alpha are untested. The neutral ice/stone PNG fixture is not evidence of inherited native texture pixels.

## Independent checks

`independent-audit.json` currently reports:

- 239 original input hashes checked.
- 56 content meshes, 742 directed original-input faces and 2,968 corresponding saved vertices checked.
- Maximum independent matrix disagreement `7.11e-15`; maximum vertex disagreement `1.42e-14` model pixels, bounded by arithmetic roundoff per comparison. These are **fixture-vs-input reconstruction errors**, not a source/current parity tolerance.
- 30 reused N02 body roots checked recursively for unchanged hierarchy, origins, rotations, cube vertices, shade, original PNG bytes and explicit normalized UVs.
- 54 embedded texture entries decoded and dimensions checked.
- 12 BP and 12 RP ingredient helper routes checked (four barrel slots plus eight pressing chunks), with no compensating scale fields.
- 24 animated tick PNGs independently checked, zero pixel mismatches.

`routing-and-source-audit.json` records all 16 active built-in fluid routes, branch pose-call checks, cross-version vanilla display parents, sprite comparisons and the unused 0.85 controller result. `manifest.json` pins every original input. `artifact-sha256.json` pins the whole deliverable.

## Prior evidence and untouched scope

Pinned public Blockbench READMEs were checked for machine/liquid/ingredient scope before adding samples. Existing bottle/signature liquid and held-shaker evidence is not reused as machine-content acceptance. N02 bodies are reused rather than duplicating their model reconstruction. Accepted held geometry/poses are not modified; the N02-referenced held attachable and geometry were rechecked against the current canonical tree. No runtime files were written.

This is a prepared GUI queue, not completed visual acceptance, all-addon coverage, Minecraft/client/BDS acceptance or a published fix.

## Reproduce without a GUI

From this directory, with the pinned local repositories and official archives present:

1. `python prepare_inputs.py`
2. `python build_scenes.py`
3. `python validate_scenes.py`
4. `python finalize_review.py`

All computations are bounded and single-process. The `.bbmodel` files open without external files or plugins. Keep them as review artifacts and never export them over runtime assets.
