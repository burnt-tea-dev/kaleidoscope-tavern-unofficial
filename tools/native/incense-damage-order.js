/** Isolated shared-slot QA only, never LIVE. Keep the T202 runtime unchanged.
 * run_living_effects.py --probe tools/native/incense-damage-order.js
 *                      --phases first --timeout-seconds 420
 * One QA scene follows a real incense pulse through native conversion completion.
 * Static vanilla definitions suggest up to 300 seconds; event success is not completion.
 */
import {world,system,BlockVolume,BlockPermutation,EntityDamageCause} from '@minecraft/server';
import {decorationDiagnostics} from './bedrock/decorations.js';
const TAG='kt_incense_order_qa',CURE='kaleidoscope_tavern:incense_curing',MARKER='kaleidoscope_tavern:incense_qa_role';
const ZOMBIES=new Set(['minecraft:zombie_villager','minecraft:zombie_villager_v2']);
const VILLAGERS=new Set(['minecraft:villager','minecraft:villager_v2']);
const roles=[{role:'lethal',x:82.5,z:2.5,health:1},{role:'survivor',x:86.5,z:2.5,health:2},{role:'damage_control',x:82.5,z:10.5,health:2}];
const pause=ticks=>new Promise(resolve=>system.runTimeout(resolve,ticks));
const out=(stage,data={})=>console.warn('[KT-INCENSE-LIFECYCLE] '+JSON.stringify({stage,tick:system.currentTick,...data}));
let active=false;
function require(value,message){if(!value)throw Error(message);}
function roleFor(entity){
 const known=roles.find(row=>row.ids?.has(entity.id));if(known)return known;
 if(!active)return;
 try{const p=entity.location;return roles.find(row=>Math.abs(p.x-row.x)<1.5&&Math.abs(p.z-row.z)<1.5&&p.y>=299&&p.y<304);}catch{}
}
function snapshot(entity){
 const id=entity.id;if(!entity.isValid)return {id,valid:false};
 try{
  const strength=entity.getEffect('strength');
  return {id,valid:true,typeId:entity.typeId,health:entity.getComponent('minecraft:health')?.currentValue??null,
   cureTag:entity.hasTag(CURE),shaking:!!entity.getComponent('minecraft:is_shaking'),
   strength:strength?{amplifier:strength.amplifier,ticks:strength.duration}:null,
   nameTag:entity.nameTag,marker:entity.getDynamicProperty(MARKER)??null,qaTag:entity.hasTag(TAG)};
 }catch(error){return {id,valid:entity.isValid,error:String(error)};}
}
function componentAccess(entity){
 return ['minecraft:is_shaking','minecraft:transformation','minecraft:timer'].map(id=>{
  try{
   const component=entity.getComponent(id);if(!component)return {id,present:false};
   const descriptors=Object.getOwnPropertyDescriptors(Object.getPrototypeOf(component));
   return {id,present:true,members:Object.entries(descriptors).filter(([name])=>name!=='constructor').map(([name,d])=>({name,get:!!d.get,set:!!d.set,method:typeof d.value==='function'}))};
  }catch(error){return {id,error:String(error)};}
 });
}
function completed(row,entity,evidence){
 if(!VILLAGERS.has(entity.typeId))return;
 row.ids.add(entity.id);row.entity=entity;
 const state=snapshot(entity);
 if(row.completeTick===undefined){row.completeTick=system.currentTick;out('actual_villager',{role:row.role,evidence,typeId:entity.typeId,...state});}
 if(state.valid&&!state.error||!row.complete)row.complete=state;
 (row.completionEvidence??=[]).push({tick:system.currentTick,evidence});
}
const signals={dataDriven:!!world.afterEvents.dataDrivenEntityTrigger,healthChanged:!!world.afterEvents.entityHealthChanged};
world.afterEvents.dataDrivenEntityTrigger?.subscribe(event=>{
 const row=roleFor(event.entity);if(!row)return;row.ids.add(event.entity.id);
 out('native_event',{role:row.role,eventId:event.eventId,typeId:event.entity.typeId});
 if(event.eventId==='villager_converted'||event.eventId==='minecraft:villager_converted'){
  row.requestTick??=system.currentTick;out('component_access_after_request',{role:row.role,components:componentAccess(event.entity)});
 }
 if(event.eventId==='minecraft:entity_transformed')completed(row,event.entity,'dataDriven:entity_transformed');
},{entityTypes:[...ZOMBIES,...VILLAGERS],eventTypes:['villager_converted','minecraft:villager_converted','minecraft:entity_transformed']});
world.afterEvents.entitySpawn.subscribe(event=>{
 const row=roleFor(event.entity);if(!row)return;row.ids.add(event.entity.id);
 out('entity_spawn',{role:row.role,cause:event.cause,id:event.entity.id,typeId:event.entity.typeId});
 if(event.cause==='Transformed')completed(row,event.entity,'entitySpawn:Transformed');
});
world.afterEvents.entityHurt.subscribe(event=>{
 const row=roleFor(event.hurtEntity);if(!row)return;
 (row.hurts??=[]).push({tick:system.currentTick,damage:event.damage,cause:event.damageSource.cause});
 out('hurt',{role:row.role,...row.hurts.at(-1),health:snapshot(event.hurtEntity).health});
});
world.afterEvents.entityHealthChanged?.subscribe(event=>{
 const row=roleFor(event.entity);if(row)out('health_changed',{role:row.role,oldValue:event.oldValue,newValue:event.newValue});
});
world.afterEvents.entityDie.subscribe(event=>{
 const row=roleFor(event.deadEntity);if(!row)return;
 row.death={tick:system.currentTick,cause:event.damageSource.cause};out('death',{role:row.role,...row.death});
});
function sample(row,dimension){
 let entity=row.entity;
 if(!entity?.isValid&&!row.death){
  const candidates=dimension.getEntities({location:{x:row.x-1.4,y:299,z:row.z-1.4},volume:{x:2.8,y:5,z:2.8}}).filter(e=>ZOMBIES.has(e.typeId)||VILLAGERS.has(e.typeId));
  if(candidates.length===1)entity=row.entity=candidates[0];
 }
 if(!entity)return;
 const state=snapshot(entity);
 if(state.cureTag&&row.tagTick===undefined)row.tagTick=system.currentTick;
 if(state.shaking&&row.shakingTick===undefined)row.shakingTick=system.currentTick;
 if(state.typeId&&VILLAGERS.has(state.typeId))completed(row,entity,'perTick:villager_type');
 // Durations change every tick. Record state changes and explicit milestones,
 // not thousands of identical countdown rows.
 const key=JSON.stringify({...state,strength:state.strength?.amplifier??null});
 if(key!==row.lastState){row.lastState=key;out('state',{role:row.role,...state});}
 const start=row.requestTick??row.tagTick;
 if(start!==undefined){
  const elapsed=system.currentTick-start;
  if([1,20,60,120,1200,2000,3600,6000].includes(elapsed))out('milestone',{role:row.role,elapsed,...state,incensePulses:decorationDiagnostics.incensePulses});
 }
 return state;
}
world.afterEvents.worldLoad.subscribe(()=>system.runTimeout(async()=>{try{
 require(world.getAllPlayers().length===0,'QA requires zero players');
 const d=world.getDimension('overworld');d.runCommand('tickingarea add circle 84 300 6 1 kt_incense_order_qa true');
 let loaded=false;for(let i=0;i<60&&!loaded;i++){await pause(5);try{loaded=!!d.getBlock({x:84,y:300,z:6});}catch{}}
 require(loaded,'QA chunk unavailable');
 d.fillBlocks(new BlockVolume({x:80,y:299,z:0},{x:88,y:304,z:12}),'minecraft:stone');
 for(const row of roles){row.ids=new Set();d.fillBlocks(new BlockVolume({x:Math.floor(row.x)-1,y:300,z:Math.floor(row.z)-1},{x:Math.floor(row.x)+1,y:303,z:Math.floor(row.z)+1}),'minecraft:air');}
 const block=d.getBlock({x:84,y:300,z:2});block.setPermutation(BlockPermutation.resolve('kaleidoscope_tavern:butterfly_incense'));
 active=true;out('capabilities',{signals,javaConfiguredTicks:60,nativeWindowTicks:6400});
 for(const row of roles){
  // Public summonable identity; record native resolution to v2 before setup.
  const entity=d.spawnEntity('minecraft:zombie_villager',{x:row.x,y:300,z:row.z});row.entity=entity;row.ids.add(entity.id);
 }
 await pause(5);
 for(const row of roles){
  sample(row,d);const entity=row.entity;require(entity?.isValid&&ZOMBIES.has(entity.typeId),'native zombie setup did not resolve: '+row.role);
  entity.nameTag='KT incense '+row.role;entity.addTag(TAG);entity.setDynamicProperty(MARKER,row.role);
  entity.getComponent('minecraft:health').setCurrentValue(row.health);row.before=snapshot(entity);
  out('resolved_recipient',{role:row.role,...row.before,components:componentAccess(entity)});
 }
 block.setPermutation(block.permutation.withState('kaleidoscope_tavern:open',1));
 const [one,survivor,control]=roles,deadline=system.currentTick+6400;
 while(system.currentTick<deadline){
  await pause(1);for(const row of roles)sample(row,d);
  const start=control.requestTick??control.tagTick;
  if(!control.tested&&start!==undefined&&system.currentTick-start>=30){
   control.tested=true;
   if(control.entity?.isValid&&ZOMBIES.has(control.entity.typeId)){
    const before=snapshot(control.entity),accepted=control.entity.applyDamage(1,{cause:EntityDamageCause.magic});
    control.controlledHurt={tick:system.currentTick,accepted,beforeHealth:before.health,immediateHealth:snapshot(control.entity).health};
    out('external_hurt_during_cure',{role:control.role,...control.controlledHurt});
   }else out('external_hurt_during_cure',{role:control.role,skipped:'recipient already removed or transformed'});
  }
  if(survivor.completeTick!==undefined||survivor.death)break;
 }
 const observations=roles.map(row=>({role:row.role,before:row.before,requestTick:row.requestTick??null,firstCureTagTick:row.tagTick??null,
  firstShakingTick:row.shakingTick??null,completeTick:row.completeTick??null,
  elapsedFromNativeEvent:row.requestTick!==undefined&&row.completeTick!==undefined?row.completeTick-row.requestTick:null,
  actualVillager:row.complete??null,completionEvidence:row.completionEvidence??[],death:row.death??null,hurts:row.hurts??[],controlledHurt:row.controlledHurt??null,
  metadata:row.complete?.valid&&!row.complete.error?{nameTagPreserved:row.complete.nameTag===row.before.nameTag,markerPreserved:row.complete.marker===row.before.marker,qaTagPreserved:row.complete.qaTag}:null}));
 const elapsed=survivor.requestTick!==undefined&&survivor.completeTick!==undefined?survivor.completeTick-survivor.requestTick:null;
 const nativeComplete=survivor.completeTick!==undefined,javaDelayMatches=elapsed===60,lethalMatches=one.death?.cause==='magic';
 const result={kind:nativeComplete&&javaDelayMatches&&lethalMatches?'done':'partial',phase:'first',players:world.getAllPlayers().length,
  nativeObservationComplete:nativeComplete,javaConfiguredTicks:60,nativeElapsedTicks:elapsed,javaDelayMatches,lethalMatches,observations};
 active=false;
 // Preserve an incomplete/mismatched scene for the native owner's inspection.
 if(result.kind==='done'){
  for(const entity of d.getEntities({location:{x:80,y:299,z:0},volume:{x:9,y:6,z:13}}))if(ZOMBIES.has(entity.typeId)||VILLAGERS.has(entity.typeId))entity.remove();
  block.setPermutation(BlockPermutation.resolve('minecraft:air'));d.runCommand('tickingarea remove kt_incense_order_qa');
 }
 console.warn('[LIVING_EFFECT_QA] '+JSON.stringify(result));
}catch(error){console.warn('[LIVING_EFFECT_QA] '+JSON.stringify({kind:'failure',error:String(error)}));}},20));
