# Tavern Blockbench visual review, 2026-11-08

This is a bounded editor review of Tavern 0.6.212 at `e58b5a421d101f83418b82a960faa1b94d0c2a73`, not an all-addon or Minecraft-client acceptance certificate. Runtime, release identity, accepted held poses and deployment are unchanged.

**Correction:** the six Signature Java-side review fixtures below omitted the source's `rotation.rescale` on two 45-degree planes. Their whole-cup geometry comparison is superseded by the [corrected fixtures and six new GUI captures](../blockbench-signature-rescale-20261108/README.md). The runtime side already had the scale baked in; this was an evidence-adapter error, not a runtime fix. Original files remain here as historical evidence. Shaker and furniture results retain their stated scope.

**Caption correction:** the paired perspective captures show **native Bedrock on screen-left and Java on screen-right**. Java occupies the lower world-X position (furniture X=-13; Signature X=-7), while native occupies the higher position (X=+13 or +7). Blockbench's default free-format perspective camera is at [-40,32,-40], looking toward [0,12,0], so +X projects toward screen-left. Historical scene titles using `LEFT`/`RIGHT` confused world-X placement with screen direction and are not evidence of screen-side identity. Only these captions are corrected; screenshots and projects remain unchanged, with their original hashes retained. The Signature rescale withdrawal above remains in force.

## Method and source

- Official Blockbench 5.2.2, Linux desktop. No plugin or server was loaded for this review.
- Shaker: opened the committed `runtime_shaker_held.geo.json`, imported the original 64×64 PNG, and used the automatically discovered committed `runtime_shaker.animation.json` in Animate mode. First-person and third-person images use Blockbench's built-in item contexts.
- Furniture: self-contained review-only `.bbmodel` scenes place the `Java authored` group at world X=-13 and the `canonical` Bedrock group at X=+13; the captured perspective shows native on screen-left and Java on screen-right. Original PNG bytes are embedded. Only the layout translation differs; runtime files were not exported or saved from these projects.
- Bedrock decoding uses Blockbench's X-coordinate reflection, X/Y rotation signs and top/bottom UV endpoint conventions. All 24 furniture variants match Java's geometry and UV data after decoding. A zero-angle pivot is geometrically inert; numeric integer/float representations are compared by value. This data comparison does not replace looking at the rendered scene.
- Source main/Java 1.20.1: `c4ec1880bd44cf3139d3ba744ab30bb379cf1416`; 1.21.1: `a1afba34981a00e89d57130d3dc8f1e64f1820a2`; 26.1.2: `9b8f165a4641e738e694641dd81240a0206573e1`. The 24 furniture model definitions and relevant PNG pixels match current 1.21.1 semantically. Line endings/PNG storage bytes can differ.
- 26.1.2 lacks the four cellar cabinet model paths and the signature cocktail model path in this comparison. Absence on that branch is not treated as a direction to remove retained features.

## Shaker

The original model and texture loaded. At right-hand first-person idle and animation times 0.05 s and 0.16 s, the textured cup stayed assembled and the two sampled positions visibly differed. The original third-person attachment rendered on the built-in player. These are two editor samples, not a full frame-by-frame motion recording, timing/frequency calibration or proof of the engine's query clock.

- [Original textured geometry](screenshots/shaker-base-textured.jpg)
- [First-person idle](screenshots/shaker-hold-first.jpg)
- [First-person shake at 0.05 s](screenshots/shaker-shake-time005.jpg)
- [First-person shake at 0.16 s](screenshots/shaker-shake-time016.jpg)
- [Third-person attachment](screenshots/shaker-hold-third.jpg)

The focused source-pose check evaluated 2,016 cases; 15 held-frame/native-frame tests passed. Their outputs explicitly retain `clientTested: false`. Off-hand slot setup was not independently established in the editor, so selecting a left-hand animation in the default right-hand context is **not** counted as off-hand visual acceptance. Player-arm shaking, HUD, cancel/restart/slot-switch, engine clock and FOV behaviour remain outside this review.

## Signature cup

**Superseded visual comparison.** Use the [corrected Signature review](../blockbench-signature-rescale-20261108/README.md). The original six source-side fixtures did not apply Java `rotation.rescale`; they also did not preserve the source's `shade` flags. The old geometry/visible-pattern equivalence inference is withdrawn. The unchanged shipped-data regression below checks its own native source-face/RGB contract, not the omitted Java rescale transform.

Six review scenes compare the Java whole cup against the committed runtime glass plus all ten RGB geometry layers for each animation frame. Every frame PNG matches the corresponding source strip pixels. The RGB case is the untinted `(255,255,255)` case: editor-only solid swatches represent the output of each actual layer's overlay colour. This is a geometry/texture composition check, **not** execution of render controllers, arbitrary mixture colours, PBR or Bedrock material shaders.

The independent shipped-data regression passed 2,856 source-face texel samples and 7,680 RGB channel cases across six frames and ten colour groups. The 1.21.1 source has the same geometry but uses `translucent` instead of main's `cutout`; relevant source alpha values are 0 or 255. No engine material/sorting equivalence is inferred from that fact.

The six historical GUI views below demonstrate what was opened, but their Java side is incomplete and must not be used to infer whole-cup geometric equivalence or a runtime size defect. No runtime size correction was made. Corrected views are linked above.

- [Frame 0](screenshots/signature-frame-0.jpg) · [Review scene](scenes/signature-frame-0.bbmodel)
- [Frame 1](screenshots/signature-frame-1.jpg) · [Review scene](scenes/signature-frame-1.bbmodel)
- [Frame 2](screenshots/signature-frame-2.jpg) · [Review scene](scenes/signature-frame-2.bbmodel)
- [Frame 3](screenshots/signature-frame-3.jpg) · [Review scene](scenes/signature-frame-3.bbmodel)
- [Frame 4](screenshots/signature-frame-4.jpg) · [Review scene](scenes/signature-frame-4.bbmodel)
- [Frame 5](screenshots/signature-frame-5.jpg) · [Review scene](scenes/signature-frame-5.bbmodel)

## Furniture

All 24 pairs were opened in the native GUI with textures loaded. The inspected perspective shows matching silhouette, join-end shape and visible wood/cushion/glass details. No missing texture or mismatched visible UV was confirmed. These are one-view pair inspections, not a multi-angle or in-world connection test. Some images retain Blockbench's pointer-hover face highlight; this editor highlight is not a texture/material difference.

| Family | Variants inspected | GUI observations |
| --- | --- | --- |
| Bar counter | Single, left, middle, right, left corner, right corner | Dark worktop, wood panels and gold trim present on both sides. |
| Bar cabinet | Single, left, middle, right | Cabinet frame, shelf and open-front textures present on both sides. |
| Cellar cabinet | Single, left, middle, right | Source-shaped storage frame and shelf textures present on both sides. |
| Glass bar cabinet | Single, left, middle, right | Glass/cutout faces and frame details present on both sides; no engine transparency claim. |
| Blue sofa | Single, left, middle, right, left corner, right corner | Blue cushions, applicable end/arm shapes and legs present on both sides. |

- [bar_counter_single](screenshots/bar_counter_single.jpg) · [Review scene](scenes/bar_counter_single.bbmodel)
- [bar_counter_left](screenshots/bar_counter_left.jpg) · [Review scene](scenes/bar_counter_left.bbmodel)
- [bar_counter_middle](screenshots/bar_counter_middle.jpg) · [Review scene](scenes/bar_counter_middle.bbmodel)
- [bar_counter_right](screenshots/bar_counter_right.jpg) · [Review scene](scenes/bar_counter_right.bbmodel)
- [bar_counter_left_corner](screenshots/bar_counter_left_corner.jpg) · [Review scene](scenes/bar_counter_left_corner.bbmodel)
- [bar_counter_right_corner](screenshots/bar_counter_right_corner.jpg) · [Review scene](scenes/bar_counter_right_corner.bbmodel)
- [bar_cabinet_single](screenshots/bar_cabinet_single.jpg) · [Review scene](scenes/bar_cabinet_single.bbmodel)
- [bar_cabinet_left](screenshots/bar_cabinet_left.jpg) · [Review scene](scenes/bar_cabinet_left.bbmodel)
- [bar_cabinet_middle](screenshots/bar_cabinet_middle.jpg) · [Review scene](scenes/bar_cabinet_middle.bbmodel)
- [bar_cabinet_right](screenshots/bar_cabinet_right.jpg) · [Review scene](scenes/bar_cabinet_right.bbmodel)
- [cellar_cabinet_single](screenshots/cellar_cabinet_single.jpg) · [Review scene](scenes/cellar_cabinet_single.bbmodel)
- [cellar_cabinet_left](screenshots/cellar_cabinet_left.jpg) · [Review scene](scenes/cellar_cabinet_left.bbmodel)
- [cellar_cabinet_middle](screenshots/cellar_cabinet_middle.jpg) · [Review scene](scenes/cellar_cabinet_middle.bbmodel)
- [cellar_cabinet_right](screenshots/cellar_cabinet_right.jpg) · [Review scene](scenes/cellar_cabinet_right.bbmodel)
- [glass_bar_cabinet_single](screenshots/glass_bar_cabinet_single.jpg) · [Review scene](scenes/glass_bar_cabinet_single.bbmodel)
- [glass_bar_cabinet_left](screenshots/glass_bar_cabinet_left.jpg) · [Review scene](scenes/glass_bar_cabinet_left.bbmodel)
- [glass_bar_cabinet_middle](screenshots/glass_bar_cabinet_middle.jpg) · [Review scene](scenes/glass_bar_cabinet_middle.bbmodel)
- [glass_bar_cabinet_right](screenshots/glass_bar_cabinet_right.jpg) · [Review scene](scenes/glass_bar_cabinet_right.bbmodel)
- [sofa_single](screenshots/sofa_single.jpg) · [Review scene](scenes/sofa_single.bbmodel)
- [sofa_left](screenshots/sofa_left.jpg) · [Review scene](scenes/sofa_left.bbmodel)
- [sofa_middle](screenshots/sofa_middle.jpg) · [Review scene](scenes/sofa_middle.bbmodel)
- [sofa_right](screenshots/sofa_right.jpg) · [Review scene](scenes/sofa_right.bbmodel)
- [sofa_left_corner](screenshots/sofa_left_corner.jpg) · [Review scene](scenes/sofa_left_corner.bbmodel)
- [sofa_right_corner](screenshots/sofa_right_corner.jpg) · [Review scene](scenes/sofa_right_corner.bbmodel)

## Reopening the evidence

The 30 `.bbmodel` projects are review-only, self-contained and embed their textures. Open them in Blockbench 5.2.2 without plugins. They must not be exported over runtime assets. The Java importer resolves only the direct elements/single texture used here; face UVs are scaled independently by the actual texture width and height divided by 16. It is not a general Java parent, rescale or multi-texture converter.

`scene-records.json` pins the source inputs. Its `source/` prefix means this repository at the runtime commit above; `java-reference/` means [the Java source repository](https://github.com/KaleidoscopeMods/KaleidoscopeTavern) at the pinned source commit. `furniture-data-comparison.json`, `upstream-comparison.json`, and the focused shaker/signature outputs preserve their separate data-check scope. `artifact-sha256.json` hashes all 35 GUI images and 30 review projects. Screenshots are unmodified native desktop captures, not synthetic renders.

## Remaining limits

- No user's local computer, LIVE server, Minecraft client or saved world was used.
- Blockbench is not Minecraft's renderer. Lighting, PBR, draw ordering, runtime property/controller selection, frame pacing and multiplayer visibility are not certified here.
- Furniture coverage is 24 shapes: bar counter (6), bar cabinet (4), cellar cabinet (4), glass bar cabinet (4), blue sofa (6). Other dye variants, stools, lamps, racks, boards, devices, bottle states and hand/inventory contexts are not added to this review by association.
- Earlier evidence remains scoped to its original inputs. In particular, the recorded T194/W180 Allium first-person viewport clipping failure is not resolved by these shaker images.
- No runtime fix was made without a confirmed defect. A documentation-only evidence change needs no pack bump or release/redeployment.
