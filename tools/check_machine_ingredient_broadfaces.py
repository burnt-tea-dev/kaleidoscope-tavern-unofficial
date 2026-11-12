"""Independent local broad-face texel oracle; not a world-frame/edge-shell claim.

Decode native cube X reflection and oriented face vertices independently of
the resource owner. Java generated north/south sample the same texel at the
same local X/Y. Hold the existing native south surface and machine poses fixed.
"""
import hashlib
import json
import math
import re
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'data/machine-ingredient-source'


def source_frames(root=ROOT):
    source = Path(root) / SOURCE
    manifest = json.loads((source / 'source.json').read_text())
    for name, record in manifest['files'].items():
        raw = (source / name).read_bytes()
        assert len(raw) == record['bytes'] and hashlib.sha256(raw).hexdigest() == record['sha256'], ('Ingredient source changed', name)
    for version in ('1.20.1', '1.21.1'):
        text = (source / f'{version}-ItemModelGenerator.bytecode.txt').read_text()
        # These literal array initializers are the two Java broad-face UVs.
        arrays = re.findall(r'newarray\s+float(.*?)invokespecial', text, re.S)[:2]
        values = [[0.0 if op == 'fconst_0' else float(value) for op, value in
                   re.findall(r'\d+: (fconst_0)|// float ([\d.]+)f', block)] for block in arrays]
        assert values == [[0, 0, 16, 16], [16, 0, 0, 16]], ('Java broad-face UV source changed', version)
    result = []
    assert len(manifest['items']) == len({r['id'] for r in manifest['items']}) == 57
    for row in manifest['items']:
        with Image.open(source / row['texture']) as image:
            sheet = image.convert('RGBA')
        assert sheet.size == (16, 16 * row['source_frame_count'])
        reference = next(iter(row['versions'].values()))
        assert hashlib.sha256(sheet.tobytes()).hexdigest() == reference['rgba_sha256'], ('Source sprite pixel identity changed', row['id'])
        assert all(model['parent'] in ('minecraft:item/generated', 'item/generated', 'minecraft:item/handheld', 'item/handheld')
                   and set(model['textures']) == {'layer0'} for model in row['models'].values()), ('Source is not a single generated sprite', row['id'])
        for index in range(row['source_frame_count']):
            result.append((row['id'], index, sheet.crop((0, index*16, 16, (index+1)*16))))
    assert len(result) == 68, 'Ingredient source-frame census changed'
    return result


def decoded(cube, face):
    x, y, z = cube['origin']; dx, dy, dz = cube['size']
    x = -x-dx; X, Y, Z = x+dx, y+dy, z+dz
    vertices = {'south': ((x, Y, Z), (X, Y, Z), (x, y, Z)),
                'north': ((X, Y, z), (x, Y, z), (X, y, z))}[face]
    uv = cube['uv'][face]
    return vertices, (*uv['uv'], *uv['uv_size'])


def texel(cube, face, x, y):
    (o, pu, pv), (u, v, du, dv) = decoded(cube, face)
    a, b = (x-o[0])/(pu[0]-o[0]), (y-o[1])/(pv[1]-o[1])
    return math.floor(u+a*du), math.floor(v+b*dv)


def normal(cube, face):
    (o, pu, pv), _ = decoded(cube, face)
    # Face winding is 0,2,3,1, not UV-coordinate order 0,1,2.
    a, b = [pv[i]-o[i] for i in range(3)], [pu[i]-o[i] for i in range(3)]
    n = [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
    length = math.sqrt(sum(v*v for v in n))
    return [round(v/length) for v in n]


def audit(cube, frames):
    assert set(cube['uv']) == {'north', 'south'}, 'This contract retains only two broad faces'
    assert normal(cube, 'north') == [0, 0, -1] and normal(cube, 'south') == [0, 0, 1], 'Face winding/normal changed'
    mismatches = alpha = visible = 0
    for _, _, frame in frames:
        for y in range(16):
            for x in range(16):
                p = (-4+(x+.5)/2, 4-(y+.5)/2)
                a = texel(cube, 'south', *p); b = texel(cube, 'north', *p)
                assert a == (x, y), 'Retained south face changed'
                assert all(0 <= v < 16 for v in b), 'Broad face samples outside sprite'
                mismatches += a != b
                pa, pb = frame.getpixel(a), frame.getpixel(b)
                alpha += pa[3] != pb[3]
                visible += pa != pb and bool(pa[3] or pb[3])
    return {'frames': len(frames), 'sampled_points': len(frames)*256,
            'texel_mismatches': mismatches, 'alpha_mismatches': alpha,
            'visible_rgba_mismatches': visible, 'normals': {'north': [0, 0, -1], 'south': [0, 0, 1]}}


def check(root=ROOT):
    root = Path(root); frames = source_frames(root); results = {}
    for name in ('runtime_pressing_card', 'runtime_barrel_ingredients_card'):
        doc = json.loads((root / f'runtime/RP/models/entity/{name}.geo.json').read_text())
        geometry = doc['minecraft:geometry'][0]
        cubes = [c for b in geometry['bones'] for c in b.get('cubes', [])]
        # Every slot is validated, without repeating 68 identical texture loops.
        assert all(c == cubes[0] for c in cubes), ('Card slot mismatch', name)
        results[name] = audit(cubes[0], frames)
        assert results[name]['texel_mismatches'] == 0, ('Generated broad faces disagree at the same local point', name, results[name])
    return {'items': 57, 'source_frames': len(frames), 'geometries': results,
            'alpha_edge_extrusion': False, 'world_frame_verified': False, 'client_verified': False}


if __name__ == '__main__':
    print(json.dumps(check(), indent=2))
