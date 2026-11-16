/** Optional OTC menu declarations from the host's accepted drink descriptors. */
import {utf8Bytes} from './util.js';

export const FOOD_CATALOG_EVENT='ordertocook:food_catalog_v1';
export const FOOD_CATALOG_REQUEST='ordertocook:food_catalog_request_v1';
const PACKET_BYTES=1900;

/** Snapshot accepted data before yielding; quality aliases are explicit IDs. */
export function* prepareDrinkFoodCatalog(registry,nutritionFor){
 const content=registry.allDrinkContent(),pages=registry.allPages(),recipes=new Map(registry.allRecipes().map(row=>[row.id,row]));
 const labels=new Map(),providers=new Map();
 for(const page of pages){
  const label=page.title?.zh_TW??page.title?.en_US??page.title?.zh_CN;
  if(label)for(const item of [page.id,page.item,...(page.recipeIds??[]).flatMap(id=>{
   const output=recipes.get(id)?.output;return output?.byQuality??(output?.item?[output.item]:[]);
  })])if(item?.startsWith(page.source+':'))labels.set(item,label.slice(0,100));
  yield;
 }
 for(const drink of content){
  const items=drink.kind==='bottle'?drink.items:[drink.item],typeId=items[0],provider=typeId.split(':')[0];
  // The receiver reserves vanilla items and its own menu namespace.
  if(provider==='minecraft'||provider==='ordertocook')continue;
  const aliases=[...new Set([...items.slice(1),...(drink.genericItem?[drink.genericItem]:[])])].filter(id=>id!==typeId).sort();
  const nutrition=nutritionFor(typeId);
  if(!Number.isInteger(nutrition)||nutrition<0||nutrition>10000)throw new Error('Invalid native drink nutrition: '+typeId);
  const food={typeId,nutrition,servingKind:'drink',label:labels.get(typeId)??labels.get(drink.genericItem)??typeId,...(aliases.length?{aliases}:{})};
  let foods=providers.get(provider);if(!foods)providers.set(provider,foods=new Map());
  if(foods.has(typeId))throw new Error('Duplicate drink canonical ID: '+typeId);
  foods.set(typeId,food);
  yield;
 }
 for(const [provider,rows] of providers){
  const owners=new Map(),foods=[...rows.values()].sort((a,b)=>a.typeId.localeCompare(b.typeId));
  for(const food of foods){
   for(const item of [food.typeId,...food.aliases??[]]){
    if(owners.has(item)&&owners.get(item)!==food.typeId)throw new Error('Conflicting drink alias: '+item);
    owners.set(item,food.typeId);
   }
   yield;
  }
  providers.set(provider,foods);
 }
 return providers;
}

function* prepareMessages(providers,advertised){
 const result=new Map(),encode=(provider,foods,replace)=>JSON.stringify({v:1,provider,...(replace?{replace:true}:{}),foods});
 for(const provider of advertised)if(!providers.has(provider))result.set(provider,[encode(provider,[],true)]);
 for(const [provider,foods] of providers){
  const messages=[];let batch=[],replace=true;
  for(const food of foods){
   let message=encode(provider,[...batch,food],replace);
   if(utf8Bytes(message)>PACKET_BYTES){
    if(batch.length){messages.push(encode(provider,batch,replace));batch=[];replace=false;}
    message=encode(provider,[food],replace);
    if(utf8Bytes(message)>PACKET_BYTES)throw new Error('Drink declaration exceeds the OTC packet limit: '+food.typeId);
   }
   batch.push(food);yield;
  }
  if(batch.length)messages.push(encode(provider,batch,replace));
  result.set(provider,messages);
 }
 return result;
}

/** Event-driven preparation and bounded one-shot work; no polling or hard dependency. */
export function installFoodCatalogPublisher(system,registry,{nutritionFor,warn=console.warn}){
 let disposed=false,dirty=false,requested=false,job,handle;
 const advertised=new Set(),sent=new Map();
 function schedule(){if(!disposed&&handle===undefined)handle=system.run(pump);}
 function refresh(){dirty=true;schedule();}
 function* publish(force){
  const providers=yield* prepareDrinkFoodCatalog(registry,nutritionFor);
  const messages=yield* prepareMessages(providers,advertised);
  for(const [provider,packets] of messages){
   const identity=packets.join('\n');if(!force&&sent.get(provider)===identity)continue;
   for(const message of packets){
    system.sendScriptEvent(FOOD_CATALOG_EVENT,message);
    if(providers.has(provider))advertised.add(provider);else advertised.delete(provider);
    yield true;
   }
   if(providers.has(provider))sent.set(provider,identity);else sent.delete(provider);
  }
 }
 function pump(){
  handle=undefined;if(disposed)return;
  if(!job){if(!dirty)return;dirty=false;job=publish(requested);requested=false;}
  try{
   let packets=0;
   for(let steps=0;steps<16&&packets<2;steps++){
    const step=job.next();if(step.done){job=undefined;break;}if(step.value===true)packets++;
   }
  }catch(error){job=undefined;warn('[Tavern] OTC drink catalog: '+error);}
  if(job||dirty)schedule();
 }
 const receive=event=>{
  if(event.id!==FOOD_CATALOG_REQUEST||event.sourceType!=='Server')return;
  try{if(JSON.parse(event.message)?.v!==1)return;}catch{return;}
  requested=true;refresh();
 };
 system.afterEvents.scriptEventReceive.subscribe(receive,{namespaces:['ordertocook']});
 const unsubscribe=registry.subscribe(refresh);
 refresh(); // Also covers an OTC request sent before Tavern's asynchronous startup.
 return {refresh,dispose(){disposed=true;job=undefined;unsubscribe();system.afterEvents.scriptEventReceive.unsubscribe(receive);if(handle!==undefined)system.clearRun(handle);}};
}
