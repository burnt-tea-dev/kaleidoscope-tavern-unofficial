import test from 'node:test';
import assert from 'node:assert/strict';
import {ExtensionRegistry} from '../runtime/BP/scripts/core/registry.js';
import {finishPreparation,utf8Bytes} from '../runtime/BP/scripts/core/util.js';
import {prepareDrinkFoodCatalog,installFoodCatalogPublisher,FOOD_CATALOG_EVENT,FOOD_CATALOG_REQUEST} from '../runtime/BP/scripts/core/food-catalog-publisher.js';

const source='drink_fixture';
function bottle(index=0){
 const stem=source+':vintage_'+index;
 return {kind:'bottle',base:stem,block:stem+'_preview',maxCount:1,visualKind:1000+index,
  items:['young','oak','reserve','cellar','aged','mature'].map(name=>stem+'_'+name),
  qualityBlocks:Array.from({length:6},(_,i)=>stem+'_display_'+i),effects:Array.from({length:6},()=>[])};
}
function extension(count=1){
 const content=Array.from({length:count},(_,i)=>bottle(i));
 return {api:1,source,version:'1.0.0',content:[...content,{kind:'cocktail',item:source+':mixed_drink',block:source+':mixed_cup',effects:[]}],
  shakerInputs:[{item:source+':unrelated_q4'}],
  pages:content.map(row=>({id:row.base,item:row.items[0],category:'barrel',title:{zh_TW:'果釀🍇',en_US:'Fruit Wine'},body:{en_US:'A declared drink.'}}))};
}
function clock(){
 let next=0;const pending=new Map(),listeners=new Set(),sent=[];
 const system={run(fn){pending.set(++next,fn);return next;},clearRun(id){pending.delete(id);},sendScriptEvent(id,message){sent.push({id,message});},
  afterEvents:{scriptEventReceive:{subscribe(fn){listeners.add(fn);},unsubscribe(fn){listeners.delete(fn);}}}};
 function emit(message='{"v":1}',sourceType='Server'){for(const fn of listeners)fn({id:FOOD_CATALOG_REQUEST,message,sourceType});}
 function drain(){let ticks=0;while(pending.size){assert(++ticks<1000,'publisher must become idle');const before=sent.length,work=[...pending.values()];pending.clear();for(const fn of work)fn();assert(sent.length-before<=2,'at most two event packets per scheduled tick');}return ticks;}
 return {system,sent,emit,drain,pending};
}

test('accepted drink types and explicit quality arrays supply aliases without name guessing',()=>{
 const registry=new ExtensionRegistry();registry.install(extension());const before=JSON.stringify(registry.allDrinkContent()),reads=[];
 const providers=finishPreparation(prepareDrinkFoodCatalog(registry,id=>{reads.push(id);return id.endsWith(':mixed_drink')?3:0;}));
 assert.deepEqual([...providers.keys()],[source]);const foods=providers.get(source),wine=foods.find(row=>row.typeId===bottle().items[0]);
 assert.equal(foods.length,2);assert.equal(wine.label,'果釀🍇');assert.equal(wine.nutrition,0);assert.equal(wine.servingKind,'drink');
 assert.deepEqual(wine.aliases,[...bottle().items.slice(1),bottle().block].sort());
 assert.equal(foods.find(row=>row.typeId===source+':mixed_drink').nutrition,3,'positive native nutrition is preserved');
 assert.equal(reads.length,2,'only each canonical native item is queried');
 assert(!foods.some(row=>row.typeId.endsWith('unrelated_q4')),'a shaker input is not a drink declaration');
 assert.equal(JSON.stringify(registry.allDrinkContent()),before);registry.remove(source);
});

test('late registration, request replay and withdrawal use bounded events and leave no idle work',()=>{
 const registry=new ExtensionRegistry(),c=clock(),publisher=installFoodCatalogPublisher(c.system,registry,{nutritionFor:()=>0,warn:error=>assert.fail(error)});
 c.drain();assert.equal(c.sent.length,0,'standalone Tavern does not replace OTC built-in catalogs');
 registry.install(extension(12));c.drain();assert(c.sent.length>2);
 for(const packet of c.sent){assert.equal(packet.id,FOOD_CATALOG_EVENT);assert(utf8Bytes(packet.message)<=1900);}
 const first=c.sent.map(packet=>JSON.parse(packet.message));assert.equal(first[0].replace,true);assert(first.slice(1).every(packet=>packet.replace===undefined));
 assert.equal(first.flatMap(packet=>packet.foods).length,13);
 const initial=c.sent.length;registry.rebuild();c.drain();assert.equal(c.sent.length,initial,'unchanged providers do not retransmit on unrelated registry rebuilds');
 c.emit('{"v":1}','Entity');c.emit('{"v":2}');c.emit('not json');c.drain();assert.equal(c.sent.length,initial);
 c.emit();c.drain();assert.deepEqual(c.sent.slice(initial),c.sent.slice(0,initial),'a later OTC startup receives the current full declaration');
 registry.remove(source);c.drain();assert.deepEqual(JSON.parse(c.sent.at(-1).message),{v:1,provider:source,replace:true,foods:[]});
 publisher.dispose();c.emit();assert.equal(c.pending.size,0);
});

test('native reads and transport failures preserve retry through the next real request',()=>{
 const registry=new ExtensionRegistry();registry.install(extension(4));const c=clock(),warnings=[];let nativeUnavailable=true;
 const publisher=installFoodCatalogPublisher(c.system,registry,{nutritionFor:()=>{if(nativeUnavailable)throw Error('native unavailable');return 0;},warn:error=>warnings.push(String(error))});
 c.drain();assert.equal(c.sent.length,0);assert.match(warnings[0],/native unavailable/);
 nativeUnavailable=false;const send=c.system.sendScriptEvent;let failed=false;
 c.system.sendScriptEvent=(id,message)=>{if(!failed){failed=true;throw Error('transport unavailable');}send(id,message);};
 c.emit();c.drain();assert.equal(c.sent.length,0);assert.match(warnings[1],/transport unavailable/);
 c.emit();c.drain();assert.equal(JSON.parse(c.sent[0].message).replace,true);assert.equal(c.sent.flatMap(packet=>JSON.parse(packet.message).foods).length,5);
 publisher.dispose();registry.remove(source);
});

test('ambiguous declared aliases fail before publishing a partial catalog',()=>{
 const registry=new ExtensionRegistry(),payload=extension(2);payload.content[1].items[1]=payload.content[0].items[0];registry.install(payload);
 const c=clock(),warnings=[],publisher=installFoodCatalogPublisher(c.system,registry,{nutritionFor:()=>0,warn:error=>warnings.push(String(error))});
 c.drain();assert.equal(c.sent.length,0);assert.match(warnings[0],/Conflicting drink alias/);
 registry.install(extension(2));c.drain();assert.equal(c.sent.flatMap(packet=>JSON.parse(packet.message).foods).length,3);
 const previous=c.sent.length,duplicate=extension(2);duplicate.content[1].items[0]=duplicate.content[0].items[0];registry.install(duplicate);c.drain();
 assert.equal(c.sent.length,previous,'a duplicate canonical ID cannot silently discard an earlier alias set');assert.match(warnings.at(-1),/Duplicate drink canonical ID/);
 publisher.dispose();registry.remove(source);
});
