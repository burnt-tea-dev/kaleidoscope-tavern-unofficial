"""Review-only Blockbench projects. No runtime files are modified or exported.
The Bedrock decode follows Blockbench 5.2.2's I6/D6 codec transforms.
"""
import json,base64,uuid,copy,math
from pathlib import Path
from PIL import Image
OUT=Path('.')  # Read-only audit does not call save().
SIDES=['north','east','south','west','up','down']
def uid():return str(uuid.uuid4())
def read(p):return json.loads(p.read_text())
class Scene:
 def __init__(self,name):self.j={'meta':{'format_version':'5.0','model_format':'free','box_uv':False},'name':name,'resolution':{'width':128,'height':128},'elements':[],'groups':[],'outliner':[],'textures':[]};self.tex={}
 def texture(self,path):
  if str(path) in self.tex:return self.tex[str(path)]
  i=len(self.j['textures']);w,h=Image.open(path).size; self.tex[str(path)]=i
  self.j['textures'].append({'name':path.name,'id':str(i),'uuid':uid(),'width':w,'height':h,'uv_width':w,'uv_height':h,'render_mode':'default','render_sides':'front','internal':True,'saved':True,'source':'data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()});return i
 def group(self,name,origin=[0,0,0],rotation=[0,0,0],parent=None):
  u=uid();self.j['groups'].append({'name':name,'uuid':u,'origin':origin,'rotation':rotation,'visibility':True,'export':True,'isOpen':False});node={'uuid':u,'isOpen':False,'children':[]}; (parent['children'] if parent else self.j['outliner']).append(node);return node
 def cube(self,name,fr,to,faces,origin,rotation,parent):
  u=uid();allfaces={side:{'uv':[0,0,0,0],'texture':None} for side in SIDES};allfaces.update(faces)
  self.j['elements'].append({'name':name,'uuid':u,'type':'cube','box_uv':False,'from':fr,'to':to,'origin':origin,'rotation':rotation,'autouv':0,'faces':allfaces,'visibility':True});parent['children'].append(u)
 def bedrock(self,path,texture,offset=[0,0,0],yaw=0,parent=None,name='canonical'):
  g=read(path)['minecraft:geometry'][0];assert Image.open(texture).size==(g['description']['texture_width'],g['description']['texture_height']), 'Review UV resolution must match texture dimensions';tex=self.texture(texture);group=self.group(name,offset,[0,yaw,0],parent);nodes={}
  def add(v):return [v[i]+offset[i] for i in range(3)]
  for b in g['bones']:
   p=b.get('pivot',[0,0,0]);r=b.get('rotation',[0,0,0]);node=self.group(b['name'],add([-p[0],p[1],p[2]]),[-r[0],-r[1],r[2]],nodes.get(b.get('parent'),group));nodes[b['name']]=node
   for n,c in enumerate(b.get('cubes',[])):
    o=c['origin'];z=c['size'];fr=[-o[0]-z[0],o[1],o[2]];to=[fr[i]+z[i] for i in range(3)];p=c.get('pivot',[0,0,0]);r=c.get('rotation',[0,0,0]);faces={}
    for side,f in c['uv'].items():
     a,bv=f['uv'];du,dv=f['uv_size'];uv=[a,bv,a+du,bv+dv]
     if side in ('up','down'):uv=uv[2:]+uv[:2]
     faces[side]={'uv':uv,'texture':tex,'rotation':f.get('uv_rotation',0)}
    self.cube(b['name']+'_'+str(n),add(fr),add(to),faces,add([-p[0],p[1],p[2]]),[-r[0],-r[1],r[2]],node)
 def java(self,path,texture,offset=[0,0,0]):
  j=read(path);assert not j.get('parent'), 'Resolve Java parents before review';tex=self.texture(texture);group=self.group('Java authored '+path.stem,offset)
  def add(v):return [v[i]+offset[i]+(-8 if i!=1 else 0) for i in range(3)]
  for n,e in enumerate(j['elements']):
   r=e.get('rotation',{});rot=[0,0,0];rot['xyz'.index(r.get('axis','y'))]=r.get('angle',0)
   faces={s:{'uv':[x*(Image.open(texture).size[k%2]/16) for k,x in enumerate(f['uv'])],'texture':tex,'rotation':f.get('rotation',0)} for s,f in e['faces'].items()}
   fr=e['from'][:];to=e['to'][:];pivot=r.get('origin',[8,0,8])
   if r.get('rescale'):
    axis='xyz'.index(r['axis']);angle=abs(r['angle']);assert angle in (0,22.5,45)
    factor=1/math.cos(math.radians(angle))
    for k in range(3):
     if k!=axis:fr[k]=pivot[k]+(fr[k]-pivot[k])*factor;to[k]=pivot[k]+(to[k]-pivot[k])*factor
   self.cube('Java element '+str(n),add(fr),add(to),faces,add(pivot),rot,group)
   self.j['elements'][-1]['shade']=e.get('shade',True)
 def save(self,name): (OUT/name).write_text(json.dumps(self.j,indent=2)+'\n')
