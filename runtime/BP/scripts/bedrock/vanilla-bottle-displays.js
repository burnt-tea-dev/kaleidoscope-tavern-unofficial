import {nativeItems} from './native-item-storage.js';
import {feedback} from './break-feedback.js';
import {registerJavaBlockUseHandler} from './java-placement-router.js';
import {world,system,BlockPermutation} from '@minecraft/server';
import {registerJavaItemUseOnRoute} from './java-placement-router.js';
import {registerProtectedBreakRoute} from './protected-break-router.js';
import {planInventory,commitInventory} from '../core/inventory.js';
import {potionDisplayInput,potionIdentity,restorePotion} from './potions.js';
import {potionDisplayColor} from '../core/potions.js';
import {nativeStorageAnchor} from '../core/native-storage-anchor.js';
import {tickStorageVisuals} from './storage-visual-maintenance.js';
import {check} from '../core/util.js';
import {makeStack,hand,inventory,handSnapshot,sameHand,placementTake,safe,canWrite,canInteract,pickupOutputs,commitPickupInventory,pickupFeedback,requireBlockReach,blockAt} from './transactions.js';
import {waterSnapshot,waterAt,setWithWater,restoreWater} from './waterlogging.js';

const NS='kaleidoscope_tavern',KEY='kt:vanillaBottleDisplays/';
const POTION_BLOCK=NS+':potion_bottle',VISUAL=NS+':potion_liquid_visual',ANCHOR=NS+':potion_liquid_anchor';
const visuals=new Map();let visualCursor=0;
export const potionVisualDiagnostics={errors:[]};
function visualError(error){potionVisualDiagnostics.errors.push(String(error?.code??error));if(potionVisualDiagnostics.errors.length>8)potionVisualDiagnostics.errors.shift();}
const TARGETS=Object.freeze({'minecraft:potion':NS+':potion_bottle','minecraft:honey_bottle':NS+':honey_bottle','minecraft:dragon_breath':NS+':dragon_breath_bottle','minecraft:experience_bottle':NS+':xp_bottle'});
const VALID=new Set([NS+':potion_bottle',NS+':xp_bottle']);
export function bottleDisplayKey(block){const p=block.location,dimension=block.dimension.id;return KEY+dimension+'/'+p.x+'_'+p.y+'_'+p.z;}
function keyAt(dimension,location){return KEY+dimension.id+'/'+location.x+'_'+location.y+'_'+location.z;}
function stored(block){const raw=world.getDynamicProperty(bottleDisplayKey(block));if(raw===undefined)return undefined;check(typeof raw==='string','BOTTLE_STATE_CORRUPT');return JSON.parse(raw);}
function save(block,value){world.setDynamicProperty(bottleDisplayKey(block),value===undefined?undefined:JSON.stringify(value));}
function offset(block,face){const v={Up:[0,1,0],Down:[0,-1,0],North:[0,0,-1],South:[0,0,1],West:[-1,0,0],East:[1,0,0]}[face];check(v,'BAD_BLOCK_FACE');return {x:block.location.x+v[0],y:block.location.y+v[1],z:block.location.z+v[2]};}
function itemPayload(item){if(item.typeId==='minecraft:potion')return potionDisplayInput(item);return {item:item.typeId};}
function resultingBlock(payload){if(payload.item==='minecraft:potion'&&['minecraft:water','minecraft:empty'].includes(payload.potion?.effectId))return NS+':bottle_water';return TARGETS[payload.item];}
function restorePayload(payload){if(payload.item==='minecraft:potion')return restorePotion(payload);return makeStack(payload.item,1);}
function helpers(block){const key=bottleDisplayKey(block),p=block.location;return block.dimension.getEntities({type:VISUAL,location:{x:p.x+.5,y:p.y,z:p.z+.5},maxDistance:2}).filter(e=>e.isValid&&e.getDynamicProperty(ANCHOR)===key);}
function discardVisual(entity){visuals.delete(entity.id);if(entity.isValid)entity.remove();}
/** Cosmetic cleanup never changes the committed native inventory or its result. */
export function clearPotionBottleVisual(block){try{for(const entity of helpers(block))discardVisual(entity);}catch(error){visualError(error);}}
export function syncPotionBottleVisual(block,tracked){
 const found=helpers(block);
 if(tracked?.isValid&&tracked.typeId===VISUAL&&tracked.getDynamicProperty(ANCHOR)===bottleDisplayKey(block)&&!found.includes(tracked))found.push(tracked);
 try{
  const payload=block.typeId===POTION_BLOCK?stored(block):undefined;
  if(!payload){for(const entity of found)discardVisual(entity);return;}
  // The same strict read as pick/removal supplies the original native stack.
  // Missing adopted storage never falls back to a plausible JSON colour.
  const stack=potionDisplayRemoval(block,payload).outputs[0].stack;
  const color=potionDisplayColor(potionIdentity(stack).effectId)??0xffffff;
  found.sort((a,b)=>a.id.localeCompare(b.id));let visual=found[0];
  const p=block.location,point={x:p.x+.5,y:p.y,z:p.z+.5};
  const yaw=({north:0,east:90,south:180,west:270})[block.permutation.getState('minecraft:cardinal_direction')]??0;
  if(!visual){
   visual=block.dimension.spawnEntity(VISUAL,point,{initialRotation:yaw});found.push(visual);
   visual.setDynamicProperty(ANCHOR,bottleDisplayKey(block));visual.addTag(NS+':visual_helper');
  }
  for(const extra of found)if(extra!==visual)discardVisual(extra);
  for(const [channel,shift]of [['red',16],['green',8],['blue',0]]){
   const value=(color>>shift)&255;if(visual.getProperty('kt_art:'+channel)!==value)visual.setProperty('kt_art:'+channel,value);
  }
  const rotation=visual.getRotation(),delta=((rotation.y-yaw+180)%360+360)%360-180;
  if(Math.abs(rotation.x)>1e-4||Math.abs(delta)>1e-4)visual.setRotation({x:0,y:yaw});
  if(['x','y','z'].some(axis=>Math.abs(visual.location[axis]-point[axis])>1e-4))visual.tryTeleport(point,{checkForBlocks:false});
  visuals.set(visual.id,visual);return visual;
 }catch(error){for(const entity of found)try{discardVisual(entity);}catch{}throw error;}
}
function repairPotionBottleVisual(block,tracked){try{syncPotionBottleVisual(block,tracked);}catch(error){visualError(error);}}
export function maintainPotionBottleVisual(entity){
 if(!entity?.isValid||entity.typeId!==VISUAL)return;
 try{
  const key=entity.getDynamicProperty(ANCHOR),anchor=nativeStorageAnchor(key);
  if(!key.startsWith(KEY)||anchor.dimension!==entity.dimension.id){discardVisual(entity);return;}
  const block=blockAt(entity.dimension,anchor.position);
  if(!block)return; // Unloaded owner cells are not evidence of destruction.
  if(block.typeId!==POTION_BLOCK){discardVisual(entity);return;}
  repairPotionBottleVisual(block,entity);
 }catch(error){visualError(error);try{discardVisual(entity);}catch{}}
}
// Visit each tracked helper: a duplicate can have drifted beyond the owner's
// nearby query, so grouping by anchor would let a nearer helper starve it.
export function tickPotionBottleVisuals(){visualCursor=tickStorageVisuals(visuals,visualCursor,maintainPotionBottleVisual,128);}
export function registerVanillaBottleDisplayComponents({blockComponentRegistry}){
 blockComponentRegistry.registerCustomComponent(NS+':potion_bottle_visual',{
  onTick:({block})=>repairPotionBottleVisual(block),
  onPlace:({block})=>{const d=block.dimension,p={...block.location};system.run(()=>{const current=blockAt(d,p);if(current?.typeId===POTION_BLOCK)repairPotionBottleVisual(current);});}
 });
}
export function placeVanillaBottle(player,block,face){
 canWrite(player);requireBlockReach(player,block.dimension,block.location);if(!player.isSneaking)return false;const item=hand(player);if(!item||!TARGETS[item.typeId])return false;
 const payload=itemPayload(item),id=resultingBlock(payload);check(id,'UNSUPPORTED_BOTTLE_CONTENT');
 const pos=offset(block,face),target=blockAt(block.dimension,pos);check(target&&(target.isAir||waterAt(target)), 'SPACE_NOT_CLEAR');
 const old=waterSnapshot(target),displayKey=keyAt(block.dimension,pos),oldRaw=world.getDynamicProperty(displayKey);
 check(oldRaw===undefined,'STORAGE_CONFLICT');
 const native=id===NS+':potion_bottle'?nativeItems.plan({key:displayKey,dimension:block.dimension,position:pos,oldIds:[],nextIds:[item.typeId],incoming:item}):undefined;
 const c=inventory(player),plan=planInventory(c,player.selectedSlotIndex,placementTake(player),[],makeStack);
 const permutation=BlockPermutation.resolve(id,{'minecraft:cardinal_direction':'north'});
 commitInventory(plan,c,()=>{setWithWater(target,permutation);world.setDynamicProperty(displayKey,payload.item==='minecraft:potion'&&id===NS+':potion_bottle'?JSON.stringify(payload):undefined);native?.apply();},()=>{try{native?.rollback();}finally{restoreWater(target,old);world.setDynamicProperty(displayKey,oldRaw);}});native?.finish();
 if(id===POTION_BLOCK)repairPotionBottleVisual(target);
 try{player.dimension.playSound('random.glass',{x:pos.x+.5,y:pos.y+.5,z:pos.z+.5},{volume:1,pitch:1});}catch{}
 return true;
}
/** Also used by natural destruction/projectile impact; no default blank potion. */
export function potionDisplayRemoval(block,payload=stored(block)){
 check(payload?.item==='minecraft:potion'&&payload.potion,'POTION_STATE_MISSING');
 const plan=nativeItems.plan({key:bottleDisplayKey(block),dimension:block.dimension,position:block.location,oldIds:['minecraft:potion'],nextIds:[],give:[{id:'minecraft:potion',count:1}],legacyStacks:payload.nativeItems===1?undefined:[restorePotion(payload)],requireNative:payload.nativeItems===1});
 return {...plan,finish(){plan.finish();clearPotionBottleVisual(block);}};
}
export function takeVanillaBottle(player,block){
 canInteract(player);requireBlockReach(player,block.dimension,block.location);
 const id=block.typeId;if(!VALID.has(id))return false;
 const native=id===NS+':potion_bottle'?potionDisplayRemoval(block):undefined;
 const give=native?.outputs??[{id:'minecraft:experience_bottle',count:1}];
 const c=inventory(player),plan=planInventory(c,player.selectedSlotIndex,0,pickupOutputs(player,give),makeStack),old=waterSnapshot(block),raw=world.getDynamicProperty(bottleDisplayKey(block));
 commitPickupInventory(plan,c,player,()=>{setWithWater(block,BlockPermutation.resolve('minecraft:air'));save(block,undefined);native?.apply();},()=>{try{native?.rollback();}finally{restoreWater(block,old);world.setDynamicProperty(bottleDisplayKey(block),raw);}});native?.finish();
 pickupFeedback(player,block,plan);return true;
}
export function installVanillaBottleDisplayEvents(){
 world.afterEvents.entityLoad.subscribe(({entity})=>{if(entity.isValid&&entity.typeId===VISUAL){visuals.set(entity.id,entity);system.run(()=>maintainPotionBottleVisual(entity));}});
 system.runInterval(tickPotionBottleVisuals,20);
 registerJavaItemUseOnRoute({id:'vanilla-bottle-displays',matches:id=>Object.hasOwn(TARGETS,id),plan:({player,block,face})=>player.isSneaking?{face}:undefined,execute:({player,block,plan})=>placeVanillaBottle(player,block,plan.face)});
 registerJavaBlockUseHandler(e=>{
  if(e.cancel||!VALID.has(e.block.typeId)||handSnapshot(e.player).id)return;
  try{canInteract(e.player);requireBlockReach(e.player,e.block.dimension,e.block.location);}catch{return;}
  e.cancel=true;if(e.isFirstEvent===false)return;const player=e.player,hs=handSnapshot(player),d=e.block.dimension,p={x:e.block.location.x,y:e.block.location.y,z:e.block.location.z},id=e.block.typeId;
  system.run(()=>safe(player,()=>{sameHand(player,hs);const b=blockAt(d,p);check(b?.typeId===id,'BLOCK_CHANGED');takeVanillaBottle(player,b);}));
 });
 registerProtectedBreakRoute({id:'vanilla-bottle-displays',isBlock:b=>VALID.has(b?.typeId),recover:({player,block})=>takeVanillaBottle(player,block)});
}

/** Preserve native potion identity; never manufacture a blank potion. */
export function pickVanillaBottleItem(block){
 const id=block.typeId;
 if(id===NS+':potion_bottle'){
  const payload=stored(block);check(payload?.item==='minecraft:potion','PICK_POTION_STATE_MISMATCH');
  return potionDisplayRemoval(block,payload).outputs[0].stack;
 }
 const item=Object.keys(TARGETS).find(item=>TARGETS[item]===id);
 return item?makeStack(item,1):undefined;
}
