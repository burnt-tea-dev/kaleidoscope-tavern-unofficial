from pathlib import Path
import json, math, copy, hashlib, base64, io, uuid, re
import numpy as np
from PIL import Image
H=Path(__file__).resolve().parent; I=H/'inputs'; R=I/'current/runtime/RP'; S=I/'forge/src/main/resources/assets/kaleidoscope_tavern'; V=I/'mojang-1.20.1/assets/minecraft'
M={'scenes':[],'derived_textures':[]}
uid=lambda:str(uuid.uuid4()); sha=lambda b:hashlib.sha256(b).hexdigest()
f=lambda x:float(np.float32(x)); mask=(1<<64)-1
location={'x':3,'y':64,'z':-5}; seed=((3&0x3ffffff)<<38)|((-5&0x3ffffff)<<12)|64
def read(p):return json.loads(p.read_text())

def T(v):m=np.eye(4);m[:3,3]=v;return m

def Q(axis,deg):
 a=math.radians(deg);c,s=math.cos(a),math.sin(a);m=np.eye(4);i,j={'x':(1,2),'y':(2,0),'z':(0,1)}[axis];m[i,i]=m[j,j]=c;m[j,i]=s;m[i,j]=-s;return m

def scale(k):return np.diag([k,k,k,1.])

def apply(m,p):return (m@np.r_[p,1])[:3].tolist()

def quad(fr,to,side,uv):
 x,y,z=fr;X,Y,Z=to
 p={'north':[[X,Y,z],[x,Y,z],[X,y,z],[x,y,z]],'south':[[x,Y,Z],[X,Y,Z],[x,y,Z],[X,y,Z]],'west':[[x,Y,z],[x,Y,Z],[x,y,z],[x,y,Z]],'east':[[X,Y,Z],[X,Y,z],[X,y,Z],[X,y,z]],'up':[[x,Y,z],[X,Y,z],[x,Y,Z],[X,Y,Z]],'down':[[x,y,Z],[X,y,Z],[x,y,z],[X,y,z]]}[side]
 a,b,c,d=uv;uvs=[[a,b],[c,b],[a,d],[c,d]];ix=[0,2,3,1]
 return [p[i] for i in ix],[uvs[i] for i in ix]

class Scene:
 def __init__(self,name):self.j={'meta':{'format_version':'5.0','model_format':'free','box_uv':False},'name':name,'resolution':{'width':128,'height':128},'elements':[],'groups':[],'outliner':[],'textures':[]};self.cache={}
 def group(self,name,parent=None):
  u=uid();self.j['groups'].append({'name':name,'uuid':u,'origin':[0,0,0],'rotation':[0,0,0],'visibility':True,'export':True});n={'uuid':u,'children':[],'isOpen':False};(parent['children']if parent else self.j['outliner']).append(n);return n
 def tex(self,path):
  key=str(path)
  if key in self.cache:return self.cache[key]
  b=path.read_bytes();im=Image.open(io.BytesIO(b));i=len(self.j['textures']);self.cache[key]=i
  self.j['textures'].append({'name':path.name,'id':str(i),'uuid':uid(),'width':im.width,'height':im.height,'uv_width':128,'uv_height':128,'render_mode':'default','render_sides':'front','internal':True,'saved':True,'source':'data:image/png;base64,'+base64.b64encode(b).decode()});return i
 def mesh(self,name,quads,matrix,tex,parent,raw):
  ti=self.tex(tex);verts={};faces={};im=Image.open(tex);w,h=im.size
  for n,(ps,uvs) in enumerate(quads):
   ks=[]
   for k,(p,uv) in enumerate(zip(ps,uvs)):
    key=f'v{n}_{k}';verts[key]=apply(matrix,p);ks.append(key)
   faces[f'f{n}']={'vertices':ks,'uv':{k:[uv[0]*128/w,uv[1]*128/h]for k,uv in zip(ks,uvs)},'texture':ti}
  u=uid();e={'name':name,'uuid':u,'type':'mesh','origin':[0,0,0],'rotation':[0,0,0],'vertices':verts,'faces':faces,'visibility':True,'shade':True,'_review':{**raw,'matrix':matrix.tolist(),'texture_input':str(tex.relative_to(H)),'quad_count':len(quads)}};self.j['elements'].append(e);parent['children'].append(u)
 def body(self,machine,off,tilt=False):
  path=I/'n02/scenes'/('barrel-open.bbmodel'if machine=='barrel'else'pressing-tubs.bbmodel');doc=read(path);nodes=doc['outliner'][:2]if machine=='barrel'or not tilt else doc['outliner'][2:4];gs={g['uuid']:g for g in doc['groups']};es={e['uuid']:e for e in doc['elements']};zold=32 if tilt else 0
  # Add N02 source/current matching roots. Every original body field survives except IDs,
  # scene placement and explicit UV normalization to shared 128-unit texture space.
  for root in nodes:
   rootg=gs[root['uuid']];source='SOURCE'in rootg['name'];dx=off[0]+(-24 if source else 24)-rootg['origin'][0];d=np.array([dx,off[1],off[2]-zold]);mapping={};tmap={}
   def walk(node):
    g=copy.deepcopy(gs[node['uuid']]);old=g['uuid'];g['uuid']=uid();mapping[old]=g['uuid'];g['origin']=(np.array(g['origin'])+d).tolist();self.j['groups'].append(g);new={'uuid':g['uuid'],'children':[],'isOpen':False}
    for c in node['children']:
     if isinstance(c,dict):new['children'].append(walk(c))
     else:
      e=copy.deepcopy(es[c]);e['uuid']=uid()
      for k in ['from','to','origin']:e[k]=(np.array(e[k])+d).tolist()
      for f in e['faces'].values():
       if f['texture']is None:continue
       oldt=f['texture'];t=doc['textures'][oldt]
       if oldt not in tmap:
        tmap[oldt]=len(self.j['textures']);nt=copy.deepcopy(t);nt['uuid']=uid();nt['id']=str(tmap[oldt]);nt['uv_width']=nt['uv_height']=128;self.j['textures'].append(nt)
       f['texture']=tmap[oldt];f['uv']=[v*128/(t.get('uv_width',t['width'])if k%2==0 else t.get('uv_height',t['height']))for k,v in enumerate(f['uv'])]
      self.j['elements'].append(e);new['children'].append(e['uuid'])
    return new
   self.j['outliner'].append(walk(root))
 def save(self,name,cases):
  p=H/'scenes'/f'{name}.bbmodel';p.parent.mkdir(exist_ok=True);p.write_text(json.dumps(self.j,indent=2)+'\n');M['scenes'].append({'file':str(p.relative_to(H)),'sha256':sha(p.read_bytes()),'cases':cases,'gui_reviewed':False});print(name,len(self.j['elements']))

def derived(path,image,origin,note):
 p=H/'derived'/path;p.parent.mkdir(exist_ok=True);image.save(p);M['derived_textures'].append({'file':str(p.relative_to(H)),'source':origin,'operation':note,'sha256':sha(p.read_bytes())});return p

def rnd(i,c):
 h=(seed^(i*0x9e3779b97f4a7c15)^(c*0x6c62272e07bb0142))&mask;h=((h^(h>>30))*0xbf58476d1ce4e5b9)&mask;h=((h^(h>>27))*0x94d049bb133111eb)&mask;h^=h>>31;v=h&0xffffffff;v=v-(1<<32)if v>=1<<31 else v;return f(f(v)/f(2147483647))

def layout(machine,index,slot=0,count=64,current=False):
 r=lambda c:rnd(index,c+slot if machine=='barrel'else c)
 if machine=='barrel':
  x,z=r(1)*6.4,r(2)*6.4;y=43.2+(index//4)*.4+r(3)*.8;yr,zr=r(4)*5,r(5)*360
  if not current:x=f(f(.5)+f(r(1)*f(.4)))*16-8;z=f(f(.5)+f(r(2)*f(.4)))*16-8;y=f(f(2.7)+f(f(index//4*f(.025))+f(r(3)*f(.05))))*16;yr=f(r(4)*5);zr=f(r(5)*360)
  if current:
   start=9 if slot==3 else 0;y+=math.sin(math.radians((start*180/math.pi)%360+(index-start)*57.2957795))*.32
  else:
   local=f(f(index//4*f(.025))+f(r(3)*f(.05)));local=f(local+f(math.sin(index)*f(.02)));y=f(f(2.7)+local)*16
 else:
  x=(-.15 if index%2==0 else .15+r(1)*.0625)*16;z=(-.15 if index%4//2==0 else .15+r(2)*.0625)*16;y=3.2+(index//4)*.5+r(3)*.8;yr=r(4)*count/10;zr=r(5)*360
  if not current:x=f(f(.5)+(-f(.15)if index%2==0 else f(f(.15)+f(r(1)*f(.0625)))))*16-8;z=f(f(.5)+(-f(.15)if index%4//2==0 else f(f(.15)+f(r(2)*f(.0625)))))*16-8;y=f(f(.2)+f(f(index//4*f(.03125))+f(r(3)*f(.05))))*16;yr=f(f(r(4)*count)/10);zr=f(r(5)*360)
 if current:x=math.floor((x+(8 if machine=='barrel'else 4))*128+.5)/128-(8 if machine=='barrel'else 4);z=math.floor((z+(8 if machine=='barrel'else 4))*128+.5)/128-(8 if machine=='barrel'else 4);yr=math.floor((yr+(5 if machine=='barrel'else 6.4))*100+.5)*.01-(5 if machine=='barrel'else 6.4);zr=math.floor((zr+360)*10+.5)*.1-360
 return [x,y,z,yr,zr]

def source_item_quads(kind,tex):
 if kind in ['stone','ice']:
  return[quad([0,0,0],[16,16,16],s,[0,0,16,16])for s in ['north','east','south','west','up','down']]
 im=Image.open(tex).convert('RGBA');frames=[np.array(im.crop((0,y,16,y+16)))[:,:,3]>0 for y in range(0,im.height,16)]
 out=[quad([0,0,7.5],[16,16,8.5],'south',[0,0,16,16]),quad([0,0,7.5],[16,16,8.5],'north',[16,0,0,16])];spans={}
 for a in frames:
  for y in range(16):
   for x in range(16):
    if not a[y,x]:continue
    for side,dx,dy in [('up',0,-1),('down',0,1),('east',-1,0),('west',1,0)]:
     xx,yy=x+dx,y+dy
     if 0<=xx<16 and 0<=yy<16 and a[yy,xx]:continue
     anchor=y if dx==0 else x;v=x if dx==0 else y;k=(side,anchor);spans.setdefault(k,[]).append(v)
 for (s,a),values in spans.items():
  lo,hi=min(values),max(values)
  if s in ['up','down']:
   y=16-a-(s=='down');fr=[lo,y,7.5];to=[hi+1,y,8.5];uv=[lo,a,hi+1,a+1]
  else:
   x=a+(s=='west');fr=[x,16-lo,7.5];to=[x,16-(hi+1),8.5];uv=[a,hi+1,a+1,lo]
  out.append(quad(fr,to,s,uv))
 return out

def add_item(sc,machine,kind,index,slot,off,current=False,tilt=None,count=64,geometry_override=None):
 x,y,z,yr,zr=layout(machine,index,slot,count,current);cube=kind in ['stone','ice'];g=sc.group(('CURRENT'if current else'SOURCE')+f' {kind} slot={slot} global={index}'+(' tilt='+str(tilt)if tilt is not None else''));raw={'kind':('current'if current else'source')+'_ingredient','machine':machine,'item':kind,'index':index,'slot':slot,'count':count,'location':location,'time_ticks':0,'layout':[x,y,z,yr,zr],'tilt_facing':tilt,'texture_bound':'neutral official Java texture control; active native texture is external'if cube and current else'owned texture exact bytes'}
 if cube:tex=V/'textures/block'/f'{kind}.png'
 else:
  if kind=='ice_grape':
   if current:tex=R/'textures/kt_runtime/machine_ingredients/ice_grape/tick_01.png'
   else:
    full=Image.open(S/'textures/item/ice_grape.png').convert('RGBA');a=np.array(full.crop((0,0,16,16)),dtype='uint16');b=np.array(full.crop((0,16,16,32)),dtype='uint16');a[:,:,:3]=(a[:,:,:3]+b[:,:,:3])//2;tex=derived('source-ice-grape-tick1.png',Image.fromarray(a.astype('uint8')),str((S/'textures/item/ice_grape.png').relative_to(H)),'tick1 RGB interpolation; current frame alpha retained; full sprite frame union used for side geometry')
   raw['texture_tick']=1
  else:tex=(R/'textures/kaleidoscope_tavern/item/grape.png')if current else S/'textures/item/grape.png' 
 if current:
  stem=('runtime_barrel_ingredients_'if machine=='barrel'else'runtime_pressing_')+('cube'if cube else'card');gp=geometry_override or R/'models/entity'/f'{stem}.geo.json';geo=read(gp)['minecraft:geometry'][0];bone=next(b for b in geo['bones']if b.get('cubes') and (machine=='barrel' or b['name']==f'item_z_{index%8}'));c=bone['cubes'][0];o,sz=c['origin'],c['size'];fr=[-o[0]-sz[0],o[1],o[2]];to=[fr[k]+sz[k]for k in range(3)];qs=[]
  for side,uv in c['uv'].items():
   u,v=uv['uv'];du,dv=uv['uv_size'];a=[u,v,u+du,v+dv];a=a[2:]+a[:2]if side in ['up','down']else a;qs.append(quad(fr,to,side,a))
  # Explicit Blockbench Bedrock decode: negate X position and X/Y angles.
  item=T([-x,y,z])@(Q('z',zr)@Q('y',-yr)@Q('x',90)if machine=='barrel'else Q('x',90)@Q('y',yr)@Q('z',-zr))
  outer=np.eye(4)
  if tilt is not None:
   pitch=45 if tilt%2 else-45;dy,dz=(8,-8)if tilt%2 else(-4,4)
   outer=Q('y',-tilt*90)@T([8,0,-8])@Q('x',-pitch)@T([-8,0,8])@T([0,dy,dz])
  matrix=T(off)@outer@item;raw.update(geometry_input=str(gp.relative_to(H)),size=sz,transform_basis='Blockbench Bedrock decoder; external entity-to-world transform not simulated',matrix_chain='tilt_yaw / tilt / offset / ingredient / item_y / item_z'if machine!='barrel'else'item single native ZYX Euler')
 else:
  qs=source_item_quads(kind,S/'textures/item/ice_grape.png'if kind=='ice_grape'else tex);outer=np.eye(4)
  if tilt is not None:
   yaw=-(180-[2,3,0,1][tilt]*90);pitch=45 if tilt%2 else-45;dy,dz=(8,-8)if tilt%2 else(-4,4)
   outer=Q('y',yaw)@T([-8,0,-8])@Q('x',pitch)@T([0,dy,dz])@T([8,0,8])
  fixed=.5 if cube else 1;matrix=T(off)@outer@T([x,y,z])@scale(.5)@Q('x',-90)@Q('y',-yr)@Q('z',-zr)@Q('y',0 if cube else 180)@scale(fixed)@T([-8,-8,-8]);raw.update(size=[4,4,4]if cube else[8,8,.5],fixed_scale=fixed,fixed_yaw=0 if cube else 180,matrix_chain='tilt / translation / half scale / XN90 / YNrandom / ZNrandom / FIXED / center',pre_atlas_uv=True)
 sc.mesh(kind+f' {index}',qs,matrix,tex,g,raw);return raw
