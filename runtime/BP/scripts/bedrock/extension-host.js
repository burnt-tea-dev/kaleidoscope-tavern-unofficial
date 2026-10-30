import {system,ScriptEventSource} from '@minecraft/server';
import {ExtensionTransport,EVENTS,TRANSPORT_LIMITS,createMutationQueue} from '../core/transport.js';
import {CAPABILITIES} from '../core/registry.js';
const EVENT_IDS=new Set(Object.values(EVENTS));
export function installExtensionHost(registry){
 const transport=new ExtensionTransport(registry,{deferred:true});let countTick=-1,eventsThisTick=0;
 const send=(id,p)=>system.sendScriptEvent(id,JSON.stringify(p));
 function ackError(job,code){send(EVENTS.ack,{ok:false,source:job.source,revision:job.revision,code});}
 const jobs=createMutationQueue({generation:source=>transport.generation(source),complete(job,value){
  if(job.operation==='install')send(EVENTS.ack,{...value,ok:true,registryRevision:value.revision,revision:job.revision});
  else send(EVENTS.ack,{ok:true,source:job.source,revision:job.revision,removed:value});
 },failed(job,error){console.warn(`[Tavern Extension] ${error}`);send(EVENTS.ack,{ok:false,...error.packetContext,code:error.code??'INVALID_PACKET'});},superseded:job=>ackError(job,'TRANSFER_SUPERSEDED'),schedule:callback=>system.runTimeout(callback,1)});
 const ready=()=>send(EVENTS.ready,{api:1,version:'0.3.0',capabilities:CAPABILITIES,maxPacketBytes:TRANSPORT_LIMITS.packetBytes,maxPayloadBytes:TRANSPORT_LIMITS.dataBytes,maxParts:TRANSPORT_LIMITS.maxParts});
 system.afterEvents.scriptEventReceive.subscribe(ev=>{
  if(!EVENT_IDS.has(ev.id)||ev.id===EVENTS.ready||ev.id===EVENTS.ack)return;
  // Server-script-origin is required. Pack namespaces are cooperative, not authenticated identities.
  if(ev.sourceType!==ScriptEventSource.Server)return;
  const tick=system.currentTick;
  if(countTick!==tick){countTick=tick;eventsThisTick=0;}
  if(++eventsThisTick>256)return;
  if(ev.id===EVENTS.ping){ready();return;}
  try{
   const result=transport.receive(ev.id,ev.message,tick);
   if(result?.transferStarted)jobs.supersede(result.transferStarted.source,result.transferStarted.generation);
   if(result?.mutationJob)jobs.enqueue(result.mutationJob);
   else if(result&&!result.transferStarted)send(EVENTS.ack,result);
  }catch(error){console.warn(`[Tavern Extension] ${error}`);send(EVENTS.ack,{ok:false,...error.packetContext,code:error.code??'INVALID_PACKET'});}
 },{namespaces:['kaleidoscope_tavern']});
 system.run(ready);let broadcasts=0;const handle=system.runInterval(()=>{ready();if(++broadcasts>=5)system.clearRun(handle);},20);
 system.runInterval(()=>transport.cleanup(system.currentTick),200);
 return {registry,transport,ready};
}
