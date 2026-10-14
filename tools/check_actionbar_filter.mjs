import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {slotsPacket,progressPacket,HUD_PREFIX,SHAKER_HUD_COLORS} from '../runtime/BP/scripts/core/shaker-hud.js';
const ui=JSON.parse(readFileSync(new URL('../runtime/RP/ui/hud_screen.json',import.meta.url),'utf8'));
const expected="((not (('%.7s' * $kt_family_actionbar_text) = 'KT_HUD!')) and (not (('%.7s' * $kt_family_actionbar_text) = 'KG_HUD!')) and (not (('%.4s' * $kt_family_actionbar_text) = '!js.')))";
assert.equal(ui.namespace,'hud');
assert(ui.root_panel.modifications[0].value.some(row=>'kt_family_tavern@$kt_tavern_hud_root' in row), 'Graphical HUD must remain installed');
for(const key of ['hud_actionbar_text','hud_actionbar_text/actionbar_message']){assert.equal(ui[key].visible,expected);assert.equal(ui[key].$kt_family_actionbar_text,'$actionbar_text');}
// Model the same text predicates used by the two native controls.
const visible=s=>!s.startsWith('KT_HUD!')&&!s.startsWith('KG_HUD!')&&!s.startsWith('!js.');
const colors=[null,...SHAKER_HUD_COLORS];
let slots=0;
for(const a of colors)for(const b of colors)for(const c of colors){assert(!visible(slotsPacket([a,b,c].map(color=>color===null?null:{color}))));slots++;}
for(let n=0;n<=111;n++)assert(!visible(progressPacket(n)));
for(const s of ['','普通提示','§a酒桶 品質 1',HUD_PREFIX+'材料不足',HUD_PREFIX+'Need three ingredients','其他模組提示'])assert(visible(s));
assert(!visible('!js.10'));
assert(visible('§r§0§r§0§0§1§0§0'));
// Only exact graphical prefixes are concealed; foreign titles are untouched.
assert(visible('§r§0Ordinary other-addon message'));
console.log(JSON.stringify({slotCases:slots,progressCases:112,messagePreservation:true,clientRenderingTested:false}));
