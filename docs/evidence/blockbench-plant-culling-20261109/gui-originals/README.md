# Plant culling GUI controls, 2026-11-09

**Completed: nine matched Front/Double view pairs, 18 accepted original model-view JPEGs.** The directory also contains 24 original supporting JPEGs showing texture settings, numeric cameras and cleanup. No captured model views were excluded.

Every queued direction shows a visible change on the affected native models when Double is enabled: additional leaf/fruit coverage appears through transparent gaps. Both crop stages change in each crop view. All three ordinary single-vine stages change in every vine view. **All source controls, and the already-Front `north_south` source/native vine controls, remain unchanged.** There is no full view pair with no visible native change; the connected-form control is the intentional unchanged result.

These are Blockbench editor material-sidedness controls, not execution of BP material instances or native Minecraft/BDS rendering. Geometry/source policy proof remains separate in the frozen preparation artifacts. No runtime repair, native-engine acceptance or publication is claimed.

## Review and evidence

`review-index.json` is the exact review index. It records SHA-256, original dimensions, bytes, write time, backing scene identities, unsaved variant identity, camera, screen/world captions, observations and accepted/excluded status for each capture. Each JPEG is the original `app.getScreenshot()` byte result at **1188 × 848**, written directly. None was cropped, edited, stitched or re-encoded.

| Scene | View | Front | Double |
| --- | --- | --- | --- |
| Ordinary crop stages 4–5 | Oblique | [Front](grape-crop-stages-2-oblique-front.jpg) | [Double](grape-crop-stages-2-oblique-double.jpg) |
| Ordinary crop stages 4–5 | Reverse | [Front](grape-crop-stages-2-reverse-front.jpg) | [Double](grape-crop-stages-2-reverse-double.jpg) |
| Gold crop stages 4–5 | Oblique | [Front](gold_grape-crop-stages-2-oblique-front.jpg) | [Double](gold_grape-crop-stages-2-oblique-double.jpg) |
| Gold crop stages 4–5 | Reverse | [Front](gold_grape-crop-stages-2-reverse-front.jpg) | [Double](gold_grape-crop-stages-2-reverse-double.jpg) |
| Ice crop stages 4–5 | Oblique | [Front](ice_grape-crop-stages-2-oblique-front.jpg) | [Double](ice_grape-crop-stages-2-oblique-double.jpg) |
| Ice crop stages 4–5 | Reverse | [Front](ice_grape-crop-stages-2-reverse-front.jpg) | [Double](ice_grape-crop-stages-2-reverse-double.jpg) |
| Ordinary vine stages 0–2 and north_south | Oblique | [Front](grapevine-shapes-stages-2-oblique-front.jpg) | [Double](grapevine-shapes-stages-2-oblique-double.jpg) |
| Ordinary vine stages 0–2 and north_south | Reverse | [Front](grapevine-shapes-stages-2-reverse-front.jpg) | [Double](grapevine-shapes-stages-2-reverse-double.jpg) |
| Ordinary vine stages 0–2 and north_south | Reverse-low | [Front](grapevine-shapes-stages-2-reverse-low-front.jpg) | [Double](grapevine-shapes-stages-2-reverse-low-double.jpg) |

No selection outlines obscure the accepted views. Every staged model is within the image. The connected vine leaf rings overlap slightly in projection, identically in both variants; their changed-pixel checks remain zero.

## Exact one-variable procedure

1. Open each exact frozen `--policy-front.bbmodel`, retaining the unrelated Champagne tab.
2. Verify texture order and name against the manifest. Native texture index 1 is the second texture row. Blockbench displays `front` as **Outside**, and `double` as **Inside and Outside**.
3. Choose an explicit supported UI camera preset and capture Front.
4. In texture properties, change only native texture index 1 to Inside and Outside. Re-hide the sidebars without a camera action and capture Double.
5. Before the next angle, Undo the texture change and inspect Outside again. The tab may still show an unsaved dot after Undo; that marker does not identify sidedness.
6. Discard the scene tab without saving.

The Double image is an **unsaved UI state of the exact Front input**, corresponding to the independently verified sole-field difference in `--old-policy-double.bbmodel`. The Double file was not separately imported. Keeping one live camera avoids camera reconstruction differences between file imports.

For ordinary vine, both prepared variants isolate `north_south` on texture index 2. Its 18 face bindings and pixel-identical PNG were independently checked. The third texture row remained Outside before and after all Double controls, and neither its bindings nor its sidedness were edited.

## Actual cameras and captions

The supported Save Angle dialog exposes position, focal point and orthographic zoom. It was read and cancelled to record actual values. Temporary presets were created through that same UI, reused, then removed.

| View | Camera position shown | Focal point shown | Zoom shown |
| --- | --- | --- | --- |
| Oblique | (-512, 264, -512) | (0, 8, 0) | 0.1986 |
| Reverse | (512, 264, 512) | (0, 8, 0) | 0.1986 |
| Reverse-low | (512, -248, 512) | (0, 8, 0) | 0.1986 |

All use orthographic projection. The numeric values retain the UI's displayed precision; no internal camera matrix was read. The initial oblique preset-definition screenshot contains a typed zoom of 0.23, but actual observed zoom after applying the preset was 0.1986 for every view. The actual observations, not that setup field, govern this review.

The views follow the queue's world-axis directions. They are not claimed to reproduce the old historical JPEG cameras exactly.

- **Oblique:** native is screen-left of source within each pair. World +X projects left/up, +Z right/up, +Y up. Crop stage 5 is the left pair; stage 4 is the right pair.
- **Reverse:** source is screen-left of native. World +X projects right/down, +Z left/down, +Y up. Crop stage 4 is the left pair; stage 5 is the right pair.
- **Reverse-low:** source is screen-left of native. World +X projects right/up, +Z left/up, +Y up. This view exposes leaf undersides.

Vine case locations and exact source/native world offsets are included for each pair in the index. Do not use a universal source-left assumption across these views.

## Independent checks

`integrity-before.json` verifies all 30 frozen preparation artifacts and independently confirms that each Front/Double file pair differs only at `/textures/1/render_sides`. The vine's 18 invariant connected-face bindings are checked there too.

`integrity-after.json` confirms those same 30 artifacts and the artifact hash manifest are unchanged. It additionally rechecks six original scene files and all 204 pinned Git-object records in the preparation input manifest. Only local read-only Git object access was used.

`verify_gui_evidence.py` reads the original JPEGs and compares decoded pixels without producing altered images. Every changed pixel in the reviewed model area is confined to the affected native model rectangles. Source-control regions and both connected-vine control regions contain zero changed decoded pixels. Changed counts are 6,645–7,199 per crop pair and 10,106–10,489 per vine pair. These include JPEG block effects and are not counts of source model texels.

Recheck locally with:

```
python verify_gui_evidence.py
```

The script rewrites only this directory's review and verification JSON. It does not drive the GUI or alter model/runtime files.

## Cleanup and scope

All four own scene tabs were discarded unsaved. All three temporary camera presets were removed through the UI. Champagne remained visibly healthy in Blockbench window **29360132**, with no modal open. Terminal **41949001** and all other windows/processes were untouched. No white viewport occurred. GUI control was explicitly handed back to the parent for the next N03 batch.

This review preserves all existing geometry, directed faces, PNGs, UVs and the frozen native thickness adaptation. It does not apply the proposed 36 BP material-field changes, change gameplay, test a Bedrock client or BDS, certify native inventory/held poses, or deploy anything.
