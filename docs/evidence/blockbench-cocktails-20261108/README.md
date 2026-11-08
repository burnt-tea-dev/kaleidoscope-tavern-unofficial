# Cocktail editor review, 2026-11-08

Completed in official Blockbench 5.2.2: 20 exact self-contained projects, 21 raw GUI screenshots, 14 classic cups and all 45 authored texture frames. No new runtime defect was established and no runtime assets were changed.

Review target: Tavern 0.6.212 at `4700ede2207f26193535bcd8054a6987f413286d`. Runtime, accepted held transforms, identity, deployment and worlds are unchanged. This extends the earlier furniture and corrected Signature evidence, not Minecraft-client acceptance.

## Which Java source is being compared

The active repository intentionally adopted the official Forge cocktail-art optimization at `c70eec14b4d8cede23f7274910b8424a8fd49f89` (2026-07-06). Its model, UV, PNG and shade changes are recorded per cup in [UPSTREAM-VISUAL-SYNC.json](../../../history/pre-release-0.6.29/docs/UPSTREAM-VISUAL-SYNC.json). Current Forge main `c4ec1880bd44cf3139d3ba744ab30bb379cf1416` (2026-07-21) retains them.

NeoForge 1.21.1 at `a1afba34981a00e89d57130d3dc8f1e64f1820a2` (2026-07-01) has different, earlier cocktail artwork. All 14 actual model blobs from the pinned uploaded 1.2.0 NeoForge JAR were retrieved by their recorded Git object IDs and checked against SHA256 and size. Their complete parsed JSON equals this NeoForge branch. The seven changed block PNGs also match the pinned JAR member hashes. This establishes that the branch difference is real; it does **not** make the deliberately selected newer Forge artwork stale. No rollback was made. A larger Minecraft version number is not a chronology of artwork.

The source selection remains per-loader, as documented by [family/java-upstream.json](../../../family/java-upstream.json). All 32 inspected cocktail paths are absent from the separate 26.1.2 branch `9b8f165a4641e738e694641dd81240a0206573e1`, verified with its tree listing. That absence does not authorize deleting retained features.

## Data checks, separate from GUI

- Fourteen current classic models contain 835 nondegenerate textured faces. Each has a unique Forge-source counterpart with equal ordered UV endpoints and matching UV-corner world coordinates within 0.0625 model units. Signed dimensions, active pivots, Java rescale and face quarter-turns are included. The bound is the existing thin-plane/same-facing separation adaptation in `tools/repair_drink_planes.py`, not unexplained shape drift. No mirrored or rotated UV mapping discrepancy was found.
- All 14 Forge/runtime PNG strips have identical decoded RGBA. Animated sources are inspected as original square frames, not by stretching the whole strip over each model.
- Java `rotation.rescale` is baked into the two perpendicular axes about the authored pivot, and Java shade flags are preserved. Native cube shade hints are resolved from each actual BP `material_instances` entry's `face_dimming`; all inspected cubes have uniform hints. These are editor hints, not execution of Bedrock materials, AO or shaders.
- Allium's flower scale is already correct: its authored 11-unit width becomes 15.556349186 before rotation. The existing native thickness changes the X/Z extent from ±5.5 to about ±5.544194179. No rescale repair is justified.
- Geometry and texture consumers are the real placed BP block references. Some inventory routes separately use generated sprites. A placed-cup review does not certify those sprite routes or held display contexts.

## GUI coverage

Twenty distinct self-contained projects cover 14 cups and 45 original source frames. The ten static cups contribute one frame each; Depth Charge four, Mystery Cocktail nine, Nether Special six and Sculk Special sixteen. These are static frame inspections, not clock, frame-rate, interpolation or playback acceptance.

Within ordinary pairs, Forge is at relative world -X and runtime at +X. The captured default perspective shows **native on screen-left and Forge on screen-right**. The seven branch-comparison projects place Forge at relative X=-16, native at X=0 and NeoForge at X=+16, so the screen order is **NeoForge left, native centre, Forge right**. The additional Allium NORTH image has the same screen order. For four-frame sheets, ascending indices use coordinates (-X,-Z), (+X,-Z), (-X,+Z), (+X,+Z), appearing near/bottom, left, right and far/top respectively. Scene groups identify exact frames. Perspective changes apparent size; it is not a geometry measurement.

Some unchanged project display names contain earlier LEFT/RIGHT labels derived from world X. Those labels were not screen-space directions and are incorrect for these camera views. Use this corrected description, the group source names and recorded coordinates. The exact captured project bytes are preserved, rather than silently relabelled after capture. The three earlier evidence READMEs receive the same view-specific caption correction; their historical images and project archives remain unchanged.

The seven branch variants are Allium Garden, Bloody Mary, Depth Charge, Grasshopper, Mojito, Screwdriver and White Lady. Their visible differences are intentional source variants. Earlier exploratory screenshots without native face-dimming hints are not included as completed evidence.


## Observations and image index

All 20 projects displayed their embedded textures and complete cup assemblies. The cups, stems, rims, straw or garnish elements were visible in the recorded views. The four animated cups showed the authored differences between their static texture frames, including the expanding/fading Sculk ring. No additional missing model, texture, reversed UV mapping or unexplained detached element was established by this review. Bloody Mary's floating red pieces are authored source geometry, not a new port defect.

Allium's extra NORTH view resolves a source-identification ambiguity: the leftmost NeoForge flower starts one texel higher than the central native and rightmost Forge flowers. Forge/native north UV [15,20,26,30] and the transparent row20 place the first opaque edge at Y=14.75; NeoForge's shifted [15,21,26,31] puts it at Y=15.75. This agrees with the existing deliberate source variant and does not justify altering native geometry.

Each `.jpg` named after a scene is that scene's raw desktop capture. There are 20 main images plus the Allium NORTH view:

- [allium_garden-source-branches-bound](allium_garden-source-branches-bound.jpg): frames 0; three source variants.
- [bloody_mary-source-branches-bound](bloody_mary-source-branches-bound.jpg): frames 0; three source variants.
- [brass_heart-bound](brass_heart-bound.jpg): frames 0; Forge/native pair per frame.
- [depth_charge-frames-0-3-source-branches-bound](depth_charge-frames-0-3-source-branches-bound.jpg): frames 0, 1, 2, 3; three source variants.
- [emerald-bound](emerald-bound.jpg): frames 0; Forge/native pair per frame.
- [empty_glassware-bound](empty_glassware-bound.jpg): frames 0; Forge/native pair per frame.
- [godfather-bound](godfather-bound.jpg): frames 0; Forge/native pair per frame.
- [grasshopper-source-branches-bound](grasshopper-source-branches-bound.jpg): frames 0; three source variants.
- [mojito-source-branches-bound](mojito-source-branches-bound.jpg): frames 0; three source variants.
- [mystery_cocktail-frames-0-3-bound](mystery_cocktail-frames-0-3-bound.jpg): frames 0, 1, 2, 3; Forge/native pair per frame.
- [mystery_cocktail-frames-4-7-bound](mystery_cocktail-frames-4-7-bound.jpg): frames 4, 5, 6, 7; Forge/native pair per frame.
- [mystery_cocktail-frames-8-8-bound](mystery_cocktail-frames-8-8-bound.jpg): frames 8; Forge/native pair per frame.
- [nether_special-frames-0-3-bound](nether_special-frames-0-3-bound.jpg): frames 0, 1, 2, 3; Forge/native pair per frame.
- [nether_special-frames-4-5-bound](nether_special-frames-4-5-bound.jpg): frames 4, 5; Forge/native pair per frame.
- [screwdriver-source-branches-bound](screwdriver-source-branches-bound.jpg): frames 0; three source variants.
- [sculk_special-frames-0-3-bound](sculk_special-frames-0-3-bound.jpg): frames 0, 1, 2, 3; Forge/native pair per frame.
- [sculk_special-frames-4-7-bound](sculk_special-frames-4-7-bound.jpg): frames 4, 5, 6, 7; Forge/native pair per frame.
- [sculk_special-frames-8-11-bound](sculk_special-frames-8-11-bound.jpg): frames 8, 9, 10, 11; Forge/native pair per frame.
- [sculk_special-frames-12-15-bound](sculk_special-frames-12-15-bound.jpg): frames 12, 13, 14, 15; Forge/native pair per frame.
- [white_lady-source-branches-bound](white_lady-source-branches-bound.jpg): frames 0; three source variants.
- [Allium NORTH](allium_garden-source-branches-bound-front.jpg): NeoForge left, native centre, Forge right.

The separate [editor WebGL error](editor-webgl-error.jpg) records an environment failure, not model acceptance. After multiple projects had been opened, the original process stopped rendering even previously working scenes; a new window explicitly reported “Error creating WebGL context.” A separate process of the same official executable with a fresh profile restored rendering of the same model bytes. The existing tabs were left untouched during recovery; none were saved or closed by this review. No plugin, server, sandbox bypass or security-setting change was used. The remaining scenes and fully framed Depth Charge and Sculk 8–11 recaptures were then completed. The underlying context failure was not diagnosed further.

Screenshots are original JPEG bytes without crop, rescale, retouch or re-encoding. `artifact-sha256.json` pins every delivered artifact except itself. This records an editor visual inspection, not native Java or Bedrock rendering equivalence.

## Reproduce

Extract `scenes.zip` and open the `.bbmodel` files in [official Blockbench 5.2.2](https://github.com/JannisX11/blockbench/releases/tag/v5.2.2), without plugins or servers. They embed exact texture bytes and are review-only; never export them over runtime assets. `scene-entry-sha256.json` pins the exact projects. `scene-records.json` pins the source files, canonical geometry/texture inputs and BP material bindings.

For the read-only ordered-face audit, use Python with Pillow, NumPy and SciPy. Run `python docs/evidence/blockbench-cocktails-20261108/check_ordered_faces.py --java-assets /path/to/pinned-forge/src/main/resources/assets/kaleidoscope_tavern`. It checks source input hashes, refuses unsupported rotated native bone hierarchies, requires one-to-one face matching and asserts the 0.0625-unit bound. Optional `--neo-models /path/to/flat/neo-models-and-pngs` adds the seven hashed branch comparisons. `review_codec.py` is a bounded review reader, not a general model importer. The saved result was reproduced exactly with the checked sources. `ordered-uv-codec-provenance.json` identifies the official bundle and examined codec/UV-mapping locations; no application code bundle is redistributed.

The `source/` prefix in input records refers to this repository. `java-reference/` refers to the pinned Forge source checkout. `current-java-inputs.json` and `jar-model-comparison.json` retain separate NeoForge/JAR provenance. Publisher checksum verification of the original uploaded JAR remains false; the JAR was not executed.

## Remaining limits

No user computer, LIVE server, Minecraft client, saved-world test or deployment was used. This does not certify engine culling, transparency sorting, light/PBR appearance, frame interpolation, controller/property selection, item GUI, player arms, FOV, multiplayer or all addon assets. The earlier T194/W180 Allium first-person clipping finding remains unresolved. No runtime patch, version bump or release follows solely from these editor views.
