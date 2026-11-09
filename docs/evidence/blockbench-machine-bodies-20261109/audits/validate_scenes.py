"""Independent saved-scene group/world-matrix, original ModelPart and ordered face audit.
Does not import the builder or compare its normalized rows to themselves.
"""
from pathlib import Path
import json,hashlib,base64,io,math,re,itertools
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.optimize import linear_sum_assignment
from PIL import Image
from portable_context import context
H, OUT, M = context()
checks={'input_hashes':0,'scenes':0,'textures':0,'cubes':0,'nested_group_vertices':0,'direct_source_modelpart_vertices':0,'direct_source_json_vertices':0,'direct_modelpart_uv_faces':0,'direct_native_vertices':0,'direct_native_uv_faces':0,'gui_reviewed':False}
sha=lambda b:hashlib.sha256(b).hexdigest()
for p,r in M['inputs'].items():
 b=(H/p).read_bytes();assert sha(b)==r['sha256'] and len(b)==r['bytes'];checks['input_hashes']+=1

def translation(v):
 m=np.eye(4);m[:3,3]=v;return m

def matrix(r):
 m=np.eye(4);m[:3,:3]=Rotation.from_euler('xyz',r,degrees=True).as_matrix();return m

def apply(m,pts):return (m@np.c_[pts,np.ones(len(pts))].T).T[:,:3]

def mesh_matrices(doc):
 gs={g['uuid']:g for g in doc['groups']};es={e['uuid']:e for e in doc['elements']};mat={}
 def walk(node,chain):
  g=gs[node['uuid']];assert sum(abs(v)>1e-8 for v in g['rotation'])<=1
  p=np.array(g['origin']);G=translation(p)@matrix(g['rotation'])@translation(-p);world=chain@G
  for ch in node['children']:
   if isinstance(ch,dict):walk(ch,world)
   else:
    assert ch not in mat;e=es[ch];q=np.array(e['origin']);mat[ch]=world@translation(q)@matrix(e['rotation'])@translation(-q)
 for node in doc['outliner']:walk(node,np.eye(4))
 assert len(mat)==len(es)
 return mat

def corners(e):return np.array(list(itertools.product(*zip(e['from'],e['to']))))

def faces(doc,mats,indices,off):
 out=[]
 for i in indices:
  e=doc['elements'][i];x,y,z=e['from'];X,Y,Z=e['to']
  for s,f in e['faces'].items():
   if f['texture'] is None:continue
   vs=[]
   for u,v in [(0,0),(1,0),(0,1),(1,1)]:
    for _ in range(int(f.get('rotation',0))//90):u,v=1-v,u
    p={'east':[X,Y+(y-Y)*v,Z+(z-Z)*u],'west':[x,Y+(y-Y)*v,z+(Z-z)*u],
       'up':[x+(X-x)*u,Y,z+(Z-z)*v],'down':[x+(X-x)*u,y,Z+(z-Z)*v],
       'south':[x+(X-x)*u,Y+(y-Y)*v,Z],'north':[X+(x-X)*u,Y+(y-Y)*v,z]}[s]
    vs.append(p)
   pts=apply(mats[e['uuid']],vs)-off
   if np.linalg.norm(np.cross(pts[1]-pts[0],pts[2]-pts[0]))<1e-8:continue
   out.append({'element':i,'face':s,'uv':f['uv'],'vertices':pts.tolist(),'texture':f['texture'],'shade':e['shade']})
 return out

def group_elements(node):
 out=[]
 for ch in node['children']:out+=group_elements(ch) if isinstance(ch,dict) else [ch]
 return out

NUM=r'-?\d+(?:\.\d+)?'
JA=H/'inputs/forge/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern'
AS=H/'inputs/forge/src/main/resources/assets/kaleidoscope_tavern'
# Separate parser returns raw local author boxes; never creates Bedrock-converted geometry.
def raw_model(name):
 t=(JA/'client/model'/ (name+'.java')).read_text();nodes={}
 for var,parent,n,body,typ,args in re.findall(r'PartDefinition\s+(\w+)\s*=\s*(\w+)\.addOrReplaceChild\("([^"]+)",\s*(.*?),\s*PartPose\.(offsetAndRotation|offset)\((.*?)\)\);',t,re.S):
  a=[float(x) for x in re.findall(NUM,args)];b=[]
  for nums,deformation in re.findall(r'\.addBox\((.*?)new CubeDeformation\(([^)]*)\)\)',body,re.S):
   v=[float(x) for x in re.findall(NUM,nums)];assert len(v)==6;b.append((v[:3],v[3:]))
  nodes[var]={'parent':parent if parent in nodes else None,'offset':a[:3],'rotation':np.degrees(a[3:] if len(a)==6 else [0,0,0]),'boxes':b}
 return nodes

def verify_modelpart(case,doc,mats,indices):
 nodes=raw_model(case['source_model']);pose=case.get('evaluated_keyframe',{});world={};renderer=translation([0,24,0])@matrix([0,0,-180])
 if 'ShakerModel'in case['source_model']:renderer=renderer@matrix([0,-180,0])
 for name,n in nodes.items():
  anim=pose.get(name,{});offset=np.array(n['offset'])+np.array(anim.get('position',[0,0,0]))*np.array([1,-1,1]);r=n['rotation']+anim.get('rotation',[0,0,0]);world[name]=(world[n['parent']] if n['parent'] else renderer)@translation(offset)@matrix(r)
 max_error=0
 for i in indices:
  e=doc['elements'][i];name=e['name'].split(':')[-2];bi=int(e['name'].split(':')[-1]);fr,size=nodes[name]['boxes'][bi];to=np.array(fr)+size;raw=np.array(list(itertools.product(*zip(fr,to))));actual=apply(mats[e['uuid']],corners(e))-case['source_offset'];expected=apply(world[name],raw)
  cost=np.linalg.norm(actual[:,None,:]-expected[None,:,:],axis=2);rr,cc=linear_sum_assignment(cost);error=float(cost[rr,cc].max());assert error<1e-6,(case['id'],name,error);max_error=max(max_error,error);checks['direct_source_modelpart_vertices']+=8
 return max_error

def verify_modelpart_uv(case,doc,mats,indices):
 text=(JA/'client/model'/ (case['source_model']+'.java')).read_text()
 declarations=re.findall(r'PartDefinition\s+(\w+)\s*=\s*(\w+)\.addOrReplaceChild\("([^"]+)",\s*(.*?),\s*PartPose\.(offsetAndRotation|offset)\((.*?)\)\);',text,re.S)
 nodes=raw_model(case['source_model']);pose=case.get('evaluated_keyframe',{});world={}
 renderer=translation([0,24,0])@matrix([0,0,-180])
 if 'ShakerModel'in case['source_model']:renderer=renderer@matrix([0,-180,0])
 for name,n in nodes.items():
  a=pose.get(name,{});world[name]=(world[n['parent']]if n['parent']else renderer)@translation(np.array(n['offset'])+np.array(a.get('position',[0,0,0]))*[1,-1,1])@matrix(n['rotation']+a.get('rotation',[0,0,0]))
 expected=[]
 used={doc['elements'][i]['name'].split(':')[-2]for i in indices}
 for var,parent,name,body,typ,args in declarations:
  if var not in used:continue
  uv=None;mirror=False
  for token in re.finditer(r'\.texOffs\(([^)]*)\)|\.mirror\(([^)]*)\)|\.addBox\((.*?)new CubeDeformation\(([^)]*)\)\)',body,re.S):
   if token[1]:uv=[float(x)for x in re.findall(NUM,token[1])];continue
   if token[2]is not None:mirror=token[2].strip()!='false';continue
   x,y,z,w,h,d=[float(x)for x in re.findall(NUM,token[3])];X,Y,Z=x+w,y+h,z+d
   if mirror:x,X=X,x
   verts=np.array([[x,y,z],[X,y,z],[X,Y,z],[x,Y,z],[x,y,Z],[X,y,Z],[X,Y,Z],[x,Y,Z]])
   u,v=uv
   # Original ModelPart.Cube polygon vertex indices and atlas rectangles;
   # Polygon maps UV (u2,v1),(u1,v1),(u1,v2),(u2,v2), then reverses mirrored winding.
   polys=[([5,1,2,6],[u+d+w,v+d,u+2*d+w,v+d+h]),([0,4,7,3],[u,v+d,u+d,v+d+h]),([1,0,3,2],[u+d,v+d,u+d+w,v+d+h]),([4,5,6,7],[u+2*d+w,v+d,u+2*d+2*w,v+d+h]),([5,4,0,1],[u+d,v,u+d+w,v+d]),([2,3,7,6],[u+d+w,v+d,u+d+2*w,v])]
   for vi,(u1,v1,u2,v2)in polys:
    pts=apply(world[var],verts[vi]);uvs=np.array([[u2,v1],[u1,v1],[u1,v2],[u2,v2]])
    if np.linalg.norm(np.cross(pts[1]-pts[0],pts[2]-pts[0]))<1e-8:continue
    expected.append((pts,uvs))
 actual=[]
 for f in faces(doc,mats,indices,np.array(case['source_offset'])):
  u,v,U,V=f['uv'];actual.append((np.array(f['vertices']),np.array([[u,v],[U,v],[u,V],[U,V]])))
 cost=np.full((len(expected),len(actual)),1e8)
 for ai,(p,uv)in enumerate(expected):
  for bi,(q,tv)in enumerate(actual):
   cc=np.linalg.norm(p[:,None,:]-q[None,:,:],axis=2);cc+=np.where(np.all(np.isclose(uv[:,None,:],tv[None,:,:],atol=1e-8),axis=2),0,1e7);rr,ccol=linear_sum_assignment(cc);cost[ai,bi]=cc[rr,ccol].max()
 rr,cc=linear_sum_assignment(cost);assert len(rr)==len(expected)==len(actual) and cost[rr,cc].max()<1e-6,(case['id'],cost[rr,cc].max())
 checks['direct_modelpart_uv_faces']+=len(actual)
 return float(cost[rr,cc].max())

def verify_json(case,doc,mats,indices):
 maxerr=0
 for i in indices:
  e=doc['elements'][i];rel,num=e['name'].rsplit(':',1);j=json.loads((AS/'models'/ (rel+'.json')).read_text());el=j['elements'][int(num)];r=el.get('rotation',{});origin=np.array(r.get('origin',[8,0,8]));angs=[0,0,0];axis='xyz'.index(r.get('axis','y'));angs[axis]=r.get('angle',0)
  coords=np.array(list(itertools.product(*zip(el['from'],el['to']))),float)
  if r.get('rescale'):
   for k in range(3):
    if k!=axis:coords[:,k]=origin[k]+(coords[:,k]-origin[k])/math.cos(math.radians(angs[axis]))
  expected=apply(translation(origin)@matrix(angs)@translation(-origin),coords)-[8,0,8]
  if 'stepladder/top'in rel:expected[:,1]+=16
  actual=apply(mats[e['uuid']],corners(e))-case['source_offset'];err=float(np.linalg.norm(actual-expected,axis=1).max());assert err<1e-6,(case['id'],err);maxerr=max(maxerr,err);checks['direct_source_json_vertices']+=8
 return maxerr

def verify_native_original(case,doc,mats,indices):
 cache={};maximum=0
 for i in indices:
  e=doc['elements'][i];stem,bone,num=e['name'].split(':');num=int(num)
  if stem not in cache:
   g=json.loads((H/'snapshot/runtime/RP/models/entity'/(stem+'.geo.json')).read_text())['minecraft:geometry'][0];bs={b['name']:b for b in g['bones']};world={}
   for n,b in bs.items():
    ap=case.get('evaluated_keyframe',{}).get(n,{});p=np.array(b.get('pivot',[0,0,0]));r=np.array(b.get('rotation',[0,0,0]))+ap.get('rotation',[0,0,0]);pos=ap.get('position',[0,0,0])
    world[n]=(world[b['parent']]if b.get('parent')else np.eye(4))@translation(pos)@translation(p)@matrix(r*[-1,1,-1])@translation(-p)
   cache[stem]=(bs,world)
  bs,world=cache[stem];c=bs[bone]['cubes'][num];o=np.array(c['origin']);size=np.array(c['size']);raw=np.array(list(itertools.product(*zip(o,o+size))));p=np.array(c.get('pivot',[0,0,0]));r=np.array(c.get('rotation',[0,0,0]));expected=apply(world[bone]@translation(p)@matrix(r*[-1,1,-1])@translation(-p),raw)*[-1,1,1]
  if stem=='stepladder_top':expected[:,1]+=16
  actual=apply(mats[e['uuid']],corners(e))-case['native_offset'];cost=np.linalg.norm(actual[:,None,:]-expected[None,:,:],axis=2);rr,cc=linear_sum_assignment(cost);err=float(cost[rr,cc].max());assert err<1e-6,(case['id'],stem,bone,err);maximum=max(maximum,err);checks['direct_native_vertices']+=8
  if isinstance(c['uv'],dict):
   uv={}
   for side,f in c['uv'].items():
    u,v=f['uv'];U,V=np.array([u,v])+f['uv_size'];rect=[u,v,U,V]if side not in ('up','down')else [U,V,u,v];uv[side]=(rect,f.get('uv_rotation',0))
  else:
   u,v=c['uv'];w,h,d=size
   uv={'east':([u,v+d,u+d,v+d+h],0),'west':([u+d+w,v+d,u+2*d+w,v+d+h],0),'north':([u+d,v+d,u+d+w,v+d+h],0),'south':([u+2*d+w,v+d,u+2*d+2*w,v+d+h],0),'up':([u+d+w,v+d,u+d,v],0),'down':([u+d+2*w,v,u+d+w,v+d],0)}
   if c.get('mirror',bs[bone].get('mirror',False)):
    uv={k:([r[2],r[1],r[0],r[3]],ang)for k,(r,ang)in uv.items()};uv['east'],uv['west']=uv['west'],uv['east']
  assert set(uv)=={k for k,f in e['faces'].items()if f['texture']is not None}
  for k,(rect,ang)in uv.items():assert np.allclose(e['faces'][k]['uv'],rect,atol=1e-8,rtol=0) and e['faces'][k].get('rotation',0)==ang;checks['direct_native_uv_faces']+=1
 return maximum

rows=[]
for sc in M['scenes']:
 b=Path(sc['file']).read_bytes();assert sha(b)==sc['sha256'];doc=json.loads(b);checks['scenes']+=1
 mats=mesh_matrices(doc);ids=[v['uuid']for key in ['elements','groups','textures']for v in doc[key]];assert len(ids)==len(set(ids));ix={e['uuid']:i for i,e in enumerate(doc['elements'])};ims={}
 for i,t in enumerate(doc['textures']):
  assert t['source'].startswith('data:image/png;base64,');im=Image.open(io.BytesIO(base64.b64decode(t['source'].split(',',1)[1]))).convert('RGBA');assert im.size==(t['width'],t['height'])==(t['uv_width'],t['uv_height']);ims[i]=im;checks['textures']+=1
 for e in doc['elements']:
  assert all(math.isfinite(v) for k in ['from','to','origin','rotation']for v in e[k]);assert isinstance(e['shade'],bool);checks['cubes']+=1;assert np.all(np.isfinite(apply(mats[e['uuid']],corners(e))));checks['nested_group_vertices']+=8
  for f in e['faces'].values():assert f['texture'] is None or f['texture']in ims
 caseids=sc['cases']
 for ci,cid in enumerate(caseids):
  case=next(c for c in M['cases']if c['id']==cid);offa=np.array(case['source_offset']);offb=np.array(case['native_offset']);
  if cid=='stepladder-placed-assembly':
   ai=[ix[x]for n in doc['outliner'] if 'SOURCE'in next(g['name'] for g in doc['groups'] if g['uuid']==n['uuid']) for x in group_elements(n)]
   bi=[ix[x]for n in doc['outliner'] if 'CURRENT'in next(g['name'] for g in doc['groups'] if g['uuid']==n['uuid']) for x in group_elements(n)]
  else:ai=[ix[x] for x in group_elements(doc['outliner'][ci*2])];bi=[ix[x] for x in group_elements(doc['outliner'][ci*2+1])]
  native_original_error=verify_native_original(case,doc,mats,bi)
  uv_original_error=verify_modelpart_uv(case,doc,mats,ai) if case['source_kind'].startswith('Java ModelPart') else 0
  raw_error=verify_modelpart(case,doc,mats,ai) if case['source_kind'].startswith('Java ModelPart') else verify_json(case,doc,mats,ai)
  af,bf=faces(doc,mats,ai,offa),faces(doc,mats,bi,offb);cost=np.full((len(af),len(bf)),1e9)
  for i,a in enumerate(af):
   for k,b in enumerate(bf):
    if np.allclose(a['uv'],b['uv'],atol=1e-8,rtol=0):cost[i,k]=np.linalg.norm(np.array(a['vertices'])-b['vertices'],axis=1).max()
  rr,cc=linear_sum_assignment(cost);pairs=[]
  for a,b in zip(rr,cc):
   x,y=af[a],bf[b];im,jm=ims[x['texture']],ims[y['texture']];pairs.append({'source_element':x['element'],'source_face':x['face'],'native_element':y['element'],'native_face':y['face'],'max_vertex_delta':float(cost[a,b]),'uv_equal':bool(np.allclose(x['uv'],y['uv'],atol=1e-8,rtol=0)),'pixels_equal':im.size==jm.size and im.tobytes()==jm.tobytes(),'shade_equal':x['shade']==y['shade']})
  row={'id':cid,'source_faces':len(af),'native_faces':len(bf),'paired_faces':len(pairs),'max_vertex_delta':max(p['max_vertex_delta']for p in pairs),'source_original_world_matrix_max_error':raw_error,'source_original_polygon_uv_error':uv_original_error,'native_original_world_matrix_max_error':native_original_error,'uv_mismatches':sum(not p['uv_equal']for p in pairs),'pixel_mismatches':sum(not p['pixels_equal']for p in pairs),'shade_mismatches':sum(not p['shade_equal']for p in pairs),'pairs':pairs}
  rows.append(row);print(cid,{k:v for k,v in row.items()if k!='pairs'})
summary={'cases':len(rows),'paired_faces':sum(r['paired_faces']for r in rows),'max_vertex_delta':max(r['max_vertex_delta']for r in rows),'uv_mismatches':sum(r['uv_mismatches']for r in rows),'pixel_mismatches':sum(r['pixel_mismatches']for r in rows),'shade_mismatches':sum(r['shade_mismatches']for r in rows)}
(OUT/'ordered-face-world-audit.json').write_text(json.dumps({'method':'Raw Java ModelPart local transforms evaluated directly; independent saved-scene homogeneous group matrices; ordered UV-parametric corners including signed extents and quarter-turn UV; one-to-one minimum vertex distance constrained by UV. Zero-area faces excluded, not silently thickened.','summary':summary,'cases':rows},indent=2)+'\n')
(OUT/'structural-validation.json').write_text(json.dumps(checks,indent=2)+'\n');print(summary);print(checks)
