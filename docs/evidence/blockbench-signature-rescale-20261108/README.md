# Corrected Signature review, 2026-11-08

This corrects the Java side of the six Signature review fixtures in [the first Blockbench batch](../blockbench-20261108/README.md). It is documentation and review evidence only. Runtime 0.6.212, accepted held poses, release identity and deployment are unchanged from `e4cffb15010ba966f98dabf1c19cc2920bacd9bb`.

## What was wrong

The first review adapter copied Java element bounds and rotation but omitted `rotation.rescale`. Signature elements 13 and 14 are zero-thickness planes rotated -45 degrees around Y with `rescale: true`. Their authored 5-unit width must be multiplied by sqrt(2), about 7.071067812 units, around the authored pivot before rotation. The original review source side therefore was not a valid full geometric comparison. The earlier visible-pattern/geometry equivalence inference is withdrawn rather than retained as a pass.

The corrected review fixtures bake that perpendicular-axis scale into `from`/`to`, preserve the original pivot and rotation, and do not also set a rescale flag. They also preserve source `shade` values. This follows the official Blockbench 5.2.2 cube transform's reciprocal-cosine scale; no free-format support for a Java-only rescale flag is assumed.

The committed native Signature representation already bakes the approximately 7.0710678-unit width. Its liquid planes use the existing 0.125-unit thickness adaptation instead of Java's zero thickness. Neither is changed here. Fixing the comparison fixture is **not** counted as a gameplay or runtime repair.

## New actual GUI review

All six distinctly named corrected projects were newly opened in official desktop Blockbench 5.2.2, not read from the editor's cached old tabs. Each screenshot is an unmodified desktop capture. Java is on the **left**; committed runtime glass and the frame's actual ten RGB layers are on the **right**. The rim, stem, base, straw and frame-specific pattern remain assembled in these views. No additional definite assembly defect was confirmed. Different perspective depth is not a size measurement.

- [Frame 0](screenshots/signature-rescale-frame-0.jpg)
- [Frame 1](screenshots/signature-rescale-frame-1.jpg)
- [Frame 2](screenshots/signature-rescale-frame-2.jpg)
- [Frame 3](screenshots/signature-rescale-frame-3.jpg)
- [Frame 4](screenshots/signature-rescale-frame-4.jpg)
- [Frame 5](screenshots/signature-rescale-frame-5.jpg)

These remain the untinted `(255,255,255)` case. Editor-only solid colour swatches stand in for the static output of each RGB overlay. They do not execute Bedrock shaders, render controllers or an engine clock. This is not acceptance of arbitrary mixture colours, alpha sorting, PBR, held/FOV contexts or native-client behaviour. Java 1.21.1's `translucent` material versus main's `cutout` remains a separate unverified renderer concern.

## Reopen and audit

Extract [scenes.zip](scenes.zip) and open any of its six self-contained `.bbmodel` files in Blockbench 5.2.2 without plugins. Do not export these review-only projects over runtime assets. `scene-entry-sha256.json` identifies the exact files that were opened, not regenerated substitutes.

The authored model copy, `java-signature-cocktail.json`, is from [KaleidoscopeTavern](https://github.com/KaleidoscopeMods/KaleidoscopeTavern) main/1.20.1 commit `c4ec1880bd44cf3139d3ba744ab30bb379cf1416`, at `src/main/resources/assets/kaleidoscope_tavern/models/block/mixology/signature_cocktail.json`, under the upstream project's CC-BY-NC-SA-4.0 terms. `scene-records.json` hashes that model, the full source PNG strip, all six matching runtime frame PNGs and both committed runtime geometry inputs. Its `source/` prefix refers to this repository at the runtime commit above; `java-reference/` refers to the pinned Java source tree. Texture bytes are embedded in each project.

Run `python docs/evidence/blockbench-signature-rescale-20261108/check_review_correction.py` from this repository. The bounded fixture audit uses sqrt(2) independently of the builder's cosine expression. It verifies all 15 authored elements' corrected bounds, pivots, rotations, face UVs and shade flags for all six projects, and checks that native-side elements, groups and embedded texture bytes are unchanged from the original review. `fixture-audit.json` records the result. The 2,856 source-face texel and 7,680 RGB channel cases in the first batch remain valid for their native data contract, but do not certify this Java transform or engine rendering.

`artifact-sha256.json` hashes the evidence files. No user computer, LIVE server, saved world or Minecraft client was used. The earlier T194/W180 Allium viewport clipping finding is not resolved by this correction. No other addon or uninspected material/pose receives a pass by association.
