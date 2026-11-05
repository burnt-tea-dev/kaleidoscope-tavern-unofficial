/** Actual Server request, publisher and consumer with deterministic API doubles. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {world,system,Player} from '@minecraft/server';
import {ExtensionRegistry} from '../runtime/BP/scripts/core/registry.js';
import {installCustomEffects,statusNow,clearCustomEffects} from '../runtime/BP/scripts/bedrock/custom-effects.js';
import {installFoundationBridge} from '../runtime/BP/scripts/bedrock/foundation-bridge.js';
import {createFoundationClient,readTavernEffects} from '../sdk/tavern-foundation-client.js';

const source='kaleidoscope_world_liquor',effect=source+':continuous_heal';
// A real registered World Liquor identity; no invented 33-effect catalogue.
const payload={api:1,source,version:'1.0.0',furniture:[],effects:[{id:effect,mode:'timed'}],legacyEffectKey:source+':effects'};
const registry=new ExtensionRegistry({recipes:[],fluids:[],itemExists:()=>true});registry.install(payload);
let players=[],serial=0;world.getAllPlayers=()=>players;
installCustomEffects();const bus=installFoundationBridge(registry,{});createFoundationClient(system,world,payload,()=>true);
const read=p=>readTavernEffects(p,source).continuous_heal;
const player=()=>{const p=new Player('snapshot-capacity-'+(++serial),world.getDimension('overworld'));players=[p];return p;};
function apply(p,amplifier,duration=600){
 system.afterEvents.scriptEventReceive.emit({sourceType:'Server',id:'kaleidoscope_tavern:effect_apply',message:JSON.stringify({entity:p.id,effect,duration,amplifier})});
}
function publish(){bus.publish();system.advance(1);}

test('33 valid amplifier requests retain the current consumer effect beyond its previous snapshot lease',()=>{
 const p=player();
 for(let amplifier=0;amplifier<32;amplifier++)apply(p,amplifier);
 publish();assert.equal(read(p)?.amplifier,31);
 apply(p,32);system.advance(25);
 assert.equal(statusNow(p).entries.length,33,'host keeps every hidden amplifier timer');
 assert.equal(read(p)?.amplifier,32,'consumer must not lose the entire effect after its old lease expires');
 const packets=system.sent.filter(row=>row.id==='kaleidoscope_tavern:effect_snapshot').map(row=>JSON.parse(row.message)).filter(row=>row.entity===p.id);
 assert(packets.some(row=>row.parts>1),'the real publisher must exercise multipart assembly');
 clearCustomEffects(p);publish();assert.equal(read(p),undefined);players=[];
});

test('the consumer receives the weaker remaining effect when the strongest timer expires',()=>{
 const p=player();apply(p,0,10);apply(p,2,1);publish();
 assert.equal(read(p)?.amplifier,2);assert.equal(statusNow(p).entries.length,2);
 system.advance(19);
 assert.equal(read(p)?.amplifier,0,'consumer fallback must work at expiry before the next host publication');
 system.advance(6);
 assert.equal(read(p)?.amplifier,0);assert(read(p).ticks>0);assert.equal(statusNow(p).entries.length,1);
 clearCustomEffects(p);publish();assert.equal(read(p),undefined);players=[];
});
