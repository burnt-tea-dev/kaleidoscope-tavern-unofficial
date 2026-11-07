/** Forge giveItemToPlayer overflow, without overriding minecraft:item/player definitions. */
import {world,system} from '@minecraft/server';
export const PICKUP_AFTER='kaleidoscope_tavern:pickup_after';
const PREFIX='script:',clocks=new WeakMap();
export function blockOverflowPickup(entity,legacyTick,key=PICKUP_AFTER){
 const now=system.currentTick,stored=entity?.getDynamicProperty?.(key),script=typeof stored==='string'&&stored.startsWith(PREFIX);
 if(!script){
  // Preserve the exact original clock for legacy numeric values in each owner.
  return Number.isSafeInteger(stored)&&stored>=0&&stored>(legacyTick??world.getAbsoluteTime());
 }
 const deadline=Number(stored.slice(PREFIX.length));
 if(!Number.isSafeInteger(deadline)||deadline<0)return false;
 if(!clocks.has(entity)||clocks.get(entity).deadline!==stored){
  clocks.set(entity,{tick:now,remaining:Math.max(0,deadline-now),deadline:stored});
 }
 const clock=clocks.get(entity);
 clock.remaining=Math.max(0,clock.remaining-Math.max(0,now-clock.tick));clock.tick=now;
 return clock.remaining>0;
}
export function markPickupDeadline(entity){
 const stored=entity.getDynamicProperty(PICKUP_AFTER),now=system.currentTick;
 if(typeof stored==='string'&&stored.startsWith(PREFIX))clocks.set(entity,{tick:now,remaining:Math.max(0,Number(stored.slice(PREFIX.length))-now),deadline:stored});
}
export function preparePickupOverflow(entity){
 entity.setDynamicProperty(PICKUP_AFTER,PREFIX+(system.currentTick+40));markPickupDeadline(entity);
 entity.clearVelocity();entity.applyImpulse({x:0,y:.2,z:0});
}
export function delayOverflowPickup(event){
 if(blockOverflowPickup(event.item))event.cancel=true;
}
let installed=false;
export function installPickupOverflowEvents(){if(installed)return;world.beforeEvents.entityItemPickup.subscribe(delayOverflowPickup);installed=true;}
