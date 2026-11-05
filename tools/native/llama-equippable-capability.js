/** Isolated QA only: one vanilla llama, no Player or entity-definition overlay.
 * run_living_effects.py --probe tools/native/llama-equippable-capability.js
 * --offline --phases first. The selected vanilla_1.26.30 llama exposes the
 * data-layer carpet slot only in its original llama_tamed component group.
 * A data-layer component name is not proof of Script API equipment access.
 */
import {world,system,BlockVolume,EntityComponentTypes,EquipmentSlot} from '@minecraft/server';
const POSITION={x:62.5,y:300,z:2.5},TAG='kt_llama_equippable_qa';
const pause=ticks=>new Promise(resolve=>system.runTimeout(resolve,ticks));
function require(value,message){if(!value)throw Error(message);}
function itemData(item){
 if(!item)return null;
 const enchantable=item.getComponent('minecraft:enchantable'),durability=item.getComponent('minecraft:durability');
 return {typeId:item.typeId,amount:item.amount,nameTag:item.nameTag??null,lore:item.getLore(),tags:item.getTags(),
  dynamicProperties:Object.fromEntries(item.getDynamicPropertyIds().map(id=>[id,item.getDynamicProperty(id)])),
  enchantments:enchantable?.getEnchantments().map(e=>({id:e.type.id,level:e.level}))??[],
  durability:durability?{damage:durability.damage,max:durability.maxDurability}:null};
}
function inspect(entity,stage){
 require(entity?.isValid,'native llama unavailable at '+stage);
 const byEnum=entity.getComponent(EntityComponentTypes.Equippable),byId=entity.getComponent('minecraft:equippable');
 const result={stage,typeId:entity.typeId,components:entity.getAllComponents().map(c=>c.typeId).sort(),
  isTamedComponent:!!entity.getComponent('minecraft:is_tamed'),enumComponentId:EntityComponentTypes.Equippable,
  enumPresent:!!byEnum,literalPresent:!!byId,slots:[]};
 const equippable=byEnum??byId;
 if(equippable)for(const [name,slot]of Object.entries(EquipmentSlot)){
  try{result.slots.push({name,slot,containerSlotValid:equippable.getEquipmentSlot(slot).isValid,item:itemData(equippable.getEquipment(slot))});}
  catch(error){result.slots.push({name,slot,error:String(error)});}
 }
 console.warn('[KT-LLAMA-EQUIPPABLE] '+JSON.stringify(result));return result;
}
world.afterEvents.worldLoad.subscribe(()=>system.runTimeout(async()=>{
 const observations=[];let result;
 try{
  require(world.getAllPlayers().length===0,'QA requires zero Players');
  const d=world.getDimension('overworld');d.runCommand('tickingarea add circle 62 300 2 1 kt_llama_equippable_qa true');
  let loaded=false;for(let i=0;i<60&&!loaded;i++){await pause(5);try{loaded=!!d.getBlock(POSITION);}catch{}}
  require(loaded,'llama QA chunk unavailable');
  d.runCommand('gamerule doMobSpawning false');
  d.fillBlocks(new BlockVolume({x:60,y:299,z:0},{x:64,y:303,z:4}),'minecraft:glass');
  d.fillBlocks(new BlockVolume({x:61,y:300,z:1},{x:63,y:302,z:3}),'minecraft:air');
  const llama=d.spawnEntity('minecraft:llama',POSITION),id=llama.id;llama.addTag(TAG);
  observations.push(inspect(llama,'spawn'));
  // Use only this unchanged vanilla entity's existing state transitions.
  // Wild llamas do not contain the data-layer equippable group at all.
  llama.triggerEvent('minecraft:ageable_grow_up');llama.triggerEvent('minecraft:on_tame');
  observations.push(inspect(llama,'native_tamed_event'));
  await pause(5);
  const settled=world.getEntity(id),row=inspect(settled,'native_tamed_after_five_ticks');observations.push(row);
  require(row.isTamedComponent,'original native tamed group did not activate');
  let nativeCarpetSetup=null;
  if(row.enumPresent||row.literalPresent){
   try{nativeCarpetSetup=d.runCommand('replaceitem entity @e[type=minecraft:llama,tag='+TAG+',c=1] slot.armor.chest 0 minecraft:red_carpet 1');}
   catch(error){nativeCarpetSetup={error:String(error)};}
   observations.push(inspect(settled,'native_carpet_readback'));
  }
  result={kind:'done',phase:'first',players:world.getAllPlayers().length,observationOnly:true,
   unchangedVanillaDefinition:true,nativeTamedGroupActivated:true,scriptEquippableAvailable:row.enumPresent||row.literalPresent,
   nativeCarpetSetup,observations,scope:'one vanilla llama; server2.7.0; no new Player, other mob, API comparison or gameplay repair'};
 }catch(error){result={kind:'failure',phase:'first',players:world.getAllPlayers().length,error:String(error),observations};}
 console.warn('[LIVING_EFFECT_QA] '+JSON.stringify(result));
},20));
