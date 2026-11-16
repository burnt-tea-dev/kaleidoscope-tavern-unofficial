# Pressing ingredient-card geometry

The shared card owner is `runtime/RP/models/entity/runtime_pressing_card.geo.json`.
Its eight centered cubes are 8×8×0.5 model pixels, with origins [-4,-4,-0.25].
Java's generated model is 16×16×1, the reviewed FIXED parent scale is 1, and the
pressing renderer applies scale 0.5. The prior 4×4×0.25 card accidentally applied
an extra half scale. No animation scale is introduced because it would also
risk scaling ingredient positions.

`tools/machine_ingredient_geometry.py` validates current native resources against
raw pinned Forge/NeoForge renderer and official generated-parent inputs under
`data/pressing-ingredient-source/`. The 1.20.1 ItemModelGenerator bytecode gives
the broad slab [0,0,7.5]→[16,16,8.5]. It does not establish the 1.21.1 extrusion
algorithm. Both maintained renderers and both generated parents agree on scale.

## Shared ownership and preserved routes

Canonical runtime JSON is the active authoring source. The former generator in
`history/pre-release-0.6.29/tools/pressing_tub_visual.py` is archived and no active
tool invokes it. It is retained as historical evidence, including its incorrect
old comment, not used to rebuild this release. No second geometry generator or
release-specific postimage is added.

The T216 contract originally owned exactly the repaired card resource. Historical launch
comparison delegates that exact path to this source-backed validator. The file
has no entry in existing reconciliation/reverse-delta/launch hash ledgers and
is not part of a historical aggregate group. Those ledgers are unchanged; tests
reject adding the card back to them. The generic source-view and historical-file
entry points use the same current contract. Release identity/history remains
separate. Unchanged route/control resources retain their existing ownership.

The full current resource census must find exactly eight pressing helpers.
They share eight card cubes per helper, 64 global slots, and 22 food IDs
(21 card kinds, including the existing sour-cherry alias). The five cube kinds
remain 4×4×4; all nine barrel cards remain 8×8×0.5. Every bone, local center,
parent chain, UV direction, texture alias, material, helper route, part visibility,
animation expression and frozen-frame selector is retained.

The actual pressing adapter is unchanged. The focused JavaScript tests execute
its helper selection/configuration across all current food IDs and counts 1–64,
compare all 64 packed slot properties with independent source-derived samples,
and check that cardinal tilt only changes the existing frame flags. Existing
machine native-storage/callback and texture-clock tests remain applicable.

## Scope of acceptance

The [portable evidence](evidence/blockbench-pressing-card-20261109/README.md)
preserves the original baseline and candidate scenes, independent audits and
raw GUI JPEGs. SOURCE and AFTER agree in isolated broad-face scale; BEFORE is
half the linear size. The candidate changes only 16 vector fields, 48 scalars,
in eight cubes. No PNG, material, shader, helper lifecycle, gameplay, body or
held-pose change is made, including the rack's accepted +6 first-person Y lift.

Native cards still approximate source alpha-edge extrusion with two broad faces.
Ordinary ice alpha/material behavior is not newly accepted. The raw decoded
Blockbench tilted AABBs exceed declared visible bounds both before and after,
for the one audited seed/count over 320 poses. The external engine/model-to-world
and culling contract is unproven, so bounds, pivots and Y signs are not changed.
Body clearance, world-facing and native material rendering are not certified.
No Minecraft, BDS, LIVE, saved-world or full addon parity acceptance is claimed.

## Layout arithmetic follow-up (2026-11-16, T227)

### Scope and current audit

This change starts from current main
[`896d023e94eb25cce1d557c34e54ae33193b004d`](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/commit/896d023e94eb25cce1d557c34e54ae33193b004d).
The existing [28-domain API review](PARITY-MATRIX.md#現行功能api-與成本重審2026-11-16t224-候選)
remains the enumeration. T224/#643 is already on this main. This is a concrete
cost improvement in T25's ingredient display path, not a second gap census or
completion claim for arbitrary item rendering, pressing-card edges or culling.

The complete open-PR file lists were checked: #577 custom effects, #623 board
evidence, #637 workflow, #640 author interoperability, #641 grape support,
#642 Molotov, #644 board anchor reads and #645 cup maintenance. None owns
`core/ingredient-layout.js`, `tools/machine_ingredient_geometry.py` or this
document. This independent branch does not include those unmerged repairs.
Paired metadata will need normal integration reconciliation; their source
versions T225/T226 are left reserved, and this candidate uses T227.

### Source and API decision

`RenderUtils.stableRandom` mixes the position, item index and channel with the
same SplitMix64 constants. The index contribution is invariant within one
item's layout. Barrel rendering samples five channels per visible item;
pressing rendering samples three to five, retaining the original conditional
X/Z calculations. Previously every channel repeated `BigInt(index)` and the
same multiplication/XOR. Now each item computes this shared input once, then
passes it to the unchanged channel mixing and float-rounding operations.
The public `stableItemRandom` interface still applies the same arithmetic.
Nothing is cached between calls, blocks, entities or ticks.

On 2026-11-16 the official branch heads were read again: Forge 1.20.1
[`c4ec1880`](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/c4ec1880bd44cf3139d3ba744ab30bb379cf1416/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/util/RenderUtils.java#L99-L105),
NeoForge 1.21.1
[`a1afba34`](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/a1afba34981a00e89d57130d3dc8f1e64f1820a2/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/util/RenderUtils.java#L94-L100)
and the separate 26.1.2 branch
[`9b8f165a`](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/9b8f165a4641e738e694641dd81240a0206573e1/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/util/RenderUtils.java#L90-L96)
all retain that mixer. The maintained Forge
[barrel renderer](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/c4ec1880bd44cf3139d3ba744ab30bb379cf1416/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/client/render/block/BarrelBlockEntityRender.java#L97-L116)
and [pressing renderer](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/c4ec1880bd44cf3139d3ba744ab30bb379cf1416/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/client/render/block/PressingTubBlockEntityRender.java#L58-L69)
provide the index/channel usage. A separate upstream branch is not described as
an adopted release or as proof of full newest-version parity.

No API upgrade or experiment is needed: this is pure arithmetic in the current
server 2.7.0 / server-ui 2.0.0, engine >=1.26.50 source. Native property writes
are deliberately untouched. Official
[Entity.getProperty/setProperty](https://learn.microsoft.com/en-us/minecraft/creator/scriptapi/minecraft/server/entity?view=minecraft-bedrock-stable)
documents deferred property application; native readback equality alone is not
a justification for removing same-tick A→B→A writes. Existing T01 storage
readback timing needs its separate owner review, and is not repaired here.

### Measured source cost

The reproduction below calls the real old and new modules. All 8,380 complete
sampled layouts and 5,280 direct random outputs are exactly equal, without an
epsilon. Inputs cover five positions including negative coordinates and the
±30,000,000 range, all pressing counts 0–64 and all eight helper offsets, and
barrel count combinations with empty/full slots and all four global offsets.
The existing independent 64-slot source samples also pass unchanged.

| Complete layout pass | BigInt conversions before → after | Index multiplications before → after | All BigInt multiplications before → after |
| --- | ---: | ---: | ---: |
| Pressing, 64 ingredients / 8 helpers | 536 → 344 | 256 → 64 | 1,024 → 832 |
| Barrel, four slots of 16 / 36 visible pieces | 372 → 228 | 180 → 36 | 720 → 576 |

Conversion counts are observed by wrapping the standard `BigInt` constructor;
the multiplication columns follow the actual mixer calls and two retained
mixing multiplications per random sample. They are operation counts, not
measured elapsed time, allocation bytes, Minecraft RAM, FPS or TPS. Helper
counts, native API writes/queries, animations, asset bytes, data/transactions,
save keys and maintenance frequencies do not change.

### Reproduction and validation

Run from this repository with the base Git object available. This one-off
analysis is recorded here; no test, fixture or CI source file was added.

```sh
node --input-type=module <<'JS'
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import assert from 'node:assert/strict';
const path='runtime/BP/scripts/core/ingredient-layout.js';
const base=execFileSync('git',['show','896d023e94eb25cce1d557c34e54ae33193b004d:'+path],{encoding:'utf8'});
const load=s=>import('data:text/javascript;base64,'+Buffer.from(s).toString('base64'));
const before=await load(base),after=await load(readFileSync(path,'utf8'));
const positions=[{x:0,y:0,z:0},{x:1,y:-64,z:-1},{x:-16,y:319,z:32},{x:30000000,y:-64,z:-30000000},{x:-30000000,y:319,z:30000000}];
let layoutCases=0,randomCases=0;
for(const p of positions){
 assert.equal(after.blockPosSeed(p),before.blockPosSeed(p));
 for(let count=0;count<=64;count++)for(let start=0;start<64;start+=8){assert.deepEqual(after.pressingIngredientLayout(p,count,start),before.pressingIngredientLayout(p,count,start));layoutCases++;}
 for(let a=0;a<=16;a++)for(let b=0;b<=16;b++){
  const counts=[a,b,16-a,16-b],slots=counts.map(count=>count?{count}:null);
  for(let slot=0;slot<4;slot++){assert.deepEqual(after.barrelIngredientLayout(p,slots,slot),before.barrelIngredientLayout(p,slots,slot));layoutCases++;}
 }
 for(let i=0;i<132;i++)for(let channel=1;channel<=8;channel++){assert.equal(after.stableItemRandom(before.blockPosSeed(p),i,channel),before.stableItemRandom(before.blockPosSeed(p),i,channel));randomCases++;}
}
const NativeBigInt=globalThis.BigInt;
function conversions(fn){let n=0;function wrapped(...args){n++;return NativeBigInt(...args);}wrapped.asIntN=NativeBigInt.asIntN;globalThis.BigInt=wrapped;try{fn();return n;}finally{globalThis.BigInt=NativeBigInt;}}
const p=positions[2];
const pressing=m=>{for(let start=0;start<64;start+=8)m.pressingIngredientLayout(p,64,start);};
const barrel=m=>{const slots=Array.from({length:4},()=>({count:16}));for(let slot=0;slot<4;slot++)m.barrelIngredientLayout(p,slots,slot);};
console.log(JSON.stringify({layoutCases,randomCases,identical:true,BigIntConversions:{pressing64:{before:conversions(()=>pressing(before)),after:conversions(()=>pressing(after))},barrel4x16:{before:conversions(()=>barrel(before)),after:conversions(()=>barrel(after))}}}));
JS
node --test tools/pressing-ingredient-routing.test.mjs
python tools/test_machine_ingredient_geometry.py
python tools/check_motion.py
```

The existing pressing adapter suite passes all four cases (including all
accepted foods/counts and independent source properties); the existing machine
ingredient resource suite passes all nine cases. Motion preservation and
JavaScript syntax checks pass. The current ingredient contract now owns the
shared layout interface and both consumer imports, while its original geometry
oracle is unchanged. The former layout hash stays verbatim in
`data/motion-source-reference.json`; the existing current-owner dispatch removes
that path from historical source equality. No historical hash is regenerated,
no inverse layer or release-specific exception is added, and the consumer
adapters retain their own source ownership.

T227 is a standalone paired candidate with unchanged UUIDs and API requirements.
The original geometry evidence above remains T216 evidence. This follow-up
does not claim a new Blockbench result, native execution, client rendering,
saved-world, multiplayer, release or deployment result. CI and packaging are
recorded on the Draft PR for its actual final commit.
