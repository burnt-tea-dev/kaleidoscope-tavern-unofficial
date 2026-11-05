/** Isolated QA only: verify the actual entity property across a normal save/restart.
 * Use run_living_effects.py --probe tools/native/custom-effect-capacity.js.
 * The registered fixture effects and spawned fish never belong on LIVE.
 */
import {world,system,BlockVolume} from '@minecraft/server';
import {ExtensionRegistry} from './core/registry.js';
import {CUSTOM_STATUS_KEY,readStatus,activeStatus} from './core/custom-effects.js';
import {applyCustomEffect,statusNow,clearCustomEffects} from './bedrock/custom-effects.js';
const KEY='kaleidoscope_tavern:capacity_qa',TAG='kt_capacity_qa',VISION='kaleidoscope_tavern:vision';
const registry=new ExtensionRegistry({recipes:[],fluids:[],itemExists:()=>true});
const effects=['capacity_left','capacity_right'].flatMap(source=>{
 const effects=Array.from({length:16},(_,i)=>({id:source+':effect_'+i,mode:'timed'}));
 registry.install({api:1,source,version:'1.0.0',effects});return effects;
});
const pause=ticks=>new Promise(resolve=>system.runTimeout(resolve,ticks));
function require(value,message){if(!value)throw Error(message);}
const finish=(phase,data)=>console.warn('[LIVING_EFFECT_QA] '+JSON.stringify({kind:'done',phase,players:world.getAllPlayers().length,...data}));
world.afterEvents.worldLoad.subscribe(()=>system.runTimeout(async()=>{try{
 require(world.getAllPlayers().length===0,'QA requires zero players');
 const d=world.getDimension('overworld'),previous=world.getDynamicProperty(KEY);
 if(previous){
  const saved=JSON.parse(previous),fish=d.getEntities({tags:[TAG]}).find(e=>e.id===saved.entity);
  require(fish,'saved fish missing');
  const raw=fish.getDynamicProperty(CUSTOM_STATUS_KEY),state=readStatus(raw);
  require(state.entries.length===35,'saved effect rows missing');
  const before=activeStatus(statusNow(fish),VISION);
  require(before?.amplifier===2&&before.ticks>0&&before.ticks<=saved.ticks,'saved strongest Vision missing');
  await pause(10);const after=activeStatus(statusNow(fish),VISION);
  require(after?.ticks===before.ticks-10,'loaded countdown did not resume');
  clearCustomEffects(fish);require(readStatus(fish.getDynamicProperty(CUSTOM_STATUS_KEY)).entries.length===0,'clear did not persist');
  fish.remove();world.setDynamicProperty(KEY,undefined);d.runCommand('tickingarea remove kt_capacity_qa');
  finish('restart',{rows:state.entries.length,before:before.ticks,after:after.ticks,cleared:true});return;
 }
 d.runCommand('tickingarea add circle 62 300 2 1 kt_capacity_qa true');
 let loaded=false;for(let i=0;i<60&&!loaded;i++){await pause(5);try{loaded=!!d.getBlock({x:62,y:300,z:2});}catch{}}
 require(loaded,'QA chunk unavailable');
 d.fillBlocks(new BlockVolume({x:60,y:299,z:0},{x:64,y:303,z:4}),'minecraft:stone');
 d.fillBlocks(new BlockVolume({x:61,y:300,z:1},{x:63,y:302,z:3}),'minecraft:water');
 const fish=d.spawnEntity('minecraft:cod',{x:62.5,y:301,z:2.5});fish.addTag(TAG);
 for(const {id}of effects)require(applyCustomEffect(fish,{effect:id,duration:600,amplifier:0}),'registered effect rejected');
 for(const amplifier of [0,1,2])require(applyCustomEffect(fish,{effect:VISION,duration:600,amplifier}),'Vision rejected above 32 rows');
 const state=readStatus(fish.getDynamicProperty(CUSTOM_STATUS_KEY));require(state.entries.length===35,'native property did not retain every row');
 const ticks=activeStatus(state,VISION).ticks;world.setDynamicProperty(KEY,JSON.stringify({entity:fish.id,ticks}));
 finish('first',{rows:state.entries.length,bytes:fish.getDynamicProperty(CUSTOM_STATUS_KEY).length,ticks});
}catch(error){console.warn('[LIVING_EFFECT_QA] '+JSON.stringify({kind:'failure',error:String(error)}));}},20));
