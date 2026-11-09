"""Independent saved-input/fixture audit. Does not import the scene builder.
The independent N03 matrix/float/face reader is reused with actual local-bone
selection. Exact-delta checks and adversarial controls are specific to this repair.
"""
from pathlib import Path
import json, copy, hashlib, base64, io, re
import numpy as np
from PIL import Image
import audit_helpers as A

H=WORK; M=json.loads((H/'manifest.json').read_text())
R=H/'inputs/current/runtime/RP'; BP=H/'inputs/current/runtime/BP'
sha=lambda b:hashlib.sha256(b).hexdigest()
rd=lambda p:json.loads(p.read_text())
report={'status':'passed','gui_reviewed':False,'native_execution':False,'runtime_applied':False,'hashes':0,'mesh_count':0,'directed_faces':0,'vertices':0,'max_matrix_error':0,'max_vertex_error':0,'cases':[],'negative_controls':[]}
for p,v in M['inputs'].items():
    b=(H/p).read_bytes();assert sha(b)==v['sha256'] and len(b)==v['bytes'],p;report['hashes']+=1
for p,v in M['provenance'].items():assert sha((H/p).read_bytes())==v['sha256'],p
assert sha((H/M['held_reuse_receipt']['file']).read_bytes())==M['held_reuse_receipt']['sha256']
for p,h in M['helper_provenance'].items():assert sha((H/p).read_bytes())==h,p
before=rd(H/'inputs/current'/M['candidate']['runtime_target']);after=rd(H/M['candidate']['file'])
assert sha((H/M['candidate']['file']).read_bytes())==M['candidate']['after_sha256']
assert sha((H/'inputs/current'/M['candidate']['runtime_target']).read_bytes())==M['candidate']['before_sha256']
def exact_delta(a,b):
    expected=copy.deepcopy(a);count=0
    for bone in expected['minecraft:geometry'][0]['bones']:
        for c in bone.get('cubes',[]):
            assert c['origin']==[-2,-2,-.125] and c['size']==[4,4,.25]
            c['origin']=[-4,-4,-.25];c['size']=[8,8,.5];count+=1
    assert count==8 and expected==b,'Candidate changes must be only eight centered origins and sizes'
exact_delta(before,after)
assert [str(p.relative_to(H/'candidate')) for p in (H/'candidate').rglob('*') if p.is_file()]==[M['candidate']['runtime_target']]
report['exact_candidate_delta']={'files':1,'cubes':8,'changed_vectors':16,'changed_scalars':48,'center_before_after':[0,0,0],'all_other_fields_equal':True,'after_sha256':M['candidate']['after_sha256']}
def reject(label,fn):
    try:fn()
    except (AssertionError,KeyError,ValueError):report['negative_controls'].append({'tamper':label,'rejected':True});return
    raise AssertionError('Negative control accepted: '+label)
for label,field,axis,delta in [('candidate width','size',0,.25),('candidate center','origin',1,.25)]:
    bad=copy.deepcopy(after);bad['minecraft:geometry'][0]['bones'][5]['cubes'][0][field][axis]+=delta
    reject(label,lambda bad=bad:exact_delta(before,bad))
bad=copy.deepcopy(after);bad['minecraft:geometry'][0]['bones'][5]['cubes'][0]['uv']['north']['uv'][0]=1
reject('candidate UV',lambda:exact_delta(before,bad))
bad=copy.deepcopy(after);bad['minecraft:geometry'][0]['bones'][1]['pivot'][1]=1
reject('candidate tilt pivot',lambda:exact_delta(before,bad))

# Portable complete bounded census; no live checkout or Git subprocess.
from census import verify_census
consumers = verify_census(PACKAGE)
expected=[f'runtime/RP/entity/runtime_pressing_tub_ingredients{("_"+str(i)) if i else ""}.entity.json' for i in range(8)]
assert sorted(consumers)==sorted(expected)
routes=[];shared_textures=None
for i,p in enumerate(expected):
    e=rd(H/'inputs/current'/p)['minecraft:client_entity']['description']
    ident='kaleidoscope_tavern:pressing_tub_ingredients'+(f'_{i}' if i else '')+'_visual'
    bp=rd(BP/'entities'/(ident.split(':')[1]+'.json'))['minecraft:entity']
    assert e['identifier']==bp['description']['identifier']==ident
    assert e['geometry']=={'card':'geometry.kt_runtime.pressing_card','cube':'geometry.kt_runtime.pressing_cube'}
    assert e['animations']=={'layout':'animation.kt_runtime.pressing.layout'} and e['scripts']=={'animate':['layout']}
    assert e['render_controllers']==['controller.render.kt_runtime.pressing_ingredients']
    shared_textures=e['textures'] if shared_textures is None else shared_textures
    assert e['textures']==shared_textures,'All eight consumers must share exact texture aliases'
    assert 'scale' not in json.dumps(bp).lower() and 'scale' not in json.dumps(e.get('scripts',{})).lower()
    routes.append({'helper':i,'global_indices':[i*8,i*8+7],'identifier':ident,'RP_input':'inputs/current/'+p,'BP_input':'inputs/current/runtime/BP/entities/'+ident.split(':')[1]+'.json','compensating_scale':False})
anim=rd(R/'animations/runtime_pressing_ingredients.animation.json')['animations']['animation.kt_runtime.pressing.layout']
assert not any('scale' in b for b in anim['bones'].values())
assert not any('scale' in b for b in before['minecraft:geometry'][0]['bones'])
controller=rd(R/'render_controllers/runtime_pressing_ingredients.render_controllers.json')['render_controllers']['controller.render.kt_runtime.pressing_ingredients']
cube_kinds=list(map(int,re.findall(r'== (\d+)',controller['geometry'])))
assert cube_kinds==[21,22,23,24,25]
foodtext=(BP/'scripts/data/pressing-ingredient-visuals.js').read_text();foods=json.loads(foodtext[foodtext.index('{'):foodtext.rindex('}')+1])
assert len(foods)==27 and set(foods.values())==set(range(1,27))
for p in ['scripts/bedrock/pressing-ingredients.js','scripts/core/ingredient-layout.js']:
    assert 'scale' not in (BP/p).read_text().lower()
spawn=(BP/'scripts/bedrock/machines.js').read_text();assert 'configurePressingIngredients(entity,core,state);' in spawn
assert 'core.dimension.spawnEntity(type,{x:core.location.x+.5,y:core.location.y,z:core.location.z+.5},{initialRotation:yaw})' in spawn
assert 'const yaw=shell?facingYaw(bottleFacingFromCardinal(barrelCardinal(core))):0;' in spawn
assert controller['textures']==["q.property('kaleidoscope_tavern:grape_kind') == 2 ? Array.ice_grape_ticks[math.mod(math.floor(q.time_stamp), 24)] : Array.kind[q.property('kaleidoscope_tavern:grape_kind')-1]"]
assert controller['part_visibility']==[{f'ingredient_{i}':f"q.property('kaleidoscope_tavern:fill_stage') > {i}"} for i in range(8)]
report['routes']={'helpers':routes,'food_routes':[{'id':k,'kind':v,'texture':shared_textures[f'kind_{v}'],'owner':'cube unchanged' if v in cube_kinds else 'card corrected'} for k,v in foods.items()],'affected_card_ids':sum(v not in cube_kinds for v in foods.values()),'unique_card_kinds':21,'cube_kinds_unchanged':cube_kinds,'animated_tick_route_unchanged':True,'helper_spawn_scale':1,'unknown_external_items_not_accepted':True}

# Independent maintained-source transform proof and accepted held-control identities.
J='src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/client/render/block/PressingTubBlockEntityRender.java'
texts=[(H/'inputs'/branch/J).read_text() for branch in ('forge','neoforge')]
calls=lambda t:re.findall(r'poseStack\.(?:translate|mulPose|scale)\([^;]+;',t)
assert calls(texts[0])==calls(texts[1])
assert 'poseStack.scale(0.5f, 0.5f, 0.5f);' in texts[0] and 'ItemDisplayContext.FIXED' in texts[0]
for v in ('1.20.1','1.21.1'):
    fixed=rd(H/f'inputs/mojang-{v}/assets/minecraft/models/item/generated.json')['display']['fixed']
    assert fixed['rotation']==[0,180,0] and fixed.get('translation',[0,0,0])==[0,0,0] and fixed['scale']==[1,1,1]
report['source_scale_proof']={'branches':[M['forge'],M['neoforge']],'renderer_scale':.5,'generated_fixed_scale':1,'generated_fixed_yaw':180,'generated_full_dimensions':[16,16,1],'effective_dimensions':[8,8,.5],'extrusion_algorithm_scope':'Official 1.20.1 bytecode only; 1.21.1 FIXED parent and renderer independently checked.'}
reuse=rd(H/M['held_reuse_receipt']['file']);held=[]
for row in reuse['shaker_held']+[reuse['tilted_rack']]:
    got=sha((H/'inputs/current'/row['file']).read_bytes());assert got==row['current_sha256'];held.append({'file':row['file'],'sha256':got})
report['held_controls']={'inputs':held,'tilted_rack_first_person_y_lift':6,'changed':False,'new_held_acceptance':False}

def source_matrix(a,off):
    x,y,z,yr,zr=A.source_values(a);cube=a['item'] in ['ice','stone']
    fixed=rd(A.V/('models/block/block.json' if cube else 'models/item/generated.json'))['display']['fixed']
    outer=np.eye(4);facing=a['tilt_facing']
    if facing is not None:
        odd=facing%2;outer=A.rot('y',-(180-[2,3,0,1][facing]*90))@A.trans([-8,0,-8])@A.rot('x',45 if odd else -45)@A.trans([0,8 if odd else -4,-8 if odd else 4])@A.trans([8,0,8])
    return A.trans(off)@outer@A.trans([x,y,z])@A.scl(.5)@A.rot('x',-90)@A.rot('y',-yr)@A.rot('z',-zr)@A.rot('y',fixed['rotation'][1])@A.scl(fixed['scale'][0])@A.trans([-8,-8,-8])
def native_quads(a):
    geo=rd(H/a['geometry_input'])['minecraft:geometry'][0]
    b=next(b for b in geo['bones'] if b.get('cubes') and (a['machine']=='barrel' or b['name']==f'item_z_{a["index"]%8}'))
    c=b['cubes'][0];o,s=c['origin'],c['size'];fr=[-o[0]-s[0],o[1],o[2]];to=[-o[0],o[1]+s[1],o[2]+s[2]];out=[]
    for side,v in c['uv'].items():
        u,w=v['uv'];du,dv=v['uv_size'];uv=[u,w,u+du,w+dv];uv=[u+du,w+dv,u,w] if side in ['up','down'] else uv;out.append(A.face(fr,to,side,uv))
    return out
def expected_texture(a):
    source=a['variant']=='source';kind=a['item']
    if kind=='stone':return (A.V/'textures/block/stone.png').read_bytes()
    if kind=='ice_grape':return (H/'derived/source-ice-grape-tick1.png' if source else R/'textures/kt_runtime/machine_ingredients/ice_grape/tick_01.png').read_bytes()
    return (A.S/'textures/item/grape.png' if source else R/'textures/kaleidoscope_tavern/item/grape.png').read_bytes()
def check_mesh(e,doc):
    a=e['_review'];off=[{'source':-24,'before':0,'after':24}[a['variant']],0,44 if a['item']=='stone' else 0]
    matrix=source_matrix(a,off) if a['variant']=='source' else A.trans(off)@A.native_matrix(a)
    q=A.source_quads(a['item']) if a['variant']=='source' else native_quads(a)
    em=A.close(a['matrix'],matrix,'matrix');assert len(q)==len(e['faces'])
    assert e['origin']==[0,0,0] and e['rotation']==[0,0,0] and e['visibility']
    maxv=0
    for n,(ps,uv) in enumerate(q):
        face=e['faces']['f'+str(n)];keys=face['vertices'];actual=[e['vertices'][k] for k in keys];expected=A.apply(matrix,ps)
        maxv=max(maxv,A.close(actual,expected,'saved directed vertices'))
        tex=doc['textures'][face['texture']];b=base64.b64decode(tex['source'].split(',',1)[1]);assert b==expected_texture(a)
        im=Image.open(io.BytesIO(b));assert (tex['width'],tex['height'])==im.size
        assert tex['render_sides']=='front' and tex['uv_width']==tex['uv_height']==128
        A.close([face['uv'][k] for k in keys],[[u*128/im.width,v*128/im.height] for u,v in uv],'UV')
    return matrix,q,em,maxv

first=None
expected_plan={'01-upright-isolated':('grape',64,[0],None),'02-upright-helper-boundaries':('grape',64,[0,7,8,63],None),'03-north-tilt-layers':('grape',64,[0,63],0),'04-east-tilt-layers':('grape',64,[0,63],1),'05-animated-ice-grape-tick1':('ice_grape',1,[0],None)}
assert {Path(r['file']).stem for r in M['scenes']}==set(expected_plan)|{'06-unchanged-controls'}
for rec in M['scenes']:
    doc=rd(H/rec['file']);assert sha((H/rec['file']).read_bytes())==rec['sha256']
    assert doc['resolution']=={'width':128,'height':128}
    for g in doc['groups']:assert g['origin']==g['rotation']==[0,0,0] and g['visibility']
    expected_ids={e['uuid'] for e in doc['elements']};seen=[]
    for n in doc['outliner']:seen+=n['children']
    assert set(seen)==expected_ids and len(seen)==len(expected_ids),'Every mesh has one identity parent'
    actual=[(e['_review']['machine'],e['_review']['item'],e['_review']['count'],e['_review']['index'],e['_review']['tilt_facing'],e['_review']['variant']) for e in doc['elements']]
    stem=Path(rec['file']).stem
    if stem in expected_plan:
        kind,count,indices,tilt=expected_plan[stem];expected=[('pressing_tub',kind,count,i,tilt,v) for i in indices for v in ['source','before','after']]
    else:expected=[(m,k,1,0,None,v) for m,k in [('barrel','grape'),('pressing_tub','stone')] for v in ['source','before','after']]
    assert actual==expected,'Exact finite capture plan and roles'
    grouped={}
    for e in doc['elements']:
        assert e['type']=='mesh';a=e['_review'];matrix,q,em,ev=check_mesh(e,doc)
        report['max_matrix_error']=max(report['max_matrix_error'],em);report['max_vertex_error']=max(report['max_vertex_error'],ev)
        report['mesh_count']+=1;report['directed_faces']+=len(q);report['vertices']+=sum(len(f['vertices']) for f in e['faces'].values())
        first=first or (e,doc)
        f=e['faces']['f0'];v=np.array([e['vertices'][k] for k in f['vertices']]);edges=np.linalg.norm(np.roll(v,-1,axis=0)-v,axis=1)
        width=4 if a['item']=='stone' or (a['variant']=='before' and a['machine']=='pressing_tub') else 8
        A.close(edges,[width]*4,'basis-invariant face edges')
        key=(a['machine'],a['item'],a['index']);grouped.setdefault(key,{})[a['variant']]=(e,matrix)
        report['cases'].append({'scene':rec['file'],'variant':a['variant'],'machine':a['machine'],'item':a['item'],'global':a['index'],'helper':a['index']//8,'local':a['index']%8,'tilt':a['tilt_facing'],'directed_quads':len(q),'face_edges':edges.tolist(),'AABB_min':np.min(np.array(list(e['vertices'].values())),axis=0).tolist(),'AABB_max':np.max(np.array(list(e['vertices'].values())),axis=0).tolist()})
    for key,sides in grouped.items():
        eb,mb=sides['before'];ea,ma=sides['after'];shift=np.array([24,0,0]);A.close(ma,A.trans(shift)@mb,'unchanged native transform')
        center=mb[:3,3];factor=2 if key[0]=='pressing_tub' and key[1]!='stone' else 1
        for k in eb['vertices']:A.close(np.array(ea['vertices'][k])-shift,center+factor*(np.array(eb['vertices'][k])-center),'exact center-preserving native delta')
        assert eb['faces']==ea['faces'] or all(eb['faces'][f]['uv']==ea['faces'][f]['uv'] for f in eb['faces'])

e,doc=first
for label,mutate in [('saved size',lambda x:x['vertices']['v0_0'].__setitem__(0,x['vertices']['v0_0'][0]+.125)),('saved center',lambda x:[p.__setitem__(1,p[1]+.25) for p in x['vertices'].values()]),('saved UV',lambda x:x['faces']['f0']['uv']['v0_0'].__setitem__(0,1)),('saved matrix',lambda x:x['_review']['matrix'][0].__setitem__(3,x['_review']['matrix'][0][3]+1))]:
    bad=copy.deepcopy(e);mutate(bad);reject(label,lambda bad=bad:check_mesh(bad,doc))

# Evaluate all 64 selected-card routes and all upright/cardinal tilt poses, while
# checking zero center displacement and doubled intrinsic world dimensions.
dimensions=[];minimum=np.array([np.inf]*3);maximum=-minimum;before_min=minimum.copy();before_max=maximum.copy()
for facing in [None,0,1,2,3]:
    for index in range(64):
        a={'machine':'pressing_tub','index':index,'slot':0,'count':64,'location':{'x':3,'y':64,'z':-5},'tilt_facing':facing,'geometry_input':M['candidate']['file']}
        mat=A.native_matrix(a);qb=native_quads(a);verts=A.apply(mat,[p for ps,uv in qb for p in ps]);A.close(mat[:3,:3].T@mat[:3,:3],np.eye(3),'pure rigid pose')
        A.close(np.mean(verts,axis=0),mat[:3,3],'zero local center preserved')
        minimum=np.minimum(minimum,np.min(verts,axis=0));maximum=np.maximum(maximum,np.max(verts,axis=0))
        old={**a,'geometry_input':'inputs/current/'+M['candidate']['runtime_target']};oldmat=A.native_matrix(old);oldverts=A.apply(oldmat,[p for ps,uv in native_quads(old) for p in ps]);A.close(oldmat,mat,'unchanged pose all routes')
        before_min=np.minimum(before_min,np.min(oldverts,axis=0));before_max=np.maximum(before_max,np.max(oldverts,axis=0))
        fv=A.apply(mat,qb[0][0]);A.close(np.linalg.norm(np.roll(fv,-1,axis=0)-fv,axis=1),[8]*4,'eight-wide all consumers')
        dimensions.append({'global':index,'tilt_facing':facing,'helper':index//8,'local':index%8,'native_properties':A.properties(a)[0],'decoded_pose_matrix':mat.tolist(),'before_AABB_min':np.min(oldverts,axis=0).tolist(),'before_AABB_max':np.max(oldverts,axis=0).tolist(),'after_AABB_min':np.min(verts,axis=0).tolist(),'after_AABB_max':np.max(verts,axis=0).tolist()})
desc=after['minecraft:geometry'][0]['description'];bbox_min=np.array([-desc['visible_bounds_width']*8,desc['visible_bounds_offset'][1]*16-desc['visible_bounds_height']*8,-desc['visible_bounds_width']*8]);bbox_max=np.array([desc['visible_bounds_width']*8,desc['visible_bounds_offset'][1]*16+desc['visible_bounds_height']*8,desc['visible_bounds_width']*8])
inside=bool(np.all(minimum>=bbox_min) and np.all(maximum<=bbox_max))
report['all_card_pose_dimensions']={'poses_checked':len(dimensions),'effective_card_dimensions':[8,8,.5],'union_decoded_AABB_min':minimum.tolist(),'union_decoded_AABB_max':maximum.tolist(),'before_union_decoded_AABB_min':before_min.tolist(),'before_union_decoded_AABB_max':before_max.tolist(),'declared_visible_bounds_min':bbox_min.tolist(),'declared_visible_bounds_max':bbox_max.tolist(),'selected_seed_all_poses_inside_declared_bounds':inside,'before_all_poses_inside_declared_bounds':bool(np.all(before_min>=bbox_min) and np.all(before_max<=bbox_max)),'not_engine_culling_acceptance':True,'scope':'Decoded reference-frame advisory only. Bounds are unchanged; outside cases require engine-frame/culling verification, not guessed metadata fixes.'}
report['all_card_pose_dimensions'].update({'raw_description':{k:desc[k] for k in ['visible_bounds_width','visible_bounds_height','visible_bounds_offset']},'declared_bounds_units':'blocks; converted at 16 model pixels per block','vertex_units':'model pixels in BB-decoded animated model-reference frame; no scene offset','location_block_coordinates':{'x':3,'y':64,'z':-5},'count':64,'indices':'every integer 0..63','tilt_facing_states':[None,0,1,2,3],'facing_mapping':{'0':'north','1':'east','2':'south','3':'west'},'unposed_local_card_before':{'min':[-2,-2,-.125],'max':[2,2,.125]},'unposed_local_card_after':{'min':[-4,-4,-.25],'max':[4,4,.25]},'full_pose_receipt':'pose-bounds-audit.json'})
(H/'pose-bounds-audit.json').write_text(json.dumps({'sample_scope':report['all_card_pose_dimensions'],'poses':dimensions},indent=2)+'\n')

source=np.array(Image.open(A.S/'textures/item/ice_grape.png').convert('RGBA'),dtype=np.uint16)
for tick in range(24):
    i=tick//2;a=source[i*16:i*16+16].copy();b=source[((i+1)%12)*16:((i+1)%12)*16+16];a[:,:,:3]=(a[:,:,:3]*(2-tick%2)+b[:,:,:3]*(tick%2))//2
    im=np.array(Image.open(R/f'textures/kt_runtime/machine_ingredients/ice_grape/tick_{tick:02d}.png').convert('RGBA'));assert np.array_equal(a,im)
assert np.array_equal(np.array(Image.open(H/'derived/source-ice-grape-tick1.png')),np.array(Image.open(R/'textures/kt_runtime/machine_ingredients/ice_grape/tick_01.png')))
assert np.array_equal(np.array(Image.open(A.S/'textures/item/grape.png')),np.array(Image.open(R/'textures/kaleidoscope_tavern/item/grape.png')))
report['texture_check']={'ice_ticks':24,'mismatches':0,'embedded_original_bytes':True,'front_hint_only':True,'native_clock_executed':False,'source_alpha_edge_quads':{'grape':len(A.source_quads('grape')),'ice_grape_union':len(A.source_quads('ice_grape'))},'native_card_faces':2}
report['scope_limits']=['No source/current coordinate-sign or placement alignment changes.','Source generated alpha-edge extrusion remains distinct from the native two-face approximation.','Ordinary ice material remains unproven and out of scope.','All registered card consumers share this owner; no new individual/addon texture or source-model acceptance.','No Minecraft, BDS, LIVE, GUI, runtime integration, versioning or publication.']
(H/'independent-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['status','hashes','mesh_count','directed_faces','vertices','max_matrix_error','max_vertex_error','all_card_pose_dimensions','negative_controls']},indent=2))
