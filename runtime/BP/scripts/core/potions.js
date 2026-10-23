/** C5: explicit vanilla potion semantics. IDs are validated against the live Potions registry.
 * No guessed potion numeric/data values, no parsing localized names, no potion execution here.
 * Duration comes from PotionEffectType.durationTicks (not a guessed fixed table).
 */
import {check,id,integer} from './util.js';
import {VANILLA_EFFECT_COLORS} from './effect-colors.js';
export const POTION_ITEMS=new Set(['minecraft:potion','minecraft:splash_potion','minecraft:lingering_potion']);
const specs={};
const add=(p,e,a=0)=>{specs['minecraft:'+p]=[[e,a]];};
for(const [p,e] of Object.entries({nightvision:'night_vision',invisibility:'invisibility',leaping:'jump_boost',fire_resistance:'fire_resistance',swiftness:'speed',slowness:'slowness',water_breathing:'water_breathing',poison:'poison',regeneration:'regeneration',strength:'strength',weakness:'weakness',slow_falling:'slow_falling'})){
 add(p,e);add('long_'+p,e);
}
for(const [p,e,a]of [['swiftness','speed',1],['leaping','jump_boost',1],['slowness','slowness',3],['poison','poison',1],['regeneration','regeneration',1],['strength','strength',1],['healing','instant_health',1],['harming','instant_damage',1]])add('strong_'+p,e,a);
add('healing','instant_health');add('harming','instant_damage');add('wither','wither');
for(const p of ['water','mundane','long_mundane','thick','awkward'])specs['minecraft:'+p]=[];
for(const p of ['turtle_master','long_turtle_master'])specs['minecraft:'+p]=[['slowness',3],['resistance',2]];
specs['minecraft:strong_turtle_master']=[['slowness',5],['resistance',3]];
export const POTION_SPECS=Object.freeze(specs);
// Display supports registry-backed potions independently of the recipe intake
// whitelist above. These newer/source-only effects do not widen recipe intake.
const DISPLAY_SPECS=Object.freeze({...POTION_SPECS,...Object.fromEntries(
 ['luck','wind_charged','weaving','oozing','infested'].map(effect=>['minecraft:'+effect,[[effect,0]]]))});
/** NeoForge 1.21.1 PotionContents: integer channel mean weighted by amplifier+1.
 * Bedrock wither has no Java potion entry; its existing identity uses Java's
 * WITHER colour. Unknown future registry IDs keep native storage and render the
 * original untinted liquid until their source semantics have been reviewed.
 */
export function potionDisplayColor(effectId){
 const entries=DISPLAY_SPECS[effectId];if(!entries)return undefined;
 if(!entries.length)return 0x385dc6;
 const channels=[0,0,0];let weight=0;
 for(const [effect,amplifier]of entries){
  const color=VANILLA_EFFECT_COLORS[effect];if(color===undefined)return undefined;
  const n=amplifier+1;weight+=n;
  for(let i=0;i<3;i++)channels[i]+=n*((color>>(16-i*8))&255);
 }
 return channels.reduce((rgb,value,i)=>rgb|(Math.floor(value/weight)<<(16-i*8)),0);
}
export function validatePotionIdentity(p){check(p&&Object.keys(p).every(k=>['effectId','deliveryId'].includes(k)),'BAD_POTION_IDENTITY');id(p.effectId);check(['Consume','ThrownSplash','ThrownLingering'].includes(p.deliveryId),'POTION_DELIVERY_UNSUPPORTED',p.deliveryId);check(Object.hasOwn(POTION_SPECS,p.effectId),'POTION_EFFECT_UNSUPPORTED',p.effectId);return p;}
export function potionEffects(effectId,durationTicks){
 const entries=POTION_SPECS[effectId];check(entries,'POTION_EFFECT_UNSUPPORTED',effectId);
 if(!entries.length)return [];
 const instantaneous=entries.every(([e])=>e==='instant_health'||e==='instant_damage');
 if(!instantaneous)integer(durationTicks,1,20000000,'potion duration ticks');
 return entries.map(([effect,amplifier])=>({effect:'minecraft:'+effect,duration:instantaneous?0:Math.floor(durationTicks/20),amplifier,probability:1}));
}
