/** Real effect callback with Script API interface doubles; no rendered outline claim. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {EffectTypes,system,world,Dimension} from '@minecraft/server';
import {pulseVision,customEffectDiagnostics,applyCustomEffect,tickExternalLivingEffects,statusNow,clearCustomEffects,installCustomEffects,CUSTOM_TEST} from '../runtime/BP/scripts/bedrock/custom-effects.js';
import {spawnThrownDrink,resolveThrownDrinkImpact} from '../runtime/BP/scripts/bedrock/storage-projectile.js';
let serial=0;
const box=(x=0)=>({center:{x,y:1,z:0},extent:{x:.3,y:.9,z:.3}});
const components=(health=20,mob=true)=>id=>id==='minecraft:health'?{currentValue:health}:id==='minecraft:type_family'?{hasTypeFamily:family=>family==='mob'&&mob}:undefined;
function fixture(){
 const sounds=[],targets=[];
 const dimension={getEntities:()=>targets,playSound:(...args)=>sounds.push(args)};
 const viewer={id:'vision-viewer-'+(++serial),location:{x:0,y:0,z:0},getAABB:()=>box(),dimension};
 const target=(x=2)=>({id:'vision-target-'+(++serial),typeId:'minecraft:zombie',getAABB:()=>box(x),
  getComponent:components(),getEffect(){assert.fail('absent Glowing must not be requested');},addEffect(){assert.fail('absent Glowing must not be applied');}});
 return {sounds,targets,viewer,target};
}
test('absent native Glowing still gives exactly one first-target sound and no invalid API calls',()=>{
 const f=fixture();f.targets.push(f.target());system.currentTick=1000;
 const errors=customEffectDiagnostics.errors.length;
 assert.equal(pulseVision(f.viewer,0),1);assert.equal(f.sounds.length,1);
 assert.equal(customEffectDiagnostics.visionOutline,'unavailable');
 system.currentTick+=50;pulseVision(f.viewer,0);assert.equal(f.sounds.length,1);
 assert.equal(customEffectDiagnostics.errors.length,errors);
});
test('one shared target lifetime suppresses duplicate sounds from another Vision viewer',()=>{
 const f=fixture();f.targets.push(f.target());system.currentTick=2000;
 pulseVision(f.viewer,0);
 const second={...f.viewer,id:'vision-second-'+(++serial)};
 pulseVision(second,0);assert.equal(f.sounds.length,1);
 f.targets.push(f.target(3));pulseVision(second,0);assert.equal(f.sounds.length,2);
});
test('a target returning before 60 ticks stays quiet; after its last refresh expires it is new',()=>{
 const f=fixture(),target=f.target();f.targets.push(target);system.currentTick=3000;
 pulseVision(f.viewer,0);f.targets.length=0;system.currentTick+=50;pulseVision(f.viewer,0);
 f.targets.push(target);system.currentTick=3059;pulseVision(f.viewer,0);assert.equal(f.sounds.length,1);
 f.targets.length=0;system.currentTick=3119;pulseVision(f.viewer,0);
 f.targets.push(target);pulseVision(f.viewer,0);assert.equal(f.sounds.length,2);
});
test('dead, out-of-range and cosmetic helper targets neither sound nor consume a detection lifetime',()=>{
 const f=fixture(),dead={...f.target(),getComponent:components(0)};
 f.targets.push(dead,f.target(8),{...f.target(),hasTag:()=>true});system.currentTick=4000;
 assert.equal(pulseVision(f.viewer,0),0);assert.equal(f.sounds.length,0);
 dead.getComponent=components();assert.equal(pulseVision(f.viewer,0),1);assert.equal(f.sounds.length,1);
});
test('health-bearing vehicles and non-living helpers cannot trigger Vision detection audio',()=>{
 const f=fixture();system.currentTick=5000;
 for(const typeId of ['minecraft:boat','example:health_display'])f.targets.push({...f.target(),typeId,getComponent:components(20,false)});
 assert.equal(pulseVision(f.viewer,0),0);assert.equal(f.sounds.length,0);
 f.targets.push(f.target(),{...f.target(),typeId:'minecraft:armor_stand',getComponent:components(20,false)},
  {...f.target(),typeId:'minecraft:player',getComponent:components(20,false)},
  {...f.target(),typeId:'minecraft:player',getComponent:components(0,false)});
 assert.equal(pulseVision(f.viewer,0),3,'living mob, armor stand and alive player remain eligible');
 assert.equal(f.sounds.length,1);
});
test('source living fish without the Native mob family are included while dead fish and unknown displays stay out',()=>{
 const f=fixture();system.currentTick=5500;
 for(const typeId of ['minecraft:cod','minecraft:salmon','minecraft:tropicalfish'])f.targets.push({...f.target(),typeId,getComponent:components(3,false)});
 f.targets.push({...f.target(),typeId:'minecraft:cod',getComponent:components(0,false)},
  {...f.target(),typeId:'example:fish_display',getComponent:components(3,false)});
 assert.equal(pulseVision(f.viewer,0),3);assert.equal(f.sounds.length,1);
});
test('Vision selects the living in-range list before applying effects to any target',async()=>{
 // Exercise the conditional native-effect branch with an API double. Java
 // getEntitiesOfClass completes its alive/AABB filter before addEffect hooks.
 const previous=EffectTypes.getAll;EffectTypes.getAll=()=>[{id:'minecraft:glowing'}];
 try{
  const {pulseVision:nativePulse}=await import('../runtime/BP/scripts/bedrock/custom-effects.js?vision-query-order');
  const f=fixture(),applied=[];let moved=false,alive=true;system.currentTick=6000;
  const first={...f.target(),getEffect:()=>undefined,addEffect(){applied.push(this.id);moved=true;alive=false;}};
  const second={...f.target(),getAABB:()=>box(moved?100:3),getComponent:id=>components(alive?20:0)(id),
   getEffect:()=>undefined,addEffect(){applied.push(this.id);}};
  f.targets.push(first,second);
  assert.equal(nativePulse(f.viewer,0),2);
  assert.deepEqual(applied,[first.id,second.id],'the first effect hook cannot remove a later query-time member');
 }finally{EffectTypes.getAll=previous;}
});

test('a living non-player keeps Vision and uses its remaining-duration pulse clock',()=>{
 const f=fixture(),data=new Map();system.currentTick=7000;
 Object.assign(f.viewer,{typeId:'minecraft:wolf',getComponent:components(),getDynamicProperty:key=>data.get(key),setDynamicProperty:(key,value)=>data.set(key,value)});
 f.targets.push(f.target());
 assert.equal(applyCustomEffect(f.viewer,{effect:'kaleidoscope_tavern:vision',ticks:51,amplifier:0}),true);
 system.currentTick++;tickExternalLivingEffects();assert.equal(f.sounds.length,0);
 system.currentTick++;tickExternalLivingEffects();assert.equal(f.sounds.length,1,'the 50-tick boundary dispatches through the existing Vision callback');
 system.currentTick+=49;tickExternalLivingEffects();assert.equal(statusNow(f.viewer).entries.length,0);
 f.targets.push(f.target());system.currentTick++;tickExternalLivingEffects();assert.equal(f.sounds.length,1,'expired rows do not keep detecting');
 clearCustomEffects(f.viewer);
});

test('script startup restores saved familyless living recipients, and entity reload pauses unloaded time',()=>{
 system.currentTick=8000;installCustomEffects();
 const dimension=world.getDimension('overworld'),fish=dimension.spawnEntity('minecraft:cod',{x:0,y:2,z:0});
 fish.health={currentValue:3,effectiveMax:3};
 assert.equal(applyCustomEffect(fish,{effect:'kaleidoscope_tavern:vision',ticks:45,amplifier:0}),true);
 world.afterEvents.entityRemove.emit({removedEntityId:fish.id});
 assert.equal(CUSTOM_TEST.tracks.has(fish.id),false);
 system.advance(1);
 assert.equal(CUSTOM_TEST.tracks.has(fish.id),true,'startup must discover saved living fish outside the native mob family');
 assert.equal(statusNow(fish).entries[0].ticks,45);
 world.afterEvents.entityRemove.emit({removedEntityId:fish.id});system.currentTick+=1000;
 world.afterEvents.entityLoad.emit({entity:fish});
 assert.equal(statusNow(fish).entries[0].ticks,45,'unloaded wall time is not charged');
 system.currentTick++;tickExternalLivingEffects();assert.equal(statusNow(fish).entries[0].ticks,44);
 clearCustomEffects(fish);fish.remove();
});

test('a real glowflower bottle impact routes its recorded Vision effect into a living mob',()=>{
 const dimension=new Dimension('minecraft:overworld'),mob=dimension.spawnEntity('minecraft:wolf',{x:1,y:2,z:0});
 mob.health={currentValue:20,effectiveMax:20};mob.getAABB=()=>({center:{x:1,y:2.9,z:0},extent:{x:.3,y:.9,z:.3}});
 const projectile=spawnThrownDrink(dimension,'kaleidoscope_tavern:glowflower_brew_q3',{x:0,y:2,z:0},{x:0,y:0,z:0},{rng:()=>0});
 projectile.getAABB=()=>({center:projectile.location,extent:{x:.125,y:.125,z:.125}});
 assert.equal(resolveThrownDrinkImpact({projectile}),true);
 assert.ok(statusNow(mob).entries.some(row=>row.id==='kaleidoscope_tavern:vision'&&row.ticks>0),'use the actual recorded bottle rows and impact dispatcher');
 clearCustomEffects(mob);mob.remove();
});
