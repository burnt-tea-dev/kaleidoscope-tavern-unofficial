/** Isolated QA copy only: install at BP/scripts/tap-source-swap-capability.js
 * and import once from that copy's entrypoint. Never add this probe to LIVE.
 * It exercises real scheduled tap callbacks and reads their saved juice on restart.
 */
import {world,system,BlockPermutation,BlockVolume} from '@minecraft/server';
import {tryOpenTap,toggleTap} from './bedrock/machines.js';
import {BottleStore,bottleKey} from './core/bottles.js';
const NS='kaleidoscope_tavern',EMPTY=NS+':bottle_empty',KEY=NS+':tap_source_qa';
const out=(stage,data={})=>console.warn('[KT-TAP-SOURCE-QA] '+stage+' '+JSON.stringify(data));
const pause=ticks=>new Promise(resolve=>system.runTimeout(resolve,ticks));
const require=(value,message)=>{if(!value)throw Error(message);};
const store=new BottleStore(world);
function source(block,kind){
 block.setPermutation(kind==='water'?BlockPermutation.resolve('minecraft:cauldron',{cauldron_liquid:'water',fill_level:6}):BlockPermutation.resolve(kind==='melon'?'minecraft:melon_block':'minecraft:stone'));
}
world.afterEvents.worldLoad.subscribe(()=>system.runTimeout(async()=>{try{
 require(world.getAllPlayers().length===0,'QA requires zero players');
 const dimension=world.getDimension('overworld'),previous=world.getDynamicProperty(KEY);
 if(previous){
  const saved=JSON.parse(previous),state=store.load(saved.key);
  require(dimension.getBlock(saved.position)?.typeId===NS+':bottle_watermelon_juice','saved juice block missing');
  require(state?.items.length===1&&state.items[0]===NS+':watermelon_juice','saved juice data changed');
  world.setDynamicProperty(KEY,undefined);dimension.runCommand('tickingarea remove kt_tap_source_qa');
  out('restart_done',{item:state.items[0],count:state.items.length,players:world.getAllPlayers().length});return;
 }
 dimension.runCommand('tickingarea add circle 40 301 32 2 kt_tap_source_qa true');
 let loaded=false;for(let i=0;i<60&&!loaded;i++){await pause(5);try{loaded=!!dimension.getBlock({x:40,y:301,z:32});}catch{}}
 require(loaded,'QA chunks unavailable');
 dimension.fillBlocks(new BlockVolume({x:30,y:299,z:30},{x:52,y:299,z:35}),'minecraft:stone');
 dimension.fillBlocks(new BlockVolume({x:30,y:300,z:30},{x:52,y:304,z:35}),'minecraft:air');
 let saved;
 const cases=[['water-to-melon','water','melon',NS+':bottle_watermelon_juice'],['melon-to-water','melon','water',NS+':bottle_water'],['unsupported','water','stone',EMPTY],['empty-opening','stone','water',EMPTY],['cancelled','water','melon',EMPTY]];
 for(let i=0;i<cases.length;i++){
  const [name,initial,replacement,expected]=cases[i],x=32+i*4;
  const tap=dimension.getBlock({x,y:301,z:32}),from=dimension.getBlock({x,y:301,z:33}),destination=dimension.getBlock({x,y:300,z:32});
  source(from,initial);destination.setType(EMPTY);tap.setPermutation(BlockPermutation.resolve(NS+':tap',{'minecraft:block_face':'north',[NS+':open']:0}));
  require(tryOpenTap(tap),'tap did not open');
  const changeAt=name==='empty-opening'?1:10;await pause(changeAt);source(from,replacement);
  if(name==='cancelled')toggleTap(tap);
  await pause(29-changeAt);require(destination.typeId===EMPTY,'tap produced before its completion boundary');
  await pause(2);require(destination.typeId===expected,'current source output differs: '+name);
  require(tap.permutation.getState(NS+':open')===0,'tap remained open');
  if(name==='water-to-melon'){
   require(from.typeId==='minecraft:melon_block','Java keeps the melon source');
   const key=bottleKey(dimension.id,destination.location),state=store.load(key);
   require(state?.items.length===1&&state.items[0]===NS+':watermelon_juice','juice data missing');
   saved={key,position:{...destination.location}};
  }
  out('case',{name,output:destination.typeId,source:from.typeId});
 }
 world.setDynamicProperty(KEY,JSON.stringify(saved));out('first_done',{cases:cases.length,savedItem:NS+':watermelon_juice'});
}catch(error){out('failure',{error:String(error),stack:error.stack});}},100));
