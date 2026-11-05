/** Isolated QA only. Never install on LIVE.
 * run_living_effects.py --probe tools/native/xp-pickup-cadence.js
 *   --gametest --offline --phases first
 * One native Survival Player, baseline vs real Allium completion, one XP burst.
 * Both Java branches clear takeXpDelay every tick and after each playerTouch;
 * the scan is every five ticks. Orb stacking means count != XP value.
 * Source: Forge c4ec1880 / Neo a1afba34 XpDrainEffect; official Minecraft
 * 1.20.1/1.21.1 ExperienceOrb.playerTouch, getExperienceValue and tick.
 * This records actual pickup cadence/value; completion is not a parity verdict.
 */
import {world,system,BlockVolume,GameMode,ItemStack,EntityDamageCause} from '@minecraft/server';
import * as gameTest from '@minecraft/server-gametest';
import {completeCocktail} from './bedrock/mixology.js';
import {clearCustomEffects,statusNow,tickCustomEffects} from './bedrock/custom-effects.js';
import {activeStatus} from './core/custom-effects.js';
import {EMPTY_CUP} from './core/mixology.js';
const XP='kaleidoscope_tavern:xp_drain',ALLIUM='kaleidoscope_tavern:allium_garden';
const PARK={x:32.5,y:300,z:40.5},PICKUP={x:64.5,y:300,z:40.5};
const CELLS=Array.from({length:8},(_,i)=>({x:48+i*4,y:300,z:32}));
const EXPECTED_XP=40,SETTLE_TICKS=85;
const stagedMobs=new Set(),nativeDeaths=[];
world.afterEvents.entityDie.subscribe(event=>{
 if(stagedMobs.has(event.deadEntity.id))nativeDeaths.push({id:event.deadEntity.id,tick:system.currentTick,
  cause:event.damageSource.cause,killer:event.damageSource.damagingEntity?.id});
});
const pause=ticks=>new Promise(resolve=>system.runTimeout(resolve,ticks));
const out=(stage,data={})=>console.warn('[KT-XP-PICKUP] '+JSON.stringify({stage,tick:system.currentTick,...data}));
function require(value,message){if(!value)throw Error(message);}
function orbs(d){return d.getEntities({type:'minecraft:xp_orb',location:{x:44,y:299,z:28},volume:{x:40,y:6,z:16}});}
function onePlayer(player){require(world.getAllPlayers().length===1&&world.getAllPlayers()[0].id===player.id,'unexpected native Player');}
async function stageBatch(player,d){
 require(orbs(d).length===0,'previous native orb batch still present');
 const before=player.getTotalXp(),firstSeen=new Map();player.teleport(PARK);
 const mobs=CELLS.map(cell=>{
  const mob=d.spawnEntity('minecraft:silverfish',{x:cell.x+.5,y:300,z:cell.z+.5});
  stagedMobs.add(mob.id);return mob;
 });
 // Let all eight spawned actors initialize before attributing native deaths.
 // The previous same-tick spawn/kill fixture produced only seven rewards.
 await pause(2);
 out('actors-initialized',{actors:mobs.map((mob,index)=>({cell:CELLS[index].x,id:mob.id,valid:mob.isValid}))});
 const deathsBefore=nativeDeaths.length;
 for(const [index,cell] of CELLS.entries()){
  // The selected vanilla silverfish rewards exactly 5 XP when killed by a
  // Player. Real native death creates the orbs; no XP amount is assigned here.
  player.teleport({x:cell.x+.5,y:300,z:cell.z+.5});
  const mob=mobs[index];
  require(mob.applyDamage(100,{cause:EntityDamageCause.entityAttack,damagingEntity:player}),'native reward setup damage rejected');
  player.teleport(PARK);
 }
 let pool=[],ready=false;const deadline=system.currentTick+220;
 while(system.currentTick<deadline){
  await pause(1);onePlayer(player);pool=orbs(d);
  for(const orb of pool)if(!firstSeen.has(orb.id))firstSeen.set(orb.id,system.currentTick);
  require(player.getTotalXp()===before,'XP was picked up during setup');
  const cellsPresent=CELLS.every(cell=>pool.some(orb=>Math.abs(orb.location.x-cell.x-.5)<1.5&&Math.abs(orb.location.z-cell.z-.5)<1.5));
  if(cellsPresent&&pool.length>=CELLS.length){
   const latest=Math.max(...pool.map(orb=>firstSeen.get(orb.id)));
   if(system.currentTick-latest>=SETTLE_TICKS){ready=true;break;}
  }
 }
 const setup={nativeDeaths:nativeDeaths.slice(deathsBefore),player:player.id,orbCount:pool.length,
  cells:CELLS.map(cell=>({x:cell.x,orbs:pool.filter(orb=>Math.abs(orb.location.x-cell.x-.5)<1.5&&Math.abs(orb.location.z-cell.z-.5)<1.5).length})),
  xpUnchanged:player.getTotalXp()===before};
 out('setup',setup);
 require(ready,'native orb pool did not settle in all eight reward cells');
 require(setup.nativeDeaths.length===CELLS.length&&setup.nativeDeaths.every(death=>death.killer===player.id),'native deaths were not all attributed to the Player');
 const times=pool.map(orb=>firstSeen.get(orb.id)),oldest=system.currentTick-Math.min(...times),youngest=system.currentTick-Math.max(...times);
 // The source reference's orb merge scan is tickCount%20==1. Keep the
 // first two five-tick scans outside that boundary in the Java comparison.
 require(oldest-youngest<=5,'orb first-observed window too wide for the bounded comparison');
 return {pool,before,ages:{youngest,oldest},ids:pool.map(orb=>orb.id)};
}
async function observe(player,d,withAllium){
 clearCustomEffects(player);const batch=await stageBatch(player,d),container=player.getComponent('minecraft:inventory').container;
 let settledItem=null;
 if(withAllium){
  player.selectedSlotIndex=0;container.setItem(0,new ItemStack(ALLIUM,1));
  completeCocktail({source:player,itemStack:container.getItem(0)},()=>0);
  require(activeStatus(statusNow(player),XP),'formal Allium completion did not apply XP Drain');
  settledItem=container.getItem(0)?.typeId;require(settledItem===EMPTY_CUP,'formal Allium completion did not settle its cup');
 }else require(!activeStatus(statusNow(player),XP),'baseline unexpectedly has XP Drain');
 player.teleport(PICKUP);
 for(const orb of batch.pool){orb.clearVelocity();require(orb.tryTeleport(PICKUP),'native orb fixture positioning failed');}
 const start=system.currentTick,before=player.getTotalXp(),samples=[];let last=-1,finishTick=null;
 // Align the actual owner pass for both controls; later passes use the normal
 // installed five-tick callback. No copy of the attraction/pickup algorithm.
 tickCustomEffects();
 const capture=()=>{
  const ticks=system.currentTick-start,xp=player.getTotalXp()-before,remaining=orbs(d).length;
  if(xp!==last||[0,1,5,6,10,20,40,80,120].includes(ticks)){samples.push({ticks,xp,remaining});last=xp;}
  require(xp<=EXPECTED_XP,'unexpected XP entered the isolated batch');
  if(xp===EXPECTED_XP&&remaining===0&&finishTick===null)finishTick=ticks;
 };
 capture();
 for(let i=0;i<120&&finishTick===null;i++){await pause(1);onePlayer(player);capture();}
 const result={allium:withAllium,nativeRewardInput:{entity:'minecraft:silverfish',kills:CELLS.length,vanillaRewardEach:5,expectedXp:EXPECTED_XP},
  setupXpUnchanged:before===batch.before,settledOrbObservedAges:batch.ages,initialOrbCount:batch.pool.length,initialOrbIds:batch.ids,
  settledItem,finishTick,totalXp:player.getTotalXp()-before,remaining:orbs(d).length,samples};
 out('case',result);return result;
}
world.afterEvents.worldLoad.subscribe(()=>system.runTimeout(async()=>{
 let player,result;
 try{
  require(world.getAllPlayers().length===0,'QA requires no existing players');
  const d=world.getDimension('overworld');d.runCommand('tickingarea add circle 48 300 36 2 kt_xp_pickup_qa true');
  let loaded=false;for(let i=0;i<60&&!loaded;i++){await pause(5);try{loaded=!!d.getBlock(PICKUP)&&!!d.getBlock(PARK);}catch{}}
  require(loaded,'QA chunks did not load');
  d.runCommand('gamerule doMobLoot true');d.runCommand('gamerule doMobSpawning false');
  // Silverfish merge into stone. Glass keeps the actual reward mobs present
  // without changing their definition, damage or native XP reward.
  d.fillBlocks(new BlockVolume({x:30,y:299,z:28},{x:80,y:303,z:44}),'minecraft:glass');
  for(const cell of CELLS)d.fillBlocks(new BlockVolume(cell,{...cell,y:302}),'minecraft:air');
  for(const at of [PARK,PICKUP])d.fillBlocks(new BlockVolume({x:Math.floor(at.x)-1,y:300,z:Math.floor(at.z)-1},{x:Math.floor(at.x)+1,y:302,z:Math.floor(at.z)+1}),'minecraft:air');
  player=gameTest.spawnSimulatedPlayer({dimension:d,...PARK},'TavernXpPickupQA',GameMode.Survival);
  require(player.typeId==='minecraft:player'&&player.getGameMode()===GameMode.Survival,'native Survival Player unavailable');
  const baseline=await observe(player,d,false);
  // An invalid baseline cannot become evidence that Allium loses XP.
  if(baseline.totalXp!==EXPECTED_XP||baseline.remaining!==0)result={kind:'partial',reason:'baseline native reward/pickup did not complete',cases:[baseline]};
  else{
   const allium=await observe(player,d,true),valid=allium.totalXp===EXPECTED_XP&&allium.remaining===0;
   result={kind:valid?'done':'partial',observationOnly:true,javaPickupParityEstablished:false,
    scope:'one native Player; native pickup cadence and total value only; no Mending or multiplayer claim',
    sourceReference:{forge:'c4ec1880',neo:'a1afba34',clearPlayerCooldownEveryTick:true,scanEveryTicks:5,touchRadius:1.5,clearAfterEachTouch:true},cases:[baseline,allium]};
  }
 }catch(error){result={kind:'failure',error:String(error)};}
 finally{
  if(player?.isValid){try{clearCustomEffects(player);}finally{player.disconnect();}}
  await pause(3);
 }
 console.warn('[LIVING_EFFECT_QA] '+JSON.stringify({...result,phase:'first',players:world.getAllPlayers().length}));
},20));
