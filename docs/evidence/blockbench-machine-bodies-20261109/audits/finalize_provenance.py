from pathlib import Path
import json, hashlib, subprocess, io, re
from PIL import Image
from portable_context import context, git
H, OUT, M = context()
R=H/'snapshot';MAIN=M['main'];sha=lambda b:hashlib.sha256(b).hexdigest()
def extra(rel):
 p=R/rel
 if not p.is_file():raise ValueError('Missing declared original input: '+rel)
 M['inputs'][str(p.relative_to(H))]={'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size,'owner':'canonical '+MAIN,'original_path':rel};return p
for rel in ['art/source-jar.lock.json','runtime/BP/scripts/core/furniture.js','runtime/BP/scripts/core/decorations.js','runtime/RP/models/entity/item_display_tilted_rack.geo.json','runtime/RP/textures/kaleidoscope_tavern/block/mixology/shaker.png']:extra(rel)
# The existing held observations are reused only for these identical captured inputs.
old='e58b5a421d101f83418b82a960faa1b94d0c2a73';reuse=[]
for rel in ['runtime/RP/models/entity/runtime_shaker_held.geo.json','runtime/RP/animations/runtime_shaker.animation.json','runtime/RP/attachables/shaker.attachable.json','runtime/RP/textures/kaleidoscope_tavern/block/mixology/shaker.png']:
 a=git('show',old+':'+rel);b=extra(rel).read_bytes();reuse.append({'file':rel,'prior_commit':old,'prior_sha256':sha(a),'current_sha256':sha(b),'exact_bytes_equal':a==b})
assert all(r['exact_bytes_equal']for r in reuse)
rack=json.loads((R/'docs/evidence/t175-rack-lift/native-review.json').read_text());rp=extra(rack['runtime_file']);rack_reuse={'file':rack['runtime_file'],'recorded_sha256':rack['runtime_sha256'],'current_sha256':sha(rp.read_bytes()),'exact_bytes_equal':rack['runtime_sha256']==sha(rp.read_bytes()),'selected_y_lift':rack['selected_y_lift'],'scope':'Historical editor held-view choice only; preserved, not reaccepted by N02.'}
(OUT/'prior-evidence-reuse.json').write_text(json.dumps({'shaker_held':reuse,'tilted_rack':rack_reuse,'t174':'Read for scope only. No T174 item fixtures are duplicated by this body review. No current reuse claim is made for unexamined T174 model bytes.','allium':'Recorded first-person clipping is still unresolved. N02 makes no held/FOV claim.'},indent=2)+'\n')
# Verify locked-JAR actual blobs, not merely hashes recorded in the lock.
lock=json.loads(extra('art/source-jar.lock.json').read_text());lookup={r['path']:r for r in lock['asset_files']};jar=[]
for p in sorted((H/'inputs/forge/src/main/resources/assets/kaleidoscope_tavern').rglob('*')):
 if not p.is_file():continue
 rel='assets/kaleidoscope_tavern/'+str(p.relative_to(H/'inputs/forge/src/main/resources/assets/kaleidoscope_tavern'));entry=lookup.get(rel)
 if not entry:jar.append({'path':rel,'status':'not in locked archive list'});continue
 b=git('cat-file','blob',entry['git_blob_sha1']);assert sha(b)==entry['sha256'] and len(b)==entry['bytes'];a=p.read_bytes();row={'path':rel,'blob':entry['git_blob_sha1'],'locked_sha256':sha(b),'actual_git_object_verified':True,'Forge_sha256':sha(a),'bytes_equal':a==b}
 if p.suffix=='.json':row['json_equal']=json.loads(a)==json.loads(b)
 if p.suffix=='.png':
  x,y=Image.open(io.BytesIO(a)).convert('RGBA'),Image.open(io.BytesIO(b)).convert('RGBA');row['pixels_equal']=x.size==y.size and x.tobytes()==y.tobytes()
 jar.append(row)
(OUT/'author-archive-verification.json').write_text(json.dumps({'archive_input':lock['input'],'assets':jar},indent=2)+'\n')
# Geometry and PUT numerical declarations are unchanged across pinned Forge/NeoForge.
base='src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/'
semantic=[]
for rel,start,end in [('client/model/brew/BarrelModel.java','public static LayerDefinition createBodyLayer()', '\n    @Override'),('client/model/mixology/ShakerModel.java','public static LayerDefinition createBodyLayer()', '\n    @Override'),('client/animation/ShakerAnimation.java','public static final AnimationDefinition PUT =', ').build();')]:
 texts=[(H/'inputs'/branch/base/rel).read_text().replace('\r','').split(start,1)[1].split(end,1)[0]for branch in ['forge','neoforge']];assert texts[0]==texts[1];semantic.append({'path':base+rel,'section':start,'exact_section_equal':True,'section_sha256':sha(texts[0].encode())})
# Renderer pose calls and visibility are compared separately from loader/API changes.
for rel in ['client/render/block/BarrelBlockEntityRender.java','client/render/block/ShakerBlockEntityRender.java']:
 texts=[(H/'inputs'/branch/base/rel).read_text()for branch in ['forge','neoforge']]
 calls=[re.findall(r'poseStack\.(?:translate|mulPose)\([^;]+;',t)for t in texts];assert calls[0]==calls[1];semantic.append({'path':base+rel,'pose_calls_equal':True,'calls':calls[0]})
(OUT/'source-branch-semantics.json').write_text(json.dumps({'checks':semantic,'notes':['Relevant model JSONs and PNG pixels are equal across both pinned source branches; see manifest source_comparison.','API/render colour signatures differ. NeoForge adds a barrel render bounding box. PUT definitions and body poses are unchanged.','This does not assert identical engine culling, renderer APIs or held animation implementations.']},indent=2)+'\n')

# Resolve actual north block routes. State/runtime behavior is not executed.
def block_route(name,states):
 b=json.loads(extra('runtime/BP/blocks/'+name+'.json').read_text())['minecraft:block'];c=dict(b['components']);hit=[]
 for p in b.get('permutations',[]):
  expr=re.sub(r"q\.block_state\('([^']+)'\)",lambda m:repr(states[m[1]]),p['condition']).replace('&&',' and ').replace('||',' or ')
  assert re.fullmatch(r"[A-Za-z0-9_\s'\"=<>!().-]+",expr),expr
  if eval(expr,{'__builtins__':{}},{}):c.update(p['components']);hit.append(p['condition'])
 return {'states':states,'conditions':hit,'geometry':c['minecraft:geometry'],'transformation':c.get('minecraft:transformation',{}),'materials':c['minecraft:material_instances']}
ns='kaleidoscope_tavern:';routes=[]
for cid,block,states in [('pressing_tub-upright','pressing_tub',{'minecraft:block_face':'up','minecraft:cardinal_direction':'north'}),('pressing_tub-tilt','pressing_tub',{'minecraft:block_face':'north','minecraft:cardinal_direction':'north'}),('tap-closed','tap',{'minecraft:block_face':'north','minecraft:cardinal_direction':'north',ns+'open':0}),('tap-open','tap',{'minecraft:block_face':'north','minecraft:cardinal_direction':'north',ns+'open':1}),('stepladder-bottom','stepladder',{ns+'half':0,ns+'facing':0}),('stepladder-top','stepladder',{ns+'half':1,ns+'facing':0}),('shaker-idle','shaker_station',{ns+'facing':0,ns+'put_visual':0}),('shaker-active-hidden-block','shaker_station',{ns+'facing':0,ns+'put_visual':1})]:
 route=block_route(block,states);route['id']=cid;routes.append(route)
expected=['geometry.kt_assets_a1.pressing_tub','geometry.kt_assets_a1.pressing_tub_tilt','geometry.kt_assets_a1.tap_closed','geometry.kt_assets_a1.tap_open','geometry.kt_assets_a12.stepladder_bottom','geometry.kt_assets_a12.stepladder_top','geometry.kt_assets_a8.shaker','geometry.kt_runtime.shaker_put_hidden']
assert [r['geometry']['identifier']for r in routes]==expected
assert all(r['transformation'].get('rotation',[0,0,0])==[0,0,0]for r in routes)
for c in M['cases']:
 if c['id'].startswith('barrel'):
  c['fixture_frame']='Java north renderer reference body versus unrotated decoded native model. External entity yaw is recorded but NOT applied or claimed equivalent by this body-only scene.';c['native_shell_initial_rotation_for_north']=180;c['facing']='Java north reference; native codec-local'
 if c['id'].startswith('shaker'):
  c['fixture_frame']='Source placed body renderer transform versus native render_anchor and PUT bones. Block/entity external yaw and transitions are not executed.';c['native_helper_initial_rotation_for_facing_0']=0
M['limits'].append('Entity-helper world yaw is explicitly not simulated. Barrel north routes through facingYaw(0)=180; shaker through facing*90. Body equality is in the documented source-reference/native-codec frame, not an in-world facing acceptance.')
(OUT/'routing-validation.json').write_text(json.dumps({'block_routes':routes,'barrel':'machines.syncVisuals selects open/closed shell; core invisible; anchor x+0.5,y,z+0.5; north maps bottleFacingFromCardinal=0, facingYaw=180. External entity orientation remains an engine limit.','shaker':'Base block and helper reference the same shaker geometry/texture. put_visual=1 selects empty hidden geometry, controller runs PUT until 0.375 seconds; helper has 0.4 second lifetime and host recovery after 8 ticks.','stepladder':'Two native blocks at y and y+1; assembled entity is not spawned by current decorations helper.','controller':'controller.render.kt_assets_a1.static uses geometry.default, material.default, texture.default.','run_scope':'Read/static resolution only; no runtime state transitions executed.'},indent=2)+'\n')
M['summary']={'scenes':6,'paired_cases':10,'gui_reviewed':False}
# Preserve the original final manifest; repeated in-memory additions are not saved.
print('Exact held inputs reused:',len(reuse),'rack exact:',rack_reuse['exact_bytes_equal'],'archive assets checked:',len(jar))
