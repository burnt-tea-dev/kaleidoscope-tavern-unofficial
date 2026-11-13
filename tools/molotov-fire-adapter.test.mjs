/** Impact callbacks against block-interface doubles, not native fire simulation. */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {world,GameMode} from '@minecraft/server';
import {naturalBreak} from '../runtime/BP/scripts/bedrock/natural-break.js';
import {handleDisplayProjectileHit,displayProjectileDiagnostics} from '../runtime/BP/scripts/bedrock/display-projectiles.js';
import {igniteMolotov,molotovDiagnostics,resolveMolotovImpact,THROWN_MOLOTOV} from '../runtime/BP/scripts/bedrock/molotov.js';
const origin={x:.5,y:10.5,z:.5};
const key=p=>p.x+','+p.y+','+p.z;
function fixture(){
 const blocks=new Map(),writes=[],sounds=[],particles=[],reads=new Map();
 function block(p,id='minecraft:air',states={},waterlogged=false){
  const value={typeId:id,location:{...p},isWaterlogged:waterlogged,permutation:{getState:name=>states[name]},
   get isAir(){return this.typeId==='minecraft:air';},get isLiquid(){return /^(?:minecraft:)(?:flowing_)?(?:water|lava)$/.test(this.typeId);},
   setType(next){writes.push({p:{...p},typeId:next});this.typeId=next;}};
  blocks.set(key(p),value);return value;
 }
 const dimension={getBlock(p){const k=key(p);reads.set(k,(reads.get(k)??0)+1);return blocks.get(k)??block(p);},playSound:(...a)=>sounds.push(a),spawnParticle:(...a)=>particles.push(a)};
 const floor=(id,states={},wet=false)=>{for(let x=-4;x<=4;x++)for(let z=-4;z<=4;z++)block({x,y:9,z},id,states,wet);};
 const center=()=>writes.find(w=>w.p.x===0&&w.p.z===0);
 return {block,dimension,floor,writes,sounds,particles,reads,center};
}
test('impact selects soul fire immediately on both soul bases, retaining the Java burst and sound counts',()=>{
 for(const id of ['minecraft:soul_sand','minecraft:soul_soil']){
  const f=fixture();f.floor(id);igniteMolotov(f.dimension,origin);
  assert.equal(f.center()?.typeId,'minecraft:soul_fire');assert(f.writes.every(w=>w.typeId==='minecraft:soul_fire'));
  assert.equal(f.particles.length,50);assert.deepEqual(f.sounds.map(s=>s[0]),['firecharge.use','random.glass']);
 }
});
test('water, lava, torch and bottom stone slab do not create unsupported fires',()=>{
 for(const id of ['minecraft:water','minecraft:lava','minecraft:torch','minecraft:stone_block_slab']){
  const f=fixture();f.floor(id,{top_slot_bit:false});igniteMolotov(f.dimension,origin);
  assert.equal(f.writes.length,0,id);assert.equal(f.particles.length,50,id);
 }
});
test('top stone slab and upside-down stair supply a full upper support face',()=>{
 for(const [id,states]of [['minecraft:stone_block_slab',{top_slot_bit:true}],['minecraft:stone_stairs',{upside_down_bit:true}]]){
  const f=fixture();f.floor(id,states);igniteMolotov(f.dimension,origin);
  assert.deepEqual(f.center(),{p:{x:0,y:10,z:0},typeId:'minecraft:fire'});
 }
});
test('normal fire may attach beside a known flammable block despite air below',()=>{
 const f=fixture();f.block({x:1,y:9,z:0},'minecraft:oak_planks');igniteMolotov(f.dimension,origin);
 assert.deepEqual(f.center(),{p:{x:0,y:9,z:0},typeId:'minecraft:fire'});
 assert(f.writes.every(w=>w.typeId==='minecraft:fire'));
});
test('waterlogged wood and nonflammable nether wood do not establish side support',()=>{
 for(const [id,wet]of [['minecraft:oak_planks',true],['minecraft:crimson_planks',false],['minecraft:warped_planks',false]]){
  const f=fixture();f.block({x:1,y:9,z:0},id,{},wet);igniteMolotov(f.dimension,origin);
  assert.equal(f.center(),undefined,id); // Fire on that block's own full top remains valid.
 }
});
test('unclassified custom supports retain existing behavior and report that uncertainty',()=>{
 for(const id of ['third_party:unknown_support','third_party:unknown_fence']){
  const f=fixture();f.floor(id);const before=molotovDiagnostics.unclassifiedSupports;
  igniteMolotov(f.dimension,origin);assert.equal(f.center()?.typeId,'minecraft:fire');
  assert.equal(molotovDiagnostics.unclassifiedSupports-before,f.writes.length);
  assert([...f.reads.values()].every(n=>n===1),'cache each block only during this impact');
 }
});
test('entity and block hit delivery still owns one impact, one burst and one removal',()=>{
 const f=fixture();f.floor('minecraft:stone');const properties=new Map();let valid=true,removes=0;
 const entity={typeId:THROWN_MOLOTOV,location:origin,dimension:f.dimension,get isValid(){return valid;},getDynamicProperty:k=>properties.get(k),setDynamicProperty:(k,v)=>properties.set(k,v),remove(){valid=false;removes++;}};
 assert.equal(resolveMolotovImpact({projectile:entity}),true);const fires=f.writes.length;
 assert.equal(resolveMolotovImpact({projectile:entity}),false);
 assert.equal(f.writes.length,fires);assert.equal(f.particles.length,50);assert.equal(removes,1);
});


// These callbacks do not prove that a real arrow delivers the native hit event.
const MOLOTOV='kaleidoscope_tavern:molotov';let placedSerial=0;
function placedMolotov(owner,{wet=false,id=MOLOTOV}={}){
 const dimension=world.getDimension('overworld'),position={x:1000+(++placedSerial)*16,y:64,z:0},block=dimension.getBlock(position);
 block.setType(id);if(wet)block.setWaterlogged(true);
 const projectile=dimension.spawnEntity('minecraft:arrow',{x:position.x-1,y:64.5,z:.5}),component={owner};
 projectile.getComponent=id=>id==='minecraft:projectile'?component:undefined;
 projectile.nameTag='Original arrow';projectile.setDynamicProperty('test:payload','keep');projectile.velocity={x:1,y:0,z:0};
 const spawned=()=>dimension.getEntities({type:THROWN_MOLOTOV,location:position,maxDistance:2});
 const hit=()=>handleDisplayProjectileHit({projectile,getBlockHit:()=>({block})});
 return {dimension,position,block,projectile,spawned,hit};
}

test('placed Molotov collision and selection use Java BottleBlock 6 by 14 by 6 shape',()=>{
 const c=JSON.parse(fs.readFileSync(new URL('../runtime/BP/blocks/molotov.json',import.meta.url)))['minecraft:block'].components;
 const expected={origin:[-3,0,-3],size:[6,14,6]};
 assert.deepEqual(c['minecraft:collision_box'],expected);assert.deepEqual(c['minecraft:selection_box'],expected);
});

for(const mode of [undefined,GameMode.Survival,GameMode.Creative,'mob'])test('placed Molotov hit launches one ownerless native projectile for '+(mode??'ownerless arrow'),()=>{
 const owner=mode==='mob'?{typeId:'minecraft:skeleton'}:mode?{typeId:'minecraft:player',getGameMode:()=>mode}:undefined;
 const f=placedMolotov(owner),rule=world.gameRules.mobGriefing;world.gameRules.mobGriefing=true;
 try{assert.equal(f.hit(),true);assert.equal(f.block.typeId,'minecraft:air');assert.equal(f.spawned().length,1);
  const child=f.spawned()[0];assert.deepEqual(child.location,{x:f.position.x+.5,y:64.5,z:.5});assert.deepEqual(child.shots,[{x:0,y:0,z:0}]);assert.equal(child.getComponent('minecraft:projectile').owner,undefined);
  assert.equal(f.projectile.removed,false);assert.equal(f.projectile.nameTag,'Original arrow');assert.equal(f.projectile.getDynamicProperty('test:payload'),'keep');assert.deepEqual(f.projectile.velocity,{x:1,y:0,z:0});
  assert.equal(f.hit(),false);assert.equal(f.spawned().length,1,'a duplicate delivered after removal must not relaunch');
  assert.equal(f.dimension.getEntities({type:'minecraft:item',location:f.position,maxDistance:2}).length,0);
 }finally{world.gameRules.mobGriefing=rule;}
});

for(const owner of [{typeId:'minecraft:player',getGameMode:()=>GameMode.Adventure},{typeId:'minecraft:skeleton'}])test('Java Molotov spawn precedes the base-bottle removal permission for '+owner.typeId,()=>{
 const f=placedMolotov(owner),rule=world.gameRules.mobGriefing;world.gameRules.mobGriefing=false;
 try{assert.equal(f.hit(),true);assert.equal(f.block.typeId,MOLOTOV);assert.equal(f.spawned().length,1);assert.equal(f.projectile.removed,false);}
 finally{world.gameRules.mobGriefing=rule;}
});

test('waterlogged placed Molotov retains its water and does not turn into an item drop',()=>{
 const f=placedMolotov(undefined,{wet:true});assert.equal(f.hit(),true);assert.equal(f.block.typeId,'minecraft:water');assert.equal(f.spawned().length,1);
 assert.equal(f.dimension.getEntities({type:'minecraft:item',location:f.position,maxDistance:2}).length,0);
});

for(const failure of ['spawn','shoot','block'])test('placed Molotov '+failure+' failure preserves the bottle and original projectile with no orphan',()=>{
 const f=placedMolotov(undefined,{wet:failure==='block'}),spawn=f.dimension.spawnEntity,errors=displayProjectileDiagnostics.errors.length;
 if(failure==='spawn')f.dimension.failSpawn=true;
 if(failure==='block')f.block.failSet=true;
 if(failure==='shoot')f.dimension.spawnEntity=function(...args){const child=spawn.apply(this,args);child.failShoot=true;return child;};
 try{assert.equal(f.hit(),false);assert.equal(f.block.typeId,MOLOTOV);assert.equal(f.spawned().length,0);assert.equal(f.projectile.removed,false);assert.equal(f.projectile.getDynamicProperty('test:payload'),'keep');assert.equal(displayProjectileDiagnostics.errors.length,errors+1);assert.equal(f.block.isWaterlogged,failure==='block');}
 finally{f.dimension.failSpawn=false;f.dimension.spawnEntity=spawn;}
});

test('an ordinary solid hit does not launch a Molotov or alter the target',()=>{
 const f=placedMolotov(undefined,{id:'minecraft:stone'});assert.equal(f.hit(),false);assert.equal(f.block.typeId,'minecraft:stone');assert.equal(f.spawned().length,0);assert.equal(f.projectile.removed,false);
});

test('the queued natural-break callback cannot refund a shattered Molotov',()=>{
 const f=placedMolotov(),brokenBlockPermutation=f.block.permutation;assert.equal(f.hit(),true);
 naturalBreak({block:f.block,brokenBlockPermutation},{drop:MOLOTOV});
 assert.equal(f.dimension.getEntities({type:'minecraft:item',location:f.position,maxDistance:2}).length,0);assert.equal(f.spawned().length,1);
});
