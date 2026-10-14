/** Production transport lifetime checks; not a Minecraft client renderer. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createFormattingHudTransport} from '../runtime/BP/scripts/core/formatting-hud-transport.js';
import {GRAPHICAL_HUD_PREFIX,GRAPHICAL_HUD_END,validShakerHudPacket,slotsPacket,progressPacket} from '../runtime/BP/scripts/core/shaker-hud.js';
function fixture(){
 let clock=0,next=1;const pending=new Map(),calls=[];
 const sender=createFormattingHudTransport({prefix:GRAPHICAL_HUD_PREFIX,endPacket:GRAPHICAL_HUD_END,validatePacket:validShakerHudPacket,maxLength:60,
  queueAvailable:()=>true,embeddedAvailable:()=>false,queueSend:(p,packet)=>calls.push([clock,p.id,packet]),
  schedule:(fn,ticks)=>{const id=next++;pending.set(id,{fn,at:clock+ticks});return id;},cancel:id=>pending.delete(id),idleTicks:12});
 const advance=n=>{for(let i=0;i<n;i++){clock++;for(const [id,row]of [...pending])if(row.at<=clock){pending.delete(id);row.fn();}}};
 return {sender,advance,pending,calls};
}
test('refresh keeps current state and missed refresh emits exactly one owned stop',()=>{
 const f=fixture(),p={id:'a'};f.sender.send(p,slotsPacket([]));f.advance(10);f.sender.send(p,progressPacket(25));
 f.advance(11);assert.equal(f.calls.length,2);f.advance(1);
 assert.deepEqual(f.calls.at(-1),[22,'a',GRAPHICAL_HUD_END]);assert.equal(f.pending.size,0);
 f.advance(100);assert.equal(f.calls.length,3);
});
test('cancel and disconnect retire only the matching player timeout',()=>{
 const f=fixture(),a={id:'a'},b={id:'b'};f.sender.send(a,progressPacket(0));f.sender.send(b,progressPacket(1));
 f.sender.send(a,GRAPHICAL_HUD_END);f.sender.forget(b.id);assert.equal(f.pending.size,0);
 f.advance(100);assert.equal(f.calls.length,3);assert.equal(f.calls.at(-1)[2],GRAPHICAL_HUD_END);
});
test('original event factory has bounded slots/progress lifetime and no title cache ancestry',()=>{
 const hud=JSON.parse(readFileSync(new URL('../runtime/RP/ui/kt_tavern_hud.json',import.meta.url)));
 assert.deepEqual(hud.root.controls[0],{'kt_mixology@kaleidoscope_tavern_hud.kt_mixology_factory':{}});
 assert.equal(hud.kt_mixology_expire.destroy_at_end,'kt_mixology_packet');
 assert.equal(hud.kt_mixology_expire.duration,'$kt_lifetime');
 assert.equal(hud.kt_mixology_packet['$kt_lifetime|default'],.6);
 assert.equal(hud.kt_mixology_packet.variables[0].$kt_lifetime,.2);
 const {kt_effect_icons,...owned}=hud;
 assert(!/#hud_title_text_string|#kt_text_latest|channel_cache_probe/.test(JSON.stringify(owned)));
});
