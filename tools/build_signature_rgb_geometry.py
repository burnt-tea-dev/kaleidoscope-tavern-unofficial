"""Source-texel surfaces for arbitrary 24-bit signature colours.

Only the out-of-atlas path uses these surfaces. Each opaque source texel is a
rectangle on its original face; equal-colour neighbouring rectangles merge.
The already-tested native overlay material tints a fully opaque white texture
by sourceRGB * cupRGB. Sparse alpha masks are deliberately not used: their mip
levels could discard the liquid between colour groups. Alpha-zero source
regions have no surface. No helpers, palette quantisation or runtime upload.

Bedrock per-face UVs follow the Blockbench Bedrock codec / CubeFace.UVToLocal
convention, including X reflection and the reversed up/down UV rectangles.
Cube pivots/rotation and existing opposite-face offsets remain unchanged.
This is source geometry/colour correctness, not native-client acceptance;
the new geometric texel boundaries still need far-distance/filtering review.
"""
import argparse
import copy
import io
import json
from pathlib import Path
from PIL import Image
from refresh_visual_compat import profile
from source_texel_geometry import partition_texels, tint_controller

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'runtime/RP/textures/kaleidoscope_tavern_jar/block/mixology/signature_cocktail.png'
MESH = 'runtime/RP/models/entity/rig_signature_liquid.geo.json'
# Java animates its atlas globally. Share a level tick clock with the existing
# atlas and glass passes so helper replacement/palette changes cannot restart
# only one pass. Source cadence is one frame per two ticks.
FRAME = 'math.mod(math.floor(q.time_stamp / 2), 6)'


def read(path):
    return json.loads(path.read_text())


def partition(root=ROOT):
    source = Image.open(root / SOURCE).convert('RGBA')
    assert source.size == (32, 192)
    geometry = read(root / MESH)['minecraft:geometry'][0]
    assert len(geometry['bones']) == 1 and geometry['bones'][0]['name'] == 'tint_root'
    return geometry, partition_texels(geometry['bones'][0]['cubes'], source, 32, 6)


def outputs(root=ROOT):
    geometry, groups = partition(root)
    result = {}
    models, controllers = [], {}
    for color, frames in groups.items():
        name = ''.join(f'{c:02x}' for c in color)
        for frame, cubes in enumerate(frames):
            model = copy.deepcopy(geometry)
            model['description'].update(identifier=f'geometry.kt_runtime.signature_rgb_{name}_{frame}', texture_width=2, texture_height=2)
            model['bones'][0]['cubes'] = cubes
            models.append(model)
        controllers[f'controller.render.kt_runtime.signature_rgb_{name}'] = tint_controller(
            [f'Geometry.rgb_{name}_{i}' for i in range(6)], color, FRAME)
    result['runtime/RP/models/entity/signature_rgb_texels.geo.json'] = {'format_version': '1.21.0', 'minecraft:geometry': models}
    result['runtime/RP/render_controllers/signature_rgb_texels.render_controllers.json'] = {'format_version': '1.8.0', 'render_controllers': controllers}
    for name in ('runtime_signature_cup', 'rig_signature_color'):
        path = f'runtime/RP/entity/{name}.entity.json'
        entity = read(root / path)
        desc = entity['minecraft:client_entity']['description']
        desc['geometry'] = {key: value for key, value in desc['geometry'].items() if not key.startswith('rgb_')}
        for color in groups:
            shade = ''.join(f'{c:02x}' for c in color)
            desc['geometry'].update({f'rgb_{shade}_{i}': f'geometry.kt_runtime.signature_rgb_{shade}_{i}' for i in range(6)})
        desc['textures']['rgb_opaque'] = 'textures/kt_runtime/signature/rgb_opaque'
        # The original atlas/controller remains identical for known colours.
        # Its former flat branch is unreachable from either active entity.
        desc['render_controllers'] = ['controller.render.kt_assets_a17.signature_glass',
            {'controller.render.kt_assets_a17.signature_tint': "query.property('kt_art:palette') >= 0"},
            *[{key: "query.property('kt_art:palette') < 0"} for key in controllers]]
        result[path] = entity
    buffer = io.BytesIO()
    Image.new('RGBA', (2, 2), (255, 255, 255, 255)).save(buffer, format='PNG')
    texture = 'textures/kt_runtime/signature/rgb_opaque'
    result[f'runtime/RP/{texture}.png'] = buffer.getvalue()
    # Match the existing signature frames/atlas PBR compatibility profile.
    result[f'runtime/RP/{texture}.texture_set.json'] = {
        'format_version': '1.16.100', 'minecraft:texture_set': {
            'color': Path(texture).name,
            'metalness_emissive_roughness': [0, 0, profile(texture)[1]]}}
    return result


def write_outputs(root=ROOT):
    for name, value in outputs(root).items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value if isinstance(value, bytes) else (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    if parser.parse_args().check:
        for name, value in outputs().items():
            assert (ROOT / name).read_bytes() == (value if isinstance(value, bytes) else (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode()), name
    else:
        write_outputs()
    _, groups = partition()
    print(json.dumps({'source_colour_groups': len(groups), 'frames': 6,
                      'rectangles_per_frame': [sum(len(frames[i]) for frames in groups.values()) for i in range(6)],
                      'extra_entities': 0, 'sparse_alpha_masks': 0, 'client_rendered': False}))
