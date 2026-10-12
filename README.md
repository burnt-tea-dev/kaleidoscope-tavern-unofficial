## Current maintained baseline: 0.6.149

T149 prepares guide and extension registration over bounded work slices and sends shaker graphics through the observed optional title router, keeping shared Actionbars available to other addons. Recipes, item settlement, guide content and original graphical timing remain unchanged. This candidate awaits canonical CI and full-family saved-world/native admission; real-client rendering is still pending. See [T149 repair scope](docs/RELEASE-NOTES-0.6.149.md).

The complete T148/G129/W125/private1.0.33 family was deployed to luosen on **2026-10-12 at 21:21:24 HKT**, with 42 packs and BDS1.26.52.3 RUNNING. Static checks, the fresh stopped-save first start/restart, admission and full file/order readback passed. Poststart recorded 313 warnings and zero errors; slow-script warnings remain. Human client acceptance is pending.

[Download v0.6.148-beta.1](https://github.com/casama233/kaleidoscope-tavern-unofficial/releases/tag/v0.6.148-beta.1) or [the complete Tavern BP/RP archive](https://github.com/casama233/kaleidoscope-tavern-unofficial/releases/download/v0.6.148-beta.1/Kaleidoscope_Tavern_Unofficial_0.6.148_baseline1.mcaddon). The [new public-download/LIVE comparison](family/PUBLIC-DOWNLOAD-LIVE-UI-20261012.md) confirms all 9339 files in the three published addons' six BP/RP packs match the installed family and admission receipt. Private cuisine and reviewed third-party host extensions have separate sources.

Private1.0.33 adds only the reviewed Cookery1.6.0 recipe-cache repair, retaining the renderer32 component and ChineseFood1.0.10432. Production-module Node comparisons reduced pot-cache rebuilds from 75 to 7 across six registration batches; they do not establish an improvement in BDS watchdog or client stalls. Rapid restart blank bars, simultaneous Actionbar writers and third-party whole-HUD replacements still need the [full-stack client regression](docs/HUD-COMPAT-CLIENT-HANDOFF-20261012.md). `client=false`, `production_ready=false`, `pending_client_acceptance`.

## Historical repair scopes

T147's bounded HUD200 repair is merged in [PR331](https://github.com/casama233/kaleidoscope-tavern-unofficial/pull/331). The shaker progress hold changes from 100 to 200 ms; one-tick cursor motion stays 50 ms. Its [original publication comparison](family/PUBLIC-DOWNLOAD-LIVE-20261012.md) and [publication preparation](docs/PUBLICATION-T147-G128-W124.md) retain their point-in-time scope and public Cookery API assembly instructions.

Limited HUD200 diagnostic recordings support improved continuity, with stationary end holds retained. They do not establish physical input/packet timing or complete acceptance of the newly versioned formal family. The [original diagnostic scope](docs/RELEASE-NOTES-0.6.147.md) stays unchanged.

T146 combines the native board inverse, restricted-safe ingredient snapshots and bounded 100 ms shaker HUD hold on canonical T145. T146/W123/G125 was deployed on 2026-10-11 after complete-family admission and a fresh saved-world first start and restart. Human client acceptance remains pending. Five earlier standalone HUD recordings retain their stated scope; while-held slot switching is inconclusive and same-second rapid restart remains untested. See [scope and validation](docs/RELEASE-NOTES-0.6.146.md).

The actual deployed family and its source, CI, native and saved-world evidence are indexed in [family/BASELINE-STATUS.md](family/BASELINE-STATUS.md). Human client acceptance remains pending; the release notes preserve their original draft-review scope and point-in-time status.

T144 addresses the client's four duplicate board input boxes and reported board-text displacement (deployed 2026-10-10); rendered input, focus and placement still require human confirmation. T145 identifies the held shaker from the live hand when a native use event copy omits its dynamic-property value. See [the repair scope](docs/RELEASE-NOTES-0.6.145.md); real-client shaking still requires human confirmation.

# Kaleidoscope Tavern (Unofficial)

A Bedrock port of [Kaleidoscope Tavern](https://github.com/KaleidoscopeMods/KaleidoscopeTavern), with standalone brewing, cocktails, storage, furniture and a shared seven-section Tavern guide. [繁體中文](README.zh-TW.md).

## Current source and requirements

- [T140 guide revision](docs/RELEASE-NOTES-0.6.140.md) retains all three languages and preparation details on demand, adds four reviewed AMW pages and shares the view through the optional Cookery entrance. T141 preserves this published guide and T139's native clock/reload, machine ingredient, Mob selection and immersion repairs.
- [T132 repairs](docs/RELEASE-NOTES-0.6.132.md) share instant splash dispatch and source immunity, repair shaker input echoes and storage rollback, preserve Vision's living recipients and query order, and add scoped guide flipbooks, board escaping and shorter HUD expiry. [Current PR disposition](docs/audit/PR-DISPOSITIONS.md) is the single backlog index; native/client/live acceptance remains separate.
- The deployed development family is Tavern **0.6.148**, World Liquor **0.1.125** and Grilling **2.8.129**, with private integration **1.0.33**. The [family lock](family/upstream.lock.json) and [current baseline index](family/BASELINE-STATUS.md) record exact dependencies, deployed sources and verification.
- [baseline.json](baseline.json) owns package identity and exact dependencies; [CHANGELOG.md](CHANGELOG.md) records changes.
- Bedrock 1.26.50 or newer; current load target BDS 1.26.52.3.
- Enable both Tavern BP and RP. Cookery is optional; the reviewed family target is author Cookery1.6.0. World Liquor uses its exact paired Tavern version.
- Use canonical source/releases, keep a world backup and remove duplicate older Tavern packs before an upgrade. Private integration is a separately identified addon; it is not a different Tavern runtime.

## Build

Python3.12+, Node22+ and Pillow11.3.0 are required for the existing validation tools.

```sh
python3 tools/build_release.py
```

The current builder directly packages committed runtime/BP and runtime/RP into dist/. It needs no historical artifact, private server directory or gameplay patch. Source generators are explicit authoring tools; they are not normal packaging steps.

## Verification

Use existing targeted checks for the behavior being changed; canonical CI owns the full required suite once. [TEST-AUDIT.md](docs/audit/TEST-AUDIT.md) distinguishes original Java oracles, production conservation/rollback, real BDS persistence and build prerequisites. [PARITY-MATRIX.md](docs/PARITY-MATRIX.md) records actual scope; [BUGS.md](docs/BUGS.md) gives reproduction scenes.

Package/source integrity and BDS loading do not certify client visuals, sound or the entire player flow. Current human acceptance remains pending. Owner rules and deployment authorization are unchanged; [proposed revisions](docs/audit/RULE-PROPOSAL.md) require approval.

## Known limits

Pure additive first-person camera roll remains unimplemented; the yaw adapter is explicit opt-in. Native machine counts and supported stackable ingredient metadata, source RGB texels, board outlines and effect appearance ownership have reviewed repairs. Colored board outlines still differ at the per-viewer feet-versus-camera 16-block boundary and first-person spyglass condition. Arbitrary NBT and three decorated nonstackable shaker inputs, wall outlines, the multiline board editor and dropped-shaker display contexts remain incomplete. Native reach, mob-target clearing, step-height, XP pickup and some instant-effect delivery semantics remain incomplete. All new hand, item-render, material and input paths need paired client review. See the release notes and matrix for source and engine boundaries.

## Licensing and history

Original Tavern code is BSD-3-Clause; original/derived art is CC BY-NC-SA4.0. Fonts and other assets retain their own notices. See [CREDITS.md](CREDITS.md), LICENSE-CODE and LICENSE-ASSETS. Historical install/download instructions are preserved in [the archive](docs/archive/pre-reorganization-README.md), not current requirements. Open the root config.json for bridge authoring; see [BRIDGE-WORKFLOW.md](docs/BRIDGE-WORKFLOW.md).
