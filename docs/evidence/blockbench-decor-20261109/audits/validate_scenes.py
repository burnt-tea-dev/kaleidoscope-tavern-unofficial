"""Independent structural and ordered UV-corner audit, not rendered acceptance."""
from pathlib import Path
from types import SimpleNamespace
from collections import Counter
import ast, base64, copy, hashlib, io, json, math
import numpy as np
from scipy.optimize import linear_sum_assignment
from PIL import Image

H = Path(__file__).resolve().parent
from portable_context import mapped_manifest
M = mapped_manifest(H / 'manifest.json')
ref = H.parent / 'tavern-visual-review-20261108/round3/compare_face_uv_ordered_all14.py'
tree = ast.parse(ref.read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('faces', 'distance')], type_ignores=[]), str(ref), 'exec'))
checks = {'input_hashes': 0, 'scene_hashes': 0, 'embedded_textures': 0, 'elements': 0, 'textured_faces': 0,
          'uuid_references': True, 'no_external_textures': True, 'gui_reviewed': False}
for p, r in M['inputs'].items():
    b = Path(p).read_bytes()
    assert len(b) == r['bytes'] and hashlib.sha256(b).hexdigest() == r['sha256'], p
    checks['input_hashes'] += 1

out = []
for row in M['scenes']:
    b = Path(row['file']).read_bytes()
    assert hashlib.sha256(b).hexdigest() == row['sha256']
    checks['scene_hashes'] += 1
    doc = json.loads(b)
    assert doc['meta']['model_format'] == 'free'
    ids = [o['uuid'] for key in ('elements', 'groups', 'textures') for o in doc[key]]
    assert len(ids) == len(set(ids))
    groups, elements = {g['uuid']: g for g in doc['groups']}, {e['uuid']: e for e in doc['elements']}
    seen = []
    def walk(nodes):
        for n in nodes:
            if isinstance(n, str):
                assert n in elements
                seen.append(n)
            else:
                assert n['uuid'] in groups
                assert groups[n['uuid']]['rotation'] == [0, 0, 0]
                walk(n['children'])
    walk(doc['outliner'])
    assert len(seen) == len(elements) and set(seen) == set(elements)
    images = {}
    for i, tex in enumerate(doc['textures']):
        assert tex['source'].startswith('data:image/png;base64,')
        image = Image.open(io.BytesIO(base64.b64decode(tex['source'].split(',', 1)[1]))).convert('RGBA')
        assert image.size == (tex['width'], tex['height']) == (tex['uv_width'], tex['uv_height'])
        images[i] = image
        checks['embedded_textures'] += 1
    for e in doc['elements']:
        assert all(math.isfinite(v) for key in ('from', 'to', 'origin', 'rotation') for v in e[key])
        assert isinstance(e['shade'], bool)
        checks['elements'] += 1
        for f in e['faces'].values():
            assert all(math.isfinite(v) for v in f['uv'])
            if f['texture'] is not None:
                assert f['texture'] in images
                checks['textured_faces'] += 1
    cursor = 0
    for case in [c for c in M['cases'] if c['scene'] == Path(row['file']).name]:
        counts = [case['audit']['source_elements'], case['audit']['native_cubes']]
        arrays = []
        for count, off in zip(counts, (case['source_world_offset'], case['native_world_offset'])):
            a = copy.deepcopy(doc['elements'][cursor:cursor + count])
            cursor += count
            for e in a:
                for key in ('from', 'to', 'origin'):
                    e[key] = [e[key][k] - off[k] for k in range(3)]
            arrays.append(a)
        af, bf = [faces(SimpleNamespace(j={'elements': a})) for a in arrays]
        cost = np.array([[distance(a, b) if np.allclose(a['uv'], b['uv'], atol=1e-9, rtol=0) else 1e6 for b in bf] for a in af])
        rows, cols = linear_sum_assignment(cost)
        pairs = []
        for ai, bi in zip(rows, cols):
            a, b = af[ai], bf[bi]
            d = np.array(b['vertices']) - np.array(a['vertices'])
            delta = float(distance(a, b))
            uv = bool(np.allclose(a['uv'], b['uv'], atol=1e-9, rtol=0))
            je, ne = arrays[0][a['element']], arrays[1][b['element']]
            shade_equal = je['shade'] == ne['shade']
            classification = 'exact' if delta < 1e-6 and uv else 'unclassified difference'
            if uv and delta > 1e-6 and np.max(np.abs(d-d[0])) < 1e-6:
                rx, ry, rz = np.radians(je['rotation'])
                X = np.array([[1,0,0],[0,np.cos(rx),-np.sin(rx)],[0,np.sin(rx),np.cos(rx)]])
                Y = np.array([[np.cos(ry),0,np.sin(ry)],[0,1,0],[-np.sin(ry),0,np.cos(ry)]])
                Z = np.array([[np.cos(rz),-np.sin(rz),0],[np.sin(rz),np.cos(rz),0],[0,0,1]])
                local = (Z@Y@X).T@d[0]
                axis = {'north':2,'south':2,'east':0,'west':0,'up':1,'down':1}[a['face']]
                if abs(je['to'][axis] - je['from'][axis]) < 1e-7 and abs(abs(local[axis]) - .08) < 1e-6 and max(abs(local[k]) for k in range(3) if k != axis) < 1e-6:
                    classification = 'observed symmetric 0.16 native plant thickness; not exact source geometry'
            at, bt = je['faces'][a['face']]['texture'], ne['faces'][b['face']]['texture']
            pixel_equal = images[at].size == images[bt].size and images[at].tobytes() == images[bt].tobytes()
            pairs.append({'source_element': a['element'], 'source_face': a['face'], 'native_cube': b['element'], 'native_face': b['face'],
                          'uv_equal': uv, 'shade_equal': shade_equal, 'texture_pixels_equal': pixel_equal,
                          'maximum_vertex_delta': delta, 'classification': classification})
        unmatched_a = [a for i,a in enumerate(af) if i not in set(rows)]
        unmatched_b = [b for i,b in enumerate(bf) if i not in set(cols)]
        out.append({'label': case['label'], 'scene': case['scene'], 'source_faces': len(af), 'native_faces': len(bf),
                    'face_bijection': len(rows) == len(af) == len(bf), 'pairs': pairs,
                    'unmatched_source_faces': unmatched_a, 'unmatched_native_faces': unmatched_b})
    assert cursor == len(doc['elements'])

summary = {'cases': len(out), 'paired_faces': sum(len(r['pairs']) for r in out),
           'classifications': dict(Counter(p['classification'] for r in out for p in r['pairs'])),
           'uv_mismatches': sum(not p['uv_equal'] for r in out for p in r['pairs']),
           'shade_mismatches': sum(not p['shade_equal'] for r in out for p in r['pairs']),
           'texture_pixel_mismatches': sum(not p['texture_pixels_equal'] for r in out for p in r['pairs']),
           'unmatched_source_faces': sum(len(r['unmatched_source_faces']) for r in out),
           'unmatched_native_faces': sum(len(r['unmatched_native_faces']) for r in out)}
(H.parent / 'rerun' / 'ordered-face-audit.json').write_text(json.dumps({'method': 'Blockbench 5.2.2 UVToLocal signed dimensions and quarter-turn UV corners; restricted one-to-one UV match. Numeric tolerance 1e-6 only. Source zero-plane vs native thickness is identified separately, not accepted as equivalence.', 'reference': str(ref), 'reference_sha256': hashlib.sha256(ref.read_bytes()).hexdigest(), 'summary': summary, 'cases': out}, indent=2)+'\n')
(H.parent / 'rerun' / 'structural-validation.json').write_text(json.dumps(checks, indent=2)+'\n')
print(json.dumps({'structure': checks, 'ordered_faces': summary}, indent=2))
