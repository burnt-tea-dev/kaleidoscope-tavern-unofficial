import {visibleEffects,effectTime,effectLevel} from './effect-bar.js';
import {EFFECT_ICONS} from '../data/effect-icons.js';
export const EFFECT_ICON_PREFIX='§r§d§e§a§d§r';
export const EFFECT_ICON_HIDE_TAG='kaleidoscope_tavern:hide_effect_icons';
export const EFFECT_ICON_SLOTS=32;
export const EFFECT_ICON_INTERVAL=20;
/** The client rebuilds its HUD some ticks after a dimension transfer; one poll resend can land before that. */
export const EFFECT_ICON_REFRESH_DELAYS=Object.freeze([20,40]);
const icons=new Map(EFFECT_ICONS.map(row=>[row.id,row]));
export const effectIcon=id=>icons.get(id);
export function effectIconToken(slot,code){
 if(!Number.isInteger(slot)||slot<0||slot>=EFFECT_ICON_SLOTS||!Number.isInteger(code)||code<1||code>255)throw new RangeError('Effect icon token');
 return [...slot.toString(16).padStart(2,'0'),...code.toString(16).padStart(2,'0')].map(n=>'§'+n).join('')+'§r';
}
/** All bytes are valid formatting pairs: native title text remains empty without UI filters. */
export function effectIconPacket(state,hidden=false,enabled=()=>true){
 const rows=hidden?[]:visibleEffects(state).filter(row=>icons.has(row.id)&&enabled(row.id));
 return EFFECT_ICON_PREFIX+rows.slice(0,EFFECT_ICON_SLOTS).map((row,slot)=>effectIconToken(slot,icons.get(row.id).code)).join('');
}
export function effectDetails(state,enabled=()=>true){
 const rows=visibleEffects(state).filter(row=>enabled(row.id)),rawtext=[{translate:'kt.effects.snapshot'}];
 if(!rows.length)rawtext.push({text:'\n\n'},{translate:'kt.effects.empty'});
 for(const row of rows)rawtext.push({text:'\n\n§f'},{translate:'effect.'+row.id.replace(':','.')},{text:effectLevel(row.amplifier)+' §7'+effectTime(row.ticks)+'§r'});
 rawtext.push({text:'\n\n'},{translate:'kt.effects.native'});
 return {rawtext};
}
/** Read-only view. No saves, no countdown traffic and no Actionbar writes. */
export function createEffectIcons({status,available,send,enabled=()=>true,hidden=p=>p.hasTag?.(EFFECT_ICON_HIDE_TAG)===true,onError=()=>{}}){
 const views=new Map();
 return {
  forget:id=>views.delete(id),
  reset:id=>views.set(id,{packet:undefined,dimension:undefined}),
  /** Resend the CURRENT packet once for a view whose client may have rebuilt its HUD. Never replays a cached packet; a known inactive view stays silent. */
  dirty(id){const view=views.get(id);if(view)view.dirty=true;return view!==undefined;},
  tick(players){
   if(!available()){views.clear();return;}
   const seen=new Set();
   for(const player of players)try{
    if(player.isValid===false)continue;
    seen.add(player.id);const old=views.get(player.id),packet=effectIconPacket(status(player),hidden(player),enabled);
    const dimension=player.dimension?.id;
    // Inactive joins need no packet. Clearing contains only our scoped formatting header.
    if(packet===EFFECT_ICON_PREFIX&&!old)continue;
    // A known inactive view has nothing to rebuild after a transfer or refresh request.
    if(packet===EFFECT_ICON_PREFIX&&old?.packet===EFFECT_ICON_PREFIX){views.set(player.id,{packet,dimension});continue;}
    if(!old?.dirty&&old?.packet===packet&&old.dimension===dimension)continue;
    send(player,packet);views.set(player.id,{packet,dimension});
   }catch(error){onError(error);}
   for(const id of views.keys())if(!seen.has(id))views.delete(id);
  }
 };
}
/**
 * Limited refresh after a dimension transfer (issue #285): mark the view dirty
 * at each delay so the ordinary poll reads and sends the current status. A
 * newer transfer, spawn or leave cancels pending work; an invalid handle or a
 * different destination dimension discards the callback.
 */
export function createDimensionRefresh({schedule,cancel,refresh,delays=EFFECT_ICON_REFRESH_DELAYS}){
 const pending=new Map();
 const clear=id=>{for(const handle of pending.get(id)??[])try{cancel(handle);}catch{}pending.delete(id);};
 return {
  pending:id=>pending.get(id)?.length??0,
  cancel:clear,
  changed(id,destination,current){
   clear(id);
   const handles=[];pending.set(id,handles);
   for(const delay of delays){
    const handle=schedule(()=>{
     if(pending.get(id)!==handles)return;
     handles.splice(handles.indexOf(handle),1);if(!handles.length)pending.delete(id);
     let player;try{player=current();}catch{return;}
     if(!player||player.isValid===false||player.dimension?.id!==destination)return;
     refresh(id);
    },delay);
    handles.push(handle);
   }
  }
 };
}
