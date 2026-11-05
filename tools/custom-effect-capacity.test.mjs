/** Production completion/persistence paths with deterministic API doubles, not BDS evidence. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {world,system,Player,ItemStack,registerFixtureItem} from '@minecraft/server';
import {ExtensionRegistry} from '../runtime/BP/scripts/core/registry.js';
import {CUSTOM_STATUS_KEY,readStatus,activeStatus} from '../runtime/BP/scripts/core/custom-effects.js';
import {statusNow,clearCustomEffects} from '../runtime/BP/scripts/bedrock/custom-effects.js';
import {completeCocktail,mixologyDiagnostics} from '../runtime/BP/scripts/bedrock/mixology.js';
import {completeDrink} from '../runtime/BP/scripts/bedrock/drink-effects.js';

const registry=new ExtensionRegistry({recipes:[],fluids:[],itemExists:()=>true});
const packs=['capacity_left','capacity_right'].map(source=>{
 const item=source+':cocktail';registerFixtureItem(item);
 // Two ordinary addon descriptors can each supply sixteen independent effects.
 // Their combined state must not prevent an unrelated Tavern bottle from working.
 const effects=Array.from({length:16},(_,i)=>({id:source+':effect_'+i,mode:'timed'}));
 registry.install({api:1,source,version:'1.0.0',effects,content:[{kind:'cocktail',item,block:source+':cup',effects:effects.map(({id})=>({effect:id,duration:600,amplifier:0,probability:1}))}]});
 return {item,effects};
});
let serial=0;
const player=()=>new Player('effect-capacity-'+(++serial),world.getDimension('overworld'));
function drink(p,id,complete){
 const itemStack=new ItemStack(id);p.inventory.setItem(p.selectedSlotIndex,itemStack);
 const result=complete({source:p,itemStack},()=>0);
 assert.equal(p.inventory.getItem(p.selectedSlotIndex).typeId,id.startsWith('kaleidoscope_tavern:')?'kaleidoscope_tavern:empty_bottle':'kaleidoscope_tavern:empty_glassware');
 system.currentTick+=32;return result;
}
function fill(p){for(const pack of packs)drink(p,pack.item,completeCocktail);}

test('two registered addons and subsequent Tavern bottles retain every completed effect beyond 32 rows',()=>{
 const p=player(),errors=mixologyDiagnostics.effectErrors.length;fill(p);
 assert.equal(statusNow(p).entries.length,32);
 for(const quality of [3,5,6]){
  const outcomes=drink(p,'kaleidoscope_tavern:glowflower_brew_q'+quality,completeDrink);
  assert(outcomes.some(row=>row.effect==='kaleidoscope_tavern:vision'&&row.status==='APPLIED_CUSTOM'));
  assert(!outcomes.some(row=>row.status==='ENGINE_REJECTED'));
 }
 const state=statusNow(p),vision=state.entries.filter(row=>row.id==='kaleidoscope_tavern:vision');
 assert.equal(state.entries.length,36);assert.deepEqual(vision.map(row=>row.amplifier),[0,1,2]);
 assert.equal(activeStatus(state,'kaleidoscope_tavern:vision').amplifier,2);
 assert.equal(mixologyDiagnostics.effectErrors.length,errors);clearCustomEffects(p);
});

test('saved state beyond 32 rows loads on a new entity handle, resumes online time and clears normally',()=>{
 const original=player();fill(original);drink(original,'kaleidoscope_tavern:glowflower_brew_q6',completeDrink);
 const raw=original.getDynamicProperty(CUSTOM_STATUS_KEY),saved=readStatus(raw);
 assert.equal(saved.entries.length,34);
 // A fresh handle has no adapter clock/cache. Offline time remains paused.
 system.currentTick+=5000;const reloaded=player();reloaded.setDynamicProperty(CUSTOM_STATUS_KEY,raw);
 assert.deepEqual(statusNow(reloaded),saved);
 system.currentTick+=20;
 assert.equal(activeStatus(statusNow(reloaded),'kaleidoscope_tavern:vision').ticks,activeStatus(saved,'kaleidoscope_tavern:vision').ticks-20);
 clearCustomEffects(reloaded);assert.deepEqual(statusNow(reloaded).entries,[]);
 assert.deepEqual(readStatus(reloaded.getDynamicProperty(CUSTOM_STATUS_KEY)).entries,[]);clearCustomEffects(original);
});

test('larger saved arrays still reject malformed effects, durations and amplifiers',()=>{
 const rows=packs.flatMap(pack=>pack.effects.map(({id})=>({id,ticks:12000,amplifier:0})));
 rows.push({id:'kaleidoscope_tavern:vision',ticks:14400,amplifier:2});
 for(const invalid of [{id:'bad id'},{ticks:0},{amplifier:256}]){
  const entries=structuredClone(rows);Object.assign(entries.at(-1),invalid);
  assert.throws(()=>readStatus(JSON.stringify({schema:1,entries})));
 }
});
