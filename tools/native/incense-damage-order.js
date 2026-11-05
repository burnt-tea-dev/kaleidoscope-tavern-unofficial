/** Isolated shared-slot QA only, never LIVE.
 * run_living_effects.py --probe tools/native/incense-damage-order.js
 * One scene follows a real incense pulse, then saves a native conversion in
 * progress for the same-world restart. Event success is never completion.
 */
import {world,system,BlockVolume,BlockPermutation,EntityDamageCause} from '@minecraft/server';
import {decorationDiagnostics} from './bedrock/decorations.js';
const TAG='kt_incense_order_qa',CURE='kaleidoscope_tavern:incense_curing',MARKER='kaleidoscope_tavern:incense_qa_role';
const CURE_EVENT='kaleidoscope_tavern:incense_cure',SAVE='kaleidoscope_tavern:incense_native_qa';
const ZOMBIES=new Set(['minecraft:zombie_villager','minecraft:zombie_villager_v2']);
const VILLAGERS=new Set(['minecraft:villager','minecraft:villager_v2']);
const roles=[{role:'lethal',x:82.5,z:2.5,health:1},{role:'survivor',x:86.5,z:2.5,health:2},{role:'damage_control',x:82.5,z:10.5,health:2},{role:'reset_control',x:82.5,z:18.5,health:2},
 {role:'village_survivor',x:86.5,z:18.5,health:2,spawnEvent:'from_village'},
 {role:'zombified_survivor',x:86.5,z:26.5,health:2,zombify:true}];
const pending={role:'save_pending',x:86.5,z:10.5,health:1,ids:new Set()};
const pause=ticks=>new Promise(resolve=>system.runTimeout(resolve,ticks));
const out=(stage,data={})=>console.warn('[KT-INCENSE-LIFECYCLE] '+JSON.stringify({stage,tick:system.currentTick,...data}));
let active=false;
function require(value,message){if(!value)throw Error(message);}
function roleFor(entity){
 const all=[...roles,pending],known=all.find(row=>row.ids?.has(entity.id));if(known)return known;
 if(!active)return;
 try{const p=entity.location;return all.find(row=>Math.abs(p.x-row.x)<1.5&&Math.abs(p.z-row.z)<1.5&&p.y>=299&&p.y<304);}catch{}
}
function snapshot(entity){
 const id=entity.id;if(!entity.isValid)return {id,valid:false};
 try{
  const strength=entity.getEffect('strength');
  return {id,valid:true,typeId:entity.typeId,health:entity.getComponent('minecraft:health')?.currentValue??null,
   cureTag:entity.hasTag(CURE),shaking:!!entity.getComponent('minecraft:is_shaking'),
   strength:strength?{amplifier:strength.amplifier,ticks:strength.duration}:null,
   nameTag:entity.nameTag,marker:entity.getDynamicProperty(MARKER)??null,qaTag:entity.hasTag(TAG),
   variant:entity.getComponent('minecraft:variant')?.value??null,
   markVariant:entity.getComponent('minecraft:mark_variant')?.value??null,
   skinId:entity.getComponent('minecraft:skin_id')?.value??null};
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
 if(!VILLAGERS.has(entity.typeId)||row.zombify&&!row.before)return;
 row.ids.add(entity.id);row.entity=entity;
 const state=snapshot(entity);
 if(row.completeTick===undefined){row.completeTick=system.currentTick;out('actual_villager',{role:row.role,evidence,typeId:entity.typeId,...state});}
 if(state.valid&&!state.error||!row.complete){row.complete=state;row.metadataReadTick=system.currentTick;}
 const seen=row.completionEvidence??=[];
 if(!seen.some(entry=>entry.evidence===evidence))seen.push({tick:system.currentTick,evidence});
}
const signals={dataDriven:!!world.afterEvents.dataDrivenEntityTrigger,healthChanged:!!world.afterEvents.entityHealthChanged};
world.afterEvents.dataDrivenEntityTrigger?.subscribe(event=>{
 const row=roleFor(event.entity);if(!row)return;row.ids.add(event.entity.id);
 out('native_event',{role:row.role,eventId:event.eventId,typeId:event.entity.typeId});
 if(event.eventId===CURE_EVENT){
  row.requestTick??=system.currentTick;(row.requestTicks??=[]).push(system.currentTick);
  out('component_access_after_request',{role:row.role,components:componentAccess(event.entity)});
 }
 if(event.eventId==='minecraft:entity_transformed')completed(row,event.entity,'dataDriven:entity_transformed');
},{entityTypes:[...ZOMBIES,...VILLAGERS],eventTypes:[CURE_EVENT,'minecraft:entity_transformed']});
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
 if(state.shaking&&row.shakingTick===undefined){
  row.shakingTick=system.currentTick;out('component_access_while_active',{role:row.role,components:componentAccess(entity)});
 }
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
 const d=world.getDimension('overworld'),previous=world.getDynamicProperty(SAVE);
 if(previous){
  const saved=JSON.parse(previous);active=true;pending.ids.add(saved.pending.id);
  const waitStarted=system.currentTick;let loaded=false,completedVillager;
  // worldLoad precedes ticking-area actor loading. Keep the exact saved ID:
  // a name/location fallback here would conceal a genuinely missing actor.
  for(let i=0;i<100;i++){
   try{loaded=!!d.getBlock({x:84,y:300,z:6});}catch{}
   if(loaded)completedVillager=world.getEntity(saved.completed.id);
   if(completedVillager?.isValid)break;
   await pause(1);
  }
  out('restart_saved_id_read',{waitStarted,chunkLoaded:loaded,savedId:saved.completed.id,state:completedVillager?snapshot(completedVillager):null});
  require(loaded,'saved QA chunk did not load');
  require(completedVillager?.isValid&&VILLAGERS.has(completedVillager.typeId),'saved completed villager missing after chunk/actor wait');
  const after=snapshot(completedVillager);
  for(const key of ['nameTag','marker','qaTag','variant','markVariant','skinId'])require(after[key]===saved.completed[key],'saved completed villager changed '+key);
  pending.entity=world.getEntity(saved.pending.id);sample(pending,d);
  out('restart_pending_initial',{beforeSave:saved.pending,afterLoad:pending.entity?snapshot(pending.entity):null});
  for(let i=0;i<100&&pending.completeTick===undefined;i++){await pause(1);sample(pending,d);}
  require(pending.completeTick!==undefined,'saved native conversion did not finish');
  await pause(2);sample(pending,d);
  require(pending.complete.nameTag===saved.pending.nameTag,'saved conversion lost name');
  out('restart_pending_completed',{state:pending.complete,completionEvidence:pending.completionEvidence});
  // An earlier failed observer may already have witnessed its transformation.
  // This restart then verifies saved final state, not another cure in flight.
  const nativeTransformationThisRun=pending.completionEvidence.some(row=>row.evidence!=='perTick:villager_type');
  const result={kind:'done',phase:'restart',players:world.getAllPlayers().length,
   scope:'saved final-state readback; native cure timing belongs to the original observation',nativeTransformationThisRun,
   completedBefore:saved.completed,completedAfter:after,pendingBefore:saved.pending,pendingAfter:pending.complete};
  for(const entity of [completedVillager,pending.entity])if(entity?.isValid)entity.remove();
  world.setDynamicProperty(SAVE,undefined);d.runCommand('tickingarea remove kt_incense_order_qa');active=false;
  console.warn('[LIVING_EFFECT_QA] '+JSON.stringify(result));return;
 }
 d.runCommand('tickingarea add circle 84 300 6 1 kt_incense_order_qa true');
 let loaded=false;for(let i=0;i<60&&!loaded;i++){await pause(5);try{loaded=!!d.getBlock({x:84,y:300,z:6});}catch{}}
 require(loaded,'QA chunk unavailable');
 d.fillBlocks(new BlockVolume({x:80,y:299,z:0},{x:88,y:304,z:28}),'minecraft:stone');
 for(const row of [...roles,pending]){row.ids=new Set();d.fillBlocks(new BlockVolume({x:Math.floor(row.x)-1,y:300,z:Math.floor(row.z)-1},{x:Math.floor(row.x)+1,y:303,z:Math.floor(row.z)+1}),'minecraft:air');}
 const block=d.getBlock({x:84,y:300,z:2});block.setPermutation(BlockPermutation.resolve('kaleidoscope_tavern:butterfly_incense'));
 active=true;out('capabilities',{signals,cureEvent:CURE_EVENT,javaConfiguredTicks:60,nativeWindowTicks:240});
 d.runCommand('difficulty hard');
 for(const row of roles){
  // Real native entry points: public summon, abandoned-village spawn, and
  // villager zombification. Count observed types, not requested identifiers.
  const entity=d.spawnEntity(row.zombify?'minecraft:villager':'minecraft:zombie_villager',{x:row.x,y:300,z:row.z},row.spawnEvent?{spawnEvent:row.spawnEvent}:undefined);
  row.entity=entity;row.ids.add(entity.id);
 }
 await pause(5);
 const zombified=roles.find(row=>row.zombify);sample(zombified,d);
 require(zombified.entity?.isValid&&VILLAGERS.has(zombified.entity.typeId),'native villager setup did not resolve');
 zombified.entity.triggerEvent('become_zombie');await pause(5);
 for(const row of roles){
  sample(row,d);const entity=row.entity;require(entity?.isValid&&ZOMBIES.has(entity.typeId),'native zombie setup did not resolve: '+row.role);
  entity.nameTag='KT incense '+row.role;entity.addTag(TAG);entity.setDynamicProperty(MARKER,row.role);
  entity.getComponent('minecraft:health').setCurrentValue(row.health);row.before=snapshot(entity);
  out('resolved_recipient',{role:row.role,...row.before,components:componentAccess(entity)});
 }
 block.setPermutation(block.permutation.withState('kaleidoscope_tavern:open',1));
 const [one,survivor,control,reset]=roles,deadline=system.currentTick+240;
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
  if(reset.resetRequestedTick===undefined&&reset.requestTick!==undefined&&system.currentTick-reset.requestTick>=20){
   reset.resetRequestedTick=system.currentTick;
   require(reset.entity?.isValid&&ZOMBIES.has(reset.entity.typeId),'reset recipient transformed too early');
   reset.entity.triggerEvent(CURE_EVENT);out('reset_during_cure',{role:reset.role,...snapshot(reset.entity)});
  }
  if([survivor,reset,...roles.slice(4)].every(row=>row.completeTick!==undefined)){
   // Native Spawn/Transformed callbacks may arrive after the per-tick type read.
   // Keep the first completion tick, then read metadata after those callbacks.
   await pause(2);for(const row of roles)sample(row,d);break;
  }
  if(survivor.death)break;
 }
 const observations=roles.map(row=>({role:row.role,before:row.before,requestTick:row.requestTick??null,requestTicks:row.requestTicks??[],firstCureTagTick:row.tagTick??null,
  firstShakingTick:row.shakingTick??null,completeTick:row.completeTick??null,
  elapsedFromNativeEvent:row.requestTick!==undefined&&row.completeTick!==undefined?row.completeTick-row.requestTick:null,
  actualVillager:row.complete??null,metadataReadTick:row.metadataReadTick??null,completionEvidence:row.completionEvidence??[],death:row.death??null,hurts:row.hurts??[],controlledHurt:row.controlledHurt??null,
  metadata:row.complete?.valid&&!row.complete.error?{nameTagPreserved:row.complete.nameTag===row.before.nameTag,markerPreserved:row.complete.marker===row.before.marker,qaTagPreserved:row.complete.qaTag}:null}));
 const elapsed=survivor.requestTick!==undefined&&survivor.completeTick!==undefined?survivor.completeTick-survivor.requestTick:null;
 const nativeComplete=survivor.completeTick!==undefined,javaDelayMatches=elapsed===60,lethalMatches=one.death?.cause==='magic';
 const externalDamageMatches=control.controlledHurt?.accepted&&control.death?.cause==='magic';
 const nativeEventConfirmed=survivor.completionEvidence?.some(row=>row.evidence!=='perTick:villager_type');
 const resetElapsed=reset.completeTick!==undefined&&reset.requestTicks?.length===2?reset.completeTick-reset.requestTicks[1]:null,resetMatches=resetElapsed===60;
 const dualCases=[survivor,...roles.slice(4)],nativeTypesCovered=[...new Set(dualCases.filter(row=>row.completeTick-row.requestTick===60&&row.completionEvidence?.some(e=>e.evidence!=='perTick:villager_type')).map(row=>row.before.typeId))],bothNativeTypes=ZOMBIES.size===nativeTypesCovered.length&&nativeTypesCovered.every(type=>ZOMBIES.has(type));
 const result={kind:nativeComplete&&javaDelayMatches&&lethalMatches&&externalDamageMatches&&nativeEventConfirmed&&resetMatches&&bothNativeTypes?'done':'partial',phase:'first',players:world.getAllPlayers().length,
  nativeObservationComplete:nativeComplete,javaConfiguredTicks:60,nativeElapsedTicks:elapsed,javaDelayMatches,lethalMatches,externalDamageMatches,nativeEventConfirmed,resetElapsed,resetMatches,nativeTypesCovered,bothNativeTypes,observations};
 if(nativeComplete){
  block.setPermutation(block.permutation.withState('kaleidoscope_tavern:open',0));
  // Keep the completed actor and save one owned native conversion in flight.
  // The runner stops normally as soon as this phase result reaches its log.
  const actor=d.spawnEntity('minecraft:zombie_villager',{x:pending.x,y:300,z:pending.z});pending.entity=actor;pending.ids.add(actor.id);
  await pause(5);sample(pending,d);require(pending.entity?.isValid&&ZOMBIES.has(pending.entity.typeId),'save recipient did not resolve');
  pending.entity.nameTag='KT incense saved conversion';pending.entity.getComponent('minecraft:health').setCurrentValue(1);
  pending.entity.triggerEvent(CURE_EVENT);await pause(1);sample(pending,d);
  require(pending.entity.isValid&&ZOMBIES.has(pending.entity.typeId)&&snapshot(pending.entity).shaking,'native save recipient is not converting');
  const save={completed:survivor.complete,pending:snapshot(pending.entity)};
  world.setDynamicProperty(SAVE,JSON.stringify(save));result.savedConversion=save;
 }
 console.warn('[LIVING_EFFECT_QA] '+JSON.stringify(result));
}catch(error){console.warn('[LIVING_EFFECT_QA] '+JSON.stringify({kind:'failure',error:String(error)}));}},world.getDynamicProperty(SAVE)?1:20));
