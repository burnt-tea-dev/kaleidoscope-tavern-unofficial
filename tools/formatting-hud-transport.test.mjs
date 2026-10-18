/** Source contracts for the real sender and declared UI bindings; no client rendering. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {sendFormattingHud} from '../runtime/BP/scripts/bedrock/shaker-hud-transport.js';
import {GRAPHICAL_HUD_PREFIX,GRAPHICAL_HUD_END,slotsPacket,progressPacket} from '../runtime/BP/scripts/core/shaker-hud.js';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('production sender delivers only valid owned graphical packets through the actionbar factory',()=>{
 const calls=[],player={onScreenDisplay:{
  setActionBar:packet=>calls.push(packet),
  setTitle(){throw Error('Effect title route overwritten');},
  updateSubtitle(){throw Error('Foreign subtitle overwritten');}
 }};
 const packets=[slotsPacket([]),progressPacket(0),progressPacket(25),GRAPHICAL_HUD_END];
 for(const packet of packets){
  assert.equal(sendFormattingHud(player,packet),'actionbar_factory');
  assert.equal(packet.replace(/§[0-9a-fr]/g,''),packet);
 }
 assert.deepEqual(calls,packets);
 for(const invalid of ['',GRAPHICAL_HUD_PREFIX+'textures/foo',GRAPHICAL_HUD_PREFIX+'§a'.repeat(40),'§r§0§r§0§r',null,{}]){
  assert.throws(()=>sendFormattingHud(player,invalid),/Invalid graphical/);
  assert.deepEqual(calls,packets,'Rejected packets must not write to the display');
 }
});
test('production graphics use bounded local actionbar events while effect titles stay separate',()=>{
 const hud=JSON.parse(read('runtime/RP/ui/kt_tavern_hud.json'));
 assert.equal(hud.kt_mixology_packet.$kt_text,'$actionbar_text');
 assert.equal(hud.kt_mixology_factory.factory.name,'hud_actionbar_text_factory');
 assert.equal(hud.kt_mixology_factory.factory.max_children_size,1);
 for(const panel of [hud.kt_mixology_packet.controls[0].slots,hud.kt_mixology_packet.controls[1].progress]){
  for(const [name,sprite] of panel.controls.flatMap(row=>Object.entries(row)))if(name.includes('@')||sprite.type==='image'){
   assert.equal(sprite.bindings,undefined);assert(sprite.visible.includes('$kt_text'));
  }
 }
 assert(read('runtime/BP/scripts/bedrock/shaker-hud-transport.js').includes('createGraphicalActionbarTransport'));
 assert(!/ui_load|setTitle/.test(read('runtime/BP/scripts/bedrock/shaker-hud-transport.js')));
 assert(read('runtime/BP/scripts/bedrock/effect-icons.js').includes('createEffectIconTransport'));
 assert(read('runtime/BP/scripts/bedrock/shaker-screen.js').includes('if(graphical.delete(player.id))try{sendFormattingHud(player,GRAPHICAL_HUD_END)'));
});
