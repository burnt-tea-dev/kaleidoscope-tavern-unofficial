"""Read-only quantitative first-visible and raw-JPEG comparisons, not engine rendering."""
import ast,base64,copy,hashlib,io,json,math,sys
from pathlib import Path
import numpy as np
from PIL import Image
O=Path(__file__).resolve().parent;B=O/'review/bottles';R=O/'review/inputs'
sys.path.insert(0,str(B));from audit_paths import load_manifest
manifest=load_manifest(B/'manifest.json');families=['glowflower_brew','luminous_bride','madame_shexiang','sunset_glow']
ref=R/'round3/compare_face_uv_ordered_all14.py';tree=ast.parse(ref.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='faces'],type_ignores=[]),str(ref),'exec'))
sys.path.insert(0,str(R/'source/tools'));from drink_surface_math import overlap
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def descendants(node):
 ids={node['uuid']}
 for ch in node['children']:
  ids.update(descendants(ch) if isinstance(ch,dict) else {ch})
 return ids
def subset(scene,node,off):
 ids=descendants(node);out=copy.deepcopy(scene);out['elements']=[e for e in out['elements'] if e['uuid'] in ids]
 for e in out['elements']:
  assert e['rotation'][0]==e['rotation'][2]==0
  for k in ['from','to','origin']:e[k]=[v-off[i] for i,v in enumerate(e[k])]
 for g in scene['groups']:
  if g['uuid'] in ids:assert g['rotation']==[0,0,0]
 return out
class Proxy:
 def __init__(self,j):self.j=j

def projected(fs):
 out=[]
 for f in fs:
  v=np.array(f['vertices']);normal=-np.cross(v[1]-v[0],v[2]-v[0]);normal/=np.linalg.norm(normal)
  if abs(normal[1])<.9999:continue
  f=copy.deepcopy(f);f.update(normal_y=float(normal[1]),y=float(v[0,1]),polygon=v[[0,1,3,2]][:,[0,2]].tolist());out.append(f)
 return out

def trace(j,xy,view):
 fs=projected(faces(Proxy(j)));hits=[];n=len(xy);depth=np.full(n,-np.inf);color=np.zeros((n,4),dtype=np.uint8);owner=np.full(n,-1);ties=np.zeros(n,int);tiecolors=np.zeros(n,int)
 textures=[np.array(Image.open(io.BytesIO(base64.b64decode(t['source'].split(',',1)[1]))).convert('RGBA')) for t in j['textures']]
 for fi,f in enumerate(fs):
  if f['normal_y']*view<0:continue
  v=np.array(f['vertices']);origin=v[0,[0,2]];basis=np.stack((v[1,[0,2]]-origin,v[2,[0,2]]-origin),axis=1)
  uv01=(xy-origin)@np.linalg.inv(basis).T;inside=np.all((uv01>=0)&(uv01<1),axis=1)
  ids=np.where(inside)[0]
  if not len(ids):continue
  uv=np.array(f['uv']);coords=uv[:2]+uv01[ids]*(uv[2:]-uv[:2]);tex=textures[j['elements'][f['element']]['faces'][f['face']]['texture']];px=np.floor(coords).astype(int);px[:,0]=px[:,0].clip(0,tex.shape[1]-1);px[:,1]=px[:,1].clip(0,tex.shape[0]-1);rgba=tex[px[:,1],px[:,0]];opaque=rgba[:,3]>0;ids=ids[opaque];rgba=rgba[opaque];z=f['y']*view
  hits.append({'face_index':fi,'ids':ids,'rgba':rgba,'depth':z});same=np.abs(depth[ids]-z)<1e-7;ties[ids[same]]+=1;tiecolors[ids[same]]+=np.any(color[ids[same]]!=rgba[same],axis=1)
  nearer=z>depth[ids]+1e-7;ni=ids[nearer];depth[ni]=z;color[ni]=rgba[nearer];owner[ni]=fi;ties[ni]=0;tiecolors[ni]=0
 return {'depth':depth,'color':color,'owner':owner,'ties':ties,'tiecolors':tiecolors,'faces':fs,'hits':hits}

results=[];internal=[];inputs={}
for family in manifest['families']:
 if family['name'] not in families:continue
 p=Path(family['scene']);assert sha(p)==family['scene_sha256'];s=json.loads(p.read_text());inputs[str(p)]=sha(p)
 for n,state in enumerate(family['states']):
  offx=(n-(len(family['states'])-1)/2)*22;a=subset(s,s['outliner'][n*2],[offx,0,-12]);b=subset(s,s['outliner'][n*2+1],[offx,0,12]);allv=np.array([f['vertices'] for f in faces(Proxy(a))]);lo=allv.min((0,1));hi=allv.max((0,1));xx,zz=np.meshgrid(np.arange(lo[0]-.1,hi[0]+.1,.125)+.037,np.arange(lo[2]-.1,hi[2]+.1,.125)+.053);xy=np.stack((xx.ravel(),zz.ravel()),axis=1)
  for view,label in [(1,'top'),(-1,'bottom')]:
   at=trace(a,xy,view);bt=trace(b,xy,view);changed=np.any(at['color']!=bt['color'],axis=1);common=np.isfinite(at['depth'])&np.isfinite(bt['depth']);both=np.isfinite(at['depth'])|np.isfinite(bt['depth']);candidate_checks=[]
   for k in np.where(changed)[0]:
    candidates=[]
    for hit in at['hits']:
     if abs(hit['depth']-at['depth'][k])<1e-7:
      wh=np.where(hit['ids']==k)[0]
      if len(wh):
       face=at['faces'][hit['face_index']];candidates.append({'element':face['element'],'face':face['face'],'rgba':hit['rgba'][wh[0]].tolist()})
    candidate_checks.append({'xz':xy[k].tolist(),'source_front_candidates':candidates,'native_rgba':bt['color'][k].tolist(),'native_matches_source_tie_member':any(c['rgba']==bt['color'][k].tolist() for c in candidates)})
   results.append({'family':family['name'],'count':state['count'],'view':label,'rays':len(xy),'covered_union_rays':int(both.sum()),'different_rgba_rays':int(changed.sum()),'different_silhouette_rays':int((np.isfinite(at['depth'])!=np.isfinite(bt['depth'])).sum()),'different_front_depth_rays':int((abs(at['depth'][common]-bt['depth'][common])>1e-7).sum()),'source_visible_depth_ties':int((at['ties']>0).sum()),'source_visible_ties_different_rgba':int((at['tiecolors']>0).sum()),'native_visible_depth_ties':int((bt['ties']>0).sum()),'source_tie_candidate_checks':candidate_checks,'changed_examples':[{'xz':xy[k].tolist(),'source_rgba':at['color'][k].tolist(),'native_rgba':bt['color'][k].tolist()} for k in np.where(changed)[0][:4]]})
  if True:
   fs=projected(faces(Proxy(a)))
   for i,f in enumerate(fs):
    for g in fs[i+1:]:
     if abs(f['y']-g['y'])<1e-8 and f['normal_y']*g['normal_y']>.999:
      area=overlap(f['polygon'],g['polygon'])
      if area>1e-8:internal.append({'family':family['name'],'count':state['count'],'faces':[[f['element'],f['face']],[g['element'],g['face']]],'y':f['y'],'overlap_area':area,'uv':[f['uv'],g['uv']]})
  for key in ['java_model','java_texture','canonical_geometry','canonical_texture']:
   p=Path(state[key]);assert sha(p)==manifest['inputs'][str(p)]['sha256'];inputs[str(p)]=sha(p)

# Raw JPEG analysis never creates or substitutes screenshots.
raw=[]
for name in families:
 for view in ['top','bottom']:
  p=B/'evidence'/f'{name}-{view}.jpg';inputs[str(p)]=sha(p);im=np.array(Image.open(p)).astype(int);a=im[340:510,300:1100];b=im[580:750,300:1100];diff=abs(a-b);mx=diff.max(2);ys,xs=np.where(mx>20);raw.append({'family':name,'view':view,'rect_source_or_native_upper':[300,340,1100,510],'paired_rect_lower':[300,580,1100,750],'upper_identity':'Java' if view=='top' else 'Canonical','translation_px':[0,240],'mean_absolute_channel_difference':float(diff.mean()),'max_channel_difference':int(diff.max()),'exact_pixel_percent':float(np.mean(mx==0)*100),'pixels_over_20':len(ys),'dominant_rows_over_20':sorted([[int(y+340),int(n)] for y,n in zip(*np.unique(ys,return_counts=True))],key=lambda p:-p[1])[:8]})
# Explicit bottle regions for Madame, preserving view-dependent z row ordering.
centers_top=[(352,430),(532,430),(612,430),(792,390),(752,470),(832,470),(972,390),(1052,390),(972,470),(1052,470)]
centers_bottom=[(352,430),(532,430),(612,430),(792,470),(752,390),(832,390),(972,470),(1052,470),(972,390),(1052,390)]
madame=[]
for view,centers in [('top',centers_top),('bottom',centers_bottom)]:
 im=np.array(Image.open(B/'evidence'/f'madame_shexiang-{view}.jpg')).astype(int)
 for i,(x,y) in enumerate(centers):
  a=im[y-29:y+29,x-29:x+29];b=im[y+211:y+269,x-29:x+29];d=abs(a-b);madame.append({'view':view,'bottle_ordinal':i+1,'center_upper':[x,y],'interior_size':[58,58],'mean_absolute_channel_difference':float(d.mean()),'max_channel_difference':int(d.max()),'exact_pixel_percent':float(np.mean(d.max(2)==0)*100)})
count1=np.array(Image.open(B/'evidence/madame_shexiang-top.jpg'));aa=count1[400:460,322:382];bb=count1[640:700,322:382];assert np.array_equal(aa,bb)
# Exhaustive first-visible crop equality for decisive example, not just face equality.
proof={'rect_java':[322,400,382,460],'rect_native':[322,640,382,700],'decoded_rgb_sha256':hashlib.sha256(aa.tobytes()).hexdigest(),'native_decoded_rgb_sha256':hashlib.sha256(bb.tobytes()).hexdigest(),'exactly_equal':True,'pixels':3600}
out={'method':'Read-only geometric top/bottom ray queries at fixed non-boundary grid spacing0.125 model units. Uses exact UV-parametric corners, texture alpha, front-side winding and first depth. This is analytical geometry, not a Minecraft render. Screenshot metrics read original JPEG bytes only.','state_views':results,'source_coplanar_same_facing_horizontal_pairs':internal,'raw_jpeg_row_metrics':raw,'madame_interior_regions':madame,'madame_count1_top_exact_rgb_proof':proof,'inputs':inputs,'limits':['No synthetic render or substituted screenshot.','No Minecraft engine, source Java render-order or client shader acceptance.','JPEG/raster edge differences are not claimed to have one fully proven GPU cause.','Grid queries exclude exact mathematical boundary rays; first-visible reasoning is additionally source-backed.']}
binding_checks=[]
for family in manifest['families']:
 if family['name'] not in families:continue
 st=family['states'][0];p=Path(st['java_texture']);im=Image.open(p).convert('RGBA');binding_checks.append({'family':family['name'],'counts':[z['count'] for z in family['states']],'png_dimensions':list(im.size),'alpha_values':sorted(set(im.getchannel('A').getdata())),'source_native_texture_bytes_equal':p.read_bytes()==Path(st['canonical_texture']).read_bytes(),'java_texture_mcmeta_exists':p.with_suffix('.png.mcmeta').exists(),'java_render_type':st['java_render_type'],'native_material':st['material'],'scene_render_sides':'front','scene_render_mode':'default'})
 for view in ['perspective','top','bottom']:
  p=B/'evidence'/(family['name']+'-'+view+'.jpg');out['inputs'][str(p)]=sha(p)
out['binding_checks']=binding_checks
extra=[]
for name,view,rect in [('madame_shexiang','bottom',[322,400,382,460]),('sunset_glow','bottom',[422,410,502,450])]:
 im=np.array(Image.open(B/'evidence'/f'{name}-{view}.jpg'));x0,y0,x1,y1=rect;aa=im[y0:y1,x0:x1];bb=im[y0+240:y1+240,x0:x1];assert np.array_equal(aa,bb);extra.append({'family':name,'view':view,'upper_identity':'Canonical','upper_rect':rect,'lower_rect':[x0,y0+240,x1,y1+240],'exactly_equal':True,'decoded_rgb_sha256':hashlib.sha256(aa.tobytes()).hexdigest()})
out['additional_exact_rgb_proofs']=extra
def relative_paths(value):
 if isinstance(value,dict):return {relative_paths(k):relative_paths(v) for k,v in value.items()}
 if isinstance(value,list):return [relative_paths(v) for v in value]
 if isinstance(value,str) and value.startswith(str(O)+'/'):return value[len(str(O))+1:]
 return value
report=O/'rerun/surface-analysis.json';report.parent.mkdir(parents=True,exist_ok=True)
report.write_text(json.dumps(relative_paths(out),indent=2)+'\n')
for r in results:print(r['family'],r['count'],r['view'],'rays',r['covered_union_rays'],'differentRGBA',r['different_rgba_rays'],'differentDepth',r['different_front_depth_rays'],'visibleTies',r['source_visible_depth_ties'])
print('Madame proof',proof)
print('Madame interiors',[(r['view'],r['bottle_ordinal'],r['max_channel_difference'],round(r['exact_pixel_percent'],2)) for r in madame])
print('coplanar',internal)
