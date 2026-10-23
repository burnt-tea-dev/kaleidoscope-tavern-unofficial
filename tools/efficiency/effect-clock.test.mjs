/** Actual status callbacks with deterministic API doubles; no native client claim. */
import test,{beforeEach,afterEach} from 'node:test';
import assert from 'node:assert/strict';
import {Dimension,Player,world,system} from './mock-server.mjs';
import {statusNow,installCustomEffects,tickCustomEffects,tickExternalLivingEffects,effectSnapshotEntities} from '../../runtime/BP/scripts/bedrock/custom-effects.js';

const KEY='kaleidoscope_tavern:custom_effects';
installCustomEffects();
const startup=()=>{
 for(const [id,task] of [...system.timers])if(task.once){system.timers.delete(id);task.fn();}
};
const remaining=p=>JSON.parse(p.dp.get(KEY)).entries[0].ticks;
const actors=[];
function restored(){
 const p=new Player(new Dimension());
 actors.push(p);
 p.dp.set(KEY,JSON.stringify({schema:1,entries:[{id:'kaleidoscope_tavern:long_reach',ticks:100,amplifier:0}]}));
 return p;
}
beforeEach(()=>{
 world.players=[];system.currentTick=100;
});
afterEach(()=>{
 for(const actor of actors.splice(0))world.afterEvents.entityRemove.emit({removedEntityId:actor.id});
 world.players=[];
});

test('spawn-to-leave before the first heartbeat counts online ticks and excludes offline ticks',()=>{
 const p=restored();world.players=[p];
 world.afterEvents.playerSpawn.emit({player:p,initialSpawn:true});
 system.currentTick=104;world.afterEvents.playerLeave.emit({playerId:p.id});
 assert.equal(remaining(p),96);
 system.currentTick=1100;world.afterEvents.playerSpawn.emit({player:p,initialSpawn:true});
 system.currentTick=1105;tickCustomEffects();
 assert.equal(remaining(p),91);
});

test('read-only snapshots do not move the persisted countdown anchor',()=>{
 const p=restored();world.players=[p];
 assert.equal(statusNow(p).entries[0].ticks,100);
 for(let tick=101;tick<=104;tick++){
  system.currentTick=tick;assert.equal(statusNow(p).entries[0].ticks,200-tick);
  assert.equal(remaining(p),100);
 }
 system.currentTick=105;tickCustomEffects();assert.equal(remaining(p),95);
});

test('players already online at script startup receive the same initial clock',()=>{
 const p=restored();world.players=[p];startup();
 system.currentTick=104;world.afterEvents.playerLeave.emit({playerId:p.id});
 assert.equal(remaining(p),96);
});

test('a replacement entity handle starts a new clock even when its ID is reused',()=>{
 const previous=restored();statusNow(previous);
 const current=restored();current.id=previous.id;world.players=[current];system.currentTick=1100;
 assert.equal(statusNow(current).entries[0].ticks,100);
 system.currentTick=1105;tickCustomEffects();assert.equal(remaining(current),95);
});

test('a failed initial property read does not create an online anchor',()=>{
 const p=restored(),read=p.getDynamicProperty;
 p.getDynamicProperty=()=>{throw Error('UNAVAILABLE_HANDLE');};
 assert.throws(()=>statusNow(p),/UNAVAILABLE_HANDLE/);
 p.getDynamicProperty=read;system.currentTick=200;world.players=[p];
 assert.equal(statusNow(p).entries[0].ticks,100);
 system.currentTick=205;tickCustomEffects();assert.equal(remaining(p),95);
});

test('reading an empty or retired status does not add countdown work',()=>{
 const p=restored();p.typeId='minecraft:wolf';
 p.getComponent=id=>id==='minecraft:health'?{currentValue:10}:undefined;
 let reads=0;const read=p.getDynamicProperty;
 p.getDynamicProperty=function(key){reads++;return read.call(this,key);};
 for(const raw of [undefined,JSON.stringify({schema:1,entries:[],legacyClosed:true})]){
  p.setDynamicProperty(KEY,raw);system.currentTick++;
  assert.equal(statusNow(p).entries.length,0);
  assert.equal(effectSnapshotEntities().includes(p),false,'the bridge receives no empty effect recipient');
  reads=0;system.currentTick++;tickExternalLivingEffects();
  assert.equal(reads,0,'an empty recipient requires no later countdown property reads');
 }
});
