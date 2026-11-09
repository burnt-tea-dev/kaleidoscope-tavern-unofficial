# Pressing-card size correction: portable evidence

This package was originally prepared on noncanonical 0.6.215 candidate `7409b71`. Final integration is now authorized against merged canonical 0.6.215 main `7fb1afc86439d67703df202d04923d4bcdc4466b` (tree `af1a39378862291b3c9c6fdd22d8d4d42bed12b7`), as recorded in the [base integration receipt](../pressing-card-integration-20261109/base-integration.json) and [pressing ingredient geometry notes](../../PRESSING-INGREDIENT-GEOMETRY.md). Paired 0.6.216 passed the corrected formal validation and is frozen in the [integration receipt](../pressing-card-integration-20261109/freeze.json). Clean-commit packaging and archive receipts are separate delivery outputs; this package establishes only the bounded visual evidence. Historical preparation identities and evidence remain unchanged.

## Result and limits

Only the eight centered card cubes change from 4×4×0.25 to **8×8×0.5**. Candidate SHA256: `d93249923210a8711fa038105816380407b9d70811c23313d4ddb56d68b83eea`. UVs, pivots, transforms, controllers, ordinary ice/materials and held views are unchanged. The rack's accepted **+6 first-person Y lift** is preserved; it does not mean six poses.

The original independent audit verifies 248 inputs, 36 meshes, 455 directed faces, 1,820 vertices, 320 poses and eight effective geometry/UV/matrix negative controls. The completed candidate GUI supplement contains seven accepted observations, two excluded diagnostics and one camera-only JPEG. The original N03 baseline contains eight scenes, 14 accepted observations, seven excluded diagnostics and one camera-only JPEG. All images are unmodified original JPEG bytes, with their original classifications, annotations and hashes.

These are bounded editor/data observations, **not gameplay or material acceptance**. Source generated alpha-edge extrusion (35 grape quads / 43 ice-grape frame-union quads) differs from the existing native two-broad-face approximation. The extrusion algorithm proof is **1.20.1 only**, not a generalized 1.21.1 algorithm claim. Frozen animated PNG agreement does not run the native clock.

Raw BB-reference tilted AABBs exceed the old visibility box both before and after correction. The 320 poses cover one location/seed `{x:3,y:64,z:-5}`, count 64, indices 0–63 and upright plus four cardinal states. This is not an all-seed/count bound. External engine-frame transforms, native culling, body clearance, world-facing and vertical alignment remain unproven. No speculative bound or placement change is included. Ordinary ice/material semantics, held views and full addon parity are not newly accepted.

## Contents and history

- `originals/candidate/`: byte-exact original preparation, all 280 preparation artifacts plus their inventory, 248 inputs, six scenes, candidate, independent audit/pose results, original scripts and the completed `gui-evidence-20261109/` supplement.
- `originals/n03/`: byte-exact N03 inputs, eight scenes, bytecode excerpts, independent audit, original scripts and completed `gui-review/`.
- `census/`: all **129** JSON definitions under canonical `runtime/RP/entity/` and `runtime/RP/attachables/`. Each byte sequence matches the corresponding Git blob in the original saved canonical runtime tree. Exactly eight reference the card owner; those eight also match the original input files. Completeness is relative to that saved canonical tree, not the later integration candidate and not inferred from eight fixtures alone.
- `replay/`: small offline wrapper and adapted independent audit copies. `adaptations.diff` records every change to the original validators. `origins.json` gives exact source-relative origins; `portable-manifest.json` records every packaged file's size, SHA256 and origin.

Original `gui_reviewed: false` / pending preparation text are intentionally retained. The completed GUI supplements supersede those pending flags **only for their bounded GUI review**. They do not rewrite historical audits, imply runtime application, or accept gameplay/materials. Original absolute paths are historical provenance, never required by replay. No full JAR, mappings, vendor bundle, private integration, world or credentials are packaged.

`verification-result.json` records the successful sequential replay; `replay-environment.json` records the installed Python/library versions used.

## Replay

With Python 3 and already-available NumPy, SciPy and Pillow, run from any directory:

    python -B /path/to/blockbench-pressing-card-20261109/replay/verify.py

Python optimization (`-O` / `-OO`, including `PYTHONOPTIMIZE`) is rejected before integrity checks can run with assertions disabled. Payload paths must be normalized relative paths: absolute paths, parent traversal and symlink files/directories are rejected before payload reads.

No installation, network, Git, GUI, Minecraft/BDS/LIVE, settings or process-control operation is performed. The replay runs sequentially and writes only disposable `.replay-*` working copies inside this package, then removes them. Do not run original prepare/build/finalize/GUI scripts: they are preserved historical evidence, not portable entry points. The replay needs no original workspace, repository metadata or source archives. It checks original inventories, candidate/scenes/raw JPEG integrity, annotation-to-scene identities, typed status flags, full bounded consumer census, both independent saved-mesh audits and exact regenerated typed audit/pose results. It also rejects omitted/extra/tampered census resources and Boolean/count type substitutions; the original eight geometry controls execute within the candidate audit.

Path adaptations are limited to `H=WORK` in the two replay validators and replacing the candidate's live sibling checkout / Git tree check / glob enumeration with `verify_census(PACKAGE)`. The original helper remains byte-exact in the disposable candidate copy, so its relative paths resolve there. The original builders are not rerun because generated UUIDs would change captured scene identity. The saved scenes are independently decoded and checked instead. SHA256 integrity establishes preservation, not photographic truth or gameplay equivalence.
