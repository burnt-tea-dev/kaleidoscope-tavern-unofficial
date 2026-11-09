# N04 occupied furniture: actual Blockbench GUI evidence

**Completed: 27 accepted raw JPEG screenshots, 8 scenes, 12 occupied cases. No new runtime defect was established.**

The screenshots are original 1188×848 Blockbench window JPEG bytes, individually captured through supported CUA UI actions. No crop, re-encoding, stitching, synthetic render, screenshot-model export or image editing was used. Exploratory/camera/identity receipts are separate in `diagnostics/`.

## Results

- Circular: six occupied slots, yaw/extrema and neck/base alignment are consistent in the pictured reconstruction.
- Tilted: three slots and source/current isolated East profiles preserve pitch and seating. This does not retest the +6 first-person lift.
- Bar cabinets: north/east twin order, broad Brandy single layout, and glass-front overlap are pictured. Opaque roof views were replaced by useful cavity/profile views.
- Cellar: all nine slots and three-by-three spacing are visible. Isolated body-hidden East profiles expose horizontal pitch. Source/current profile captures are independently taken but byte-identical at that projection.
- Holder: Wine and Luminous contacts, pitched side profiles, and underside occlusion are pictured.
- Glassware: full four-cup silhouette, hanging contacts and underside texture features are pictured. Sparse east/west cup counts and their deliberately different reference frames are recorded, not treated as proof of a runtime-facing bug.

## Identity and camera rules

SOURCE is model/world-contract translation X=-24; CURRENT is X=+24. Cases progress along Z by 34 units. The original named root groups, manifest case IDs and screenshot compass determine identity. Screen side is camera-dependent:

- Top and Bottom: source screen-left, current screen-right.
- North: current screen-left, source screen-right.
- True Isometric Right (30°): current upper-left, source lower-right for each same-case pair.
- True Isometric Left (30°): current lower-left, source upper-right for each same-case pair.
- East: the source/current X translations collapse in projection; they were isolated for accepted paired side captures. Higher Z cases appear screen-left.

All accepted captures have selection cleared. The index names every actual UI view and exact scene hash, states all visibility isolation, and includes numeric camera values only where observed/set through Save Angle. Numeric values displayed by Blockbench can be rounded; omitted values were not invented. All selected textures remained Front.

## Capture index

| # | File | Scene | Camera |
|---|---|---|---|
| 01 | [01-circular-true-isometric-right.jpg](01-circular-true-isometric-right.jpg) | circular-full | True Isometric Right (30°), orthographic |
| 02 | [02-circular-top.jpg](02-circular-top.jpg) | circular-full | Top, orthographic |
| 03 | [03-circular-north.jpg](03-circular-north.jpg) | circular-full | North, orthographic |
| 04 | [04-tilted-true-isometric-right.jpg](04-tilted-true-isometric-right.jpg) | tilted-full | True Isometric Right (30°), orthographic |
| 05 | [05-tilted-top.jpg](05-tilted-top.jpg) | tilted-full | Top, orthographic |
| 06 | [06-tilted-east-current-only.jpg](06-tilted-east-current-only.jpg) | tilted-full | East, orthographic, current isolated |
| 07 | [07-tilted-east-source-only.jpg](07-tilted-east-source-only.jpg) | tilted-full | East, orthographic, source isolated |
| 08 | [08-bar-twin-true-isometric-left.jpg](08-bar-twin-true-isometric-left.jpg) | bar-twin-cardinal | True Isometric Left (30°), orthographic; all four groups |
| 09 | [09-bar-twin-north-case0.jpg](09-bar-twin-north-case0.jpg) | bar-twin-cardinal | North, orthographic; case 0 only |
| 10 | [10-bar-twin-east-source-case1.jpg](10-bar-twin-east-source-case1.jpg) | bar-twin-cardinal | East, orthographic; source case 1 only |
| 11 | [11-bar-twin-east-current-case1.jpg](11-bar-twin-east-current-case1.jpg) | bar-twin-cardinal | East, orthographic; current case 1 only |
| 12 | [12-bar-single-true-isometric-left.jpg](12-bar-single-true-isometric-left.jpg) | bar-single-irregular | True Isometric Left (30°), orthographic |
| 13 | [13-bar-single-north.jpg](13-bar-single-north.jpg) | bar-single-irregular | North, orthographic |
| 14 | [14-glass-bar-true-isometric-left.jpg](14-glass-bar-true-isometric-left.jpg) | glass-bar-material | True Isometric Left (30°), orthographic |
| 15 | [15-glass-bar-north.jpg](15-glass-bar-north.jpg) | glass-bar-material | North, orthographic |
| 16 | [16-cellar-true-isometric-left.jpg](16-cellar-true-isometric-left.jpg) | cellar-full | True Isometric Left (30°), orthographic |
| 17 | [17-cellar-north.jpg](17-cellar-north.jpg) | cellar-full | North, orthographic |
| 18 | [18-cellar-east-source-bottles-only.jpg](18-cellar-east-source-bottles-only.jpg) | cellar-full | East, orthographic; source bottles only |
| 19 | [19-cellar-east-current-bottles-only.jpg](19-cellar-east-current-bottles-only.jpg) | cellar-full | East, orthographic; current bottles only |
| 20 | [20-holder-true-isometric-left.jpg](20-holder-true-isometric-left.jpg) | holder-occupied | True Isometric Left (30°), orthographic, all groups |
| 21 | [21-holder-bottom.jpg](21-holder-bottom.jpg) | holder-occupied | Bottom, orthographic, all groups |
| 22 | [22-holder-east-source-only.jpg](22-holder-east-source-only.jpg) | holder-occupied | East, orthographic, source cases only |
| 23 | [23-holder-east-current-only.jpg](23-holder-east-current-only.jpg) | holder-occupied | East, orthographic, current cases only |
| 24 | [24-glassware-true-isometric-left.jpg](24-glassware-true-isometric-left.jpg) | glassware-occupied | True Isometric Left (30°), orthographic, all groups |
| 25 | [25-glassware-bottom-all-cases.jpg](25-glassware-bottom-all-cases.jpg) | glassware-occupied | Bottom, orthographic, all groups |
| 26 | [26-glassware-full-pair-isometric.jpg](26-glassware-full-pair-isometric.jpg) | glassware-occupied | True Isometric Left (30°), orthographic, full north pair only |
| 27 | [27-glassware-full-pair-bottom.jpg](27-glassware-full-pair-bottom.jpg) | glassware-occupied | Bottom, orthographic, full north pair only |

The full per-image observations, SHA-256, byte length, dimensions, scene identity, case metadata and isolation are in `gui-index.json`. Source/case frame limits remain those in the preparation README and audits.

## Integrity and cleanup

- Preflight and postflight: all 266 frozen artifacts unchanged, zero mismatches. This includes every frozen input and all eight scene files.
- The 131 selected current files in the provided local read-only worktree still equal their frozen snapshot hashes. No broader/latest remote canonical claim is made.
- No runtime/source/scene file overwritten, no export, no publication, no plugin installation, no security/material setting change, no Minecraft/BDS/LIVE/deployment.
- Temporary group/body visibility changes were never saved and were discarded when closing each own review tab. In screenshots 26 and 27, the dirty dot specifically records hiding the four sparse east/west root groups to show only the full north pair. Camera/centering work was review-only; no geometry/UV/texture change was saved. The whole temporary state was discarded.
- One temporary numeric East preset was created solely to center cellar profiles, then deleted. Its absence was verified in the angle menu.
- An exploratory bar-twin context-menu mis-target left unintended unsaved editor state. It was discarded, then the frozen scene was reopened before accepted bar-twin captures. The diagnostic receipt is retained.
- GUI handoff: only the original healthy Champagne tab remains in Blockbench window 29360132; no modal. All five Terminal windows, including 41949001, were untouched. Control was explicitly released to the parent.

## Boundaries

These are actual GUI observations of prepared algebraic placed-layout reconstructions. Stored-bottle source Java PoseStack is compared against the documented shipped helper/scale/root-pitch contract, not literal BB Euler signs interpreted as an engine. Glassware Java-world and literal BB-decoded quadrants intentionally differ; the separate 64-mask audit relies on a historical client convention, not a new client test.

Native entity material sorting/culling/alpha/AO/dimming/shaders, Forge/Neo runtime rendering and held display transforms are not executed. Luminous keeps the exact accepted #611 covered strip/cap adaptation; preview transparency does not establish a new bug. Forge cutout versus Neo translucent empty-cup declarations and occupied-renderer cutout scope remain the documented source distinction.

Six already-local bottle author members were verified during preparation; 26 optional archive-member checks remain not run. The denied optional Git blob route and author JAR were not retried. This occupied core batch does not imply all addon ports or externalVisual helper routes are accepted.
