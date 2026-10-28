/** Isolated production-block physics probe. Never load into a survival save. */
import {world,system,BlockPermutation} from '@minecraft/server';
import {BREAK_ROUTE_TEST} from './bedrock/protected-break-router.js';
const NS='kaleidoscope_tavern:',HEAD=NS+'wild_grapevine',BODY=NS+'wild_grapevine_plant';
const wait=ticks=>new Promise(resolve=>system.runTimeout(resolve,ticks));
const check=(ok,message)=>{if(!ok)throw Error(message);};
world.afterEvents.worldLoad.subscribe(()=>system.runTimeout(async()=>{try{
 const d=world.getDimension('overworld');
 d.runCommand('tickingarea add circle 0 220 0 2 wild_grapevine_qa true');
 for(let n=0;n<60;n++){await wait(5);try{if(d.getBlock({x:0,y:220,z:0}))break;}catch{}}
 const block=(x,y)=>d.getBlock({x,y,z:0});
 const set=(x,y,id)=>block(x,y).setPermutation(BlockPermutation.resolve(id,id===HEAD?{[NS+'age_low']:9,[NS+'age_high']:1}:{}));
 const entities=x=>d.getEntities({type:'minecraft:item',location:{x,y:215,z:0},maxDistance:20});
 const drops=x=>entities(x).filter(e=>Math.abs(e.location.x-x)<4).map(e=>e.getComponent('minecraft:item').itemStack);
 const clean=async x=>{for(let y=198;y<229;y++)set(x,y,'minecraft:air');await wait(3);for(const e of entities(x))if(Math.abs(e.location.x-x)<4)e.remove();};
 const settle=async(predicate,limit=12)=>{const start=system.currentTick;for(let n=0;n<limit&&!predicate();n++)await wait(1);check(predicate(),'native chain did not settle');return system.currentTick-start;};
 const exactDrops=(x,amount)=>{const stacks=drops(x);check(stacks.every(s=>s.typeId===NS+'grapevine')&&stacks.reduce((n,s)=>n+s.amount,0)===amount,'wrong/duplicate drops '+JSON.stringify(stacks.map(s=>[s.typeId,s.amount])));};
 const cases=[];
 for(const [x,support]of [[0,'minecraft:stone'],[12,'minecraft:birch_leaves']]){
  await clean(x);set(x,223,support);set(x,222,BODY);set(x,221,BODY);set(x,220,HEAD);await wait(3);
  d.runCommand(`setblock ${x} 221 0 air destroy`);
  const ticks=await settle(()=>block(x,220).isAir&&block(x,222).typeId===HEAD);exactDrops(x,2);
  cases.push({case:'middle-break',support,detachedWithinTicks:ticks,drops:2,upperBecameHead:true});
 }
 const route=BREAK_ROUTE_TEST.routes.find(r=>r.id==='cultivation');check(route?.onNeighborBreak,'production neighbour observer missing');
 await clean(0);set(0,223,'minecraft:stone');set(0,222,BODY);set(0,221,BODY);set(0,220,HEAD);await wait(3);
 // Directly invoke the production callback with native blocks. This does not
 // pretend that a zero-player probe exercised a real player's input event.
 route.onNeighborBreak({block:block(0,223)});route.onNeighborBreak({block:block(0,223)});set(0,223,'minecraft:air');
 const supportTicks=await settle(()=>[220,221,222].every(y=>block(0,y).isAir));exactDrops(0,3);
 cases.push({case:'duplicate-support-notification',detachedWithinTicks:supportTicks,drops:3});
 await clean(0);set(0,226,'minecraft:stone');for(let y=225;y>200;y--)set(0,y,BODY);set(0,200,HEAD);await wait(3);
 d.runCommand('setblock 0 225 0 air destroy');const longTicks=await settle(()=>Array.from({length:26},(_,i)=>block(0,200+i).isAir).every(Boolean),60);exactDrops(0,26);
 cases.push({case:'26-cell-chain',detachedWithinTicks:longTicks,drops:26});
 await clean(0);set(0,223,'minecraft:stone');set(0,222,BODY);set(0,221,BODY);set(0,220,HEAD);await wait(3);
 world.gameRules.doTileDrops=false;
 try{d.runCommand('setblock 0 222 0 air destroy');await settle(()=>[220,221,222].every(y=>block(0,y).isAir));exactDrops(0,0);}
 finally{world.gameRules.doTileDrops=true;}
 cases.push({case:'tile-drops-disabled',drops:0});
 console.log('WILD_GRAPEVINE_QA_DONE '+JSON.stringify({cases,players:world.getAllPlayers().length,realPlayerInputTested:false}));
 d.runCommand('tickingarea remove wild_grapevine_qa');
}catch(error){console.error('WILD_GRAPEVINE_QA_FAILED '+String(error)+' '+error.stack);}},40));
