/** Java main c4ec188 ModEffects and Mojang 1.20.1 MobEffects/PotionUtils.
 * Only declared visible effects participate. The caller must not guess the
 * visibility of a native/foreign effect from getEffects(), which omits it.
 */
import {VANILLA_EFFECT_COLORS} from './effect-colors.js';
export const TAVERN_AURA_COLORS=Object.freeze({
 'kaleidoscope_tavern:slightly_tipsy':0xffd94a,
 'kaleidoscope_tavern:high_heels':0xe85baa,
 'kaleidoscope_tavern:grass_stealth':0x71bde7,
 'kaleidoscope_tavern:vision':0x408997,
 'kaleidoscope_tavern:bloody_mary':0xf73a36,
 'kaleidoscope_tavern:ardent_heat':0xff6b35,
 'kaleidoscope_tavern:long_reach':0x8b6914,
 'kaleidoscope_tavern:tomb_raider':0xdaa520,
 'kaleidoscope_tavern:xp_drain':0x7cfc00
});
/** Source colors for supported timed native drink effects; these are not the
 * older pre-1.20 potion palette. No guessed colors for external custom IDs.
 */
export const NATIVE_AURA_COLORS=Object.freeze(Object.fromEntries([
 'speed','slowness','haste','mining_fatigue','strength','jump_boost','nausea',
 'regeneration','resistance','fire_resistance','water_breathing','invisibility',
 'blindness','night_vision','hunger','weakness','poison','wither','health_boost',
 'absorption','levitation','slow_falling','bad_omen','village_hero'
].map(id=>[id,VANILLA_EFFECT_COLORS[id==='village_hero'?'hero_of_the_village':id]])));
export const nativeAuraId=id=>typeof id==='string'?id.replace(/^minecraft:/,''):undefined;
export function customAuraRows(entries){
 const active=new Map();
 for(const row of entries){
  if(row.ticks<=0||TAVERN_AURA_COLORS[row.id]===undefined)continue;
  const before=active.get(row.id);
  if(!before||row.amplifier>before.amplifier)active.set(row.id,{...row,color:TAVERN_AURA_COLORS[row.id],visible:true,ambient:false});
 }
 return [...active.values()];
}
/** Preserve Java float accumulation, division and truncation, including the
 * occasional channel below an integer that real-number averaging would round.
 */
export function statusAuraColor(rows){
 const channels=[0,0,0];let weight=0;
 for(const row of rows){
  if(row.visible===false)continue;
  const n=row.amplifier+1;
  if(!Number.isInteger(row.color)||row.color<0||row.color>0xffffff||!Number.isInteger(n)||n<1||n>256)continue;
  for(let i=0;i<3;i++)channels[i]=Math.fround(channels[i]+Math.fround((n*(row.color>>(16-i*8)&255))/255));
  weight+=n;
 }
 if(weight===0)return 0;
 return channels.reduce((color,value,i)=>color|(Math.trunc(Math.fround(Math.fround(value/weight)*255))<<(16-i*8)),0);
}
/** LivingEntity.tickEffects: one chance per tick, 1/2 normally, 1/15 for native
 * invisibility, and a further 1/5 when every visible row is ambient.
 */
export function sampleStatusAura(box,rows,invisible=false,random=Math.random){
 const color=statusAuraColor(rows);if(color<=0)return undefined;
 const ambient=rows.every(row=>row.visible===false||row.ambient===true);
 if(invisible?Math.floor(random()*15)!==0:random()>=.5)return undefined;
 if(ambient&&Math.floor(random()*5)!==0)return undefined;
 for(const axis of ['x','y','z'])if(!Number.isFinite(box?.center?.[axis])||!Number.isFinite(box?.extent?.[axis])||box.extent[axis]<0)return undefined;
 return {color,ambient,position:{
  x:box.center.x+(random()*2-1)*box.extent.x,
  y:box.center.y-box.extent.y+random()*box.extent.y*2,
  z:box.center.z+(random()*2-1)*box.extent.z
 }};
}
