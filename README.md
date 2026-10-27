## Current maintained source

Current source identity and dependencies come from [baseline.json](baseline.json), and the reviewed family pairings come from [family/upstream.lock.json](family/upstream.lock.json). The source includes placed-bottle facing and potion tint, guide navigation, and bounded cabinet retries. The reviewed Orchard adapter may fill missing creative-group icons while preserving category, membership and ordering. Actual client acceptance remains pending.

**Public download:** [Tavern v0.6.185](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/releases/tag/v0.6.185), paired with **World Liquor 0.1.164** and optional **Grilling 2.8.157** in the reviewed family. Its author inputs are Cookery **1.6.4** and ChineseFood **1.0.6**, pinned in [the public family lock](family/upstream.lock.json). This download contains only the owned Tavern BP/RP; it does not include author packages or private integration, or assemble the full family on import.

**Publication scope (2026-10-27):** v0.6.185 was published from source `06c7c97cb2b0dbf0b7181660e1347b2f08d190a4`; all 21 uploaded assets were downloaded and matched the build. Complete-family native first-load/restart and saved-data checks passed for the tested T185/G157/W164 pairing on this date. These fixed-scope results do not certify human gameplay, rendering or client acceptance.

**Deployment records:** Actual server identities, private integration versions, deployment times and production receipts are kept in private maintenance records. Public versions and acceptance limits remain in the family status index.

**Remaining work:** complete the current gameplay/client acceptance, the owner's all-item Blockbench first-person/side-texture inspection, and the specific scenes in [PARITY-MATRIX](docs/PARITY-MATRIX.md) and [BUGS](docs/BUGS.md). T160 side faces, T167 cursor work and T169 progress expiry repairs are retained. `client=false`, `production_ready=false`, `pending_client_acceptance`.

**Historical scope:** the earlier T183/G155 source candidate and the T170/G149/W148 stable-channel publication retain their original versions and evidence. The latter followed the owner's source/editor/CI/package decision; this update does not add a new client gate to that publication or relabel either record as T185 acceptance. [Earlier README evidence](https://github.com/casama233/kaleidoscope-tavern-unofficial/blob/115942e55e9946cfd257fbcdc41c849f75b77509/README.md) and versioned release notes retain their original scope.

# Kaleidoscope Tavern (Unofficial)

A Bedrock port of [Kaleidoscope Tavern](https://github.com/KaleidoscopeMods/KaleidoscopeTavern), with standalone brewing, cocktails, storage, furniture and a shared seven-section Tavern guide. [繁體中文](README.zh-TW.md).

## Current source and requirements

- Current work, public downloads, repository-recorded deployment and acceptance are maintained in [one family status index](family/BASELINE-STATUS.md). [PR dispositions](docs/audit/PR-DISPOSITIONS.md) retain historical source decisions.
- [baseline.json](baseline.json) owns package identity and exact dependencies; [CHANGELOG.md](CHANGELOG.md) records changes.
- Bedrock 1.26.50 or newer; current load target BDS 1.26.52.3.
- Enable both Tavern BP and RP. Cookery is optional; the reviewed author version and World Liquor pairing are defined in [the family lock](family/upstream.lock.json).
- Use canonical source/releases, keep a world backup and remove duplicate older Tavern packs before an upgrade. Private integration is a separately identified addon; it is not a different Tavern runtime.
- For a family candidate with the reviewed integration Cookery RP repair, a clean resource-pack installation or targeted removal of the older Cookery RP is a prerequisite for client acceptance. Server replacement alone does not prove a client refresh; see [Cookery RP installation](family/COOKERY-RP-INSTALLATION.md).

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
