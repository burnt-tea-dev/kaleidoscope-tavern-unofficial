"""Audit all incense cutouts and source geometry; not a rendered-client test."""
import hashlib
import json
import math
from pathlib import Path
from drink_surface_math import conflicts, dot, faces

ROOT = Path(__file__).resolve().parents[1]
KINDS = ('butterfly', 'catnip', 'firefly', 'ginkgo', 'pine', 'sakura', 'snow', 'spore')

def runtime_sources():
    return frozenset({f'runtime/BP/blocks/{kind}_incense.json' for kind in KINDS}
                     | {f'runtime/RP/models/entity/incense_{state}.geo.json' for state in ('closed', 'open')})


def first_opaque_down(model, image, x, z, *, java):
    """An upward ray in the common rendered frame (Java X/Z centred at 8).

    Only unrotated horizontal down faces can meet this ray. The foliage has
    vertical front/back faces, so it contributes no downward-facing surface.
    Bedrock's mirrored X frame and reversed down UV endpoints are converted
    explicitly, independently of the source-face equality assertion below.
    This is point-sampled alpha geometry, not a Minecraft renderer.
    """
    nodes = model['elements'] if java else model['bones'][0]['cubes']
    hits = []
    for index, node in enumerate(nodes):
        face = node.get('faces' if java else 'uv', {}).get('down')
        if face is None:
            continue
        if java:
            lo, hi = node['from'], node['to']
            if hi[0] == lo[0] or hi[2] == lo[2]:
                continue  # Authored collapsed foliage edge caps have no area.
            assert 'rotation' not in node, 'Unexpected rotated horizontal source face'
            left, right, front, back = lo[0]-8, hi[0]-8, lo[2]-8, hi[2]-8
            y = lo[1]
            u0, v0, u1, v1 = [n * image.size[i % 2] / 16 for i, n in enumerate(face['uv'])]
        else:
            o, size = node['origin'], node['size']
            if size[0] == 0 or size[2] == 0:
                continue
            assert node.get('rotation', [0, 0, 0]) == [0, 0, 0], 'Unexpected rotated horizontal native face'
            left, right, front, back = -o[0]-size[0], -o[0], o[2], o[2]+size[2]
            y = o[1]
            u1, v1 = face['uv']; du, dv = face['uv_size']
            u0, v0 = u1+du, v1+dv
        if not (left <= x < right and front <= z < back):
            continue
        u, v = (x-left)/(right-left), (back-z)/(back-front)
        tu, tv = u0+u*(u1-u0), v0+v*(v1-v0)
        rgba = image.getpixel((math.floor(tu), math.floor(tv)))
        if rgba[3] >= 128:
            hits.append((y, index, rgba))
    return min(hits) if hits else None


def check_underside(source, geometry, image):
    rays = 0
    for x in (-1.5, -.5, .5, 1.5):
        for z in (-1.5, -.5, .5, 1.5):
            original = first_opaque_down(source, image, x, z, java=True)
            actual = first_opaque_down(geometry, image, x, z, java=False)
            assert original and original[:2] == (1, 3), 'Source fill bottom must be first opaque underside'
            assert actual == original, ('First-visible incense underside differs', x, z, original, actual)
            rays += 1
    return rays


def check(root=ROOT, java_source=None):
    from PIL import Image
    root = Path(root)
    read = lambda path: json.loads((root / path).read_text())
    provenance = read('data/incense-surfaces/source.json')
    for name, record in provenance['files'].items():
        assert hashlib.sha256((root / 'data/incense-surfaces' / name).read_bytes()).hexdigest() == record['sha256'], 'Pinned incense source fixture differs'
    geometries, sources = {}, {}
    underside_rays = 0
    for state in ('closed', 'open'):
        geo = read(f'runtime/RP/models/entity/incense_{state}.geo.json')['minecraft:geometry'][0]
        source = read(f'data/incense-surfaces/java-{state}.json')
        cubes = geo['bones'][0]['cubes']
        geometries[state], sources[state] = geo, source
        assert geo['description']['identifier'] == f'geometry.kt_assets_a13.incense_{state}'
        assert (geo['description']['texture_width'], geo['description']['texture_height']) == (32, 32)
        assert len(geo['bones']) == 1 and geo['bones'][0]['name'] == 'root'
        assert geo['bones'][0]['pivot'] == [0, 0, 0] and 'rotation' not in geo['bones'][0]
        assert len(cubes) == len(source['elements']) == 6
        # The four solid author elements retain every face, UV, and shade.
        # These current resources replace the old T158 hidden-bottom premise.
        for index, (cube, element) in enumerate(zip(cubes[:4], source['elements'][:4])):
            lo, hi = element['from'], element['to']
            assert cube['origin'] == [8-hi[0], lo[1], lo[2]-8], ('Source solid origin differs', state, index)
            assert cube['size'] == [b-a for a, b in zip(lo, hi)], ('Source solid size differs', state, index)
            expected = {}
            for side, face in element['faces'].items():
                u0, v0, u1, v1 = [n*2 for n in face['uv']]
                if side in ('up', 'down'):
                    u0, v0, u1, v1 = u1, v1, u0, v0
                expected[side] = {'uv': [u0, v0], 'uv_size': [u1-u0, v1-v0]}
                if not element.get('shade', True):
                    expected[side]['material_instance'] = 'unshaded'
            assert cube['uv'] == expected, ('Source solid faces/UV/shade differ', state, index)
            assert set(cube) == {'origin', 'size', 'uv'}, 'Unexpected solid transform or render override'
        for index, axis, visible_faces in [(4, 0, {'east', 'west'}), (5, 2, {'north', 'south'})]:
            cube, element = cubes[index], source['elements'][index]
            assert cube['size'][axis] == 0 and cube['origin'][axis] == 0, 'No thickened duplicate cutout layers'
            assert cube['size'][1] == element['to'][1] - element['from'][1] == 16
            assert cube['origin'][1] == element['from'][1]
            span_axis = 2 if axis == 0 else 0
            span = (element['to'][span_axis] - element['from'][span_axis]) * math.sqrt(2)
            assert abs(cube['size'][span_axis] - span) < 1e-6
            assert abs(cube['origin'][span_axis] + span / 2) < 1e-6
            assert cube['pivot'] == [0, element['rotation']['origin'][1], 0]
            assert cube['rotation'] == [0, -45, 0]
            assert set(cube['uv']) == visible_faces, 'No collapsed-UV edge caps'
            for face, uv in cube['uv'].items():
                original = element['faces'][face]['uv']
                assert uv == {'uv': [original[0]*2, original[1]*2],
                              'uv_size': [(original[2]-original[0])*2, (original[3]-original[1])*2],
                              'material_instance': 'foliage'}
            pair = [f for f in faces(geo) if f['cube'] == index]
            assert len(pair) == 2 and dot(pair[0]['normal'], pair[1]['normal']) < -.999999
            # Opposing front/back planes are only safe with culling. Each camera
            # direction admits at most one side; the material checks below are
            # essential and catch the previous double-sided rendering failure.
            for angle in (0, 20, 70, 110, 160, 200, 250, 290, 340):
                view = (math.cos(math.radians(angle)), .3, math.sin(math.radians(angle)))
                assert sum(dot(f['normal'], view) > 1e-6 for f in pair) == 1
        # Base-up/fill-down and lid-down/frame-up are opposite-facing contact
        # planes, not competing front faces under alpha_test_single_sided.
        # Their shared texture masks are checked below, including the transparent
        # base centre through which the source fill bottom is actually visible.
        assert conflicts(geo, two_sided=False) == [], 'Competing same-facing incense surfaces'
        overlaps = conflicts(geo, two_sided=True)
        assert [(a['cube'], a['face'], b['cube'], b['face']) for a,b,*_ in overlaps] == [(0, 'up', 3, 'down'), (1, 'down', 2, 'up')]
        assert cubes[2]['uv']['up'] == {'uv': [14.0, 6.0], 'uv_size': [-6.0, -6.0]}
    for kind in KINDS:
        block = read(f'runtime/BP/blocks/{kind}_incense.json')['minecraft:block']
        components = block['components']
        assert block['description']['identifier'] == f'kaleidoscope_tavern:{kind}_incense'
        assert block['description']['states']['kaleidoscope_tavern:open'] == [0, 1]
        assert len(block['permutations']) == 1
        assert block['permutations'][0]['condition'] == "q.block_state('kaleidoscope_tavern:open') == 1"
        # A matching permutation replaces whole components, not nested fields.
        # Validate what each state actually uses, including inherited components.
        effective = {'closed': components,
                     'open': {**components, **block['permutations'][0]['components']}}
        contexts = list(effective.values()) + [c['minecraft:item_visual'] for c in effective.values()]
        for context in contexts:
            materials = context.get('minecraft:material_instances', context.get('material_instances'))
            assert {v['render_method'] for v in materials.values()} == {'alpha_test_single_sided'}, (kind, 'Mixed render methods')
            foliage = materials['foliage']
            assert foliage['render_method'] == 'alpha_test_single_sided', (kind, 'Both cutout faces would render together')
            assert foliage['texture'] == materials['*']['texture']
            assert {k:v for k,v in foliage.items() if k!='render_method'} == {k:v for k,v in materials['*'].items() if k!='render_method'}
        # Current block lifecycle wiring stays protected after retiring the old
        # whole-file hash projection. Gameplay implementations are exercised by
        # the existing decoration/incense suites, not by these resource rays.
        lifecycle = {
            'kaleidoscope_tavern:incense': {},
            'kaleidoscope_tavern:natural_break': {'drop': f'kaleidoscope_tavern:{kind}_incense'},
            'minecraft:loot': 'loot_tables/empty.json',
            'minecraft:tick': {'interval_range': [20, 20], 'looping': True},
            'minecraft:redstone_consumer': {'min_power': 0, 'propagates_power': False},
            'minecraft:movable': {'movement_type': 'immovable'},
            'minecraft:collision_box': {'origin': [-3, 0, -3], 'size': [6, 7, 6]},
            'minecraft:selection_box': {'origin': [-3, 0, -3], 'size': [6, 7, 6]},
            'minecraft:destructible_by_mining': {'seconds_to_destroy': .2},
            'minecraft:destructible_by_explosion': {'explosion_resistance': 0},
            'minecraft:light_dampening': 0,
            'minecraft:connection_rule': {'accepts_connections_from': 'none'},
        }
        for state, context in effective.items():
            for component, expected in lifecycle.items():
                assert context.get(component) == expected, ('Effective incense lifecycle differs', kind, state, component)
            # Identifier alone is insufficient: bone_visibility can hide the
            # shared root while leaving every source face and UV unchanged.
            assert context['minecraft:geometry'] == {'identifier': f'geometry.kt_assets_a13.incense_{state}'}, ('Incense geometry route/visibility differs', kind, state, 'block')
            assert context['minecraft:item_visual']['geometry'] == {'identifier': 'geometry.kt_assets_a13.incense_closed'}, ('Incense geometry route/visibility differs', kind, state, 'item')
        texture_key = f'kt_assets_a13_block_deco_incense_{kind}_incense'
        for context in contexts:
            materials = context.get('minecraft:material_instances', context.get('material_instances'))
            assert {m['texture'] for m in materials.values()} == {texture_key}, 'Incense texture binding differs'
        for context in contexts[:2]:
            materials = context['minecraft:material_instances']
            assert materials['*']['face_dimming'] is True
            assert materials['*']['ambient_occlusion'] == 0
        assert effective['open']['minecraft:material_instances']['unshaded']['face_dimming'] is False
        texture = f'textures/kaleidoscope_tavern/block/deco/incense/{kind}_incense'
        assert read('runtime/RP/textures/terrain_texture.json')['texture_data'][texture_key]['textures'] == texture
        image = Image.open(root / ('runtime/RP/' + texture + '.png')).convert('RGBA')
        assert image.size == (32, 32)
        if java_source is not None:
            assets = Path(java_source) / 'src/main/resources/assets/kaleidoscope_tavern'
            original = Image.open(assets / f'textures/block/deco/incense/{kind}_incense.png').convert('RGBA')
            assert original.size == image.size and original.tobytes() == image.tobytes(), ('Source incense texture differs', kind)
            for state, folder in (('closed', 'incense'), ('open', 'incense_open')):
                model = json.loads((assets / f'models/block/deco/{folder}/{kind}_incense.json').read_text())
                assert model['elements'] == sources[state]['elements'], ('Source incense model differs', kind, state)
        assert all(image.getpixel((x, y))[3] == 0 for y in range(10, 14) for x in range(9, 13)), (kind, 'Opaque base blocks the source underside')
        assert all(image.getpixel((x, y))[3] == 255 for y in range(12, 16) for x in range(16, 20)), (kind, 'Transparent source fill bottom')
        for state in ('closed', 'open'):
            underside_rays += check_underside(sources[state], geometries[state], image)
        assert all(image.getpixel((x,y))[3] == 0 for y in range(1,5) for x in range(9,13)), (kind, 'Opaque frame/lid overlap')
    owned = runtime_sources()
    ledger = read('data/baseline-reconciliation.json')
    for section in ('files', 'reviewedFunctionalDeltas'):
        assert not owned & set(ledger.get(section, {})), 'Incense returned to a historical postimage'
    for section in ('reviewedFunctionalDeltaLayers', 'reviewedAssetDeltaLayers'):
        for layer in ledger.get(section, []):
            assert not owned & set(layer['files']), 'Incense returned to a reverse delta'
    launch = read('data/launch-repair-reference.json')
    for section in ('reviewedChanges', 'newRuntimeFiles'):
        assert not owned & set(launch[section]), 'Incense returned to the historical launch aggregate'
    return {'firstVisibleUndersideRays': underside_rays, 'sourceFillBottomRetained': True, 'incenseTypes': len(KINDS), 'sharedModels': 2, 'culledCutoutSides': True,
            'opaqueInterCubeOverlaps': 0, 'clientRenderingTested': False}

if __name__ == '__main__':
    print(json.dumps(check()))
