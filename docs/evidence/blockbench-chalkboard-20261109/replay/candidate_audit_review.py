"""Independent raw-input reconstruction. Does not import or run the builder.
Native vertex table is parsed as inert data from official Blockbench setShape;
source polygons independently reconstruct Minecraft ModelPart and the renderer.
"""
from pathlib import Path
import json,hashlib,copy,re,base64,io,math
import numpy as np
from PIL import Image
H=WORK;read=lambda p:json.loads(p.read_text());sha=lambda b:hashlib.sha256(b).hexdigest();M=read(H/'manifest.json')
R=H/'inputs/current';S=H/'inputs/forge';N=H/'inputs/neoforge';AS='src/main/resources/assets/kaleidoscope_tavern/';JA='src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/'
def save(name,d):(H/name).write_text(json.dumps(d,indent=2)+'\n')
report={'inputs_verified':0,'candidate_files':[],'source_branch_contracts':[],'saved_scenes':0,'saved_meshes':0,'saved_faces':0,'saved_vertices':0,'embedded_textures':0,'max_vertex_error':0.,'max_uv_error':0.,'surface_comparisons':[],'gui_reviewed':False,'engine_reviewed':False}
for rel,info in M['inputs'].items():assert sha((H/rel).read_bytes())==info['sha256'];report['inputs_verified']+=1

def delta(a,b,p=''):
 if type(a)!=type(b):return [{'path':p,'before':a,'after':b}]
 if isinstance(a,dict):
  out=[]
  for k in sorted(set(a)|set(b)):
   if k not in a:out.append({'path':p+'/'+k,'operation':'add','after':b[k]})
   elif k not in b:out.append({'path':p+'/'+k,'operation':'remove','before':a[k]})
   else:out+=delta(a[k],b[k],p+'/'+k)
  return out
 if isinstance(a,list):
  assert len(a)==len(b);return sum((delta(x,y,p+'/'+str(i)) for i,(x,y) in enumerate(zip(a,b))),[])
 return [] if a==b else [{'path':p,'before':a,'after':b}]
proposals={r['file']:r for r in read(H/'original-proposed-changes.json')['proposed_changes']}
for row in read(H/'candidate-files.json'):
 a=read(R/row['path']);b=read(H/'candidate'/row['path']);assert sha((R/row['path']).read_bytes())==row['before_sha256'];assert sha((H/'candidate'/row['path']).read_bytes())==row['after_sha256'];d=delta(a,b)
 ac=a['minecraft:geometry'][0]['bones'][0]['cubes'][0];bc=b['minecraft:geometry'][0]['bones'][0]['cubes'][0];av=ac.pop('uv');bv=bc.pop('uv');assert a==b,'Non-UV field changed'
 assert {k:v for k,v in av.items() if k not in ['east','west','down']}=={k:v for k,v in bv.items() if k not in ['east','west','down']}
 expected=copy.deepcopy(av)
 east=expected.pop('east',None);west=expected.pop('west',None)
 if east is not None:expected['west']=east
 if west is not None:expected['east']=west
 if 'down' in expected:expected['down']['uv'][1]=1;expected['down']['uv_size'][1]=-1
 assert bv==expected
 if d:assert bv==proposals['inputs/current/'+row['path']]['after_uv']
 else:assert (R/row['path']).read_bytes()==(H/'candidate'/row['path']).read_bytes()
 report['candidate_files'].append({**row,'exact_delta':d,'all_other_fields_unchanged':True,'north_south_up_unchanged':True})
assert sum(bool(x['exact_delta']) for x in report['candidate_files'])==7

# Inert source assertions document exactly which vendor rules underpin decode.
bb=(H/'inputs/reference/js__formats__bedrock__bedrock.js.txt').read_text();mp=(H/'inputs/reference/ModelPart.java.reference.txt').read_text();cub=(H/'inputs/reference/cube.js.official.txt').read_text()
for token in ['base_cube.from[0] = -(base_cube.from[0] + s.size[0])',"if (key == 'up' || key == 'down')",'face.uv = [face.uv[2], face.uv[3], face.uv[0], face.uv[1]]','face.texture = null']:
 assert token in bb
assert 'new ModelPart.Vertex[]{var9, var8, var4, var5}, var13, var18, var14, var19' in mp
assert 'new ModelPart.Vertex[]{var6, var7, var11, var10}, var14, var19, var15, var18' in mp
assert 'param0[0] = param0[0].remap(param3 / param5 - var0, param2 / param6 + var1)' in mp
assert 'Format.per_texture_uv_size' in cub
shape=(H/'inputs/reference/three-shape.official.txt').read_text();corners={}
for side,tokens in re.findall(r'// (East|West|Up|Down|South|North)\s+position.array.set\(\[([\s\S]*?)\], \d+\)',shape):
 tokens=re.findall(r'(from|to)\[(\d)\]',tokens);assert len(tokens)==12;corners[side.lower()]=[tokens[i:i+3] for i in range(0,12,3)]
assert len(corners)==6
assert 'indices.push(0 + i*4, 2 + i*4, 1 + i*4, 2 + i*4, 3 + i*4, 1 + i*4)' in (H/'inputs/reference/cube-face-indices.official.txt').read_text()

def nums(txt):return [float(x.rstrip('F')) for x in re.findall(r'-?\d+(?:\.\d+)?F?',txt)]
def source_contract(root,size):
 name=size.title()+'ChalkboardModel';text=(root/(JA+'client/model/deco/'+name+'.java')).read_text();box=nums(re.search(r'addBox\((.*?)new CubeDeformation',text).group(1));offset=nums(re.search(r'PartPose.offset\((.*?)\)',text).group(1));dims=nums(re.search(r'LayerDefinition.create\(meshdefinition, (.*?)\)',text).group(1));assert '.mirror(' not in text and 'new CubeDeformation(0.0F)' in text and 'texOffs(0, 0)' in text and 'RenderType::entityCutoutNoCull' in text
 rt=(root/(JA+'client/render/block/ChalkboardBlockEntityRender.java')).read_text();body=rt[rt.index('protected void renderModel'):rt.index('protected void renderText')]
 for t in ['poseStack.translate(0.5, 1.5, 0.5)','Axis.ZN.rotationDegrees(180)','Axis.YN.rotationDegrees(180 - facing.get2DDataValue() * 90)','RenderType.entityCutoutNoCull(LARGE_TEXTURE)','RenderType.entityCutoutNoCull(SMALL_TEXTURE)']:assert t in body
 return {'box':box,'offset':offset,'texture_dimensions':dims,'mirror':False,'deformation':0,'render_material':'entityCutoutNoCull'}
for size in ['small','large']:
 f=source_contract(S,size);n=source_contract(N,size);assert f==n
 p=AS+f'textures/entity/deco/{size}_chalkboard.png';im=Image.open(S/p).convert('RGBA');nm=Image.open(N/p).convert('RGBA');assert im.size==nm.size==tuple(f['texture_dimensions']) and im.tobytes()==nm.tobytes();report['source_branch_contracts'].append({'size':size,**f,'forge_neoforge_equal':True,'texture_pixels_equal':True})

def rotate(p,a,axis):
 p=list(p);i,j={'x':(1,2),'y':(2,0),'z':(0,1)}[axis];c=math.cos(math.radians(a));s=math.sin(math.radians(a));p[i],p[j]=p[i]*c-p[j]*s,p[i]*s+p[j]*c;return np.array(p)
def source_faces(size,facing):
 c=source_contract(S,size);x,y,z,w,h,d=c['box'];X,Y,Z=x+w,y+h,z+d;vs=[[x,y,z],[X,y,z],[X,Y,z],[x,Y,z],[x,y,Z],[X,y,Z],[X,Y,Z],[x,Y,Z]]
 # ModelPart variable names retained to keep derivation auditable.
 v12,v13,v14,v15,v16,v17,v18,v19,v20=0,d,d+w,d+2*w,2*d+w,2*d+2*w,0,d,d+h
 table={'down':([5,4,0,1],[v13,v18,v14,v19]),'up':([2,3,7,6],[v14,v19,v15,v18]),'west':([0,4,7,3],[v12,v19,v13,v20]),'north':([1,0,3,2],[v13,v19,v14,v20]),'east':([5,1,2,6],[v14,v19,v16,v20]),'south':([4,5,6,7],[v16,v19,v17,v20])};out={}
 for side,(ids,(u,v,U,V)) in table.items():
  ps=[]
  for i in ids:
   p=np.array(vs[i])+c['offset'];p=rotate(p,-(180-{'north':2,'east':3}[facing]*90),'y');p=rotate(p,-180,'z');ps.append((p+[0,24,0]).tolist())
  out[side]=(np.array(ps),np.array([[U,v],[u,v],[u,V],[U,V]]))
 return out
bp=read(R/'runtime/BP/blocks/chalkboard.json')['minecraft:block'];terrain=read(R/'runtime/RP/textures/terrain_texture.json')['texture_data']
def native_faces(el,facing):
 rr=el['_review'];g=read(H/rr['geometry_input'])['minecraft:geometry'][0];assert len(g['bones'])==1;b=g['bones'][0];assert b['pivot']==[0,0,0] and not b.get('rotation') and not b.get('mirror');assert len(b['cubes'])==1;c=b['cubes'][0];assert not c.get('mirror') and not c.get('rotation') and not c.get('inflate');o=c['origin'];s=c['size'];lo=[-o[0]-s[0],o[1],o[2]];hi=[lo[i]+s[i] for i in range(3)];out={}
 ident=g['description']['identifier'];size,col,half=re.match(r'geometry.kt_java.chalk_(small|large)_(\d)_(\d)',ident).groups();col=int(col);half=int(half);pos=0 if size=='small' else 3-col;perm=next(x for x in bp['permutations'] if x['components'].get('minecraft:geometry',{}).get('identifier')==ident);assert perm['condition']==f"q.block_state('kaleidoscope_tavern:position') == {pos} && q.block_state('kaleidoscope_tavern:half') == {half}"
 yaw=next(x['components']['minecraft:transformation']['rotation'][1] for x in bp['permutations'] if x['condition']==f"q.block_state('minecraft:cardinal_direction') == '{facing}'");assert yaw=={'north':0,'east':270}[facing]
 offset=np.array([0,half*16,0])+np.array({'north':[1,0,0],'east':[0,0,1]}[facing])*((pos-2)*16 if size=='large' else 0);assert np.max(abs(offset-rr['offset']))<1e-10
 for side,f in c['uv'].items():
  ps=[[({'from':lo,'to':hi}[name])[int(axis)] for name,axis in corner] for corner in corners[side]];a,v=f['uv'];du,dv=f['uv_size'];uv=[a,v,a+du,v+dv]
  if side in ['up','down']:uv=uv[2:]+uv[:2]
  a,v,U,V=uv;us=[[a,v],[U,v],[a,V],[U,V]];out[side]=(np.array([rotate(ps[i],yaw,'y')+offset for i in [0,2,3,1]]),np.array([us[i] for i in [0,2,3,1]]))
 return out,perm['components']['minecraft:material_instances']['*']

surfaces={}
for entry in M['scenes']:
 p=H/entry['file'];assert sha(p.read_bytes())==entry['sha256'];doc=read(p);report['saved_scenes']+=1
 assert all(g['origin']==[0,0,0] and g['rotation']==[0,0,0] for g in doc['groups'])
 if entry['variant']=='TOGGLE':
  assert [g['visibility'] for g in doc['groups']]==[True,False,False]
  assert all(e['visibility']==(e['_review']['variant']=='SOURCE') for e in doc['elements'])
 for t in doc['textures']:
  blob=base64.b64decode(t['source'].split(',')[1]);assert blob==(H/t['_review_input']).read_bytes();im=Image.open(io.BytesIO(blob));assert t['width']==t['uv_width']==im.width and t['height']==t['uv_height']==im.height and t['render_sides']=='front';report['embedded_textures']+=1
 for e in doc['elements']:
  r=e['_review'];source=r['variant']=='SOURCE';expected=source_faces(entry['size'],entry['facing']) if source else native_faces(e,entry['facing'])[0];assert set(expected)==set(e['faces']);assert e['origin']==e['rotation']==[0,0,0];report['saved_meshes']+=1
  for side,(ps,us) in expected.items():
   face=e['faces'][side];savedp=np.array([e['vertices'][k] for k in face['vertices']]);savedu=np.array([face['uv'][k] for k in face['vertices']]);matched=[]
   for p,u in zip(ps,us):
    n=int(np.linalg.norm(savedp-p,axis=1).argmin());assert n not in matched;matched.append(n);pe=float(np.max(abs(savedp[n]-p)));ue=float(np.max(abs(savedu[n]-u)));assert pe<1e-10 and ue<1e-10,(entry['file'],e['name'],side,pe,ue);report['max_vertex_error']=max(report['max_vertex_error'],pe);report['max_uv_error']=max(report['max_uv_error'],ue)
   assert all((matched[(i+1)%4]-matched[i])%4==1 for i in range(4)),'winding mismatch'
   material=r['faces'][side]['material'];tp=doc['textures'][face['texture']]['_review_input'];assert tp==r['faces'][side]['texture_input']
   if source:assert material['render_type']=='entityCutoutNoCull'
   else:
    expectedmat=native_faces(e,entry['facing'])[1];assert material=={'tag':'*',**expectedmat};assert tp=='inputs/current/runtime/RP/'+terrain[expectedmat['texture']]['textures']+'.png'
   report['saved_faces']+=1;report['saved_vertices']+=4
   if entry['variant']!='TOGGLE':surfaces.setdefault((entry['size'],entry['facing'],r['variant']),[]).append({'points':savedp,'uv':savedu,'side':side,'element':e['name']})

def coverage(source,native):
 areas=[0.]*len(source);issues=[];maxuv=0.
 for face in native:
  options=[]
  for i,src in enumerate(source):
   p=src['points'];edge=np.array([p[1]-p[0],p[3]-p[0]]).T;ab=np.linalg.lstsq(edge,(face['points']-p[0]).T,rcond=None)[0].T;res=p[0]+ab@edge.T
   if np.max(abs(res-face['points']))>1e-7 or ab.min()<-1e-7 or ab.max()>1+1e-7:continue
   u=src['uv'];uv=u[0]+ab[:,0,None]*(u[1]-u[0])+ab[:,1,None]*(u[3]-u[0]);err=float(np.max(abs(uv-face['uv'])));options.append((err,i))
  if not options:issues.append({'element':face['element'],'side':face['side'],'not_on_source_exterior':True});continue
  err,i=min(options);maxuv=max(maxuv,err);p=face['points'];areas[i]+=float(np.linalg.norm(np.cross(p[1]-p[0],p[3]-p[0])))
  if err>1e-7:issues.append({'element':face['element'],'side':face['side'],'uv_error':err})
 expected=[float(np.linalg.norm(np.cross(x['points'][1]-x['points'][0],x['points'][3]-x['points'][0]))) for x in source]
 return {'issues':issues,'max_uv_error':maxuv,'source_areas':expected,'native_exterior_areas':areas,'max_area_error':max(abs(a-b) for a,b in zip(areas,expected))}
for size in ['small','large']:
 for facing in ['north','east']:
  for mode in ['BEFORE','AFTER']:
   result=coverage(surfaces[(size,facing,'SOURCE')],surfaces[(size,facing,mode)]);report['surface_comparisons'].append({'size':size,'facing':facing,'variant':mode,**result})
   if mode=='AFTER':assert not result['issues'] and result['max_area_error']<1e-7
   else:assert len(result['issues'])==(5 if size=='small' else 7)

# Real texture samples establish whether GUI views can distinguish the changes.
pixels=[]
for size in ['small','large']:
 w=16 if size=='small' else 48;im=np.array(Image.open(S/(AS+f'textures/entity/deco/{size}_chalkboard.png')).convert('RGBA'));a,b=im[1:29,0],im[1:29,w+1];ys=np.flatnonzero(np.any(a!=b,axis=1))+1;front=im[1:29,1:w+1];back=im[1:29,w+2:2*w+2]
 depths=[0.125,0.25,0.5,0.75,0.875];floors_before=np.floor(depths).astype(int).tolist();floors_after=np.floor(1-np.array(depths)).astype(int).tolist();assert floors_before==floors_after
 row={'size':size,'dimensions':[im.shape[1],im.shape[0]],'side_texel_differences':[{'v':int(y),'world_y_center':30.5-float(y),'positive_end_source_u0':im[y,0].tolist(),'negative_end_source_u_width_plus_1':im[y,w+1].tolist()} for y in ys],'different_side_texels':len(ys),'front_back_different_texels':int(np.any(front!=back,axis=2).sum()),'front_mirror_different_texels':int(np.any(front!=front[:,::-1],axis=2).sum()),'back_mirror_different_texels':int(np.any(back!=back[:,::-1],axis=2).sum()),'bottom_nearest_sampling':{'tested_fractional_depths':depths,'before_and_after_v_floor':floors_before,'different_texels':0,'limitation':'Both directed V intervals traverse the same single pixel row. Nearest sampling cannot prove this correction visually.'}}
 assert row['different_side_texels']==(7 if size=='small' else 0);pixels.append(row)
save('pixel-discrimination.json',pixels)
before=read(H/'original-integrity-before.json');old=ORIGINAL_SNAPSHOT;after={str(p.relative_to(old)):sha(p.read_bytes()) for p in old.rglob('*') if p.is_file()};assert before==after;report['original_files_preserved']=len(before);report['original_scenes_preserved']=sum(k.endswith('.bbmodel') for k in before)
report['status']='PASS: exact candidate delta, saved-file reconstruction, source exterior/UV parity; not GUI or engine acceptance'
save('independent-review-audit.json',report);save('original-integrity-after.json',after)
print(json.dumps({k:v for k,v in report.items() if k not in ['candidate_files','source_branch_contracts','surface_comparisons']},indent=2))
