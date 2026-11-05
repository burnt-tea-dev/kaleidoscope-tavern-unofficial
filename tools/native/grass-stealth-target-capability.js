/** Isolated QA only. Requires server2.12.0-beta, server-gametest1.0.0-beta,
 * gametest and upcoming_creator_features on the selected BDS1.26.60.6 engine.
 * Import in a tiny diagnostic BP, warm the chunks around 0/5/0, then send
 * scriptevent tavern:qa_target. Never install this observer on LIVE.
 * Successful observation is distinct from clear_target_supported.
 */
import {world,system,GameMode} from '@minecraft/server';
import * as gameTest from '@minecraft/server-gametest';
const wait=ticks=>new Promise(resolve=>system.runTimeout(resolve,ticks));
let running=false;
system.afterEvents.scriptEventReceive.subscribe(event=>{
 if(event.id!=='tavern:qa_target'||running)return;running=true;
 run().catch(error=>console.error('TAVERN_TARGET_FATAL '+String(error)+' '+error?.stack));
});
async function run(){
 const dimension=world.getDimension('overworld'),checks=[],observations=[];let player,zombie,pig;
 const check=(name,ok)=>{checks.push({name,passed:!!ok});if(!ok)throw Error(name);};
 try{
  dimension.runCommand('time set midnight');dimension.runCommand('difficulty normal');
  dimension.runCommand('fill -4 4 -4 10 4 4 stone');dimension.runCommand('fill -4 5 -4 10 8 4 air');
  player=gameTest.spawnSimulatedPlayer({dimension,x:8.5,y:5,z:.5},'TargetCapability',GameMode.Survival);
  zombie=dimension.spawnEntity('minecraft:zombie',{x:.5,y:5,z:.5});
  for(let i=0;i<100&&zombie.target?.id!==player.id;i++)await wait(1);
  console.warn('TAVERN_TARGET_SETUP '+JSON.stringify({zombieLocation:zombie.location,playerLocation:player.location,targetIsPlayer:zombie.target?.id===player.id,gameMode:player.getGameMode()}));
  check('real zombie acquired survival Player target',zombie.target?.id===player.id);
  for(const [name,value] of [['undefined',undefined],['null',null]]){
   const before=zombie.target?.id===player.id;let accepted=false,error;
   try{zombie.target=value;accepted=true;}catch(e){error=String(e);}
   observations.push({assignment:name,before_player:before,accepted,error,immediate_target_is_player:zombie.target?.id===player.id});
  }
  pig=dimension.spawnEntity('minecraft:pig',{x:0,y:5,z:2.5});
  let accepted=false,error;
  try{zombie.target=pig;accepted=true;}catch(e){error=String(e);}
  observations.push({assignment:'other native Entity',accepted,error,immediate_target_is_pig:zombie.target?.id===pig.id});
  let prototype=zombie,descriptor;
  while(prototype&&!descriptor){descriptor=Object.getOwnPropertyDescriptor(prototype,'target');prototype=Object.getPrototypeOf(prototype);}
  observations.push({descriptor_found:!!descriptor,has_getter:typeof descriptor?.get==='function',has_setter:typeof descriptor?.set==='function'});
  await wait(3);
  check('native target getter remains functional',zombie.target?.id===player.id||zombie.target?.id===pig.id||zombie.target===undefined);
 }finally{
  zombie?.remove();pig?.remove();player?.disconnect();await wait(3);
  check('simulated Player removed',world.getAllPlayers().length===0);
 }
 console.warn('TAVERN_TARGET_RESULT '+JSON.stringify({passed:true,checks,playersAfter:0,observations,
  clear_target_supported:observations.some(row=>['undefined','null'].includes(row.assignment)&&row.accepted&&!row.immediate_target_is_player),
  scope:'Actual vanilla zombie target getter and assignment on BDS1.26.60.6/server2.12.0-beta. No production mob override or runtime change.'}));
}
