/** Two real native potion fixtures in the existing paired first/restart world.
 * Native block/storage setup is observer input, not a Player interaction. Only
 * the production block tick creates/repairs the liquid; this never calls sync.
 * RGB properties are API evidence, not client-rendered colour acceptance.
 */
import {world,system,Potions,BlockPermutation,ItemLockMode} from '@minecraft/server';
import {canonical} from './core/util.js';
import {NATIVE_ITEM_ENTITY,NATIVE_STORAGE_OWNER,nativeItemKey} from './core/native-item-storage.js';
import {nativeItems} from './bedrock/native-item-storage.js';
import {potionCapabilities,potionDisplayInput,potionIdentity} from './bedrock/potions.js';
import {bottleDisplayKey,pickVanillaBottleItem,potionDisplayRemoval} from './bedrock/vanilla-bottle-displays.js';

const NS='kaleidoscope_tavern:',VISUAL=NS+'potion_liquid_visual',ANCHOR=NS+'potion_liquid_anchor';
const SAVED='qa:potion_visual_fixture',pause=ticks=>new Promise(resolve=>system.runTimeout(resolve,ticks));
const check=(ok,message)=>{if(!ok)throw Error(message);};
// Independent original-JVM vectors in data/java-parity/potion-colors.json.
// These expected values deliberately do not call potionDisplayColor().
const CASES=[
 {effectId:'minecraft:healing',rgb:0xf82423,position:{x:16,y:300,z:4},facing:'north',yaw:0},
 {effectId:'minecraft:poison',rgb:0x87a363,position:{x:20,y:300,z:4},facing:'east',yaw:90}
];
function shape(item){
 return {typeId:item.typeId,amount:item.amount,nameTag:item.nameTag,rawLore:item.getRawLore(),
  canDestroy:item.getCanDestroy(),canPlaceOn:item.getCanPlaceOn(),keepOnDeath:item.keepOnDeath,lockMode:item.lockMode,
  properties:Object.fromEntries(item.getDynamicPropertyIds().sort().map(id=>[id,item.getDynamicProperty(id)])),potion:potionIdentity(item)};
}
function helpers(block){return block.dimension.getEntities({type:VISUAL,location:block.location,maxDistance:2}).filter(e=>e.getDynamicProperty(ANCHOR)===bottleDisplayKey(block));}
async function loadedBlock(dimension,position){
 for(let waited=0;waited<=300;waited+=5){
  try{const block=dimension.getBlock(position);if(block?.typeId)return block;}catch{}
  if(waited<300)await pause(5);
 }
 throw Error('potion fixture cell is outside loaded parent scene: '+JSON.stringify(position));
}
function helperShape(entity){
 const rgb=['red','green','blue'].map(channel=>entity.getProperty('kt_art:'+channel));
 check(rgb.every(value=>Number.isInteger(value)&&value>=0&&value<=255),'invalid native liquid RGB properties');
 return {id:entity.id,type:entity.typeId,anchor:entity.getDynamicProperty(ANCHOR),rgb:(rgb[0]<<16)|(rgb[1]<<8)|rgb[2],
  position:{...entity.location},rotation:entity.getRotation(),inventory:!!entity.getComponent('minecraft:inventory')};
}
async function liquid(block,row){
 let waitedTicks=0;
 while(waitedTicks<=80){
  const found=helpers(block);
  if(found.length===1){
   const observed=helperShape(found[0]),point={x:row.position.x+.5,y:row.position.y,z:row.position.z+.5};
   if(observed.rgb===row.rgb&&['x','y','z'].every(k=>Math.abs(observed.position[k]-point[k])<1e-4)&&
      Math.abs(observed.rotation.x)<1e-4&&Math.abs(observed.rotation.y-row.yaw)<1e-4){
    check(!observed.inventory,'cosmetic helper exposes another inventory');return {helper:observed,helperCount:found.length,waitedTicks};
   }
  }
  if(waitedTicks===80)break;await pause(5);waitedTicks+=5;
 }
 throw Error('production liquid tick did not produce one correctly coloured/positioned helper: '+JSON.stringify({ownerKey:bottleDisplayKey(block),expectedRGB:row.rgb,observed:helpers(block).map(helperShape)}));
}
function registry(phase,out){
 const currentPotionEffectTypes=Potions.getAllEffectTypes().map(effect=>effect.id).sort(),cap=potionCapabilities();
 check(!cap.error&&currentPotionEffectTypes.length>0,'current native potion registry unavailable');
 const mappedDisplayEffects=cap.mappedDisplayEffects.slice().sort(),unmappedDisplayEffects=cap.unmappedDisplayEffects.slice().sort();
 check(canonical([...mappedDisplayEffects,...unmappedDisplayEffects].sort())===canonical(currentPotionEffectTypes),'potion display coverage does not partition current native registry');
 for(const row of CASES)check(mappedDisplayEffects.includes(row.effectId),'required native fixture potion unavailable: '+row.effectId);
 out('case',{mode:'native-potion-registry',phase,currentPotionEffectTypes,mappedDisplayEffects,unmappedDisplayEffects,
  deliveryTypes:cap.deliveryTypes.slice().sort(),playerUse:false,client:false});
}
function create(block,row,index){
 const key=bottleDisplayKey(block);check(world.getDynamicProperty(key)===undefined&&world.getDynamicProperty(nativeItemKey(key))===undefined,'stale native potion fixture');
 const item=Potions.resolve(Potions.getEffectType(row.effectId),Potions.getDeliveryType('Consume'));
 item.nameTag='Native liquid '+row.effectId;item.setLore([{text:'Retain potion metadata '+index}]);
 item.setDynamicProperty('potion_probe:payload','original stack '+index);item.keepOnDeath=true;
 item.setCanDestroy(['minecraft:stone']);item.setCanPlaceOn(['minecraft:glass']);item.lockMode=index===0?ItemLockMode.inventory:ItemLockMode.slot;
 const expected=shape(item),payload=potionDisplayInput(item);
 // Both JSON identities intentionally disagree with their native ItemStacks.
 // Correct colour and readonly pick must follow the original native carrier.
 payload.potion.effectId=CASES[1-index].effectId;
 block.setPermutation(BlockPermutation.resolve(NS+'potion_bottle',{'minecraft:cardinal_direction':row.facing}));
 const plan=nativeItems.plan({key,dimension:block.dimension,position:block.location,oldIds:[],nextIds:[item.typeId],incoming:item});
 try{world.setDynamicProperty(key,JSON.stringify(payload));plan.apply();}catch(error){try{plan.rollback();}finally{world.setDynamicProperty(key,undefined);}throw error;}plan.finish();
 const stored=nativeItems.readAdopted({key,dimension:block.dimension,position:block.location});
 check(stored&&canonical(shape(stored.items[0]))===canonical(expected),'native potion fixture changed on insertion');
 return {expected,carrier:stored.record.entity,raw:stored.raw,payload:world.getDynamicProperty(key)};
}
export async function runPotionBottleProbe({phase,dimension,container,out}){
 check(phase==='first'||phase==='restart','unknown potion probe phase');registry(phase,out);
 let saved;
 if(phase==='first'){
  check(world.getDynamicProperty(SAVED)===undefined,'potion fixture already exists on first start');
  saved={schema:1,id:'native-potion-'+world.getAbsoluteTime(),rows:[]};
 }else{
  const raw=world.getDynamicProperty(SAVED);check(typeof raw==='string','same-world potion fixture did not persist');saved=JSON.parse(raw);
  check(saved.schema===1&&typeof saved.id==='string'&&saved.rows?.length===2,'saved potion fixture is invalid');
 }
 for(const [index,row]of CASES.entries()){
  const block=await loadedBlock(dimension,row.position);
  if(phase==='first')saved.rows.push(create(block,row,index));
  const expected=saved.rows[index],key=bottleDisplayKey(block);
  check(block.typeId===NS+'potion_bottle'&&block.permutation.getState('minecraft:cardinal_direction')===row.facing,'saved potion block/rotation was lost');
  const readback=await liquid(block,row),stored=nativeItems.readAdopted({key,dimension,position:row.position});
  check(stored&&stored.record.entity===expected.carrier&&stored.raw===expected.raw,'saved native potion carrier/ledger was replaced');
  check(canonical(shape(stored.items[0]))===canonical(expected.expected),'native potion metadata changed across normal reload');
  check(world.getDynamicProperty(key)===expected.payload,'native authority check rewrote stale display JSON');
  const picked=pickVanillaBottleItem(block);
  check(canonical(shape(picked))===canonical(expected.expected),'readonly pick did not return original native potion');
  check(world.getDynamicProperty(nativeItemKey(key))===expected.raw&&world.getDynamicProperty(key)===expected.payload,'readonly pick changed native/display state');
  const nativeCarrierCount=dimension.getEntities({type:NATIVE_ITEM_ENTITY,location:row.position,maxDistance:2}).filter(e=>e.getDynamicProperty(NATIVE_STORAGE_OWNER)===key).length;
  check(nativeCarrierCount===1,'duplicate native potion carrier');
  out('case',{mode:'native-potion-liquid',phase,fixtureId:saved.id,slot:index,position:row.position,facing:row.facing,ownerKey:key,
   displayPayload:JSON.parse(expected.payload),nativeCarrier:stored.record.entity,nativeRecord:JSON.parse(stored.raw),
   nativeStack:shape(stored.items[0]),pickedStack:shape(picked),nativeCarrierCount,...readback,playerUse:false,client:false});
  if(phase==='restart'){
   const plan=potionDisplayRemoval(block),slot=18+index;
   check(container.getItem(slot)===undefined,'potion recovery receipt slot is occupied');
   check(plan.outputs.length===1&&canonical(shape(plan.outputs[0].stack))===canonical(expected.expected),'potion removal lost native authority');
   const permutation=block.permutation;
   try{plan.apply();container.setItem(slot,plan.outputs[0].stack);world.setDynamicProperty(key,undefined);block.setType('minecraft:air');}
   catch(error){try{container.setItem(slot,undefined);plan.rollback();}finally{world.setDynamicProperty(key,expected.payload);block.setPermutation(permutation);}throw error;}plan.finish();
   await pause(1);
   const result={fixtureId:saved.id,slot:index,ownerKey:key,nativeCarrier:stored.record.entity,helperId:readback.helper.id,
    recoveredSlot:slot,recoveredStack:shape(container.getItem(slot)),ledgerGone:world.getDynamicProperty(nativeItemKey(key))===undefined,
    nativeRequiredGone:nativeItems.readAdopted({key,dimension,position:row.position})===undefined,
    carrierGone:world.getEntity(stored.record.entity)?.isValid!==true,helperGone:world.getEntity(readback.helper.id)?.isValid!==true,
    nearbyHelpers:helpers(block).length,remainingNativeCarriers:dimension.getEntities({type:NATIVE_ITEM_ENTITY,location:row.position,maxDistance:2}).filter(e=>e.getDynamicProperty(NATIVE_STORAGE_OWNER)===key).length,
    blockType:block.typeId,displayPayloadGone:world.getDynamicProperty(key)===undefined,playerUse:false,client:false};
   check(canonical(result.recoveredStack)===canonical(expected.expected)&&result.ledgerGone&&result.nativeRequiredGone&&result.carrierGone&&result.helperGone&&
    result.nearbyHelpers===0&&result.remainingNativeCarriers===0&&result.blockType==='minecraft:air'&&result.displayPayloadGone,'native potion cleanup/readback failed '+JSON.stringify(result));
   out('case',{mode:'native-potion-cleanup',phase,...result});
  }
 }
 if(phase==='first')world.setDynamicProperty(SAVED,JSON.stringify(saved));
}
