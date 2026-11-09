# Chalkboard narrow-edge repair: portable N05 evidence

This package preserves both original N05 preparation and its completed editor review, plus the separately reviewed narrow-edge candidate. [Current integration and source contract](../../CHALKBOARD-GEOMETRY.md) explains canonical ownership and the exact runtime repair. This evidence package does not itself publish or deploy a release.

## Scope and limits

The original seven scenes cover all 14 sandwich-board bodies, three Allium placed-angle controls and small/large chalkboards facing north/east. Its 29 original JPEGs include six explicitly excluded diagnostics. The candidate has 52 JPEGs: 36 model captures form 12 SOURCE/BEFORE/AFTER triplets, plus 16 camera, visibility and cleanup readbacks. Both large raking ends and both small end strips are compared in north/east; broad front/back controls retain identity and orientation.

Large raking views show the complete near end while intentionally cropping distant portions. They are not whole-board framing claims. The lower down-face V reversal is exact source-coordinate evidence only: nearest sampling traverses the same one-texel row, so no visual difference or GUI proof is claimed. The earlier white renderer also affected the Champagne control; failed diagnostic images and the recorded recovery remain intact.

No native engine culling, alpha-test lighting, text/font/alignment, state transitions, waterlogging, held-view, multiplayer, saved-world or LIVE acceptance is established here. All 14 sandwich bodies, the accepted +6 tilted-rack first-person lift, intentional justified/distributed and vertical text extensions, and unresolved Allium held clipping remain untouched. N06 text scoping and N07 painting UV findings are separate.

## Preserved payload

- 28 bounded ZIP parts contain 1,043 byte-exact files: 899 original N05 files (863 frozen preparation plus 36 GUI supplement files) and 144 candidate files (85 preparation plus 59 GUI files).
- `archive-entries.json` identifies each full ZIP and part by length and SHA256; its normalized `entries_file` links point to the compact per-archive member inventories. Each original member retains its exact length and SHA256. No screenshot was cropped, re-encoded, stitched or synthesized. All pending preparation flags and historical paths remain unchanged as provenance; completed GUI supplements supersede pending status only for their bounded editor scope.
- `controls/champagne.bbmodel` preserves the exact renderer-health scene. Only its one explicit historical relative alias is mapped to this file during replay. Other parent traversal is rejected.
- `replay/` contains path-adapted independent saved-scene validators, with every adaptation recorded in `adaptations.diff` and `adaptations.json`. Geometry/UV calculations, thresholds and acceptance predicates are unchanged. The original/candidate builders and preparation scripts are retained as history and must not be run as portable entrypoints.
- Source Java, textures and bounded reference excerpts are in the untouched payload. Source licenses are additionally retained under `licenses/forge/` and `licenses/neoforge/`. Tavern code uses BSD-3-Clause and assets CC BY-NC-SA 4.0; see their exact notices. Bounded Minecraft/Blockbench reference excerpts retain their provenance in the input manifests; no full JARs, mappings, executables, vendor bundles, worlds or credentials are included.

## Offline replay

With Python 3, NumPy and Pillow already installed:

    python -B /path/to/blockbench-chalkboard-20261109/validate_evidence.py
    python -B /path/to/blockbench-chalkboard-20261109/test_verifier_boundaries.py

The replay is sequential and sets numerical-library threads to one. It needs no original workspace, Git, network, GUI or engine. It validates the complete portable inventory, every ZIP part/member, all 81 raw JPEGs and scene identities, frozen snapshots and all twelve same-camera triplets, then reruns both independent saved-mesh audits against disposable temporary copies. Generated reports must match saved values and types exactly. The original 863-file frozen snapshot is reconstructed separately, excluding the later GUI supplement, for the candidate's historical integrity check.

Path traversal, symlinks, nonregular ZIP members, duplicate/missing/extra archive members, tampered hashes, duplicate JSON keys, nonfinite values (including overflow such as `1e999`), and Python optimization are rejected. All archive members are checked before extraction starts. Only temporary directories are written; results go to stdout. `artifact-sha256.json` excludes only itself, avoiding circular hashes. Save replay output outside this directory to preserve its complete inventory.

Replay verifies preserved evidence and independent source geometry, not photographic truth or additional visual/gameplay acceptance. It does not rerun the saved analytic camera sampler or original route-audit census. The canonical current-resource contract separately validates current slice routes, consumers, materials and source surfaces.
