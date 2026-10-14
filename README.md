## Current maintained baseline: 0.6.162

T162 replaces formatting-only shaker data with bounded ASCII tokens and hides only owned transport titles. Manual-only probes distinguish native mount, catalog and cache. T161 did not restore the reported UI; actual client recovery remains unverified. [Scope](docs/RELEASE-NOTES-0.6.162.md).

T155/G133 repair the missing shaker/eating UI receivers with permanent panels and independent channel caches; the obsolete shaker progress-parent gate is removed. [Repair scope](docs/RELEASE-NOTES-0.6.155.md). Client-rendered recovery remains unconfirmed.

At **2026-10-13 17:05:52 HKT**, T155/G133/W132/P34/Ribbits10037 completed canonical PR/CI, full-family static admission, one stopped-save first/restart and exact live readback: 42 packs, BDS1.26.52.3 RUNNING.

[Download v0.6.155-beta.1](https://github.com/casama233/kaleidoscope-tavern-unofficial/releases/tag/v0.6.155-beta.1). At 17:08:50 HKT, all three public archives were anonymously downloaded; their six owned packs and **9346 files** matched LIVE and the admitted receipt. [Current deployment and public comparison](family/PUBLIC-DOWNLOAD-LIVE-PERSISTENT-HUD-20261013.md).

Poststart has **165 warnings / 0 errors**, including **138 watchdog records (9 spikes, 129 slowdowns)**; Ribbits still records a **252 ms** startup spike. UI visibility, rapid reopen, Java cursor interpolation, client sound and complete parity remain unverified. `client=false`, `production_ready=false`, `pending_client_acceptance`.

## Historical repair scopes

The [T150/G130/W127 proof](family/PUBLIC-DOWNLOAD-LIVE-STARTUP-20261013.md) retains its original receipt, thresholds and observation scope.

The [T149/G130/W126 proof](family/PUBLIC-DOWNLOAD-LIVE-HUD-20261013.md) retains its original receipt, observation windows and native QA threshold limitations.

The [T148/G129/W125 comparison](family/PUBLIC-DOWNLOAD-LIVE-UI-20261012.md) retains its original 9339-file receipt and acceptance scope. Historical client recordings are not reassigned to T149/G130.

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
- The deployed development family is Tavern **0.6.155**, World Liquor **0.1.132** and Grilling **2.8.133**, with private integration **1.0.34**. The [family lock](family/upstream.lock.json) and [current baseline index](family/BASELINE-STATUS.md) record exact dependencies, deployed sources and verification.
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
