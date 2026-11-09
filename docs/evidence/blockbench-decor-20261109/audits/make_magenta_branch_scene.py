"""Keep the genuine source branch divergence visible instead of averaging it away."""
from pathlib import Path
import ast, copy, hashlib, json
import numpy as np
from scipy.optimize import linear_sum_assignment
import review_codec as C
H = Path(__file__).resolve().parent
from portable_context import mapped_manifest
M = mapped_manifest(H / 'manifest.json')
case = next(c for c in M['cases'] if c['block'] == 'light_magenta')
forge = Path(case['source_model'])
jar = H / 'verified-jar-assets/assets/kaleidoscope_tavern/models/block/deco/string_lights/magenta.json'
texture = forge.parents[4] / 'textures/block/deco/string_lights/magenta.png'
native_geometry = Path(case['binding']['geometry'])
native_texture = Path(case['binding']['materials']['*']['_path'])
assert texture.is_file()
f, n = C.read(forge), C.read(jar)
signature = lambda e: json.dumps({k:v for k,v in e.items() if k != 'faces'}, sort_keys=True)
F, N = {signature(e):e for e in f['elements']}, {signature(e):e for e in n['elements']}
assert len(F) == len(N) == 19 and F.keys() == N.keys()
removed = []
for key in F:
    a, b = F[key], N[key]
    if a['faces'] != b['faces']:
        assert set(a['faces']) - set(b['faces']) == {'down'}
        assert {s:v for s,v in a['faces'].items() if s != 'down'} == b['faces']
        removed.append({'from': a['from'], 'to': a['to'], 'rotation': a.get('rotation'), 'removed_face': a['faces']['down']})
assert len(removed) == 12
assert {k:v for k,v in f.items() if k != 'elements'} == {k:v for k,v in n.items() if k != 'elements'}
scene = C.Scene('Magenta source divergence | Forge -X / Native centre / NeoForge JAR +X')
scene.java(forge, texture, [-30, 0, 0]); scene.j['groups'][-1]['name'] = 'Forge c4ec1880 | world X=-30'
first = len(scene.j['elements'])
scene.bedrock(native_geometry, native_texture, [0, 0, 0], name='Native 0.6.212 | world X=0')
cube_index = first
for bone in C.read(native_geometry)['minecraft:geometry'][0]['bones']:
    for cube in bone.get('cubes', []):
        shades = {case['binding']['materials'][face.get('material_instance', '*')].get('face_dimming', True) for face in cube['uv'].values()}
        assert len(shades) == 1
        scene.j['elements'][cube_index]['shade'] = next(iter(shades)); cube_index += 1
scene.java(jar, texture, [30, 0, 0]); scene.j['groups'][-1]['name'] = 'NeoForge a1afba34 and verified actual JAR | world X=+30'
C.OUT = H / 'scenes'
# Preserve the captured scene bytes: no scene.save() during replay.
ref = H.parent / 'tavern-visual-review-20261108/round3/compare_face_uv_ordered_all14.py'
tree = ast.parse(ref.read_text())
exec(compile(ast.Module(body=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in ('faces','distance')], type_ignores=[]), str(ref), 'exec'))
a, b = C.Scene('Neo'), C.Scene('Native')
a.java(jar, texture); b.bedrock(native_geometry, native_texture)
af, bf = faces(a), faces(b)
cost = np.array([[distance(x,y) if np.allclose(x['uv'],y['uv'],rtol=0,atol=1e-9) else 1e6 for y in bf] for x in af])
rows, cols = linear_sum_assignment(cost)
assert len(rows) == len(af) and len(bf) - len(af) == 12
assert max(cost[i,j] for i,j in zip(rows,cols)) < 1e-6
extra = [face for i,face in enumerate(bf) if i not in set(cols)]
scene_path = C.OUT / 'magenta-three-way-branch-difference.bbmodel'
result = {'status': 'Source branch divergence, not an automatically classified runtime defect',
          'scene': str(scene_path), 'scene_sha256': hashlib.sha256(scene_path.read_bytes()).hexdigest(), 'gui_reviewed': False,
          'finding': 'Native retains Forge petal backs. NeoForge, the actual locked 1.2.0 JAR, and matching-path unpublished 26.1.2 omit 12 down faces; other element geometry and remaining face mappings agree. Element order also differs.',
          'elements_each_author_model': 19, 'removed_author_back_faces': removed,
          'neo_faces': len(af), 'native_faces': len(bf), 'all_neo_faces_exact_ordered_uv_match_native': True,
          'additional_native_faces': extra,
          'layout': 'Forge X=-30, native X=0, NeoForge/JAR X=+30. Default perspective displays them in reverse screen order. Check underside/back as well as front.',
          'input_sha256': {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (forge,jar,texture,native_geometry,native_texture)}}
(H.parent / 'rerun' / 'magenta-branch-difference.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('removed_author_back_faces','additional_native_faces','input_sha256')},indent=2))
