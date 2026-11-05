/** Isolated QA only; never LIVE. One v1 boundary, not another v2 cure test.
 * run_living_effects.py --probe tools/native/incense-v1-boundary.js --offline
 * Reuse the canonical registration factory's actual incense onTick callback.
 * The receiver only captures that callback: blocks, actors, time and metadata
 * are native. No gameplay implementation or entity definition is substituted.
 * Current BDS normally upgrades a newly spawned v1 actor on its next tick.
 * If that happens here, stop partial instead of measuring its v2 replacement.
 */
import {world,system,BlockVolume,BlockPermutation,EntityComponentTypes,EquipmentSlot} from '@minecraft/server';
import {registerDecorationComponents,decorationDiagnostics} from './bedrock/decorations.js';
const Z1='minecraft:zombie_villager',Z2='minecraft:zombie_villager_v2',V1='minecraft:villager',V2='minecraft:villager_v2';
const CURE='kaleidoscope_tavern:incense_cure',SAVE='kaleidoscope_tavern:incense_v1_boundary_qa';
const POSITION={x:62.5,y:300,z:2.5},PARK={x:56.5,y:300,z:2.5},BLOCK={x:60,y:300,z:2},TAG='kt_incense_v1_qa';
const pause=ticks=>new Promise(resolve=>system.runTimeout(resolve,ticks));
const out=(stage,data={})=>console.warn('[KT-INCENSE-V1] '+JSON.stringify({stage,tick:system.currentTick,...data}));
function require(value,message){if(!value)throw Error(message);}
let onTick,active;
registerDecorationComponents({blockComponentRegistry:{registerCustomComponent(id,component){if(id==='kaleidoscope_tavern:incense')onTick=component.onTick;}},itemComponentRegistry:{registerCustomComponent(){}}});
function itemData(item){
 if(!item)return null;
 return {typeId:item.typeId,amount:item.amount,nameTag:item.nameTag??null,lore:item.getLore(),
  dynamicProperties:Object.fromEntries(item.getDynamicPropertyIds().sort().map(id=>[id,item.getDynamicProperty(id)]))};
}
function snapshot(entity){
 if(!entity?.isValid)return null;
 const components=entity.getComponents().map(c=>c.typeId).sort(),equipment=entity.getComponent(EntityComponentTypes.Equippable),inventory=entity.getComponent('minecraft:inventory')?.container;
 const equipmentSlots=[];
 if(equipment)for(const [name,slot]of Object.entries(EquipmentSlot)){
  try{equipmentSlots.push({name,slot,item:itemData(equipment.getEquipment(slot))});}catch(error){equipmentSlots.push({name,slot,error:String(error)});}
 }
 return {id:entity.id,typeId:entity.typeId,nameTag:entity.nameTag,tags:entity.getTags().sort(),
  dynamicProperties:Object.fromEntries(entity.getDynamicPropertyIds().sort().map(id=>[id,entity.getDynamicProperty(id)])),
  health:entity.getComponent('minecraft:health')?.currentValue??null,
  variant:entity.getComponent('minecraft:variant')?.value??null,
  markVariant:entity.getComponent('minecraft:mark_variant')?.value??null,
  skinId:entity.getComponent('minecraft:skin_id')?.value??null,
  equipmentExposed:!!equipment,equipmentSlots,inventoryExposed:!!inventory,
  inventory:inventory?Array.from({length:inventory.size},(_,slot)=>({slot,item:itemData(inventory.getItem(slot))})):null,
  tradeComponents:components.filter(id=>/trade/.test(id))};
}
function relevant(entity){
 if(!active)return false;
 try{return [Z1,Z2,V1,V2].includes(entity.typeId)&&Math.abs(entity.location.x-POSITION.x)<1.5&&Math.abs(entity.location.z-POSITION.z)<1.5;}catch{return false;}
}
world.afterEvents.dataDrivenEntityTrigger?.subscribe(event=>{
 if(!relevant(event.entity))return;
 if(event.eventId===CURE)active.nativeRequests.push({tick:system.currentTick,typeId:event.entity.typeId});
 out('native_event',{role:active.role,eventId:event.eventId,typeId:event.entity.typeId});
},{entityTypes:[Z1,Z2,V1,V2],eventTypes:[CURE,'minecraft:entity_transformed']});
world.afterEvents.entitySpawn.subscribe(event=>{
 if(!relevant(event.entity))return;
 active.events.push({tick:system.currentTick,cause:event.cause,typeId:event.entity.typeId});
 if(event.cause==='Transformed'&&event.entity.typeId===V1){active.completedTick??=system.currentTick;active.entity=event.entity;}
 out('entity_spawn',{role:active.role,cause:event.cause,typeId:event.entity.typeId});
});
async function readChunk(d){
 for(let i=0;i<100;i++){try{if(d.getBlock(POSITION))return;}catch{}await pause(1);}
 throw Error('v1 QA chunk did not load');
}
async function observeV1(d,role,reset){
 const block=d.getBlock(BLOCK),period=Math.floor(system.currentTick/120);
 // Prime the real owner's coordinate, then remove the block while waiting.
 // This prevents automatic block ticks consuming the controlled pulse before
 // the native actor's one-tick v1 window. No clock or block object is mocked.
 block.setPermutation(BlockPermutation.resolve('kaleidoscope_tavern:butterfly_incense'));
 onTick({block});block.setPermutation(BlockPermutation.resolve('minecraft:air'));
 while(Math.floor(system.currentTick/120)===period)await pause(1);
 const row={role,nativeRequests:[],events:[]};active=row;
 const entity=d.spawnEntity(Z1,POSITION);row.entity=entity;
 row.spawnedType=entity.typeId;
 if(entity.typeId!==Z1){active=null;return {...row,entity:undefined,status:'v1_not_created'};}
 entity.nameTag='KT v1 '+role;entity.addTag(TAG);entity.addTag('kt_v1_'+role);
 entity.setDynamicProperty('kaleidoscope_tavern:v1_qa_role',role);
 entity.setDynamicProperty('kaleidoscope_tavern:v1_qa_number',42);
 entity.setDynamicProperty('kaleidoscope_tavern:v1_qa_boolean',true);
 entity.getComponent('minecraft:health').setCurrentValue(2);row.before=snapshot(entity);
 const curesBefore=decorationDiagnostics.incenseCures;
 block.setPermutation(BlockPermutation.resolve('kaleidoscope_tavern:butterfly_incense').withState('kaleidoscope_tavern:open',1));
 row.ownerTick=system.currentTick;onTick({block});block.setPermutation(BlockPermutation.resolve('minecraft:air'));
 row.ownerCureRequests=decorationDiagnostics.incenseCures-curesBefore;
 require(row.ownerCureRequests===1,'canonical incense callback did not request the v1 cure');
 for(let elapsed=0;elapsed<100;elapsed++){
  await pause(1);
  const candidates=d.getEntities({location:{x:61,y:299,z:1},volume:{x:3,y:5,z:3}}).filter(e=>[Z1,Z2,V1,V2].includes(e.typeId));
  require(candidates.length===1,'native cure recipient missing or ambiguous');row.entity=candidates[0];
  const state=snapshot(row.entity);
  if(state.typeId===Z2){row.status='automatic_v1_to_v2_upgrade';row.upgraded=state;break;}
  if(state.typeId===V1&&row.completedTick!==undefined){
   row.elapsedTicks=row.completedTick-(row.resetTick??row.ownerTick);row.status=row.elapsedTicks===60?'v1_cure_completed':'v1_timing_mismatch';
   await pause(2);
   const settled=d.getEntities({location:{x:61,y:299,z:1},volume:{x:3,y:5,z:3}}).filter(e=>[V1,V2].includes(e.typeId));
   require(settled.length===1,'completed native villager did not settle');
   row.entity=settled[0];row.final=snapshot(row.entity);break;
  }
  if(reset&&system.currentTick-row.ownerTick===20){
   // Same owned native reset event as the already reviewed v2 reset control.
   // Initial damage and the cure request above always use the real incense owner.
   row.resetTick=system.currentTick;row.entity.triggerEvent(CURE);
  }
 }
 row.status??='v1_conversion_not_completed';active=null;
 const {entity:unused,...result}=row;out('case',result);return result;
}
world.afterEvents.worldLoad.subscribe(()=>system.runTimeout(async()=>{try{
 require(world.getAllPlayers().length===0,'QA requires zero players');
 const d=world.getDimension('overworld'),previous=world.getDynamicProperty(SAVE);
 if(previous){
  const saved=JSON.parse(previous);await readChunk(d);const after=[];
  for(const before of saved){
   let entity;for(let i=0;i<100;i++){entity=world.getEntity(before.id);if(entity?.isValid)break;await pause(1);}
   require(entity?.isValid,'saved final actor missing after chunk/actor wait');const state=snapshot(entity);
   for(const field of ['typeId','nameTag','tags','dynamicProperties','variant','markVariant','skinId','equipmentSlots','inventory'])require(JSON.stringify(state[field])===JSON.stringify(before[field]),'saved final actor changed '+field);
   after.push(state);
  }
  console.warn('[LIVING_EFFECT_QA] '+JSON.stringify({kind:'done',phase:'restart',players:0,scope:'same QA saved final-state readback only',before:saved,after}));return;
 }
 require(typeof onTick==='function','canonical incense callback unavailable');
 d.runCommand('tickingarea add circle 62 300 2 1 kt_incense_v1_qa true');await readChunk(d);d.runCommand('difficulty hard');d.runCommand('gamerule doMobSpawning false');
 d.fillBlocks(new BlockVolume({x:54,y:299,z:0},{x:65,y:304,z:4}),'minecraft:stone');
 d.fillBlocks(new BlockVolume({x:55,y:300,z:1},{x:64,y:303,z:3}),'minecraft:air');
 const first=await observeV1(d,'normal',false),cases=[first];
 if(first.status==='v1_cure_completed'){
  const completed=world.getEntity(first.final.id);require(completed?.isValid,'completed control disappeared');completed.teleport(PARK);
  cases.push(await observeV1(d,'reset',true));
 }
 const complete=cases.length===2&&cases.every(row=>row.status==='v1_cure_completed');
 if(complete)world.setDynamicProperty(SAVE,JSON.stringify(cases.map(row=>row.final)));
 console.warn('[LIVING_EFFECT_QA] '+JSON.stringify({kind:complete?'done':'partial',phase:'first',players:world.getAllPlayers().length,
  observationOnly:true,v1Verified:complete,metadataScope:'actual native name/tags/DP and exposed equipment/inventory only; no arbitrary Java data/trade claim',cases}));
}catch(error){console.warn('[LIVING_EFFECT_QA] '+JSON.stringify({kind:'failure',phase:world.getDynamicProperty(SAVE)?'restart':'first',players:world.getAllPlayers().length,error:String(error)}));}},20));
