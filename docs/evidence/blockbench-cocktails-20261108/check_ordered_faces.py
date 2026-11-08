"""Read-only ordered face audit. Requires Pillow, NumPy and SciPy."""
import json,math,itertools,sys,argparse,tempfile,hashlib
from PIL import Image
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
from review_codec import Scene
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[3])
parser.add_argument('--java-assets',type=Path,required=True,help='Pinned Forge assets/kaleidoscope_tavern directory')
parser.add_argument('--neo-models',type=Path,help='Optional flat directory of NeoForge model JSON and PNG files')
args=parser.parse_args(); J=args.java_assets; RP=args.repo/'runtime/RP'
temp=tempfile.TemporaryDirectory(); T=Path(temp.name)
# Refuse source drift from the inputs used in the captured scenes.
rows=json.loads((Path(__file__).parent/'scene-records.json').read_text())
for record in {i['path']:i for row in rows for i in row['inputs']}.values():
    path=record['path']
    if path.startswith('source/'):
        local=args.repo/path.removeprefix('source/')
    elif 'assets/kaleidoscope_tavern/' in path:
        local=J/path.split('assets/kaleidoscope_tavern/',1)[1]
    else:continue
    assert hashlib.sha256(local.read_bytes()).hexdigest()==record['sha256'], str(local)
if args.neo_models:
 for record in json.loads((Path(__file__).parent/'current-java-inputs.json').read_text()):
  local=args.neo_models/Path(record['path']).name
  assert hashlib.sha256(local.read_bytes()).hexdigest()==record['sha256'], str(local)
N='allium_garden bloody_mary depth_charge grasshopper mojito screwdriver white_lady brass_heart emerald empty_glassware godfather mystery_cocktail nether_special sculk_special'.split()
def faces(scene):
 out=[]
 for i,e in enumerate(scene.j['elements']):
  lo,hi=np.array(e['from']),np.array(e['to']);p=np.array(e['origin']);rx,ry,rz=np.radians(e['rotation'])
  X=np.array([[1,0,0],[0,np.cos(rx),-np.sin(rx)],[0,np.sin(rx),np.cos(rx)]]);Y=np.array([[np.cos(ry),0,np.sin(ry)],[0,1,0],[-np.sin(ry),0,np.cos(ry)]]);Z=np.array([[np.cos(rz),-np.sin(rz),0],[np.sin(rz),np.cos(rz),0],[0,0,1]])
  for s,f in e['faces'].items():
   if f['texture'] is None:continue
   axis,side={'north':(2,0),'south':(2,1),'west':(0,0),'east':(0,1),'down':(1,0),'up':(1,1)}[s]
   axes=[a for a in range(3) if a!=axis]
   # Blockbench 5.2.2 CubeFace.UVToLocal, decoded Bedrock via I6.
   # These are UV-parametric corners, not arbitrary geometric enumeration.
   vs=[]
   for u,v in [(0,0),(1,0),(0,1),(1,1)]:
    for _ in range(int(f.get('rotation',0))//90):u,v=1-v,u
    x0,y0,z0=lo;x1,y1,z1=hi
    pt={'east':[x1,y1+(y0-y1)*v,z1+(z0-z1)*u],
        'west':[x0,y1+(y0-y1)*v,z0+(z1-z0)*u],
        'up':[x0+(x1-x0)*u,y1,z0+(z1-z0)*v],
        'down':[x0+(x1-x0)*u,y0,z1+(z0-z1)*v],
        'south':[x0+(x1-x0)*u,y1+(y0-y1)*v,z1],
        'north':[x1+(x0-x1)*u,y1+(y0-y1)*v,z0]}[s]
    vs.append(Z@Y@X@(np.array(pt)-p)+p)
   vs=np.array(vs)
   if np.linalg.norm(np.cross(vs[1]-vs[0],vs[2]-vs[0]))<1e-8:continue
   out.append(dict(element=i,face=s,uv=f['uv'],vertices=vs.tolist(),centroid=vs.mean(axis=0).tolist()))
 return out
def distance(a,b):
 a=np.array(a['vertices']);b=np.array(b['vertices']);return np.linalg.norm(a-b,axis=1).max()
results=[]
for n in N:
 old=Scene(n);old.java(J/f'models/block/mixology/{n}.json',J/f'textures/block/mixology/{n}.png')
 texture=RP/f'textures/kaleidoscope_tavern/block/mixology/{n}.png'
 im=Image.open(texture)
 if im.height!=im.width:
  texture=T/(n+'.png');im.crop((0,0,im.width,im.width)).save(texture)
 native=Scene(n);native.bedrock(RP/f'models/entity/{n}.geo.json',texture)
 assert not any(any(g['rotation']) for g in native.j['groups']), 'This audit does not flatten rotated bone hierarchies.'
 new=Scene(n)
 if args.neo_models and (args.neo_models/f'{n}.json').exists():new.java(args.neo_models/f'{n}.json',args.neo_models/f'{n}.png')
 # Animated sheets: face UV vertical coordinates above use full image; normalize to frame height32.
 for sc in [s for s in (old,new) if s.j['textures']]:
  h=sc.j['textures'][0]['height'];w=sc.j['textures'][0]['width']
  for e in sc.j['elements']:
   for f in e['faces'].values():f['uv'][1]*=w/h;f['uv'][3]*=w/h
 of,bf,nf=map(faces,(old,native,new));matches=[]
 costs=np.array([[distance(a,b) if np.allclose(a['uv'],b['uv'],atol=1e-9,rtol=0) else 1e6 for b in bf] for a in of])
 rows,cols=linear_sum_assignment(costs)
 assert len(rows)==len(of)==len(bf), 'Expected complete bijection'
 for ai,bi in zip(rows,cols):
  a,b=of[ai],bf[bi]
  matches.append({'java_element':a['element'],'java_face':a['face'],'native_cube':b['element'],'native_face':b['face'],'vertex_max_delta':round(distance(a,b),8),'uv_equal':np.allclose(a['uv'],b['uv'],atol=1e-9,rtol=0),'java_centroid':a['centroid'],'native_centroid':b['centroid']})
 bounds=lambda fs:[np.min([f['vertices'] for f in fs],axis=(0,1)).tolist(),np.max([f['vertices'] for f in fs],axis=(0,1)).tolist()]
 row={'name':n,'face_counts':[len(of),len(bf),len(nf)],'bounds_old_native_121':[bounds(f) if f else None for f in (of,bf,nf)],'bijective':True,'all_uv_equal':all(m['uv_equal'] for m in matches),'matched_face_count':len(matches),'max_delta':max(m['vertex_max_delta'] for m in matches),'nonzero_matches':[m for m in matches if m['vertex_max_delta']>1e-6 or not m['uv_equal']]};results.append(row)
 assert row['all_uv_equal'] and row['max_delta']<=0.0625001, row['name']
assert sum(r['matched_face_count'] for r in results)==835
print(json.dumps(results,indent=2))
temp.cleanup()
