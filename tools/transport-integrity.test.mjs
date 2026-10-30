/** Receiver integrity only: pure source data, no world or player substitutes. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {ExtensionTransport,EVENTS,packetsFor,TRANSPORT_LIMITS} from '../runtime/BP/scripts/core/transport.js';
import {ExtensionRegistry} from '../runtime/BP/scripts/core/registry.js';
import {digest,freeze,utf8Bytes} from '../runtime/BP/scripts/core/util.js';
const source='integrity_probe';
const payload={api:1,source,version:'1.0.0',pages:[{id:source+':unicode',title:{en_US:'Probe'},body:{en_US:('葡萄🍇\ud800\u0000').repeat(180)},recipeIds:[]}]};
const error=(fn,code)=>assert.throws(fn,e=>e.code===code);
const registry=()=>new ExtensionRegistry({itemExists:()=>true,itemTags:()=>[]});
const send=(receiver,id,row,tick=0)=>receiver.receive(id,JSON.stringify(row),tick);
function frame(parts,bytes=utf8Bytes(parts.join('')),checksum=digest(parts.join(''))){
 const revision='unicode_boundary';
 return [{id:EVENTS.begin,row:{api:1,source,revision,parts:parts.length,bytes,digest:checksum}},...parts.map((data,index)=>({id:EVENTS.chunk,row:{source,revision,index,data}})),{id:EVENTS.commit,row:{source,revision}}];
}

test('ordered native-sized parts and exact duplicates preserve Unicode content and synchronous ACK',()=>{
 const r=registry(),receiver=new ExtensionTransport(r),packets=packetsFor(payload,'ordered_unicode'),initialRevision=r.revision;
 receiver.receive(packets[0].id,packets[0].message,0);
 for(const packet of packets.slice(1,-1)){
  const tx=receiver.pending.get(source),before=tx.digestParts;
  assert.equal(receiver.receive(packet.id,packet.message,1),null);
  assert(tx.digestParts-before<=2,'one chunk event advances at most two stored parts');
  assert.equal(receiver.receive(packet.id,packet.message,1),null);
 }
 const tx=receiver.pending.get(source);assert.equal(tx.digestParts,tx.parts);
 const ack=receiver.receive(packets.at(-1).id,packets.at(-1).message,2);
 assert.equal(ack.ok,true);assert.equal(ack.revision,'ordered_unicode');assert.equal(ack.registryRevision,initialRevision+1);
 assert.equal(r.allPages()[0].body.en_US,payload.pages[0].body.en_US);
 assert.equal(receiver.pending.has(source),false);
 assert.equal(send(receiver,EVENTS.unregister,{api:1,source},3).removed,true);
});

test('reverse order retains digest fallback, corruption errors and begin replacement',()=>{
 const r=registry(),receiver=new ExtensionTransport(r),packets=packetsFor(payload,'reverse_unicode'),initialRevision=r.revision;
 receiver.receive(packets[0].id,packets[0].message,0);
 for(const packet of packets.slice(1,-1).reverse())receiver.receive(packet.id,packet.message,1);
 const tx=receiver.pending.get(source);assert(tx.digestParts<tx.parts,'reverse receipt leaves a bounded prefix');
 assert.equal(receiver.receive(packets.at(-1).id,packets.at(-1).message,2).ok,true);
 assert.equal(r.allPages()[0].body.en_US,payload.pages[0].body.en_US);
 const corrupt=JSON.parse(packets[0].message);corrupt.digest=corrupt.digest==='00000000'?'ffffffff':'00000000';
 send(receiver,EVENTS.begin,corrupt,3);
 for(const packet of packets.slice(1,-1))receiver.receive(packet.id,packet.message,3);
 error(()=>receiver.receive(packets.at(-1).id,packets.at(-1).message,3),'DIGEST_MISMATCH');assert.equal(r.revision,initialRevision+1);
 receiver.receive(packets[0].id,packets[0].message,4);
 receiver.receive(packets[1].id,packets[1].message,4);
 const conflict=JSON.parse(packets[1].message);conflict.data+='x';error(()=>send(receiver,EVENTS.chunk,conflict,4),'CONFLICTING_CHUNK');
 receiver.receive(packets[0].id,packets[0].message,4);
 error(()=>receiver.receive(packets.at(-1).id,packets.at(-1).message,4),'MISSING_CHUNKS');
 const expired=6+TRANSPORT_LIMITS.pendingTicks;receiver.receive(packets[0].id,packets[0].message,5);receiver.cleanup(expired);
 error(()=>receiver.receive(packets[1].id,packets[1].message,expired),'NO_PENDING_TRANSFER');
});

test('a current extension larger than the former byte and part limits installs atomically',()=>{
 const large={api:1,source,version:'1.0.0',pages:Array.from({length:96},(_,i)=>({id:source+':page_'+i,title:{en_US:'Page '+i},body:{en_US:'x'.repeat(7000)}}))};
 const r=registry(),receiver=new ExtensionTransport(r),packets=packetsFor(large,'large_current_extension'),initialRevision=r.revision;
 assert(packets.length>514);assert(utf8Bytes(JSON.stringify(large))>262144);
 for(const packet of packets.slice(0,-1)){receiver.receive(packet.id,packet.message,0);assert.equal(r.revision,initialRevision);}
 assert.equal(receiver.receive(packets.at(-1).id,packets.at(-1).message,1).ok,true);
 assert.equal(r.allPages().length,large.pages.length);assert.equal(r.allPages().at(-1).body.en_US,large.pages.at(-1).body.en_US);
});

test('split surrogate boundaries across empty parts retain byte rejection and failed-chunk side effects',()=>{
 const raw=JSON.stringify({api:1,source,version:'1.0.0',label:'🍇'}),at=raw.indexOf('🍇');
 const parts=[raw.slice(0,at+1),'','',raw.slice(at+1)];
 assert.equal(parts.reduce((n,part)=>n+utf8Bytes(part),0),utf8Bytes(raw)+2);
 const r=registry(),receiver=new ExtensionTransport(r),sum=parts.reduce((n,part)=>n+utf8Bytes(part),0),initialRevision=r.revision;
 // Declaring the per-part sum permits all chunks, but joined UTF-8 must still reject it.
 const wrong=frame(parts,sum);
 for(const p of wrong.slice(0,-1))send(receiver,p.id,p.row);
 error(()=>send(receiver,wrong.at(-1).id,wrong.at(-1).row),'DIGEST_MISMATCH');assert.equal(r.revision,initialRevision);
 // Declaring the exact joined bytes retains the earlier original CHUNK rejection.
 const exact=frame(parts);
 for(const p of exact.slice(0,-2))send(receiver,p.id,p.row);
 error(()=>send(receiver,exact.at(-2).id,exact.at(-2).row),'PAYLOAD_TOO_LARGE');
 const tx=receiver.pending.get(source),poisoned=tx.actualBytes;assert(poisoned>tx.bytes);assert.equal(tx.partsData.has(3),false);
 error(()=>send(receiver,exact.at(-2).id,exact.at(-2).row),'PAYLOAD_TOO_LARGE');assert.equal(tx.actualBytes,poisoned+utf8Bytes(parts[3]));
 error(()=>send(receiver,exact.at(-1).id,exact.at(-1).row),'MISSING_CHUNKS');assert.equal(receiver.pending.has(source),false);assert.equal(r.revision,initialRevision);
 // Unpaired surrogate endpoints do not become a pair after joining.
 const unpaired=[raw.slice(0,at)+'\ud800','','x\udc00'+raw.slice(at+2)];
 const valid=frame(unpaired);let ack;for(const p of valid)ack=send(receiver,p.id,p.row);assert.equal(ack.ok,true);
});

test('valid parsed packets retain source and revision in rejection ACK context',()=>{
 const receiver=new ExtensionTransport(registry());
 assert.throws(()=>send(receiver,EVENTS.begin,{api:2,source,revision:'context_revision'}),error=>{
  assert.equal(error.code,'API_VERSION_MISMATCH');assert.deepEqual(error.packetContext,{source,revision:'context_revision'});return true;
 });
 assert.throws(()=>receiver.receive(EVENTS.begin,'{',0),error=>error.code==='BAD_JSON'&&error.packetContext===undefined);
 assert.throws(()=>receiver.receive(EVENTS.begin,' '.repeat(TRANSPORT_LIMITS.packetBytes+1),0),error=>error.code==='PACKET_TOO_LARGE'&&error.packetContext===undefined);
});
