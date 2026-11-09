# Tavern occupied-furniture Blockbench evidence, 2026-11-09

**Completed bounded editor review: eight scenes, twelve occupied source/current cases, 27 accepted original JPEG captures.** Nineteen additional camera, framing, selection and cleanup diagnostics are retained and excluded from acceptance. See the [scene/capture index](scene-index.md), the unchanged [completed GUI report](gui/gui-index.json), and its [review notes](gui/README.md).

No newly established visual migration defect was found in the pictured source geometry, UVs, slots and modeled occupied layouts. This is editor evidence of prepared reconstructions, not native Minecraft material/facing acceptance, addon helper/gameplay acceptance, an all-inventory review, or all-addon completion.

## Reviewed scope and identities

- Circular rack: all six bottle slots, yaw, extrema and neck/base alignment.
- Tilted rack: three slots, pitch and seating, including separately isolated source/current East profiles.
- Bar cabinets: north/east twin ordering, broad Brandy single layout, and the distinct glass-front body with the same bottle layout owner.
- Cellar: all nine slots, three-by-three spacing and separately captured body-hidden East profiles.
- Holder: Wine and Luminous contacts, pitched profiles and underside occlusion.
- Glassware holder: full north four-cup silhouette, hanging contacts and underside detail; sparse east/west cases retain their documented different reference frames.

SOURCE is X=-24 and CURRENT is X=+24. Cases advance along Z by 34 units. Screen side changes with the camera; named root groups, case IDs and compass identify the actual side. All selected textures are explicitly **Front-sided**. Numeric camera fields are provided only where actually read or set in the UI, with displayed precision, not invented from a screenshot.

The exact archived preparation retains canonical **0.6.213**, commit `cb2b37dfa2181ee042a090d8dbd434758a762afb`, runtime tree `38c5977dd6bfe14b1824734612e3c601e1e41028`, and its checked read-only worktree commit `e4209276dab846dc6689d5760bc9e1809261d58d`. Its original README, manifest and audit still say GUI pending/false. Those historical bytes are unchanged. The separate completed GUI report records subsequent inspection; it does not rewrite preparation history.

All **266 frozen artifacts** passed original GUI preflight/postflight. This package additionally preserves their inventory itself, for **267 preparation files**. All **131 selected canonical files** were rechecked unchanged at merged **0.6.215**, main `7fb1afc86439d67703df202d04923d4bcdc4466b`, full tree `af1a39378862291b3c9c6fdd22d8d4d42bed12b7`, runtime tree `a62a8655d96a71a9d1d6395b5fa8216ca298f197`. See [current input verification](current-input-verification.json). The old global runtime identity remains historical; the newer relevant-input equality does not claim a second GUI run.

## Preserving publication base update

Publication now uses merged **0.6.216**, main `2e14d0f348e9ad3f93a679d4c66fee1af8ab6051`, full tree `ffc0d9aaf7787580888bf2f29a5ef436c085e376`, runtime tree `fe2aa4c3c0e4f7b90f6998470cdb2a7b25ef331a`. The separate [0.6.216 base-reuse receipt](base-reuse-0.6.216.json) records exact equality of all **131 relevant inputs**. The intervening pressing-card and release-identity changes do not intersect those inputs. No new GUI or engine review occurred.

All original archives, captures, GUI receipts and the historical 0.6.215 input receipt remain unchanged. The unchanged portable verifier reports that historical documented base while `--repository .` checks the same 131 input bytes in the newer checkout. This supplement changes only the publication-base context, not acceptance or audit calculations.

## Reference-frame and material boundaries

Stored bottles reconstruct source Java PoseStack and the shipped helper position/yaw/scale/root-pitch contract. Pitch is applied exactly once by the RP root animation, while helper adapters set entity pitch to zero. These are the existing Java-compatible world-contract signs, **not a reinterpretation of raw Blockbench Euler signs as native renderer behavior**. Source float32 scales explain the preserved small numerical difference from native literals.

Sparse glassware is deliberately different: the source uses Java-world quadrants while current uses literal Blockbench-decoded canonical bones, including Blockbench's X negation. The separate shared world-slot checker covers 64 masks/facings and 256 visibility decisions under the recorded 2026-09-29 client convention. That convention was not re-observed in a client. No mirror/reposition correction was introduced and no apparent sparse-side reversal is called a native-facing failure.

Luminous keeps the exact accepted [#611](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/pull/611) adaptation: four covered bottom-strip crop faces and four cap surfaces offset by ±0.0625 model units per placement. The preserved count-one proof and all four original proof inputs bind the adaptation. The Java model input differs only in line endings; geometry and textures are exact. The eight adapted faces are not new mismatches or hidden by widened tolerances.

Forge `c4ec1880bd44cf3139d3ba744ab30bb379cf1416` and NeoForge `a1afba34981a00e89d57130d3dc8f1e64f1820a2` remain separately pinned. All 51 bounded model/texture/source comparisons are replayed. Seven renderer bodies match after excluding import lines. The empty glassware model's Forge cutout versus NeoForge translucent declaration differs, while the occupied-holder renderer explicitly requests cutout in both. Neither source runtime is executed. Editor Front, lighting and transparency cannot prove native culling, alpha sorting, AO, face dimming or shaders.

## Original capture events and cleanup

- All 27 accepted images and 19 excluded diagnostics are untouched **1188×848 JPEG byte streams**, with no re-encoding, cropping, compositing or synthetic replacement.
- Cellar captures **18 and 19 are byte-identical**, including UI, despite being separately captured source/current isolated side-projection events. Both events, names and hashes remain present. Neither is substituted for the other. This supports only the pictured projection, not all-angle identity.
- The dirty marker in glassware captures 26/27 records the unsaved Hide of the four sparse east/west root groups, leaving the full north pair. No geometry, UV or texture edit was saved. The visibility state was discarded on close.
- The mistaken bar-twin context-menu state was discarded and the frozen scene reopened before accepted captures. A temporary cellar East preset was removed. Historical window IDs in the unchanged GUI notes are provenance, not current GUI state or instructions.

## Independent checks and portable replay

Replay evaluates the exact saved scenes; it never calls a scene builder:

- 240 declared input hashes, eight scene hashes and 44 embedded original PNG entries.
- 604 saved meshes, 1,416 direct source faces, 1,360 direct native faces and 11,104 ordered face vertices. The original signed bounds, hierarchy, rotations, rescale and placed transforms remain intact.
- Original maximum saved/input vertex error **7.11e-15 model pixels**, zero saved UV error. Non-adapted storage faces match source geometry/UV/pixels; the exact Luminous adaptation remains explicit.
- The original independent route and saved-scene audits run unchanged in a disposable copy. Reports must match saved JSON values, scalar types and array order exactly; object-key ordering alone is immaterial. No numeric rounding, tolerance change or saved-report rewrite is used.
- The archived current shared glassware checker reproduces its report; the archived shared storage checker's pure Node core-pose snapshot reproduces all 100 recorded pose cases. The route audit reuses that checker's existing algebraic functions for 800 point comparisons. These are bounded checks, not the broad runtime test suite.
- Seven renderer-body comparisons, 51 branch comparisons, held-rack identity and all four prior Luminous input identities are rechecked. Six already-materialized bottle resources match the public author lock and pinned source JSON/pixels. **26 optional archive-member comparisons remain not run.** The earlier denied lazy-fetch attempt remains recorded and was not retried.

The **five independent ZIPs**, each below 200,000 bytes, contain 277 nonoverlapping members: 267 unchanged preparation files, four author licences, five prior Luminous proof files and the public author-asset lock. Extract them together into one new directory. [Archive entries](archive-entries.json) gives each exact member's size, SHA-256 and Git blob SHA-1; [source snapshots](source-snapshot-index.json) identifies the 250 bounded inputs/proof/licence/lock records. [Artifact inventory](artifact-sha256.json) covers every direct package file except itself.

Historical workspace paths appear only in unchanged provenance. Replay does not access them, require Git history or download anything. Blob hashes authenticate supplied bytes against recorded identities; offline replay does not independently authenticate publishers or prove remote commit membership. The author JAR's hash is the recorded uploaded input identity, not a newly verified publisher checksum.

Requires **Python 3.10+**, Pillow, NumPy, SciPy and **Node.js with ES modules**. Verified with Python 3.12.14, Pillow 13.0.0, NumPy 2.3.5, SciPy 1.17.0 and Node.js 24.22.1. No installation is performed. Numerical libraries run single-threaded and audits run sequentially.

```sh
python docs/evidence/blockbench-occupied-furniture-20261109/validate_evidence.py --repository .
python docs/evidence/blockbench-occupied-furniture-20261109/test_verifier_boundaries.py
```

Omit `--repository` for self-contained replay. That option compares only the 131 relevant supplied-checkout files, not its entire Git identity. Optional `--work-dir /new/external/directory` retains extraction and disposable replay; `--report /new/external/receipt.json` writes a new informational receipt. Outputs must be new, nonoverlapping, outside every Git checkout and the package, with no symlink components. Existing outputs are never overwritten. Python `-O`, `-OO` and `PYTHONOPTIMIZE` are rejected. Traversal, malformed/absolute paths, symlinks, duplicate/missing/extra members, corrupt payloads, duplicate JSON keys and non-finite numeric payloads are rejected. Do not execute the archived historical builders or materializers.

## Attribution and unchanged scope

Original source/assets: **Kaleidoscope Official Production Team**, [KaleidoscopeMods/KaleidoscopeTavern](https://github.com/KaleidoscopeMods/KaleidoscopeTavern). [LICENSE-ASSETS](LICENSE-ASSETS) is [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/); [LICENSE-CODE](LICENSE-CODE) is BSD 3-Clause. Both branches' pinned notices are archived. The comparison scenes are adapted editor fixtures, not untouched author originals or author endorsement.

No complete author JAR, application executable, mappings, world, private author script or credential is distributed. The accepted tilted-rack **+6 first-person lift** remains unchanged; it is not reaccepted here. Prior Allium first-person clipping is unchanged and unresolved by this batch. Core representative bottles do not accept externalVisual addon helpers or every inventory item.

This documentation changes no runtime, version, baseline, release identity, CI classification, deployment or user computer. No Minecraft, BDS, LIVE, native-facing/material, controller-tick, gameplay, client or all-addon acceptance is claimed.
