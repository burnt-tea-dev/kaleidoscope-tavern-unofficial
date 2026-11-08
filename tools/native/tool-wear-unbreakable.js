/** Real native ItemStack calls to the shared shearing durability owner.
 * No player simulation, crop interaction, client or LIVE validation.
 */
import {world,system,ItemStack} from '@minecraft/server';
import {withToolWear} from './bedrock/transactions.js';
const out=(kind,fields={})=>console.warn('[LIVING_EFFECT_QA] '+JSON.stringify({kind,...fields}));
world.afterEvents.worldLoad.subscribe(()=>system.run(()=>{try{
 if(world.getAllPlayers().length)throw Error('requires zero players');
 const rows=[];
 for(const [label,unbreakable,finalPoint,creative]of [['ordinary',false,false,false],['unbreakable',true,false,false],['unbreakable-final-point',true,true,false],['creative-final-point',false,true,true]]){
  const item=new ItemStack('minecraft:shears');item.nameTag='Native tool '+label;item.setLore(['Original shears']);item.setDynamicProperty('qa_tool:original','retained');
  const durability=item.getComponent('minecraft:durability'),damage=finalPoint?durability.maxDurability-1:12;durability.damage=damage;durability.unbreakable=unbreakable;
  const plan={after:[item],changes:[]};let rolls=0;withToolWear(plan,0,creative,()=>{rolls++;return 0;});
  const after=plan.after[0],row={label,unbreakable,creative,beforeDamage:damage,maxDurability:durability.maxDurability,deleted:!after,afterDamage:after?.getComponent('minecraft:durability').damage??null,afterUnbreakable:after?.getComponent('minecraft:durability').unbreakable??null,changes:plan.changes,rolls,metadata:after?.nameTag===item.nameTag&&JSON.stringify(after.getRawLore())===JSON.stringify(item.getRawLore())&&after.getDynamicProperty('qa_tool:original')==='retained'};
  rows.push(row);out('case',row);
 }
 const ordinary=rows[0],protectedRows=rows.slice(1);
 if(ordinary.deleted||ordinary.afterDamage!==13||ordinary.rolls!==1)throw Error('ordinary tool behavior changed');
 if(protectedRows.some(r=>r.deleted||r.afterDamage!==r.beforeDamage||r.changes.length||r.rolls||!r.metadata))throw Error('protected native shears were worn, removed or rewritten');
 out('done',{phase:'first',players:0,nativeItemStacks:true,scope:'Direct shared utility calls only, not native crop/player interactions.'});
}catch(error){out('failure',{error:String(error),stack:error.stack});}}));
