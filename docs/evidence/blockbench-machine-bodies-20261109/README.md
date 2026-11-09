# Tavern machine-body Blockbench evidence, 2026-11-09

**Completed bounded editor review: six scenes, ten source/current body-state pairs, 19 accepted original JPEGs.** The [scene and camera index](scene-index.md) links every capture and its exact scene/archive identity. Five additional clipped framing diagnostics are retained but explicitly excluded from acceptance. The original reviewer inspected all 19 accepted images in official cloud Blockbench 5.2.2; the parent also re-viewed barrel-open perspective and shaker PUT isometric-left. Packaging adds no new GUI or engine acceptance.

No new body geometry or UV discrepancy was observed in the chosen views. This is **body/reference-frame editor evidence**, not native Minecraft visual parity, gameplay, BDS, full addon acceptance, or completion of N03 contents.

## Reviewed scope

- Barrel closed/open: body, lid, bands, feet, cavity and hinge/zero-width strut. Four views cover the open barrel; the other scenes each have three.
- Pressing tubs: upright and tilted bodies. Ingredients and liquids are outside this batch.
- Taps: closed/open handles and spouts.
- Placed stepladder: the actual two-block bottom/top assembly, including the Y+16 join. The unused assembled entity is not presented as the placed route.
- Placed shaker: idle and frozen PUT keyframes at 0.0833 and 0.2083 seconds. Root-channel final-key clamping is explicit. These are not animation interpolation, timing, transition or held-view tests.

All fixtures are Free-format with explicitly **Front-sided** textures and inherited editor Shading enabled. They do not execute Java `entityCutoutNoCull`, Bedrock `entity_alphatest` or block material shaders. No dark or absent backface is classified as an engine defect. External entity yaw is untested: barrel north routes through `facingYaw(0)=180`; shaker helper rotation uses `facing*90`. Source/current offsets describe the comparison frame, not in-world placement acceptance.

Previously accepted held-shaker poses and tilted-rack **+6** remain unchanged and are not reaccepted here. The earlier Allium first-person clipping remains unresolved. N03 machine contents have no accepted captures in this package and remain outside its completion claim.

## Original and current identities

The exact original preparation and GUI files retain canonical **0.6.213**, main `d42a39745f25082aa129f4d4bb823684e4174771`, runtime tree `38c5977dd6bfe14b1824734612e3c601e1e41028`. Their original preparation README and structural report still say GUI pending/false. Those historical bytes are deliberately unchanged; the separate completed [GUI report](gui-review.json) and [review summary](gui-review-README.md) supersede that preparation status only.

All 94 original inputs and six scene hashes were verified. All **48 relevant canonical inputs** were independently rechecked unchanged against **0.6.214**, main `682a9dd01cc8d5ad26b714c0b279d04cbafeb205`, tree `dd322fc23aca7beb1f36650ba5dc6cb674c412b9`, runtime tree `870c0596cc2f0244d0e6ee17a0905d4b75734620`. See [current input verification](current-input-verification.json). The historical global runtime tree is provenance, not a false current identity. Passing `--repository` checks those exact 48 input bytes in the supplied checkout; it does not claim its entire tree is the documented base.

Forge `c4ec1880bd44cf3139d3ba744ab30bb379cf1416` and NeoForge `a1afba34981a00e89d57130d3dc8f1e64f1820a2` are pinned separately. All 23 bounded branch input comparisons are replayed. Relevant ModelPart declarations, PUT values and renderer pose calls match; renderer API signatures and the NeoForge barrel bounding box differ. Full renderer equivalence is not asserted.

## Independent saved-scene checks

Replay evaluates the exact saved `.bbmodel` files, never rebuilt fixtures:

- **452 paired nonzero faces**, zero UV, texture-pixel or carried shade-flag mismatches.
- **170 cubes / 1,360 vertices** through complete nested group matrices.
- **680 original native vertices** and 496 native UV face records independently decoded.
- **336 Java ModelPart vertices**, 208 original ModelPart polygon/UV faces, and **344 Java JSON vertices** independently evaluated.
- Maximum source/current coordinate difference **8.85e-9 model pixels**, from the documented stored barrel radian-to-degree rounding. Zero-area faces are excluded, not silently thickened. The original audit tolerances and calculations are unchanged.
- Twelve embedded original PNG entries, all exact byte matches to declared input textures. Eleven actual bounded author-archive asset blobs are checked against the lock: six JSON models semantically equal despite byte differences, five textures pixel-equal.

## Portable package

- `images/`: 19 accepted and five excluded original **1188×848 JPEG byte streams**, without cropping, repainting, resizing or re-encoding.
- `archives/`: **two standard ZIPs**, each below 200,000 bytes (largest 178,126), with **142 nonoverlapping members**: 123 exact original review files, four prior held-source blobs, eleven locked-archive asset blobs and four pinned author licence files. Extract together into one new external directory. Six exact self-contained scenes are included.
- [Archive entries](archive-entries.json): complete member byte lengths, SHA-256, Git blob SHA-1 and origin identifiers. [Source snapshot index](source-snapshot-index.json): 113 bounded source/asset/licence identities. Blob hashing authenticates content against these recorded identities; offline replay cannot independently authenticate the publisher or re-prove remote commit membership.
- `audits/`: portable copies of the original independent scene validator and provenance checker. [The exact diff](audit-portability.patch) changes only declared input paths, bounded Git reads and output destinations; original calculation and acceptance predicates are unchanged. The final manifest write is suppressed, so replay never changes a saved scene or report. The original scripts are archived unchanged for provenance; **do not run their historical builders**.
- [Artifact inventory](artifact-sha256.json): every direct file's bytes, SHA-256 and Git blob identity, excluding only this self-referential inventory. Generated verification receipts are external, informational and never a trusted oracle.

The original scripts' absolute workspace paths are historical identifiers, not access instructions. Replay relocates only the declared review root in memory, loads exact bounded archived Git blobs, and compares all six regenerated reports for **exact JSON values, scalar types and array order**. Only object-key ordering is immaterial. It uses no rounding, numeric normalization, widened tolerance or silent saved-report rewrite.

## Reproduce

Requires Python 3.10+ with Pillow, NumPy and SciPy. Verified with Python 3.12.14, Pillow 13.0.0, NumPy 2.3.5 and SciPy 1.17.0. No Git history, network, original workspace, Blockbench, Minecraft or BDS is required. The verifier forces numerical libraries to one thread and runs the audits sequentially in one Python process.

```sh
python docs/evidence/blockbench-machine-bodies-20261109/validate_evidence.py --repository .
python docs/evidence/blockbench-machine-bodies-20261109/test_verifier_boundaries.py
```

Omit `--repository` for self-contained replay. Optional `--work-dir /new/external/directory` retains extraction and generated reports; `--report /new/external/receipt.json` writes an exclusive new receipt. Outputs must be new, nonoverlapping, outside evidence and every Git checkout, without symlink components. Existing files are never overwritten. Python `-O`, `-OO` and `PYTHONOPTIMIZE` are rejected. The verifier rejects traversal/absolute/malformed paths, symlinks, duplicate/missing/extra ZIP or inventory entries, changed payloads, and non-finite/duplicate-key JSON. Boundary tests cover these negative cases and exact comparison semantics.

## Attribution and limits

Original assets/source: **Kaleidoscope Official Production Team**, [KaleidoscopeMods/KaleidoscopeTavern](https://github.com/KaleidoscopeMods/KaleidoscopeTavern). See [LICENSE-ASSETS](LICENSE-ASSETS), [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/), and [LICENSE-CODE](LICENSE-CODE), BSD 3-Clause. Both pinned branches' original notices are archived. This is an unofficial port review, not author endorsement; comparison scenes adapt the geometry for editor inspection and are not author originals.

The locked `kaleidoscopetavern-1.2.0-neoforge+mc1.21.1.jar` is identified by the recorded user-upload hash, not a verified publisher checksum. Only eleven applicable asset blobs are included. No whole JAR, application bundle, mappings, private script, world or credential is distributed or executed.

This documentation changes no runtime, data, version, baseline, CI classification, accepted held/rack pose, GUI setting, deployment or user computer. Native culling/alpha/material/lighting, world yaw, controllers, collision, interpolation, timing, held views, N03 contents and all other addons remain outside this evidence. Repository source regressions are not native gameplay sessions.
