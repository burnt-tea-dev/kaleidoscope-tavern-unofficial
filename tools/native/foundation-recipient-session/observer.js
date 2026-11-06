// QA only: copy beside W's real scripts/main.js in the existing saved-world copy.
// Importing W's actual entry creates its actual client; never create a second SDK.
import './main.js';
import {world,system,ScriptEventSource} from '@minecraft/server';
import {foundationReady} from './foundation.js';
import {readTavernEffects,getTavernEffectEntities} from './sdk/tavern-foundation-client.js';

const SOURCE='kaleidoscope_world_liquor',NAMES=['qaNetPlain','qaNetHeavy'];
const sessions=new Map(NAMES.map(name=>[name,[]])),events=[],issues=[];
let started=false,phase='waiting',deadline=0,finished=false;
const note=(kind,data={})=>events.push({tick:system.currentTick,kind,...data});
const marker=(name,data={})=>console.log(name+' '+JSON.stringify({tick:system.currentTick,...data}));
const rows=()=>[...sessions.values()].flat();
const current=name=>sessions.get(name)?.at(-1);
function finish(reason){
 if(finished)return;finished=true;
 const data=rows().map(({handle,...row})=>row);
 const controls=data.length===4&&data.every(row=>row.initialSpawn&&row.emptyCount===1&&row.sdkAccepted&&row.idleChecked);
 const race=data.filter(row=>row.session===2).every(row=>row.sameId&&row.newHandle&&row.betweenPublishes);
 marker('TAVERN_QA_SESSION_RESULT',{status:issues.length?'fail':controls&&race?'pass':'inconclusive',reason,
  controls,criticalWindowObserved:controls&&race,playersAfter:world.getAllPlayers().length,issues,sessions:data,events});
}
world.afterEvents.playerSpawn.subscribe(({player,initialSpawn})=>{
 if(!started||!NAMES.includes(player.name)||!initialSpawn)return;
 const list=sessions.get(player.name),previous=list.at(-1);
 if(list.length>=2){issues.push('unexpected third session: '+player.name);return;}
 const row={name:player.name,id:player.id,handle:player,session:list.length+1,spawnTick:system.currentTick,
  initialSpawn,emptyCount:0,sdkAccepted:false,idleChecked:false};
 if(previous){
  row.sameId=previous.id===player.id;row.newHandle=previous.handle!==player;
  row.leaveTick=previous.leaveTick;
  // T205's unmodified publisher runs every five ticks. Use a native sequence to
  // calibrate that phase. Boundary ticks are deliberately inconclusive: event
  // ordering there cannot prove absence was never seen by a publish.
  const first=previous.emptySequence,start=previous.leaveTick,end=system.currentTick;
  row.betweenPublishes=Number.isInteger(first)&&Number.isInteger(start)&&start<end&&
   Math.floor((start-first)/5)===Math.floor((end-first)/5)&&(start-first)%5!==0&&(end-first)%5!==0;
 }
 list.push(row);note('initialSpawn',{name:row.name,id:row.id,session:row.session});
});
world.afterEvents.playerLeave.subscribe(({playerId})=>{
 if(!started)return;
 for(const list of sessions.values()){
  const row=list.at(-1);if(row?.id!==playerId||row.leaveTick!==undefined)continue;
  row.leaveTick=system.currentTick;note('leave',{name:row.name,id:playerId,session:row.session});
 }
});
system.afterEvents.scriptEventReceive.subscribe(event=>{
 if(event.sourceType!==ScriptEventSource.Server)return;
 if(event.id==='tavern_qa:session_begin'){
  if(started||finished)return;
  if(world.getAllPlayers().length){issues.push('begin requires zero players');finish('entry');return;}
  started=true;phase='registration';deadline=system.currentTick+1200;note('begin');return;
 }
 if(!started||finished||event.id!=='kaleidoscope_tavern:effect_snapshot')return;
 let packet;try{packet=JSON.parse(event.message);}catch{return;}
 if(packet.source!==SOURCE)return;
 const row=rows().find(row=>row.id===packet.entity&&row.leaveTick===undefined);
 if(!row)return;
 note('snapshot',{name:row.name,session:row.session,sequence:packet.sequence,rows:packet.rows?.length});
 if(packet.parts!==1||packet.part!==0||!Array.isArray(packet.rows)||packet.rows.length){issues.push('authority is not empty: '+row.name);return;}
 row.emptyCount++;row.emptySequence=packet.sequence;row.receivedTick=system.currentTick;
 // The real SDK receives the same event. Check after all subscribers ran;
 // read()=={} alone would not distinguish an accepted empty from no snapshot.
 system.run(()=>{
  try{row.sdkAccepted=getTavernEffectEntities(world,SOURCE).some(p=>p.id===row.id)&&
   Object.keys(readTavernEffects(row.handle,SOURCE)).length===0;}
  catch(error){issues.push('SDK read: '+String(error));}
  note('sdk',{name:row.name,session:row.session,accepted:row.sdkAccepted});
 });
});
system.runInterval(()=>{
 if(!started||finished)return;
 if(system.currentTick>deadline){issues.push('timeout in '+phase);finish('timeout');return;}
 if(phase==='registration'&&foundationReady()){
  phase='first';deadline=system.currentTick+1600;marker('TAVERN_QA_SESSION_LOGIN_READY');
 }
 for(const row of rows()){
  if(row.receivedTick===undefined||row.idleChecked||system.currentTick-row.receivedTick<10)continue;
  row.idleChecked=true;note('idle',{name:row.name,session:row.session,emptyCount:row.emptyCount});
  if(row.emptyCount!==1)issues.push('idle duplicate: '+row.name+'/'+row.session);
  if(!row.sdkAccepted)issues.push('SDK did not accept empty: '+row.name+'/'+row.session);
 }
 if(phase==='first'&&NAMES.every(name=>current(name)?.session===1&&current(name).idleChecked)){
  phase='first_leave';deadline=system.currentTick+600;marker('TAVERN_QA_SESSION_DISCONNECT_READY',{session:1});
 }else if(phase==='first_leave'&&world.getAllPlayers().length===0&&NAMES.every(name=>current(name)?.leaveTick!==undefined)){
  phase='second';deadline=system.currentTick+1600;marker('TAVERN_QA_SESSION_RECONNECT_READY');
 }else if(phase==='second'&&NAMES.every(name=>current(name)?.session===2&&current(name).idleChecked)){
  phase='second_leave';deadline=system.currentTick+600;marker('TAVERN_QA_SESSION_DISCONNECT_READY',{session:2});
 }else if(phase==='second_leave'&&world.getAllPlayers().length===0&&NAMES.every(name=>current(name)?.leaveTick!==undefined))finish('normal disconnect');
},1);
