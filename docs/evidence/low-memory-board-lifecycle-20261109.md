# Persistent board glyph cleanup

## Failure and scope

Base: [`1e991be7f64fd7227fd2586491e43c430bc650c3`](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/commit/1e991be7f64fd7227fd2586491e43c430bc650c3), the fresh main read on 2026-11-09. Open PRs #577, #622 and #623 were checked before editing. None owns the natural-destruction cleanup changed here; #622's atlas/seat changes remain a separate candidate.

`bedrock/board-text.js` stores each glyph under `kt:writingBoard/anchor` with a `boardKey|row|index` value. The glyph definition is persistent. `bedrock/natural-break.js` retired helpers only when a string property equalled an owner key, began with `ownerKey/`, or contained a matching JSON `position`. A glyph's pipe-delimited anchor and its JSON `location` satisfy none of those conditions. After the natural-destruction transaction committed, the blocks and board data disappeared but the glyph actors remained. No glyph entity-load or orphan-maintenance path subsequently retired them.

The production functions with the existing deterministic API double reproduce a wide board containing 300 nonblank glyphs: after `naturalBreak`, all six board blocks and its world data are gone, while all **300 persistent glyph handles remain**. Repeating this at different coordinates can accumulate actors independent of the number of surviving boards. This is a source-backed lifetime defect; it is not a measurement of native bytes, RSS, FPS or watchdog time.

The fix calls the existing `removeBoardText` owner for writing-board keys after destruction commits. It removes only that board's glyphs and invalidates its bounded layout-cache entry. Other storage/helper cleanup, data commits, material drops and rollback remain in their current owners. There is no new timer, whole-world sweep, text limit, shortened view distance or changed artwork.

## Java and identity checks

The upstream branch heads were read again from the GitHub API on 2026-11-09:

- Forge 1.20.1 (`main`): `c4ec1880bd44cf3139d3ba744ab30bb379cf1416`.
- NeoForge 1.21.1: `a1afba34981a00e89d57130d3dc8f1e64f1820a2`.
- NeoForge 26.1.2: `9b8f165a4641e738e694641dd81240a0206573e1` (`mod_version=1.1.2-neoforge+mc26.1.2`).

The maintained Forge/1.21.1 source copies and the current 26.1.2 `ChalkboardBlockEntity` / `ChalkboardBlockEntityRender` tie text to its board block entity. They do not create independently persistent glyph actors. This change repairs the lifetime of Bedrock's existing presentation adaptation without changing Java text layout or interactions. The 26.1.2 renderer is a new submit/render-state API; no full loader-port parity is inferred from this check.

Source links: [Forge renderer](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/c4ec1880bd44cf3139d3ba744ab30bb379cf1416/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/client/render/block/ChalkboardBlockEntityRender.java), [1.21.1 renderer](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/a1afba34981a00e89d57130d3dc8f1e64f1820a2/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/client/render/block/ChalkboardBlockEntityRender.java), [26.1.2 renderer](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/9b8f165a4641e738e694641dd81240a0206573e1/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/client/render/block/ChalkboardBlockEntityRender.java).

Main's latest identity was T217 and the separate #622 candidate reserved T218. This candidate uses fresh paired **0.6.219**, preserves UUIDs and Script API dependencies, and appends its own history entry. `publication_request` stays false.

## Discriminating validation

Two cases were added to the existing `tools/board-farm-interaction.test.mjs` entrypoint:

1. Natural destruction of a sandwich board, small chalkboard and wide chalkboard, including upper/side cells, retires 30/30/300 glyphs respectively. A neighboring board remains unchanged. Recreating identical content at the same position rebuilds the retired cache entry.
2. An injected native drop failure preserves board data, blocks and glyphs through rollback. Subsequent normal player recovery still removes the board and glyphs.

With only the tests added, the main-source test run failed at `30 !== 0` (34 passed, one failed). With the four-line runtime repair, the board/farm, pickup, shaker retention, machine ingredient and potion display suites pass **368/368**, with zero failures/skips. They exercise the actual runtime modules with deterministic API doubles.

```sh
node --experimental-loader ./tools/foundation/mock-loader.mjs --test \
  tools/board-farm-interaction.test.mjs tools/pickup/adapters.test.mjs \
  tools/shaker-item-retention.test.mjs tools/machine-native-ingredients.test.mjs \
  tools/potion-bottle-visual.test.mjs
```

The existing current-extension source contract and pinned integration-baseline launch check cover the changed shared lifecycle owner. No inverse-source layer, version-specific verifier, historical hash rewrite or test bypass was introduced. Frozen identity and exact exported archive validation are separate from the behavioral checks.

## Remaining dense-board cost

A separate source operation-count check uses the existing efficiency API double and actual `renderBoardText`: 16 small chalkboards on a 4×4 grid, each with 100 nonblank glyphs. After initialization, one maintenance pass over all boards retains 1,600 helpers and makes 16 entity queries, 26,800 anchor-property reads and 1,600 own-glyph signature comparisons, with zero spawns/removals. Each radius-four query also returns neighboring boards' glyphs before the JavaScript owner filter. These are deterministic API operation counts, not native engine timings or memory measurements.

The glyph definition has 32 client-synchronized properties. The layout cache already has a 128-board bound; the source font metrics module is 65,760 bytes. The lifetime repair leaves this active-board actor density, property schema and maintenance strategy unchanged. A future batching or exact-owner-query change needs separate legacy-helper and multiplayer validation.

## Remaining limits

- This prevents new leaks when the native natural-destruction callback executes. It does not retrospectively scan or remove glyphs already orphaned in a saved world, and does not certify command-driven replacements that bypass that callback.
- Surviving text still has one native helper per nonblank glyph. Dense active boards, their client rendering and neighbor-query costs remain unchanged.
- No BDS, Minecraft client, user computer, saved-world migration, deployment or LIVE operation was used. Native actor serialization, real device peak memory, frame time and visual acceptance remain unmeasured.
