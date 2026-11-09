# Tavern decorative Blockbench evidence, 2026-11-09

**Completed bounded editor review: 25 scenes, 79 ordinary Java/source–native pairs, and a separate magenta three-way comparison.** The 84 distinct, unmodified 1188×848 JPEG captures are directly viewable in the [scene and capture index](scene-index.md). The recorded reviewer inspected every image in official Blockbench 5.2.2. This documentation package does not reopen the GUI or add new visual acceptance.

No additional unexplained source/native discrepancy was observed within those comparisons. This is **editor evidence**, not native Bedrock or Java client acceptance, full visual parity, gameplay acceptance, or completion of other addons.

## What was reviewed

- Seven table forms and seven bare trellis forms: perspective, TOP and BOTTOM.
- Seventeen string-light colours/forms and eighteen grape crop stages: perspective plus opposite oblique orthographic views.
- Thirty grapevine growth/connection forms: perspective, opposite oblique orthographic views and a further underside oblique orthographic view. All nine vine scenes have four views; the other sixteen scenes have three.
- Magenta: perspective, BOTTOM and low underside perspective. Forge/native retain twelve petal back faces, for 47 faces, while NeoForge and the pinned JAR omit them, for 35 faces. This confirmed source-branch difference is not automatically a runtime defect or a rollback request.

The known plant adaptation remains explicit: 336 faces differ by ±0.08 model units, producing native thickness 0.16 rather than exact source zero-thickness geometry. In the 79 accepted ordinary comparisons, the unchanged ordered audit has 1,386 paired faces: 1,050 exact and 336 thickness-adapted, with no UV, shade or texture-pixel mismatch. GUI observations do not remove that geometric difference.

## Current scope versus historical provenance

The captured scenes were prepared against **0.6.212**, runtime tree `e269f993ad73f091e49866e31df4929817505480`. Their inputs were then checked against main `d42a39745f25082aa129f4d4bb823684e4174771`, **0.6.213**, runtime tree `38c5977dd6bfe14b1824734612e3c601e1e41028`.

All 417 historical input files still match their original hashes. Of 149 corresponding current canonical files, 147 are identical. The only two changed inputs are `incense_closed.geo.json` and `incense_open.geo.json`, repaired in [PR #609](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/pull/609). All four incense scenes, their sixteen states, and catnip are excluded from this current GUI batch. The verifier rechecks all 149 current files when given a canonical checkout.

The archives retain the **original bytes** of the historical manifest, scripts, reports and 29 scenes: 28 original paired scenes including four old incense scenes, plus the magenta scene. The original preparation README and records still say “pending” or `gui_reviewed: false`. The historical underside audit still reproduces its sixteen missing fill bottoms and 256 depth / 254 colour ray differences. These are provenance of the already repaired 0.6.212 inputs, **not current failures or pending current acceptance**. No historical flag, scene UUID, hash, model or report was silently corrected. The later, separate [GUI review record](gui-review.json) establishes this batch's accepted scope.

## Coordinates and camera captions

Ordinary source is at lower world X; native is at higher world X within each pair. The default negative-X/negative-Z perspective and matching oblique orthographic project native screen-left and source screen-right. TOP/BOTTOM and opposite positive-X/positive-Z oblique views put source screen-left and native screen-right. Row order can reverse. Use the per-image direction and exact case offsets in the [index](scene-index.md) or [CSV](capture-index.csv).

Magenta uses Forge world X=-30, native X=0, NeoForge/JAR X=+30. The initial perspective shows NeoForge/JAR left and Forge right; BOTTOM and low underside show Forge left and NeoForge/JAR right. Orthographic views intentionally remain oblique so different Z rows do not overlap. Named TOP/BOTTOM camera labels are visible in the original captures.

## Portable package

- `images/`: all 84 original JPEGs, no crop, stitch, reencoding or reconstruction.
- `gui-review.json`: original completed GUI index, SHA-256 `4c2cc47ec511ada4b81181083fc4d50a955fe2e0fc89457d387282f57b7c795c`.
- `latest-input-reuse.json`: original subsequent byte-reuse check, not a new render claim.
- `archives/`: eight independent standard ZIP files, each below 200,000 bytes (largest 185,241). Extract together into one **new external directory**; they do not overlap. All 1,085 archived entries have exact bytes, size and SHA-256 in `archive-entries.json`.
- Historical sources include 417 original inputs, the exact 134 locked-JAR asset blobs, 444 bounded pinned Git asset/blockstate blobs, 33 original blockstate files, source receipts, audit scripts, and licences. Twenty-four matching paths are absent from the unpublished branch and are recorded as absent, not silently filled from another branch. There is no full mod JAR, Blockbench bundle, executable, private integration, world or credential.
- `source-snapshot-index.json`: branch/commit/path identity of the 468 bounded Git lookups, including 24 documented absences. Replay checks hashes and byte/JSON/pixel equality from the included blobs; it cannot establish independent publisher authentication or re-prove remote absence without fetching those commits.
- `audits/` and `audit-portability.patch`: reviewable portable audit copies and a zero-context unified diff. Calculations and acceptance predicates are unchanged. Only historical input paths are mapped in memory, pinned Git reads use the same bounded bytes, and outputs go to a separate rerun directory. One explicit `scene.save()` call in the magenta script is suppressed so replay never replaces the captured scene. Its comparison is still computed in memory.
- `artifact-sha256.json`: complete direct-file inventory, excluding only itself and the generated `verification.json` receipt. `verification.json` is informational, not trusted as validation input.

The original absolute paths retained in historical documents are provenance identifiers, not instructions to read or write those paths. Replay accepts only declared canonical relative members under resolved extraction roots. It checks duplicate/missing inventory entries, symlinks, ZIP member types, original input bytes, source comparisons, required scene views, 84 distinct image hashes, dimensions, case offsets, and all five audit reports. The saved reports and scenes are checked again unchanged after replay.

## Reproduce without the original workspace

Requires Python 3.10+ with Pillow, NumPy and SciPy. Validated with Python 3.12.14, Pillow 13.0.0, NumPy 2.3.5 and SciPy 1.17.0. From a checkout, run:

```sh
python docs/evidence/blockbench-decor-20261109/validate_evidence.py --repository .
python docs/evidence/blockbench-decor-20261109/test_verifier_boundaries.py
```

The optional `--repository` checks current canonical files against the documented 0.6.213 hashes. Omit it for self-contained evidence replay. `--work-dir /new/external/path` retains the fresh extraction, and `--report /new/external/report.json` writes an exclusive new receipt. Both destinations must be new and outside evidence and **every Git checkout**, including symlink aliases. Default replay uses a temporary directory. Existing files are never overwritten. Python `-O` / `PYTHONOPTIMIZE` is rejected; assertions must remain active. Do not run historical scene-generation scripts: they are retained for provenance, not required for replay.

The replay runs structural/ordered-face, full historical routing, historical underside, and magenta branch audits. Each report must match all saved JSON values, scalar types and array ordering after the declared path relocation only. Object-key order is immaterial. No numeric rounding, geometry normalization or altered acceptance rules are used.

## Source attribution and limits

Assets and source are by the **Kaleidoscope Official Production Team**, from [KaleidoscopeMods/KaleidoscopeTavern](https://github.com/KaleidoscopeMods/KaleidoscopeTavern): Forge `c4ec1880bd44cf3139d3ba744ab30bb379cf1416`, NeoForge `a1afba34981a00e89d57130d3dc8f1e64f1820a2`, and unpublished `9b8f165a`. This is an unofficial port review, not author endorsement. Original asset notices are in [LICENSE-ASSETS](LICENSE-ASSETS) ([CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)); code notices are in [LICENSE-CODE](LICENSE-CODE) (BSD 3-Clause). Copies from both original checkouts are retained in the archives. Source inputs are unchanged; the prepared paired editor scenes adapt the port geometry for comparison and are not author originals.

The locked `kaleidoscopetavern-1.2.0-neoforge+mc1.21.1.jar` identity is a verified user-upload SHA-256/blob record, not a publisher checksum. Only bounded asset blobs are included; no JAR was executed. The Blockbench codec provenance report describes signed endpoints, UV quarter turns, rescale and a 0.001 preview zero-plane epsilon; that epsilon is not native geometry. No application bundle is redistributed.

This evidence does not establish native shaders, culling/alpha sidedness, emission, ambient lighting, tint, water behavior, connection/growth mechanics, particles, item/held poses, boards, device renderers, barrel assembly, wild vines or other addons. No runtime, version, baseline, CI classifier, BDS, LIVE world or user-local computer was changed by packaging. Repository release/observer fixture checks are source regressions, not native gameplay sessions.
