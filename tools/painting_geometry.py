"""Current shared painting surfaces against pinned official Java resources.

Standard library only. Independently decodes Bedrock parseCube X reflection,
rotation signs and top/bottom UV endpoints; preserves per-vertex UV association.
Java blockstate rotations are clockwise around the block center. Native block
transformation rotations are read directly, including ceiling facing offsets.
No renderer, image library, exporter or historical inverse ledger is imported.
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'data/painting-source'
N = 'kaleidoscope_tavern:'
MODELS = {name: f'runtime/RP/models/entity/{name}.geo.json'
          for name in ('painting_base', 'painting_wall', 'painting_ceiling')}


def read(p):
    return json.loads(p.read_text(), parse_constant=lambda x: (_ for _ in ()).throw(AssertionError(x)))


def resource_paths(root=ROOT):
    names = read(root/SOURCE/'manifest.json')['consumers']
    return set(MODELS.values()) | {f'runtime/BP/blocks/{name}.json' for name in names}


def vector(v, length):
    assert len(v) == length and all(type(x) in (int, float) and math.isfinite(x) for x in v), v
    return list(v)


def rotate(point, angles):
    p = list(point)
    for angle, (a, b) in zip(vector(angles, 3), ((1, 2), (2, 0), (0, 1))):
        c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        p[a], p[b] = p[a]*c-p[b]*s, p[a]*s+p[b]*c
    return p


def faces(lo, hi, mapping):
    x, y, z = vector(lo, 3)
    X, Y, Z = vector(hi, 3)
    corners = {
        'north': [(X,Y,z),(x,Y,z),(x,y,z),(X,y,z)],
        'south': [(x,Y,Z),(X,Y,Z),(X,y,Z),(x,y,Z)],
        'east': [(X,Y,Z),(X,Y,z),(X,y,z),(X,y,Z)],
        'west': [(x,Y,z),(x,Y,Z),(x,y,Z),(x,y,z)],
        'up': [(x,Y,z),(X,Y,z),(X,Y,Z),(x,Y,Z)],
        'down': [(x,y,Z),(X,y,Z),(X,y,z),(x,y,z)],
    }
    assert set(mapping) == set(corners), 'Painting must retain all six faces'
    result = []
    for name, f in mapping.items():
        u, v, U, V = vector(f['uv'], 4)
        angle = f.get('rotation', 0)
        assert type(angle) in (int, float) and angle in (0, 90, 180, 270)
        uv = [(u,v),(U,v),(U,V),(u,V)]
        n = int(angle/90)
        if n: uv = uv[-n:] + uv[:-n]
        result.append(list(zip(corners[name], uv)))
    return result


def native_faces(document):
    assert len(document['minecraft:geometry']) == 1
    g = document['minecraft:geometry'][0]
    assert g['description']['texture_width'] == g['description']['texture_height'] == 16
    assert len(g['bones']) == 1
    bone = g['bones'][0]
    assert set(bone) == {'name', 'pivot', 'cubes'} and vector(bone['pivot'], 3) == [0,0,0]
    assert len(bone['cubes']) == 1
    cube = bone['cubes'][0]
    assert set(cube) == {'origin', 'size', 'uv'}, 'Unexpected cube deformation or transform'
    o, s = vector(cube['origin'], 3), vector(cube['size'], 3)
    lo = [-o[0]-s[0], o[1], o[2]]
    hi = [lo[i]+s[i] for i in range(3)]
    mapping = {}
    for name, f in cube['uv'].items():
        assert set(f) <= {'uv', 'uv_size', 'uv_rotation'}
        a, d = vector(f['uv'], 2), vector(f['uv_size'], 2)
        uv = a + [a[i]+d[i] for i in range(2)]
        if name in ('up', 'down'): uv = uv[2:] + uv[:2]
        mapping[name] = {'uv': uv, 'rotation': f.get('uv_rotation', 0)}
    return g['description']['identifier'], faces(lo, hi, mapping)


def canonical(surface, shift, angles):
    result = []
    for face in surface:
        vertices = [tuple(round(x, 7) for x in rotate(
            [p[i]+shift[i] for i in range(3)], angles)) + tuple(uv) for p, uv in face]
        # Starting corner is immaterial, but reversed winding is not.
        result.append(min(tuple(vertices[i:]+vertices[:i]) for i in range(4)))
    return sorted(result)


def check(root=ROOT):
    base = root/SOURCE
    manifest = read(base/'manifest.json')
    assert set(manifest['branches']) == {'forge', 'neoforge'}
    for name, source in manifest['files'].items():
        raw = (base/name).read_bytes()
        assert len(raw) == source['bytes'] and hashlib.sha256(raw).hexdigest() == source['sha256'], name
    model = read(base/'base.json')
    assert len(model['elements']) == 1
    cube = model['elements'][0]
    assert cube.get('rotation', {}).get('angle', 0) == 0
    java = faces(cube['from'], cube['to'], cube['faces'])
    variants = read(base/'tartaric_acid_painting.json')['variants']
    assert len(variants) == 24
    geometries = dict(native_faces(read(root/path)) for path in MODELS.values())
    names = manifest['consumers']
    assert len(names) == len(set(names)) == 14
    for branch in manifest['branches']:
        verified = manifest['consumer_source_verification'][branch]
        assert set(verified) == set(names)
        assert all(v['shared_parent_and_placement_verified'] is True for v in verified.values())
    consumers = set()
    for p in (root/'runtime/BP/blocks').glob('*.json'):
        d = read(p)['minecraft:block']
        routes = [d.get('components', {})] + [r['components'] for r in d.get('permutations', [])]
        if any(r.get('minecraft:geometry', {}).get('identifier') in geometries for r in routes):
            consumers.add(p.stem)
    assert consumers == set(names), ('Shared painting consumer coverage', consumers)
    count = 0
    for name in names:
        block = read(root/f'runtime/BP/blocks/{name}.json')['minecraft:block']
        assert block['description']['identifier'] == N+name
        assert block['description']['states'] == {N+'facing': [0,1,2,3], N+'attach_face': [0,1,2]}
        assert len(block['permutations']) == 12
        for attach, side in enumerate(('wall', 'floor', 'ceiling')):
            for facing, direction in enumerate(('north', 'east', 'south', 'west')):
                key = f'face={side},facing={direction},waterlogged=false'
                source = variants[key]
                assert source == variants[key.replace('false', 'true')]
                assert not source.get('uvlock', False)
                condition = f"q.block_state('{N}attach_face') == {attach} && q.block_state('{N}facing') == {facing}"
                matches = [r['components'] for r in block['permutations'] if r['condition'] == condition]
                assert len(matches) == 1, (name, condition)
                components = {**block['components'], **matches[0]}
                transform = components['minecraft:transformation']
                assert set(transform) == {'rotation'}
                gid = components['minecraft:geometry']['identifier']
                assert gid in geometries, (name, gid)
                expected = canonical(java, [-8,-8,-8], [-source.get('x',0), -source.get('y',0), 0])
                actual = canonical(geometries[gid], [0,-8,0], transform['rotation'])
                assert actual == expected, (name, side, direction, 'Painting source vertex/UV mismatch')
                count += 1
    return {'consumers': len(names), 'placement_cases': count, 'faces': count*6,
            'vertex_uv_pairs': count*24, 'source_branches': list(manifest['branches']),
            'engine_verified': False}


if __name__ == '__main__':
    print(json.dumps(check(), indent=2))
