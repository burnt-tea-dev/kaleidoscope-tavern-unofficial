/** Isolated QA only. Fixed candidate/server2.7.0 + GameTest1beta, no LIVE.
 * run_living_effects.py --probe tools/native/high-heels-player-capability.js
 * --gametest --offline --phases first. No persistence format changes/restart.
 * Read real Player input/velocity. Never replace inputInfo or teleport methods.
 * Player.teleport results from another API version do not prove tryTeleport.
 */
import {world,system,BlockVolume,BlockPermutation,GameMode,ItemStack} from '@minecraft/server';
import * as gameTest from '@minecraft/server-gametest';
import {completeCocktail} from './bedrock/mixology.js';
import {clearCustomEffects,statusNow,customEffectDiagnostics} from './bedrock/custom-effects.js';
import {activeStatus,highHeelsDirection,highHeelsBlocked,highHeelsNearBoundary} from './core/custom-effects.js';
import {EMPTY_CUP} from './core/mixology.js';
const HEELS='kaleidoscope_tavern:high_heels',WHITE_LADY='kaleidoscope_tavern:white_lady';
const CASES=[{name:'flower',block:'minecraft:dandelion',z:24},{name:'water',block:'minecraft:water',z:40},{name:'solid',block:'minecraft:stone',z:56}];
const pause=ticks=>new Promise(resolve=>system.runTimeout(resolve,ticks));
const out=(stage,data={})=>console.warn('[KT-HIGH-HEELS] '+JSON.stringify({stage,tick:system.currentTick,...data}));
function require(value,message){if(!value)throw Error(message);}
function snapshot(player){
 return {tick:system.currentTick,position:{...player.location},velocity:player.getVelocity(),input:player.inputInfo.getMovementVector(),
  onGround:player.isOnGround,jumping:player.isJumping,flying:player.isFlying,gliding:player.isGliding,swimming:player.isSwimming,climbing:player.isClimbing};
}
function eligible(state,player){
 const direction=highHeelsDirection(player.getRotation().y,state.input);
 return state.onGround&&!state.jumping&&!state.flying&&!state.gliding&&!state.swimming&&!state.climbing&&
  highHeelsBlocked(state.input,state.velocity)&&!!direction&&highHeelsNearBoundary(state.position,direction);
}
function drinkWhiteLady(player){
 const container=player.getComponent('minecraft:inventory').container;player.selectedSlotIndex=0;
 container.setItem(0,new ItemStack(WHITE_LADY,1));completeCocktail({source:player,itemStack:container.getItem(0)},()=>0);
 require(!!activeStatus(statusNow(player),HEELS),'formal White Lady completion did not apply High Heels');
 require(container.getItem(0)?.typeId===EMPTY_CUP,'formal White Lady did not settle its glass');
}
async function ownerCase(player,d,row){
 player.stopMoving();clearCustomEffects(player);
 const start={x:64.5,y:300,z:row.z+.65},at={x:64,y:300,z:row.z+1};
 d.getBlock({x:64,y:299,z:row.z+1}).setType('minecraft:grass_block');
 d.getBlock(at).setPermutation(BlockPermutation.resolve(row.block));
 player.teleport(start,{rotation:{x:0,y:0}});await pause(3);drinkWhiteLady(player);
 const beforeSteps=customEffectDiagnostics.highHeelsSteps,beforeErrors=customEffectDiagnostics.errors.length;
 const trace=[];player.moveRelative(0,1,.15);
 for(let i=0;i<16;i++){await pause(1);const state=snapshot(player);trace.push({...state,eligible:eligible(state,player),steps:customEffectDiagnostics.highHeelsSteps-beforeSteps});}
 player.stopMoving();const after=snapshot(player),steps=customEffectDiagnostics.highHeelsSteps-beforeSteps;
 const eligibleFrames=trace.filter(frame=>frame.eligible).length,sourceErrors=customEffectDiagnostics.errors.slice(beforeErrors);
 const observedBlock=d.getBlock(at).typeId,fixtureIntact=observedBlock===row.block;
 const observed=eligibleFrames>0&&fixtureIntact;
 const matches=observed&&(row.name==='solid'?steps>0&&after.position.y>start.y+.8:steps===0&&Math.max(...trace.map(frame=>frame.position.y))<start.y+.2);
 const result={name:row.name,requestedBlock:row.block,observedBlock,fixtureIntact,start,after,eligibleFrames,steps,sourceErrors,matches,trace};
 clearCustomEffects(player);out('owner_case',result);return result;
}
async function exactPlayerOptions(player){
 player.stopMoving();clearCustomEffects(player);player.teleport({x:64.5,y:300,z:8.5},{rotation:{x:0,y:0}});await pause(3);
 player.moveRelative(0,1,.15);await pause(1);const before=snapshot(player),target={x:before.position.x,y:before.position.y+1,z:before.position.z+.2};
 let accepted=false,error=null;
 try{accepted=player.tryTeleport(target,{checkForBlocks:true,keepVelocity:true});}catch(e){error=String(e);}
 const immediate=snapshot(player);await pause(1);const next=snapshot(player);player.stopMoving();
 const result={method:'Player.tryTeleport',options:{checkForBlocks:true,keepVelocity:true},target,accepted,error,before,immediate,next,
  nonzeroVelocityBefore:Math.hypot(before.velocity.x,before.velocity.z)>0,
  velocityPreservedImmediately:['x','y','z'].every(axis=>Math.abs(before.velocity[axis]-immediate.velocity[axis])<1e-6)};out('exact_options',result);return result;
}
world.afterEvents.worldLoad.subscribe(()=>system.runTimeout(async()=>{
 let player,result;
 try{
  require(world.getAllPlayers().length===0,'QA requires no existing Players');const d=world.getDimension('overworld');
  d.runCommand('tickingarea add 60 299 6 68 304 60 kt_high_heels_qa true');
  let loaded=false;for(let i=0;i<60&&!loaded;i++){await pause(5);try{loaded=!!d.getBlock({x:64,y:300,z:8})&&!!d.getBlock({x:64,y:300,z:58});}catch{}}
  require(loaded,'High Heels QA chunks unavailable');d.runCommand('gamerule doMobSpawning false');
  d.fillBlocks(new BlockVolume({x:62,y:299,z:6},{x:66,y:299,z:60}),'minecraft:stone');
  d.fillBlocks(new BlockVolume({x:62,y:300,z:6},{x:66,y:304,z:60}),'minecraft:air');
  player=gameTest.spawnSimulatedPlayer({dimension:d,x:64.5,y:300,z:8.5},'HighHeelsPlayerQA',GameMode.Survival);
  require(player.typeId==='minecraft:player'&&player.getGameMode()===GameMode.Survival,'native Survival Player unavailable');
  const cases=[];for(const row of CASES)cases.push(await ownerCase(player,d,row));
  const exactOptions=await exactPlayerOptions(player);
  const complete=cases.every(row=>row.matches&&!row.sourceErrors.length)&&exactOptions.accepted&&!exactOptions.error&&exactOptions.nonzeroVelocityBefore&&exactOptions.velocityPreservedImmediately;
  result={kind:complete?'done':'partial',observationOnly:true,allAffectedCasesObserved:complete,exactOptions,cases,
   scope:'actual server2.7 Player; formal White Lady owner; native movement input and exact tryTeleport options only; no full Java step-height/client parity'};
 }catch(error){result={kind:'failure',error:String(error)};}
 finally{
  if(player?.isValid){try{player.stopMoving();clearCustomEffects(player);}finally{player.disconnect();}}await pause(3);
 }
 console.warn('[LIVING_EFFECT_QA] '+JSON.stringify({...result,phase:'first',players:world.getAllPlayers().length}));
},20));
