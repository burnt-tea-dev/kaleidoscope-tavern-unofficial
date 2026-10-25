/** Real owned callbacks with a deterministic API double; no native/client claim. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {world,Player,ItemStack,registerFixtureItem} from '@minecraft/server';
import {ExtensionRegistry} from '../runtime/BP/scripts/core/registry.js';
import {placeBottle,takeBottles,registerBottleComponents} from '../runtime/BP/scripts/bedrock/bottles.js';
import {bottleKey} from '../runtime/BP/scripts/core/bottles.js';
const source='adapter_fixture',base=source+':wine',items=Array.from({length:6},(_,i)=>base+'_q'+(i+1));
for(const id of [...items,base])registerFixtureItem(id);
const registry=new ExtensionRegistry({itemExists:()=>true});
registry.install({api:1,source,version:'1.0.0',content:[{kind:'bottle',base,block:base,items,qualityBlocks:items,maxCount:4,compact:true,visualKind:1101,effects:Array.from({length:6},()=>[]),displayStates:{count:'kaleidoscope_tavern:count',facing:'minecraft:cardinal_direction'}}]});
const dimension=world.getDimension('overworld');
const components=new Map();registerBottleComponents({blockComponentRegistry:{registerCustomComponent:(id,component)=>components.set(id,component)}});

test('native mixed-quality placement/pickup retains exact stacks and selects each newly exposed top block',()=>{
 const position={x:16,y:2,z:0},player=new Player('quality-block-pickup',dimension);player.location={...position};
 const block=dimension.getBlock(position),first=new ItemStack(items[0]),second=new ItemStack(items[5]);
 first.nameTag='Original first';first.setLore(['first opaque lore']);second.nameTag='Original top';second.setLore(['top opaque lore']);
 player.inventory.setItem(0,first);placeBottle(player,position);assert.equal(block.typeId,items[0]);
 player.inventory.setItem(0,second);placeBottle(player,position);assert.equal(block.typeId,items[5]);assert.equal(block.permutation.getState('minecraft:cardinal_direction'),'south');
 assert.equal(player.inventory.getItem(0),undefined);takeBottles(player,block);assert.equal(block.typeId,items[0]);
 assert.equal(player.inventory.getItem(0).nameTag,second.nameTag);assert.deepEqual(player.inventory.getItem(0).getLore(),second.getLore());
 player.inventory.setItem(0,undefined);takeBottles(player,block);assert.equal(block.typeId,'minecraft:air');
 assert.equal(player.inventory.getItem(0).typeId,items[0]);assert.equal(player.inventory.getItem(0).nameTag,first.nameTag);assert.deepEqual(player.inventory.getItem(0).getLore(),first.getLore());
});

test('registered placement guard allows an empty location and preserves saved or orphaned native ownership',()=>{
 const guard=components.get('kaleidoscope_tavern:placeable_drink_placement_guard');assert.equal(typeof guard?.beforeOnPlayerPlace,'function');
 const block=dimension.getBlock({x:20,y:2,z:0}),key=bottleKey(dimension.id,block.location);
 const fresh={block,cancel:false};guard.beforeOnPlayerPlace(fresh);assert.equal(fresh.cancel,false);
 const raw=JSON.stringify({schema:1,revision:0,base,facing:0,items:[items[2]]});world.setDynamicProperty(key,raw);
 const occupied={block,cancel:false};guard.beforeOnPlayerPlace(occupied);assert.equal(occupied.cancel,true);assert.equal(world.getDynamicProperty(key),raw);
 world.setDynamicProperty(key,undefined);world.setDynamicProperty('kt:native_required/'+key,true);
 const orphaned={block,cancel:false};guard.beforeOnPlayerPlace(orphaned);assert.equal(orphaned.cancel,true);assert.equal(world.getDynamicProperty('kt:native_required/'+key),true);
 world.setDynamicProperty('kt:native_required/'+key,undefined);
 const invalid={get block(){throw Error('unloaded');},cancel:false};guard.beforeOnPlayerPlace(invalid);assert.equal(invalid.cancel,true);
});

test('a generic preview keeps its original native stack when a quality bottle is placed above it and removed',()=>{
 const position={x:24,y:2,z:0},player=new Player('generic-bottle-pickup',dimension);player.location={...position};
 const block=dimension.getBlock(position),generic=new ItemStack(base);generic.nameTag='Original preview';generic.setLore(['Original preview lore']);
 player.inventory.setItem(0,generic);placeBottle(player,position);assert.equal(block.typeId,base);
 player.inventory.setItem(0,new ItemStack(items[0]));placeBottle(player,position);assert.equal(block.typeId,items[0]);
 takeBottles(player,block);assert.equal(block.typeId,base);assert.equal(player.inventory.getItem(0).typeId,items[0]);
 player.inventory.setItem(0,undefined);takeBottles(player,block);assert.equal(block.typeId,'minecraft:air');
 assert.equal(player.inventory.getItem(0).typeId,base);assert.equal(player.inventory.getItem(0).nameTag,generic.nameTag);assert.deepEqual(player.inventory.getItem(0).getLore(),generic.getLore());
});
