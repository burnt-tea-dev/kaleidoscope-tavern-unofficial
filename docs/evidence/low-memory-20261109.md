# T218: identical board textures and bounded seat maintenance

Base: [`e47978d1fc4d27048e20792f0c4368ce2f263a82`](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/commit/e47978d1fc4d27048e20792f0c4368ce2f263a82), checked against fresh main and open PRs #577/#621 on 2026-11-09. Those PRs do not own the font or seat implementation changed here.

## Concrete costs and repairs

| Source | Before | T218 |
| --- | --- | --- |
| `RP/entity/board_glyph_visual.entity.json` and `textures/board_font` | 256 distinct texture paths; 33 PNGs contain exactly the same fallback page | All 256 logical page keys remain; the 33 identical pages share `glyph_D8`, so 224 PNGs remain |
| Font atlas RGBA8 pixel accounting | 64 MiB | 56 MiB; 8 MiB less nominal pixel storage and 32,160 fewer PNG file bytes |
| `BP/scripts/bedrock/furniture.js::tickFurniture` | Copies all known seat handles every five ticks, then processes at most 128 | Uses the existing bounded storage iterator; enumerates/processes at most 128 handles, progressing after removals |
| Actual seat adapter with 8,192 retained handles | 8,192 registry yields per maintenance pass | 128 yields; the following pass visits the next 128, retiring invalid handles |

The pixel figures are width × height × four bytes per physical PNG. They are **not measured Minecraft RAM/VRAM savings**: native residency, compression, mipmaps, atlas padding and decoder peaks have not been measured. No FPS, TPS or watchdog improvement is claimed from Node counters.

`tools/build_board_font.py` owns the deduplication and binding updates. It compares full alpha-page bytes; RGB is uniformly white in every generated page. It keeps the first identical page and removes only that generator's superseded PNG path. It does not resize a texture or change a glyph. The complete 256-page routing was compared with the immutable base: each new resolved PNG is byte-identical to its old resolved PNG, including all RGBA pixels. The 65,536 advance metrics, page-array ordering, geometries, UVs, animations, tint, glowing outline and camera gates are unchanged. Running the generator again reproduced the same output bytes.

The seat change reuses `bedrock/storage-visual-maintenance.js`. Seat ownership, riders, eject conditions, yaw and five-tick cadence remain in their existing adapters. Its existing tests cover bounded iteration, deletion and newly spawned work; two added tests exercise the real seat entrypoint, its enumeration budget and maintenance of a live stool after invalid handles retire.

## Current contracts replace historical source projections

- `tools/current_extension_source_contract.py` now owns the actual furniture adapter as well as its existing core model. Startup, event and five-tick maintenance wiring stay checked; the actual adapter tests cover seating, transfer rollback, recovery, yaw and the 128-handle budget.
- `tools/board_font_contract.py` derives all RGBA pixels, 256 logical bindings and 65,536 metrics from the pinned GNU Unifont input. It rejects missing or extra atlases, returned duplicate files, wrong page/cell arrays and selectors, missing geometry bindings and material changes. The existing rendering generator still checks every UV, outline, tint and range gate.
- Only the furniture preimage, its T131/T156 reverse deltas and launch postimage, and the board entity's T134 reverse asset entry are retired. No new inverse delta or version-specific exception is added.
- The storage and motion texture aggregates hand exactly 256 font paths to the current contract. The remaining **1,754 historical texture files** keep aggregate `33c0ef8ef55b96e29efcba73fe3c4a951f087d6824a147dd7834070cd31cc9ae`. Adding the 256 original font hashes from the base commit reproduces the former 2,010-file aggregate `a85b798ece7151ec00f6a4d8af2569a4f2cbaf348b2d839fe3a4558d6358c144` exactly; unrelated textures were not reaccepted from changed bytes.
- Launch inventory separately requires all 224 physical atlases plus their entity and subtracts only the 32 source-derived retired aliases. Unrelated-file preservation, geometry budgets, manifests/dependencies, identity and append-only release history remain enabled.

## Verification

- `node --experimental-loader ./tools/foundation/mock-loader.mjs --test tools/furniture-interaction.test.mjs`: 17 passed.
- `node --experimental-loader ./tools/efficiency/mock-loader.mjs --test tools/efficiency/efficiency.test.mjs tools/efficiency/board-rendering.test.mjs`: 66 passed.
- Negative control: loading only the base `furniture.js` into the same 17-case test run gives 15 passes and both new regression failures, including `8192 !== 128`. The working source was not overwritten.
- `python3 tools/test_board_font_contract.py`: 9 passed, including negative mutations to mapping, each RGBA channel, glyph ink, missing/returned atlases, page/cell order, selectors, UVs, tint, outline offsets, metrics and source input; repeated generation is byte-identical.
- `python3 tools/build_board_rendering.py --check`: passed, including original material/UV/outline contracts.
- `node tools/check_board_layout.mjs`: passed the independent full-BMP advance/bold oracle and existing layout checks.
- `python3 tools/check_launch.py --baseline <cedfaedf6140bae61b24afb658869b1d0e6ea1a9 checkout>`: passed exact runtime inventory, with 2,986 unchanged existing runtime files checked. Storage, motion and client-asset checks also passed; no new Java checkout or native observation is claimed.
- Full logical-page byte comparison and repeat generation: passed. The short reproduction below needs the base Git object and Pillow for generation.
- Release identity, append-only history and archive checks are separate from these behavior/resource checks; T218 is a new paired identity with the same UUIDs and API dependencies.

```python
import json, subprocess
from pathlib import Path
base = 'e47978d1fc4d27048e20792f0c4368ce2f263a82'
def old(path):
    return subprocess.check_output(['git', 'show', base + ':' + path])
path = 'runtime/RP/entity/board_glyph_visual.entity.json'
before = json.loads(old(path))
after = json.loads(Path(path).read_bytes())
a = before['minecraft:client_entity']['description']['textures']
b = after['minecraft:client_entity']['description']['textures']
assert a.keys() == b.keys() and len(b) == 256
for key in a:
    assert old('runtime/RP/' + a[key] + '.png') == Path('runtime/RP/' + b[key] + '.png').read_bytes()
before['minecraft:client_entity']['description']['textures'] = b
assert before == after
assert len(set(b.values())) == 224
assert len(list(Path('runtime/RP/textures/board_font').glob('*.png'))) == 224
metrics = 'runtime/BP/scripts/data/board-font.js'
assert old(metrics) == Path(metrics).read_bytes()
```

## Remaining limits

Dense text still uses one native helper per visible glyph (`bedrock/board-text.js`); 300 displayed nonblank glyphs still mean 300 helpers. Full cellar cabinets still require up to nine bottle helpers. This patch reduces duplicate texture resources and script iteration; it does not solve native actor or draw-call density.

No Minecraft client, BDS, user's computer, saved-world deployment or LIVE instance was used. Low-memory-device peak RSS, native texture residency, frame time, rendering, save/reload and multiplayer acceptance remain unmeasured. World Liquor's manifest currently pins Tavern T205; this standalone candidate does not silently rebind that family dependency or publish a release.

## Follow-up: reuse cup state within one maintenance pass (2026-11-16, T226)

Base: `8d4a9c6a8d8e030fd07800b99de025572995fe7d`. This is a bounded implementation improvement to T21 in the existing [28-domain reassessment in PR643](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/pull/643), not a second parity inventory. Open PRs 577, 623, 637, 640, 641, 642, 643 and 644 were checked; none owns `bedrock/mixology.js`. Their runtime changes remain separate candidates. All local and fetched remote source baselines and release histories were checked; T225 was the highest occupied public source version before this candidate reserved paired T226.

`syncCupVisual` previously read the cup record to check initialization, then read it again to load the state. The same synchronous pass also rewrote the chosen helper's anchor even though that helper had just matched the identical key. `initializeNativeCup` now returns the validated current or newly saved state, and the visual adapter reuses it until the pass ends. A new helper still receives its anchor before any color writes. Existing helpers retain their already matched anchor. Native save conflict checks remain in `MixStore.save`; missing records still use the existing `getCup` default, while malformed records fail without replacement. An existing record is now validated during `onPlace` as well as visual maintenance; a malformed record is reported earlier and remains untouched.

The original entity query, duplicate cleanup order, 20-tick block component, palette and RGB writes, rotation, cup payload, placement/pickup transactions and unknown-color fallback are unchanged. There is no cross-pass state cache, new helper, new timer, new experimental requirement, model/texture change or migrated data schema. `mixology.js` already belongs to the current extension source contract, so no historical hash or inverse ledger needed changing.

### Source and API boundaries

The upstream branch heads were re-read on 2026-11-16: Forge `c4ec1880bd44cf3139d3ba744ab30bb379cf1416`, NeoForge 1.21.1 `a1afba34981a00e89d57130d3dc8f1e64f1820a2`, and the separate 26.1.2 branch `9b8f165a4641e738e694641dd81240a0206573e1`. [Forge SignatureCocktailColor](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/c4ec1880bd44cf3139d3ba744ab30bb379cf1416/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/client/render/misc/SignatureCocktailColor.java) reads the saved block-entity color for tint layer 0 and leaves other layers white. [NeoForge SignatureCocktailBlockEntity](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/a1afba34981a00e89d57130d3dc8f1e64f1820a2/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/blockentity/mixology/SignatureCocktailBlockEntity.java) retains the per-cup color/effects. Their color ownership is preserved; this narrow read/write reduction does not certify full loader or renderer equivalence.

The official [Entity API](https://learn.microsoft.com/en-us/minecraft/creator/scriptapi/minecraft/server/entity?view=minecraft-bedrock-stable#setproperty) states that `setProperty` applies on the next tick. Therefore a tempting `getProperty() === expected` skip alone cannot prove same-tick A→B→A correctness: committed A can still have a pending B write. This candidate preserves all palette/RGB writes instead of adopting that shortcut or adding a second property cache. The actual target remains `@minecraft/server` 2.7.0 / server-ui 2.0.0; no claim about a newer API's runtime availability is needed. Dynamic-property reads and writes already exist in the target implementation.

### Operation counts and behavior checks

Using the actual before/after `syncCupVisual` and the existing foundation API double, 128 initialized signature cups (four facings, atlas and arbitrary RGB values), followed by 20 manual maintenance rounds, produced:

| Operation | Before | T226 |
| --- | ---: | ---: |
| World cup-record reads | 5,120 | 2,560 |
| Existing-helper anchor writes | 2,560 | 0 |
| Entity queries | 2,560 | 2,560 |
| Palette/RGB property writes | 10,240 | 10,240 |
| Rotation writes | 2,560 | 2,560 |
| Retained helpers | 128 | 128 |
| Spawns / removals during measured rounds | 0 / 0 | 0 / 0 |

These are API operation counts, not native elapsed time, networking bytes, FPS, TPS, RAM or GC measurements. The rounds are explicit calls, not 20 Minecraft ticks. Color/property writes still occur at the original frequency; active helper density is unchanged. The latest state is read on every pass.

A scratch-only comparison also ran nine scenario groups against both complete production modules and compared all world records, actor state and diagnostic errors: live color/facing A→B→A; duplicate cleanup with foreign anchors retained; missing legacy signature/ordinary cups; missing-helper recreation; corrupt numeric/null/JSON/object records; save failure/retry; spawn failure/retry; property failure/retry; and non-cup cleanup. All snapshots matched. This is deterministic source/API-double evidence, not native-engine or rendered-client acceptance. No tests, fixture files or CI files were added or modified.

The bounded count can be reproduced in any checkout of the before or after commit with its existing loader. Run from the checkout root:

```sh
node --experimental-loader ./tools/foundation/mock-loader.mjs --input-type=module <<'JS'
import {world,Entity,Dimension,BlockPermutation} from '@minecraft/server';
import {syncCupVisual} from './runtime/BP/scripts/bedrock/mixology.js';
import {MixStore,validateCup,cupKey,SIGNATURE,EMPTY_CUP} from './runtime/BP/scripts/core/mixology.js';
const d=world.getDimension('overworld'),store=new MixStore(world,validateCup);
const anchor='kaleidoscope_tavern:cup_anchor',calls={};
for(const [object,name,label,filter] of [
 [world,'getDynamicProperty','worldReads',k=>k.startsWith('kt:cup/')],
 [Entity.prototype,'setDynamicProperty','anchorWrites',k=>k===anchor],
 [Entity.prototype,'setProperty','propertyWrites'],
 [Entity.prototype,'setRotation','rotationWrites'],
 [Dimension.prototype,'getEntities','queries'],
 [Dimension.prototype,'spawnEntity','spawns'],[Entity.prototype,'remove','removes']]){
 const original=object[name];calls[label]=0;
 object[name]=function(...args){if(!filter||filter(...args))calls[label]++;return original.apply(this,args);};
}
const colors=[0x123456,0x5555ff,0xff5555,0xffffff,0];
const cups=Array.from({length:128},(_,i)=>{
 const b=d.getBlock({x:i*4,y:4,z:0}),facing=i%4;
 b.setPermutation(BlockPermutation.resolve('kaleidoscope_tavern:cup_signature_cocktail',{'kaleidoscope_tavern:facing':facing}));
 store.save(cupKey(d.id,b.location),{schema:1,revision:0,item:SIGNATURE,facing,
  payload:{schema:1,color:colors[i%5],effects:[],ingredients:[EMPTY_CUP,EMPTY_CUP,EMPTY_CUP]}},-1);
 syncCupVisual(b);return b;
});
for(const key of Object.keys(calls))calls[key]=0;
for(let round=0;round<20;round++)for(const b of cups)syncCupVisual(b);
console.log({...calls,actors:d.entities.size});
JS
```

Existing shaker-retention, offhand, shared-interaction echo and instant-drink completion suites passed 110 cases. The initial creative-pick invocation did not start because its required World Liquor checkout was absent; this setup failure is distinct from those passing cases. With its existing CI-pinned World Liquor input `879e4bcaec6f77233046629955e09dcc26d76e0c` checked out, the creative-pick suite then passed all 114 cases. The current-extension ownership/syntax/localization check, launch compatibility check and diff check passed. The launch check without arguments does not revalidate upstream Java or a client renderer. Release identity, build and remote CI are recorded separately in the PR.

T21's arbitrary-RGB shading difference and broader client matrix remain open. The existing T02/T03 native container routes still require capacity, metadata and saved-world migration evidence before eliminating helper storage. No BDS, Minecraft client, user's computer, save, deployment or LIVE operation was used.
