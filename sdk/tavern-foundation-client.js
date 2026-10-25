/** Pack-side transport and legacy handoff only. No cabinet rules or inventory code. */
import {packetsFor} from './protocol.js';
import {canonical,digest,utf8Bytes} from './util.js';
const NS='kaleidoscope_tavern:',effects=new Map();let clock=()=>0;
export function readTavernEffects(entity,source){
 const snapshot=effects.get(source+'/'+entity.id),result={};
 if(!snapshot||clock()-snapshot.sequence>20)return result;
 const elapsed=Math.max(0,clock()-snapshot.sequence);
 for(const row of snapshot.rows){if(row.ticks<=elapsed)continue;const name=row.id.slice(source.length+1),old=result[name];if(!old||row.amplifier>old.amplifier||row.amplifier===old.amplifier&&row.ticks>old.ticks)result[name]=row;}
 return result;
}
/** Resolve only this addon's fresh snapshot recipients, never scan the world. */
export function getTavernEffectEntities(world,source){
 const result=[];
 for(const [key,snapshot] of effects){
  if(!key.startsWith(source+'/'))continue;
  if(clock()-snapshot.sequence>20){effects.delete(key);continue;}
  try{const entity=world.getEntity(key.slice(source.length+1));if(entity&&entity.isValid!==false)result.push(entity);}catch{}
 }
 return result;
}
export function createFoundationClient(system,world,payload,ready,{log=console.warn}={}){
 const source=payload.source,definitions=new Map(payload.furniture.map(x=>[x.block,x])),queue=[],staged=new Map();
 // These are transport receipts, never cabinet contents or inventory authority.
 // A finite retry window permits the original native actor to load/recover.
 const rejected=new Map(),acknowledged=new Map();let active,seq=0,lastQueueWarning=-100;clock=()=>system.currentTick;
 const legacyKey=(def,dimension,p)=>def.legacyPrefix+dimension.split(':')[1]+'/'+p.x+'_'+p.y+'_'+p.z;
 const identity=row=>canonical(row.kind==='cabinet'?[source,row.kind,row.type,row.dimension,row.position.x,row.position.y,row.position.z]:[source,row.kind,row.entity]);
 const remember=(map,key,value)=>{map.delete(key);map.set(key,value);if(map.size>256)map.delete(map.keys().next().value);};
 const context=row=>row.kind==='cabinet'?{source,kind:row.kind,type:row.type,dimension:row.dimension,position:{...row.position}}:{source,kind:row.kind,entity:row.entity};
 function reject(entry,code){
  acknowledged.delete(entry.identity);
  const old=rejected.get(entry.identity),failures=old?.key===entry.key?old.failures+1:1;
  const delay=Math.min(600,20*2**Math.min(failures-1,5)),retryAt=system.currentTick+delay;
  remember(rejected,entry.identity,{key:entry.key,failures,retryAt,code,target:context(entry.row)});
  log('[Tavern foundation] '+JSON.stringify({...context(entry.row),code,failures,retryAt,oldDataRetained:true}));
 }
 function enqueue(row,onAck,{refresh=false}={}){
  const key=canonical(row),owner=identity(row),pending=queue.findIndex(x=>x.identity===owner);
  if(active?.key===key){if(pending>=0)queue.splice(pending,1);return;}
  if(pending>=0&&queue[pending].key===key)return;
  const failed=rejected.get(owner);
  if(failed?.key===key&&system.currentTick<failed.retryAt)return;
  if(failed&&failed.key!==key)rejected.delete(owner);
  if(row.kind==='cabinet'&&!refresh&&acknowledged.get(owner)===key)return;
  if(pending<0&&queue.length>=256){if(system.currentTick-lastQueueWarning>=100){lastQueueWarning=system.currentTick;log('[Tavern foundation] '+JSON.stringify({...context(row),code:'QUEUE_FULL',oldDataRetained:true}));}return;}
  const revision='f'+(++seq)+'_'+digest(key);
  const entry={key,identity:owner,row,revision,onAck,packets:packetsFor({...row,source},revision).map(p=>({id:p.id.replace(':extension_',':foundation_'),message:p.message})),attempts:0};
  if(pending>=0)queue[pending]=entry;else queue.push(entry);
 }
 function cabinetBlock(row){
  try{const block=world.getDimension(row.dimension).getBlock(row.position);return block&&(block.typeId===row.type||block.isAir)?block:undefined;}catch{return undefined;}
 }
 function cabinet(row,options){
  const def=definitions.get(row.type),p=row.position;
  if(!def||!['x','y','z'].every(k=>Number.isInteger(p?.[k]))||!/^minecraft:[a-z_]+$/.test(row.dimension))return;
  const block=cabinetBlock(row);if(!block)return;const dimension=block.dimension;
  const key=legacyKey(def,row.dimension,p),raw=world.getDynamicProperty(key)??null;
  enqueue({kind:'cabinet',type:row.type,dimension:row.dimension,position:p,raw},ack=>{
   if(raw!==null&&world.getDynamicProperty(key)===raw)world.setDynamicProperty(key,undefined);
   if(ack.visualReady)for(const entity of dimension.getEntities({location:{x:p.x+.5,y:p.y+.5,z:p.z+.5},maxDistance:2})){
    if(entity.typeId.startsWith(source+':cabinet_')&&entity.getDynamicProperty(source+':anchor')===key)entity.remove();
   }
  },options);
 }
 function migrateEffects(){
  if(!ready())return;
  for(const p of world.getAllPlayers()){
   const raw=p.getDynamicProperty(payload.legacyEffectKey)??null;
   // An in-memory ACK cache avoids redundant transfers. The host's persisted
   // receipt, not this cache, provides exactly-once import after reload.
   const key=source+'/'+p.id;if(effectAcks.get(key)===raw)continue;
   enqueue({kind:'effects',entity:p.id,raw},()=>{if(raw!==null&&p.getDynamicProperty(payload.legacyEffectKey)===raw)p.setDynamicProperty(payload.legacyEffectKey,undefined);effectAcks.set(key,null);});
  }
 }
 const effectAcks=new Map();
 // Entity handles may be unavailable while their chunk is loading. An observed
 // carrier at the owner cell makes a failed background read eligible now; the
 // host still verifies its exact saved ID, owner, token and native inventory.
 world.afterEvents.entityLoad?.subscribe(({entity})=>{
  if(entity?.typeId!==NS+'stored_items')return;
  system.run(()=>{
   if(!entity.isValid)return;
   for(const failed of rejected.values()){
    const row=failed.target,p=row.position;
    if(failed.code!=='NATIVE_STORAGE_UNAVAILABLE'||row.kind!=='cabinet'||entity.dimension.id!==row.dimension||!['x','y','z'].every(k=>Math.abs(entity.location[k]-p[k]-.5)<.1))continue;
    failed.retryAt=system.currentTick;cabinet(row,{refresh:true});
   }
  });
 });
 system.afterEvents.scriptEventReceive.subscribe(ev=>{
  // Other Tavern channels include large extension transfers; they cannot affect
  // foundation state and must not pay its byte scan or JSON parse.
  if(ev.id!==NS+'foundation_request'&&ev.id!==NS+'foundation_ack'&&ev.id!==NS+'effect_snapshot')return;
  if(ev.sourceType!=='Server'||utf8Bytes(ev.message)>1900)return;
  try{
   const row=JSON.parse(ev.message);if(row.source!==source)return;
   if(ev.id===NS+'foundation_request'&&row.kind==='cabinet'){cabinet(row,{refresh:true});return;}
   if(ev.id===NS+'foundation_ack'){
    if(!active||row.revision!==active.revision)return;
    const entry=active;
    if(row.ok){entry.onAck?.(row);rejected.delete(entry.identity);if(entry.row.kind==='cabinet')remember(acknowledged,entry.identity,entry.key);active=undefined;}
    else{active=undefined;reject(entry,row.code??'INVALID_PACKET');}return;
   }
   if(ev.id!==NS+'effect_snapshot')return;
   if(typeof row.entity!=='string'||!Number.isInteger(row.sequence)||!Number.isInteger(row.parts)||row.parts<1||row.parts>8||!Number.isInteger(row.part)||row.part<0||row.part>=row.parts||!Array.isArray(row.rows)||row.rows.length>32)return;
   if(row.rows.some(x=>typeof x.id!=='string'||!x.id.startsWith(source+':')||!Number.isInteger(x.ticks)||x.ticks<1||x.ticks>20000000||!Number.isInteger(x.amplifier)||x.amplifier<0||x.amplifier>255))return;
   const key=source+'/'+row.entity;if((effects.get(key)?.sequence??-1)>row.sequence)return;
   let state=staged.get(key);if(!state||row.sequence>state.sequence){state={sequence:row.sequence,total:row.parts,parts:new Map()};staged.set(key,state);}
   if(state.sequence!==row.sequence||state.total!==row.parts)return;state.parts.set(row.part,row.rows);
   if(state.parts.size===state.total){const rows=Array.from({length:state.total},(_,i)=>state.parts.get(i)).flat();if(rows.length<=32)effects.set(key,{sequence:row.sequence,rows});staged.delete(key);}
  }catch(e){log('[Tavern foundation] '+e+'; old data retained');}
 },{namespaces:['kaleidoscope_tavern']});
 system.runInterval(()=>{
  if(!ready())return;
  if(!active)active=queue.shift();if(!active)return;
  if(active.sentAt!==undefined){if(system.currentTick-active.sentAt<100)return;if(active.attempts>=3){const entry=active;active=undefined;reject(entry,'ACK_TIMEOUT');return;}active.index=0;active.sentAt=undefined;}
  // A queued snapshot may outlive its loaded owner. Check only when sending,
  // not on every idle tick while an ACK is in flight.
  if(active.row.kind==='cabinet'&&!cabinetBlock(active.row)){active=undefined;return;}
  if(!active.index)active.attempts++;
  for(let n=0;n<4&&(active.index??0)<active.packets.length;n++){const packet=active.packets[active.index??0];system.sendScriptEvent(packet.id,packet.message);active.index=(active.index??0)+1;}
  if(active.index===active.packets.length)active.sentAt=system.currentTick;
 },1);
 system.runInterval(migrateEffects,20);
 const clear=p=>{effects.delete(source+'/'+p.id);staged.delete(source+'/'+p.id);p.setDynamicProperty(payload.legacyEffectKey,undefined);};
 world.afterEvents.itemCompleteUse.subscribe(e=>{if(e.itemStack?.typeId==='minecraft:milk_bucket')clear(e.source);});
 world.afterEvents.entityDie.subscribe(e=>{const entity=e.deadEntity;if(!entity?.id)return;effects.delete(source+'/'+entity.id);staged.delete(source+'/'+entity.id);if(entity.typeId==='minecraft:player')clear(entity);});
 world.afterEvents.entityRemove?.subscribe(e=>{effects.delete(source+'/'+e.removedEntityId);staged.delete(source+'/'+e.removedEntityId);});
 world.afterEvents.playerLeave.subscribe(e=>{const key=source+'/'+e.playerId;effects.delete(key);staged.delete(key);effectAcks.delete(key);});
 system.runInterval(()=>{for(const [key,state] of staged)if(system.currentTick-state.sequence>20)staged.delete(key);},20);
 return {cabinet,enqueue,migrateEffects,read:entity=>readTavernEffects(entity,source),nativeUse(e){if(e.player&&ready())system.sendScriptEvent(NS+'foundation_native_use',JSON.stringify({source,kind:'native_use',tick:system.currentTick,slot:e.player.selectedSlotIndex,type:e.block.typeId,dimension:e.block.dimension.id,position:e.block.location,entity:e.player.id,face:String(e.face??e.blockFace),faceLocation:e.faceLocation}));}};
}
