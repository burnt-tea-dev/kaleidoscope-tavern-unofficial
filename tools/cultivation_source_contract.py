"""Current cultivation ownership and Java-backed wild-vine resources.

Actual adapters run in board-farm-interaction.test.mjs; native destruction and
cascade evidence is recorded separately. No old source body is reconstructed.
"""
import json
from pathlib import Path
from foundation.source_contract import read_module

ROOT = Path(__file__).resolve().parents[1]
BLOCKS = ('wild_grapevine', 'wild_grapevine_plant')
LOOT = 'loot_tables/blocks/wild_grapevine.json'
SCRIPTS = ('bedrock/cultivation.js', 'bedrock/protected-break-router.js')


def runtime_sources():
    return frozenset({'runtime/BP/blocks/' + name + '.json' for name in BLOCKS}
                     | {'runtime/BP/' + LOOT}
                     | {'runtime/BP/scripts/' + name for name in SCRIPTS})


def check_resources(root=ROOT, java_source=None):
    root = Path(root)
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


def check(root=ROOT, java_source=None, *, syntax=True):
    root = Path(root)
    check_resources(root, java_source)
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
    return {'sources': sorted(sources), 'resources': 'passed',
            'behavior': 'actual board-farm-interaction suite, not run by this resource check',
            'bds': False, 'client': False}


if __name__ == '__main__':
    print(json.dumps(check()))
