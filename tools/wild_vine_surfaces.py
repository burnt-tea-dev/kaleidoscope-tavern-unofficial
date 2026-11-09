"""Java-source surface checks for the current shared cultivation geometry.

This reads resources, not a historical converter or inverse runtime ledger.
Rotations are checked independently as complex numbers. Slab center planes and
physical thickness are separate assertions; editor/native rendering is not run.
"""
import cmath
import hashlib
import itertools
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEOMETRY = 'runtime/RP/models/entity/wild_grapevine.geo.json'
IDENTIFIER = 'geometry.kt_assets_a2.wild_grapevine'
NAMES = ('wild_grapevine', 'wild_grapevine_plant')
FIXTURES = 'data/wild-vine-surfaces'
THICKNESS = .16  # Explicit centered Bedrock adaptation, not a renderer minimum.


def _read(path):
    return json.loads(path.read_text())


def _sample(lo, hi, face, u, v):
    if face == 'north':
        return [hi[0] + (lo[0] - hi[0]) * u, hi[1] + (lo[1] - hi[1]) * v, lo[2]]
    if face == 'south':
        return [lo[0] + (hi[0] - lo[0]) * u, hi[1] + (lo[1] - hi[1]) * v, hi[2]]
    if face == 'west':
        return [lo[0], hi[1] + (lo[1] - hi[1]) * v, lo[2] + (hi[2] - lo[2]) * u]
    if face == 'east':
        return [hi[0], hi[1] + (lo[1] - hi[1]) * v, hi[2] + (lo[2] - hi[2]) * u]
    raise AssertionError('Unexpected cross face: ' + face)


def _rotate(point, pivot, angle):
    q = complex(point[0] - pivot[0], point[2] - pivot[2]) * cmath.exp(-1j * math.radians(angle))
    return [pivot[0] + q.real, point[1], pivot[2] + q.imag]


def check_geometry(document, source):
    assert set(document) == {'format_version', 'minecraft:geometry'}
    assert document['format_version'] == '1.21.0'
    assert len(document['minecraft:geometry']) == 1
    geometry = document['minecraft:geometry'][0]
    assert set(geometry) == {'description', 'bones'}
    assert geometry['description'] == {
        'identifier': IDENTIFIER, 'texture_width': 16, 'texture_height': 16,
        'visible_bounds_width': 2, 'visible_bounds_height': 2,
        'visible_bounds_offset': [0, .5, 0]}, 'Shared wild-vine identity/bounds changed'
    assert len(geometry['bones']) == 1
    bone = geometry['bones'][0]
    assert {k: v for k, v in bone.items() if k != 'cubes'} == {'name': 'root', 'pivot': [0, 0, 0]}
    assert source['ambientocclusion'] is False
    assert len(bone['cubes']) == len(source['elements']) == 2
    samples = [(0, 0), (1, 0), (1, 1), (0, 1)]
    samples += [((u + .5) / 16, (v + .5) / 16) for u, v in itertools.product(range(16), repeat=2)]
    maximum = 0
    faces = 0
    for cube, element in zip(bone['cubes'], source['elements']):
        assert set(cube) == {'origin', 'size', 'pivot', 'rotation', 'uv'}
        assert isinstance(cube['uv'], dict) and set(cube['uv']) == set(element['faces']), 'Directed cross faces changed'
        assert cube['rotation'][0] == cube['rotation'][2] == 0
        assert element['shade'] is False
        rotation = element['rotation']
        assert rotation['axis'] == 'y' and rotation['rescale'] is True
        flat_axes = [i for i in range(3) if element['from'][i] == element['to'][i]]
        assert len(flat_axes) == 1
        axis = flat_axes[0]
        assert cube['size'][axis] == THICKNESS, 'Undisclosed cross thickness change'
        # Bedrock model X is reflected relative to Java. Undo that reflection,
        # then compare UV-corresponding points in the same centered coordinates.
        low = [-cube['origin'][0] - cube['size'][0], cube['origin'][1], cube['origin'][2]]
        high = [low[i] + cube['size'][i] for i in range(3)]
        center = (low[axis] + high[axis]) / 2
        low[axis] = high[axis] = center
        pivot = [-cube['pivot'][0], cube['pivot'][1], cube['pivot'][2]]
        factor = 1 / math.cos(math.radians(rotation['angle']))
        for face, original in element['faces'].items():
            native = cube['uv'][face]
            uv = original['uv']
            assert original['texture'] == '#cross'
            assert native == {'uv': uv[:2], 'uv_size': [uv[2] - uv[0], uv[3] - uv[1]]}, 'Source face UV or wildcard material changed'
            for u, v in samples:
                point = _sample(element['from'], element['to'], face, u, v)
                for i in (0, 2):
                    point[i] = rotation['origin'][i] + (point[i] - rotation['origin'][i]) * factor
                java = _rotate(point, rotation['origin'], rotation['angle'])
                java[0] -= 8
                java[2] -= 8
                native_point = _rotate(_sample(low, high, face, u, v), pivot, -cube['rotation'][1])
                error = math.dist(java, native_point)
                assert error < 1e-7, ('Source cross position/rescale/orientation mismatch', face, error)
                maximum = max(maximum, error)
            faces += 1
    return {'directed_faces': faces, 'uv_corners': faces * 4, 'texel_centers': faces * 256,
            'maximum_center_plane_error': maximum, 'centered_slab_thickness': THICKNESS}


def _visual(components, name):
    geometry = {'identifier': IDENTIFIER}
    material = {'*': {'texture': 'kt_assets_a2_' + name, 'render_method': 'alpha_test_single_sided',
                      'ambient_occlusion': 0, 'face_dimming': False}}
    assert components['minecraft:geometry'] == geometry, ('Wild-vine world geometry hidden/disconnected', name)
    assert components['minecraft:material_instances'] == material, ('Wild-vine source cutout material changed', name)
    assert components['minecraft:item_visual'] == {'geometry': geometry, 'material_instances': material}, ('Wild-vine item route changed', name)
    assert 'minecraft:transformation' not in components, ('Unexpected source cross transform', name)


def check(root=ROOT, java_source=None):
    root = Path(root)
    fixtures = root / FIXTURES
    records = _read(fixtures / 'source.json')
    raw_parent = (fixtures / 'official-cross.json').read_bytes()
    assert hashlib.sha256(raw_parent).hexdigest() == records['official_parent']['sha256']
    source = json.loads(raw_parent)
    result = check_geometry(_read(root / GEOMETRY), source)
    terrain = _read(root / 'runtime/RP/textures/terrain_texture.json')['texture_data']
    for name in NAMES:
        for kind in ('model', 'blockstate'):
            local = name + '-' + kind + '.json'
            raw = (fixtures / local).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == records['files'][local]['sha256']
            if java_source is not None:
                # Git may check text resources out with CRLF; compare canonical LF.
                assert raw == (Path(java_source) / records['files'][local]['path']).read_bytes().replace(b'\r\n', b'\n')
        model = _read(fixtures / (name + '-model.json'))
        assert model == {'parent': 'minecraft:block/cross', 'render_type': 'minecraft:cutout',
                         'textures': {'cross': 'kaleidoscope_tavern:block/plant/' + name}}
        assert _read(fixtures / (name + '-blockstate.json')) == {'variants': {'': {'model': 'kaleidoscope_tavern:block/plant/' + name}}}
        record = records['files'][name + '.png']
        texture = (root / record['canonical_path']).read_bytes()
        assert hashlib.sha256(texture).hexdigest() == record['sha256'], 'Wild-vine source texture changed'
        if java_source is not None:
            assert texture == (Path(java_source) / record['path']).read_bytes()
        assert terrain['kt_assets_a2_' + name]['textures'] == 'textures/kaleidoscope_tavern/block/plant/' + name
        block = _read(root / ('runtime/BP/blocks/' + name + '.json'))['minecraft:block']
        components = block['components']
        _visual(components, name)
        for permutation in block.get('permutations', []):
            _visual({**components, **permutation['components']}, name)
    return result
