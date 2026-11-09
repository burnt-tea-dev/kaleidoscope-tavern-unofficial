# Bottled drinks: source-paired editor review

All 25 bottle families and 97 placed-count states were inspected in the recorded
native Blockbench default-perspective, TOP and BOTTOM views. This folder retains
75 original JPEGs, three distinct image hashes per family. No new runtime defect
or review adapter error was confirmed in these bounded editor samples. Numerical
exactness, documented adaptations and actual engine acceptance remain distinct.

- [Scene and image index](scene-index.md): direct links to every recorded view.
- [Completed GUI record](gui-progress.json) and [capture dimensions/hashes](capture-index.csv).
- [Capture provenance and exclusions](capture-provenance.json).
- [Latest-base input verification](baseline-input-verification.json): 148 unchanged runtime inputs.
- [Reproduction result](verification.json) and [artifact hashes](artifact-sha256.json).

## Source and numerical coverage

Twenty-five exact self-contained scenes cover 97 placed-count states. Java models
sit at world Z=-12 and canonical models at Z=+12, with increasing count along X.
TOP shows Java in the upper row and canonical in the lower row. BOTTOM reverses
those rows. Default perspective does not have a universal left/right source row;
use the group identities and world coordinates. Count ranges differ by family.

These are actual placed BP block material/terrain routes, not held, drinking,
throwing, storage-rack or entity material acceptance. The saved source snapshot
is 0.6.212. All 148 runtime inputs referenced by the bottle manifest were freshly
hash-checked against fetched canonical main d42a39745f25082aa129f4d4bb823684e4174771,
version 0.6.213, runtime tree 38c5977dd6bfe14b1824734612e3c601e1e41028. All match.
This bounded equality does not mean the entire two runtimes are identical. This
docs-only change leaves runtime, version, baseline, release identity/history and
release request unchanged.

The audits cover 4,132 faces. Eighty-two states match exact imported geometry and
UVs; fifteen states in Glowflower, Luminous Bride, Madame Shexiang and Sunset Glow
use existing reviewed adaptations. The final adaptation audit checks all 960
faces of those states against exact local-axis offsets and full UV correspondence.
It is not a blanket 0.0625 tolerance. Luminous Bride retains forty previously
reviewed hidden shell-face crops against its opaque authored base. The earlier
raw diagnostic intentionally records those differences; it must be interpreted
with the later precise adaptation contract.

## Compact portable inputs

The seven archives contain the exact 25 scene files, bounded Java/native input
snapshots, receipts, numerical audits and licences. They contain no screenshots,
Blockbench application bundle or executable JAR. Every archive is under 200 KB.
Raw JPEGs are stored separately for direct viewing. The 673 archived entries and
all 25 scene files retain their exact original bytes.

For a clean reproducible check, with a suitable Python, Pillow, NumPy and SciPy
installation, run:

    python validate_evidence.py --repository ../../..

This verifies the archive/image hashes and complete family/view/count coverage,
extracts into a fresh temporary directory, reproduces the four saved numerical
reports as exact JSON values and scalar types, preserving array order, and
reproduces the unchanged surface analysis.
It records byte equality separately: the unchanged routing audit iterates
filesystem glob order, so `routing.json` object-key order can vary by extraction
filesystem while all bindings and values remain exactly equal. The
repository argument additionally rechecks the 148 current runtime inputs. Omit it
when reviewing an evidence-only download. Use `--work-dir /path/to/new-directory`
to keep the independent extraction and `--report /path/to/report.json` to save
the verification summary. Both destinations must be new and outside the evidence
folder and Git checkouts; existing files are never overwritten. The verifier
rejects absolute, parent-traversal, backslash and drive/colon paths in its
metadata, checks resolved paths remain inside their declared input roots, and
checks inventory completeness and duplicates. Run it on the pristine evidence
folder, before manually extracting extra files into that folder. No GUI or
Minecraft process is started. This does not rebuild scene files.

Small traversal, duplicate/omitted inventory and output-alias regressions:

    python test_verifier_boundaries.py

For individual audit commands, extract all archives with a suitable Python,
Pillow, NumPy and SciPy installation (recorded versions are in the restored
review/requirements.txt):

    for f in archives/*.zip; do unzip -q "$f" -d .; done
    python review/bottles/validate_scenes.py
    python review/bottles/check_routing.py
    python review/bottles/compare_faces.py
    python review/bottles/verify_face_adaptations.py

The scripts write under review/rerun/bottles. The earlier workspace clean
extraction reproduced all four saved JSON reports byte for byte; this historical
result is retained in `portable-validation.json`. A later independent `/tmp`
extraction exposed only `routing.json` object-key serialization order from its
unsorted filesystem glob. Complete JSON values, scalar types and array order
remained exactly equal. The
verifier reports both facts rather than changing the archived audit, its
calculations or its 673 archived entries. See `verification.json` and
`archive-entries.json`. The restored original numerical reports and README
preserve their earlier GUI-pending status; a later GUI record supplements them.
Scene, texture, UUID, hierarchy and transform bytes have not been regenerated.

## The four adapted bottle families

An apparent broad Madame Shexiang top-pattern difference was disproved by the
original JPEG pixels. Its count-one TOP and BOTTOM 60x60 regions are exactly equal
between source and native; the Sunset count-one BOTTOM 80x40 regions also match.
The pixel coordinates, original image hashes and decoded RGB hashes are in
surface-analysis.json. These are three specific regions, not whole-image or
cross-engine pixel equivalence.

For those four families, an independent first-visible analysis covers 15 states,
30 top/bottom views and 111,188 hit rays. The one small colour exception is Sunset
count three: two original bottle-body surfaces overlap over 0.058874503 square
model units, with tied source depths and different UV samples. Existing native
local-axis +/-0.0625 model-unit face separation chooses an original source
candidate colour. No new UV or runtime defect was established. Some depths in Glowflower/Luminous differ because of
existing separation; matching samples are not a claim of identical geometry.

With the archive inputs and the original screenshots present, run:

    python analyze_surfaces.py

It writes rerun/surface-analysis.json. The portable copy changes only path/input
and report-output plumbing; surface-portability.patch records the changes. A clean
run reproduced the original result exactly after path normalization. This is an
analytical geometry and original-JPEG check, not Minecraft renderer simulation.
The precise source of all JPEG/raster edge differences was not established.

## Capture integrity and excluded diagnostics

The 23 original 1364x1024 full-desktop JPEGs and 52 original 1188x848
`app.getScreenshot` JPEGs are preserved without cropping or re-encoding. Honey
Wine perspective and TOP are the valid earlier raw images; its BOTTOM is the
new distinct capture. Every family has exactly one accepted image per view,
three different image hashes, and an exact captured-scene hash.

The stale Honey Wine `bottom.invalid-duplicate-top` file and both white-viewport
diagnostic images are excluded from this folder and from the accepted 75. Their
hashes and reasons are recorded in `capture-provenance.json`. An unchanged
Champagne control reproduced the old white viewport; a fresh official Blockbench
instance restored the textured control. The root cause remains unknown. This is
not evidence for a browser/GPU cause, and no renderer flags, assets or security
settings were changed.

The completed source GUI record initially retained stale pending-count fields.
`gui-progress-completion-correction.json` records their correction and the source
record before/after hashes. The portable GUI record only changes relative paths;
all 75 image and scene hashes remain unchanged. Historical pending fields inside
the untouched archived numerical reports describe that earlier stage, not the
current 75-image review.

## Evidence boundaries

Editor views are limited to their visible surfaces, camera, static count state and
original texture frame. Perspective objects can occlude each other; TOP/BOTTOM
hide the opposite surfaces. These pictures do not establish all-facing or
all-surface coverage, actual controller selection, particle/animation timing,
liquid tint, shader/PBR/lighting, cutout/blend sorting, first-person FOV/arms,
gameplay, Minecraft client, BDS, LIVE or saved-world deployment acceptance.
Diagnostic failures and invalid captures must be excluded from accepted images.
No synthetic render, repainted texture or edited screenshot is acceptance evidence.

Forge author pin: c4ec1880bd44cf3139d3ba744ab30bb379cf1416. NeoForge pin:
a1afba34981a00e89d57130d3dc8f1e64f1820a2. Locked source JAR SHA256:
03f35e1e614953b22cd1f5e34345613f3a6a283bf1b1c99659b57d58970edeff.
The JAR was never executed and is not bundled; publisher checksum verification
remains false. Forge/native texture bytes match; NeoForge/JAR encoding can differ
while decoded RGBA matches.

Original code/art: Kaleidoscope Official Production Team / YSBB,
https://github.com/KaleidoscopeMods/KaleidoscopeTavern . Bedrock adaptation:
casama233 and contributors, https://github.com/casama233/kaleidoscope-tavern-unofficial .
Retain the restored BSD-3-Clause code and CC BY-NC-SA 4.0 artwork licences,
attribution, noncommercial and share-alike terms. No source texture was redrawn;
no author, Mojang or Microsoft endorsement is implied.
