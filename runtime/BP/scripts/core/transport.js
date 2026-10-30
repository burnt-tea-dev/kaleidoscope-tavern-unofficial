import {check,integer,text,utf8Bytes,digest,TavernError,prepareJson,prepareDigest,jsonCodepointBytes,finishPreparation} from './util.js';
export const EVENTS=Object.freeze({ping:'kaleidoscope_tavern:api_ping',ready:'kaleidoscope_tavern:api_ready',begin:'kaleidoscope_tavern:extension_begin',chunk:'kaleidoscope_tavern:extension_chunk',commit:'kaleidoscope_tavern:extension_commit',ack:'kaleidoscope_tavern:extension_ack',unregister:'kaleidoscope_tavern:extension_unregister'});
export const TRANSPORT_LIMITS=Object.freeze({packetBytes:1900,dataBytes:1500000,maxParts:2048,pendingTicks:2400});
const MAX_PACKET_BYTES=TRANSPORT_LIMITS.packetBytes,MAX_DATA_BYTES=TRANSPORT_LIMITS.dataBytes,TTL=TRANSPORT_LIMITS.pendingTicks;
/** FIFO generator jobs with both a clock budget and a hard per-pump step cap. */
export function createMutationQueue({generation,complete,failed,superseded,schedule,clock=()=>Date.now(),budgetMs=1,stepLimit=32}){
 const queue=[];let active=null,scheduled=false,api;
 const requestPump=()=>{if(!schedule||scheduled)return;scheduled=true;schedule(()=>{scheduled=false;api.pump();if(api.size)requestPump();});};
 api={
  enqueue(job){queue.push(job);requestPump();return true;},
  supersede(source,value){
   for(let i=queue.length-1;i>=0;i--)if(queue[i].source===source&&queue[i].generation<value){superseded(queue[i]);queue.splice(i,1);}
   if(active?.source===source&&active.generation<value)active.cancelled=true;
  },
  pump(){
   if(!active)active=queue.shift()??null;if(!active)return;
   const job=active;
   if(job.cancelled||generation(job.source)!==job.generation){superseded(job);active=null;return;}
   const started=clock();let steps=0;
   try{
    while(steps++<stepLimit&&clock()-started<budgetMs){
     if(job.cancelled||generation(job.source)!==job.generation){superseded(job);active=null;return;}
     const result=job.job.next();if(result.done){complete(job,result.value);active=null;return;}
    }
   }catch(error){failed(job,error);active=null;}
   requestPump();
  },
  get size(){return queue.length+(active?1:0);},
 };
 return api;
}
/** Complete and validate the whole transfer before emitting its begin packet. */
export function* preparePacketsFor(extension,revision,{quotedLimit=1100}={}){
 const data=yield* prepareJson(extension,{canonicalKeys:true});
 const checksum=yield* prepareDigest(data);
 if(revision===undefined)revision='r'+checksum;
 const parts=[];let start=0,bytes=0,dataBytes=0,units=0;
 for(let i=0;i<data.length;){
  const code=data.codePointAt(i),length=code>65535?2:1,unit=jsonCodepointBytes(code);
  if(bytes+unit>quotedLimit){parts.push(data.slice(start,i));start=i;bytes=0;}
  bytes+=unit;dataBytes+=code<128?1:code<2048?2:code<65536?3:4;i+=length;
  check(dataBytes<=MAX_DATA_BYTES,'PAYLOAD_TOO_LARGE');
  if((units+=length)>=2048){units=0;yield;}
 }
 if(start<data.length)parts.push(data.slice(start));
 check(parts.length<=TRANSPORT_LIMITS.maxParts,'TOO_MANY_PARTS');
 const info={api:1,source:extension.source,revision,parts:parts.length,bytes:dataBytes,digest:checksum};
 const packets=[{id:EVENTS.begin,message:JSON.stringify(info)}];
 for(let index=0;index<parts.length;index++){
  packets.push({id:EVENTS.chunk,message:JSON.stringify({source:info.source,revision,index,data:parts[index]})});yield;
 }
 packets.push({id:EVENTS.commit,message:JSON.stringify({source:info.source,revision})});
 for(const p of packets){check(utf8Bytes(p.message)<=MAX_PACKET_BYTES,'PACKET_TOO_LARGE');yield;}
 return {revision,packets};
}
export function packetsFor(extension,revision='r1'){return finishPreparation(preparePacketsFor(extension,revision,{quotedLimit:1098})).packets;}
/** Joined UTF-8 differs from per-part bytes only at nonempty surrogate boundaries. */
function joinedUtf8Bytes(parts,bytes){
 let last=0;
 for(const part of parts){
  if(!part.length)continue;
  const first=part.charCodeAt(0);
  if(last>=0xd800&&last<=0xdbff&&first>=0xdc00&&first<=0xdfff)bytes-=2;
  last=part.charCodeAt(part.length-1);
 }
 return bytes;
}
function contextualJob(job,source,revision){
 return (function*(){try{let step;do{step=job.next();if(!step.done)yield;}while(!step.done);return step.value;}catch(error){error.packetContext={source,revision};throw error;}})();
}
/** Advance only stored contiguous parts; at most 2800 UTF16 units per chunk event. */
function advanceDigest(tx){
 for(let n=0;n<2&&tx.partsData.has(tx.digestParts);n++){
  const part=tx.partsData.get(tx.digestParts++);
  for(let i=0;i<part.length;i++){tx.digestState^=part.charCodeAt(i);tx.digestState=Math.imul(tx.digestState,16777619);}
 }
}
export class ExtensionTransport {
 constructor(registry,{deferred=false}={}){this.registry=registry;this.pending=new Map();this.usedBytes=0;this.deferred=deferred;this.generations=new Map();}
 generation(source){return this.generations.get(source)??0;}
 bump(source){const value=this.generation(source)+1;this.generations.set(source,value);return value;}
 cleanup(tick){for(const[k,p]of this.pending)if(tick-p.tick>TTL)this.pending.delete(k);}
 receive(eventId,message,tick){
  this.cleanup(tick);check(typeof message==='string'&&utf8Bytes(message)<=MAX_PACKET_BYTES,'PACKET_TOO_LARGE');
  let p;try{p=JSON.parse(message);}catch{throw new TavernError('BAD_JSON');}
  try{
  check(p&&typeof p==='object','BAD_PACKET');check(typeof p.source==='string'&&/^[a-z][a-z0-9_]{1,47}$/.test(p.source),'INVALID_SOURCE');
  check(p.source!=='kaleidoscope_tavern'&&p.source!=='minecraft'&&p.source!=='kaleidoscope_cookery','RESERVED_SOURCE');
  if(eventId===EVENTS.unregister){check(p.api===1,'API_VERSION_MISMATCH');this.pending.delete(p.source);const generation=this.bump(p.source);if(this.deferred)return {mutationJob:{source:p.source,revision:p.revision,generation,operation:'remove',job:contextualJob(this.registry.prepareRemove(p.source),p.source,p.revision)}};return {ok:true,source:p.source,removed:this.registry.remove(p.source)};}
  text(p.revision,64);check(/^[a-zA-Z0-9_.-]+$/.test(p.revision),'INVALID_REVISION');
  if(eventId===EVENTS.begin){
   check(p.api===1,'API_VERSION_MISMATCH');integer(p.parts,1,TRANSPORT_LIMITS.maxParts);integer(p.bytes,2,MAX_DATA_BYTES);check(/^[0-9a-f]{8}$/.test(p.digest),'INVALID_DIGEST');
   check(this.pending.has(p.source)||this.pending.size<16,'PENDING_LIMIT');
   const generation=this.bump(p.source);this.pending.set(p.source,{...p,tick,generation,partsData:new Map(),actualBytes:0,digestParts:0,digestState:2166136261});return this.deferred?{transferStarted:{source:p.source,revision:p.revision,generation}}:null;
  }
  const tx=this.pending.get(p.source);check(tx&&tx.revision===p.revision,'NO_PENDING_TRANSFER');
  if(eventId===EVENTS.chunk){integer(p.index,0,tx.parts-1);text(p.data,1400);const old=tx.partsData.get(p.index);check(old===undefined||old===p.data,'CONFLICTING_CHUNK');
   if(old===undefined){tx.actualBytes+=utf8Bytes(p.data);check(tx.actualBytes<=tx.bytes&&tx.actualBytes<=MAX_DATA_BYTES,'PAYLOAD_TOO_LARGE');tx.partsData.set(p.index,p.data);}advanceDigest(tx);return null;
  }
  check(eventId===EVENTS.commit,'UNKNOWN_EVENT');
  try{
   check(tx.partsData.size===tx.parts,'MISSING_CHUNKS');const parts=Array.from({length:tx.parts},(_,i)=>tx.partsData.get(i)),data=parts.join('');
   check(joinedUtf8Bytes(parts,tx.actualBytes)===tx.bytes&&(tx.digestParts===tx.parts?(tx.digestState>>>0).toString(16).padStart(8,'0'):digest(data))===tx.digest,'DIGEST_MISMATCH');const raw=JSON.parse(data);check(raw.source===p.source,'SOURCE_MISMATCH');
   if(this.deferred){
    const generation=tx.generation,job=this.registry.prepareInstall(raw),source=p.source,revision=p.revision;
    return {mutationJob:{source,revision,generation,operation:'install',job:contextualJob(job,source,revision)}};
   }
   const installed=this.registry.install(raw);
   return {...installed,ok:true,registryRevision:installed.revision,revision:p.revision};
  }finally{this.pending.delete(p.source);}
  }catch(error){error.packetContext={source:p?.source,revision:p?.revision};throw error;}
 }
}
