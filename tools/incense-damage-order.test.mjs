/** Real registered incense tick callback; Script API doubles, not native evidence. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {system,EntityDamageCause} from '@minecraft/server';
import {registerDecorationComponents} from '../runtime/BP/scripts/bedrock/decorations.js';
const callbacks=new Map(),NS='kaleidoscope_tavern',CURE=NS+':incense_curing';let serial=0;
registerDecorationComponents({blockComponentRegistry:{registerCustomComponent:(id,row)=>callbacks.set(id,row)},itemComponentRegistry:{registerCustomComponent(){}}});
function fixture(hp,{accepted=true,type='minecraft:zombie_villager_v2'}={}){
 const calls=[],tags=new Set(),health={currentValue:hp};
 const target={typeId:type,isValid:true,getComponent:id=>id==='minecraft:health'?health:undefined,
  hasTag:tag=>tags.has(tag),addTag:tag=>tags.add(tag),removeTag:tag=>tags.delete(tag),
  applyDamage(amount,options){calls.push({kind:'damage',amount,cause:options.cause});if(accepted)health.currentValue=Math.max(0,health.currentValue-amount);return accepted;},
  triggerEvent(event){calls.push({kind:'cure',event});}};
 const dimension={id:'minecraft:overworld',getEntities(query){assert.deepEqual(query.families,['undead']);return [target];}};
 const block={typeId:NS+':butterfly_incense',location:{x:++serial*100,y:0,z:0},dimension,permutation:{getState:key=>key===NS+':open'?1:undefined}};
 const tick=()=>callbacks.get(NS+':incense').onTick({block});
 // The existing block cadence needs an initial period witness before a pulse.
 tick();system.currentTick+=120;
 return {calls,tags,health,pulse:tick};
}

test('one-health zombie villagers receive lethal magic damage before any cure attempt',()=>{
 for(const type of ['minecraft:zombie_villager','minecraft:zombie_villager_v2']){
  const f=fixture(1,{type});f.pulse();
  assert.deepEqual(f.calls,[{kind:'damage',amount:1,cause:EntityDamageCause.magic}]);
  assert.equal(f.health.currentValue,0);assert.equal(f.tags.has(CURE),false);
 }
});
test('two-health zombie villagers start curing only after the damage leaves one health',()=>{
 const f=fixture(2);f.pulse();
 assert.deepEqual(f.calls.map(row=>row.kind),['damage','cure']);assert.equal(f.health.currentValue,1);assert(f.tags.has(CURE));
});
test('a rejected hurt still precedes the Java post-hurt cure check',()=>{
 const f=fixture(1,{accepted:false});f.pulse();
 assert.deepEqual(f.calls.map(row=>row.kind),['damage','cure']);assert.equal(f.health.currentValue,1);assert(f.tags.has(CURE));
});
test('dead undead recipients cannot be damaged or converted by the pulse',()=>{
 const f=fixture(0);f.pulse();assert.deepEqual(f.calls,[]);assert.equal(f.tags.has(CURE),false);
});
