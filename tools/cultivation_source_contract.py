"""Current cultivation ownership and Java-backed plant resources.

Actual adapters run in board-farm-interaction.test.mjs; native destruction and
cascade evidence is recorded separately. No old source body is reconstructed.
"""
import hashlib
import itertools
import json
import re
from pathlib import Path
from foundation.source_contract import read_module
from wild_vine_surfaces import GEOMETRY, check as check_surfaces

ROOT = Path(__file__).resolve().parents[1]
BLOCKS = ('wild_grapevine', 'wild_grapevine_plant')
PLANTS = ('grape_crop', 'gold_grape_crop', 'ice_grape_crop', 'grapevine_trellis')
PLANT_CONTROLS = ('gold_grapevine_trellis', 'ice_grapevine_trellis')
PLANT_FIXTURES = 'data/cultivation-plants'
LOOT = 'loot_tables/blocks/wild_grapevine.json'
SCRIPTS = ('bedrock/cultivation.js', 'bedrock/protected-break-router.js')


def runtime_sources():
    return frozenset({'runtime/BP/blocks/' + name + '.json' for name in BLOCKS + PLANTS}
                     | {'runtime/BP/' + LOOT, GEOMETRY}
                     | {'runtime/BP/scripts/' + name for name in SCRIPTS})



def plant_resource_paths(root=ROOT):
    """Inputs read by the shared check, not a postimage or runtime ownership list."""
    paths = {'runtime/RP/textures/terrain_texture.json'}
    for name in PLANTS + PLANT_CONTROLS:
        paths.add('runtime/BP/blocks/' + name + '.json')
        paths.add('runtime/RP/textures/kaleidoscope_tavern/block/plant/' + name + '.png')
        for path in (Path(root) / PLANT_FIXTURES / 'models/block/plant' / name).glob('*.json'):
            native, _ = _plant_binding(name, 'kaleidoscope_tavern:block/plant/' + name + '/' + path.stem)
            paths.add('runtime/RP/models/entity/' + native + '.geo.json')
    return paths


def _plant_binding(name, reference):
    prefix = 'kaleidoscope_tavern:block/plant/' + name + '/'
    assert reference.startswith(prefix), ('Unexpected source plant model', name, reference)
    shape = reference.removeprefix(prefix)
    assert '/' not in shape
    stage = shape.startswith(('stage', 'single_stage'))
    native = name.removesuffix('_trellis') + '_' + shape.removeprefix('single_')
    group = 'a2' if name in PLANTS and stage else 'a3'
    return native, 'kt_assets_' + group


def _plant_condition(expression, state):
    # Deliberately bounded Molang grammar. No eval or engine interpretation.
    for atom in expression.split(' && '):
        match = re.fullmatch(r"q\.block_state\('([^']+)'\) == (\d+|'[^']+'|true|false)", atom)
        assert match, ('Unsupported plant condition', atom)
        raw = match[2]
        value = raw[1:-1] if raw.startswith("'") else (raw == 'true' if raw in ('true', 'false') else int(raw))
        assert match[1] in state, ('Undeclared plant state', match[1])
        if state[match[1]] != value:
            return False
    return True


def check_plant_resources(root=ROOT, java_source=None):
    """Resolve source blockstates against every native state and material route.

    Single-sided cutout keeps each authored directed face. It does not remove
    neighbour cullfaces or certify renderer/item-context parity. Existing AO=0
    and 0.16-unit thickness are Bedrock adaptations, unchanged by this policy.
    """
    root = Path(root)
    fixtures = root / PLANT_FIXTURES
    records = json.loads((fixtures / 'source.json').read_text())
    for relative, record in records['files'].items():
        raw = (fixtures / relative).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == record['sha256'], ('Plant source fixture changed', relative)
        if java_source is not None:
            source = (Path(java_source) / record['path']).read_bytes()
            assert raw == (source.replace(b'\r\n', b'\n') if relative.endswith('.json') else source)
    terrain = json.loads((root / 'runtime/RP/textures/terrain_texture.json').read_text())['texture_data']
    models = {}
    face_count = 0
    for name in PLANTS + PLANT_CONTROLS:
        for path in sorted((fixtures / 'models/block/plant' / name).glob('*.json')):
            source = json.loads(path.read_text())
            assert source['render_type'] in ('cutout', 'minecraft:cutout')
            assert 'parent' not in source, 'Plant models must resolve before material checks'
            ref = 'kaleidoscope_tavern:block/plant/' + name + '/' + path.stem
            native, group = _plant_binding(name, ref)
            geometry = json.loads((root / ('runtime/RP/models/entity/' + native + '.geo.json')).read_text())['minecraft:geometry']
            assert len(geometry) == 1
            identifier = 'geometry.' + group + '.' + native
            assert geometry[0]['description']['identifier'] == identifier
            cubes = [c for b in geometry[0]['bones'] for c in b.get('cubes', [])]
            assert len(cubes) == len(source['elements']), ('Plant directed element ownership changed', ref)
            materials = {'*': {'texture': group + '_' + native, 'render_method': 'alpha_test_single_sided',
                                'ambient_occlusion': 0, 'face_dimming': True}}
            for cube, element in zip(cubes, source['elements']):
                assert isinstance(cube['uv'], dict) and set(cube['uv']) == set(element['faces']), ('Plant directed faces changed', ref)
                tag = '*' if element.get('shade', True) else 'unshaded'
                if tag == 'unshaded':
                    materials[tag] = {**materials['*'], 'face_dimming': False}
                for direction, face in element['faces'].items():
                    assert cube['uv'][direction].get('material_instance', '*') == tag, ('Plant face material changed', ref, direction)
                    texture = face['texture']
                    seen = set()
                    while texture.startswith('#'):
                        assert texture not in seen, 'Texture alias cycle'
                        seen.add(texture)
                        texture = source['textures'][texture[1:]]
                    assert texture == 'kaleidoscope_tavern:block/plant/' + name
                    face_count += 1
            texture_path = 'textures/kaleidoscope_tavern/block/plant/' + name
            assert terrain[group + '_' + native]['textures'] == texture_path, ('Plant terrain binding changed', native)
            assert (root / ('runtime/RP/' + texture_path + '.png')).read_bytes() == (fixtures / ('textures/block/plant/' + name + '.png')).read_bytes(), ('Plant source texture changed', name)
            models[ref] = {'geometry': {'identifier': identifier}, 'material_instances': materials}

    state_count = 0
    declarations = 0
    for name in PLANTS + PLANT_CONTROLS:
        block = json.loads((root / ('runtime/BP/blocks/' + name + '.json')).read_text())['minecraft:block']
        description = block['description']
        assert description['identifier'] == 'kaleidoscope_tavern:' + name
        source = json.loads((fixtures / ('blockstates/' + name + '.json')).read_text())['variants']
        source_states = [dict(pair.split('=', 1) for pair in key.split(',')) for key in source]
        crop = name.endswith('_crop')
        expected_states = {'kaleidoscope_tavern:age': sorted({int(s['age']) for s in source_states})}
        if not crop:
            expected_states.update({'kaleidoscope_tavern:shape': sorted({s['type'] for s in source_states}),
                                    'kaleidoscope_tavern:waterlogged': [False, True]})
        assert set(description['states']) == set(expected_states)
        for key, values in expected_states.items():
            assert sorted(description['states'][key]) == sorted(values), ('Plant state domain changed', name, key)
        expected_traits = {} if crop else {'minecraft:placement_position': {'enabled_states': ['minecraft:block_face']}}
        assert description.get('traits', {}) == expected_traits
        states = dict(description['states'])
        if not crop:
            states['minecraft:block_face'] = ['down', 'up', 'north', 'south', 'west', 'east']
        base = block['components']
        zero = 'stage0' if crop else 'single_stage0'
        fallback = models['kaleidoscope_tavern:block/plant/' + name + '/' + zero]
        def visual(components, expected):
            assert components['minecraft:geometry'] == expected['geometry'], ('Plant world geometry route changed', name)
            assert components['minecraft:material_instances'] == expected['material_instances'], ('Plant source cutout material changed', name)
            # Filled-vine/crop source item models do not exist. Keep the native
            # stage-zero fallback, without claiming Java inventory equivalence.
            assert components['minecraft:item_visual'] == fallback, ('Plant item fallback changed', name)
            assert 'minecraft:transformation' not in components, ('Plant pose changed', name)
        visual(base, fallback)
        visited = set()
        for values in itertools.product(*states.values()):
            state = dict(zip(states, values))
            short = {k.split(':', 1)[1]: v for k, v in state.items()}
            java_state = {'age': str(short['age'])}
            if not crop:
                java_state.update(type=short['shape'], waterlogged=str(short['waterlogged']).lower())
            key = ','.join(k + '=' + v for k, v in sorted(java_state.items()))
            source_variant = source[key]
            assert source_variant.get('x', 0) == source_variant.get('y', 0) == 0
            components = dict(base)
            matched = []
            for index, permutation in enumerate(block.get('permutations', [])):
                if _plant_condition(permutation['condition'], state):
                    assert 'minecraft:item_visual' not in permutation['components'], ('Plant item inheritance changed', name)
                    components.update(permutation['components'])
                    matched.append(index)
                    visited.add(index)
            assert len(matched) == 1, ('Plant route must match exactly one permutation', name, state, matched)
            visual(components, models[source_variant['model']])
            state_count += 1
        assert visited == set(range(len(block.get('permutations', [])))), ('Unreachable plant permutation', name)
        declarations += 1 + len(visited)
    assert len(models) == 48 and face_count == 660 and state_count == 1026
    return {'models': len(models), 'directed_faces': face_count, 'state_combinations': state_count,
            'visual_declarations': declarations, 'engine_execution': False}


def check_resources(root=ROOT, java_source=None):
    root = Path(root)
    check_surfaces(root, java_source)
    plants = check_plant_resources(root, java_source)
    for name in BLOCKS:
        block = json.loads((root / 'runtime/BP/blocks' / (name + '.json')).read_text())['minecraft:block']
        assert block['description']['identifier'] == 'kaleidoscope_tavern:' + name
        components = block['components']
        assert components.get('minecraft:loot') == LOOT, ('Native wild-vine loot disconnected', name)
        assert 'kaleidoscope_tavern:natural_break' not in components, ('Duplicate scripted wild-vine loot', name)
        assert components['minecraft:destructible_by_mining']['seconds_to_destroy'] == 0
        assert 'kaleidoscope_tavern:' + name in components, ('Cultivation component disconnected', name)
    loot = json.loads((root / 'runtime/BP' / LOOT).read_text())
    # Java's two maintained tables each yield one grapevine, without a hand/tool
    # predicate. Explosion handling stays the engine's block-loot responsibility.
    expected = 'kaleidoscope_tavern:grapevine'
    if java_source is not None:
        for name in BLOCKS:
            path = Path(java_source) / 'src/generated/resources/data/kaleidoscope_tavern/loot_tables/blocks' / (name + '.json')
            java = json.loads(path.read_text())
            assert len(java['pools']) == 1
            pool = java['pools'][0]
            assert pool['rolls'] == 1 and len(pool['entries']) == 1
            assert pool['entries'][0] == {'type': 'minecraft:item', 'name': expected}
            assert pool.get('conditions', []) == [{'condition': 'minecraft:survives_explosion'}]
    assert loot == {'pools': [{'rolls': 1, 'entries': [{'type': 'item', 'name': expected, 'weight': 1}]}]}, 'Wild-vine loot must yield one grapevine with no tool predicate'

    return plants


def check(root=ROOT, java_source=None, *, syntax=True):
    root = Path(root)
    plants = check_resources(root, java_source)
    for name in SCRIPTS:
        read_module(root, 'runtime/BP/scripts/' + name, syntax)
    sources = runtime_sources()
    ledger = json.loads((root / 'data/baseline-reconciliation.json').read_text())
    for section in ('files', 'reviewedFunctionalDeltas'):
        assert not sources & set(ledger.get(section, {})), 'Cultivation returned to a historical postimage'
    for section in ('reviewedFunctionalDeltaLayers', 'reviewedAssetDeltaLayers'):
        for layer in ledger.get(section, []):
            assert not sources & set(layer['files']), 'Cultivation returned to a reverse delta'
    reference = json.loads((root / 'data/launch-repair-reference.json').read_text())
    for section in ('reviewedChanges', 'newRuntimeFiles'):
        assert not sources & set(reference[section]), 'Cultivation returned to the historical launch aggregate'
    return {'sources': sorted(sources), 'resources': 'passed', 'plants': plants,
            'behavior': 'actual board-farm-interaction suite, not run by this resource check',
            'bds': False, 'client': False}


if __name__ == '__main__':
    print(json.dumps(check()))
