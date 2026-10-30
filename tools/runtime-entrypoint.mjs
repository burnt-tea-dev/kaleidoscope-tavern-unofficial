/** Execute the production entrypoint body against isolated imported interfaces.
 * This observes call order, phase and arguments. It does not execute imported
 * Bedrock modules, simulate players, or certify native/client initialization.
 */
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
import vm from 'node:vm';

// Reviewed T127 order plus T136's registered shared-guide entrance after its
// publisher. Formatting changes do not change this initialization contract.
const COMPONENTS=[
 ['registerNaturalBreak','natural-break'],
 ['registerExtensionFurnitureComponents','extension-furniture'],
 ['registerFurnitureComponents','furniture'],
 ['registerDecorationComponents','decorations'],
 ['registerWritingBoardComponents','writing-boards'],
 ['registerMachineComponents','machines'],
 ['registerMixologyComponents','mixology'],
 ['registerCultivation','cultivation'],
 ['registerBottleComponents','bottles'],
 ['registerTapSourceComponents','tap-sources'],
 ['registerVanillaBottleDisplayComponents','vanilla-bottle-displays'],
 ['registerHolderComponents','holder'],
 ['registerTiltedRackComponents','tilted-rack'],
 ['registerCircularRackComponents','circular-rack'],
 ['registerBarCabinetComponents','bar-cabinet'],
 ['registerCellarCabinetComponents','cellar-cabinet'],
 ['registerDrinkEffects','drink-effects'],
];
const INSTALLERS=[
 ['installInstantEffects','instant-effects'],
 ['installPickupOverflowEvents','pickup-overflow'],
 ['installFurnitureEvents','furniture'],
 ['installDecorationEvents','decorations'],
 ['installWritingBoardEvents','writing-boards'],
 ['installCustomEffects','custom-effects'],
 ['installMixologyEvents','mixology'],
 ['installEffectBar','effect-bar'],
 ['installEffectIcons','effect-icons'],
 ['installMachineEvents','machines'],
 ['installCultivation','cultivation'],
 ['installStorageProjectileEvents','storage-projectile'],
 ['installMolotovEvents','molotov'],
 ['installTapSourceEvents','tap-sources'],
 ['installHolderEvents','holder'],
 ['installTiltedRackEvents','tilted-rack'],
 ['installCircularRackEvents','circular-rack'],
 ['installBarCabinetEvents','bar-cabinet'],
 ['installCellarCabinetEvents','cellar-cabinet'],
 ['installBottleEvents','bottles'],
 ['installVanillaBottleDisplayEvents','vanilla-bottle-displays'],
 ['installDisplayProjectileEvents','display-projectiles'],
 ['installQualityTooltipEvents','quality-tooltip'],
 ['installCreativePickEvents','creative-pick'],
 ['installJavaItemUseOnEvents','java-placement-router'],
];
const importedCall=([name,module])=>`call:./bedrock/${module}.js:${name}`;
export const runtimeEntrypointSource=()=>readFileSync(new URL('../runtime/BP/scripts/main.js',import.meta.url),'utf8');

export function checkRuntimeEntrypoint(source=runtimeEntrypointSource()){
 const trace=[],startup=[],deferred=[],context={};let phase='load';
 const record=(kind,name,args=[])=>trace.push({phase,key:`${kind}:${name}`,args});
 const subscribe=name=>({subscribe:(...args)=>{
  assert.equal(typeof args[0],'function',`${name} needs a callback`);
  record('subscribe',name,args);if(name==='startup')startup.push(args[0]);
 }});
 const body=source.replace(/^import\s*\{([^}]+)\}\s*from\s*['"]([^'"]+)['"];\s*$/gm,(_,bindings,module)=>{
  for(const binding of bindings.split(',')){
   const [exported,local=exported]=binding.trim().split(/\s+as\s+/);
   assert(exported&&!(local in context),`Ambiguous imported binding: ${local}`);
   context[local]=(...args)=>{
    record('call',`${module}:${exported}`,args);
   };
  }
  return '';
 }).replace(/^export\s+(?=function\s)/gm,'');
 assert(!/^import\s/m.test(body),'Entrypoint import form needs an explicit fixture update');
 context.system={
  beforeEvents:{startup:subscribe('startup')},
  afterEvents:{scriptEventReceive:subscribe('scriptEventReceive')},
  runJob:(...args)=>{assert.equal(typeof args[0]?.next,'function');record('defer','bootstrap',args);deferred.push(args[0]);},
 };
 context.world={afterEvents:{playerLeave:subscribe('playerLeave')}};
 vm.runInNewContext(body,context,{filename:'runtime/BP/scripts/main.js',timeout:1000});
 const load=trace.slice();
 assert.deepEqual(load.map(row=>row.key),[
  'call:./bedrock/native-storage-pinning.js:installNativeStoragePinning',
  'call:./core/cookery-guide-entry.js:installCookeryGuideEntry',
  'subscribe:playerLeave','subscribe:startup',
  ...INSTALLERS.map(importedCall),
  'subscribe:scriptEventReceive','defer:bootstrap',
 ],'Entrypoint load order or installation count changed');
 for(const row of load.filter(row=>INSTALLERS.some(spec=>importedCall(spec)===row.key)))
  assert.equal(row.args.length,0,`${row.key} must install without a startup event`);
 const [pinning,guideEntry]=load;
 assert.equal(pinning.args.length,1);assert.equal(typeof pinning.args[0],'function');
 assert.equal(pinning.args[0](),undefined,'Storage pinning keeps the deferred registry getter');
 assert.equal(guideEntry.args.length,1);
 assert.equal(guideEntry.args[0].system,context.system);
 assert.equal(guideEntry.args[0].world,context.world);
 for(const key of ['available','show','warn'])assert.equal(typeof guideEntry.args[0][key],'function');
 const scriptEvent=load.find(row=>row.key==='subscribe:scriptEventReceive');
 assert.deepEqual(JSON.parse(JSON.stringify(scriptEvent.args[1])),{namespaces:['kaleidoscope_cookery']});
 assert.equal(startup.length,1);assert.equal(deferred.length,1);
 const startupEvent={itemComponentRegistry:{registerCustomComponent:(...args)=>record('component','legacy_guide',args)}};
 phase='startup';startup[0](startupEvent);
 const registrations=trace.slice(load.length);
 assert.deepEqual(registrations.map(row=>row.key),[...COMPONENTS.map(importedCall),'component:legacy_guide'],
  'Entrypoint component order or registration count changed');
 for(const row of registrations.slice(0,-1)){
  assert.equal(row.args.length,1);assert.equal(row.args[0],startupEvent,`${row.key} needs the original startup event`);
 }
 const guide=registrations.at(-1);
 assert.equal(guide.args[0],'kaleidoscope_tavern:legacy_guide');
 assert.equal(typeof guide.args[1]?.onUse,'function');
 return {
  scope:'production entrypoint body; imported interfaces isolated; no BDS/client proof',
  installers:INSTALLERS.map(([name])=>name),
  registrations:COMPONENTS.map(([name])=>name),
  legacyGuideRegisteredLast:true,
  deferredBootstrapJobs:deferred.length,
 };
}

/** Execute the real main.js bootstrap generator with isolated imported interfaces. */
export function checkCookeryBootstrap(source=runtimeEntrypointSource()){
 const jobs=[],trace=[],context={};let ready=false,publisherInstalled=false;
 const noop=(name,module)=>(...args)=>{trace.push(`${module}:${name}`);};
 const Registry=class{
  constructor(options){assert.equal(options.deferInitialRebuild,true);this.options=options;this.ready=false;}
  *prepareRebuild(){trace.push('registry:prepare-start');yield;trace.push('registry:prepare-middle');yield;this.ready=true;ready=true;this.recipeCache=[];this.pageCache=[];this.revision=1;trace.push('registry:prepare-done');}
  subscribe(){trace.push('registry:subscribe');}
  list(){return [];}
  allRecipes(){return this.ready?[]:undefined;}
  pendingBarrelRecipeSources(){return [];}
 };
 const overrides={
  system:{beforeEvents:{startup:{subscribe(){}}},afterEvents:{scriptEventReceive:{subscribe(){}}},runJob(job){assert.equal(typeof job.next,'function');jobs.push(job);},sendScriptEvent(id){trace.push(`send:${id}`);}},
  world:{afterEvents:{playerLeave:{subscribe(){}}}},
  ItemTypes:{get:()=>true},ItemStack:class{getTags(){return []; }},ScriptEventSource:{Server:'Server'},
  ExtensionRegistry:Registry,BUILTIN_RECIPES:[],SHAKER_RECIPES:[],GUIDE_PAGES:[],EFFECT_PAGES:[],MIXOLOGY_PAGES:[],FLUIDS:[],
  installedBarrelRecipeSources:()=>[],cacheNativeItemDefinitionExists:()=>()=>true,cacheItemDefinitionTags:()=>()=>[],
  installCookeryGuidePublisher(_system,provider){assert(ready,'publisher must only install after registry readiness');assert(provider().ready,'publisher provider must see the complete registry');publisherInstalled=true;return {getStatus:()=>({deliveryState:'waiting_to_send'}),refresh(){trace.push('publisher:refresh');}};},
  prepareCookeryGuidePayload:registry=>registry,
  setRegistry:()=>{trace.push('machines:registry-bound');},setMixologyRegistry:()=>{trace.push('mixology:registry-bound');},
  installExtensionFurniture:()=>({}),installFoundationBridge:()=>{},installExtensionHost:()=>{},
  diagnostics:{errors:[]},console:{warn(){},error(){}},
 };
 const body=source.replace(/^import\s*\{([^}]+)\}\s*from\s*['"]([^'"]+)['"];\s*$/gm,(_,bindings,module)=>{
  for(const binding of bindings.split(',')){
   const [exported,local=exported]=binding.trim().split(/\s+as\s+/);assert(exported&&!(local in context),`Ambiguous imported binding: ${local}`);
   context[local]=Object.hasOwn(overrides,exported)?overrides[exported]:noop(exported,module);
  }
  return '';
 }).replace(/^export\s+(?=function\s)/gm,'');
 assert(!/^import\s/m.test(body),'Entrypoint import form needs an explicit fixture update');
 context.console=overrides.console;
 context.diagnosticSnapshot=undefined;vm.runInNewContext(body,context,{filename:'runtime/BP/scripts/main.js',timeout:1000});
 assert.equal(jobs.length,1);assert.equal(context.runtimeRegistry(),undefined,'registry is private until runJob completes');
 assert.equal(context.diagnosticSnapshot().cookeryInitialization.state,'pending');
 const first=jobs[0].next();assert.equal(first.done,false);assert.equal(context.runtimeRegistry(),undefined,'registry remains private during prepareRebuild');
 assert.equal(publisherInstalled,false);
 assert.equal(context.diagnosticSnapshot().cookeryInitialization.state,'preparing_registry');
 const second=jobs[0].next();assert.equal(second.done,false);assert.equal(context.runtimeRegistry(),undefined,'registry remains private for every preparation yield');
 assert.equal(publisherInstalled,false);
 const last=jobs[0].next();assert.equal(last.done,true);
 const registry=context.runtimeRegistry();assert(registry?.ready);assert(publisherInstalled,'publisher installs after the complete registry is published');
 const snapshot=context.diagnosticSnapshot();assert.equal(snapshot.cookeryInitialization.state,'ready');assert.equal(snapshot.cookeryGuideChapter.deliveryState,'waiting_to_send');
 const readyAt=trace.indexOf('registry:prepare-done');
 for(const event of ['machines:registry-bound','mixology:registry-bound','publisher:refresh'])assert(trace.indexOf(event)>readyAt,`${event} must wait for completed registry`);
 return {scope:'real main.js bootstrap generator with isolated imported interfaces; no BDS/client proof',registryPrivateUntilReady:true,publisherAfterReady:true,jobYields:2,phase:trace};
}

if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)
 console.log(JSON.stringify(checkRuntimeEntrypoint()));
