/** Production display adapter with a deterministic clock/display handle.
 * These are script regressions, never Minecraft client or simulated-player tests.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {BARREL_HUD_SHOW_TAG,slotsPacket,progressPacket,GRAPHICAL_HUD_END} from '../runtime/BP/scripts/core/shaker-hud.js';
const clock={currentTick:0};
globalThis.immersionFeedbackClock=clock;
const core=new URL('../runtime/BP/scripts/core/shaker-hud.js',import.meta.url).href;
const source=readFileSync(new URL('../runtime/BP/scripts/bedrock/shaker-screen.js',import.meta.url),'utf8')
 .replace("import {system} from '@minecraft/server';",'const system=globalThis.immersionFeedbackClock;')
 .replace("'../core/shaker-hud.js'",JSON.stringify(core))
 .replace("import {sendFormattingHud,forgetFormattingHud} from './shaker-hud-transport.js';","const sendFormattingHud=(player,packet)=>player.graphics.push(packet),forgetFormattingHud=()=>{};");
const display=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
let sequence=0;
function handle(){const writes=[],tags=new Set();return {graphics:[],id:'display-'+sequence++,hasTag:t=>tags.has(t),tags,writes,onScreenDisplay:{setActionBar:value=>writes.push(value)}};}
test('looking at a barrel is silent until its optional status is explicitly enabled',()=>{
 const p=handle(),text=[{text:'barrel status'}];
 for(clock.currentTick=0;clock.currentTick<1200;clock.currentTick+=10)display.showBarrelHud(p,text);
 assert.deepEqual(p.writes,[]);p.tags.add(BARREL_HUD_SHOW_TAG);display.showBarrelHud(p,text);assert.equal(p.writes.length,1);
 p.tags.clear();clock.currentTick+=10;display.showBarrelHud(p,text);display.hideShakerHud(p);assert.equal(p.writes.length,1);
});
test('a rejection writes once and is never refreshed by crosshair/idle polling',()=>{
 const p=handle();clock.currentTick=0;display.showShakerMessage(p,'NEED_THREE_INGREDIENTS');
 assert.equal(p.writes[0].rawtext[1].translate,'message.kaleidoscope_tavern.shaker.amount_too_low');
 for(clock.currentTick=1;clock.currentTick<40;clock.currentTick++){
  display.showShakerMessage(p,'NEED_THREE_INGREDIENTS');display.showShakerSlots(p,{slots:[]});display.hideShakerHud(p);
 }
 assert.equal(p.writes.length,1);display.showShakerSlots(p,{slots:[]});assert.equal(p.writes.length,1);assert.equal(p.graphics.length,1);
});
test('successful mixing has no text announcement and retains graphical progress/slots',()=>{
 const p=handle();clock.currentTick=0;display.showShakerProgress(p,37);display.showShakerMessage(p,'READY');
 assert.deepEqual(p.writes,[]);assert.equal(p.graphics[0],progressPacket(37));
 clock.currentTick=10;display.showShakerSlots(p,{slots:[{color:0xff5555}]});assert.equal(p.graphics[1],slotsPacket([{color:0xff5555}]));assert.deepEqual(p.writes,[]);
});
test('low-quality ingredients use the original translated chat without taking the Actionbar',()=>{
 const p=handle(),chat=[];p.sendMessage=value=>chat.push(value);clock.currentTick=0;
 display.showShakerMessage(p,'QUALITY_TOO_LOW');
 assert.deepEqual(chat,[{translate:'message.kaleidoscope_tavern.shaker.brew_level_too_low'}]);
 assert.deepEqual(p.writes,[]);
 display.showShakerSlots(p,{slots:[]});assert.equal(p.graphics.length,1);assert.deepEqual(p.writes,[]);
});
test('leaving a target or clearing a session never erases a foreign Actionbar',()=>{
 const p=handle();clock.currentTick=0;p.tags.add(BARREL_HUD_SHOW_TAG);display.showBarrelHud(p,[{text:'barrel'}]);
 display.showShakerProgress(p,25);
 p.onScreenDisplay.setActionBar('foreign message');const count=p.writes.length;
 for(clock.currentTick=10;clock.currentTick<200;clock.currentTick+=10)display.hideShakerHud(p);
 display.clearShakerPlayer(p);assert.deepEqual(p.graphics,[progressPacket(25),GRAPHICAL_HUD_END]);assert.equal(p.writes.length,count);assert.equal(p.writes.at(-1),'foreign message');
});
