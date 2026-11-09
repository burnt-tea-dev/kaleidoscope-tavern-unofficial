# N04 scene and capture index

All linked JPEGs are unchanged raw capture files. Accepted images and diagnostics are separate in [the original GUI index](gui/gui-index.json). Exact scenes are ZIP members, not regenerated exports.

## circular-full

- Exact scene: `review/scenes/circular-full.bbmodel` in [evidence-03.zip](archives/evidence-03.zip).
- SHA-256: `ae64257ed3885936c1b92242c9104396397f4d9fdd5fa4e467385385139607ad`; Git blob: `a8fa87e36447c2fbf83f44bc7ef945dacc9da7d7`; bytes: 464806.
- Cases: `circular-full-0`.

- [01: True Isometric Right (30°), orthographic](gui/01-circular-true-isometric-right.jpg). All scene groups visible.
- [02: Top, orthographic](gui/02-circular-top.jpg). All scene groups visible.
- [03: North, orthographic](gui/03-circular-north.jpg). All scene groups visible.

## tilted-full

- Exact scene: `review/scenes/tilted-full.bbmodel` in [evidence-04.zip](archives/evidence-04.zip).
- SHA-256: `d9a5f942a3e97da5793018ae992287ffc6d4a91a119d24cbd99621c13a358174`; Git blob: `1999fa3483414510b44746722df4e99e23f745a6`; bytes: 279365.
- Cases: `tilted-full-0`.

- [04: True Isometric Right (30°), orthographic](gui/04-tilted-true-isometric-right.jpg). All scene groups visible.
- [05: Top, orthographic](gui/05-tilted-top.jpg). All scene groups visible.
- [06: East, orthographic, current isolated](gui/06-tilted-east-current-only.jpg). SOURCE world -X group hidden. CURRENT remains fully visible. Sidebars shown so group eyes identify the isolation.
- [07: East, orthographic, source isolated](gui/07-tilted-east-source-only.jpg). CURRENT world +X group hidden. SOURCE remains fully visible. Sidebars shown. Both temporary visibility states were discarded on close.

## bar-twin-cardinal

- Exact scene: `review/scenes/bar-twin-cardinal.bbmodel` in [evidence-03.zip](archives/evidence-03.zip).
- SHA-256: `1b4c5d4c4fc243721b94925671c35fbc131d5328922e5fd1ff6d29bfae7a8835`; Git blob: `8d88bb38a6fcb0d90566fceb26e28acfb5b9a7e5`; bytes: 442793.
- Cases: `bar-twin-cardinal-0`, `bar-twin-cardinal-1`.

- [08: True Isometric Left (30°), orthographic; all four groups](gui/08-bar-twin-true-isometric-left.jpg). All scene groups visible.
- [09: North, orthographic; case 0 only](gui/09-bar-twin-north-case0.jpg). Both case-1/east groups hidden; both case-0/north groups visible.
- [10: East, orthographic; source case 1 only](gui/10-bar-twin-east-source-case1.jpg). Only SOURCE world -X | bar-twin-cardinal-1 visible; the three other root groups hidden.
- [11: East, orthographic; current case 1 only](gui/11-bar-twin-east-current-case1.jpg). Only CURRENT world +X | bar-twin-cardinal-1 visible; the three other root groups hidden. All temporary visibility discarded.

## bar-single-irregular

- Exact scene: `review/scenes/bar-single-irregular.bbmodel` in [evidence-03.zip](archives/evidence-03.zip).
- SHA-256: `ec1b07ccc32ce0913eaede484226c9dbc72f00e4c6666bbb8f55b04bfb5a612a`; Git blob: `a37c0820d684b9d4ffa00e52c554e3bebae05587`; bytes: 200736.
- Cases: `bar-single-irregular-0`.

- [12: True Isometric Left (30°), orthographic](gui/12-bar-single-true-isometric-left.jpg). All scene groups visible.
- [13: North, orthographic](gui/13-bar-single-north.jpg). All scene groups visible.

## glass-bar-material

- Exact scene: `review/scenes/glass-bar-material.bbmodel` in [evidence-03.zip](archives/evidence-03.zip).
- SHA-256: `3c6c804b2d0d6ddf82cd697b423f0e3cfc408c68843aa7e8694b3a0c123728cc`; Git blob: `c5c4445d710f255512c929f924cef9e7bdfcb4e8`; bytes: 231841.
- Cases: `glass-bar-material-0`.

- [14: True Isometric Left (30°), orthographic](gui/14-glass-bar-true-isometric-left.jpg). All scene groups visible.
- [15: North, orthographic](gui/15-glass-bar-north.jpg). All scene groups visible.

## cellar-full

- Exact scene: `review/scenes/cellar-full.bbmodel` in [evidence-03.zip](archives/evidence-03.zip).
- SHA-256: `b4447cf0968597973a5aada650aa9d3ad4fa9b45ac34bb055e289a4fb32df6ed`; Git blob: `73ac1d649ba79421695d31ba9385a6b2fba74848`; bytes: 519018.
- Cases: `cellar-full-0`.

- [16: True Isometric Left (30°), orthographic](gui/16-cellar-true-isometric-left.jpg). All scene groups visible.
- [17: North, orthographic](gui/17-cellar-north.jpg). All scene groups visible.
- [18: East, orthographic; source bottles only](gui/18-cellar-east-source-bottles-only.jpg). SOURCE body element 0 through 6 hidden, all CURRENT hidden. Source bottle meshes remain. Group re-enabling was followed by re-hiding the seven body meshes before capture.
- [19: East, orthographic; current bottles only](gui/19-cellar-east-current-bottles-only.jpg). CURRENT body root cube 0 through 6 hidden, all SOURCE hidden. Current bottle meshes remain. Temporary visibility discarded.

## holder-occupied

- Exact scene: `review/scenes/holder-occupied.bbmodel` in [evidence-04.zip](archives/evidence-04.zip).
- SHA-256: `70a017a879916cac38988bbf14b416eaf623decd0ce082a0976fa49bd0089e48`; Git blob: `384ab67a988768b997c0befac9c9490a016f0936`; bytes: 1008941.
- Cases: `holder-occupied-0`, `holder-occupied-1`.

- [20: True Isometric Left (30°), orthographic, all groups](gui/20-holder-true-isometric-left.jpg). All scene groups visible.
- [21: Bottom, orthographic, all groups](gui/21-holder-bottom.jpg). All scene groups visible.
- [22: East, orthographic, source cases only](gui/22-holder-east-source-only.jpg). Both CURRENT root groups hidden; both SOURCE groups fully visible.
- [23: East, orthographic, current cases only](gui/23-holder-east-current-only.jpg). Both SOURCE root groups hidden; both CURRENT groups fully visible. Temporary visibility discarded.

## glassware-occupied

- Exact scene: `review/scenes/glassware-occupied.bbmodel` in [evidence-04.zip](archives/evidence-04.zip).
- SHA-256: `e92520bbe0933685faf2db8c9b390c7faa9c2c3175271fade66c84deab9ddbb7`; Git blob: `f578ecd3a9e62d1866290d41300d75749bbf9fd4`; bytes: 1467852.
- Cases: `glassware-0`, `glassware-1`, `glassware-2`.

- [24: True Isometric Left (30°), orthographic, all groups](gui/24-glassware-true-isometric-left.jpg). All scene groups visible.
- [25: Bottom, orthographic, all groups](gui/25-glassware-bottom-all-cases.jpg). All scene groups visible.
- [26: True Isometric Left (30°), orthographic, full north pair only](gui/26-glassware-full-pair-isometric.jpg). Both east and both west case groups hidden; SOURCE and CURRENT full north groups visible. Both root groups were explicitly selected (124 meshes) for centering, then Edit > Unselect All before capture.
- [27: Bottom, orthographic, full north pair only](gui/27-glassware-full-pair-bottom.jpg). Same full-north-only visibility as #26. Temporary visibility discarded on close.

## Excluded diagnostics

The 19 unchanged files under `gui/diagnostics/` are camera/selection/framing/cleanup receipts only. They do not increase the accepted capture or scene count.

## Byte-identical capture events

[18: source cellar East](gui/18-cellar-east-source-bottles-only.jpg) and [19: current cellar East](gui/19-cellar-east-current-bottles-only.jpg) were separately captured. Their complete JPEG byte streams happen to be identical at the isolated projection; both original event records are retained.
