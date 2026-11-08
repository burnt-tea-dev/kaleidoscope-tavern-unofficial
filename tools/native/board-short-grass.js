/** Native item identity and canonical decoration map, not player/crafting acceptance. */
import {world,system,ItemStack,BlockPermutation} from '@minecraft/server';
import {FLOWER_BOARD_TRANSFORMS} from './core/boards.js';
const out=(kind,fields={})=>console.warn('[LIVING_EFFECT_QA] '+JSON.stringify({kind,...fields}));
world.afterEvents.worldLoad.subscribe(()=>system.run(()=>{try{
 if(world.getAllPlayers().length)throw Error('requires zero players');
 for(const input of ['minecraft:grass','minecraft:grass_block','minecraft:short_grass','minecraft:tallgrass','minecraft:tall_grass']){
  let item,error,block,blockError;try{item=new ItemStack(input);}catch(e){error=String(e);}try{block=BlockPermutation.resolve(input);}catch(e){blockError=String(e);}
  out('case',{input,itemTypeId:item?.typeId??null,itemError:error??null,blockTypeId:block?.type.id??null,blockError:blockError??null,boardTransform:item?FLOWER_BOARD_TRANSFORMS[item.typeId]??null:null});
 }
 const short=new ItemStack('minecraft:short_grass'),alias=new ItemStack('minecraft:tallgrass');
 if(FLOWER_BOARD_TRANSFORMS[short.typeId]!=='kaleidoscope_tavern:grass_sandwich_board'||alias.typeId!==short.typeId)throw Error('Short-grass decoration mapping failed');
 if(FLOWER_BOARD_TRANSFORMS[new ItemStack('minecraft:grass_block').typeId])throw Error('Grass block must not decorate a board');
 out('done',{phase:'first',players:0,scope:'Native item aliases and production board transform map only. Not real player interaction or crafting.'});
}catch(error){out('failure',{error:String(error),stack:error.stack});}}));
