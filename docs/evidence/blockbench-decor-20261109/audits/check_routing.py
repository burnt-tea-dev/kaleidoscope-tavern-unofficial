"""Enumerate all native state bindings and verify independently authored state selection."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import copy, hashlib, itertools, json, re, subprocess
H = Path(__file__).resolve().parent
ROOT = H.parent / 'tavern-visual-review-20261108/source'
JAVA = H.parent / 'tavern-visual-review-20261108/java-reference'
from portable_context import mapped_manifest
M = mapped_manifest(H / 'manifest.json')
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
terrain = read(ROOT / 'runtime/RP/textures/terrain_texture.json')['texture_data']
geo = {}
for p in (ROOT / 'runtime/RP/models').rglob('*.json'):
    for g in read(p).get('minecraft:geometry', []):
        geo[g['description']['identifier']] = g

def evaluate(text, states):
    text = re.sub(r"q\.block_state\('([^']+)'\)", lambda m: repr(states[m[1]]), text)
    text = text.replace('&&', ' and ').replace('||', ' or ')
    text = re.sub(r'\btrue\b', 'True', text)
    text = re.sub(r'\bfalse\b', 'False', text)
    return eval(text, {'__builtins__': {}}, {})

def check_block(name):
    bp = ROOT / 'runtime/BP/blocks' / (name + '.json')
    b = read(bp)['minecraft:block']
    declared = copy.deepcopy(b['description'].get('states', {}))
    traits = b['description'].get('traits', {})
    if 'minecraft:cardinal_direction' in traits.get('minecraft:placement_direction', {}).get('enabled_states', []):
        declared['minecraft:cardinal_direction'] = ['north', 'east', 'south', 'west']
    rows = []
    model_set = {c['binding']['geometry_id'] for c in M['cases'] if c['block'] == name}
    for vals in itertools.product(*declared.values()):
        state = dict(zip(declared, vals))
        c = copy.deepcopy(b['components'])
        matched = []
        for p in b.get('permutations', []):
            if evaluate(p['condition'], state):
                c.update(p['components'])
                matched.append(p['condition'])
        gid = c['minecraft:geometry']['identifier']
        assert gid in model_set, (name, state, 'Uncovered distinct model')
        materials = c['minecraft:material_instances']
        for bone in geo[gid]['bones']:
            for cube in bone.get('cubes', []):
                for f in cube['uv'].values():
                    tag = f.get('material_instance', '*')
                    assert tag in materials, (name, tag)
                    texture = terrain[materials[tag]['texture']]['textures']
                    assert isinstance(texture, str) and (ROOT / 'runtime/RP' / (texture + '.png')).is_file()
        rows.append({'states': state, 'geometry': gid, 'matched_conditions': matched,
                     'transformation': c.get('minecraft:transformation'), 'material_instances': materials})
    source_name = 'string_lights_' + name.removeprefix('light_') if name.startswith('light_') else name
    jp = JAVA / 'src/generated/resources/assets/kaleidoscope_tavern/blockstates' / (source_name + '.json')
    j = read(jp)
    rel = str(jp.relative_to(JAVA))
    source_checks = {}
    for branch in ('Forge', 'NeoForge'):
        raw = (H.parent / 'pinned-source' / branch / rel).read_bytes()  # Same pinned bytes, bounded offline snapshot.
        source_checks[branch] = {'sha256': hashlib.sha256(raw).hexdigest(), 'json_equal_to_reviewed_worktree': json.loads(raw) == j}
        assert source_checks[branch]['json_equal_to_reviewed_worktree']
    source_cases = []
    for case in [c for c in M['cases'] if c['block'] == name]:
        n = case['states']
        if name == 'table':
            source_state = {'axis': 'z' if n['cardinal_direction'] in ('east', 'west') else 'x', 'position': str(n['position']), 'waterlogged': 'false'}
        elif name.startswith('light_'):
            source_state = {'facing': 'north', 'waterlogged': 'false'}
        elif name.endswith('_incense'):
            source_state = {'facing': 'north', 'open': str(bool(n['open'])).lower(), 'powered': 'false'}
        elif name.endswith('_crop'):
            source_state = {'age': str(n['age'])}
        elif name == 'trellis':
            source_state = {'type': n['shape'], 'waxed': 'false', 'waterlogged': 'false'}
        else:
            source_state = {'type': n['shape'], 'age': str(n['age']), 'waterlogged': 'false'}
        key = ','.join(k + '=' + str(v) for k, v in sorted(source_state.items()))
        assert key in j['variants'], (name, key)
        actual = j['variants'][key]
        expected = 'kaleidoscope_tavern:' + str(Path(case['source_model']).relative_to(JAVA / 'src/main/resources/assets/kaleidoscope_tavern/models')).removesuffix('.json')
        assert actual['model'] == expected and actual.get('x', 0) == 0 and actual.get('y', 0) == 0, (name, key, actual, expected)
        source_cases.append({'label': case['label'], 'source_state_key': key, 'source_variant': actual})
    return {'block': name, 'bp_sha256': sha(bp), 'source_blockstate': str(jp), 'source_worktree_sha256': sha(jp),
            'source_pinned_checks': source_checks, 'paired_cases': source_cases, 'native_combinations': rows}

names = sorted(set(c['block'] for c in M['cases']))
with ThreadPoolExecutor(max_workers=8) as pool:
    results = list(pool.map(check_block, names))
summary = {'blocks': len(results), 'native_state_combinations': sum(len(r['native_combinations']) for r in results),
           'independently_verified_source_state_pairs': sum(len(r['paired_cases']) for r in results),
           'all_distinct_native_models_covered_by_scenes': True, 'all_geometry_material_texture_bindings_resolved': True,
           'all_source_blockstates_equal_pinned_forge_and_neoforge_json': True, 'runtime_or_gui_execution': False}
(H.parent / 'rerun' / 'routing-validation.json').write_text(json.dumps({'summary': summary, 'blocks': results}, indent=2)+'\n')
print(json.dumps(summary, indent=2))
