"""Check the existing aggregate handoff against a supplied complete checkout."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch


def main():
    if sys.flags.optimize:
        raise SystemExit('Assertions must remain active.')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, required=True)
    args = parser.parse_args()
    root = args.repository.resolve()
    sys.path.insert(0, str(root / 'tools'))
    from reviewed_changes import historical_files, historical_digest, current_contract_sources
    read = lambda path: json.loads(path.read_bytes())
    receipt = read(Path(__file__).with_name('ownership-handoff.json'))
    motion = read(root / 'data/motion-source-reference.json')
    scope = motion['historicalPreservedGroups']['runtime/BP/blocks']
    launch = read(root / 'data/launch-repair-reference.json')
    retired = receipt['retired_historical_beforeProjected']
    assert set(retired) <= current_contract_sources()
    assert all(scope['originalFiles'][path] == digest for path, digest in retired.items())
    def fingerprint(rows):
        raw = ''.join(path + '\0' + digest + '\n' for path, digest in sorted(rows.items())).encode()
        return {'files': len(rows), 'sha256': hashlib.sha256(raw).hexdigest()}
    rows = {p.relative_to(root).as_posix(): historical_digest(p, projected=True) for p in historical_files('runtime/BP/blocks')}
    assert fingerprint(rows) == motion['preservedGroups']['runtime/BP/blocks'] == receipt['current_remaining_group']
    rows.update(retired)
    assert fingerprint(rows) == receipt['base_remaining_group']
    for path in scope['retiredToCurrentContract']:
        rows[path] = scope['originalFiles'].get(path) or launch['historicalChanges'][path]['beforeProjected']
    assert fingerprint(rows) == scope['original'] == receipt['unchanged_original_group']
    target = root / 'runtime/BP/blocks/trellis.json'
    original = target.read_bytes()
    changed = read(target)
    changed['minecraft:block']['components']['minecraft:light_dampening'] = 1
    mutant = (json.dumps(changed, indent=2) + '\n').encode()
    assert mutant != original
    reader = Path.read_bytes
    with patch.object(Path, 'read_bytes', lambda p: mutant if p == target else reader(p)):
        try:
            historical_digest(target, projected=True)
        except AssertionError as error:
            assert 'Reconciled source mutated' in str(error)
        else:
            raise AssertionError('Remaining historical block mutation was accepted')
    assert target.read_bytes() == original
    print(json.dumps({'base_remaining_files': 149, 'remaining_files': 145,
                      'original_files': 159, 'retired_paths': 4,
                      'remaining_historical_mutation': 'rejected', 'disk_modified': False}))


if __name__ == '__main__':
    main()
