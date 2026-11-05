/** Execute the actual observer; the external API fixture controls load timing. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {world,system,Signal} from '@minecraft/server';

async function scenario(missing){
 const savedWorld={afterEvents:world.afterEvents,getDynamicProperty:world.getDynamicProperty,setDynamicProperty:world.setDynamicProperty,getEntity:world.getEntity,getAllPlayers:world.getAllPlayers,getDimension:world.getDimension};
 const warn=console.warn,logs=[],idReads=[];let spatialReads=0;
 const actor=(id,name,variant)=>({id,nameTag:name,typeId:'minecraft:villager_v2',isValid:true,
  getComponent(id){if(id==='minecraft:health')return {currentValue:20};if(id==='minecraft:variant')return {value:variant};if(id==='minecraft:mark_variant'||id==='minecraft:skin_id')return {value:0};},
  hasTag:()=>false,getEffect:()=>undefined,getDynamicProperty:()=>undefined,remove(){this.isValid=false;}});
 const complete=actor('saved-complete','KT incense survivor',2),pending=actor('transformed-pending','KT incense saved conversion',7);
 let value=JSON.stringify({completed:{id:complete.id,nameTag:complete.nameTag,marker:null,qaTag:false,variant:2,markVariant:0,skinId:0},pending:{id:'old-pending',nameTag:pending.nameTag}});
 const dimension={getBlock(){return system.currentTick>=10?{}:undefined;},getEntities(){spatialReads++;return [pending];},runCommand(){}};
 try{
  system.queue.clear();system.currentTick=0;
  world.afterEvents=Object.fromEntries(['worldLoad','dataDrivenEntityTrigger','entitySpawn','entityHurt','entityHealthChanged','entityDie'].map(name=>[name,new Signal()]));
  world.getDynamicProperty=()=>value;world.setDynamicProperty=(_key,next)=>{value=next;};
  world.getAllPlayers=()=>[];world.getDimension=()=>dimension;
  world.getEntity=id=>{idReads.push({id,tick:system.currentTick});return id===complete.id&&!missing&&system.currentTick>=20?complete:undefined;};
  console.warn=line=>logs.push(String(line));
  // The native runner copies this module beside bedrock/. Only relocate that
  // import for the source fixture; execute the observer body without edits.
  const source=(await readFile(new URL('./incense-damage-order.js',import.meta.url),'utf8')).replace("'./bedrock/decorations.js'",JSON.stringify(new URL('../../runtime/BP/scripts/bedrock/decorations.js',import.meta.url).href));
  await import('data:text/javascript,'+encodeURIComponent(source+'\n// scenario '+missing));
  world.afterEvents.worldLoad.emit({});
  for(let i=0;i<130;i++){system.advance(1);await Promise.resolve();}
  return {logs,idReads,spatialReads};
 }finally{console.warn=warn;Object.assign(world,savedWorld);system.queue.clear();}
}

test('restart waits for the same saved actor after the chunk loads and accepts an already transformed pending actor',async()=>{
 const result=await scenario(false);
 const row=result.logs.find(line=>line.startsWith('[LIVING_EFFECT_QA] '));
 assert(row,'observer did not finish');const observed=JSON.parse(row.slice('[LIVING_EFFECT_QA] '.length));
 assert.equal(observed.kind,'done');assert.equal(observed.phase,'restart');assert.equal(observed.completedAfter.id,'saved-complete');
 assert.equal(observed.nativeTransformationThisRun,false);
 assert(result.idReads.some(row=>row.id==='saved-complete'&&row.tick===20));
 assert(result.idReads.filter(row=>row.id==='saved-complete').every(row=>row.tick>=10));
});
test('a genuinely missing saved ID still fails after loading without a spatial or name fallback',async()=>{
 const result=await scenario(true);
 const row=result.logs.find(line=>line.startsWith('[LIVING_EFFECT_QA] '));
 const observed=JSON.parse(row.slice('[LIVING_EFFECT_QA] '.length));
 assert.equal(observed.kind,'failure');assert.match(observed.error,/missing after chunk\/actor wait/);
 assert.equal(result.spatialReads,0);assert(result.idReads.at(-1).tick>=100);
});
