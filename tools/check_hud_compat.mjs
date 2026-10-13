import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {HUD_PREFIX,GRAPHICAL_HUD_PREFIX,SHAKER_HUD_COLORS,slotToken,slotsPacket,progressPacket,hudSendDue} from '../runtime/BP/scripts/core/shaker-hud.js';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const bridge=JSON.parse(read('runtime/RP/ui/hud_screen.json'));
const hud=JSON.parse(read('runtime/RP/ui/kt_tavern_hud.json'));
const adapter=read('runtime/BP/scripts/bedrock/shaker-screen.js');
assert(!/updateSubtitle|ktmix:|textures\//.test(adapter),'HUD must not put resource paths in messages');
assert(adapter.includes('sendFormattingHud(player,raw)'));
assert(adapter.includes('setActionBar(raw)'));
assert(!('hud_title_text' in hud));
for(const key of ['hud_actionbar_text','hud_actionbar_text/actionbar_message'])
 assert.deepEqual(Object.keys(bridge[key]).sort(),['$kt_family_actionbar_text','visible']);
assert.equal(hud.namespace,'kaleidoscope_tavern_hud');
assert.equal(hud.root.type,'panel');
assert.equal(bridge.root_panel.modifications[0].operation,'insert_back');
assert.deepEqual(hud.root.controls[0],{'kt_mixology@kaleidoscope_tavern_hud.kt_mixology_packet':{}});
const raw=JSON.stringify(hud);
assert(!/#stored_text|#texture/.test(raw));
assert.equal(hud.kt_mixology_packet.bindings,undefined);
let textures=0;
function walk(value){
 if(!value||typeof value!=='object')return;
 if('texture' in value){
  const p=value.texture;assert.equal(typeof p,'string');assert(p.startsWith('textures/ui/kt_mixology/'));
  assert(existsSync(new URL('../runtime/RP/'+p+'.png',import.meta.url)));textures++;
 }
 for(const v of Object.values(value))walk(v);
}
const {kt_effect_icons,...shakerHud}=hud;
walk(shakerHud);assert.equal(textures,53); // 51 fixed slot sprites + bar + cursor template
const controls=hud.kt_mixology_packet.controls;
const slots=controls[0].slots.controls.filter(row=>Object.keys(row)[0].includes('@kaleidoscope_tavern_hud.kt_mixology_slot'));assert.equal(slots.length,51);
for(let i=0;i<3;i++)for(let c=0;c<17;c++)assert(JSON.stringify(slots[i*17+c]).includes(slotToken(i,c)));
const cursors=controls[1].progress.controls.filter(row=>Object.keys(row)[0].startsWith('cursor_'));assert.equal(cursors.length,112);
for(let n=0;n<112;n++){
 const cursor=Object.values(cursors[n])[0];assert(cursor.bindings.at(-1).source_property_name.includes(`(#kt_text = '${progressPacket(n)}')`));
}
assert.equal(progressPacket(-10),progressPacket(0));assert.equal(progressPacket(Infinity),progressPacket(0));
assert.equal(progressPacket(200),progressPacket(111));
const colors=SHAKER_HUD_COLORS;
let cases=0;
for(let a=0;a<17;a++)for(let b=0;b<17;b++)for(let c=0;c<17;c++){
 const indices=[a,b,c],packet=slotsPacket(indices.map(n=>n?{color:colors[n-1]}:null));
 assert.equal(packet,GRAPHICAL_HUD_PREFIX+'§r§0'+indices.map((n,i)=>slotToken(i,n)).join(''));
 assert.equal(packet.replace(/§[0-9a-fr]/g,''),'');
 assert(!/textures\/|ktmix:/.test(packet));cases++;
}
assert(hudSendDue(undefined,'active',0));assert(!hudSendDue({key:'active',tick:0},'active',9));
assert(hudSendDue({key:'active',tick:0},'active',10));
for(let tick=0;tick<256;tick++)assert(!hudSendDue({key:'active',tick:0},undefined,tick));
const hide=adapter.split('export function hideShakerHud')[1].split('\n}')[0];
assert(hide.includes('last.delete(player.id)'));
assert(!/setActionBar|setTitle/.test(hide),'Leaving a target must not clear a foreign Actionbar');
const clear=adapter.split('export function clearShakerPlayer')[1].split('\n}')[0];
assert(!/\bsend\(|setActionBar|setTitle/.test(clear));
const barrel=adapter.split('export function showBarrelHud')[1].split('\n}')[0];
assert(!barrel.includes('HUD_PREFIX'));
assert(barrel.includes("send(player,'barrel/'+JSON.stringify(rawtext),{rawtext})"));
assert(barrel.includes('if(!barrelHudEnabled(player))return;'));
assert(read('runtime/BP/scripts/bedrock/mixology.js').includes('clearShakerPlayer(playerId)'));
console.log(JSON.stringify({hudStaticChecks:'passed',slotCases:cases,progressStates:112,idleSamples:256,literalImageReferences:textures,clientTested:false}));

assert(!controls.some(c=>c.status),'Barrel text must use only the native actionbar, not an expiring duplicate label');
