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
test('persistent receivers have no once snapshot or expiring factory ancestry',()=>{
 const hud=JSON.parse(readFileSync(new URL('../runtime/RP/ui/kt_tavern_hud.json',import.meta.url)));
 assert.deepEqual(hud.root.controls[0],{'kt_mixology@kaleidoscope_tavern_hud.kt_mixology_packet':{}});
 const {kt_effect_icons,...owned}=hud;
 assert(!/"factory"|"once"|"destroy_at_end"|"anims"/.test(JSON.stringify(owned)));
 const progress=hud.kt_mixology_packet.controls[1].progress;
 assert.equal(progress.visible,undefined,'Old / 111 text gate hides every new formatting packet');
 assert(!/\$kt_text|#kt_text_latest/.test(JSON.stringify(owned)),'No unbound legacy snapshot variables');
});
