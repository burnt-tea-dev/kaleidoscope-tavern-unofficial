/** Actual placement/storage/visual callbacks with the existing API double.
 * Colours are independent original-JVM results; this is not client acceptance.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {world,system,Player,Potions,ItemStack,GameMode,registerFixturePotion} from '@minecraft/server';
import {potionDisplayColor,POTION_SPECS} from '../runtime/BP/scripts/core/potions.js';
import {potionIdentity,potionCapabilities} from '../runtime/BP/scripts/bedrock/potions.js';
import {placeVanillaBottle,pickVanillaBottleItem,takeVanillaBottle,bottleDisplayKey,syncPotionBottleVisual,maintainPotionBottleVisual,registerVanillaBottleDisplayComponents,installVanillaBottleDisplayEvents,tickPotionBottleVisuals} from '../runtime/BP/scripts/bedrock/vanilla-bottle-displays.js';
import {naturalBreak} from '../runtime/BP/scripts/bedrock/natural-break.js';
import {handleDisplayProjectileHit} from '../runtime/BP/scripts/bedrock/display-projectiles.js';
import {takeWaterBottle,installBottleEvents} from '../runtime/BP/scripts/bedrock/bottles.js';
import {resolveCreativePick} from '../runtime/BP/scripts/bedrock/creative-pick.js';
import {installJavaItemUseOnEvents} from '../runtime/BP/scripts/bedrock/java-placement-router.js';
import {nativeItems} from '../runtime/BP/scripts/bedrock/native-item-storage.js';
const oracle=JSON.parse(fs.readFileSync(new URL('../data/java-parity/potion-colors.json',import.meta.url)));
const java=new Map(oracle.java_potions.map(r=>[r.id,r])),NS='kaleidoscope_tavern:',VISUAL=NS+'potion_liquid_visual';
const nativeIds=oracle.observed_native_registry.ids;
for(const id of nativeIds)registerFixturePotion(id);
let serial=0;
const expected=id=>id==='minecraft:wither'?oracle.wither_adaptation.rgb:java.get(id.replace('minecraft:','').replace('long_mundane','mundane').replace('nightvision','night_vision')).rgb;
const rgb=e=>(e.getProperty('kt_art:red')<<16)|(e.getProperty('kt_art:green')<<8)|e.getProperty('kt_art:blue');
function setup(effectId='minecraft:healing'){
 const d=world.getDimension('overworld'),at={x:++serial*8,y:64,z:0},p=new Player('potion'+serial,d);
 p.location={...at};p.selectedSlotIndex=7;p.isSneaking=true;const base=d.getBlock(at);base.setType('minecraft:stone');
 const item=Potions.resolve(Potions.getEffectType(effectId),Potions.getDeliveryType('Consume'));
 item.nameTag='saved native '+effectId;item.setLore(['metadata retained']);item.setDynamicProperty('test:metadata','opaque');p.inventory.setItem(7,item);
 assert.equal(placeVanillaBottle(p,base,'Up'),true);const block=d.getBlock({...at,y:65});return {p,d,block,item,key:bottleDisplayKey(block)};
}
const visual=b=>b.dimension.getEntities({type:VISUAL,location:b.location,maxDistance:2});
const record=key=>world.getDynamicProperty(key);
function sameItem(got,wanted){assert.equal(got.typeId,wanted.typeId);assert.equal(got.amount,1);assert.deepEqual(got.meta,wanted.meta);assert.equal(got.nameTag,wanted.nameTag);assert.deepEqual(potionIdentity(got),potionIdentity(wanted));}
installVanillaBottleDisplayEvents();
installBottleEvents();
installJavaItemUseOnEvents();

test('every historically observed native potion has an original-source default colour',()=>{
 for(const row of oracle.java_potions)assert.equal(potionDisplayColor('minecraft:'+row.id.replace('night_vision','nightvision')),row.rgb,row.id);
 for(const id of nativeIds)assert.equal(potionDisplayColor(id),expected(id),id);
 assert.equal(potionCapabilities().unmappedDisplayEffects.length,0);
 for(const id of ['wind_charged','weaving','oozing','infested'])assert.equal(Object.hasOwn(POTION_SPECS,'minecraft:'+id),false,'Display must not widen recipe intake');
});
test('all non-water native potion identities drive one shared helper and retain full stacks through pick/take',()=>{
 for(const id of nativeIds.filter(id=>id!=='minecraft:water')){
  const {p,d,block,item,key}=setup(id),entities=visual(block);assert.equal(entities.length,1);assert.equal(rgb(entities[0]),expected(id));
  assert.equal(d.getEntities({type:NS+'stored_items',location:block.location,maxDistance:2}).length,1);
  const before=record(key),ledger=record('kt:native_items/'+key);sameItem(pickVanillaBottleItem(block),item);
  assert.equal(record(key),before);assert.equal(record('kt:native_items/'+key),ledger);assert.equal(visual(block)[0],entities[0]);
  p.inventory.setItem(7,undefined);takeVanillaBottle(p,block);sameItem(p.inventory.getItem(0),item);
  assert.equal(block.typeId,'minecraft:air');assert.equal(record(key),undefined);assert.equal(visual(block).length,0);
 }
});
test('future native IDs keep placement and exact pickup with explicit unmapped white display',()=>{
 registerFixturePotion('minecraft:future_native');const {p,block,item}=setup('minecraft:future_native');
 assert.equal(potionDisplayColor('minecraft:future_native'),undefined);assert.equal(rgb(visual(block)[0]),0xffffff);
 assert.deepEqual(potionCapabilities().unmappedDisplayEffects,['minecraft:future_native']);
 sameItem(pickVanillaBottleItem(block),item);p.inventory.setItem(7,undefined);takeVanillaBottle(p,block);sameItem(p.inventory.getItem(0),item);
});
test('native colour overrides stale JSON; a missing carrier removes the visual without reconstructing inventory',()=>{
 const {block,item,key,d}=setup(),state=JSON.parse(record(key));state.potion.effectId='minecraft:poison';world.setDynamicProperty(key,JSON.stringify(state));
 assert.equal(rgb(syncPotionBottleVisual(block)),expected('minecraft:healing'));
 const before=record(key),ledger=record('kt:native_items/'+key),carrier=d.getEntities({type:NS+'stored_items',location:block.location,maxDistance:2})[0];carrier.removed=true;
 assert.throws(()=>syncPotionBottleVisual(block));assert.equal(visual(block).length,0);assert.equal(record(key),before);assert.equal(record('kt:native_items/'+key),ledger);
 carrier.removed=false;assert.equal(rgb(syncPotionBottleVisual(block)),expected('minecraft:healing'));sameItem(pickVanillaBottleItem(block),item);
});
test('moved helper is repaired, duplicates collapse, unloaded owners defer, and removed owners retire helpers',()=>{
 const {block,key,d}=setup(),original=visual(block)[0];original.location={x:block.location.x+50,y:66,z:10};original.setRotation({x:30,y:45});
 maintainPotionBottleVisual(original);assert.equal(visual(block)[0],original);assert.deepEqual(original.location,{x:block.location.x+.5,y:65,z:.5});assert.deepEqual(original.getRotation(),{x:0,y:0});
 const duplicate=d.spawnEntity(VISUAL,block.location);duplicate.setDynamicProperty(NS+'potion_liquid_anchor',key);syncPotionBottleVisual(block);assert.equal(visual(block).length,1);
 const current=visual(block)[0],cell=`${block.location.x}_${block.location.y}_${block.location.z}`;d.unloaded.add(cell);maintainPotionBottleVisual(current);assert.equal(current.isValid,true);
 d.unloaded.delete(cell);block.setType('minecraft:air');maintainPotionBottleVisual(current);assert.equal(current.isValid,false);
});
test('colour/pick use read-only native access; healthy helper maintenance leaves inventory work to the block tick',()=>{
 const {block,item,d}=setup(),helper=visual(block)[0],components=new Map();registerVanillaBottleDisplayComponents({blockComponentRegistry:{registerCustomComponent:(id,c)=>components.set(id,c)}});
 const plan=nativeItems.plan,read=nativeItems.read;let reads=0;
 nativeItems.plan=()=>{throw Error('visual/pick must not construct a removal plan');};nativeItems.read=function(...args){reads++;return read.apply(this,args);};
 try{
  sameItem(pickVanillaBottleItem(block),item);assert.equal(reads,1);reads=0;
  for(let n=0;n<3;n++)maintainPotionBottleVisual(helper);assert.equal(reads,0);
  components.get(NS+'potion_bottle_visual').onTick({block});assert.equal(reads,1);assert.equal(rgb(helper),expected('minecraft:healing'));
  d.getEntities({type:NS+'stored_items',location:block.location,maxDistance:2})[0].remove();components.get(NS+'potion_bottle_visual').onTick({block});assert.equal(visual(block).length,0);
 }finally{nativeItems.plan=plan;nativeItems.read=read;}
});
test('block lifecycle repairs missing helpers; cleanup is shared by natural and projectile destruction',()=>{
 const components=new Map();registerVanillaBottleDisplayComponents({blockComponentRegistry:{registerCustomComponent:(id,c)=>components.set(id,c)}});
 const {block,d,item,key}=setup();visual(block)[0].remove();components.get(NS+'potion_bottle_visual').onTick({block});assert.equal(visual(block).length,1);
 const permutation=block.permutation;block.setType('minecraft:air');naturalBreak({block,brokenBlockPermutation:permutation},{params:{drop:NS+'potion_bottle'}});
 assert.equal(visual(block).length,0);assert.equal(record(key),undefined);sameItem(d.getEntities({type:'minecraft:item',location:block.location,maxDistance:2})[0].itemStack,item);
 const next=setup('minecraft:poison'),projectile=next.d.spawnEntity('minecraft:arrow',next.block.location);
 assert.equal(handleDisplayProjectileHit({block:next.block,projectile}),true);assert.equal(visual(next.block).length,0);assert.equal(record(next.key),undefined);
});
test('near-first maintenance does not starve a far duplicate with the same owner',()=>{
 const {block,key,d}=setup(),near=visual(block)[0],raw=record(key),ledger=record('kt:native_items/'+key);
 const far=d.spawnEntity(VISUAL,{x:block.location.x+50,y:65,z:10});far.setDynamicProperty(NS+'potion_liquid_anchor',key);
 world.afterEvents.entityLoad.emit({entity:far});
 for(let i=0;i<3;i++)tickPotionBottleVisuals();
 assert.equal(visual(block).length,1);assert.equal([near,far].filter(e=>e.isValid).length,1);
 assert.equal(record(key),raw);assert.equal(record('kt:native_items/'+key),ledger);
});
test('selective cosmetic spawn failure preserves committed native placement and repairs later',()=>{
 const d=world.getDimension('overworld'),spawn=d.spawnEntity.bind(d);let result;
 d.spawnEntity=(type,...args)=>{if(type===VISUAL)throw new Error('cosmetic spawn unavailable');return spawn(type,...args);};
 try{result=setup('minecraft:poison');}finally{d.spawnEntity=spawn;}
 const {p,block,item,key}=result;assert.equal(visual(block).length,0);assert.equal(p.inventory.getItem(7),undefined);
 const raw=record(key),ledger=record('kt:native_items/'+key);sameItem(pickVanillaBottleItem(block),item);
 syncPotionBottleVisual(block);assert.equal(visual(block).length,1);assert.equal(rgb(visual(block)[0]),expected('minecraft:poison'));
 assert.equal(record(key),raw);assert.equal(record('kt:native_items/'+key),ledger);
 takeVanillaBottle(p,block);sameItem(p.inventory.getItem(0),item);
});
test('Java WATER/EMPTY placement stays stateless and returns canonical water through existing routes',()=>{
 // Forge VanillaBottlePlaceEvent.getPlacement: EMPTY/WATER use the ordinary
 // water block, storePotionStack=false; its loot creates canonical water.
 registerFixturePotion('minecraft:empty');
 const canonicalWater=item=>{
  assert.deepEqual(potionIdentity(item),{effectId:'minecraft:water',deliveryId:'Consume'});
  assert.equal(item.nameTag,undefined);assert.deepEqual(item.getLore(),[]);assert.deepEqual(item.getDynamicPropertyIds(),[]);
 };
 for(const effectId of ['minecraft:water','minecraft:empty'])for(const route of ['take','use','protected-break','natural','projectile']){
  const {p,d,block,key}=setup(effectId);assert.equal(block.typeId,NS+'bottle_water');assert.equal(p.inventory.getItem(7),undefined);
  assert.equal(record(key),undefined);assert.equal(record('kt:native_items/'+key),undefined);assert.equal(visual(block).length,0);
  assert.equal(d.getEntities({type:NS+'stored_items',location:block.location,maxDistance:2}).length,0);canonicalWater(resolveCreativePick(block));
  if(route==='take')takeWaterBottle(p,block);
  else if(route==='use'||route==='protected-break'){const event={player:p,block,isFirstEvent:true,cancel:false};(route==='use'?world.beforeEvents.playerInteractWithBlock:world.beforeEvents.playerBreakBlock).emit(event);assert.equal(event.cancel,true);system.advance(1);}
  else if(route==='natural'){const permutation=block.permutation;block.setType('minecraft:air');naturalBreak({block,brokenBlockPermutation:permutation},{params:{drop:NS+'bottle_water'}});}
  else{const projectile=d.spawnEntity('minecraft:arrow',block.location);assert.equal(handleDisplayProjectileHit({block,projectile}),true);}
  assert.equal(block.typeId,'minecraft:air');assert.equal(record(key),undefined);assert.equal(record('kt:native_items/'+key),undefined);
  const drops=d.getEntities({type:'minecraft:item',location:block.location,maxDistance:2});
  if(route==='take'||route==='use'){canonicalWater(p.inventory.getItem(0));assert.equal(drops.length,0);}
  else if(route==='projectile'){assert.equal(p.inventory.getItem(0),undefined);assert.equal(drops.length,0);}
  else{assert.equal(p.inventory.getItem(0),undefined);assert.equal(drops.length,1);canonicalWater(drops[0].itemStack);}
 }
});
test('real vanilla bottle placement faces opposite the player across Java cardinals without changing input or quantity rules',()=>{
 // BottleBlock.getStateForPlacement uses getHorizontalDirection().getOpposite().
 // Java/Minecraft yaw cardinals: south=0, west=90, north=180, east=270.
 registerFixturePotion('minecraft:empty');
 const directions=[[0,'north'],[90,'east'],[180,'south'],[270,'west']];
 const inputs=[
  ['minecraft:healing','potion_bottle'],['minecraft:water','bottle_water'],['minecraft:empty','bottle_water'],
  ['minecraft:honey_bottle','honey_bottle'],['minecraft:dragon_breath','dragon_breath_bottle'],['minecraft:experience_bottle','xp_bottle']
 ];
 for(const [yaw,facing]of directions)for(const mode of [GameMode.Survival,GameMode.Creative])for(const [source,result]of inputs){
  const d=world.getDimension('overworld'),at={x:++serial*8,y:64,z:0},p=new Player('facing'+serial,d,mode),base=d.getBlock(at);
  p.location={...at};p.rotation={x:0,y:yaw};p.selectedSlotIndex=7;p.isSneaking=true;base.setType('minecraft:stone');
  const effect=Potions.getEffectType(source),item=effect?Potions.resolve(effect,Potions.getDeliveryType('Consume')):new ItemStack(source,3),before=item.amount;p.inventory.setItem(7,item);
  assert.equal(placeVanillaBottle(p,base,'Up'),true);const block=d.getBlock({...at,y:65});
  assert.equal(block.typeId,NS+result);assert.equal(block.permutation.getState('minecraft:cardinal_direction'),facing,source+' yaw '+yaw);
  assert.equal(p.inventory.getItem(7)?.amount??0,before-(mode===GameMode.Creative?0:1));
 }
 const d=world.getDimension('overworld'),at={x:++serial*8,y:64,z:0},p=new Player('ordinary'+serial,d);p.location={...at};const block=d.getBlock(at);block.setType('minecraft:stone');p.inventory.setItem(0,new ItemStack('minecraft:experience_bottle'));
 assert.equal(placeVanillaBottle(p,block,'Up'),false);assert.equal(p.inventory.getItem(0).amount,1);assert.equal(d.getBlock({...at,y:65}).isAir,true);
});
