/** Source contracts for the real sender and declared UI bindings; no client rendering. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createFormattingHudTransport} from '../runtime/BP/scripts/core/formatting-hud-transport.js';
import {GRAPHICAL_HUD_PREFIX,GRAPHICAL_HUD_END,slotsPacket,progressPacket} from '../runtime/BP/scripts/core/shaker-hud.js';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('graphical packets route without touching the shared Actionbar or subtitle',()=>{
 for(const mode of ['ui_queue','embedded_queue','standalone']){
  const calls=[],player={onScreenDisplay:{setTitle:(...args)=>calls.push(['title',...args]),setActionBar(){throw Error('Foreign Actionbar overwritten');},updateSubtitle(){throw Error('Foreign subtitle overwritten');}}};
  const sender=createFormattingHudTransport({prefix:GRAPHICAL_HUD_PREFIX,maxLength:60,queueAvailable:()=>mode==='ui_queue',embeddedAvailable:()=>mode==='embedded_queue',queueSend:(p,packet)=>calls.push(['queue',packet]),legacySend:(p,packet)=>calls.push(['embedded',packet])});
  for(const packet of [slotsPacket([]),progressPacket(0),progressPacket(25),GRAPHICAL_HUD_END]){
   assert.equal(sender.send(player,packet),mode);assert.equal(packet.replace(/§[0-9a-fr]/g,''),'');
  }
  assert.equal(calls.length,4);
  if(mode==='standalone')for(const [,packet,options] of calls)assert.deepEqual(options,{fadeInDuration:0,fadeOutDuration:0,stayDuration:0});
  const count=calls.length;
  for(const invalid of ['',GRAPHICAL_HUD_PREFIX+'textures/foo',GRAPHICAL_HUD_PREFIX+'§a'.repeat(40),'§r§0§r§0§r'])assert.throws(()=>sender.send(player,invalid),/Invalid graphical/);
  assert.equal(calls.length,count);
 }
});
test('factory snapshots remain separate from prefix-latched stop state',()=>{
 const hud=JSON.parse(read('runtime/RP/ui/kt_tavern_hud.json'));
 assert.equal(hud.kt_mixology_factory.factory.name,'hud_title_text_factory');
 assert(hud.kt_mixology_packet.bindings.some(b=>b.binding_condition==='once'&&b.binding_name==='#hud_title_text_string'));
 for(const [kind,panel] of [['kt_slot',hud.kt_mixology_packet.controls[0].slots],['kt_progress',hud.kt_mixology_packet.controls[1].progress]]){
  const controls=Object.fromEntries(panel.controls.flatMap(row=>Object.entries(row))),frame=controls[kind+'_frame'],channel=controls[kind+'_channel'];
  assert.deepEqual(frame.bindings,[{binding_name:'#hud_title_text_string',binding_name_override:'#kt_text',binding_type:'global',binding_condition:'once'}]);
  assert(channel.bindings.at(-1).source_property_name.includes("'%.12s'"),'Formatting prefix length is UTF-8 bytes');
  for(const [name,sprite] of Object.entries(controls))if(name.includes('@')||sprite.type==='image'){
   assert.equal(sprite.bindings[0].source_control_name,kind+'_frame');assert.equal(sprite.bindings[0].resolve_sibling_scope,true);
   assert(!sprite.bindings.some(b=>b.binding_name==='#hud_title_text_string'));
   const gate=sprite.bindings.at(-1).source_property_name;
   assert(gate.includes('#kt_text_latest = #kt_text'),'Later own frames cannot revive an expired prior session snapshot');
   assert(gate.includes(GRAPHICAL_HUD_END));
  }
 }
 assert(read('runtime/BP/scripts/bedrock/shaker-screen.js').includes('if(graphical.delete(player.id))try{sendFormattingHud(player,GRAPHICAL_HUD_END)'));
});
