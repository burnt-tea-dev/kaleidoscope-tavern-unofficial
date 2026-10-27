/** Small public contracts; clean author archives are exercised privately. No native acceptance claims. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {world,system,Player,GameMode,ItemStack,registerFixtureItem} from '@minecraft/server';
import {ExtensionRegistry} from '../runtime/BP/scripts/core/registry.js';
import {TRANSPORT_LIMITS,EVENTS} from '../runtime/BP/scripts/core/transport.js';
import {installExtensionHost} from '../runtime/BP/scripts/bedrock/extension-host.js';
import {buildCookeryGuidePayload} from '../runtime/BP/scripts/data/cookery-guide-payload.js';
import {GUIDE_ROOTS} from '../runtime/BP/scripts/data/guide-navigation.js';
import {BUILTIN_RECIPES} from '../runtime/BP/scripts/data/recipes.js';
import {SHAKER_RECIPES} from '../runtime/BP/scripts/data/mixology.js';
import {FLUIDS} from '../runtime/BP/scripts/data/fluids.js';
import {interact} from '../runtime/BP/scripts/core/machines.js';
import {machineKey} from '../runtime/BP/scripts/core/storage.js';
import {createBarrel,operate,tickBarrel,setRegistry,installMachineEvents,TEST_ACCESS} from '../runtime/BP/scripts/bedrock/machines.js';
import {JAVA_PLACEMENT_TEST} from '../runtime/BP/scripts/bedrock/java-placement-router.js';

const source='current_fixture',N=source+':',boosterItem=N+'mead_essence';
const labels=text=>({en_US:text,zh_CN:text,zh_TW:text});
const baseRegistry=()=>new ExtensionRegistry({fluids:FLUIDS,recipes:[...BUILTIN_RECIPES,...SHAKER_RECIPES]});
const booster={item:boosterItem,boost:1,firstBoost:2,maxQuality:6,cooldownTicks:600,damage:1,consume:false};
const meadItem='kaleidoscope_dim_wine:mead_essence',qualityUpKey='kaleidoscope_tavern.message.barrel_quality_up';
const qualityUpMessage={rawtext:[{text:'§a'},{translate:qualityUpKey},{text:'§r'}]};

test('guide pages count unique recipe references and retain the distinct-recipe limit',()=>{
 const r=baseRegistry();
 const recipes=Array.from({length:33},(_,i)=>({id:N+'wine_'+i,kind:'barrel',fluid:'minecraft:water',ingredients:[['minecraft:apple']],output:{item:N+'drink_'+i}}));
 const page={id:N+'wine',title:labels('Wine'),body:labels('Age in a barrel.')};
 r.install({api:1,source,version:'1.0.0',recipes,pages:[{...page,recipeIds:Array(33).fill(recipes[0].id)}]});
 assert.deepEqual(r.extensions.get(source).pages[0].recipeIds,[recipes[0].id]);
 assert.throws(()=>r.install({api:1,source,version:'1.0.1',recipes,pages:[{...page,recipeIds:recipes.map(recipe=>recipe.id)}]}),/TOO_MANY_PAGE_RECIPES/);
 assert.deepEqual(r.extensions.get(source).pages[0].recipeIds,[recipes[0].id]);
});

test('current transport negotiation advertises the same limits used by the receiver',()=>{
 const host=installExtensionHost(baseRegistry());host.ready();
 const ready=JSON.parse(system.sent.filter(event=>event.id===EVENTS.ready).at(-1).message);
 assert.equal(ready.maxPayloadBytes,TRANSPORT_LIMITS.dataBytes);assert.equal(ready.maxParts,TRANSPORT_LIMITS.maxParts);assert.equal(ready.maxPacketBytes,TRANSPORT_LIMITS.packetBytes);
});

test('declared ingredient groups and omitted fluid titles reach the existing recipe and shared guide consumers',()=>{
 const r=baseRegistry(),fluid=N+'juice',filled=N+'juice_bucket',drink=N+'wine_q1';
 r.install({api:1,source,version:'1.0.0',
  fluids:[{id:fluid,filled,visuals:{barrel:N+'barrel_liquid',pressing_tub:N+'press_liquid'}}],
  itemGroups:[{id:N+'flowers',items:['minecraft:dandelion','minecraft:poppy']}],
  guideCategories:[{id:'tavern'},{id:'brewing',parent:'tavern'},{id:'pressing',parent:'tavern'},{id:'cookery'},{id:'millstone',parent:'cookery'},{id:'decorations'},{id:'string_lights',parent:'decorations'}],
  recipes:[{id:N+'barrel/wine',kind:'barrel',fluid,ingredients:[['minecraft:glowstone_dust'],[{group:N+'flowers'}]],output:{byQuality:Array.from({length:6},(_,i)=>N+'wine_q'+(i+1))}}],
  pages:[{id:filled,category:'pressing',title:labels('Reviewed Juice Bucket'),body:labels('Collect the juice.')},{id:N+'wine',category:'brewing',title:labels('Reviewed Wine'),body:labels('Age it in the barrel.'),recipeIds:[N+'barrel/wine']},{id:N+'food',category:'millstone',title:labels('Reviewed Food'),body:labels('Grind it.')},{id:N+'light',category:'string_lights',title:labels('Reviewed Light'),body:labels('Place it.')}]
 });
 assert.equal(r.findBarrel(fluid,[{id:'minecraft:glowstone_dust',count:1},{id:'minecraft:poppy',count:1}]).id,N+'barrel/wine');
 const p=buildCookeryGuidePayload(r);
 assert.deepEqual(p.categories.filter(category=>!category.parent).map(category=>category.id),GUIDE_ROOTS);
 assert.equal(p.entries.find(entry=>entry.id===drink).category,'barrel_addons');assert.equal(p.entries.find(entry=>entry.id===filled).category,'juices');
 assert.equal(p.entries.find(entry=>entry.id===N+'food').category,'food_crafting');assert.equal(p.entries.find(entry=>entry.id===N+'light').category,'lamps');
 for(const locale of ['zh_CN','zh_TW','en_US'])assert.equal(p.names[locale][filled],'Reviewed Juice Bucket');
 const previous=r.extensions.get(source);
 assert.throws(()=>r.install({api:1,source,version:'1.0.1',guideCategories:[{id:'loop',parent:'loop'}]}),/GUIDE_CATEGORY_CYCLE/);assert.equal(r.extensions.get(source),previous);
 r.remove(source);
});

test('optional recipe conditions are resolved before ingredient validation',()=>{
 const r=new ExtensionRegistry({fluids:FLUIDS,itemExists:item=>item!==N+'missing'});
 r.install({api:1,source,version:'1.0.0',recipes:[{id:N+'optional',kind:'barrel',fluid:'minecraft:water',ingredients:[[N+'missing']],when:{itemsAll:[N+'missing']},output:{item:N+'output'}}]});
 assert.equal(r.recipe(N+'optional'),undefined);
});

registerFixtureItem(boosterItem,1);registerFixtureItem(meadItem,1);let serial=0;
function barrel(boosterId=boosterItem){
 const r=baseRegistry();r.install({api:1,source:boosterId.split(':')[0],version:'1.0.0',barrelQualityBoosters:[{...booster,item:boosterId}]});setRegistry(r);
 const dimension=world.getDimension('overworld'),location={x:++serial*8,y:4,z:160},player=new Player('booster-'+serial,dimension),block=dimension.getBlock(location),key=machineKey(dimension.id,location);
 player.inventory.setItem(0,new ItemStack('kaleidoscope_tavern:barrel'));createBarrel(player,location);
 const state=TEST_ACCESS.store.load(key);state.fluid='minecraft:water';state.amount=4000;TEST_ACCESS.store.restoreRaw(key,JSON.stringify(state));
 operate(player,block,'lid');tickBarrel(block);tickBarrel(block);
 const item=new ItemStack(boosterId);item.nameTag='Original essence';item.setLore(['Unrelated lore']);item.setDynamicProperty('foreign:owner','kept');item.meta['minecraft:durability']={damage:0,maxDurability:10};player.inventory.setItem(0,item);
 return {r,player,block,key,load:()=>TEST_ACCESS.store.load(key),held:()=>player.inventory.getItem(0)};
}

test('a produced Java level-one batch advances once, preserves its countdown and retains exhausted native essence',()=>{
 const f=barrel(),remaining=f.load().batch.ticksRemaining,original=f.held();
 const tx=operate(f.player,f.block,'use');assert.equal(tx.state.batch.quality,2);assert.equal(f.load().batch.ticksRemaining,remaining);assert.equal(f.held().getComponent('minecraft:durability').damage,1);
 assert.equal(f.held().nameTag,original.nameTag);assert.deepEqual(f.held().getLore(),original.getLore());assert.equal(f.held().getDynamicProperty('foreign:owner'),'kept');
 assert.throws(()=>operate(f.player,f.block,'use'),/BOOSTER_COOLDOWN/);assert.equal(f.load().batch.quality,2);
 system.currentTick+=600;const almost=f.held();almost.getComponent('minecraft:durability').damage=9;f.player.inventory.setItem(0,almost);operate(f.player,f.block,'use');
 assert.equal(f.held().getComponent('minecraft:durability').damage,10);assert.equal(f.load().batch.quality,3);
 system.currentTick+=600;assert.throws(()=>operate(f.player,f.block,'use'),/BOOSTER_EXHAUSTED/);assert.equal(f.load().batch.quality,3);
 f.player.mode=GameMode.Creative;assert.throws(()=>operate(f.player,f.block,'use'),/BOOSTER_EXHAUSTED/);assert.equal(f.load().batch.quality,3);
 const reusable=f.held();reusable.getComponent('minecraft:durability').damage=4;f.player.inventory.setItem(0,reusable);operate(f.player,f.block,'use');assert.equal(f.load().batch.quality,4);assert.equal(f.held().getComponent('minecraft:durability').damage,4);
 const state=f.load();state.batch.quality=6;assert.throws(()=>interact(state,{action:'use',held:{id:boosterItem,count:1}},f.r,FLUIDS),/MAXIMUM_QUALITY/);
 assert.deepEqual(f.player.messages,[],'Other boosters do not invent success feedback');
});

test('Java Mead success emits one green translated quality notice without barrel status',()=>{
 for(const locale of ['en_US','zh_CN','zh_TW']){
  const rows=readFileSync(new URL(`../runtime/RP/texts/${locale}.lang`,import.meta.url),'utf8').split(/\r?\n/).filter(line=>line.startsWith(qualityUpKey+'='));
  assert.equal(rows.length,1);assert.ok(rows[0].slice(qualityUpKey.length+1).trim());
 }
 const f=barrel(meadItem),remaining=f.load().batch.ticksRemaining;
 assert.deepEqual(f.player.messages,[]);operate(f.player,f.block,'use');
 assert.deepEqual(f.player.messages,[qualityUpMessage]);assert.equal(f.load().batch.quality,2);assert.equal(f.load().batch.ticksRemaining,remaining);
 assert.throws(()=>operate(f.player,f.block,'use'),/BOOSTER_COOLDOWN/);assert.deepEqual(f.player.messages,[qualityUpMessage]);
 system.currentTick+=600;f.player.mode=GameMode.Creative;const original=f.held();operate(f.player,f.block,'use');
 assert.deepEqual(f.player.messages,[qualityUpMessage,qualityUpMessage]);assert.equal(f.held().getComponent('minecraft:durability').damage,original.getComponent('minecraft:durability').damage);
 system.currentTick+=600;const exhausted=f.held();exhausted.getComponent('minecraft:durability').damage=10;f.player.inventory.setItem(0,exhausted);
 assert.throws(()=>operate(f.player,f.block,'use'),/BOOSTER_EXHAUSTED/);assert.deepEqual(f.player.messages,[qualityUpMessage,qualityUpMessage]);
});

test('a failed native quality save restores the exact original essence and does not consume its cooldown',()=>{
 const f=barrel(meadItem),raw=world.getDynamicProperty(f.key),original=f.held(),save=world.setDynamicProperty;let failed=false;
 world.setDynamicProperty=function(key,value){save.call(this,key,value);if(key===f.key&&!failed){failed=true;throw Error('INJECTED_BOOST_SAVE');}};
 try{assert.throws(()=>operate(f.player,f.block,'use'),/INJECTED_BOOST_SAVE/);}finally{world.setDynamicProperty=save;}
 assert.equal(world.getDynamicProperty(f.key),raw);assert.deepEqual(f.held().meta,original.meta);assert.equal(f.held().nameTag,original.nameTag);
 assert.deepEqual(f.player.messages,[]);
 assert.doesNotThrow(()=>operate(f.player,f.block,'use'));assert.equal(f.load().batch.quality,2);assert.equal(f.held().getComponent('minecraft:durability').damage,1);
 assert.deepEqual(f.player.messages,[qualityUpMessage]);
});

test('the existing deferred machine-use route accepts essence on a closed produced barrel',()=>{
 const f=barrel();installMachineEvents();const event={player:f.player,block:f.block,cancel:false,isFirstEvent:true};
 JAVA_PLACEMENT_TEST.blockHandlers.at(-1)(event);assert.equal(event.cancel,true);assert.equal(f.load().batch.quality,1);
 system.advance(1);assert.equal(f.load().batch.quality,2);assert.equal(f.held().getComponent('minecraft:durability').damage,1);
});
