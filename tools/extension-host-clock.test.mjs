import test from 'node:test';
import assert from 'node:assert/strict';
import {system,ScriptEventSource} from '@minecraft/server';
import {ExtensionRegistry} from '../runtime/BP/scripts/core/registry.js';
import {ExtensionTransport,EVENTS,TRANSPORT_LIMITS,packetsFor} from '../runtime/BP/scripts/core/transport.js';
import {installExtensionHost} from '../runtime/BP/scripts/bedrock/extension-host.js';

test('host snapshots one tick per server event and preserves per-tick limit and TTL boundary',()=>{
 const tickDescriptor=Object.getOwnPropertyDescriptor(system,'currentTick'),sendScriptEvent=system.sendScriptEvent;
 let tick=100,reads=0;const sent=[];
 Object.defineProperty(system,'currentTick',{configurable:true,enumerable:true,get(){reads++;return tick;},set(value){tick=value;}});
 system.sendScriptEvent=(id,message)=>sent.push({id,message});
 try{
  const {transport}=installExtensionHost(new ExtensionRegistry());reads=0;
  system.afterEvents.scriptEventReceive.emit({id:EVENTS.ping,message:'{}',sourceType:'Entity'});
  system.afterEvents.scriptEventReceive.emit({id:'kaleidoscope_tavern:unknown',message:'{}',sourceType:ScriptEventSource.Server});
  assert.equal(reads,0,'rejected source/event filters do not read the clock');

  for(let i=0;i<257;i++)system.afterEvents.scriptEventReceive.emit({id:EVENTS.ping,message:'{}',sourceType:ScriptEventSource.Server});
  assert.equal(reads,257,'each matching server event reads currentTick once');
  assert.equal(sent.filter(row=>row.id===EVENTS.ready).length,256,'the 257th same-tick event remains capped');
  tick=101;system.afterEvents.scriptEventReceive.emit({id:EVENTS.ping,message:'{}',sourceType:ScriptEventSource.Server});
  assert.equal(reads,258);assert.equal(sent.filter(row=>row.id===EVENTS.ready).length,257,'a new tick resets the event cap');

  const raw={api:1,source:'clock_probe',version:'1.0.0',label:'ttl boundary'},packets=packetsFor(raw,'clock_revision');
  tick=200;system.afterEvents.scriptEventReceive.emit({id:EVENTS.begin,message:packets[0].message,sourceType:ScriptEventSource.Server});
  assert.equal(transport.pending.get('clock_probe').tick,200);
  tick=200+TRANSPORT_LIMITS.pendingTicks;
  system.afterEvents.scriptEventReceive.emit({id:packets[1].id,message:packets[1].message,sourceType:ScriptEventSource.Server});
  assert.equal(transport.pending.get('clock_probe').partsData.size,1,'the exact TTL boundary remains valid');
  tick++;
  system.afterEvents.scriptEventReceive.emit({id:packets.at(-1).id,message:packets.at(-1).message,sourceType:ScriptEventSource.Server});
  assert.equal(transport.pending.has('clock_probe'),false,'the transfer expires one tick after the TTL boundary');
  const ack=JSON.parse(sent.filter(row=>row.id===EVENTS.ack).at(-1).message);assert.equal(ack.code,'NO_PENDING_TRANSFER');
  assert.equal(reads,261,'begin, boundary chunk and expired commit each use one consistent tick snapshot');
 }finally{
  system.sendScriptEvent=sendScriptEvent;
  if(tickDescriptor)Object.defineProperty(system,'currentTick',tickDescriptor);else delete system.currentTick;
 }
});
