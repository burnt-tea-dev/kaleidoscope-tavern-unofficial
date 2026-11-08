/** Scoped native storage/drop observation. Failure injection invokes the real
 * adapter with a dimension facade; it is not a natural engine-error claim.
 * The complete canonical host is loaded. No player, client or LIVE use.
 */
import {world,system,ItemStack,BlockPermutation,BlockVolume} from '@minecraft/server';
import {naturalBreak} from './bedrock/natural-break.js';
import {nativeStoragePlan,nativeItems} from './bedrock/native-item-storage.js';
import {nativeItemKey} from './core/native-item-storage.js';
import {holderState,holderKey,HOLDER_KIND} from './core/holder.js';
import {replaceBlockWithoutNaturalDrops} from './bedrock/scripted-block-change.js';
const N='kaleidoscope_tavern:',pause=n=>new Promise(r=>system.runTimeout(r,n));
const out=(kind,fields={})=>console.warn('[LIVING_EFFECT_QA] '+JSON.stringify({kind,...fields}));
const need=(yes,text)=>{if(!yes)throw Error(text);};
const shape=item=>({id:item.typeId,amount:item.amount,name:item.nameTag,lore:item.getRawLore(),place:item.getCanPlaceOn(),destroy:item.getCanDestroy(),keep:item.keepOnDeath});
world.afterEvents.worldLoad.subscribe(()=>system.run(async()=>{try{
 need(world.getAllPlayers().length===0,'requires zero players');const d=world.getDimension('overworld');
 d.runCommand('tickingarea add circle 0 300 0 2 natural_drop_qa true');
 let loaded=false;for(let i=0;i<120&&!loaded;i++){try{loaded=!!d.getBlock({x:0,y:300,z:0});}catch{}if(!loaded)await pause(2);}
 need(loaded,'fixture chunk unavailable');d.fillBlocks(new BlockVolume({x:0,y:299,z:0},{x:18,y:299,z:3}),'minecraft:stone');
 for(const [index,mode]of ['first-drop-failure','partial-drop-failure','missing-public-state'].entries()){
  const at={x:2+index*5,y:300,z:1},block=d.getBlock(at),key=holderKey(d.id,at);
  const item=new ItemStack(N+'wine_q3');item.nameTag='Retain native '+mode;item.setLore(['Original native bottle metadata']);item.setCanDestroy(['minecraft:stone']);item.setCanPlaceOn(['minecraft:glass']);item.keepOnDeath=true;
  const expected=JSON.stringify(shape(item)),state=holderState(item.typeId,0);
  block.setPermutation(BlockPermutation.resolve(N+'holder',{[HOLDER_KIND]:Math.min(state.kind,15)}));
  const plan=nativeStoragePlan(block,key,undefined,state,item);plan.apply();world.setDynamicProperty(key,JSON.stringify(state));plan.finish();
  const raw=world.getDynamicProperty(key),ledger=world.getDynamicProperty(nativeItemKey(key)),permutation=block.permutation;
  replaceBlockWithoutNaturalDrops(block,BlockPermutation.resolve('minecraft:air'));await pause(4);
  need(world.getDynamicProperty(key)===raw,'suppressed preparation unexpectedly consumed state');
  const failAt=mode==='partial-drop-failure'?2:1;let calls=0;
  const dimension={id:d.id,getBlock:p=>d.getBlock(p),getEntities:q=>d.getEntities(q),spawnItem:(stack,p)=>{if(++calls===failAt)throw Error('QA_INJECTED_SPAWN_FAILURE');return d.spawnItem(stack,p);}};
  if(mode==='missing-public-state')world.setDynamicProperty(key,undefined);
  let error;try{naturalBreak({block:{dimension,location:at},brokenBlockPermutation:permutation},{});}catch(e){error=String(e);}
  need(error?.includes(mode==='missing-public-state'?'NATIVE_STORAGE_STATE_MISSING':'QA_INJECTED_SPAWN_FAILURE'),'expected failure missing: '+error);
  need(block.typeId===N+'holder','owner was not restored');need(world.getDynamicProperty(nativeItemKey(key))===ledger,'native ledger changed');
  need(world.getDynamicProperty(key)===(mode==='missing-public-state'?undefined:raw),'public bytes changed');
  const stored=nativeItems.readAdopted({key,dimension:d,position:at});need(JSON.stringify(shape(stored.items[0]))===expected,'native metadata lost during rollback');
  need(d.getEntities({type:'minecraft:item',location:at,maxDistance:2}).length===0,'partial drop remained after rollback');
  out('case',{mode,nativeCarrier:stored.entity.id,blockRestored:true,exactPublicBytes:true,exactNativeMetadata:true,partialDrops:0});
  if(mode==='missing-public-state')world.setDynamicProperty(key,raw); // Explicit fixture repair, not production inference.
  replaceBlockWithoutNaturalDrops(block,BlockPermutation.resolve('minecraft:air'));await pause(4);
  naturalBreak({block,brokenBlockPermutation:permutation},{});
  const drops=d.getEntities({type:'minecraft:item',location:at,maxDistance:2}),bottle=drops.map(e=>e.getComponent('minecraft:item').itemStack).find(x=>x.typeId===item.typeId);
  need(drops.length===2&&bottle&&JSON.stringify(shape(bottle))===expected,'retry output mismatch');
  need(world.getDynamicProperty(key)===undefined&&world.getDynamicProperty(nativeItemKey(key))===undefined,'retry did not retire records');
  need(d.getEntities({type:N+'stored_items',location:at,maxDistance:2}).length===0,'retry did not retire carrier');
  out('case',{mode:mode+'-retry',drops:2,exactNativeMetadata:true,carrierRetired:true});
  for(const entity of drops)entity.remove();
 }
 out('done',{phase:'first',players:world.getAllPlayers().length,scope:'Real canonical host/native item storage; three explicitly injected adapter paths and normal retry. No natural-engine exception, restart, multiplayer, client or LIVE proof.'});
}catch(error){out('failure',{error:String(error),stack:error.stack});}}));
