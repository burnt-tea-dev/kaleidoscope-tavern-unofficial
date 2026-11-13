import test from 'node:test';
import assert from 'node:assert/strict';
import {ExtensionRegistry} from '../runtime/BP/scripts/core/registry.js';
import {installedBarrelRecipeSources} from '../runtime/BP/scripts/core/installed-recipe-sources.js';
import {newMachine,advanceBarrel,interact} from '../runtime/BP/scripts/core/machines.js';
import {BUILTIN_RECIPES} from '../runtime/BP/scripts/data/recipes.js';
import {FLUIDS} from '../runtime/BP/scripts/data/fluids.js';

// Recipe fields from World Liquor W129 payload, source 7edcb3589b849ac54533cd78b8c17d9e1d6a4b1b.
const source='kaleidoscope_world_liquor';
const recipe={id:source+':barrel/absolut_vodka',kind:'barrel',fluid:'minecraft:water',ingredients:[['minecraft:wheat'],['minecraft:wheat_seeds']],carrier:'kaleidoscope_tavern:empty_bottle',unitTime:2400,output:{byQuality:Array.from({length:6},(_,i)=>source+':absolut_vodka_q'+(i+1))}};
const payload={api:1,source,version:'0.1.129',recipes:[recipe]};
function registry(installed=true){return new ExtensionRegistry({recipes:BUILTIN_RECIPES,fluids:FLUIDS,expectedBarrelRecipeSources:installedBarrelRecipeSources(id=>installed&&id===source+':absolut_vodka_q1')});}
function barrel(){const state=newMachine('barrel','saved-before-recipe-registration');Object.assign(state,{open:false,fluid:recipe.fluid,amount:4000,nativeItems:1});recipe.ingredients.forEach((options,i)=>state.slots[i]={id:options[0],count:4});return state;}

test('installed source waits without consuming stored ingredients, then starts the actual vodka recipe',()=>{
 const host=registry(),state=barrel(),before=JSON.stringify(state);
 for(let i=0;i<20;i++)assert.equal(advanceBarrel(state,host),state,'no transition means no native inventory or storage commit');
 assert.equal(JSON.stringify(state),before);
 host.install({api:1,source:'unrelated_addon',version:'1.0.0'});
 assert.equal(advanceBarrel(state,host),state);
 assert.throws(()=>host.install({...payload,recipes:[{...recipe,output:{item:'invalid'}}]}));
 assert.equal(advanceBarrel(state,host),state,'rejected registration cannot release the barrier');
 host.install(payload);const ready=advanceBarrel(state,host);
 assert.equal(ready.batch.recipeId,recipe.id);assert.equal(ready.batch.remaining,4);
 assert.equal(ready.batch.ticksRemaining,2400);assert.deepEqual(ready.batch.output,recipe.output);
 assert.equal(ready.amount,0);assert.ok(ready.slots.every(x=>!x));assert.equal(ready.nativeItems,undefined);
 assert.equal(JSON.stringify(state),before);
});

test('saved batches keep their cadence and outputs while a source is absent or removed',()=>{
 const host=registry();host.install(payload);const started=advanceBarrel(barrel(),host);
 host.remove(source);const next=advanceBarrel(started,host);
 assert.equal(next.batch.ticksRemaining,2303);assert.equal(next.batch.recipeId,recipe.id);
 assert.deepEqual(next.batch.output,started.batch.output);assert.equal(next.batch.remaining,4);
 const fresh=barrel();assert.equal(advanceBarrel(fresh,host),fresh);
 host.install(payload);assert.equal(advanceBarrel(fresh,host).batch.recipeId,recipe.id);
});

test('absent providers retain standalone vinegar fallback and each marker is probed once',()=>{
 const calls=[];assert.deepEqual(installedBarrelRecipeSources(id=>{calls.push(id);return false}),[]);
 assert.deepEqual(calls,[source+':absolut_vodka_q1',...authorSources.map(row=>row.marker)]);
 const result=advanceBarrel(barrel(),registry(false));
 assert.equal(result.batch.recipeId,'kaleidoscope_tavern:vinegar_fallback');assert.equal(result.batch.remaining,16);
 assert.equal(new ExtensionRegistry().barrelRecipesReady(),true);
});

test('after registration genuinely unmatched ingredients still ferment into vinegar',()=>{
 const host=registry();host.install(payload);const state=barrel();state.slots[0].id='minecraft:dirt';
 assert.equal(advanceBarrel(state,host).batch.recipeId,'kaleidoscope_tavern:vinegar_fallback');
});

test('builtin recipes keep working while an optional source is pending',()=>{
 const host=registry(),builtin=BUILTIN_RECIPES.find(row=>row.kind==='barrel'),state=newMachine('barrel','builtin');
 Object.assign(state,{open:false,fluid:builtin.fluid,amount:4000});
 builtin.ingredients.forEach((items,index)=>state.slots[index]={id:items[0],count:4});
 assert.equal(host.barrelRecipesReady(),false);
 assert.equal(advanceBarrel(state,host).batch.recipeId,builtin.id);
});

test('a native lookup failure during staged rebuild cannot expose an unbuilt recipe view as ready',()=>{
 const host=registry(),state=barrel(),itemTags=host.itemTags;
 host.itemTags=()=>{throw new Error('native metadata unavailable during rebuild');};
 assert.throws(()=>host.install(payload),/native metadata unavailable/);
 assert.equal(host.extensions.has(source),false,'failed staged data remains invisible');
 assert.deepEqual(host.pendingBarrelRecipeSources(),[source]);
 assert.equal(advanceBarrel(state,host),state);
 host.itemTags=itemTags;host.install(payload);
 assert.deepEqual(host.pendingBarrelRecipeSources(),[]);
 assert.equal(advanceBarrel(state,host).batch.recipeId,recipe.id);
});

// Minimal recipe fields reviewed from the clean author extensions, not a copy
// of their scripts: Orchard CF9227353, Sculk CF9317015, Dimensions Wine CF9317013.
const authorSources=[
 {source:'kaleidoscope_orchard',marker:'kaleidoscope_orchard:strawberry_wine_q1',name:'glow_honey_wine',fluid:'kaleidoscope_tavern:glow_berries_juice',ingredients:[['minecraft:honeycomb']]},
 {source:'kaleidoscope_sculk',marker:'kaleidoscope_sculk:honglan_wine_q1',name:'huadiao_wine',fluid:'kaleidoscope_tavern:gold_grape_juice',ingredients:[['kaleidoscope_cookery:rice'],['kaleidoscope_sculk:sculk_dust']]},
 {source:'kaleidoscope_dim_wine',marker:'kaleidoscope_dim_wine:abyssal_porter_q1',name:'beeswax_honey_wine',fluid:'minecraft:water',ingredients:[['minecraft:honeycomb'],['minecraft:honey_bottle']]}
];
for(const author of authorSources)test(author.source+' waits for its own late registration across host reload and retry',()=>{
 const installed=new Set([source+':absolut_vodka_q1',author.marker]);
 const make=()=>new ExtensionRegistry({recipes:BUILTIN_RECIPES,fluids:FLUIDS,expectedBarrelRecipeSources:installedBarrelRecipeSources(id=>installed.has(id))});
 const ownRecipe={...recipe,id:author.source+':barrel/'+author.name,fluid:author.fluid,ingredients:author.ingredients,output:{byQuality:Array.from({length:6},(_,i)=>author.source+':'+author.name+'_q'+(i+1))}};
 const ownPayload={api:1,source:author.source,version:'1.0.0',recipes:[ownRecipe]};
 const state=newMachine('barrel','saved-author-ingredients');Object.assign(state,{open:false,fluid:author.fluid,amount:4000,nativeItems:1});
 author.ingredients.forEach((options,i)=>state.slots[i]={id:options[0],count:4});
 const saved=JSON.stringify(state);
 for(const host of [make(),make()]){
  const loaded=JSON.parse(saved);host.install(payload);
  assert.deepEqual(host.pendingBarrelRecipeSources(),[author.source],'World Liquor registering does not release another source');
  for(let i=0;i<200;i++)assert.equal(advanceBarrel(loaded,host),loaded,'no timeout converts missing-provider inputs into vinegar');
  assert.equal(JSON.stringify(loaded),saved);
  assert.throws(()=>host.install({...ownPayload,recipes:[{...ownRecipe,output:{item:'invalid'}}]}));
  assert.equal(advanceBarrel(loaded,host),loaded,'a rejected registration keeps native ingredients intact');
  host.install(ownPayload);const started=advanceBarrel(loaded,host);
  assert.equal(started.batch.recipeId,ownRecipe.id);assert.deepEqual(started.batch.output,ownRecipe.output);assert.equal(started.batch.remaining,4);
  host.remove(author.source);assert.equal(advanceBarrel(loaded,host),loaded);
  assert.equal(advanceBarrel(started,host).batch.ticksRemaining,2303,'an existing batch still ages while the provider is absent');
  const completed=JSON.parse(JSON.stringify(started));Object.assign(completed.batch,{quality:6,ticksRemaining:0});
  assert.equal(advanceBarrel(completed,host),completed,'saved completed batches remain complete without their provider');
  assert.deepEqual(interact(completed,{action:'extract',held:{id:completed.batch.carrier,count:1}},host,FLUIDS).give,[{id:ownRecipe.output.byQuality[5],count:1}]);
  host.install(ownPayload);assert.equal(advanceBarrel(loaded,host).batch.recipeId,ownRecipe.id);
 }
});
