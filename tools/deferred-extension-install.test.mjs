import test from 'node:test';
import assert from 'node:assert/strict';
import {ExtensionTransport,EVENTS,packetsFor,createMutationQueue} from '../runtime/BP/scripts/core/transport.js';
import {ExtensionRegistry} from '../runtime/BP/scripts/core/registry.js';
import {prepareFreeze,finishPreparation} from '../runtime/BP/scripts/core/util.js';

const bundle=(source,revision,label)=>({api:1,source,version:'1.0.0',pages:[{id:`${source}:page`,title:{en_US:label},body:{en_US:`${label} 葡萄🍇`},recipeIds:[]}]});
function prepare(receiver,raw,revision,tick=0){
 let result;
 for(const packet of packetsFor(raw,revision))result=receiver.receive(packet.id,packet.message,tick);
 assert(result?.mutationJob,'deferred COMMIT returns a job');return result.mutationJob;
}
function drain(job){let result;do{result=job.job.next();}while(!result.done);return result.value;}

test('deferred install keeps old snapshot and listeners until atomic commit',()=>{
 const registry=new ExtensionRegistry(),receiver=new ExtensionTransport(registry,{deferred:true});let notices=0;registry.subscribe(()=>notices++);
 const old=bundle('install_probe','old','Old'),next=bundle('install_probe','next','New');next.pages=Array.from({length:20},(_,i)=>({id:`install_probe:page_${i}`,title:{en_US:`New ${i}`},body:{en_US:`New 葡萄🍇 ${i}`},recipeIds:[]}));registry.install(old);const before=registry.revision,oldPage=registry.allPages()[0];
 const job=prepare(receiver,next,'new_revision');
 for(let i=0;i<4;i++){assert.equal(job.job.next().done,false);assert.equal(registry.revision,before);assert.equal(registry.allPages()[0],oldPage);assert.equal(notices,1);}
 drain(job);assert.equal(registry.revision,before+1);assert.equal(registry.allPages()[0].title.en_US,'New 0');assert.equal(registry.allPages()[0].body.en_US,'New 葡萄🍇 0');assert.equal(notices,2);
});

test('incremental freeze traverses children of shallow-frozen parents',()=>{
 const value=Object.freeze({child:Object.freeze({nested:{value:'kept'}})});
 assert.equal(finishPreparation(prepareFreeze(value)),value);
 assert(Object.isFrozen(value));assert(Object.isFrozen(value.child));assert(Object.isFrozen(value.child.nested));
 const deep={row:[{value:1}]};finishPreparation(prepareFreeze(deep));
 assert(Object.isFrozen(deep.row[0]));assert(Object.isFrozen(deep.row));assert(Object.isFrozen(deep));
});

test('registry rebuild yields between native item-tag reads',()=>{
 let reads=0;const registry=new ExtensionRegistry({itemTags:()=>{reads++;return [];}});
 registry.install({api:1,source:'tag_probe',version:'1.0.0',shakerInputs:Array.from({length:80},(_,i)=>({item:`tag_probe:input_${i}`,ingredientTags:['tag_probe:fruit']}))});
 const job=registry.prepareRebuild();let step;
 do{const before=reads;step=job.next();assert(reads-before<=1,'one scheduler step performs at most one native tag read');}while(!step.done);
 assert(registry.categoryCatalog.tags('tag_probe:input_79').includes('tag_probe:fruit'));
});

test('more than sixteen distinct completed transfers remain FIFO and all commit',()=>{
 const registry=new ExtensionRegistry(),receiver=new ExtensionTransport(registry,{deferred:true}),completed=[];
 const queue=createMutationQueue({generation:source=>receiver.generation(source),complete:job=>completed.push(job.source),failed:(_job,error)=>{throw error;},superseded:job=>{throw new Error(`unexpected cancel ${job.source}`);}});
 const sources=Array.from({length:20},(_,i)=>`queued_addon_${String(i).padStart(2,'0')}`);
 for(const source of sources)assert(queue.enqueue(prepare(receiver,bundle(source,'queued_r','Queued'),'queued_revision')));
 while(queue.size)queue.pump();
 assert.deepEqual(completed,sources);assert.equal(registry.list().length,20);assert.equal(registry.allPages().length,20);
});

test('bad deferred payload leaves the prior snapshot and revision intact',()=>{
 const registry=new ExtensionRegistry(),receiver=new ExtensionTransport(registry,{deferred:true});registry.install(bundle('invalid_probe','old','Old'));
 const before=registry.revision,oldPage=registry.allPages()[0];
 const invalid=bundle('invalid_probe','bad','Bad');invalid.pages[0].recipeIds=Array.from({length:33},(_,i)=>`kaleidoscope_tavern:missing_${i}`);
 const job=prepare(receiver,invalid,'bad_revision');
 assert.throws(()=>drain(job),error=>error.code==='TOO_MANY_PAGE_RECIPES'&&error.packetContext.source==='invalid_probe'&&error.packetContext.revision==='bad_revision');
 assert.equal(registry.revision,before);assert.equal(registry.allPages()[0],oldPage);
});

test('new BEGIN invalidates an older queued commit generation',()=>{
 const registry=new ExtensionRegistry(),receiver=new ExtensionTransport(registry,{deferred:true});
 const old=prepare(receiver,bundle('replace_probe','old','Old'),'old_revision');
 const next=bundle('replace_probe','new','New'),packets=packetsFor(next,'new_revision');
 const started=receiver.receive(EVENTS.begin,packets[0].message,1).transferStarted;
 assert(started.generation>old.generation);assert.notEqual(receiver.generation(old.source),old.generation);
 // The native host checks this token before each pump step and reports the old job as superseded.
 assert.equal(receiver.pending.get(old.source).revision,'new_revision');
});

test('deferred UNREGISTER leaves its extension visible until removal commits',()=>{
 const registry=new ExtensionRegistry(),receiver=new ExtensionTransport(registry,{deferred:true});registry.install(bundle('remove_probe','installed','Installed'));
 const before=registry.revision,result=receiver.receive(EVENTS.unregister,JSON.stringify({api:1,source:'remove_probe'}),1),job=result.mutationJob;
 assert.equal(registry.extensions.has('remove_probe'),true);assert.equal(registry.revision,before);
 assert.equal(drain(job),true);assert.equal(registry.extensions.has('remove_probe'),false);assert.equal(registry.revision,before+1);
});

test('native FIFO pump stays bounded with a frozen clock and reports superseded work',()=>{
 const generations=new Map([['first_addon',0],['second_addon',0]]),completed=[],failed=[],cancelled=[];let steps=0;
 const queue=createMutationQueue({generation:source=>generations.get(source),clock:()=>1234,complete:(job,value)=>completed.push([job.source,value]),failed:(job,error)=>failed.push([job.source,error]),superseded:job=>cancelled.push(job.source)});
 function* work(source){for(let i=0;i<100;i++){steps++;yield;}return source;}
 const old={source:'first_addon',revision:'old',generation:0,job:work('old')};
 assert(queue.enqueue(old));assert(queue.enqueue({source:'second_addon',generation:0,job:work('second')}));
 queue.pump();assert.equal(steps,32);assert.equal(queue.size,2);
 generations.set('first_addon',1);queue.supersede('first_addon',1);queue.pump();assert.deepEqual(cancelled,['first_addon']);
 let pumps=0;while(queue.size&&pumps<20){const before=steps;queue.pump();assert(steps-before<=32);pumps++;}
 assert.equal(queue.size,0);assert(completed.some(([,value])=>value==='second'));assert.deepEqual(failed,[]);
});

test('scheduled host queue stays idle without jobs and uses one-shot ticks while busy',()=>{
 const callbacks=[],completed=[];let schedules=0,steps=0;
 const queue=createMutationQueue({generation:()=>0,complete:(job,value)=>completed.push(value),failed:()=>assert.fail('job failed'),superseded:()=>assert.fail('unexpected cancel'),clock:()=>55,schedule:callback=>{schedules++;callbacks.push(callback);}});
 assert.equal(queue.size,0);assert.equal(schedules,0);assert.equal(callbacks.length,0);
 function* work(){for(let i=0;i<100;i++){steps++;yield;}return 'done';}
 assert(queue.enqueue({source:'synthetic_addon',generation:0,job:work()}));assert.equal(schedules,1);assert.equal(callbacks.length,1);
 let ticks=0;while(callbacks.length){const callback=callbacks.shift(),before=steps;callback();assert(steps-before<=32);ticks++;}
 assert(ticks>=4);assert.deepEqual(completed,['done']);assert.equal(queue.size,0);assert.equal(callbacks.length,0);assert.equal(schedules,ticks);
});
