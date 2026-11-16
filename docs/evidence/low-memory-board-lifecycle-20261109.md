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

## Follow-up: one anchor read per maintenance pass (2026-11-16, T225)

This candidate starts from main `8d4a9c6a8d8e030fd07800b99de025572995fe7d`. All open Tavern and World Liquor PR changed paths were reviewed again. Tavern #623 owns isolated board evidence tooling; #640 owns compatibility and #641 owns grape destruction. None changes `bedrock/board-text.js`. The separate holder candidate #643 remains independent.

### API reassessment and chosen change

[Issue #639](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/issues/639) proposes `Dimension.getEntitiesAtBlockLocation`. The [official Dimension reference](https://learn.microsoft.com/en-us/minecraft/creator/scriptapi/minecraft/server/dimension?view=minecraft-bedrock-stable#getentitiesatblocklocation) and published [@minecraft/server 2.7.0 package metadata](https://registry.npmjs.org/@minecraft/server/2.7.0) were checked. The target package includes the method (`server-2.7.0.tgz` published SHA-1 `f3b92eb373b63e83a5018d40c76596cdb3abde70`), but its declaration only describes entities at a location. Neither inspected contract defines point-versus-block-volume/bounding-box semantics or establishes that every existing half-block-root helper and previously discoverable displaced helper remains included. There is no verified isolated BDS result here. **#639's exact-block replacement remains open**, not an engine impossibility and not a completed query-scope optimization.

The existing radius query has a separate proven cost: owner filtering reads each helper's anchor, then rendering reads each owned helper's same anchor again for grouping. The source callback is synchronous, contains no yield and performs no anchor writes in that interval. `forEachHelper` now passes the already-read value to grouping. There is no cross-call cache, new persistent field, helper or API requirement. Every pass still performs the native query and observes every returned helper anchor again.

Rendering builds the same anchor groups before changing any actor. Removal first collects the matching handles in native query order, then removes them in that order; it does not traverse grouped duplicates. Invalid-handle/property-read errors therefore occur before actor changes, as before. The prefix conversion, type filter, radius, query origin, signatures, glyph origin/local offsets, duplicate cleanup, bounded layout cache and recovery paths remain unchanged. The rendering path also no longer materializes the intermediate filtered-helper array; callback/allocation/native timing has not been benchmarked.

The Forge `main` head `c4ec1880bd44cf3139d3ba744ab30bb379cf1416`, NeoForge `1.21.1` head `a1afba34981a00e89d57130d3dc8f1e64f1820a2` and separate `26.1.2` head `9b8f165a4641e738e694641dd81240a0206573e1` were read on 2026-11-16. The maintained [Forge TextBlockEntityRender](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/c4ec1880bd44cf3139d3ba744ab30bb379cf1416/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/client/render/block/TextBlockEntityRender.java) and [1.21.1 renderer](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/a1afba34981a00e89d57130d3dc8f1e64f1820a2/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/client/render/block/TextBlockEntityRender.java) still bind text to the board and cull its text at the board center. This change only reduces discovery work in the existing Bedrock presentation adaptation. Java font, glow, camera/culling and complete loader parity are not newly established.

### Reproducible source-operation result

One steady maintenance pass, after initialization, using the unchanged existing efficiency API double and each revision's actual `renderBoardText`:

| Scene | Anchor reads before → after | Entity queries | Signature reads | Retained actors | Spawn/remove |
|---|---:|---:|---:|---:|---:|
| One small board, 100 nonblank glyphs | 200 → 100 (50% fewer) | 1 → 1 | 100 → 100 | 100 → 100 | 0/0 → 0/0 |
| 4×4 adjacent small boards, 100 glyphs each | 26,800 → 25,200 (1,600 fewer; 5.97%) | 16 → 16 | 1,600 → 1,600 | 1,600 → 1,600 | 0/0 → 0/0 |

The reduction is exactly one native anchor read per matching owned helper during rendering. Neighbor helpers still dominate the dense scene. Removal already read anchors once and has no claimed read-count reduction. These are deterministic operation counts, not BDS/RAM/FPS/GC/render-time measurements; no actual client, user computer, saved-world or LIVE run was performed.

Run this from the candidate repository to compare its current file against the fixed main source without adding a test or fixture:

```sh
node --input-type=module <<'JS'
import {execFileSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
import {Dimension,Entity,counters,resetCounters} from './tools/efficiency/mock-server.mjs';
const path='runtime/BP/scripts/bedrock/board-text.js';
const base='8d4a9c6a8d8e030fd07800b99de025572995fe7d';
const read=Entity.prototype.getDynamicProperty;
let anchors=0,signatures=0;
Entity.prototype.getDynamicProperty=function(k){
 if(k==='kt:writingBoard/anchor')anchors++;
 if(k==='kt:writingBoard/signature')signatures++;
 return read.call(this,k);
};
for(const label of ['before','after']){
 const source=label==='before'?execFileSync('git',['show',base+':'+path],{encoding:'utf8'}):readFileSync(path,'utf8');
 const code=source.replace(/from '(\.\.[^']+)'/g,(_,s)=>`from '${new URL(s,pathToFileURL(process.cwd()+'/'+path))}'`);
 const owner=await import('data:text/javascript;base64,'+Buffer.from(code).toString('base64'));
 for(const width of [1,4]){
  const d=new Dimension(label+width),boards=[];
  const data={text:'A'.repeat(100),color:'white',glowing:false,alignment:'left',verticalAlignment:'top'};
  for(let x=0;x<width;x++)for(let z=0;z<width;z++)boards.push({info:{kind:'chalk',large:false,facing:'north',root:{x,y:0,z}},key:`board/${x}/${z}`});
  for(const b of boards)owner.renderBoardText(d,b.info,data,null,b.key);
  resetCounters();anchors=0;signatures=0;
  for(const b of boards)owner.renderBoardText(d,b.info,data,null,b.key);
  console.log({label,boards:boards.length,anchors,signatures,queries:counters.queries,actors:d.entities.size,spawns:counters.spawns,removes:counters.removes});
 }
}
JS
```

The bounded offline comparison also checked complete actor property/signature/position snapshots after missing-glyph recovery, a version60 helper displaced outside the board block but within the original radius, duplicates, missing/numeric/vector anchors, another owner's prefix and an unrelated entity type. Shortening, interleaved `A/B/A` clear order and an invalid-handle read throwing before any actor mutation matched the base. No new tests, fixtures or CI jobs were added.

Existing checks passed: efficiency entrypoints 74 passed / 3 existing skips; board/farm interaction 35 passed; board layout; current-extension source wiring/syntax/localization; launch compatibility. The skips remain skips and are not native acceptance. Runtime is frozen as fresh paired 0.6.225 after inspecting all remote/local producer baselines and release histories (maximum occupied source version 0.6.224); UUIDs, `@minecraft/server 2.7.0`, UI 2.0.0 and engine requirements remain unchanged. This source version is independent of private family manifest-only 3xxxx output identities. Required PR CI and exact archive equality are separate release checks.
