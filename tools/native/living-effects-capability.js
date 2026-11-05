/** Isolated saved-world observer only. Copy to BP/scripts/living-effects-capability.js
 * and import once from that QA copy's entrypoint. Never install this probe on LIVE.
 * First load: fish Vision independently; native Tomb Raider drop if equipment exists.
 * Restart: startup track restoration and loaded timer advance, then remove QA actors.
 */
import {world,system,ItemStack,EquipmentSlot,EntityDamageCause,BlockVolume} from '@minecraft/server';
import {applyCustomEffect,statusNow,effectSnapshotEntities,customEffectDiagnostics,TOMB_PICKUP_UNLOCK} from './bedrock/custom-effects.js';
const KEY='kaleidoscope_tavern:living_effects_qa',TAG='kt_living_effects_qa';
const VISION='kaleidoscope_tavern:vision',TOMB='kaleidoscope_tavern:tomb_raider';
const out=(stage,data={})=>console.warn('[KT-LIVING-QA] '+stage+' '+JSON.stringify(data));
const finish=(phase,data)=>{const complete=data.tombRaider.status==='pass';out(phase+(complete?'_done':'_partial'),data);console.warn('[LIVING_EFFECT_QA] '+JSON.stringify({kind:complete?'done':'partial',phase,...data}));};
const pause=ticks=>new Promise(resolve=>system.runTimeout(resolve,ticks));
function require(value,message){if(!value)throw Error(message);}
const effect=(entity,id)=>statusNow(entity).entries.find(row=>row.id===id);
world.afterEvents.worldLoad.subscribe(()=>system.runTimeout(async()=>{try{
 require(world.getAllPlayers().length===0,'QA requires zero players');
 const dimension=world.getDimension('overworld'),previous=world.getDynamicProperty(KEY);
 if(previous){
  const saved=JSON.parse(previous),entities=dimension.getEntities({tags:[TAG]});
  const fish=entities.find(entity=>entity.id===saved.fish),attacker=entities.find(entity=>entity.id===saved.attacker);
  require(fish&&attacker,'saved QA recipients missing');
  // Inspect the restored track before statusNow can itself anchor a handle.
  const loaded=new Set(effectSnapshotEntities().map(entity=>entity.id));
  require(loaded.has(fish.id)&&loaded.has(attacker.id),'startup did not restore saved living tracks');
  const before=effect(fish,VISION)?.ticks,tomb=effect(attacker,TOMB)?.ticks;
  require(before>0&&before<=saved.vision&&tomb>0&&tomb<=saved.tomb,'saved effect data missing or increased');
  await pause(10);const after=effect(fish,VISION)?.ticks;
  require(after===before-10,'restored timer did not advance by loaded ticks');
  const result={fish:fish.typeId,before,after,tomb,vision:{status:'pass',restored:true},tombRaider:saved.tombRaider,players:world.getAllPlayers().length};
  for(const entity of entities)entity.remove();
  world.setDynamicProperty(KEY,undefined);dimension.runCommand('tickingarea remove kt_living_effects_qa');finish('restart',result);return;
 }
 dimension.runCommand('tickingarea add circle 6 300 2 1 kt_living_effects_qa true');
 let loaded=false;
 for(let i=0;i<60&&!loaded;i++){await pause(5);try{loaded=!!dimension.getBlock({x:6,y:300,z:2});}catch{}}
 require(loaded,'QA chunks unavailable');
 dimension.fillBlocks(new BlockVolume({x:0,y:299,z:0},{x:12,y:304,z:4}),'minecraft:stone');
 dimension.fillBlocks(new BlockVolume({x:1,y:300,z:1},{x:11,y:302,z:3}),'minecraft:air');
 dimension.fillBlocks(new BlockVolume({x:8,y:300,z:1},{x:8,y:302,z:3}),'minecraft:stone');
 dimension.fillBlocks(new BlockVolume({x:9,y:300,z:1},{x:11,y:301,z:3}),'minecraft:water');
 const attacker=dimension.spawnEntity('minecraft:wolf',{x:2.5,y:300,z:2.5});attacker.addTag(TAG);
 const target=dimension.spawnEntity('minecraft:zombie',{x:6.5,y:300,z:2.5});target.addTag(TAG);
 const fish=dimension.spawnEntity('minecraft:cod',{x:10.5,y:300,z:2.5});fish.addTag(TAG);
 const weapon=new ItemStack('minecraft:diamond_sword');weapon.nameTag='Tavern living QA';weapon.setLore(['native metadata witness']);weapon.setDynamicProperty('example:qa_owner','living-probe');
 weapon.getComponent('minecraft:durability').damage=7;
 const equipment=target.getComponent('minecraft:equippable');
 const tombRaider={status:equipment?'pending':'unavailable',target:target.typeId,component:'minecraft:equippable'};
 if(equipment)require(equipment.setEquipment(EquipmentSlot.Mainhand,weapon)!==false,'native equipment write rejected');
 else out('capability_unavailable',tombRaider);
 require(applyCustomEffect(attacker,{effect:TOMB,ticks:6000,amplifier:0}),'mob Tomb Raider rejected');
 require(applyCustomEffect(fish,{effect:VISION,ticks:6000,amplifier:0}),'fish Vision rejected');
 const pulses=customEffectDiagnostics.visionPulses,disarms=customEffectDiagnostics.tombDisarms;
 await pause(55);require(customEffectDiagnostics.visionPulses>pulses,'fish Vision did not pulse');
 out('case',{feature:'fish_vision',status:'pass',visionPulses:customEffectDiagnostics.visionPulses-pulses});
 if(equipment){
  for(let i=0;i<64&&equipment.getEquipment(EquipmentSlot.Mainhand);i++){
   target.getComponent('minecraft:health').resetToMaxValue();
   target.applyDamage(1,{cause:EntityDamageCause.entityAttack,damagingEntity:attacker});await pause(11);
  }
  require(!equipment.getEquipment(EquipmentSlot.Mainhand),'native hurt events did not disarm after 64 trials');
  const drops=dimension.getEntities({type:'minecraft:item',location:target.location,maxDistance:8}).filter(entity=>entity.getComponent('minecraft:item')?.itemStack?.nameTag===weapon.nameTag);
  require(drops.length===1&&customEffectDiagnostics.tombDisarms===disarms+1,'native event must produce one drop');
  const dropped=drops[0].getComponent('minecraft:item').itemStack,durability=dropped.getComponent('minecraft:durability');
  require(dropped.typeId===weapon.typeId&&dropped.getDynamicProperty('example:qa_owner')==='living-probe'&&dropped.getLore()[0]==='native metadata witness','native drop metadata changed');
  require(durability.damage===durability.maxDurability-1,'native drop durability differs');
  require(typeof drops[0].getDynamicProperty(TOMB_PICKUP_UNLOCK)==='number','native pickup delay missing');
  drops[0].addTag(TAG);tombRaider.status='pass';tombRaider.metadata=true;
 }
 const saved={fish:fish.id,attacker:attacker.id,vision:effect(fish,VISION).ticks,tomb:effect(attacker,TOMB).ticks,tombRaider};world.setDynamicProperty(KEY,JSON.stringify(saved));
 finish('first',{...saved,vision:{status:'pass',visionPulses:customEffectDiagnostics.visionPulses-pulses},players:world.getAllPlayers().length});
}catch(error){out('failure',{error:String(error),stack:error.stack});console.warn('[LIVING_EFFECT_QA] '+JSON.stringify({kind:'failure',error:String(error)}));}},100));
