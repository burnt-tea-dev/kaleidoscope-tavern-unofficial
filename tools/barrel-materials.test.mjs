/** Real render adapters and pack resources; no Minecraft client/simulated players. */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {runInNewContext} from 'node:vm';
import {barrelIngredientVisuals,configureBarrelIngredients} from '../runtime/BP/scripts/bedrock/barrel-ingredients.js';
import {BARREL_INGREDIENT_KINDS as kinds} from '../runtime/BP/scripts/data/barrel-ingredient-visuals.js';
import {BUILTIN_RECIPES} from '../runtime/BP/scripts/data/recipes.js';
const N='kaleidoscope_tavern';
const read=p=>JSON.parse(fs.readFileSync(new URL('../'+p,import.meta.url)));
const catalog=read('data/barrel-materials.json').materials;
const controllers=read('runtime/RP/render_controllers/runtime_barrel_ingredients.render_controllers.json').render_controllers;
const geometries=Object.fromEntries(['card','cube'].map(model=>[model,read(`runtime/RP/models/entity/runtime_barrel_ingredients_${model}.geo.json`)['minecraft:geometry'][0].description.identifier]));
const floatAnimations=read('runtime/RP/animations/runtime_barrel_ingredients.animation.json').animations;
const activeNames=(bindings,context)=>(bindings??[]).flatMap(entry=>typeof entry==='string'?[entry]:Object.entries(entry).filter(([,condition])=>runInNewContext(condition,context)).map(([name])=>name));
function activeControllers(description,context){
 const names=activeNames(description.render_controllers,context);assert.ok(names.length,'helper has no active render controller');
 return names.map(name=>{assert.ok(controllers[name],'helper points to an unrelated or missing barrel controller: '+name);return controllers[name];});
}
const state=slots=>({kind:'barrel',open:true,slots});
const core={location:{x:354,y:56,z:-573}};
function entity(slot){
 const properties=read(`runtime/BP/entities/barrel_ingredients_${slot}_visual.json`)['minecraft:entity'].description.properties;
 const dp=new Map(),values={};
 return {typeId:N+`:barrel_ingredients_${slot}_visual`,values,getDynamicProperty:k=>dp.get(k),setDynamicProperty:(k,v)=>dp.set(k,v),setProperty(k,v){
  const p=properties[k];assert.ok(p,'Property exists: '+k);assert.ok(Number.isFinite(v)&&v>=p.range[0]&&v<=p.range[1],`${k}=${v} in ${p.range}`);
  if(p.type==='int')assert.ok(Number.isInteger(v));values[k]=v;
 }};
}
test('catalogue helpers connect their native IDs to current geometry, texture and float animation',()=>{
 assert.equal(catalog.length,61);assert.equal(new Set(catalog.map(r=>r.id)).size,catalog.length);
 for(let slot=0;slot<4;slot++){
  const bp=read(`runtime/BP/entities/barrel_ingredients_${slot}_visual.json`)['minecraft:entity'].description;
  const rp=read(`runtime/RP/entity/runtime_barrel_ingredients_${slot}.entity.json`)['minecraft:client_entity'].description,e=entity(slot);
  assert.equal(rp.identifier,bp.identifier);assert.equal(rp.identifier,e.typeId);
  catalog.forEach((row,i)=>{
   const slots=Array.from({length:4},(_,j)=>j===slot?{id:row.id,count:1}:null),s=state(slots);
   assert.ok(barrelIngredientVisuals(s).includes(rp.identifier));configureBarrelIngredients(e,core,s);
   const context={q:{property:name=>e.values[name]},Geometry:rp.geometry};
   assert.equal(kinds[row.id],i+1);assert.equal(rp.textures[`kind_${i+1}`],row.texture);
   for(const rc of activeControllers(rp,context)){
    assert.equal(rc.arrays.textures['Array.kind'].length,catalog.length);
    assert.equal(rc.arrays.textures['Array.kind'][i],`Texture.kind_${i+1}`);
    assert.equal(runInNewContext(rc.geometry,context),geometries[row.model],row.id+' selects its source model');
   }
   assert.ok(activeNames(rp.scripts?.animate,context).some(alias=>Object.hasOwn(floatAnimations,rp.animations?.[alias])),'helper does not run its float animation');
  });
 }
});
test('only ordinary ice selects the source translucent material in all four barrel slots',()=>{
 // Official Java 1.21.1 ICE uses RenderType.translucent; its 16x16 texture
 // and Mojang's Bedrock ice texture both have alpha=190 at every pixel.
 for(let slot=0;slot<4;slot++){
  const rp=read(`runtime/RP/entity/runtime_barrel_ingredients_${slot}.entity.json`)['minecraft:client_entity'].description,e=entity(slot);
  // Reuse a configured helper, including ice -> sugar, to catch a sticky
  // material after inventory changes as well as a blanket blend conversion.
  for(const row of [...catalog,{id:'minecraft:ice'},{id:'minecraft:sugar'}]){
   const slots=Array.from({length:4},(_,i)=>i===slot?{id:row.id,count:1}:null);
   configureBarrelIngredients(e,core,state(slots));
   const context={q:{property:name=>e.values[name]},Material:rp.materials};
   for(const rc of activeControllers(rp,context)){
    const material=runInNewContext(rc.materials[0]['*'],context);
    assert.equal(material,row.id==='minecraft:ice'?'entity_alphablend':'entity_alphatest',`${row.id} in slot ${slot}`);
   }
  }
 }
});
for(const row of catalog)test(row.id+' renders in all four slots, counts 1..16 stay in native property ranges',()=>{
 for(let slot=0;slot<4;slot++)for(let count=1;count<=16;count++){
  const slots=Array(4).fill(null).map((_,i)=>i<=slot?{id:row.id,count}:null),s=state(slots),e=entity(slot);
  assert.ok(barrelIngredientVisuals(s).includes(e.typeId));configureBarrelIngredients(e,core,s);
  assert.equal(e.values[N+':kind'],kinds[row.id]);assert.equal(e.values[N+':count'],Math.floor(count/2)+1);
 }
});
test('video regression: rice panicle and wheat both visible; reconfiguration updates count and material',()=>{
 const s=state([{id:'kaleidoscope_cookery:rice_panicle',count:9},{id:'minecraft:wheat',count:16},null,null]);
 assert.deepEqual(barrelIngredientVisuals(s),[N+':barrel_ingredients_0_visual',N+':barrel_ingredients_1_visual']);
 const e=entity(0);configureBarrelIngredients(e,core,s);assert.equal(e.values[N+':count'],5);
 s.slots[0]={id:'minecraft:wheat',count:1};configureBarrelIngredients(e,core,s);assert.equal(e.values[N+':kind'],kinds['minecraft:wheat']);assert.equal(e.values[N+':count'],1);
 s.slots[0]=null;assert.deepEqual(barrelIngredientVisuals(s),[N+':barrel_ingredients_1_visual']);
 s.open=false;assert.deepEqual(barrelIngredientVisuals(s),[]);
});
test('unknown external item remains an explicit renderer limitation, not a fake substitute',()=>{
 assert.deepEqual(barrelIngredientVisuals(state([{id:'external:unregistered',count:16},null,null,null])),[]);
});
test('every current paired barrel recipe option has a render definition',async()=>{
 assert.ok(process.env.LIQUOR_SOURCE,'LIQUOR_SOURCE is required: never skip paired coverage');
 const {payload}=await import(pathToFileURL(path.resolve(process.env.LIQUOR_SOURCE,'runtime/BP/scripts/payload.js')).href);
 const recipes=[...BUILTIN_RECIPES,...payload.recipes].filter(r=>r.kind==='barrel');
 assert.equal(recipes.length,42);
 for(const recipe of recipes)for(const options of recipe.ingredients)for(const id of options)assert.ok(kinds[id],`${recipe.id}: missing ${id}`);
});
