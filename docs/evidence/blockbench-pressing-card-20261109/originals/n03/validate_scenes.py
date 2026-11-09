"""Independent original-input and saved-mesh audit. Never imports the builder.
Separate vector/matrix library, float32 arithmetic via struct, generic bone chain
and restricted Molang evaluator. Per-coordinate FP-roundoff bound, no parity tolerance.
"""
from pathlib import Path
import json,math,struct,re,hashlib,base64,io,ast,operator
import numpy as np
from scipy.spatial.transform import Rotation
from PIL import Image
H=Path(__file__).resolve().parent;M=json.loads((H/'manifest.json').read_text());I=H/'inputs';R=I/'current/runtime/RP';V=I/'mojang-1.20.1/assets/minecraft';S=I/'forge/src/main/resources/assets/kaleidoscope_tavern';audit={'hashes':0,'textures':0,'meshes':0,'directed_faces':0,'vertices':0,'max_matrix_error':0,'max_vertex_error':0,'body_instances':0,'route_checks':{},'cases':[],'gui_reviewed':False}
sha=lambda b:hashlib.sha256(b).hexdigest();rd=lambda p:json.loads(p.read_text())
for path,e in M['inputs'].items():
 b=(H/path).read_bytes();assert sha(b)==e['sha256'] and len(b)==e['bytes'];audit['hashes']+=1
for e in M['derived_textures']:assert sha((H/e['file']).read_bytes())==e['sha256']
def trans(v):m=np.eye(4);m[:3,3]=v;return m
def rot(axis,d):m=np.eye(4);v=np.zeros(3);v['xyz'.index(axis)]=math.radians(d);m[:3,:3]=Rotation.from_rotvec(v).as_matrix();return m
def scl(n):return np.diag([n,n,n,1.])
def apply(m,p):return np.einsum('ij,kj->ki',m,np.column_stack([p,np.ones(len(p))]))[:,:3]
def close(actual,expected,label):
 a,b=np.array(actual),np.array(expected);error=float(np.max(np.abs(a-b))) if a.size else 0;bound=256*np.finfo(float).eps*max(1,float(np.max(np.abs(b))))
 assert error<=bound,(label,error,bound);return error
# Derive Java RNG independently with signed 64-bit overflow at every multiply.
def signed64(x):return ((x+(1<<63))%(1<<64))-(1<<63)
def unsigned64(x):return x%(1<<64)
f32=lambda n:struct.unpack('f',struct.pack('f',n))[0]
def rng(loc,i,c):
 seed=((loc['x']&67108863)<<38)|((loc['z']&67108863)<<12)|(loc['y']&4095);h=signed64(seed^signed64(i*-7046029254386353131)^signed64(c*7809847782465536322));h=signed64((h^(unsigned64(h)>>30))*-4658895280553007687);h=signed64((h^(unsigned64(h)>>27))*-7723592293110705685);h=h^(unsigned64(h)>>31);v=((h+(1<<31))%(1<<32))-(1<<31);return f32(f32(v)/f32(2147483647))
def source_values(a):
 i,slot,count=a['index'],a['slot'],a['count'];r=lambda c:rng(a['location'],i,c+slot if a['machine']=='barrel'else c)
 if a['machine']=='barrel':
  x=f32(f32(.5)+f32(r(1)*f32(.4)))*16-8;z=f32(f32(.5)+f32(r(2)*f32(.4)))*16-8;y=f32(f32(i//4*f32(.025))+f32(r(3)*f32(.05)));y=f32(y+f32(math.sin(i)*f32(.02)));y=f32(f32(2.7)+y)*16;yr=f32(r(4)*5);zr=f32(r(5)*360)
 else:
  xp=-f32(.15)if i%2==0 else f32(f32(.15)+f32(r(1)*f32(.0625)));zp=-f32(.15)if i%4//2==0 else f32(f32(.15)+f32(r(2)*f32(.0625)));x=f32(f32(.5)+xp)*16-8;z=f32(f32(.5)+zp)*16-8;y=f32(f32(.2)+f32(f32(i//4*f32(.03125))+f32(r(3)*f32(.05))))*16;yr=f32(f32(r(4)*count)/10);zr=f32(r(5)*360)
 return x,y,z,yr,zr
def properties(a):
 i,slot,count=a['index'],a['slot'],a['count'];r=lambda c:rng(a['location'],i,c+slot if a['machine']=='barrel'else c);rr=lambda v:math.floor(v+.5)
 if a['machine']=='barrel':
  local=i if slot==0 else i-9;start=i-local;x=r(1)*6.4;z=r(2)*6.4;y=43.2+(i//4)*.4+r(3)*.8;yr=r(4)*5;zr=r(5)*360;b=8;radix=2048;ra=5
 else:
  local=i%8;x=(-.15 if i%2==0 else .15+r(1)*.0625)*16;z=(-.15 if i%4//2==0 else .15+r(2)*.0625)*16;y=3.2+(i//4)*.5+r(3)*.8;yr=r(4)*count/10;zr=r(5)*360;b=4;radix=1024;ra=6.4;start=0
 props={f'xz{local}':rr((x+b)*128)*radix+rr((z+b)*128),f'y{local}':y,f'rot{local}':rr((yr+ra)*100)*7201+rr((zr+360)*10),'phase':(start*180/math.pi)%360,'tilt':int(a['tilt_facing'] is not None),'facing':a['tilt_facing']or 0}
 return props,local
def expression(s,props):
 if isinstance(s,(int,float)):return s
 s=re.sub(r"(?:q|query)\.property\('(?:kaleidoscope_tavern:|kt_art:)([^']+)'\)",lambda m:str(props[m[1]]),s).replace('q.life_time','0').replace('query.life_time','0')
 def strip(x):
  while x.startswith('('):
   depth=0;end=None
   for i,c in enumerate(x):
    depth+=(c=='(')-(c==')')
    if not depth:end=i;break
   if end!=len(x)-1:break
   x=x[1:-1].strip()
  return x
 def ternary(x):
  x=strip(x.strip());depth=0;q=None;nested=0
  for n,c in enumerate(x):
   depth+=(c=='(')-(c==')')
   if depth:continue
   if c=='?' and q is None:q=n
   elif c=='?' and q is not None:nested+=1
   elif c==':'and q is not None:
    if nested:nested-=1
    else:return ternary(x[q+1:n]if ternary(x[:q])else x[n+1:])
  node=ast.parse(x,mode='eval').body
  def ev(n):
   if isinstance(n,ast.Constant):return n.value
   if isinstance(n,ast.UnaryOp):return -ev(n.operand)if isinstance(n.op,ast.USub)else ev(n.operand)
   if isinstance(n,ast.BinOp):return {ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.Mod:operator.mod}[type(n.op)](ev(n.left),ev(n.right))
   if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.value.id=='math':return {'floor':math.floor,'mod':math.fmod,'sin':lambda d:math.sin(math.radians(d))}[n.func.attr](*[ev(a)for a in n.args])
   raise ValueError(ast.dump(n))
  return ev(node)
 return ternary(s)
def native_matrix(a):
 geo=rd(H/a['geometry_input'])['minecraft:geometry'][0];props,idx=properties(a);anfile='runtime_barrel_ingredients.animation.json'if a['machine']=='barrel'else'runtime_pressing_ingredients.animation.json';anim=next(iter(rd(R/'animations'/anfile)['animations'].values()))['bones'];chain={};piv={};target=None
 for b in geo['bones']:
  name=b['name'];oldname=name;name=re.sub(r'_0$',f'_{idx}',name);ap=anim.get(name,{});p=np.array(b.get('pivot',[0,0,0]))*[-1,1,1];r=np.array([expression(x,props)for x in ap.get('rotation',b.get('rotation',[0,0,0]))])*[-1,-1,1];pos=np.array([expression(x,props)for x in ap.get('position',[0,0,0])])*[-1,1,1]
  if b.get('parent') not in chain:parent=np.eye(4);pp=np.zeros(3)
  else:parent=chain[b['parent']];pp=piv[b['parent']]
  chain[oldname]=parent@trans(p-pp+pos)@rot('z',r[2])@rot('y',r[1])@rot('x',r[0]);piv[oldname]=p
  if b.get('cubes'):target=chain[oldname]@trans(-p);break
 return target
# Independent polygon construction: explicit outward directed faces and UV association.
def face(fr,to,s,uv):
 x,y,z=fr;X,Y,Z=to;a,b,c,d=uv
 ps={'north':[[X,Y,z],[X,y,z],[x,y,z],[x,Y,z]],'south':[[x,Y,Z],[x,y,Z],[X,y,Z],[X,Y,Z]],'west':[[x,Y,z],[x,y,z],[x,y,Z],[x,Y,Z]],'east':[[X,Y,Z],[X,y,Z],[X,y,z],[X,Y,z]],'up':[[x,Y,z],[x,Y,Z],[X,Y,Z],[X,Y,z]],'down':[[x,y,Z],[x,y,z],[X,y,z],[X,y,Z]]}[s]
 return ps,[[a,b],[a,d],[c,d],[c,b]]
def source_quads(kind):
 if kind in ('ice','stone'):return[face([0,0,0],[16,16,16],d,[0,0,16,16])for d in ['north','east','south','west','up','down']]
 im=Image.open(S/f'textures/item/{kind}.png').convert('RGBA');q=[face([0,0,7.5],[16,16,8.5],'south',[0,0,16,16]),face([0,0,7.5],[16,16,8.5],'north',[16,0,0,16])];rows={}
 # Traverse pixels and maintain min/max spans, independently of builder's lists.
 for frame in range(im.height//16):
  for y in range(16):
   for x in range(16):
    if im.getpixel((x,frame*16+y))[3]==0:continue
    for d,dx,dy in [('up',0,-1),('down',0,1),('east',-1,0),('west',1,0)]:
     nx,ny=x+dx,y+dy
     if 0<=nx<16 and 0<=ny<16 and im.getpixel((nx,frame*16+ny))[3]!=0:continue
     key=(d,y if dy else x);v=x if dy else y;lo,hi=rows.get(key,(v,v));rows[key]=(min(lo,v),max(hi,v))
 for (d,k),(lo,hi)in rows.items():
  if d in ('up','down'):y=16-k-int(d=='down');q.append(face([lo,y,7.5],[hi+1,y,8.5],d,[lo,k,hi+1,k+1]))
  else:x=k+int(d=='west');q.append(face([x,16-lo,7.5],[x,15-hi,8.5],d,[k,hi+1,k+1,lo]))
 return q
for scene in M['scenes']:
 p=H/scene['file'];assert sha(p.read_bytes())==scene['sha256'];doc=rd(p);tex=[]
 for t in doc['textures']:
  im=Image.open(io.BytesIO(base64.b64decode(t['source'].split(',',1)[1])));assert im.size==(t['width'],t['height']);assert t['uv_width']==t['uv_height']==128;tex.append(im);audit['textures']+=1
 # Contents are world-baked meshes. Hierarchy nodes for these meshes are identity.
 gs={g['uuid']:g for g in doc['groups']};elementparents={}
 def walk(node,chain):
  g=gs[node['uuid']];p=np.array(g['origin']);r=g['rotation'];chain=chain@trans(p)@rot('z',r[2])@rot('y',r[1])@rot('x',r[0])@trans(-p)
  for ch in node['children']:
   if isinstance(ch,dict):walk(ch,chain)
   else:elementparents[ch]=chain
 for node in doc['outliner']:walk(node,np.eye(4))
 for e in doc['elements']:
  if e['type']!='mesh':continue
  a=e['_review'];matrix=np.array(a['matrix']);kind=a['kind'];source=kind.startswith('source');off=np.array([24 if not source else-24,0,0]);zoffset=matrix[2,3] # Recovered scene separation comes from scene rows, not arbitrary translation fitting.
  if 'fluid'in kind:
   row=['water','lava','grape'].index(a['fluid']);off[2]=row*44;size=16 if a['machine']=='barrel'else 12;cap=4000 if a['machine']=='barrel'else 1000;y=32+10.4*a['amount']/cap if a['machine']=='barrel'else 2+4*a['amount']/cap
   expected_matrix=trans(off)
   if source:
    y=f32(f32(a['amount']/cap)*f32(.65))*16+32 if a['machine']=='barrel' else f32(f32(.125)+f32(f32(a['amount']/cap)*f32(.25)))*16
    q=[([[-size/2,y,-size/2],[-size/2,y,size/2],[size/2,y,size/2],[size/2,y,-size/2]],[[0,0],[0,size],[size,size],[size,0]])]
   else:
    c=rd(H/a['geometry_input'])['minecraft:geometry'][0]['bones'][0]['cubes'][0];o=c['origin'];s=c['size'];u,v=c['uv']['up']['uv'];du,dv=c['uv']['up']['uv_size'];q=[face([-o[0]-s[0],y,o[2]],[-o[0],y,o[2]+s[2]],'up',[u+du,v+dv,u,v])]
  else:
   if 'cube-material'in scene['file']:off[2]=[('barrel','stone'),('barrel','ice'),('pressing_tub','stone'),('pressing_tub','ice')].index((a['machine'],a['item']))*44
   if 'animated-card'in scene['file']:off[2]=['barrel','pressing_tub'].index(a['machine'])*44
   if source:
    x,y,z,yr,zr=source_values(a);close(a['layout'],[x,y,z,yr,zr],'Java float layout');cube=a['item']in ['ice','stone'];parent=rd(V/('models/block/block.json'if cube else'models/item/generated.json'))['display']['fixed'];fixed=parent['scale'][0];fy=parent['rotation'][1];outer=np.eye(4);facing=a['tilt_facing']
    if facing is not None:
     odd=facing%2;outer=rot('y',-(180-[2,3,0,1][facing]*90))@trans([-8,0,-8])@rot('x',45 if odd else-45)@trans([0,8 if odd else-4,-8 if odd else 4])@trans([8,0,8])
    expected_matrix=trans(off)@outer@trans([x,y,z])@scl(.5)@rot('x',-90)@rot('y',-yr)@rot('z',-zr)@rot('y',fy)@scl(fixed)@trans([-8,-8,-8]);q=source_quads(a['item'])
   else:
    expected_matrix=trans(off)@native_matrix(a);c=next(b for b in rd(H/a['geometry_input'])['minecraft:geometry'][0]['bones']if b.get('cubes'))['cubes'][0];o,s=c['origin'],c['size'];fr=[-o[0]-s[0],o[1],o[2]];to=[-o[0],o[1]+s[1],o[2]+s[2]];q=[]
    for side,v in c['uv'].items():
     u,w=v['uv'];du,dv=v['uv_size'];uv=[u,w,u+du,w+dv];uv=[u+du,w+dv,u,w]if side in ['up','down']else uv;q.append(face(fr,to,side,uv))
  audit['max_matrix_error']=max(audit['max_matrix_error'],close(matrix,expected_matrix,'world matrix '+e['name']));assert len(q)==len(e['faces']);close(elementparents[e['uuid']],np.eye(4),'mesh parent identity')
  for n,(ps,uvs)in enumerate(q):
   faceid='f'+str(n);f=e['faces'][faceid];ks=f['vertices'];actual=[e['vertices'][k]for k in ks];expected=apply(expected_matrix,ps);audit['max_vertex_error']=max(audit['max_vertex_error'],close(actual,expected,'directed world vertices'))
   image=tex[f['texture']];uvexpected=[[u*128/image.width,v*128/image.height]for u,v in uvs];close([f['uv'][k]for k in ks],uvexpected,'original directed UV');audit['directed_faces']+=1;audit['vertices']+=4
  audit['meshes']+=1
# Verify copied N02 body hierarchy independently, including UV normalization and PNG bytes.
originals=[]
for op in (I/'n02/scenes').glob('*.bbmodel'):
 od=rd(op);og={g['uuid']:g for g in od['groups']};oe={e['uuid']:e for e in od['elements']}
 for root in od['outliner']:originals.append((od,og,oe,root))
for scene in M['scenes']:
 d=rd(H/scene['file']);gs={g['uuid']:g for g in d['groups']};es={e['uuid']:e for e in d['elements']}
 for root in d['outliner']:
  matches=[v for v in originals if v[1][v[3]['uuid']]['name']==gs[root['uuid']]['name']]
  if not matches:continue
  assert len(matches)==1;od,og,oe,old=matches[0];delta=np.array(gs[root['uuid']]['origin'])-og[old['uuid']]['origin']
  def compare_nodes(a,b):
   ga,gb=gs[a['uuid']],og[b['uuid']];assert ga['name']==gb['name'] and ga['rotation']==gb['rotation'];close(np.array(ga['origin'])-delta,gb['origin'],'N02 group pivot');assert len(a['children'])==len(b['children'])
   for ca,cb in zip(a['children'],b['children']):
    assert isinstance(ca,dict)==isinstance(cb,dict)
    if isinstance(ca,dict):compare_nodes(ca,cb);continue
    ea,eb=es[ca],oe[cb];assert ea['name']==eb['name'] and ea['rotation']==eb['rotation'] and ea['shade']==eb['shade']
    for key in ['from','to','origin']:close(np.array(ea[key])-delta,eb[key],'N02 cube '+key)
    for side,fb in eb['faces'].items():
     fa=ea['faces'][side]
     if fb['texture'] is None:assert fa['texture'] is None;continue
     ta,tb=d['textures'][fa['texture']],od['textures'][fb['texture']];assert ta['source']==tb['source'];assert fa.get('rotation',0)==fb.get('rotation',0);expected=[v*128/(tb.get('uv_width',tb['width'])if i%2==0 else tb.get('uv_height',tb['height']))for i,v in enumerate(fb['uv'])];close(fa['uv'],expected,'N02 directed UV')
  compare_nodes(root,old);audit['body_instances']+=1

# Complete active ingredient routes have no scale compensator.
scale_fields=[];bp=[];rp=[]
for p in (I/'current/runtime/BP/entities').glob('*ingredients*json'):
 j=rd(p);assert 'minecraft:scale'not in j['minecraft:entity']['components'];bp.append(str(p.relative_to(H)))
for p in (R/'entity').glob('*ingredients*json'):
 d=rd(p)['minecraft:client_entity']['description'];assert 'scale'not in d.get('scripts',{});rp.append(str(p.relative_to(H)))
for p in list((R/'animations').glob('*ingredients*json'))+list((R/'models/entity').glob('runtime_*ingredients*json'))+list((R/'models/entity').glob('runtime_pressing*json')):
 def scan(v,path=''):
  if isinstance(v,dict):
   for k,x in v.items():
    if 'scale'in k:scale_fields.append([str(p),path+'/'+k])
    scan(x,path+'/'+k)
  if isinstance(v,list):
   for n,x in enumerate(v):scan(x,path+'/'+str(n))
 scan(rd(p))
assert not scale_fields
# Verify source first-card edge distances and actual current card edge distances in final mesh space.
D=rd(H/'scenes/pressing-card-upright.bbmodel');cards=[e for e in D['elements']if e['type']=='mesh'and e['_review']['index']==0];widths=[]
for e in cards:
 f=e['faces']['f0'];ps=np.array([e['vertices'][k]for k in f['vertices']]);widths.append({'kind':e['_review']['kind'],'edge_lengths':[float(np.linalg.norm(ps[(i+1)%4]-ps[i]))for i in range(4)]})
audit['route_checks']={'BP_helpers_checked':len(bp),'RP_helpers_checked':len(rp),'compensating_scale_fields':scale_fields,'pressing_card_final_directed_edges':widths,'pressing_ice_material':'Material.default -> entity_alphatest','barrel_ice_material':'Material.translucent -> entity_alphablend','source_ice_alpha':sorted(set(Image.open(V/'textures/block/ice.png').convert('RGBA').getchannel('A').get_flattened_data())),'native_ice_texture':'external inheritance, not validated; neutral Java-PNG control only'}
# Material/controller assertions are extracted from the active client descriptions.
brc=rd(R/'render_controllers/runtime_barrel_ingredients.render_controllers.json')['render_controllers']['controller.render.kt_runtime.barrel_ingredients'];prc=rd(R/'render_controllers/runtime_pressing_ingredients.render_controllers.json')['render_controllers']['controller.render.kt_runtime.pressing_ingredients'];assert "== 17" in brc['materials'][0]['*'];assert prc['materials']==[{'*':'Material.default'}]
assert rd(R/'entity/runtime_barrel_ingredients_0.entity.json')['minecraft:client_entity']['description']['materials']['translucent']=='entity_alphablend'
assert rd(R/'entity/runtime_pressing_tub_ingredients.entity.json')['minecraft:client_entity']['description']['materials']['default']=='entity_alphatest'
# Texture frame audit covers every 24-frame binding without asserting clock execution.
full=np.array(Image.open(S/'textures/item/ice_grape.png').convert('RGBA'),dtype=np.uint16);mismatch=[]
for tick in range(24):
 i=tick//2;a=full[i*16:(i+1)*16].copy();b=full[((i+1)%12)*16:((i+1)%12+1)*16];a[:,:,:3]=(a[:,:,:3]*(2-tick%2)+b[:,:,:3]*(tick%2))//2;native=np.array(Image.open(R/f'textures/kt_runtime/machine_ingredients/ice_grape/tick_{tick:02d}.png').convert('RGBA'))
 if not np.array_equal(a,native):mismatch.append(tick)
assert not mismatch;audit['animated_frame_pixel_check']={'ticks_checked':24,'RGB_interpolation_current_alpha':True,'mismatches':mismatch,'clock_executed':False}
(H/'independent-audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit,indent=2))
