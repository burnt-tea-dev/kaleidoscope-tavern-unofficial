/** Forge giveItemToPlayer overflow, without overriding minecraft:item/player definitions. */
import {world,system} from '@minecraft/server';
export const PICKUP_AFTER='kaleidoscope_tavern:pickup_after';
export const TOMB_PICKUP_UNLOCK='kaleidoscope_tavern:tomb_pickup_unlock';
const PREFIX='loaded:',KEYS=[PICKUP_AFTER,TOMB_PICKUP_UNLOCK],active=new Map();
function remaining(raw){
 if(typeof raw!=='string'||!raw.startsWith(PREFIX))return undefined;
 const value=Number(raw.slice(PREFIX.length));
 return Number.isSafeInteger(value)&&value>=0&&value<=40?value:undefined;
}
function remember(entity,key,value){
 let row=active.get(entity.id);
 if(!row){row={entity,keys:new Map()};active.set(entity.id,row);}
 row.entity=entity;row.keys.set(key,{remaining:value,tick:system.currentTick});
}
export function startPickupDelay(entity,key=PICKUP_AFTER){
 if(!KEYS.includes(key))throw Error('Unknown pickup delay owner');
 entity.setDynamicProperty(key,PREFIX+40);remember(entity,key,40);
}
function readLoaded(entity,key,raw=entity.getDynamicProperty(key)){
 if(typeof raw==='string'&&raw.startsWith('script:')){
  const deadline=Number(raw.slice(7));
  if(!Number.isSafeInteger(deadline)||deadline<0)return undefined;
  // Old session deadlines did not save elapsed loaded time. A bounded
  // conversion prevents a restarted clock from locking an item for hours;
  // time already lost while unloaded cannot be reconstructed.
  const value=Math.min(40,Math.max(0,deadline-system.currentTick));
  entity.setDynamicProperty(key,PREFIX+value);return value;
 }
 return remaining(raw);
}
function restore(entity){
 if(entity?.typeId!=='minecraft:item')return;
 const tracked=active.get(entity.id);if(tracked)tracked.entity=entity;
 for(const key of KEYS)try{
  if(tracked?.keys.has(key))continue;
  const value=readLoaded(entity,key);
  if(value>0)remember(entity,key,value);
 }catch{
  // Loading can transiently reject native access. Retain this exact key for
  // retry, rather than abandoning a saved positive countdown forever.
  remember(entity,key,null);
 }
}
function tickPickupDelays(){
 const now=system.currentTick;
 for(const [id,row]of active){
  try{if(row.entity.isValid===false){active.delete(id);continue;}}catch{active.delete(id);continue;}
  for(const [key,clock]of row.keys)try{
   let value;
   if(clock.remaining===null){
    const raw=row.entity.getDynamicProperty(key);
    value=readLoaded(row.entity,key,raw);clock.remaining=value;
    // A persisted remainder is anchored at the original load, including
    // transient read failures. A legacy deadline was just converted at now.
    if(typeof raw==='string'&&raw.startsWith('script:'))clock.tick=now;
   }else value=remaining(row.entity.getDynamicProperty(key));
   if(value===undefined||value===0){row.keys.delete(key);continue;}
   const elapsed=Math.max(0,now-clock.tick),next=Math.max(0,value-elapsed);
   // Persist each loaded tick, including expiry. The saved item never relies
   // on a session clock, unload callback or a later pickup attempt to settle.
   row.entity.setDynamicProperty(key,PREFIX+next);
   clock.remaining=next;clock.tick=now;if(next===0)row.keys.delete(key);
  }catch{
   // A valid entity can reject a transient write. Keep the unsettled clock
   // for retry instead of leaving a positive saved delay permanently inert.
  }
  if(!row.keys.size)active.delete(id);
 }
}
export function blockOverflowPickup(entity,legacyTick,key=PICKUP_AFTER){
 const stored=entity?.getDynamicProperty?.(key),value=remaining(stored);
 if(value!==undefined){
  const clock=active.get(entity.id)?.keys.get(key);
  // Pickup before-events are read-only. Account for this tick without
  // mutating native state; the writable scheduler saves the same countdown.
  return Math.max(0,value-(clock?Math.max(0,system.currentTick-clock.tick):0))>0;
 }
 if(typeof stored==='string'&&stored.startsWith('script:')){
  const deadline=Number(stored.slice(7));
  return Number.isSafeInteger(deadline)&&deadline>=0&&deadline>system.currentTick;
 }
 // Preserve each original producer's semantics for legacy numeric values.
 return Number.isSafeInteger(stored)&&stored>=0&&stored>(legacyTick??world.getAbsoluteTime());
}
export function preparePickupOverflow(entity){
 startPickupDelay(entity);
 entity.clearVelocity();entity.applyImpulse({x:0,y:.2,z:0});
}
export function delayOverflowPickup(event){if(blockOverflowPickup(event.item))event.cancel=true;}
let installed=false;
export function installPickupOverflowEvents(){
 if(installed)return;installed=true;
 world.beforeEvents.entityItemPickup.subscribe(delayOverflowPickup);
 world.afterEvents.entityLoad.subscribe(({entity})=>restore(entity));
 world.afterEvents.entityRemove.subscribe(({removedEntityId})=>active.delete(removedEntityId));
 world.afterEvents.worldLoad.subscribe(()=>{
  for(const dimension of ['overworld','nether','the_end'])try{
   for(const entity of world.getDimension(dimension).getEntities({type:'minecraft:item'}))restore(entity);
  }catch{}
 });
 system.runInterval(tickPickupDelays,1);
}
