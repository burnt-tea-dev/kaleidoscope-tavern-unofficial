"""Current foundation ownership/wiring; behavior runs in the foundation CI lane.

This checks exact domain paths and SDK consumer bytes, never a historical
postimage, reverse delta, release number, or directory-wide exception.
"""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = 'runtime/BP/scripts/bedrock/foundation-bridge.js'
FURNITURE = 'runtime/BP/scripts/bedrock/extension-furniture.js'
SDK = 'sdk/tavern-foundation-client.js'
CONSUMER = 'runtime/BP/scripts/sdk/tavern-foundation-client.js'


def runtime_sources():
    return frozenset({BRIDGE, FURNITURE})


def read_module(root, name, syntax):
    path = root / name
    assert path.is_file() and not path.is_symlink(), ('Missing current foundation module', name)
    if syntax:
        subprocess.run(['node', '--check', str(path)], check=True, capture_output=True, text=True)
    return path.read_text()


def imported(text, module, names):
    matches = re.findall(r"import\s*\{([^}]+)\}\s*from\s*['\"]([^'\"]+)['\"]", text)
    found = {name.strip().split(' as ')[0] for body, path in matches if path == module for name in body.split(',')}
    assert set(names) <= found, ('Foundation owner import differs', module, sorted(set(names) - found))


def check(root=ROOT, consumer=None, *, syntax=True):
    root = Path(root)
    bridge = read_module(root, BRIDGE, syntax)
    furniture = read_module(root, FURNITURE, syntax)
    sdk = read_module(root, SDK, syntax)
    entrypoint = read_module(root, 'runtime/BP/scripts/main.js', False)
    imported(bridge, '../core/transport.js', {'ExtensionTransport'})
    imported(bridge, './custom-effects.js', {'importExternalEffects', 'statusNow', 'effectSnapshotEntities'})
    assert 'furniture.importSnapshot(row)' in bridge and 'furniture.nativeUse(' in bridge
    imported(furniture, './native-item-storage.js', {'nativeStorageView'})
    imported(furniture, '../core/extension-storage.js', {'ExtensionCabinetStore'})
    imported(furniture, '../core/native-item-storage.js', {'NATIVE_ITEM_ENTITY', 'NATIVE_STORAGE_OWNER', 'nativeItemKey'})
    assert 'nativeStorageView(new ExtensionCabinetStore(' in furniture
    assert 'store.importLegacy(row.raw' in furniture
    imported(sdk, './protocol.js', {'packetsFor'})
    imported(sdk, './util.js', {'canonical', 'digest', 'utf8Bytes'})
    assert 'world.getDynamicProperty(key)===raw' in sdk, 'ACK must retain a changed owner copy'
    assert "NS+'foundation_native_use'" in sdk, 'Native interaction must keep its direct transport'
    imported(entrypoint, './bedrock/foundation-bridge.js', {'installFoundationBridge'})
    imported(entrypoint, './bedrock/extension-furniture.js', {'installExtensionFurniture'})
    assert entrypoint.count('installFoundationBridge(registry,extensionFurniture)') == 1
    ledger = json.loads((root / 'data/baseline-reconciliation.json').read_text())
    assert not (runtime_sources() & set(ledger['files'])), 'Current foundation domain returned to a historical postimage guard'
    for layer in ledger.get('reviewedFunctionalDeltaLayers', []):
        assert not (runtime_sources() & set(layer['files'])), 'Current foundation domain returned to a reverse delta'
    if consumer is not None:
        consumer = Path(consumer)
        consumer_sdk = read_module(consumer, CONSUMER, syntax)
        assert consumer_sdk == sdk, 'Foundation SDK consumer differs from its shared owner'
        consumer_owner = read_module(consumer, 'runtime/BP/scripts/foundation.js', False)
        imported(consumer_owner, './sdk/tavern-foundation-client.js', {'createFoundationClient'})
        assert 'bridge=createFoundationClient(' in consumer_owner
        consumer_ledger = json.loads((consumer / 'data/baseline-reconciliation.json').read_text())
        assert CONSUMER not in consumer_ledger['files'], 'SDK consumer returned to a historical postimage guard'
    return {'sources': sorted(runtime_sources()), 'sdkOwner': SDK,
            'consumer': CONSUMER if consumer is not None else None,
            'syntax': 'passed' if syntax else 'not run', 'ownershipAndWiring': 'passed',
            'behavior': 'actual foundation.test.mjs in the existing foundation CI lane; not run by this static check',
            'nativeInventoryRecovery': False, 'bds': False, 'client': False}


if __name__ == '__main__':
    print(json.dumps(check()))
