from pathlib import Path
import json, math, struct, re, ast, operator
import numpy as np
from scipy.spatial.transform import Rotation
from PIL import Image
H=Path(__file__).resolve().parent; I=H/'inputs'; R=I/'current/runtime/RP'; V=I/'mojang-1.20.1/assets/minecraft'; S=I/'forge/src/main/resources/assets/kaleidoscope_tavern'
rd=lambda p:json.loads(p.read_text())
f32=lambda n:struct.unpack('f',struct.pack('f',n))[0]
def trans(v):m=np.eye(4);m[:3,3]=v;return m

def rot(axis,d):m=np.eye(4);v=np.zeros(3);v['xyz'.index(axis)]=math.radians(d);m[:3,:3]=Rotation.from_rotvec(v).as_matrix();return m

def scl(n):return np.diag([n,n,n,1.])

def apply(m,p):return np.einsum('ij,kj->ki',m,np.column_stack([p,np.ones(len(p))]))[:,:3]

def close(actual,expected,label):
 a,b=np.array(actual),np.array(expected);error=float(np.max(np.abs(a-b))) if a.size else 0;bound=256*np.finfo(float).eps*max(1,float(np.max(np.abs(b))))
 assert error<=bound,(label,error,bound);return error

def signed64(x):return ((x+(1<<63))%(1<<64))-(1<<63)

def unsigned64(x):return x%(1<<64)

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
 target_name=next(b['name'] for b in geo['bones'] if b.get('cubes') and (a['machine']=='barrel' or b['name']==f'item_z_{idx}'))
 bones={b['name']:b for b in geo['bones']}; needed=set(); cursor=target_name
 while cursor is not None:
  needed.add(cursor); cursor=bones[cursor].get('parent')
 for b in geo['bones']:
  if b['name'] not in needed:continue
  name=b['name'];oldname=name;name=name;ap=anim.get(name,{});p=np.array(b.get('pivot',[0,0,0]))*[-1,1,1];r=np.array([expression(x,props)for x in ap.get('rotation',b.get('rotation',[0,0,0]))])*[-1,-1,1];pos=np.array([expression(x,props)for x in ap.get('position',[0,0,0])])*[-1,1,1]
  if b.get('parent') not in chain:parent=np.eye(4);pp=np.zeros(3)
  else:parent=chain[b['parent']];pp=piv[b['parent']]
  chain[oldname]=parent@trans(p-pp+pos)@rot('z',r[2])@rot('y',r[1])@rot('x',r[0]);piv[oldname]=p
  if b.get('cubes') and (a['machine']=='barrel' or b['name']==f'item_z_{idx}'):target=chain[oldname]@trans(-p);break
 return target

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
