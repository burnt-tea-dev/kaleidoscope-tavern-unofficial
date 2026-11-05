/** Isolated QA only. Schedule with the shared native owner, never on LIVE.
 * run_living_effects.py --probe tools/native/incense-damage-order.js --phases first
 * Uses the real placed incense tick, native health/damage and native death event.
 * A successful conversion request does not prove Java's full 60-tick cure delay.
 */
import {world,system,BlockVolume,BlockPermutation} from '@minecraft/server';
import {decorationDiagnostics} from './bedrock/decorations.js';
const TAG='kt_incense_order_qa',CURE='kaleidoscope_tavern:incense_curing';
const pause=ticks=>new Promise(resolve=>system.runTimeout(resolve,ticks));
const targets=new Set(),deaths=new Map();
world.afterEvents.entityDie.subscribe(event=>{if(targets.has(event.deadEntity.id))deaths.set(event.deadEntity.id,event.damageSource.cause);});
function require(value,message){if(!value)throw Error(message);}
world.afterEvents.worldLoad.subscribe(()=>system.runTimeout(async()=>{try{
 require(world.getAllPlayers().length===0,'QA requires zero players');
 const d=world.getDimension('overworld');d.runCommand('tickingarea add circle 84 300 2 1 kt_incense_order_qa true');
 let loaded=false;for(let i=0;i<60&&!loaded;i++){await pause(5);try{loaded=!!d.getBlock({x:84,y:300,z:2});}catch{}}
 require(loaded,'QA chunk unavailable');
 d.fillBlocks(new BlockVolume({x:80,y:299,z:0},{x:88,y:304,z:4}),'minecraft:stone');
 d.fillBlocks(new BlockVolume({x:81,y:300,z:1},{x:87,y:303,z:3}),'minecraft:air');
 const block=d.getBlock({x:84,y:300,z:2});block.setPermutation(BlockPermutation.resolve('kaleidoscope_tavern:butterfly_incense'));
 await pause(5);block.setPermutation(block.permutation.withState('kaleidoscope_tavern:open',1));
 const recipients=[1,2].map((health,index)=>{
  const entity=d.spawnEntity('minecraft:zombie_villager_v2',{x:82.5+index*4,y:300,z:2.5});
  entity.addTag(TAG);targets.add(entity.id);entity.getComponent('minecraft:health').setCurrentValue(health);return entity;
 });
 const [one,two]=recipients,pulses=decorationDiagnostics.incensePulses,cures=decorationDiagnostics.incenseCures;
 for(let i=0;i<60&&decorationDiagnostics.incensePulses===pulses;i++)await pause(5);
 require(decorationDiagnostics.incensePulses>pulses,'placed incense did not pulse');await pause(2);
 require(deaths.get(one.id)==='magic','one-health recipient did not die from the native magic pulse');
 require(decorationDiagnostics.incenseCures===cures+1,'pulse must request exactly one surviving recipient cure');
 const result={kind:'done',phase:'first',players:0,oneHealthDeath:deaths.get(one.id),cureRequests:decorationDiagnostics.incenseCures-cures,
  twoHealthStillValid:two.isValid,twoHealth:two.isValid?two.getComponent('minecraft:health')?.currentValue:null,
  twoCureTag:two.isValid?two.hasTag(CURE):null,fullConversionDelayVerified:false};
 for(const entity of d.getEntities({tags:[TAG]}))entity.remove();
 block.setPermutation(BlockPermutation.resolve('minecraft:air'));d.runCommand('tickingarea remove kt_incense_order_qa');
 console.warn('[LIVING_EFFECT_QA] '+JSON.stringify(result));
}catch(error){console.warn('[LIVING_EFFECT_QA] '+JSON.stringify({kind:'failure',error:String(error)}));}},20));
