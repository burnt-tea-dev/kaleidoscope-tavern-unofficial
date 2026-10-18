/** Synthetic extension contracts only; native BDS/client validation is separate. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {ExtensionRegistry} from '../runtime/BP/scripts/core/registry.js';
import {localeMap} from '../runtime/BP/scripts/core/util.js';
import {bottleBase,bottleBlock,isBottleBlock} from '../runtime/BP/scripts/core/extension-content.js';
import {bottlePermutationBlock,bottlePermutationStates,bottleDisplayMatches,legacyBottleDisplay} from '../runtime/BP/scripts/core/bottle-display-schema.js';
import {nativeStorageAnchor,checkNativeStorageOwner} from '../runtime/BP/scripts/core/native-storage-anchor.js';

const source='bottle_fixture',base=source+':wine',items=Array.from({length:6},(_,i)=>base+'_q'+(i+1));
const contract=()=>({api:1,source,version:'1.0.0',content:[{kind:'bottle',base,block:base,items:items.slice(),qualityBlocks:items.slice(),maxCount:4,compact:true,visualKind:1100,effects:Array.from({length:6},()=>[]),displayStates:{count:'kaleidoscope_tavern:count',facing:'minecraft:cardinal_direction'}}]});
const registry=()=>new ExtensionRegistry({itemExists:()=>true});
const block=(typeId,states)=>({typeId,permutation:{getState:key=>states[key]}});

test('locale maps preserve every supplied language and retain shape, length and count bounds',()=>{
 const locales=['bg_BG','cs_CZ','da_DK','de_DE','el_GR','en_GB','en_US','es_ES','es_MX','fi_FI','fr_CA','fr_FR','hu_HU','id_ID','it_IT','ja_JP','ko_KR','nb_NO','nl_NL','pl_PL','pt_BR','pt_PT','ru_RU','sk_SK','sv_SE','tr_TR','uk_UA','zh_CN','zh_TW'];
 const original=Object.fromEntries(locales.map(locale=>[locale,'Original '+locale]));
 assert.deepEqual(localeMap(original),original);
 for(const bad of [[],null,{},JSON.parse('{"__proto__":"bad"}'),{'en-US':'bad'},{en_US:'x'.repeat(8193)}])assert.throws(()=>localeMap(bad));
 assert.throws(()=>localeMap(Object.fromEntries(Array.from({length:65},(_,i)=>['a'+String.fromCharCode(97+i%26)+String.fromCharCode(97+Math.floor(i/26))+'_US','x']))),/LOCALE_LIMIT/);
});

test('native cardinal states and topmost mixed quality select the exact block and storage owner',()=>{
 const r=registry();r.install(contract());
 try{
  for(let facing=0;facing<4;facing++)for(let quality=1;quality<=6;quality++){
   const state={schema:1,revision:0,base,facing,items:[items[5],items[0],items[quality-1]]};
   const id=bottlePermutationBlock(state),states=bottlePermutationStates(state),placed=block(id,states);
   assert.equal(id,items[quality-1]);assert.equal(bottleBase(id),base);assert(isBottleBlock(id));
   assert.deepEqual(states,{'kaleidoscope_tavern:count':3,'minecraft:cardinal_direction':['south','west','north','east'][facing]});
   assert(bottleDisplayMatches(placed,state));assert(!bottleDisplayMatches(block(items[quality%6],states),state));
   const key='kt:bottles/overworld/1_2_3',raw=JSON.stringify(state),anchor=nativeStorageAnchor(key,undefined,()=>raw);
   assert.equal(anchor.type,id);assert.deepEqual(anchor.displayIds,state.items);
   const owner={...placed,dimension:{id:'minecraft:overworld'},location:{x:1,y:2,z:3}};
   assert.equal(checkNativeStorageOwner(anchor,owner,[...state.items,...Array(6).fill(null)]),true);
  }
 }finally{r.remove(source);}
});

test('quality-block legacy reads recover only declared count, facing and exact quality without writing',()=>{
 const r=registry();r.install(contract());
 try{
  for(let quality=1;quality<=6;quality++){
   const states={'kaleidoscope_tavern:count':2,'minecraft:cardinal_direction':'east'},placed=block(items[quality-1],states);
   assert.deepEqual(legacyBottleDisplay(placed),{schema:1,revision:0,base,facing:3,items:[items[quality-1],items[quality-1]]});
   assert.equal(legacyBottleDisplay(block(items[quality-1],{...states,'minecraft:cardinal_direction':'sideways'})),undefined);
  }
  const creative=block(base,{'kaleidoscope_tavern:count':1,'minecraft:cardinal_direction':'south'}),restored=legacyBottleDisplay(creative);
  assert.deepEqual(restored.items,[items[5]]);assert(bottleDisplayMatches(creative,restored));
 }finally{r.remove(source);}
});

test('invalid quality layouts and foreign state keys reject atomically; replacement clears stale aliases',()=>{
 const r=registry();r.install(contract());const before=r.extensions.get(source);
 for(const mutate of [
  d=>d.qualityBlocks[0]='foreign:wine',d=>d.qualityBlocks[0]=d.qualityBlocks[1],d=>d.qualityBlocks.pop(),
  d=>d.displayStates.count='foreign:count',d=>d.displayStates.facing='minecraft:facing_direction',d=>delete d.displayStates,
  d=>d.displayStates.extra='bottle_fixture:extra',
 ]){const next=contract();mutate(next.content[0]);assert.throws(()=>r.install(next));assert.equal(r.extensions.get(source),before);}
 const aliasCollision=contract(),other=structuredClone(aliasCollision.content[0]);other.base=source+':other';other.block=source+':other';aliasCollision.content.push(other);
 assert.throws(()=>r.install(aliasCollision),/DUPLICATE_CONTENT_BLOCK/);assert.equal(r.extensions.get(source),before);
 const replacement=contract();delete replacement.content[0].qualityBlocks;replacement.content[0].displayStates={count:source+':count',facing:source+':facing',quality:source+':quality'};
 r.install(replacement);assert.equal(bottleBase(items[0]),undefined);assert(!isBottleBlock(items[0]));assert.equal(bottleBlock(base),base);
 const state={schema:1,revision:0,base,facing:2,items:[items[3]]};
 assert.deepEqual(bottlePermutationStates(state),{[source+':count']:1,[source+':facing']:2,[source+':quality']:4});
 r.remove(source);assert.equal(bottleBase(base),undefined);
});
