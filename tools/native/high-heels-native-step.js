/** QA component capability only. No production High Heels or Player adoption.
 * Native moveRelative delivers physical movement while the selected simulated
 * Player's input getter remains zero. This probe measures the component's
 * actual motion; it does not claim to reach the old Script input predicate.
 * No teleport/impulse/jump calls inside any walking observation window.
 */
import {world,system,BlockVolume,BlockPermutation,GameMode} from '@minecraft/server';
import * as gameTest from '@minecraft/server-gametest';
const ON='kaleidoscope_tavern:qa_native_step_on',OFF='kaleidoscope_tavern:qa_native_step_off';
const pause=ticks=>new Promise(resolve=>system.runTimeout(resolve,ticks));
const out=(stage,data)=>console.warn('[KT-NATIVE-STEP] '+JSON.stringify({stage,tick:system.currentTick,...data}));
function require(value,message){if(!value)throw Error(message);}
function snapshot(player){return {position:{...player.location},velocity:player.getVelocity(),input:player.inputInfo.getMovementVector(),onGround:player.isOnGround,jumping:player.isJumping};}
async function reset(player,start){
 player.stopMoving();player.teleport(start,{rotation:{x:0,y:0}});await pause(3);
 require(player.isOnGround,'native Player did not settle on the QA floor');
}
async function walk(player,name,start){
 await reset(player,start);const trace=[];player.moveRelative(0,1,.15);
 for(let i=0;i<24;i++){await pause(1);trace.push(snapshot(player));}
 player.stopMoving();
 const elevated=trace.find(row=>row.position.y>start.y+.8),moved=trace.some(row=>Math.hypot(row.velocity.x,row.velocity.z)>.01);
 const crossed=trace.some(row=>row.position.y>start.y+.8&&row.position.z>start.z+.4);
 const result={name,start,trace,moved,stepped:crossed,
  jumpObserved:trace.some(row=>row.jumping),elevationVelocity:elevated?.velocity,
  nativeStep:crossed&&!trace.some(row=>row.jumping)&&Math.abs(elevated.velocity.y)<.08,
  maxRise:Math.max(...trace.map(row=>row.position.y-start.y))};
 out('walk',result);return result;
}
async function jump(player,name){
 const start={x:68.5,y:300,z:8.5};await reset(player,start);const trace=[],accepted=player.jump();
 for(let i=0;i<24;i++){await pause(1);trace.push(snapshot(player));}
 const result={name,accepted,trace,maxRise:Math.max(...trace.map(row=>row.position.y-start.y)),landed:player.isOnGround};
 out('jump',result);return result;
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
  d.getBlock({x:64,y:299,z:49}).setType('minecraft:grass_block');
  d.getBlock({x:64,y:300,z:49}).setPermutation(BlockPermutation.resolve('minecraft:dandelion'));
  d.getBlock({x:64,y:300,z:57}).setPermutation(BlockPermutation.resolve('minecraft:water'));
  player=gameTest.spawnSimulatedPlayer({dimension:d,x:64.5,y:300,z:8.5},'NativeStepPlayerQA',GameMode.Survival);
  require(player.typeId==='minecraft:player'&&player.getGameMode()===GameMode.Survival,'native Survival Player unavailable');
  const start={x:64.5,y:300,z:32.65};
  const baseline=await walk(player,'baseline_block',start),baselineJump=await jump(player,'baseline_jump');
  player.triggerEvent(ON);await pause(2);
  const enabled=await walk(player,'enabled_block',start);
  const flower=await walk(player,'enabled_flower',{x:64.5,y:300,z:48.65});
  const water=await walk(player,'enabled_water',{x:64.5,y:300,z:56.65});
  const enabledJump=await jump(player,'enabled_jump');
  player.triggerEvent(OFF);await pause(2);const disabled=await walk(player,'disabled_block',start);
  const fixtureIntact=d.getBlock({x:64,y:300,z:49}).typeId==='minecraft:dandelion'&&d.getBlock({x:64,y:300,z:57}).typeId==='minecraft:water';
  const baselineBlocked=baseline.moved&&!baseline.stepped&&!baseline.jumpObserved;
  const disableRestored=disabled.moved&&!disabled.stepped&&!disabled.jumpObserved;
  const flatWalks=[flower,water].every(row=>row.moved&&row.maxRise<.2&&!row.jumpObserved);
  const unchangedJump=baselineJump.accepted&&enabledJump.accepted&&baselineJump.landed&&enabledJump.landed&&Math.abs(baselineJump.maxRise-enabledJump.maxRise)<1e-4;
  const supported=baselineBlocked&&enabled.moved&&enabled.nativeStep&&disableRestored&&flatWalks&&fixtureIntact&&unchangedJump;
  result={kind:supported?'done':'partial',observationOnly:true,supported,baselineBlocked,disableRestored,flatWalks,fixtureIntact,unchangedJump,
   baseline,enabled,disabled,flower,water,baselineJump,enabledJump,
   scope:'selected vanilla Player plus QA-only variable_max_auto_step group; actual native motion/jump comparison only; not production High Heels, public composition or full Java parity'};
 }catch(error){result={kind:'failure',error:String(error)};}
 finally{if(player?.isValid){try{player.stopMoving();}finally{player.disconnect();}}await pause(3);}
 console.warn('[LIVING_EFFECT_QA] '+JSON.stringify({...result,phase:'first',players:world.getAllPlayers().length}));
},20));
