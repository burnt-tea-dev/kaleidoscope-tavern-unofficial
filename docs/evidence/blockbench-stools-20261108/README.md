# Bar stool source-paired editor review, 2026-11-08

All sixteen colours and four body-turn samples were inspected in official native
Blockbench 5.2.2. Five exact scenes and ten original JPEG screenshots are retained.
No new visible silhouette or texture mismatch was found in these recorded views.
This is documentation only: canonical 0.6.212 runtime, release identity, accepted
held transforms and saved worlds are unchanged.

## Coverage and camera order

- Colours 1: black, blue, brown, cyan.
- Colours 2: gray, green, light blue, light gray.
- Colours 3: lime, magenta, orange, pink.
- Colours 4: purple, red, white, yellow.
- Body poses: blue stool at 0, 45, 90 and 180 degrees. The base stays fixed.

Every scene has a `-perspective.jpg` and `-top.jpg` screenshot beside this file.
Default perspective shows **native left / source right** within a pair. TOP shows
**source left / native right**. Camera direction changes screen order; world
coordinates and group identities are authoritative. All four pairs fit within
each recorded viewport. Some rear bases are naturally occluded in perspective,
and TOP hides bases beneath the bodies. These views do not establish every-surface
coverage, rider animation, interpolation, interaction timing or Minecraft-engine
lighting, culling, shader or transparency parity. No Minecraft client, BDS, LIVE
server or deployment was used.

## Sources and exact reproduction inputs

The comparison uses the actual placed `runtime_seat_colour` entity route, not the
static item/block display. The Java body model and renderer are pinned upstream
1.21 source; base models, colour parents and 32 textures were extracted from the
hash-checked Java JAR. The original 64x32 body / 32x32 base textures match the native
atlas crops. The scene audit compares 280 boxes in 20 pairs, including ordered UVs,
active pivots and hierarchy transforms. This does not establish unsampled runtime
animation behaviour. Source pins, paths and extraction hashes are in `manifest.json`
and `extraction.json` and the portable bundle.

- [Ten-image review record](gui-review.json), with observations and exact hashes.
- [Exact five scenes](scenes.zip), with [per-entry hashes](scene-entry-sha256.json).
- [Portable review bundle](review-bundle.zip): those scenes, bounded source/native inputs, source receipts, licences and the independent audit.
- [Static validation](validation.json), recorded before the GUI review.
- [Artifact hashes](artifact-sha256.json).

The original manifests and numerical reports retain their earlier `gui_reviewed:
false` fields. The subsequent `gui-review.json` is the completed, explicitly bounded
GUI record. Its `stools/` paths refer to the bundle layout; raw JPEGs here have the
same basenames and unchanged bytes. Its historical bottle-pending note is not a
claim about subsequent bottle work; bottle acceptance is outside this folder.

Raw JPEGs are published beside this file rather than duplicated in the portable
bundle. Its historical image index refers to those external unchanged bytes.

Extract `review-bundle.zip` into a new directory. With an existing suitable Python
and Pillow installation, run `python stools/validate_scenes.py` there. It writes
`rerun/stools/validation.json` and reproduces the saved five-row static report.
Open a `stools/scenes/*.bbmodel` in Blockbench for independent visual inspection.
No application plugin or external texture load is required. The ZIP contains the
exact captured scene bytes, including UUIDs, rather than regenerated approximations.

Original code/art: Kaleidoscope Official Production Team / YSBB,
https://github.com/KaleidoscopeMods/KaleidoscopeTavern . Bedrock adaptation:
casama233 and port contributors, https://github.com/casama233/kaleidoscope-tavern-unofficial .
Code is BSD-3-Clause and art is CC BY-NC-SA 4.0; see retained licences. No source
texture was redrawn. No author, Mojang or Microsoft endorsement is implied.
