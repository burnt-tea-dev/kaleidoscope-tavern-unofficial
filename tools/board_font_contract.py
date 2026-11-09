"""Current source-pixel and routing contract for Tavern Board Font.

The pinned GNU Unifont input owns all BMP cells, including the retained fallback
glyphs. Historical byte snapshots no longer own these atlases or their entity.
Native allocation, FPS and rendered client acceptance are not measured here.
"""
import json
from pathlib import Path
from PIL import Image
from build_board_font import ROOT, ENTITY, METRICS, ATLAS_DIRECTORY, layout
from build_board_rendering import check as check_rendering, P

CONTROLLERS = 'runtime/RP/render_controllers/board_glyph_visual.render_controllers.json'
ATLAS_SCOPE = frozenset(f'{ATLAS_DIRECTORY}/glyph_{page:02X}.png' for page in range(256))


def owned_sources():
    """Exact current ownership, including aliases retired by the source layout."""
    return ATLAS_SCOPE | {ENTITY}


def runtime_sources(root=ROOT):
    return frozenset(layout(root)[1]) | {ENTITY}


def retired_sources(root=ROOT):
    return ATLAS_SCOPE - runtime_sources(root)


def check(root=ROOT):
    root = Path(root)
    textures, atlases, metrics = layout(root)
    physical = {p.relative_to(root).as_posix() for p in (root / ATLAS_DIRECTORY).rglob('*') if p.is_file()}
    assert physical == set(atlases), 'Missing, extra or retired board font atlas'
    for name, pixels in atlases.items():
        path = root / name
        assert not path.is_symlink(), ('Board font atlas must be owned', name)
        with Image.open(path) as image:
            assert image.mode == 'RGBA' and image.size == (256, 256), ('Board font format differs', name)
            assert image.tobytes() == pixels, ('Board font source RGBA differs', name)
    assert (root / METRICS).read_text() == metrics, 'Board glyph advances or bold offset differ from source'
    definition = json.loads((root / ENTITY).read_text())
    assert set(definition) == {'format_version', 'minecraft:client_entity'} and definition['format_version'] == '1.10.0'
    assert set(definition['minecraft:client_entity']) == {'description'}
    entity = definition['minecraft:client_entity']['description']
    assert set(entity) == {'identifier', 'materials', 'textures', 'geometry', 'animations', 'scripts', 'render_controllers'}
    assert entity['identifier'] == 'kaleidoscope_tavern:board_glyph_visual'
    assert entity['textures'] == textures, 'Board logical page binding differs from source'
    assert entity['geometry'] == {
        **{f'cell_{i}': f'geometry.kt_runtime.board_glyph_cell_{i}' for i in range(256)},
        **{f'outline_cell_{i}': f'geometry.kt_runtime.board_outline_cell_{i}' for i in range(256)}}, 'Board glyph geometry bindings differ'
    assert entity['materials'] == {'default': 'entity_alphatest_change_color', 'glow': 'entity_emissive_alpha'}
    assert entity['animations'] == {'layout': 'animation.kt_runtime.board_glyph_line'}
    assert entity['scripts'] == {'animate': ['layout'], 'scale': P('font_scale')}
    controllers = json.loads((root / CONTROLLERS).read_text())['render_controllers']
    assert set(controllers) == {'controller.render.kt_runtime.board_glyph', 'controller.render.kt_runtime.board_outline'}
    for kind in ('glyph', 'outline'):
        controller = controllers['controller.render.kt_runtime.board_' + kind]
        assert controller['arrays']['textures'] == {'Array.pages': [f'Texture.page_{i}' for i in range(256)]}, 'Board texture page order differs'
        cell = 'cell' if kind == 'glyph' else 'outline_cell'
        assert controller['arrays']['geometries'] == {'Array.cells': [f'Geometry.{cell}_{i}' for i in range(256)]}, 'Board geometry cell order differs'
        assert controller['arrays']['materials'] == {'Array.ink': ['Material.default', 'Material.glow']}
        assert controller['textures'] == [f"Array.pages[math.floor({P('char_0')} / 256)]"], 'Board page selector differs'
        assert controller['geometry'] == f"Array.cells[math.mod({P('char_0')}, 256)]", 'Board cell selector differs'
        if kind == 'glyph':
            assert controller['materials'] == [{'*': f"Array.ink[{P('glowing')}]"}]
    # Existing generator checks all UVs, foreground/outline geometry, animation,
    # tint, material selection and native-root distance gates independently of
    # the texture aliases and arrays validated above.
    check_rendering(root)
    ledger = json.loads((root / 'data/baseline-reconciliation.json').read_text())
    for section in ('files', 'reviewedFunctionalDeltas'):
        assert not owned_sources() & set(ledger.get(section, {})), 'Board font returned to a historical postimage'
    for section in ('reviewedFunctionalDeltaLayers', 'reviewedAssetDeltaLayers'):
        assert all(not owned_sources() & set(layer['files']) for layer in ledger.get(section, [])), 'Board font returned to an inverse delta'
    for reference in ('launch-repair-reference.json', 'efficiency-repair-reference.json'):
        rows = json.loads((root / 'data' / reference).read_text())
        for section in ('reviewedChanges', 'newRuntimeFiles', 'removedRuntimeFiles'):
            assert not owned_sources() & set(rows.get(section, {})), 'Board font returned to a historical hash aggregate'
    return {'logicalPages': len(textures), 'physicalAtlases': len(atlases),
            'sourceRgbaBytes': sum(len(pixels) for pixels in atlases.values()),
            'glyphs': 65536, 'sourcePixelsAndRouting': 'passed', 'client': False}


if __name__ == '__main__':
    print(json.dumps(check()))
