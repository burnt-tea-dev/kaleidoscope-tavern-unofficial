/** Callback replay of the unchanged observer module and real foundation SDK.
 * Native events, player handles, time and W registration are fixture boundaries.
 * This is source regression evidence, never a Native session PASS.
 * Run: node --experimental-vm-modules --test tools/native/foundation-recipient-session/observer.test.mjs
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const SOURCE='kaleidoscope_world_liquor';
const NAMES=['qaNetPlain','qaNetHeavy'];

async function fixture(){
 const players=[],logs=[],pending=[],intervals=[],sdkReads=[];
 const signal=()=>{const callbacks=[];return {subscribe:fn=>callbacks.push(fn),emit:event=>{for(const fn of callbacks)fn(event);}};};
 const afterEvents=Object.fromEntries(['playerSpawn','playerLeave','itemCompleteUse','entityDie','entityRemove','entityLoad'].map(name=>[name,signal()]));
 const scriptEventReceive=signal();
 const world={afterEvents,getAllPlayers:()=>players.slice(),getEntity:id=>players.find(p=>p.id===id)};
 const system={currentTick:0,afterEvents:{scriptEventReceive},run:fn=>pending.push(fn),
  runInterval:(fn,period)=>intervals.push({fn,period,next:system.currentTick+period}),sendScriptEvent(){}};
 const context=vm.createContext({console:{log:line=>logs.push(line)},JSON,Map,Set,Math,Uint8Array});
 const modules=new Map();
 function load(url){
  if(!modules.has(url.href))modules.set(url.href,new vm.SourceTextModule(fs.readFileSync(url,'utf8'),{context,identifier:url.href}));
  return modules.get(url.href);
 }
 const sdk=load(new URL('../../../sdk/tavern-foundation-client.js',import.meta.url));
 await sdk.link((specifier,from)=>load(new URL(specifier,from.identifier)));
 await sdk.evaluate();
 sdk.namespace.createFoundationClient(system,world,{source:SOURCE,furniture:[],legacyEffectKey:SOURCE+':effects'},()=>true,{log(){}});
 function boundary(name,values){
  return new vm.SyntheticModule(Object.keys(values),function(){for(const [key,value] of Object.entries(values))this.setExport(key,value);},{context,identifier:name});
 }
 const dependencies={
  './main.js':boundary('W registration fixture',{}),
  '@minecraft/server':boundary('Native fixture',{world,system,ScriptEventSource:{Server:'Server'}}),
  './foundation.js':boundary('W readiness fixture',{foundationReady:()=>true}),
  './sdk/tavern-foundation-client.js':boundary('Actual SDK exports',{
   readTavernEffects(entity,source){sdkReads.push({id:entity.id,tick:system.currentTick});return sdk.namespace.readTavernEffects(entity,source);},
   getTavernEffectEntities:sdk.namespace.getTavernEffectEntities,
  }),
 };
 const observer=load(new URL('./observer.js',import.meta.url));
 await observer.link(specifier=>{assert.ok(dependencies[specifier],specifier);return dependencies[specifier];});
 await observer.evaluate();
 function advance(target){
  while(system.currentTick<target){
   system.currentTick++;
   for(const fn of pending.splice(0))fn();
   for(const task of intervals)if(system.currentTick>=task.next){task.next+=task.period;task.fn();}
  }
 }
 const event=(id,message)=>scriptEventReceive.emit({sourceType:'Server',id,message:JSON.stringify(message)});
 return {system,world,logs,sdkReads,advance,
  begin(){event('tavern_qa:session_begin',{});advance(1);},
  join(ids){
   const handles=NAMES.map((name,index)=>({name,id:ids[index],isValid:true,getDynamicProperty(){},setDynamicProperty(){}}));
   players.push(...handles);
   for(const player of handles)afterEvents.playerSpawn.emit({player,initialSpawn:true});
   return handles;
  },
  empty(handles){for(const player of handles)event('kaleidoscope_tavern:effect_snapshot',
   {source:SOURCE,entity:player.id,sequence:system.currentTick,part:0,parts:1,rows:[]});},
  leave(handles){for(const player of handles){players.splice(players.indexOf(player),1);afterEvents.playerLeave.emit({playerId:player.id});}},
  marker(name){const line=logs.find(line=>line.startsWith(name+' '));return line&&JSON.parse(line.slice(name.length+1));},
 };
}

async function replay({differentIds=false,crossPublish=false}={}){
 const f=await fixture();f.begin();
 assert.ok(f.marker('TAVERN_QA_SESSION_LOGIN_READY'));
 f.advance(2);const first=f.join(['plain-1','heavy-1']);
 f.advance(5);f.empty(first);f.advance(15);
 assert.equal(f.marker('TAVERN_QA_SESSION_DISCONNECT_READY').session,1);
 f.advance(16);f.leave(first);f.advance(17);
 assert.ok(f.marker('TAVERN_QA_SESSION_RECONNECT_READY'));
 f.advance(crossPublish?27:17);
 const second=f.join(differentIds?['plain-2','heavy-2']:['plain-1','heavy-1']);
 const snapshotTick=crossPublish?30:20;f.advance(snapshotTick);f.empty(second);f.advance(snapshotTick+10);
 const secondDisconnect=f.logs.some(line=>line.startsWith('TAVERN_QA_SESSION_DISCONNECT_READY ')&&JSON.parse(line.slice(line.indexOf(' ')+1)).session===2);
 f.advance(snapshotTick+11);f.leave(second);f.advance(snapshotTick+12);
 // A broken observer may never reach its second-leave phase. Keep its actual
 // timeout output so red evidence exposes the ignored second snapshot/leave.
 if(!f.marker('TAVERN_QA_SESSION_RESULT'))f.advance(1700);
 const result=f.marker('TAVERN_QA_SESSION_RESULT');assert.ok(result);
 return {f,result,secondDisconnect,snapshotTick};
}

function checkSecondSession({f,result,secondDisconnect,snapshotTick}){
 const second=result.sessions.filter(row=>row.session===2);
 assert.deepEqual({
  secondDisconnect,emptyCounts:second.map(row=>row.emptyCount),
  sdkAccepted:second.map(row=>row.sdkAccepted),idleChecked:second.map(row=>row.idleChecked),
  leaveTicks:second.map(row=>row.leaveTick),
  sdkReads:f.sdkReads.filter(row=>row.tick===snapshotTick+1).length,
  secondLeaves:result.events.filter(row=>row.kind==='leave'&&row.session===2).length,
 },{secondDisconnect:true,emptyCounts:[1,1],sdkAccepted:[true,true],idleChecked:[true,true],
  leaveTicks:[snapshotTick+11,snapshotTick+11],sdkReads:2,secondLeaves:2});
 assert.equal(result.controls,true);assert.equal(result.playersAfter,0);assert.deepEqual(result.issues,[]);
 assert.deepEqual(result.sessions.filter(row=>row.session===1).map(row=>row.leaveTick),[16,16]);
}

test('callback fixture: second session counts empty/SDK receipt and its own native leave',async()=>{
 const replayed=await replay();checkSecondSession(replayed);
 assert.ok(replayed.result.sessions.filter(row=>row.session===2).every(row=>row.sameId&&row.newHandle&&row.betweenPublishes));
 assert.equal(replayed.result.status,'pass');
});
test('callback fixture: different IDs keep controls valid and the result inconclusive',async()=>{
 const replayed=await replay({differentIds:true});checkSecondSession(replayed);
 assert.ok(replayed.result.sessions.filter(row=>row.session===2).every(row=>!row.sameId&&row.newHandle));
 assert.equal(replayed.result.criticalWindowObserved,false);assert.equal(replayed.result.status,'inconclusive');
});
test('callback fixture: crossing a publish keeps the original critical-window limit',async()=>{
 const replayed=await replay({crossPublish:true});checkSecondSession(replayed);
 assert.ok(replayed.result.sessions.filter(row=>row.session===2).every(row=>row.sameId&&row.newHandle&&!row.betweenPublishes));
 assert.equal(replayed.result.criticalWindowObserved,false);assert.equal(replayed.result.status,'inconclusive');
});
