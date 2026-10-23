"""Split the original potion bottle into untinted glass and shared RGB liquid.

The original Java model's second element has tintindex=0 on its six faces.
All potion identities share these source texels and one cosmetic helper type.
No inventory or recoverable item lives in this helper.
"""
import argparse
import copy
import io
import json
from pathlib import Path
from PIL import Image
from source_texel_geometry import partition_texels, tint_controller

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'runtime/RP/models/entity/potion_bottle.geo.json'
TEXTURE = 'runtime/RP/textures/kaleidoscope_tavern_jar/block/brew/potion_bottle.png'
LIQUID_ELEMENT = 1


def read(path):
    return json.loads(path.read_text())


def potion_block(glass_geometry, item_geometry):
    """Complete current block declaration; never seed output from itself."""
    material = {'*': {'texture': 'kt_assets_a17_potion_bottle',
                     'render_method': 'alpha_test', 'ambient_occlusion': 0.0, 'face_dimming': True}}
    return {'format_version': '1.26.50', 'minecraft:block': {
        'description': {'identifier': 'kaleidoscope_tavern:potion_bottle',
                        'traits': {'minecraft:placement_direction': {
                            'enabled_states': ['minecraft:cardinal_direction'], 'y_rotation_offset': 180.0}}},
        'components': {
            'minecraft:geometry': {'identifier': glass_geometry},
            'minecraft:material_instances': copy.deepcopy(material),
            'minecraft:item_visual': {'geometry': {'identifier': item_geometry},
                                     'material_instances': copy.deepcopy(material)},
            'minecraft:collision_box': False,
            'minecraft:selection_box': {'origin': [-3,0,-3], 'size': [6,10,6]},
            'minecraft:destructible_by_mining': {'seconds_to_destroy': 0.6},
            'minecraft:destructible_by_explosion': {'explosion_resistance': 0},
            'minecraft:movable': {'movement_type': 'immovable'},
            'minecraft:loot': 'loot_tables/empty.json',
            'minecraft:light_dampening': 0,
            'minecraft:liquid_detection': {'detection_rules': [{
                'liquid_type': 'water', 'can_contain_liquid': True,
                'on_liquid_touches': 'blocking', 'use_liquid_clipping': True}]},
            'kaleidoscope_tavern:natural_break': {'drop': 'kaleidoscope_tavern:potion_bottle'},
            'minecraft:connection_rule': {'accepts_connections_from': 'none'},
            'kaleidoscope_tavern:potion_bottle_visual': {},
            'minecraft:tick': {'interval_range': [20,20], 'looping': True}},
        'permutations': [{'condition': f"q.block_state('minecraft:cardinal_direction') == '{facing}'",
                          'components': {'minecraft:transformation': {'rotation': [0,-90*index,0]}}}
                         for index, facing in enumerate(('north','east','south','west'))]}}


def outputs(root=ROOT):
    original = read(root / MODEL)['minecraft:geometry'][0]
    assert len(original['bones']) == 1
    liquid = original['bones'][0]['cubes'][LIQUID_ELEMENT]
    source = Image.open(root / TEXTURE).convert('RGBA')
    assert source.size == (32, 32)
    groups = partition_texels([liquid], source, 32, 1)
    glass = copy.deepcopy(original)
    glass['description']['identifier'] = 'geometry.kt_runtime.potion_bottle_glass'
    del glass['bones'][0]['cubes'][LIQUID_ELEMENT]
    models, controllers, aliases = [], {}, {}
    for color, frames in groups.items():
        shade = ''.join(f'{c:02x}' for c in color)
        model = copy.deepcopy(original)
        identifier = f'geometry.kt_runtime.potion_liquid_{shade}'
        model['description'].update(identifier=identifier, texture_width=2, texture_height=2)
        model['bones'][0]['cubes'] = frames[0]
        models.append(model)
        aliases[f'rgb_{shade}'] = identifier
        controllers[f'controller.render.kt_runtime.potion_liquid_{shade}'] = tint_controller([f'Geometry.rgb_{shade}'], color)
    bp = {'format_version': '1.21.0', 'minecraft:entity': {
        'description': {'identifier': 'kaleidoscope_tavern:potion_liquid_visual',
                        'is_spawnable': False, 'is_summonable': True, 'is_experimental': False,
                        'properties': {f'kt_art:{channel}': {'type': 'int', 'range': [0, 255], 'default': 255, 'client_sync': True}
                                       for channel in ('red', 'green', 'blue')}},
        'components': {
            'minecraft:physics': {'has_gravity': False, 'has_collision': False},
            'minecraft:collision_box': {'width': 0, 'height': 0},
            'minecraft:health': {'value': 1, 'max': 1},
            'minecraft:persistent': {},
            'minecraft:pushable': {'is_pushable': False, 'is_pushable_by_piston': False},
            'minecraft:type_family': {'family': ['kt_potion_liquid_visual']},
            'minecraft:damage_sensor': {'triggers': [{'cause': 'all', 'deals_damage': 'no'}]}}}}
    rp = {'format_version': '1.10.0', 'minecraft:client_entity': {'description': {
        'identifier': 'kaleidoscope_tavern:potion_liquid_visual',
        'materials': {'liquid_rgb': 'entity_alphatest_change_color'},
        'textures': {'rgb_opaque': 'textures/kt_runtime/potion/rgb_opaque'},
        'geometry': aliases, 'render_controllers': list(controllers)}}}
    block = potion_block(glass['description']['identifier'], original['description']['identifier'])
    carrier = io.BytesIO()
    Image.new('RGBA', (2, 2), (255, 255, 255, 255)).save(carrier, format='PNG')
    texture_set = read((root / TEXTURE).with_suffix('.texture_set.json'))
    texture_set['minecraft:texture_set']['color'] = 'rgb_opaque'
    return {
        'runtime/RP/textures/kt_runtime/potion/rgb_opaque.png': carrier.getvalue(),
        'runtime/RP/textures/kt_runtime/potion/rgb_opaque.texture_set.json': texture_set,
        'runtime/RP/models/entity/potion_bottle_glass.geo.json': {'format_version': '1.21.0', 'minecraft:geometry': [glass]},
        'runtime/RP/models/entity/potion_liquid_texels.geo.json': {'format_version': '1.21.0', 'minecraft:geometry': models},
        'runtime/RP/render_controllers/potion_liquid.render_controllers.json': {'format_version': '1.8.0', 'render_controllers': controllers},
        'runtime/BP/entities/potion_liquid_visual.json': bp,
        'runtime/RP/entity/potion_liquid_visual.entity.json': rp,
        'runtime/BP/blocks/potion_bottle.json': block}


def encoded(value):
    return value if isinstance(value, bytes) else (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    check = parser.parse_args().check
    for name, value in outputs().items():
        path = ROOT / name
        if check:
            assert path.read_bytes() == encoded(value), name
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(encoded(value))
    print(json.dumps({'shared_potion_geometry': True, 'inventory_helpers_added': 0, 'client_rendered': False}))
