"""Glowflower faces and hidden-base crop against official Java, not old output.

The source fixtures retain exact upstream bytes and licenses. Match ordered
vertex/UV pairs independently of the repair owner. Keep the existing 0.125
opposing-sheet thickness; only the source-opaque base strip is discarded.
This is an asset contract, not a Minecraft rendering claim.
"""
import copy
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'data/glowflower-source'
GEOMETRIES = tuple(f'runtime/RP/models/entity/glowflower_brew_{n}.geo.json' for n in range(1, 5))
TEXTURE = 'runtime/RP/textures/kaleidoscope_tavern/block/brew/glowflower_brew.png'


def read(path): return json.loads(path.read_text())


def rotate(point, angles):
    p = list(point)
    for angle, (a, b) in zip(angles, ((1, 2), (2, 0), (0, 1))):
        c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        p[a], p[b] = p[a]*c-p[b]*s, p[a]*s+p[b]*c
    return p


def face_vertices(lo, hi, side, angle=0):
    x, y, z = lo
    X, Y, Z = hi
    result = []
    assert angle in (0, 90, 180, 270)
    for u, v in ((0, 0), (1, 0), (0, 1), (1, 1)):
        for _ in range(int(angle/90)): u, v = 1-v, u
        result.append({'east': [X, Y+(y-Y)*v, Z+(z-Z)*u],
                       'west': [x, Y+(y-Y)*v, z+(Z-z)*u],
                       'up': [x+(X-x)*u, Y, z+(Z-z)*v],
                       'down': [x+(X-x)*u, y, Z+(z-Z)*v],
                       'south': [x+(X-x)*u, Y+(y-Y)*v, Z],
                       'north': [X+(x-X)*u, Y+(y-Y)*v, z]}[side])
    return result


def signature(lo, hi, side, uv, origin, rotation, angle=0, offset=0):
    points = face_vertices(lo, hi, side, angle)
    a = [points[1][i]-points[0][i] for i in range(3)]
    b = [points[2][i]-points[0][i] for i in range(3)]
    cross = [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
    if sum(v*v for v in cross) < 1e-16: return None
    result = []
    for p, (u, v) in zip(points, ((0,0), (1,0), (0,1), (1,1))):
        p[1] += offset
        rotated = rotate([p[i]-origin[i] for i in range(3)], rotation)
        vertex = [rotated[i]+origin[i] for i in range(3)]
        result.append(tuple(round(x, 7) for x in vertex) +
                      (uv[0]+u*(uv[2]-uv[0]), uv[1]+v*(uv[3]-uv[1])))
    return tuple(result)


def source_faces(model, image, count):
    assert model['render_type'] == 'cutout'
    assert image.size == (16, 16)
    elements = copy.deepcopy(model['elements'])
    shells = 0
    for e in elements:
        if e['from'][1] != .1 or e['to'][1] != 11.1 or e['from'][0] <= e['to'][0]:
            continue
        bases = [q for q in elements if q['from'][1] == .1 and q['to'][1] == 1.1
                 and q.get('rotation') == e.get('rotation')
                 and sorted((q['from'][0],q['to'][0])) == sorted((e['from'][0],e['to'][0]))
                 and sorted((q['from'][2],q['to'][2])) == sorted((e['from'][2],e['to'][2]))]
        assert len(bases) == 1, 'Inward shell needs an authored covering base'
        assert set(e['faces']) == {'north','east','south','west'}
        assert set(bases[0]['faces']) == {'north','east','south','west','up','down'}
        # A closed opaque base also occludes the strip from oblique/top/bottom views.
        for f in bases[0]['faces'].values():
            assert f['texture'] == '#0'
            u, v, U, V = f['uv']
            assert all(image.getpixel((x,y))[3] == 255
                       for x in range(math.floor(min(u,U)),math.ceil(max(u,U)))
                       for y in range(math.floor(min(v,V)),math.ceil(max(v,V)))), 'Base is not fully opaque'
        for side, f in e['faces'].items():
            assert f['uv'] == [11,5,15,16] and f['texture'] == '#0'
            base = bases[0]['faces'][side]
            assert base['uv'] == [11,15,15,16] and base['texture'] == '#0'
            assert all(image.getpixel((x,15))[3] == 255 for x in range(11,15)), 'Base is not fully opaque'
            f['uv'][3] = 15
        e['from'][1] = 1.1
        shells += 1
    assert shells == count
    result = []
    for e in elements:
        r = e.get('rotation', {})
        assert not r.get('rescale')
        rotation = [0,0,0]
        rotation['xyz'.index(r.get('axis','y'))] = r.get('angle',0)
        origin = r.get('origin',[8,0,8])
        lo, hi = e['from'], e['to']
        for side, f in e['faces'].items():
            # Retain the established platform separation only on true source sheets.
            offset = (.0625 if side == 'up' else -.0625) if lo[1] == hi[1] and side in ('up','down') else 0
            value = signature(lo,hi,side,f['uv'],origin,rotation,f.get('rotation',0),offset)
            if value is not None: result.append(value)
    return Counter(result)


def native_faces(doc, count):
    assert len(doc['minecraft:geometry']) == 1
    geo = doc['minecraft:geometry'][0]
    d = geo['description']
    assert d['identifier'] == f'geometry.kt_assets_a8.glowflower_brew_{count}'
    assert d['texture_width'] == d['texture_height'] == 16
    assert len(geo['bones']) == 1
    bone = geo['bones'][0]
    assert set(bone) == {'name','pivot','cubes'} and bone['pivot'] == [0,0,0]
    result = []
    for c in bone['cubes']:
        assert set(c) <= {'origin','size','pivot','rotation','uv'}
        assert all(type(v) in (int,float) and math.isfinite(v) for key in ('origin','size','pivot','rotation') for v in c.get(key,[]))
        o, size = c['origin'], c['size']
        assert all(v >= 0 for v in size)
        lo = [-o[0]-size[0]+8,o[1],o[2]+8]
        hi = [lo[i]+size[i] for i in range(3)]
        p = c.get('pivot',[0,0,0]); origin = [-p[0]+8,p[1],p[2]+8]
        r = c.get('rotation',[0,0,0]); rotation = [-r[0],-r[1],r[2]]
        for side, f in c['uv'].items():
            assert set(f) <= {'uv','uv_size','uv_rotation'}
            uv = f['uv']+[f['uv'][i]+f['uv_size'][i] for i in range(2)]
            if side in ('up','down'): uv = uv[2:]+uv[:2]
            value = signature(lo,hi,side,uv,origin,rotation,f.get('uv_rotation',0))
            if value is not None: result.append(value)
    return Counter(result)


def runtime_sources(): return frozenset(GEOMETRIES)


def resource_paths():
    return set(runtime_sources()) | {TEXTURE, 'data/baseline-reconciliation.json',
        'data/launch-repair-reference.json', 'data/efficiency-repair-reference.json',
        'data/drink-surface-review.json'}


def check_current_ownership(root):
    owned = runtime_sources()
    ledger = read(root/'data/baseline-reconciliation.json')
    for section in ('files', 'reviewedFunctionalDeltas'):
        assert not owned & set(ledger.get(section, {})), 'Glowflower returned to a historical postimage'
    for section in ('reviewedFunctionalDeltaLayers', 'reviewedAssetDeltaLayers'):
        for layer in ledger.get(section, []):
            assert not owned & set(layer['files']), 'Glowflower returned to a reverse delta'
    for filename, label in [('launch-repair-reference.json', 'launch'),
                            ('efficiency-repair-reference.json', 'efficiency')]:
        ledger = read(root/'data'/filename)
        for section in ('reviewedChanges', 'newRuntimeFiles', 'removedRuntimeFiles'):
            assert not owned & set(ledger.get(section, {})), f'Glowflower returned to a historical {label} aggregate'
    ledger = read(root/'data/drink-surface-review.json')
    assert not owned & set(ledger['files']), 'Glowflower returned to a historical drink-surface hash guard'


def check(root=ROOT):
    from PIL import Image
    root = Path(root)
    check_current_ownership(root)
    fixture = root/SOURCE
    manifest = read(fixture/'manifest.json')
    assert set(manifest['branches']) == {'forge','neoforge'}
    for name, row in manifest['files'].items():
        data = (fixture/name).read_bytes()
        assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256'], name
    with Image.open(fixture/'glowflower_brew.png') as im: image = im.convert('RGBA')
    with Image.open(root/TEXTURE) as im:
        assert im.size == image.size and im.convert('RGBA').tobytes() == image.tobytes()
    face_count = 0
    for count, name in enumerate(GEOMETRIES, 1):
        expected = source_faces(read(fixture/f'count{count}.json'), image, count)
        actual = native_faces(read(root/name), count)
        assert actual == expected, (name, 'Source ordered vertex/UV mismatch', sum((expected-actual).values()), sum((actual-expected).values()))
        face_count += expected.total()
    return {'meshes':4, 'ordered_faces':face_count, 'vertex_uv_pairs':face_count*4,
            'cropped_occluded_shell_faces':40, 'removed_legacy_x_offsets':20,
            'retained_sheet_thickness':.125, 'source_texture_unchanged':True,
            'current_source_owner':True, 'historical_projection_rows':0, 'engine_accepted':False}


if __name__ == '__main__': print(json.dumps(check()))
