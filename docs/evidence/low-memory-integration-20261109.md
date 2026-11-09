# T220 integrated low-memory repairs

## Exact inputs and scope

This candidate integrates [#622](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/pull/622), head `4d5728bb94d0cf5e6cf07f7b525c5ed4ab343184` (T218), and [#624](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/pull/624), head `809cc96a31b7a4ba4df7c77e0d23c54a84bdba09` (T219), over main `99ef7d028db20c055c80480c287957fd4cf1a924`.

The two original candidates were frozen independently from T217. Their identities are not reused for the combination. T220 retains all 137 main history entries plus the exact original T218 and T219 entries, then appends a new paired identity. Original source branches remain ancestors. No historical record is rewritten. UUIDs, external dependencies and Script APIs remain unchanged. `publication_request=false`, client/family/production acceptance remain false or pending.

Open #577 (High Heels), #623 (text verifier isolation) and #626 (manual suite upkeep) were inspected for coordination. Their independent work is not overwritten or represented as part of these runtime repairs. Main's #621/#625 family tooling is retained byte-for-byte.

The Java upstream heads were read again during this review: Forge/main `c4ec1880bd44cf3139d3ba744ab30bb379cf1416`, NeoForge/1.21.1 `a1afba34981a00e89d57130d3dc8f1e64f1820a2`, and NeoForge/26.1.2 `9b8f165a4641e738e694641dd81240a0206573e1`. They match the existing source evidence. This does not establish full parity across loaders.

## Coupled verification

- Six current interaction suites: **385/385 passed**, zero skips. This includes the actual furniture adapter and natural-board destruction, rollback, player recovery, pickup, shaker retention, native machine ingredient and potion display adapters with deterministic API doubles.
- Efficiency and board-rendering suites: **66/66 passed**, zero skips. Existing four-face, sixteen-heading, layout/alignment, outline and range-gate cases remain effective.
- Font source/negative-control suite: **9/9 passed**. Two complete regenerations and a metrics-only regeneration reproduce committed bytes. Missing/returned atlases, altered RGBA, page/cell selectors, UVs, tint, outline, metrics and source drift are rejected.
- Independent immutable-main comparison: all **256 logical texture pages** resolve to exactly the same PNG bytes. The entity is otherwise identical and the complete metrics module is unchanged. There are 224 physical atlas files instead of 256. The removed files total 32,160 bytes; nominal RGBA8 source pixels decrease by 8 MiB, not measured native memory.
- Negative controls load only the main furniture or natural-break module at its current module URL, keeping the candidate fixtures and all other modules. Main furniture gives 15 pass / 2 fail, including 8,192 registry yields instead of 128 and missed live-stool maintenance. Main natural-break gives 34 pass / 1 fail (`30 !== 0` persistent glyphs). The actual integrated tree passes both sets.
- Current-extension ownership, syntax/localization, full-BMP layout/advance/bold oracle and generated rendering-resource checks pass. Pinned launch validation is run against `cedfaedf6140bae61b24afb658869b1d0e6ea1a9` and the exact Forge Java checkout above.
- Independent read-only review found no blocking implementation, font-contract handoff, history-preservation or main-tooling regression. Release freeze, clean-source packaging and canonical CI remain separate integrity boundaries.

The focused commands are recorded in the [font/seat report](low-memory-20261109.md) and [glyph-lifecycle report](low-memory-board-lifecycle-20261109.md). The combined adapter invocation adds `tools/furniture-interaction.test.mjs` to the five-suite lifecycle command. No new runtime implementation was needed during integration; conflict resolution is confined to the paired identity and history.

## Acceptance limits

All operation counts above are source/API-double evidence. There was no BDS, Minecraft client, user-computer, saved-world or LIVE operation. Native RAM/VRAM, peak RSS, frame time, mobile performance, serialization and multiplayer behavior remain unmeasured. Dense valid boards still use one actor per visible nonblank glyph; this repair does not clear historical orphan glyphs or add retries for failed native removals. World Liquor still pins Tavern T205, so this standalone source merge does not certify a family pairing or silently update it.

## Frozen package result

T220 freeze and clean-commit release gate passed against each of main, T218 and T219 as history bases. The canonical packager exported **4,038 files (838 BP / 3,200 RP)**. Archive membership and every file's bytes match committed runtime; paired manifests and release identity pass. Archive SHA-256: `19e756696a48a4a72087a11174fdcaf3335e005cc2b461db5b870df3e84fe8b4` (5,892,118 bytes). This is a build/identity receipt, not a native or client acceptance result. The publication request verifier confirms publishing is disabled. Canonical remote PR and post-merge CI are reported by their linked runs.
