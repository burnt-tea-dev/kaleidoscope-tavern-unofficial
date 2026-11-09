# Incense underside: visual evidence and contract follow-up

**All 16 incense type/state combinations have captured Blockbench source/current/candidate comparisons. The candidate restores the source underside pattern. Both contract gaps found during the first independent review subsequently passed focused follow-up checks. Minecraft-engine and final release acceptance remain separate.**

## Open the original images

- [Image captions, camera order and SHA256](review/image-index.md)
- [13 repaired-candidate raw JPEGs](review/candidate/evidence/)
- [11 original source/current baseline JPEGs](review/baseline/evidence/)
- [Machine-readable image index](review/image-index.json)

All 24 JPEGs are the original 1364×1024 bytes, individually inspected, never cropped, edited or re-encoded. All four candidate BOTTOM rows and all three columns fit within the viewport. BOTTOM shows **source left / current middle / candidate right**; default perspective reverses each triplet. Source and candidate underside patterns agree across all 16 states, while old current differs. Perspective sheets are overview evidence with small details and some foliage overlap. The extra Catnip closed tilted-bottom view is an unmeasured orbit, not a calibrated angle.

## Compact scene and source packages

- [Exact scenes ZIP](archives/incense-scenes.zip): six candidate and five baseline `.bbmodel` files, plus the original scene-only archives/index needed to preserve the existing verifier and hash inventory.
- [Portable source and audits ZIP](archives/portable-source-audits.zip): unchanged bounded input snapshots, source receipts, author contracts and offline verifier, with a documentation-only caption correction and updated hash manifests.
- [Per-archive and per-entry hashes](archive-entries.json)
- [All public artifact SHA256 values](ARTIFACT-SHA256SUMS)

Each ZIP is below 200,000 bytes. Neither contains a JPEG or the previous 1.7 MB full evidence ZIP. The raw images remain beside the archives for direct GitHub viewing. The packages do not contain a Blockbench application bundle, executable JAR or private investigation report.

## Restore and verify offline

From this directory, with the checked-out `review/` raw images and image index present:

```sh
unzip -q archives/incense-scenes.zip -d .
unzip -q archives/portable-source-audits.zip -d .
python review/verify_bundle.py
```

Both ZIPs restore paths under `review/`. Together with the adjacent images/index, they reconstruct the **107-file reviewed payload**. **102 files remain byte-identical to the original snapshot.** The README and two image indexes receive only the green-mark wording correction described below; `inventory.json` and `SHA256SUMS` are regenerated for those three document changes. All raw JPEGs, scenes, inputs, source audits and verifier bytes are unchanged. Use Python 3.12 and Pillow 13.0.0. No network, GUI, plugin, server or source checkout is needed. The verifier checks 36 inputs, 11 exact scenes, 28 embedded PNG entries, all 24 raw JPEGs and scene ZIP identities, then rebuilds six previews in a temporary copy and compares their contents after UUID rebasing. Captured scenes remain untouched. [Restoration verification](compact-validation.json) records the independently repeated clean-directory run.

**Caption correction:** A small green mark is visible near the current Catnip model in the tilted-bottom captures; origin was not diagnosed, and it is not used as defect evidence. The earlier wording incorrectly identified it as a viewport marker. This wording correction does not alter images or the underside colour comparison.

The historical `review/README.md` mentions an outer full-evidence ZIP and receipt. Those two distribution wrappers are intentionally not restored or needed; the complete reviewed payload, including the controlled documentation corrections, is restored.

## Captured identity versus later contract results

The images and exact scene bytes belong to captured geometry commit `df2559ef4ac9984d89d2dc4f01cfb60d1e7b7be7`. They are not relabeled as new captures. The later reviewed tip is `58b6bcb4c13976938e9a5bb940b74e6c5d291c26`, based on `95b5f18a216990a604d37e0f355f2a6dcde30fe7`. Its entire runtime tree remains `fbde705a2a6042201eba7b06f1c22192f05448a6`. The two geometry files and sixteen block/texture inputs were hash-checked against that tip, so the visual evidence is reused without modifying or regenerating it.

The first review found gaps in effective-open lifecycle override and root bone-visibility checks. The subsequent independent review reports both resolved: **18 real CLI negative launches reject for the intended semantic reason, the 18-test suite passes, and the pinned-source positive launch passes**. The tested code and relevant inputs were unchanged by the rebase to the reviewed tip. These are attributed independent review results; compact packaging reran payload verification, not the guard-test harness. [Follow-up status and exact identities](followup-contract-status.json) records the distinction. Original documents retain their historical pending wording.

**The repaired candidate is frozen as 0.6.213.** The local frozen source snapshot is `c3f83ca4677e65d85023257fc9a7d502750ad6dc`, with runtime tree `38c5977dd6bfe14b1824734612e3c601e1e41028`. The four version metadata files changed in addition to the two reviewed model faces; the captured model/texture bytes remain identical. Paired identities, append-only history, strict release checking and the real packager passed. The 5,913,211-byte candidate archive has SHA256 `8788b736b3806e0d3d2cc9e524dfe388a3cf551a64b7c938f1987ab88fd91b8f`. See [frozen validation](frozen-validation.json). The final PR adds this documentation and retains the later stool evidence without altering that runtime tree.

Canonical CI is a separate check on the published PR head. No BDS, Minecraft client, LIVE, gameplay, held-item behavior, deployment or saved-world acceptance is claimed. Automatic release publication remains disabled. Historical bundle fields describe their original capture/preparation snapshots, not the subsequent frozen candidate.

## Attribution

Original code/artwork: Kaleidoscope Official Production Team / YSBB, [Kaleidoscope Tavern](https://github.com/KaleidoscopeMods/KaleidoscopeTavern). Bedrock adaptation: casama233 and contributors, [unofficial port](https://github.com/casama233/kaleidoscope-tavern-unofficial). Code is BSD-3-Clause; artwork and derivatives are CC BY-NC-SA 4.0. Exact license files restore as `review/LICENSE-CODE` and `review/LICENSE-ASSETS`. The candidate restores the two authored underside faces; textures are unchanged. Preserve attribution, noncommercial and share-alike terms when sharing. No endorsement is implied.
