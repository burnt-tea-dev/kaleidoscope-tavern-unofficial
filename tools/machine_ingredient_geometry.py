"""Current pressing-card geometry and consumer contract.

Canonical runtime JSON is the authoring owner. No active geometry generator
exists: history/pre-release-0.6.29 is archived, not a release input. This check
owns the shared card's dimensions/topology, without an inverse hash projection.
Placed frame/culling semantics remain a separate, unproven engine contract.
"""
import hashlib
import json
import re
from pathlib import Path
from machine_ingredient_animation import bindings

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'data/pressing-ingredient-source'
SPRITE_SOURCE = 'data/machine-ingredient-source'
CARD = 'runtime/RP/models/entity/runtime_pressing_card.geo.json'
CUBE = 'runtime/RP/models/entity/runtime_pressing_cube.geo.json'
BARREL = 'runtime/RP/models/entity/runtime_barrel_ingredients_card.geo.json'
ANIMATION = 'runtime/RP/animations/runtime_pressing_ingredients.animation.json'
CONTROLLER = 'runtime/RP/render_controllers/runtime_pressing_ingredients.render_controllers.json'
FOODS = 'runtime/BP/scripts/data/pressing-ingredient-visuals.js'
N = 'kaleidoscope_tavern:'
CARD_ID = 'geometry.kt_runtime.pressing_card'
HELPERS = tuple('pressing_tub_ingredients' + (f'_{i}' if i else '') for i in range(8))
CUBE_ITEMS = ('blue_ice', 'ice', 'packed_ice', 'dirt', 'stone')
ITEMS = ('grape', 'ice_grape', 'gold_grape', 'green_grape', 'sweet_berries', 'glow_berries',
         'apple', 'blaze_powder', 'glow_ink_sac', 'glowstone_dust', 'gold_nugget',
         'gunpowder', 'honeycomb', 'iron_nugget', 'potato', 'redstone', 'sugar',
         'sugar_cane', 'wheat', 'rotten_flesh', *CUBE_ITEMS, 'pink_petals')
TEXTURES = ('kaleidoscope_tavern/item/grape', 'kt_derived/a17/icon_ice_grape',
            'kaleidoscope_tavern/item/gold_grape', 'kaleidoscope_tavern/item/green_grape',
            'items/sweet_berries', 'items/glow_berries', 'items/apple', 'items/blaze_powder',
            'items/dye_powder_glow', 'items/glowstone_dust', 'items/gold_nugget',
            'items/gunpowder', 'kt_runtime/machine_ingredients/java/honeycomb', 'items/iron_nugget', 'items/potato',
            'items/redstone_dust', 'items/sugar', 'items/reeds', 'items/wheat',
            'items/rotten_flesh', 'blocks/blue_ice', 'blocks/ice', 'blocks/ice_packed',
            'blocks/dirt', 'blocks/stone', 'items/pink_petals')


def read(path):
    return json.loads(path.read_text())


def runtime_sources():
    # Current resource/Java contracts replace obsolete helper-texture inverse
    # projections. Unchanged controllers and the animation clock keep owners.
    return frozenset({CARD, BARREL}) | frozenset(
        'runtime/RP/entity/runtime_' + h + '.entity.json' for h in HELPERS) | frozenset(
        f'runtime/RP/entity/runtime_barrel_ingredients_{i}.entity.json' for i in range(4)) | frozenset(
        f'runtime/RP/textures/kt_runtime/machine_ingredients/java/{name}{suffix}'
        for name in ('honeycomb', 'lilac') for suffix in ('.png', '.texture_set.json'))


def resource_paths():
    return set(runtime_sources()) | {CARD, CUBE, BARREL, ANIMATION, CONTROLLER, FOODS,
            'data/barrel-materials.json', SPRITE_SOURCE + '/source.json',
            'data/baseline-reconciliation.json', 'data/launch-repair-reference.json'} | {
        'runtime/RP/entity/runtime_' + h + '.entity.json' for h in HELPERS} | {
        'runtime/BP/entities/' + h + '_visual.json' for h in HELPERS} | {
        str(p.relative_to(ROOT)) for p in (ROOT / SPRITE_SOURCE).rglob('*') if p.is_file()}


def broad_face_uv():
    # Retain the south face as the local-frame reference. Java's north UV
    # rectangle is [16,0,0,16], so its Bedrock delta is [-16,16].
    return {'north': {'uv': [16, 0], 'uv_size': [-16, 16]},
            'south': {'uv': [0, 0], 'uv_size': [16, 16]}}


def source_dimensions(root):
    source = root / SOURCE
    records = read(source / 'source.json')
    for name, record in records['files'].items():
        raw = (source / name).read_bytes()
        assert len(raw) == record['bytes'] and hashlib.sha256(raw).hexdigest() == record['sha256'], ('Source fixture changed', name)
    renderers = [(source / (b + '-renderer.java')).read_text() for b in ('forge', 'neoforge')]
    scales = []
    for renderer in renderers:
        matches = re.findall(r'poseStack\.scale\(([^;]+)\);', renderer)
        assert len(matches) == 1 and 'ItemDisplayContext.FIXED' in renderer
        values = [float(v.strip().removesuffix('f')) for v in matches[0].split(',')]
        assert values == [.5, .5, .5]
        scales.append(values)
    # This narrow bytecode evidence establishes the main generated slab,
    # not all alpha-edge quads or any later Minecraft algorithm version.
    bytecode = (source / '1.20.1-ItemModelGenerator.bytecode.txt').read_text()
    constructor = bytecode.split('115: dup', 1)[1].split('140: aload', 1)[0]
    values = [0.0 if op == 'fconst_0' else float(value) for op, value in
              re.findall(r'\d+: (fconst_0)|// float ([\d.]+)f', constructor)]
    assert values == [0, 0, 7.5, 16, 16, 8.5], 'Generated broad-face slab changed'
    dims = [values[i+3] - values[i] for i in range(3)]
    for version in ('1.20.1', '1.21.1'):
        fixed = read(source / (version + '-generated.json'))['display']['fixed']
        assert fixed == {'rotation': [0, 180, 0], 'scale': [1, 1, 1]}, 'Generated FIXED display changed'
    return [d*s for d, s in zip(dims, scales[0])]


def check_geometry(value, kind, dimensions):
    assert not re.search(r'\b(?:true|false|NaN|Infinity)\b', json.dumps(value)), 'Invalid geometry numeric type'
    assert value['format_version'] == '1.12.0' and len(value['minecraft:geometry']) == 1
    geo = value['minecraft:geometry'][0]
    assert geo['description'] == {
        'identifier': 'geometry.kt_runtime.pressing_' + kind,
        'texture_width': 16, 'texture_height': 16, 'visible_bounds_width': 3,
        'visible_bounds_height': 3, 'visible_bounds_offset': [0, 1, 0]}, 'Geometry metadata changed'
    base = [{'name': 'tilt_yaw', 'pivot': [0, 0, 0]},
            {'name': 'tilt', 'parent': 'tilt_yaw', 'pivot': [-8, 0, -8]},
            {'name': 'offset', 'parent': 'tilt', 'pivot': [0, 0, 0]}]
    assert geo['bones'][:3] == base and len(geo['bones']) == 27, 'Shared pose hierarchy changed'
    faces = ('north', 'south') if kind == 'card' else ('north', 'south', 'east', 'west', 'up', 'down')
    box = {'origin': [-d/2 for d in dimensions], 'size': dimensions,
           'uv': broad_face_uv() if kind == 'card' else
                 {face: {'uv': [0, 0], 'uv_size': [16, 16]} for face in faces}}
    for i in range(8):
        bones = geo['bones'][3+i*3:6+i*3]
        assert bones == [
            {'name': f'ingredient_{i}', 'parent': 'offset', 'pivot': [0, 0, 0]},
            {'name': f'item_y_{i}', 'parent': f'ingredient_{i}', 'pivot': [0, 0, 0]},
            {'name': f'item_z_{i}', 'parent': f'item_y_{i}', 'pivot': [0, 0, 0], 'cubes': [box]}], ('Centered dimensions, UV or hierarchy changed', kind, i)


def check(root=ROOT):
    root = Path(root)
    dimensions = source_dimensions(root)
    check_geometry(read(root / CARD), 'card', dimensions)
    check_geometry(read(root / CUBE), 'cube', [4, 4, 4])
    barrel_doc = read(root / BARREL)
    assert barrel_doc['format_version'] == '1.12.0' and len(barrel_doc['minecraft:geometry']) == 1
    barrel = barrel_doc['minecraft:geometry'][0]
    assert barrel['description'] == {'identifier': 'geometry.kt_runtime.barrel_ingredients_card',
        'texture_width': 16, 'texture_height': 16, 'visible_bounds_width': 3,
        'visible_bounds_height': 4, 'visible_bounds_offset': [0, 1.5, 0]}
    assert len(barrel['bones']) == 9
    for i, bone in enumerate(barrel['bones']):
        assert bone == {'name': f'item_{i}', 'pivot': [0, 0, 0], 'cubes': [{
            'origin': [-4, -4, -.25], 'size': [8, 8, .5],
            'uv': broad_face_uv()}]}, ('Barrel control changed', i)
    consumers = set()
    for sub in ('entity', 'attachables'):
        for path in (root / 'runtime/RP' / sub).glob('*.json'):
            if CARD_ID in path.read_text():
                consumers.add(path.relative_to(root).as_posix())
    expected = {'runtime/RP/entity/runtime_' + h + '.entity.json' for h in HELPERS}
    assert consumers == expected, 'Shared card consumer census changed'
    textures = {f'kind_{i}': 'textures/' + p for i, p in enumerate(TEXTURES, 1)} | bindings()
    for h in HELPERS:
        e = read(root / ('runtime/RP/entity/runtime_' + h + '.entity.json'))['minecraft:client_entity']['description']
        assert e == {'identifier': N + h + '_visual', 'materials': {'default': 'entity_alphatest'},
                     'textures': textures, 'geometry': {'card': CARD_ID, 'cube': 'geometry.kt_runtime.pressing_cube'},
                     'animations': {'layout': 'animation.kt_runtime.pressing.layout'},
                     'scripts': {'animate': ['layout']},
                     'render_controllers': ['controller.render.kt_runtime.pressing_ingredients']}, ('Helper resource route changed', h)
        bp = read(root / ('runtime/BP/entities/' + h + '_visual.json'))['minecraft:entity']
        assert bp['description']['identifier'] == e['identifier']
        assert 'scale' not in json.dumps(bp).lower(), 'Unexpected helper scale'
        properties = bp['description']['properties']
        for name, maximum in [('grape_kind', 26), ('fill_stage', 8), ('tilt', 1), ('facing', 3)]:
            p = properties[N + name]
            assert p['client_sync'] is True and p['range'] == ([1, maximum] if name == 'grape_kind' else [0, maximum])
    anim = read(root / ANIMATION)['animations']['animation.kt_runtime.pressing.layout']
    assert anim['loop'] is True and len(anim['bones']) == 27
    assert not any('scale' in b for b in anim['bones'].values()), 'Do not compensate with animation scale'
    # Preserve the existing placed-frame contract separately from dimensions.
    # This is not a claim that its model-to-world frame or culling is proven.
    tilt = "q.property('kaleidoscope_tavern:tilt')"
    axis = "math.mod(q.property('kaleidoscope_tavern:facing'),2)"
    assert anim['bones']['tilt_yaw'] == {'rotation': [0, f"{tilt} ? q.property('kaleidoscope_tavern:facing')*90 : 0", 0]}
    assert anim['bones']['tilt'] == {'rotation': [f'{tilt} ? ({axis} ? 45 : -45) : 0', 0, 0]}
    assert anim['bones']['offset'] == {'position': [0, f'{tilt} ? ({axis} ? 8 : -4) : 0', f'{tilt} ? ({axis} ? -8 : 4) : 0']}
    for i in range(8):
        q = lambda n: f"q.property('{N}{n}{i}')"
        assert anim['bones'][f'ingredient_{i}'] == {'position': [f'math.floor({q("xz")}/1024)/128-4', q('y'), f'math.mod({q("xz")},1024)/128-4'], 'rotation': [-90, 0, 0]}
        assert anim['bones'][f'item_y_{i}'] == {'rotation': [0, f'-(math.floor({q("rot")}/7201)*.01-6.4)', 0]}
        assert anim['bones'][f'item_z_{i}'] == {'rotation': [0, 0, f'-(math.mod({q("rot")},7201)*.1-360)']}
    text = (root / FOODS).read_text()
    foods = json.loads(text[text.index('{'):text.rindex('}')+1])
    assert foods == {**{(N if i <= 4 else 'minecraft:') + name: i for i, name in enumerate(ITEMS, 1)}, 'amw:sour_cherry': 5}, 'Food routing changed'
    controller = read(root / CONTROLLER)['render_controllers']['controller.render.kt_runtime.pressing_ingredients']
    condition = ' || '.join(f"q.property('{N}grape_kind') == {i}" for i in range(21, 26))
    assert controller == {
        'geometry': f'({condition}) ? Geometry.cube : Geometry.card',
        'materials': [{'*': 'Material.default'}],
        'textures': [f"q.property('{N}grape_kind') == 2 ? Array.ice_grape_ticks[math.mod(math.floor(q.time_stamp), 24)] : Array.kind[q.property('{N}grape_kind')-1]"],
        'arrays': {'textures': {'Array.kind': [f'Texture.kind_{i}' for i in range(1, 27)], 'Array.ice_grape_ticks': ['Texture.' + name for name in bindings()]}},
        'part_visibility': [{f'ingredient_{i}': f"q.property('{N}fill_stage') > {i}"} for i in range(8)]}, 'Controller route changed'
    # Keep the complete barrel helper definition with its existing generator.
    # Only two ingredient-specific PNG aliases change; no vanilla override.
    from build_barrel_materials import client_description
    catalog = read(root / 'data/barrel-materials.json')['materials']
    source = read(root / SPRITE_SOURCE / 'source.json')
    replacements = source['private_texture_replacements']
    assert replacements == {'minecraft:honeycomb': 'textures/kt_runtime/machine_ingredients/java/honeycomb',
                            'minecraft:lilac': 'textures/kt_runtime/machine_ingredients/java/lilac'}
    assert len(catalog) == 61
    for row in source['items']:
        if 'barrel_kind' in row:
            entry = catalog[row['barrel_kind']-1]
            assert entry['id'] == row['id'] and entry['model'] == 'card'
            assert entry['texture'] == replacements.get(row['id'], row['native_texture']), ('Ingredient texture route changed', row['id'])
        if row['id'] not in replacements:
            continue
        texture = replacements[row['id']]
        assert (root / 'runtime/RP' / (texture + '.png')).read_bytes() == (root / SPRITE_SOURCE / row['texture']).read_bytes(), ('Java ingredient pixels changed', row['id'])
        assert read(root / 'runtime/RP' / (texture + '.texture_set.json')) == {
            'format_version': '1.16.100', 'minecraft:texture_set': {
                'color': Path(texture).name, 'metalness_emissive_roughness': [0, 0, 200]}}
    for slot in range(4):
        description = read(root / f'runtime/RP/entity/runtime_barrel_ingredients_{slot}.entity.json')['minecraft:client_entity']['description']
        assert description == client_description(slot, catalog), ('Barrel helper resource route changed', slot)
    barrel_consumers = {p.relative_to(root).as_posix() for folder in ('entity', 'attachables')
                        for p in (root / 'runtime/RP' / folder).glob('*.json')
                        if 'geometry.kt_runtime.barrel_ingredients_card' in p.read_text()}
    assert barrel_consumers == {f'runtime/RP/entity/runtime_barrel_ingredients_{slot}.entity.json' for slot in range(4)}, 'Barrel card consumer census changed'
    # A current source contract must not be silently reclaimed by old ledgers.
    ledger = read(root / 'data/baseline-reconciliation.json')
    for section in ('files', 'reviewedFunctionalDeltas'):
        assert not runtime_sources() & set(ledger.get(section, {})), 'Current geometry has a historical postimage guard'
    for section in ('reviewedFunctionalDeltaLayers', 'reviewedAssetDeltaLayers'):
        for layer in ledger.get(section, []):
            assert not runtime_sources() & set(layer['files']), 'Current geometry has a reverse delta'
    launch = read(root / 'data/launch-repair-reference.json')
    for section in ('reviewedChanges', 'newRuntimeFiles'):
        assert not runtime_sources() & set(launch.get(section, {})), 'Current geometry has a launch hash guard'
    from check_machine_ingredient_broadfaces import check as check_broadfaces
    broadfaces = check_broadfaces(root)
    return {'card_dimensions': dimensions, 'center': [0, 0, 0], 'cubes': 8,
            'helpers': 8, 'slots': 64, 'card_ids': 22, 'cube_kinds': 5,
            'barrel_control_cubes': 9, 'native_frame_culling_verified': False,
            'broadface_source_frames': broadfaces['source_frames'],
            'alpha_edge_extrusion': False, 'geometry_ids': 2,
            'card_allocated_vertices': {'pressing': 8*24, 'barrel': 9*24},
            'gameplay_verified': False, 'material_verified': False}


if __name__ == '__main__':
    print(json.dumps(check(), indent=2))
