import {check} from './util.js';

// A native inventory is authoritative once adopted. The old string-ID records
// remain readable for pre-upgrade worlds; they are never a fallback for a lost
// or corrupt native inventory. No ItemStack metadata is serialized into JSON.
export const NATIVE_ITEM_ENTITY='kaleidoscope_tavern:stored_items';
export const NATIVE_STORAGE_OWNER='kaleidoscope_tavern:storage_owner';
const OWNER=NATIVE_STORAGE_OWNER,TOKEN='kaleidoscope_tavern:storage_token';
const padded=(ids,size)=>{check(Array.isArray(ids)&&ids.length<=size&&ids.every(id=>id===null||typeof id==='string'&&id.length>0),'NATIVE_STORAGE_IDS');return Array.from({length:size},(_,i)=>ids[i]??null);};
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
// Position identity is the three finite numeric coordinates, not object key order.
const samePosition=(a,b)=>{
 if(a==null||b==null)return false;
 for(const axis of ['x','y','z']){
  const left=a[axis],right=b[axis];
  if(!Number.isFinite(left)||!Number.isFinite(right)||left!==right)return false;
 }
 return true;
};
// Counted callers keep whole stacks in the same native owner. Omitted counts
// retain the established one-item display contract and its existing save shape.
const amounts=(ids,counts,size)=>{
 check(counts===undefined||Array.isArray(counts)&&counts.length<=size,'NATIVE_STORAGE_COUNTS');
 const result=ids.map((id,i)=>id?(counts===undefined?1:counts[i]):0);
 check(result.every((count,i)=>ids[i]?Number.isInteger(count)&&count>0&&count<=255:counts===undefined||!counts[i]),'NATIVE_STORAGE_COUNTS');
 return result;
};
const counted=(item,count)=>{check(item&&count<=item.maxAmount,'NATIVE_STORAGE_STACK_CAPACITY');const stack=item.clone();stack.amount=count;check(stack.amount===count,'NATIVE_STORAGE_STACK_CAPACITY');return stack;};
export const nativeItemKey=key=>'kt:native_items/'+key;
const requiredKey=key=>'kt:native_required/'+key;
// Host adapters may use their own backing entity without requiring the Tavern pack.
export class NativeItemStorage {
 constructor({backend,findEntity,createEntity,makeStack,entityType=NATIVE_ITEM_ENTITY,size=9,legacySize=size,token=()=>Math.random().toString(36).slice(2)}){check(Number.isInteger(size)&&size>0&&Number.isInteger(legacySize)&&legacySize>0&&legacySize<=size,'NATIVE_STORAGE_SIZE');Object.assign(this,{backend,findEntity,createEntity,makeStack,entityType,size,legacySize,token});}
 read(input){return this.#read(input,true);}
 #read({key,dimension,position,ids,counts,legacyStacks,requireNative=false},requirePosition){
  const size=this.size;ids=padded(ids,size);const sizes=amounts(ids,counts,size),raw=this.backend.getDynamicProperty(nativeItemKey(key)),required=this.backend.getDynamicProperty(requiredKey(key));
  if(raw===undefined){
   check(required===undefined&&!requireNative,'NATIVE_STORAGE_MISSING');
   return {raw,required,ids,counts:sizes,items:ids.map((id,i)=>id?counted(legacyStacks?.[i]??this.makeStack(id,sizes[i]),sizes[i]):undefined)};
  }
  check(typeof raw==='string','NATIVE_STORAGE_CORRUPT');let record;
  try{record=JSON.parse(raw);}catch{check(false,'NATIVE_STORAGE_CORRUPT');}
  check(required===1&&record?.schema===1&&record.key===key&&record.dimension===dimension.id&&samePosition(record.position,position)&&Array.isArray(record.ids)&&[size,this.legacySize].includes(record.ids.length)&&same(padded(record.ids,size),ids),'NATIVE_STORAGE_MISMATCH');
  check(counts===undefined?record.counts===undefined:same(record.counts,sizes),'NATIVE_STORAGE_COUNT_MISMATCH');
  check(typeof record.entity==='string'&&typeof record.token==='string'&&record.token.length>0,'NATIVE_STORAGE_CORRUPT');
  const entity=this.findEntity(record.entity);
  check(entity?.isValid&&entity.typeId===this.entityType&&entity.dimension.id===dimension.id,'NATIVE_STORAGE_UNAVAILABLE');
  check(entity.getDynamicProperty(OWNER)===key&&entity.getDynamicProperty(TOKEN)===record.token,'NATIVE_STORAGE_WRONG_OWNER');
  const p=entity.location;
  const centered=p&&Math.abs(p.x-position.x-.5)<.1&&Math.abs(p.y-position.y-.5)<.1&&Math.abs(p.z-position.z-.5)<.1;
  if(requirePosition&&!centered){try{this.requestReanchor?.(key);}catch{/* Recovery scheduling must not mask the strict read failure. */}check(false,'NATIVE_STORAGE_MOVED');}
  const container=entity.getComponent('minecraft:inventory')?.container;check(container&&[size,this.legacySize].includes(container.size)&&ids.slice(container.size).every(id=>!id),'NATIVE_STORAGE_CONTAINER');
  const items=Array.from({length:size},(_,i)=>i<container.size?container.getItem(i)?.clone():undefined);
  for(let i=0;i<size;i++)check(ids[i]?items[i]?.typeId===ids[i]&&items[i].amount===sizes[i]:!items[i],'NATIVE_STORAGE_CONTENT_MISMATCH');
  return {raw,required,record,entity,container,ids,counts:sizes,items};
 }
 /** Read-only recovery proof: every normal native check except current position.
  * Only the separate after-event adapter may move this exact owned entity. */
 inspectForReanchor({key,dimension,position,entity}){
  const raw=this.backend.getDynamicProperty(nativeItemKey(key));
  check(typeof raw==='string','NATIVE_STORAGE_MISSING');let record;
  try{record=JSON.parse(raw);}catch{check(false,'NATIVE_STORAGE_CORRUPT');}
  check(Array.isArray(record?.ids)&&[this.size,this.legacySize].includes(record.ids.length)&&record.ids.some(Boolean),'NATIVE_STORAGE_IDS');
  const proof=this.#read({key,dimension,position,ids:record.ids,counts:record.counts,requireNative:true},false);
  check(entity?.isValid&&entity.id===proof.record.entity&&entity.id===proof.entity.id,'NATIVE_STORAGE_WRONG_ENTITY');
  check(['x','y','z'].every(axis=>Number.isFinite(proof.entity.location?.[axis])),'NATIVE_STORAGE_MOVED');
  return proof;
 }
 /** Read an adopted native container without trusting a stale display index. */
 readAdopted({key,dimension,position}){
  const raw=this.backend.getDynamicProperty(nativeItemKey(key));
  if(raw===undefined){check(this.backend.getDynamicProperty(requiredKey(key))===undefined,'NATIVE_STORAGE_MISSING');return undefined;}
  check(typeof raw==='string','NATIVE_STORAGE_CORRUPT');let record;
  try{record=JSON.parse(raw);}catch{check(false,'NATIVE_STORAGE_CORRUPT');}
  // read still validates key, location, owner, token and every native slot.
  return this.read({key,dimension,position,ids:record?.ids,counts:record?.counts,requireNative:true});
 }
 plan({key,dimension,position,oldIds,nextIds,oldCounts,nextCounts,incoming,give=[],legacyStacks,requireNative=false,nextItems}){
  const size=this.size;position={x:position.x,y:position.y,z:position.z};
  check(typeof key==='string'&&key.length>0&&Object.values(position).every(Number.isInteger),'NATIVE_STORAGE_LOCATION');
  check((oldCounts===undefined)===(nextCounts===undefined)&& (nextCounts===undefined||nextItems!==undefined),'NATIVE_STORAGE_ITEMS');
  const before=this.read({key,dimension,position,ids:oldIds,counts:oldCounts,legacyStacks,requireNative}),ids=padded(nextIds,size),counts=amounts(ids,nextCounts,size);
  const removed=before.ids.flatMap((id,i)=>id&&id!==ids[i]?[{slot:i,stack:before.items[i]}]:[]);
  const additions=ids.flatMap((id,i)=>id&&id!==before.ids[i]?[i]:[]);
  check(nextItems!==undefined||additions.length<=1,'NATIVE_STORAGE_MULTIPLE_INPUTS');
  if(nextItems!==undefined){
   check(Array.isArray(nextItems)&&nextItems.length<=size,'NATIVE_STORAGE_ITEMS');
   for(let i=0;i<size;i++)check(ids[i]?nextItems[i]?.typeId===ids[i]&&nextItems[i].amount===counts[i]:!nextItems[i],'NATIVE_STORAGE_INPUT_MISMATCH');
  }
  for(const i of additions){const item=nextItems?.[i]??incoming;check(item?.typeId===ids[i]&&item.amount>=counts[i],'NATIVE_STORAGE_INPUT_MISMATCH');}
  // Explicit native replacements update a stored item's payload without
  // changing its identifier. Each side retains its own complete native copy.
  const after=ids.map((id,i)=>!id?undefined:nextItems?nextItems[i].clone():id===before.ids[i]?before.items[i]?.clone():counted(incoming,counts[i]));
  // Match only removed slots, never another identically named/type-ID slot.
  const available=removed.slice(),outputs=[];
  for(const output of give){
   check(Number.isInteger(output.count)&&output.count>0&&output.count<=1024,'BAD_GIVE');
   let count=output.count;const id=output.stack?.typeId??output.id;
   while(count){const index=available.findIndex(row=>row.stack.typeId===id);if(index<0)break;
    const row=available[index],size=Math.min(count,row.stack.amount);outputs.push({...output,stack:counted(row.stack,size),count:size,exact:true});count-=size;
    if(size===row.stack.amount)available.splice(index,1);else row.stack=counted(row.stack,row.stack.amount-size);
   }
   if(count)outputs.push({...output,count});
  }
  let entity=before.entity,container=before.container,created=false,applied=false;
  const priorEntity=entity,priorContainer=container;
  const occupied=ids.some(Boolean),newToken=before.record?.token??this.token();
  return {
   outputs,before:before.items.map(x=>x?.clone()),after:after.map(x=>x?.clone()),removed,
   apply:()=>{
    check(!applied,'NATIVE_STORAGE_REUSED_TRANSACTION');
    check(this.backend.getDynamicProperty(nativeItemKey(key))===before.raw&&this.backend.getDynamicProperty(requiredKey(key))===before.required,'NATIVE_STORAGE_CONFLICT');
    applied=true;
    if(occupied&&(!entity||container.size!==size)){entity=this.createEntity(dimension,{x:position.x+.5,y:position.y+.5,z:position.z+.5});created=true;
     check(entity?.isValid&&entity.typeId===this.entityType,'NATIVE_STORAGE_CREATE_FAILED');
     entity.setDynamicProperty(OWNER,key);entity.setDynamicProperty(TOKEN,newToken);
     container=entity.getComponent('minecraft:inventory')?.container;check(container?.size===size,'NATIVE_STORAGE_CONTAINER');
     for(let i=0;i<size;i++)check(!container.getItem(i),'NATIVE_STORAGE_NOT_EMPTY');
    }
    if(container)for(let i=0;i<container.size;i++)container.setItem(i,after[i]);
    // Grow the same owner with complete native copies; the former actor stays
    // recoverable until this plan commits. No metadata is reconstructed.
    if(created&&priorContainer)for(let i=0;i<priorContainer.size;i++)priorContainer.setItem(i,undefined);
    this.backend.setDynamicProperty(requiredKey(key),occupied?1:undefined);
    this.backend.setDynamicProperty(nativeItemKey(key),occupied?JSON.stringify({schema:1,key,dimension:dimension.id,position,ids,...(nextCounts===undefined?{}:{counts}),entity:entity.id,token:newToken}):undefined);
   },
   rollback:()=>{
    if(!applied)return;let failed=false;
    if(created){
     // A failed slot cleanup must not skip other slots or leave the staged
     // entity alive with a second copy of the restored input. A retry after
     // successful removal must not write through its now-invalid container.
     if(entity?.isValid!==false){
      if(container)for(let i=0;i<container.size;i++)try{container.setItem(i,undefined);}catch{failed=true;}
      try{entity?.remove();}catch{failed=true;}
     }
    }
    if(priorContainer)for(let i=0;i<priorContainer.size;i++)try{priorContainer.setItem(i,before.items[i]);}catch{failed=true;}
    // These are independent durable writes; attempt both even when one fails.
    try{this.backend.setDynamicProperty(nativeItemKey(key),before.raw);}catch{failed=true;}
    try{this.backend.setDynamicProperty(requiredKey(key),before.required);}catch{failed=true;}
    check(!failed,'NATIVE_STORAGE_ROLLBACK_FAILED');applied=false;
   },
   finish:()=>{if(!applied)return;for(const retired of [created?priorEntity:undefined,!occupied?entity:undefined])if(retired){try{retired.remove();}catch{/* Empty retired helper: never recreate or re-emit contents. */}}}
  };
 }
}
