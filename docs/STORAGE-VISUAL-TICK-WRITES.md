# Storage display updates within one tick

## Problem and source

The shared storage display owner in main `896d023e94eb25cce1d557c34e54ae33193b004d` compares the desired bottle kind with `Entity.getProperty`. The [official Entity contract](https://learn.microsoft.com/en-us/minecraft/creator/scriptapi/minecraft/server/entity?view=minecraft-bedrock-stable#getproperty) says that a `setProperty` value is applied on the next tick. Reading it again within the same tick still returns the old value.

For an entity showing A, two calls requesting B then A therefore queue only B: the second call reads A and skips its write. This is a source/API-contract defect; this review does not claim a reproduced native player input sequence. It was already noted as an open counterexample in the family review, and is not attributed solely to the holder change in #643.

Java renders the current stored stack: [HolderBlockEntityRender](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/c4ec1880bd44cf3139d3ba744ab30bb379cf1416/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/client/render/block/HolderBlockEntityRender.java) and the other storage renderers recorded in `data/storage-render-source.json`. The reviewed upstream heads remain Forge `c4ec1880`, NeoForge `a1afba34`, and the separate 26.1.2 line `9b8f165a`. This repair keeps their existing poses and item identities.

## Repair in 0.6.228

`bedrock/storage-visual-maintenance.js` remembers successful kind writes by entity ID and property for the current server tick. A request writes when the actual value differs, or when this owner's pending value differs. The pending value is recorded immediately after a successful setter, before rotation or teleport work. Setter failure preserves the last successful pending value; later pose failure does not erase it.

The next call in a different tick clears this map and uses fresh native readback. The map holds IDs and property values, not entity or ItemStack objects. Its size follows the successful entity/property writes in the last active tick; cleanup happens on the next call, with no new timer or world scan. Different wrappers for the same native ID share pending state. Different properties remain independent.

The owner still repairs every observable property, position and rotation mismatch. Settled displays retain zero property, rotation and teleport writes. Repeated writes before the native property settles are not newly deduplicated. Arbitrary queued writes from another addon in the same tick cannot be read or arbitrated here; the normal later maintenance observes the committed value.

This common path serves holders, tilted/circular racks, cellar/bar cabinets and registered extension furniture. Inventory, transactions, helper counts, maintenance intervals, geometry, textures and animations are unchanged. The module moves to the existing current furniture source contract; its original efficiency hash record remains unchanged under `historicalNewRuntimeFiles`, without a reverse-source layer or version exception.

## Targeted validation

- The formal function was called through the existing efficiency API loader with next-tick property application. For A → B → A, main queued `[B]` and ended on B; the repair queued `[B, A]` and ended on A. Both performed two native property reads.
- All 363 sequences of one to five requests over three kinds ended on their final requested kind. Main failed 116 of these sequences; the repair failed none. Each call used a new wrapper with the same entity ID.
- Setter failure and retry, pose failure after a successful setter, independent properties and next-tick drift checks passed. A 100-call settled-state sample retained 100 property reads and zero writes before and after.
- The unchanged 56-case efficiency suite passed. The first experimental implementation failed two existing missing-property checks; that design was discarded in favor of the conservative write condition above. No test file was changed.

Focused commands use the existing suite and Java source contract:

```sh
node --no-warnings --loader ./tools/efficiency/mock-loader.mjs --test tools/efficiency/efficiency.test.mjs
python tools/check_storage_rendering.py --java-source /path/to/official-tavern-forge-checkout
```

The minimal API-contract reproduction can run from either main or the repaired checkout:

```sh
node --no-warnings --loader ./tools/efficiency/mock-loader.mjs --input-type=module <<'JS'
import {system} from './tools/efficiency/mock-server.mjs';
import {syncStorageVisualPose} from './runtime/BP/scripts/bedrock/storage-visual-maintenance.js';
let actual=0, queued, writes=[];
const at={x:0,y:0,z:0};
const e={id:'reproduction',location:at,getProperty:()=>actual,
 setProperty:(_k,v)=>{queued=v;writes.push(v);},
 getRotation:()=>({x:0,y:0}),setRotation:()=>{},tryTeleport:()=>true};
system.currentTick=1;
for(const kind of [1,0])syncStorageVisualPose(e,'kaleidoscope_tavern:storage_kind',kind,at,0);
actual=queued??actual;
console.log({actual,writes});
JS
```

These are offline contract and source results. They do not measure native CPU, memory, FPS, TPS, client rendering or saved-world behavior. No tests, fixtures, CI, engine/API upgrade, client, BDS, player-device or LIVE operation was added.
