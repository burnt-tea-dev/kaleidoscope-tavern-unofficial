/** Actual adapter callbacks and independent source property samples. No engine. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {pressingVisualId, pressingIngredientVisuals, configurePressingIngredients} from '../runtime/BP/scripts/bedrock/pressing-ingredients.js';
import {PRESSING_INGREDIENT_KINDS} from '../runtime/BP/scripts/data/pressing-ingredient-visuals.js';
const N='kaleidoscope_tavern:', reference=JSON.parse(readFileSync(new URL('../data/pressing-ingredient-source/slot-properties.json',import.meta.url)));
const state=(id=N+'grape',count=64)=>({kind:'pressing_tub',slots:[{id,count}]});
function configure(helper,s=state(),face='up',cardinal='north'){
 const properties={},entity={typeId:pressingVisualId(helper),setProperty:(k,v)=>{assert.equal(properties[k],undefined,'Duplicate property write');properties[k]=v;}};
 const core={location:reference.location,permutation:{getState:k=>k==='minecraft:block_face'?face:cardinal}};
 configurePressingIngredients(entity,core,s);
 return properties;
}
test('all accepted food IDs use the existing helper ranges and exact kind route',()=>{
 assert.equal(Object.keys(PRESSING_INGREDIENT_KINDS).length,27);
 for(const [id,kind] of Object.entries(PRESSING_INGREDIENT_KINDS))for(let count=1;count<=64;count++){
  const ids=pressingIngredientVisuals(state(id,count));
  assert.equal(ids.length,Math.ceil(count/8));
  assert.equal(new Set(ids).size,ids.length);
  ids.forEach((id,i)=>assert.equal(id,pressingVisualId(i)));
  const last=configure(ids.length-1,state(id,count));
  assert.equal(last[N+'grape_kind'],kind);
  assert.equal(last[N+'fill_stage'],count-(ids.length-1)*8);
  assert.equal(Object.keys(last).length,4+last[N+'fill_stage']*3);
 }
});
test('all 64 slots retain independent source-seeded packed properties',()=>{
 assert.equal(reference.slots.length,64);
 for(let helper=0;helper<8;helper++){
  const actual=configure(helper);
  for(const row of reference.slots.filter(x=>x.helper===helper)){
   assert.equal(row.global,helper*8+row.local);
   for(const [name,expected] of Object.entries(row.properties)){
    const got=actual[N+name];
    if(name.startsWith('y'))assert.ok(Math.abs(got-expected)<1e-12,`${row.global}: ${got} vs ${expected}`);
    else assert.equal(got,expected);
   }
  }
 }
});
test('tilt facing changes only existing frame flags, not ingredient centers or scale',()=>{
 for(let helper=0;helper<8;helper++){
  const upright=configure(helper),base={...upright};delete base[N+'tilt'];delete base[N+'facing'];
  ['north','east','south','west'].forEach((direction,i)=>{
   const actual=configure(helper,state(),direction,direction);
   assert.equal(actual[N+'tilt'],1);assert.equal(actual[N+'facing'],i);
   delete actual[N+'tilt'];delete actual[N+'facing'];assert.deepEqual(actual,base);
  });
 }
});
test('empty, unknown and non-pressing items do not acquire card helpers',()=>{
 assert.deepEqual(pressingIngredientVisuals({kind:'pressing_tub',slots:[]}),[]);
 assert.deepEqual(pressingIngredientVisuals(state('other:unknown')),[]);
 assert.deepEqual(pressingIngredientVisuals({...state(),kind:'barrel'}),[]);
 assert.deepEqual(pressingIngredientVisuals(state(N+'grape',0)),[]);
 const entity={typeId:N+'unrelated',setProperty(){assert.fail('Unrelated entity mutated');}};
 configurePressingIngredients(entity,{},state());
});
