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
assert.deepEqual(hud.root.controls[0],{'kt_mixology@kaleidoscope_tavern_hud.kt_mixology_factory':{}});
const raw=JSON.stringify(hud);
assert(!/#stored_text|#texture/.test(raw));
assert.equal(hud.kt_mixology_packet.$kt_text,'$actionbar_text');
assert.equal(hud.kt_mixology_factory.factory.name,'hud_actionbar_text_factory');
assert.equal(hud.kt_mixology_factory.factory.max_children_size,1);
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
// anchor_from selects the parent point; anchor_to selects this control's point.
// Project the actual controls across viewport sizes rather than assuming that
// swapping these fields preserves the position (the old graphics sat below centre).
const points={top_middle:[.5,0],center:[.5,.5]};
function projectedCenter(panel,width,height){
 const parent=points[panel.anchor_from],self=points[panel.anchor_to];
 assert(parent&&self,'Expected source-backed parent/control anchors');
 return [parent[0]*width+panel.offset[0]+(.5-self[0])*panel.size[0],
         parent[1]*height+panel.offset[1]+(.5-self[1])*panel.size[1]];
}
const packet=hud.kt_mixology_packet;
assert.deepEqual(packet['$kt_graphical_offset|default'],[0,0]);
assert.equal(packet.offset,'$kt_graphical_offset');
const touchShift=packet.variables.filter(row=>row.requires==='$touch');
assert.equal(touchShift.length,1);
assert.deepEqual(touchShift[0].$kt_graphical_offset,[0,16]);
for(const [name,y] of [['slots',32],['progress',26]]){
 const panel=controls.find(row=>name in row)[name];
 for(const [width,height] of [[320,180],[640,360],[426,240]]){
  assert.deepEqual(projectedCenter(panel,width,height),[width/2,y],name+' must stay at the Java top position');
  const previous={...panel,anchor_from:'center',anchor_to:'top_middle'};
  assert.notDeepEqual(projectedCenter(previous,width,height),[width/2,y],'Reject the previous inverted anchors');
  const offset=touchShift[0].$kt_graphical_offset;
  const touchCenter=projectedCenter(panel,width,height).map((value,index)=>value+offset[index]);
  assert.deepEqual(touchCenter,[width/2,y+16]);
  assert(touchCenter[1]-panel.size[1]/2>24,'Touch graphics must clear the native top controls');
 }
}
const slots=controls[0].slots.controls.filter(row=>Object.keys(row)[0].includes('@kaleidoscope_tavern_hud.kt_mixology_slot'));assert.equal(slots.length,51);
for(let i=0;i<3;i++)for(let c=0;c<17;c++)assert(JSON.stringify(slots[i*17+c]).includes(slotToken(i,c)));
const cursors=controls[1].progress.controls.filter(row=>Object.keys(row)[0].startsWith('cursor_'));assert.equal(cursors.length,112);
// Evaluate the shipped substring predicates. Complete semicolon tokens keep
// prefixed progress states distinct; formatting must not blank the cursor.
const containsPredicate=token=>`(not (($kt_text - '${token}') = $kt_text))`;
const predicateToken=predicate=>{
 const match=/^\(not \(\(\$kt_text - '([^']+)'\) = \$kt_text\)\)$/.exec(predicate);
 assert(match,'Expected a literal owned-token substring predicate');
 return match[1];
};
for(let n=0;n<112;n++){
 const cursor=Object.values(cursors[n])[0];
 assert.equal(cursor.visible,containsPredicate(progressPacket(n)));
}
const cursorTokens=cursors.map(row=>predicateToken(Object.values(row)[0].visible));
const shownCursors=text=>cursorTokens.flatMap((token,index)=>text.replaceAll(token,'')!==text?[index]:[]);
assert.equal(packet.visible,"(not (($kt_text - 'KT_HUD!') = $kt_text) and (($kt_text - 'KT_HUD!END;') = $kt_text))");
const packetVisible=text=>text.replaceAll('KT_HUD!','')!==text&&text.replaceAll('KT_HUD!END;','')===text;
let formattedProgressCases=0;
for(const lead of ['','§r','§r§f','§a§r','§r§0§r§0']){
 for(let n=0;n<112;n++){
  const text=lead+progressPacket(n)+'§r';
  assert(packetVisible(text));assert.deepEqual(shownCursors(text),[n]);formattedProgressCases++;
 }
 const end=lead+'KT_HUD!END;§r';
 assert(!packetVisible(end));assert.deepEqual(shownCursors(end),[]);
}
for(const text of ['普通提示','§r其他模組提示','KG_HUD!END;',slotsPacket([null,null,null])])
 assert.deepEqual(shownCursors(text),[]);
assert.equal(progressPacket(-10),progressPacket(0));assert.equal(progressPacket(Infinity),progressPacket(0));
assert.equal(progressPacket(200),progressPacket(111));
const colors=SHAKER_HUD_COLORS;
let cases=0;
for(let a=0;a<17;a++)for(let b=0;b<17;b++)for(let c=0;c<17;c++){
 const indices=[a,b,c],packet=slotsPacket(indices.map(n=>n?{color:colors[n-1]}:null));
 assert.equal(packet,GRAPHICAL_HUD_PREFIX+'S:'+indices.map((n,i)=>slotToken(i,n)).join(''));
 assert.equal(packet.replace(/§[0-9a-fr]/g,''),packet);
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
console.log(JSON.stringify({hudStaticChecks:'passed',slotCases:cases,progressStates:112,formattedProgressCases,idleSamples:256,literalImageReferences:textures,clientTested:false}));

assert(!controls.some(c=>c.status),'Barrel text must use only the native actionbar, not an expiring duplicate label');
