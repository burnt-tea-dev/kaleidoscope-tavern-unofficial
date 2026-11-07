/** QA copy only. Import after the normal Tavern entrypoint; never install on LIVE.
 * Setup may seed a board. After READY, only normal block-use/form submission
 * may change it. The network driver owns the real form request/response log.
 */
import {world,system,BlockPermutation,BlockVolume} from '@minecraft/server';
import {BOARD_HALF,CHALK_POSITION,CHALKBOARD,boardRuntimeKey,normalizeBoardData} from './core/boards.js';
import {WRITING_BOARD_DIAGNOSTICS} from './bedrock/writing-boards.js';

const NAME='qaNetPlain',PREPARE='kt_qa:board_prepare',POS={x:96,y:300,z:4},FROM={x:96.5,y:300,z:1.5};
const seed={text:'seed\nliteral \\n\nC:\\new\\log',color:'blue',glowing:false,waxed:false,alignment:'center',verticalAlignment:'middle'};
const submitted='edit\nliteral \\n\nC:\\new\\log';
const expected={...seed,text:submitted,alignment:'distributed',verticalAlignment:'bottom'};
const state={started:false,ready:false,finished:false,clicks:[],issues:[]};
const out=(stage,data={})=>console.warn('TAVERN_QA_BOARD_'+stage+' '+JSON.stringify({tick:system.currentTick,...data}));
const require=(value,message)=>{if(!value)throw Error(message);};
function blocks(){return [POS,{...POS,y:POS.y+1}].map(p=>{
 const b=state.dimension.getBlock(p);
 return {typeId:b.typeId,states:b.permutation.getAllStates()};
});}
function finish(status,extra={}){
 if(state.finished)return;state.finished=true;
 out('RESULT',{status,issues:state.issues,clicks:state.clicks,...extra,
  scope:'Real block-use + wire form + owner save only; driver request/response evidence required. No physical Enter, rendered UI, touch/gamepad or restart claim.'});
}
function setup(player){
 const d=state.dimension;
 d.fillBlocks(new BlockVolume({x:94,y:299,z:0},{x:98,y:302,z:6}),'minecraft:air');
 d.fillBlocks(new BlockVolume({x:94,y:299,z:0},{x:98,y:299,z:6}),'minecraft:stone');
 for(let half=0;half<2;half++)d.getBlock({...POS,y:POS.y+half}).setPermutation(BlockPermutation.resolve(CHALKBOARD,{
  [BOARD_HALF]:half,[CHALK_POSITION]:0,'minecraft:cardinal_direction':'north','kaleidoscope_tavern:waterlogged':false,
 }));
 d.fillBlocks(new BlockVolume({...POS,z:5},{...POS,y:301,z:5}),'minecraft:stone');
 state.key=boardRuntimeKey(d.id,POS);
 // This is the only save-key write. The seed uses the owner's unchanged schema.
 state.seedRaw=JSON.stringify(normalizeBoardData(seed,350));
 world.setDynamicProperty(state.key,state.seedRaw);
 state.blocks=blocks();state.edited=WRITING_BOARD_DIAGNOSTICS.edited;state.deadline=system.currentTick+1200;
 require(!player.getComponent('minecraft:inventory').container.getItem(player.selectedSlotIndex),'QA hand must be empty');
 const target={x:96.5,y:300.65,z:4.95};
 player.teleport(FROM,{dimension:d,facingLocation:target});
 state.ready=true;
 out('READY',{name:NAME,dimension:d.id,position:FROM,targetBlock:POS,face:'North',faceLocation:{x:.5,y:.65,z:.95},
  lookAt:target,rotation:player.getRotation(),blockStates:state.blocks,key:state.key,
  form:{titlePrefix:'§r§0§r',types:['input','dropdown','dropdown'],defaultText:seed.text,defaultDropdowns:[1,1],
   response:[submitted,4,2]},seed,expected,postReadyWrites:'none; normal owner submission only',deadlineTick:state.deadline});
}
world.beforeEvents.playerInteractWithBlock.subscribe(event=>{
 if(!state.ready||state.finished||event.player.id!==state.player.id)return;
 const p=event.block.location;
 if(p.x!==POS.x||p.z!==POS.z||p.y<POS.y||p.y>POS.y+1)return;
 state.clicks.push({tick:system.currentTick,block:{...p},face:event.blockFace,first:event.isFirstEvent});
});
system.afterEvents.scriptEventReceive.subscribe(event=>{
 if(event.id!==PREPARE||state.started||state.finished)return;
 // Common sends this once AFTER real driver spawn + initial_loading_end.
 // getAllPlayers alone can see an actor that is still logging in.
 const player=world.getAllPlayers().find(p=>p.name===NAME);
 if(!player){state.issues.push('Prepare arrived without the expected player; no scene prepared.');finish('inconclusive');return;}
 state.started=true;state.player=player;state.dimension=player.dimension;
 try{
  player.teleport(FROM,{dimension:state.dimension});
  out('PREPARING',{name:NAME,prepareEvent:PREPARE,wireSpawnAndLoadingEvidenceRequired:true});
  // This delay loads the relocated QA chunk, not the login handshake.
  system.runTimeout(()=>{try{setup(player);}catch(error){state.issues.push('QA setup: '+String(error));finish('inconclusive',{phase:'setup'});}},20);
 }catch(error){state.issues.push('QA relocation: '+String(error));finish('inconclusive',{phase:'setup'});}
});
system.runInterval(()=>{
 if(state.finished)return;
 try{
  if(!state.ready)return;
  const raw=world.getDynamicProperty(state.key);
  if(raw!==state.seedRaw){
   const data=JSON.parse(raw),currentBlocks=blocks(),edits=WRITING_BOARD_DIAGNOSTICS.edited-state.edited;
   require(state.clicks.length>0,'No normal target block click observed');
   require(JSON.stringify(data)===JSON.stringify(expected),'Owner save differs from the raw wire submission/metadata contract');
   require(JSON.stringify(currentBlocks)===JSON.stringify(state.blocks),'Board identity/states changed');
   require(edits===1,'Expected exactly one owner save');
   finish('owner_save_observed',{data,blocks:currentBlocks,ownerEdits:edits,wireEvidenceRequired:true});
  }else if(system.currentTick>state.deadline){
   state.issues.push('No owner save before deadline. Inspect real request/response logs; missing wire support is not a Tavern negative.');
   finish('inconclusive',{data:JSON.parse(raw)});
  }
 }catch(error){state.issues.push(String(error));finish('fail');}
},5);
system.run(()=>out('LOGIN_READY',{name:NAME,players:1,prepareEvent:PREPARE}));
