/** Optional pack content. No addon is required until it registers a descriptor. */
import {BOTTLES} from '../data/bottles.js';
import {DRINK_EFFECTS} from '../data/drink-effects.js';
import {COCKTAILS} from '../data/mixology.js';
const drinks=new Map(),blocks=new Map(),sources=new Map(),foundations=new Map(),effectDefinitions=new Map(),itemParticles=new Map(),furnitureDefinitions=new Map();
export const externalDrink=item=>drinks.get(item);
export const bottleBlock=(base,quality)=>BOTTLES[base]?.qualityBlocks?.[quality-1]??BOTTLES[base]?.block??`kaleidoscope_tavern:bottle_${base}`;
export const bottleBase=block=>blocks.get(block)??(block?.startsWith('kaleidoscope_tavern:bottle_')?block.slice('kaleidoscope_tavern:bottle_'.length):undefined);
export const cupBlock=item=>COCKTAILS[item]?.block??`kaleidoscope_tavern:cup_${item.split(':')[1]}`;
export const isBottleBlock=block=>[...Object.keys(BOTTLES)].some(base=>bottleBlock(base)===block||BOTTLES[base].qualityBlocks?.includes(block));
// Reverse lookup must use the exact clicked block, never a nearby station.
export const cupItem=block=>block==='kaleidoscope_tavern:cup_empty_glassware'?'kaleidoscope_tavern:empty_glassware':Object.keys(COCKTAILS).find(item=>cupBlock(item)===block);
export const isCupBlock=block=>cupItem(block)!==undefined;
export const externalVisual=(helper,item)=>externalDrink(item)?.visuals?.[helper.split(':')[1]]??helper;
export const isExternalVisual=(type,helper)=>type===helper||[...drinks.values()].some(d=>d.visuals?.[helper.split(':')[1]]===type);
export function installContent(source,content=[],foundation={}){
 for(const row of foundations.get(source)?.furniture??[])furnitureDefinitions.delete(row.block);
 for(const row of foundation.furniture??[])furnitureDefinitions.set(row.block,row);
 for(const row of foundations.get(source)?.effects??[])effectDefinitions.delete(row.id);
 for(const row of foundations.get(source)?.itemParticles??[])itemParticles.delete(row.item);
 for(const row of foundation.itemParticles??[])itemParticles.set(row.item,row.particle);
 foundations.set(source,foundation);for(const row of foundation.effects??[])effectDefinitions.set(row.id,row);
 for(const old of sources.get(source)??[]){for(const item of old.items??[])drinks.delete(item);if(old.genericItem)drinks.delete(old.genericItem);for(const block of [old.block,...old.qualityBlocks??[]])blocks.delete(block);delete BOTTLES[old.base];delete DRINK_EFFECTS[old.base];if(old.item)delete COCKTAILS[old.item];}
 sources.set(source,content);
 for(const d of content){
  if(d.kind==='bottle'){
   BOTTLES[d.base]={maxCount:d.maxCount,qualities:6,block:d.block,qualityBlocks:d.qualityBlocks,items:d.items,genericItem:d.genericItem,displayStates:d.displayStates,color:d.color};DRINK_EFFECTS[d.base]=d.effects;for(const block of [d.block,...d.qualityBlocks??[]])blocks.set(block,d.base);
   // The clean Creative preview has maximum effects, but keeps its exact item
   // identity through placement, storage and pickup instead of becoming q6.
   if(d.genericItem)drinks.set(d.genericItem,{...d,modNameKey:foundation.modNameKey,item:d.genericItem,quality:6,id:d.genericItem,kind:d.visualKind,creative:true});
   d.items.forEach((item,i)=>drinks.set(item,{...d,modNameKey:foundation.modNameKey,item,quality:i+1,id:item,kind:d.visualKind}));
  }else COCKTAILS[d.item]={name:d.item.split(':')[1],block:d.block,effects:d.effects};
 }
}
export function externalEffectSource(effect){const source=effect?.split(':')[0];return sources.has(source)?source:undefined;}

export const externalEffectDefinition=id=>effectDefinitions.get(id);
export const externalFurnitureDefinition=id=>furnitureDefinitions.get(id);
export const externalEffectMigrations=()=>[...foundations.entries()].filter(([,x])=>x.legacyEffectKey).map(([source,x])=>({source,key:x.legacyEffectKey,effects:x.effects}));

/** External packs supply only data; the host owns the Creative pick adapter. */
export function externalPickBlock(blockId){
 for(const value of foundations.values()){
  const rule=value.pickBlocks?.find(row=>row.block===blockId);if(rule)return rule;
 }
}

/** Exact namespaced item-to-one-particle binding supplied by a validated addon. */
export const externalItemParticle=item=>itemParticles.get(item);
/** Optional namespaced presentation descriptors; removed with their source. */
export function externalBreakFeedback(id){for(const value of foundations.values()){const row=value.breakFeedback?.find(row=>row.block===id);if(row)return row;}}
