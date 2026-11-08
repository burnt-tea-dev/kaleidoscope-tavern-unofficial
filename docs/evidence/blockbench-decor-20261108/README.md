# Tavern decor and bottle editor review, 2026-11-08

Review target: Tavern 0.6.212 at `b2aba0e99d30b6dec87fdd06157da03998133f2b`. This extends the [first editor review](../blockbench-20261108/README.md), with unchanged runtime and accepted held poses. No user machine, LIVE server, Minecraft client or saved world is used.

## Inputs and scope

- Official Blockbench 5.2.2 Linux desktop, no plugin or service. Paired review-only scenes place Java on the left and canonical Bedrock on the right. Textures are embedded; none of these projects is a runtime export.
- Java main/1.20.1 source: `c4ec1880bd44cf3139d3ba744ab30bb379cf1416`. All 42 distinct Java model/texture inputs match 1.21.1 at `a1afba34981a00e89d57130d3dc8f1e64f1820a2` semantically or by RGBA pixels.
- Source 26.1.2 at `9b8f165a4641e738e694641dd81240a0206573e1` has 24/42 identical inputs, 17 absent paths, and a different empty-bottle model (five elements instead of four). This is recorded explicitly, not treated as permission to remove retained features or as proof of parity with that branch.
- Scope is empty circular/tilted racks; blue, yellow and bell two-block pendant lamps; six bottle shapes; and all 16 sofa colour textures on the single sofa geometry. This does not add other sofa shapes in other colours by association.
- The lamps combine the original bottom model with the top model translated up 16 model units. The runtime assembled geometry is used unchanged.
- Empty and experience bottles have negative-size boxes in the Java source. Their runtime face-only representation has a different cube count. This is an intentional representation distinction, not an automatic defect.
- The other nine individual pairs match normalized cube bounds, rotations and UV faces exactly. All 16 sofa source/runtime colour textures have equal RGBA pixels. Static comparisons remain separate from GUI evidence.

## GUI observations

The 15 scenes were opened in the native editor and captured in 19 unmodified screenshots. No missing texture, detached part, visible UV mismatch or assembly defect was confirmed in these views. Perspective makes nearer paired objects appear larger; no size adjustment was made.

- Empty circular rack: the post and six slot rims match in perspective and top view. The view does not simulate bottle placement.
- Tilted rack: supports and the slanted structure match in the inspected perspective.
- Three lamps: full assembled silhouettes and original textures match. Bottom views expose the blue/yellow lamp-face colour differences and bell underside, which are not visible clearly from the above-facing perspective. These are albedo checks, not light emission tests.
- Six bottle shapes: the cutout borders, caps and source texture colours are present on both sides. Empty/experience bottle face decomposition did not introduce a visible assembly error in the sampled perspective. Potion is the untinted base texture; no arbitrary potion colour is tested.
- Four sofa sheets: each sheet contains four colour pairs. All sixteen colours show matching source/runtime cushions, frame texture and legs on the single sofa shape. Their block/property selection is not executed.

| Scene | Native GUI image | Additional view |
| --- | --- | --- |
| circular_rack | [Perspective](screenshots/circular_rack.jpg) | [Top](screenshots/circular_rack-top.jpg) |
| tilted_rack | [Perspective](screenshots/tilted_rack.jpg) | — |
| blue_pendant_lamp_assembled | [Perspective](screenshots/blue_pendant_lamp_assembled.jpg) | [Bottom](screenshots/blue_pendant_lamp-bottom.jpg) |
| bell_pendant_lamp_assembled | [Perspective](screenshots/bell_pendant_lamp_assembled.jpg) | [Bottom](screenshots/bell_pendant_lamp-bottom.jpg) |
| yellow_pendant_lamp_assembled | [Perspective](screenshots/yellow_pendant_lamp_assembled.jpg) | [Bottom](screenshots/yellow_pendant_lamp-bottom.jpg) |
| empty_bottle | [Perspective](screenshots/empty_bottle.jpg) | — |
| water_bottle | [Perspective](screenshots/water_bottle.jpg) | — |
| xp_bottle | [Perspective](screenshots/xp_bottle.jpg) | — |
| potion_bottle | [Perspective](screenshots/potion_bottle.jpg) | — |
| honey_bottle | [Perspective](screenshots/honey_bottle.jpg) | — |
| dragon_breath_bottle | [Perspective](screenshots/dragon_breath_bottle.jpg) | — |
| sofa-colours-0 | [Perspective](screenshots/sofa-colours-0.jpg) | — |
| sofa-colours-1 | [Perspective](screenshots/sofa-colours-1.jpg) | — |
| sofa-colours-2 | [Perspective](screenshots/sofa-colours-2.jpg) | — |
| sofa-colours-3 | [Perspective](screenshots/sofa-colours-3.jpg) | — |

Each sofa colour appears twice, Java on the left within its pair. Sheet 0: white, orange, magenta, light blue. Sheet 1: yellow, lime, pink, gray. Sheet 2: light gray, cyan, purple, blue. Sheet 3: brown, green, red, black.

## Limits and reproduction

Download [the 15 self-contained review projects](scenes.zip), extract them, then open the `.bbmodel` files in Blockbench. The archive preserves the exact project bytes opened for this review; it avoids duplicating large pretty-printed model data in the document diff. Never export them over canonical runtime assets. The bounded converter and coordinate conventions are described in the first review. `scene-records.json` pins each input; `source/` means this repository and `java-reference/` means [KaleidoscopeTavern](https://github.com/KaleidoscopeMods/KaleidoscopeTavern) at the source commit above.

`artifact-sha256.json` hashes the 19 screenshots, the archive and each of its 15 model entries. No screenshot is cropped, repainted or reconstructed.

This work does not test PBR, light emission, engine transparency/sorting, potion tint/controller selection, rack contents or placement/interaction, hand/inventory contexts, seat passengers, runtime colour routing, or Minecraft rendering. Bar-stool entity geometry and seating dynamics are not included. No runtime fix, version bump, release or deployment is justified solely by passing these editor views.
