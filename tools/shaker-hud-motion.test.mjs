/** Evaluate shipped visibility expressions against real packets; no client renderer. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {GRAPHICAL_HUD_END,slotsPacket,progressPacket} from '../runtime/BP/scripts/core/shaker-hud.js';
const hud=JSON.parse(readFileSync(new URL('../runtime/RP/ui/kt_tavern_hud.json',import.meta.url)));
const packet=hud.kt_mixology_packet;
// Deliberately small expression interpreter: unsupported or unbound expressions
// fail instead of silently approving another old-variable visibility gate.
function evaluate(source,values){
 const tokens=source.match(/'[^']*'|[#\$][\w]+|\b(?:true|false|not|and|or)\b|[()=\-]/g)??[];let i=0;
 assert.equal(tokens.join(''),source.replace(/\s+(?=(?:[^']*'[^']*')*[^']*$)/g,''));
 function primary(){const t=tokens[i++];if(t==='('){const v=or();assert.equal(tokens[i++],')');return v;}if(t==='not')return !primary();if(t==='true'||t==='false')return t==='true';if(t?.startsWith("'"))return t.slice(1,-1);assert(Object.hasOwn(values,t),'Unbound UI property '+t);return values[t];}
 function minus(){let a=primary();while(tokens[i]==='-'){i++;a=String(a).replaceAll(String(primary()),'');}return a;}
 function eq(){let a=minus();while(tokens[i]==='='){i++;a=a===minus();}return a;}
 function and(){let a=eq();while(tokens[i]==='and'){i++;const b=eq();a=Boolean(a&&b);}return a;}
 function or(){let a=and();while(tokens[i]==='or'){i++;const b=and();a=Boolean(a||b);}return a;}
 const result=or();assert.equal(i,tokens.length);return result;
}
function visible(panel,text){
 const values={'#kt_text':text};if(panel.visible!==undefined&&!evaluate(panel.visible,values))return [];
 return panel.controls.flatMap(row=>Object.entries(row)).filter(([name,sprite])=>(sprite.type==='image'||name.includes('@'))&&evaluate(sprite.bindings.at(-1).source_property_name,values));
}
const slots=packet.controls[0].slots,progress=packet.controls[1].progress;
test('actual initial, slots, progress and stop gates select the expected graphics',()=>{
 assert.deepEqual(visible(slots,''),[]);assert.deepEqual(visible(progress,''),[]);
 const slot=slotsPacket([null,{color:0xff55ff},{color:0x55ffff}]);
 assert.deepEqual(visible(slots,slot).map(([key])=>key),['kt_slot_0_0@kaleidoscope_tavern_hud.kt_mixology_slot','kt_slot_1_1@kaleidoscope_tavern_hud.kt_mixology_slot','kt_slot_2_16@kaleidoscope_tavern_hud.kt_mixology_slot']);
 assert.deepEqual(visible(progress,slot),[]);
 for(const tick of [0,25,55,111]){
  const rows=visible(progress,progressPacket(tick));
  assert.deepEqual(rows.map(([name])=>name),['bar',`cursor_${tick}@kaleidoscope_tavern_hud.kt_mixology_cursor`]);
  assert.deepEqual(rows[1][1].offset,[tick*1.5,0]);
  assert.equal(visible(slots,progressPacket(tick)).length,0);
 }
 assert.equal(visible(slots,GRAPHICAL_HUD_END).length,0);assert.equal(visible(progress,GRAPHICAL_HUD_END).length,0);
});
test('declared channel gate accepts late own data and ignores interleaved foreign titles',()=>{
 const channel=slots.controls.at(-1).kt_slot_channel;let text='';
 for(const [incoming,expected]of [[slotsPacket([]),slotsPacket([])],['AMW_CH!magic_main!foo',slotsPacket([])],['§r§0§r§0§0§1§0§0',slotsPacket([])],[progressPacket(25),progressPacket(25)],[GRAPHICAL_HUD_END,GRAPHICAL_HUD_END]]){
  const values={'#kt_text':text,'#hud_title_text_string':incoming};
  if(evaluate(channel.bindings.at(-1).source_property_name,values))text=incoming;
  assert.equal(text,expected);
 }
});
