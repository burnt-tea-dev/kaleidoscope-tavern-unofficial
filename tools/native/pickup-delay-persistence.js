/** Narrow zero-player native observation of the shared pickup-delay owner.
 * Import beside an unchanged copy of bedrock/pickup-overflow.js in a QA pack.
 * Normal stop/restart reuses this exact world; no client or LIVE operations.
 */
import {world,system,ItemStack,BlockVolume} from '@minecraft/server';
import {preparePickupOverflow,startPickupDelay,installPickupOverflowEvents,PICKUP_AFTER,TOMB_PICKUP_UNLOCK,blockOverflowPickup} from './bedrock/pickup-overflow.js';
const KEY='kt_pickup_persistence_qa',TAG='kt_pickup_persistence_qa',seen=new Map();
const out=(kind,fields={})=>console.warn('[LIVING_EFFECT_QA] '+JSON.stringify({kind,...fields}));
const need=(value,message)=>{if(!value)throw Error(message);};
const pause=ticks=>new Promise(resolve=>system.runTimeout(resolve,ticks));
const read=e=>({id:e.id,tick:system.currentTick,overflow:e.getDynamicProperty(PICKUP_AFTER),tomb:e.getDynamicProperty(TOMB_PICKUP_UNLOCK)});
world.afterEvents.entityLoad.subscribe(({entity})=>{try{if(entity.hasTag(TAG))seen.set(entity.id,read(entity));}catch{}});
installPickupOverflowEvents();
world.afterEvents.worldLoad.subscribe(()=>system.run(async()=>{try{
 need(world.getAllPlayers().length===0,'QA requires zero players');
 const d=world.getDimension('overworld'),previous=world.getDynamicProperty(KEY);
 if(previous){
  const saved=JSON.parse(previous);
  out('observation',{stage:'restart-initial',tick:system.currentTick,items:d.getEntities({type:'minecraft:item'}).map(read),seen:[...seen.values()]});
  d.runCommand('tickingarea preload kt_pickup_persistence true');
  for(let i=0;i<120&&saved.ids.some(id=>!seen.has(id));i++)await pause(1);
  out('observation',{stage:'restart-loaded',tick:system.currentTick,items:d.getEntities({type:'minecraft:item'}).map(read),seen:[...seen.values()]});
  const entities=saved.ids.map(id=>world.getEntity(id));need(entities.every(Boolean),'saved native items missing');
  const loaded=entities.map(e=>seen.get(e.id)??read(e));
  const pending=loaded[0],initial=Number(pending.overflow?.slice(7));
  need(initial>0&&initial<=40,'fixture stopped too late or remaining delay was not saved');
  const unloadedWorldTicks=pending.tick-saved.startedTick;
  need(unloadedWorldTicks>40,'fixture did not distinguish the old absolute-clock deadline');
  need(loaded[1].overflow==='loaded:0','expired item revived across restart');
  await pause(45);
  need(entities[0].getDynamicProperty(PICKUP_AFTER)==='loaded:0','restored delay did not expire');
  need(entities[0].getDynamicProperty(TOMB_PICKUP_UNLOCK)==='loaded:0','restored Tomb delay did not expire');
  need(!blockOverflowPickup(entities[0])&&!blockOverflowPickup(entities[0],system.currentTick,TOMB_PICKUP_UNLOCK),'expired item remains blocked');
  out('done',{phase:'restart',players:0,loaded,after:entities.map(read),savedAt:saved.startedTick,unloadedWorldTicks});return;
 }
 d.runCommand('tickingarea add circle 4098 300 4098 1 kt_pickup_persistence true');
 for(let i=0;i<40;i++){try{if(d.getBlock({x:4098,y:300,z:4098}))break;}catch{}await pause(2);}
 d.fillBlocks(new BlockVolume({x:4096,y:299,z:4096},{x:4102,y:299,z:4102}),'minecraft:stone');
 const pending=d.spawnItem(new ItemStack('minecraft:diamond_sword'),{x:4098.5,y:300,z:4098.5});pending.addTag(TAG);
 const expired=d.spawnItem(new ItemStack('minecraft:iron_helmet'),{x:4101.5,y:300,z:4101.5});expired.addTag(TAG);
 preparePickupOverflow(pending);startPickupDelay(pending,TOMB_PICKUP_UNLOCK);preparePickupOverflow(expired);
 const start=system.currentTick;await pause(10);
 need(pending.getDynamicProperty(PICKUP_AFTER)==='loaded:'+Math.max(0,40-(system.currentTick-start)),'normal overflow ticks differ');
 need(pending.getDynamicProperty(TOMB_PICKUP_UNLOCK)===pending.getDynamicProperty(PICKUP_AFTER),'Tomb owner ticks differ');
 await pause(30);need(expired.getDynamicProperty(PICKUP_AFTER)==='loaded:0','expiry was not persisted without pickup');
 // Save at a known world tick. On restart this distant chunk is explicitly
 // preloaded; its delayed arrival must not consume saved remaining ticks.
 await pause(100);preparePickupOverflow(pending);startPickupDelay(pending,TOMB_PICKUP_UNLOCK);
 const saved={ids:[pending.id,expired.id],startedTick:system.currentTick};world.setDynamicProperty(KEY,JSON.stringify(saved));
 out('done',{phase:'first',players:0,items:[read(pending),read(expired)],...saved});
}catch(error){out('failure',{error:String(error),stack:error.stack});}}));
