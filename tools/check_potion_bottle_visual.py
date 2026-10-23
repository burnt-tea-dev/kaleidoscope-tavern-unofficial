#!/usr/bin/env python3
"""Current source/resource contract for the shared placed-potion renderer.

The functional adapter suite owns storage, lifecycle and original-JVM colours.
This check owns original model/texture conversion and generated resource wiring.
Neither check is a native client render acceptance.
"""
import argparse
import copy
import json
from pathlib import Path
from PIL import Image
from build_potion_bottle_visual import ROOT, MODEL, TEXTURE, LIQUID_ELEMENT, outputs, encoded, read

# Current domain boundary used by the old launch guard after retiring its
# inverse patches. No release versions, preimages or runtime hashes live here.
SCRIPT_SOURCES = {'runtime/BP/scripts/'+name for name in (
    'bedrock/vanilla-bottle-displays.js', 'bedrock/potions.js',
    'core/potions.js', 'core/effect-colors.js', 'core/status-aura.js', 'main.js')}


def runtime_sources():
    return SCRIPT_SOURCES | set(outputs())


def check(java_source=None, root=ROOT):
    generated = outputs(root)
    for name, value in generated.items():
        assert (root/name).read_bytes() == encoded(value), ('Stale generated potion resource', name)
    original = read(root/MODEL)['minecraft:geometry'][0]
    cubes = original['bones'][0]['cubes']
    assert len(cubes) == 8
    if java_source:
        resource = java_source/'src/main/resources/assets/kaleidoscope_tavern'
        java = read(resource/'models/block/brew/potion_bottle.json')
        assert java['texture_size'] == [32, 32] and java['render_type'] == 'cutout'
        assert (resource/'textures/block/brew/potion_bottle.png').read_bytes() == (root/TEXTURE).read_bytes()
        assert len(java['elements']) == len(cubes)
        for index, (element, cube) in enumerate(zip(java['elements'], cubes)):
            assert cube['origin'] == [8-element['to'][0], element['from'][1], element['from'][2]-8]
            assert cube['size'] == [b-a for a,b in zip(element['from'], element['to'])]
            assert element.get('rotation', {}).get('angle', 0) == 0
            assert not cube.get('rotation') and set(cube['uv']) == set(element['faces'])
            for face, info in element['faces'].items():
                assert info['texture'] == '#0'
                assert info.get('tintindex') == (0 if index == LIQUID_ELEMENT else None)
                u0,v0,u1,v1 = info['uv']
                expected = {'uv':[u1*2,v1*2], 'uv_size':[(u0-u1)*2,(v0-v1)*2]} if face in ('up','down') else {
                    'uv':[u0*2,v0*2], 'uv_size':[(u1-u0)*2,(v1-v0)*2]}
                assert cube['uv'][face] == expected, ('Java source UV differs', index, face)
        source = java_source/'src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/client'
        color = (source/'render/misc/PotionBottleColor.java').read_text()
        assert 'tintIndex != 0' in color and '.getColor(' in color
        assert 'PotionBottleBlockEntity' in color and 'getPotionStack()' in color
    glass = generated['runtime/RP/models/entity/potion_bottle_glass.geo.json']['minecraft:geometry'][0]
    expected = copy.deepcopy(original)
    expected['description']['identifier'] = glass['description']['identifier']
    del expected['bones'][0]['cubes'][LIQUID_ELEMENT]
    assert glass == expected
    image = Image.open(root/'runtime/RP/textures/kt_runtime/potion/rgb_opaque.png').convert('RGBA')
    assert image.tobytes() == bytes((255,255,255,255))*image.width*image.height
    source_set = read((root/TEXTURE).with_suffix('.texture_set.json'))
    target_set = copy.deepcopy(source_set);target_set['minecraft:texture_set']['color']='rgb_opaque'
    assert read(root/'runtime/RP/textures/kt_runtime/potion/rgb_opaque.texture_set.json') == target_set
    components = generated['runtime/BP/entities/potion_liquid_visual.json']['minecraft:entity']['components']
    assert 'minecraft:inventory' not in components and not components['minecraft:physics']['has_collision']
    return {'java_model_texture_verified':bool(java_source), 'generated_resources':len(generated),
            'untinted_glass_cubes':len(glass['bones'][0]['cubes']), 'shared_liquid_geometry':True,
            'inventory_helpers_added':0, 'client_rendered':False}


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--java-source',type=Path)
    print(json.dumps(check(parser.parse_args().java_source)))
