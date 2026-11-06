/** QA component capability only. No production High Heels or Player adoption.
 * Native moveRelative delivers physical movement while the selected simulated
 * Player's input getter remains zero. This probe measures the component's
 * actual motion; it does not claim to reach the old Script input predicate.
 * No teleport/impulse/jump calls inside any walking observation window.
 */
import {world,system,BlockVolume,GameMode} from '@minecraft/server';
import * as gameTest from '@minecraft/server-gametest';
const ON='kaleidoscope_tavern:qa_native_step_on',OFF='kaleidoscope_tavern:qa_native_step_off',MARKER='kt_qa_native_step_enabled';
const pause=ticks=>new Promise(resolve=>system.runTimeout(resolve,ticks));
const out=(stage,data)=>console.warn('[KT-NATIVE-STEP] '+JSON.stringify({stage,tick:system.currentTick,...data}));
function require(value,message){if(!value)throw Error(message);}
function snapshot(player){return {position:{...player.location},velocity:player.getVelocity(),input:player.inputInfo.getMovementVector(),onGround:player.isOnGround,jumping:player.isJumping};}
async function reset(player,start){
 player.stopMoving();player.teleport(start,{rotation:{x:0,y:0}});await pause(3);
 require(player.isOnGround,'native Player did not settle on the QA floor');
}
async function walk(player,name,start,event){
 await reset(player,start);
 // Setup teleport precedes activation, so it cannot reset the tested change.
 if(event){player.triggerEvent(event);await pause(2);require(player.hasTag(MARKER)===(event===ON),'selected Player event response was not observed: '+event);}
 const eventAcknowledged=event?player.hasTag(MARKER)===(event===ON):null,trace=[];player.moveRelative(0,1,.15);
 for(let i=0;i<24;i++){await pause(1);trace.push(snapshot(player));}
 player.stopMoving();
 const elevated=trace.find(row=>row.position.y>start.y+.8),moved=trace.some(row=>Math.hypot(row.velocity.x,row.velocity.z)>.01);
 const crossed=trace.some(row=>row.position.y>start.y+.8&&row.position.z>start.z+.4);
 const result={name,start,event,eventAcknowledged,trace,moved,stepped:crossed,
  jumpObserved:trace.some(row=>row.jumping),elevationVelocity:elevated?.velocity,
  nativeStep:crossed&&!trace.some(row=>row.jumping)&&Math.abs(elevated.velocity.y)<.08,
  maxRise:Math.max(...trace.map(row=>row.position.y-start.y))};
 out('walk',result);return result;
}
world.afterEvents.worldLoad.subscribe(()=>system.runTimeout(async()=>{
 let player,result;
 try{
  require(world.getAllPlayers().length===0,'QA requires no existing Players');const d=world.getDimension('overworld');
  d.runCommand('tickingarea add 60 299 6 72 304 60 kt_native_step_qa true');
  let loaded=false;for(let i=0;i<60&&!loaded;i++){await pause(5);try{loaded=!!d.getBlock({x:64,y:300,z:8})&&!!d.getBlock({x:64,y:300,z:58});}catch{}}
  require(loaded,'native step QA chunks unavailable');d.runCommand('gamerule doMobSpawning false');
  d.fillBlocks(new BlockVolume({x:62,y:299,z:6},{x:70,y:299,z:60}),'minecraft:stone');
  d.fillBlocks(new BlockVolume({x:62,y:300,z:6},{x:70,y:304,z:60}),'minecraft:air');
  d.fillBlocks(new BlockVolume({x:62,y:300,z:33},{x:66,y:300,z:40}),'minecraft:stone');
  player=gameTest.spawnSimulatedPlayer({dimension:d,x:64.5,y:300,z:8.5},'NativeStepPlayerQA',GameMode.Survival);
  require(player.typeId==='minecraft:player'&&player.getGameMode()===GameMode.Survival,'native Survival Player unavailable');
  const start={x:64.5,y:300,z:32.65};
  require(!player.hasTag(MARKER),'new Player already has the QA event marker');
  const baseline=await walk(player,'baseline_block',start);
  const enabled=await walk(player,'enabled_block',start,ON);
  const disabled=await walk(player,'disabled_block',start,OFF);
  const baselineBlocked=baseline.moved&&!baseline.stepped&&!baseline.jumpObserved;
  const disableRestored=disabled.moved&&!disabled.stepped&&!disabled.jumpObserved;
  const eventDeliveryProven=enabled.eventAcknowledged&&disabled.eventAcknowledged;
  const supported=eventDeliveryProven&&baselineBlocked&&enabled.moved&&enabled.nativeStep&&disableRestored;
  result={kind:supported?'done':'partial',observationOnly:true,supported,eventDeliveryProven,baselineBlocked,disableRestored,baseline,enabled,disabled,
   scope:'selected vanilla Player plus QA-only variable_max_auto_step group, witnessed event delivery after setup teleport; native full-block motion only; first-scene flower/water/jump samples not replayed; no production or full Java parity claim'};
 }catch(error){result={kind:'failure',error:String(error)};}
 finally{if(player?.isValid){try{player.stopMoving();}finally{player.disconnect();}}await pause(3);}
 console.warn('[LIVING_EFFECT_QA] '+JSON.stringify({...result,phase:'first',players:world.getAllPlayers().length}));
},20));
