"""Independent saved-file audit; does not import scene builder or runtime/source code.
Scalar point rotations and explicit corner tables rederive every face from raw inputs.
"""
from pathlib import Path
import json,math,hashlib,base64,io,re,copy
import numpy as np
from PIL import Image
H=WORK;R=H/'inputs/current';S=H/'inputs/forge';M=json.loads((H/'manifest.json').read_text());read=lambda p:json.loads(p.read_text());sha=lambda b:hashlib.sha256(b).hexdigest()
AS='src/main/resources/assets/kaleidoscope_tavern/';GS='src/generated/resources/assets/kaleidoscope_tavern/'
terrain=read(R/'runtime/RP/textures/terrain_texture.json')['texture_data'];cases={x['id']:x for x in M['cases']};report={'inputs':0,'scenes':0,'textures':0,'meshes':0,'faces':0,'vertices':0,'material_tags':0,'max_vertex_error':0.,'max_uv_error':0.,'pairs':[],'gui_reviewed':False}
for rel,d in M['inputs'].items():assert sha((H/rel).read_bytes())==d['sha256'],rel;report['inputs']+=1

def rotate(point,angles,pivot=(0,0,0)):
 p=[point[i]-pivot[i]for i in range(3)]
 for axis,angle in enumerate(angles):
  c,s=math.cos(angle*math.pi/180),math.sin(angle*math.pi/180);i,j=[(1,2),(2,0),(0,1)][axis];p[i],p[j]=c*p[i]-s*p[j],s*p[i]+c*p[j]
 return [p[i]+pivot[i]for i in range(3)]
def qrot(point,q):
 v=np.array(q[:3]);p=np.array(point);w=q[3];return ((w*w-np.dot(v,v))*p+2*np.dot(v,p)*v+2*w*np.cross(v,p)).tolist()
def add(p,q):return [p[i]+q[i]for i in range(3)]
def geometry_faces(fr,to,rect,rotation=0):
 x,y,z=fr;X,Y,Z=to
 corners={'north':[[X,Y,z],[x,Y,z],[X,y,z],[x,y,z]],'east':[[X,Y,Z],[X,Y,z],[X,y,Z],[X,y,z]],'south':[[x,Y,Z],[X,Y,Z],[x,y,Z],[X,y,Z]],'west':[[x,Y,z],[x,Y,Z],[x,y,z],[x,y,Z]],'up':[[x,Y,z],[X,Y,z],[x,Y,Z],[X,Y,Z]],'down':[[x,y,Z],[X,y,Z],[x,y,z],[X,y,z]]}
 side,uv=rect;a,b,c,d=uv;us=[[a,b],[c,b],[a,d],[c,d]]
 for _ in range(rotation//90):us=[us[2],us[0],us[3],us[1]]
 return [(corners[side][i],us[i])for i in [0,2,3,1]]
def model(name):
 d=read(S/M['source_model_index'][name])
 if 'parent'in d:
  p=model(d['parent'].split(':')[1]);return {**p,**d,'textures':{**p.get('textures',{}),**d.get('textures',{})}}
 return d

def expected(el):
 r=el['_review'];case=cases[r['case']];kind=r['kind'];out={}
 if kind=='java_json':
  name=r['model'];d=model(name);e=d['elements'][r['element']];rot=e.get('rotation',{});pv=rot.get('origin',[0,0,0]);angles=[0,0,0];angles['xyz'.index(rot.get('axis','x'))]=rot.get('angle',0)
  def trans(p):
   p=list(p)
   if rot.get('rescale'):
    k=1/math.cos(math.radians(rot['angle']))
    for i in range(3):
     if i!='xyz'.index(rot['axis']):p[i]=pv[i]+(p[i]-pv[i])*k
   p=rotate(p,angles,pv);p=add(qrot(add(p,[-8,-8,-8]),d.get('transform',{}).get('rotation',[0,0,0,1])),[8,8,8]);return add(add(p,[-8,r['half']*16,-8]),case['source_offset'])
  assert r['offset']==case['source_offset'];assert el['shade']==e.get('shade',True)
  for side,f in e['faces'].items():
   v=f['texture']
   while v.startswith('#'):v=d['textures'][v[1:]]
   tp=S/(AS+'textures/'+v.split(':')[1]+'.png');im=Image.open(tp);uv=[x*im.size[i%2]/16 for i,x in enumerate(f['uv'])];pairs=geometry_faces(e['from'],e['to'],(side,uv),f.get('rotation',0));out[side]=([(trans(p),u)for p,u in pairs],tp,{'render_type':d.get('render_type','solid'),'shade':e.get('shade',True),'cullface':f.get('cullface')})
 elif kind=='native_geometry':
  gp=H/r['geometry_input'];g=next(x for x in read(gp)['minecraft:geometry']if x['description']['identifier']==r['identifier']);bs={b['name']:b for b in g['bones']};bone_root=bs[r['bone']];c=bone_root['cubes'][r['cube']];raw=c['origin'];size=c['size'];fr=[-raw[0]-size[0],raw[1],raw[2]];to=add(fr,size)
  def trans(p):
   pv=c.get('pivot',[0,0,0]);a=c.get('rotation',[0,0,0]);p=rotate(p,[-a[0],-a[1],a[2]],[-pv[0],pv[1],pv[2]]);node=bone_root
   while True:
    pv=node.get('pivot',[0,0,0]);a=node.get('rotation',[0,0,0]);p=rotate(p,[-a[0],-a[1],a[2]],[-pv[0],pv[1],pv[2]])
    if 'parent'not in node:break
    node=bs[node['parent']]
   return add(rotate(p,[0,r['bp_yaw'],0]),r['offset'])
  if case['owner']=='chalkboard':
   bp=read(R/'runtime/BP/blocks/chalkboard.json')['minecraft:block'];cc=next(p['components']for p in bp['permutations']if p['components'].get('minecraft:geometry',{}).get('identifier')==r['identifier']);mat=cc['minecraft:material_instances'];assert r['bp_yaw']=={'north':0,'east':270}[case['facing']]
  else:
   bp=read(R/f'runtime/BP/blocks/{case["owner"]}_sandwich_board.json')['minecraft:block'];cc={**bp['components'],**bp['permutations'][case['rotation']]['components']};assert cc['minecraft:geometry']['identifier']==r['identifier'];assert r['offset']==case['current_offset']and r['bp_yaw']==0;mat=cc['minecraft:material_instances']
  for side,f in c['uv'].items():
   a,b=f['uv'];u,v=f['uv_size'];uv=[a,b,a+u,b+v]
   if side in ['up','down']:uv=[a+u,b+v,a,b]
   tag=f.get('material_instance','*');material=mat.get(tag,mat['*']);tp=R/('runtime/RP/'+terrain[material['texture']]['textures']+'.png');pairs=geometry_faces(fr,to,(side,uv),f.get('uv_rotation',0));out[side]=([(trans(p),u)for p,u in pairs],tp,{'tag':tag,**material})
 elif kind=='java_modelpart':
  text=(H/r['model_input']).read_text();nums=re.search(r'addBox\((.*?)new CubeDeformation',text).group(1);v=[float(s.rstrip('F'))for s in re.findall(r'-?\d+(?:\.\d+)?F?',nums)];x,y,z,w,h,d=v;X,Y,Z=x+w,y+h,z+d;pts=[[x,y,z],[X,y,z],[X,Y,z],[x,Y,z],[x,y,Z],[X,y,Z],[X,Y,Z],[x,Y,Z]];rects={'down':([5,4,0,1],[d,0,d+w,d]),'up':([2,3,7,6],[d+w,d,d+2*w,0]),'west':([0,4,7,3],[0,d,d,d+h]),'north':([1,0,3,2],[d,d,d+w,d+h]),'east':([5,1,2,6],[d+w,d,2*d+w,d+h]),'south':([4,5,6,7],[2*d+w,d,2*d+2*w,d+h])}
  def trans(p):
   p=add(p,[8,24,-8]);p=rotate(p,[0,-(180-{'north':2,'east':3}[case['facing']]*90),0]);p=rotate(p,[0,0,-180]);return add(add(p,[0,24,0]),case['source_offset'])
  tp=S/(AS+'textures/entity/deco/'+('large'if case['large']else'small')+'_chalkboard.png')
  for side,(ids,uv)in rects.items():
   a,b,c,d=uv;out[side]=([(trans(pts[i]),u)for i,u in zip(ids,[[c,b],[a,b],[a,d],[c,d]])],tp,{'render_type':'entityCutoutNoCull','source_part':'bone','shade':'entity lighting; no Java JSON shade property'})
 else:raise AssertionError(kind)
 return out
allpairs={}
for row in M['scenes']:
 doc=read(H/row['file']);assert sha((H/row['file']).read_bytes())==row['sha256'];report['scenes']+=1;assert all(g['origin']==[0,0,0]and g['rotation']==[0,0,0]for g in doc['groups'])
 texs=doc['textures']
 for t in texs:
  raw=base64.b64decode(t['source'].split(',')[1]);assert raw==(H/t['_review_input']).read_bytes();im=Image.open(io.BytesIO(raw));assert t['width']==t['uv_width']==im.width and t['height']==t['uv_height']==im.height;assert t['render_sides']=='front';report['textures']+=1
 for el in doc['elements']:
  ex=expected(el);assert set(ex)==set(el['faces']);assert el['origin']==[0,0,0]and el['rotation']==[0,0,0];report['meshes']+=1
  for side,(pairs,tp,mat)in ex.items():
   f=el['faces'][side];vs=[np.array(el['vertices'][k])for k in f['vertices']];uv=[np.array(f['uv'][k])for k in f['vertices']];assert texs[f['texture']]['_review_input']==str(tp.relative_to(H));assert el['_review']['faces'][side]['material']==mat
   matched=[]
   for p,u in pairs:
    j=min(range(4),key=lambda j:np.linalg.norm(vs[j]-p));assert j not in matched;matched.append(j);pe=float(max(abs(vs[j]-p)));ue=float(max(abs(uv[j]-u)));report['max_vertex_error']=max(report['max_vertex_error'],pe);report['max_uv_error']=max(report['max_uv_error'],ue);assert pe<1e-10 and ue<1e-10,(el['name'],side,pe,ue)
   # Cyclic rotations are permitted; winding reversal is not.
   assert all((matched[(i+1)%4]-matched[i])%4==1 for i in range(4)),(el['name'],side,matched)
   report['vertices']+=4;report['faces']+=1;report['material_tags']+=1
   r=el['_review'];cid=r['case'];current=r['kind']=='native_geometry';case=cases[cid];ps=np.array(vs)-(case['current_offset']if current else case['source_offset']);us=np.array(uv)
   # Explicit native atlas owner proven separately by complete PNG crop checks.
   if not current and case['owner']!='chalkboard':
    atlas=read(H/'routing-and-source-audit.json')['atlas_ownership'];ar=next(x for x in atlas if x['owner']==case['owner']);us[:,0]+=(ar['body_atlas_offset']if tp.name=='body.png'else ar['decor_atlas_offset'])[0]
   allpairs.setdefault(cid,{'source':[],'current':[]})['current'if current else'source'].append({'p':ps,'u':us,'texture':tp.name,'element':el['name'],'side':side})
# Compare independently reconstructed body pairs by exact quad geometry + UV, not images alone.
for cid,faces in allpairs.items():
 case=cases[cid];a,b=faces['source'],faces['current'];out={'case':cid,'source_faces':len(a),'current_faces':len(b)}
 if case['owner']!='chalkboard':
  used=set();errors=[];issues=[]
  for n,x in enumerate(a):
   best=None
   for j,y in enumerate(b):
    if j in used:continue
    for k in range(4):
     pp=np.roll(y['p'],k,axis=0);uu=np.roll(y['u'],k,axis=0);pe=float(np.max(abs(x['p']-pp)));ue=float(np.max(abs(x['u']-uu)));cost=max(pe,ue)
     if best is None or cost<best[0]:best=(cost,j,pe,ue)
   cost,j,pe,ue=best;used.add(j);errors.append((pe,ue))
   if pe>3e-5 or ue>3e-5:issues.append({'source':x['element'],'side':x['side'],'native':b[j]['element'],'native_side':b[j]['side'],'vertex_error':pe,'uv_error':ue})
  out.update(matched_faces=len(a)-len(issues),max_position_error=max(x[0]for x in errors),max_uv_error=max(x[1]for x in errors),issues=issues);assert len(a)==len(b);report['pairs'].append(out)
 else:
  # A whole source cuboid is split across 2/6 active native block pieces. Match each
  # native exterior quad against the whole source plane and its affine UV field.
  areas=[0.]*len(a);issues=[];maxuv=0
  for n,y in enumerate(b):
   candidates=[]
   for j,x in enumerate(a):
    p=x['p'];edge=np.array([p[1]-p[0],p[3]-p[0]]).T;ab=np.linalg.lstsq(edge,(y['p']-p[0]).T,rcond=None)[0].T;res=p[0]+ab@edge.T;err=float(np.max(abs(res-y['p'])));uv=x['u'][0]+ab[:,0,None]*(x['u'][1]-x['u'][0])+ab[:,1,None]*(x['u'][3]-x['u'][0]);ue=float(np.max(abs(uv-y['u'])));
    if err<1e-7 and ab.min()>-1e-7 and ab.max()<1+1e-7:candidates.append((ue,j))
   if not candidates:issues.append({'native':y['element'],'side':y['side'],'no_source_plane':True});continue
   ue,j=min(candidates);maxuv=max(maxuv,ue);area=float(np.linalg.norm(np.cross(y['p'][1]-y['p'][0],y['p'][3]-y['p'][0])));areas[j]+=area
   if ue>1e-7:issues.append({'native':y['element'],'side':y['side'],'uv_error':ue})
  sourceareas=[float(np.linalg.norm(np.cross(x['p'][1]-x['p'][0],x['p'][3]-x['p'][0])))for x in a];out.update(max_uv_error=maxuv,source_exterior_areas=sourceareas,native_exterior_areas=areas,area_error=max(abs(x-y)for x,y in zip(sourceareas,areas)),issues=issues);report['pairs'].append(out)
(H/'independent-saved-file-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='pairs'},indent=2));print('pair issues',[(x['case'],len(x['issues']))for x in report['pairs']])
