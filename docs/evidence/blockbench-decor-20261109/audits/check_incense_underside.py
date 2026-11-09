"""Static first-hit underside rays. No GPU or Minecraft-engine claim."""
from pathlib import Path
from types import SimpleNamespace
import ast, base64, copy, hashlib, io, json
import numpy as np
from PIL import Image
H = Path(__file__).resolve().parent
from portable_context import mapped_manifest
M = mapped_manifest(H / 'manifest.json')
ref = H.parent / 'tavern-visual-review-20261108/round3/compare_face_uv_ordered_all14.py'
tree = ast.parse(ref.read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name == 'faces'], type_ignores=[]), str(ref), 'exec'))
result = []
for case in M['cases']:
    if not case['block'].endswith('_incense'):
        continue
    scene = json.loads((H / 'scenes' / case['scene']).read_text())
    cursor = 0
    for c in M['cases']:
        if c['scene'] != case['scene']:
            continue
        if c['label'] == case['label']:
            break
        cursor += c['audit']['source_elements'] + c['audit']['native_cubes']
    images = {i:Image.open(io.BytesIO(base64.b64decode(t['source'].split(',',1)[1]))).convert('RGBA') for i,t in enumerate(scene['textures'])}
    all_faces = []
    for count, offset in zip([case['audit']['source_elements'],case['audit']['native_cubes']], [case['source_world_offset'],case['native_world_offset']]):
        es = copy.deepcopy(scene['elements'][cursor:cursor+count]); cursor += count
        for e in es:
            for key in ('from','to','origin'):
                e[key] = [e[key][i] - offset[i] for i in range(3)]
        fs = faces(SimpleNamespace(j={'elements':es}))
        for f in fs:
            f['texture_index'] = es[f['element']]['faces'][f['face']]['texture']
        all_faces.append(fs)
    def first_hit(fs, x, z):
        hits = []
        for f in fs:
            p = np.array(f['vertices']); U,V = p[1]-p[0],p[2]-p[0]
            normal = np.cross(V,U)  # BB triangle winding 0,2,1.
            if normal[1] >= -1e-8:
                continue
            matrix = np.array([[U[0],V[0]],[U[2],V[2]]])
            if abs(np.linalg.det(matrix)) < 1e-8:
                continue
            u,v = np.linalg.solve(matrix,np.array([x,z])-p[0,[0,2]])
            if not (0 <= u < 1 and 0 <= v < 1):
                continue
            uv = f['uv']; tu,tv = uv[0]+u*(uv[2]-uv[0]),uv[1]+v*(uv[3]-uv[1])
            im = images[f['texture_index']]
            pixel = im.getpixel((int(np.floor(tu)) % im.width,int(np.floor(tv)) % im.height))
            if pixel[3] < 128:
                continue
            point = p[0] + u*U + v*V
            hits.append({'element':f['element'],'face':f['face'],'y':round(float(point[1]),6),'uv_sample':[float(tu),float(tv)],'rgba':pixel})
        return sorted(hits,key=lambda h:h['y'])[0] if hits else None
    rays = []
    for x in [-1.5,-.5,.5,1.5]:
        for z in [-1.5,-.5,.5,1.5]:
            source,native = [first_hit(fs,x,z) for fs in all_faces]
            assert source and source['element'] == 3 and source['face'] == 'down' and source['y'] == 1
            assert native and native['element'] == 1 and native['face'] == 'down' and native['y'] == 4
            rays.append({'x':x,'z':z,'source_first_opaque':source,'native_first_opaque':native,'rgba_equal':source['rgba']==native['rgba']})
    result.append({'label':case['label'],'scene':case['scene'],'rays':rays})
tool = H.parent / 'tavern-visual-review-20261108/source/tools/check_incense_surfaces.py'
out = {'status':'Specific pending BOTTOM GUI review candidate, not a confirmed native-engine defect',
       'finding':'The 16 omitted source cube3/down faces are not occluded by an opaque base at their central 4x4 footprint. Base centre is alpha 0. Under culled front-face geometry, source rays first hit fill/down at y=1; native rays hit lid/down at y=4. This is not established as a hidden-face equivalence.',
       'method':'Independent UV-parametric faces and front-face winding; vertical first opaque texel rays at 16 central points per case, alpha cutoff 128. No lighting, GPU, texture filtering, or engine acceptance.',
       'cases':result,'summary':{'cases':len(result),'rays':sum(len(r['rays']) for r in result),'depth_differences':sum(len(r['rays']) for r in result),'rgba_differences':sum(not q['rgba_equal'] for r in result for q in r['rays']),'gui_reviewed':False},
       'existing_contract':{'path':str(tool),'sha256':hashlib.sha256(tool.read_bytes()).hexdigest(),'result':{'incenseTypes':8,'sharedModels':2,'culledCutoutSides':True,'opaqueInterCubeOverlaps':0,'clientRenderingTested':False},'limitation':'Its hidden-fill-bottom assertion does not prove source underside occlusion; keep this bounded candidate distinct from its passing overlap checks.'}}
(H.parent / 'rerun' / 'incense-underside-candidate.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out['summary'],indent=2))
