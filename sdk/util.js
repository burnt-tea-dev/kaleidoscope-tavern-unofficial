/** Client-side pure utilities used by the public Tavern extension SDK. */
export class TavernError extends Error {
 constructor(code,detail=''){super(detail?`${code}: ${detail}`:code);this.name='TavernError';this.code=code;}
}
export function check(ok,code,detail=''){if(!ok)throw new TavernError(code,detail);}
export function canonical(value){
 if(Array.isArray(value))return '['+value.map(canonical).join(',')+']';
 if(value&&typeof value==='object')return '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+canonical(value[k])).join(',')+'}';
 return JSON.stringify(value);
}
export function utf8Bytes(s){let n=0;for(const c of s){const v=c.codePointAt(0);n+=v<128?1:v<2048?2:v<65536?3:4;}return n;}
/** Integrity checksum, NOT a signature/authentication mechanism. */
export function digest(s){let h=2166136261;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619);}return(h>>>0).toString(16).padStart(8,'0');}

/** JSON data preparation with bounded work between yields. Wire order is unchanged. */
function* quotedTokens(value){
 let chunk='"';
 for(let i=0;i<value.length;i++){
  const code=value.charCodeAt(i);
  if(code===34)chunk+='\\"';
  else if(code===92)chunk+='\\\\';
  else if(code===8)chunk+='\\b';
  else if(code===9)chunk+='\\t';
  else if(code===10)chunk+='\\n';
  else if(code===12)chunk+='\\f';
  else if(code===13)chunk+='\\r';
  else if(code<32||code>=0xd800&&code<=0xdfff&&!(code<=0xdbff&&value.charCodeAt(i+1)>=0xdc00&&value.charCodeAt(i+1)<=0xdfff))chunk+='\\u'+code.toString(16).padStart(4,'0');
  else if(code>=0xd800&&code<=0xdbff){chunk+=value.slice(i,i+2);i++;}
  else chunk+=value[i];
  if(chunk.length>=1024){yield chunk;chunk='';}
 }
 yield chunk+'"';
}
function* jsonTokens(value,canonicalKeys,arrayMember=false){
 if(typeof value==='string'){yield* quotedTokens(value);return;}
 if(Array.isArray(value)){
  yield '[';
  for(let i=0;i<value.length;i++){
   if(i)yield ',';
   if(canonicalKeys&&!Object.hasOwn(value,i))continue;
   yield* jsonTokens(value[i],canonicalKeys,true);
  }
  yield ']';return;
 }
 if(value&&typeof value==='object'){
  yield '{';let comma=false;
  const keys=Object.keys(value);if(canonicalKeys)keys.sort();
  for(const key of keys){
   const row=value[key];
   if(!canonicalKeys&&['undefined','function','symbol'].includes(typeof row))continue;
   if(comma)yield ',';comma=true;
   yield* quotedTokens(key);yield ':';yield* jsonTokens(row,canonicalKeys);
  }
  yield '}';return;
 }
 const encoded=JSON.stringify(value);
 yield encoded===undefined?(canonicalKeys?(arrayMember?'':'undefined'):'null'):encoded;
}
export function* prepareJson(value,{canonicalKeys=false}={}){
 const parts=[];let units=0,tokens=0;
 for(const token of jsonTokens(value,canonicalKeys)){
  parts.push(token);units+=token.length;
  if(++tokens>=128||units>=2048){units=0;tokens=0;yield;}
 }
 return parts.join('');
}
export function* prepareDigest(value){
 let h=2166136261;
 for(let i=0;i<value.length;i++){
  h^=value.charCodeAt(i);h=Math.imul(h,16777619);
  if((i+1)%2048===0)yield;
 }
 return (h>>>0).toString(16).padStart(8,'0');
}
/** JSON clone for owned plain data, without one large stringify/parse step. */
export function* prepareClone(value){
 let nodes=0;
 function* copy(row){
  if(++nodes%64===0)yield;
  if(Array.isArray(row)){const out=[];for(const item of row)out.push(yield* copy(item));return out;}
  if(row&&typeof row==='object'){const out={};for(const [key,item]of Object.entries(row))if(!['undefined','function','symbol'].includes(typeof item))out[key]=yield* copy(item);return out;}
  return typeof row==='number'&&!Number.isFinite(row)?null:row;
 }
 return yield* copy(value);
}
/** Exact UTF-8 cost inside a JSON-quoted string, excluding its two quotes. */
export function jsonCodepointBytes(code){
 return code===34||code===92||code===8||code===9||code===10||code===12||code===13?2:
  code<32||code>=0xd800&&code<=0xdfff?6:code<128?1:code<2048?2:code<65536?3:4;
}
export function finishPreparation(job){let result;do{result=job.next();}while(!result.done);return result.value;}
