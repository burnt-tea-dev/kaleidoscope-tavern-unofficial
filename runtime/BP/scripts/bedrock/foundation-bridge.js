/** Cross-pack bridge: dynamic properties are pack-scoped, not a shared database.
 * Reuses extension chunk framing and validation. Server source is cooperative,
 * not authentication between trusted addons.
 */
import {world,system,ScriptEventSource} from '@minecraft/server';
import {ExtensionTransport,EVENTS} from '../core/transport.js';
import {check,utf8Bytes,canonical} from '../core/util.js';
import {externalEffectMigrations} from '../core/extension-content.js';
import {importExternalEffects,statusNow,effectSnapshotEntities} from './custom-effects.js';
const PREFIX='kaleidoscope_tavern:',ACK=PREFIX+'foundation_ack';
const incoming=new Map(['begin','chunk','commit'].map(k=>[PREFIX+'foundation_'+k,EVENTS[k]]));
export function installFoundationBridge(registry,furniture){
 let tick=-1,count=0,failedImport;const snapshotCache=new Map(),warnings=new Map();
 const diagnostics={failures:0,suppressedWarnings:0,errors:[]};
 const importContext=row=>row.kind==='cabinet'?{source:row.source,kind:row.kind,type:row.type,dimension:row.dimension,position:{...row.position}}:{source:row.source,kind:row.kind,entity:row.entity};
 function warn(error,packet){
  const context=failedImport??{source:packet?.source},code=error.code??String(error),key=canonical([context,code]),now=system.currentTick;
  const previous=warnings.get(key),repeats=(previous?.repeats??0)+1;
  diagnostics.failures++;diagnostics.errors.push({...context,code,tick:now,repeats});if(diagnostics.errors.length>16)diagnostics.errors.shift();
  if(previous&&now-previous.tick<100){previous.repeats=repeats;diagnostics.suppressedWarnings++;return;}
  warnings.delete(key);warnings.set(key,{tick:now,repeats});if(warnings.size>128)warnings.delete(warnings.keys().next().value);
  console.warn('[Tavern foundation] '+JSON.stringify({...context,code,repeats,oldDataRetained:true}));
 }
 const transport=new ExtensionTransport({install(row){
  try{
  check(registry.extensions.has(row.source),'EXTENSION_NOT_READY');check(utf8Bytes(JSON.stringify(row))<=8192,'FOUNDATION_PAYLOAD_LIMIT');
  if(row.kind==='cabinet')return furniture.importSnapshot(row);
  if(row.kind==='native_use'){furniture.nativeUse(row);return {kind:row.kind};}
  check(row.kind==='effects','UNKNOWN_FOUNDATION_KIND');
  const def=externalEffectMigrations().find(x=>x.source===row.source);check(def,'EFFECT_MIGRATION_NOT_REGISTERED');
  const p=world.getEntity(row.entity);check(p?.typeId==='minecraft:player','PLAYER_UNAVAILABLE');
  importExternalEffects(p,row.source,row.raw,def.effects);return {kind:'effects',entity:row.entity};
  }catch(error){failedImport=importContext(row);throw error;}
 }});
 system.afterEvents.scriptEventReceive.subscribe(ev=>{
  const id=incoming.get(ev.id),native=ev.id===PREFIX+'foundation_native_use';if((!id&&!native)||ev.sourceType!==ScriptEventSource.Server)return;
  if(tick!==system.currentTick){tick=system.currentTick;count=0;}if(++count>256)return;
  let packet;failedImport=undefined;
  try{check(utf8Bytes(ev.message)<=1900,'PACKET_TOO_LARGE');packet=JSON.parse(ev.message);if(native){furniture.nativeUse(packet);return;}const result=transport.receive(id,ev.message,system.currentTick);if(result)system.sendScriptEvent(ACK,JSON.stringify({...result,source:packet.source}));}
  catch(e){warn(e,packet);if(packet?.source&&packet?.revision)system.sendScriptEvent(ACK,JSON.stringify({source:packet.source,revision:packet.revision,ok:false,code:e.code??'INVALID_PACKET'}));}
 },{namespaces:['kaleidoscope_tavern']});
 // Authoritative, read-only snapshots; no addon reaches into another pack's DP.
 const publish=()=>{
  const seen=new Set();
  const definitions=externalEffectMigrations();
  // No registered consumer needs a world/recipient scan. Old entries still
  // take the revocation path below if a descriptor was removed.
  for(const p of definitions.length?effectSnapshotEntities():[]){
   let state;
   try{state=statusNow(p);}catch(e){console.warn('[Tavern effect snapshot] '+e);continue;}
   for(const def of definitions)try{
   const key=def.source+'/'+p.id;seen.add(key);const rows=state.entries.filter(x=>x.id.startsWith(def.source+':'));
   const data=canonical(rows),old=snapshotCache.get(key);
   // Empty state has no effect lease to renew. Keep one initial/transition
   // clear; active rows retain the existing timing and heartbeat window.
   if(old?.data===data&&(!rows.length||system.currentTick-old.tick<10))continue;
   const groups=[];let group=[];
   for(const row of rows){if(utf8Bytes(JSON.stringify([...group,row]))>1400){groups.push(group);group=[];}group.push(row);}
   groups.push(group);
   groups.forEach((rows,part)=>system.sendScriptEvent(PREFIX+'effect_snapshot',JSON.stringify({source:def.source,entity:p.id,sequence:system.currentTick,part,parts:groups.length,rows})));
   // A rejected send must not cache a clear that no consumer received.
   snapshotCache.set(key,{data,tick:system.currentTick});
  }catch(e){console.warn('[Tavern effect snapshot] '+e);}
  }
  for(const key of snapshotCache.keys())if(!seen.has(key)){
   if(snapshotCache.get(key).data==='[]'){snapshotCache.delete(key);continue;}
   // A cleared/unloaded nonplayer no longer occurs in the active track index.
   // Revoke its prior rows explicitly rather than leaving a 20-tick cached buff.
   const split=key.indexOf('/');
   system.sendScriptEvent(PREFIX+'effect_snapshot',JSON.stringify({source:key.slice(0,split),entity:key.slice(split+1),sequence:system.currentTick,part:0,parts:1,rows:[]}));
   snapshotCache.delete(key);
  }
 };
 system.runInterval(publish,5);system.runInterval(()=>transport.cleanup(system.currentTick),200);
 return {transport,publish,diagnostics};
}
