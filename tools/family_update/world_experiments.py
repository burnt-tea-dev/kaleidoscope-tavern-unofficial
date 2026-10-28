"""Source-bound experiment flags in the existing stopped-save transaction.

Only the exact reviewed curated selection supplies flags. The existing backup,
saved-world report and deployment result carry this small metadata transition;
no arbitrary flag configuration or alternate world/admission path is accepted.
"""
import copy
import hashlib
import os
import re
import struct
from pathlib import Path

from family_update import common as c

HISTORY_FLAGS = ('experiments_ever_used', 'saved_with_toggled_experiments')


def required():
    from family_update.current_author_validation import curated_selected, current_selection
    if not c.EXTENSION or not curated_selected():
        return {}
    flags = current_selection().get('required_experiments', {})
    if (not isinstance(flags, dict) or any(not isinstance(name, str)
            or not re.fullmatch('[a-z][a-z0-9_]*', name) or name in HISTORY_FLAGS
            or value is not True for name, value in flags.items())):
        raise ValueError('Reviewed required_experiments must contain only named true flags')
    return dict(flags)


def metadata(raw):
    from author_state_migration import StrictNBTStream
    from bedrock_nbt import parse_root
    if len(raw) < 9 or struct.unpack('<I', raw[4:8])[0] != len(raw) - 8:
        raise ValueError('Invalid level.dat header or body length')
    stream = StrictNBTStream(raw[8:])
    data = parse_root(stream)
    if stream.tell() != len(raw) - 8:
        raise ValueError('Unparsed level.dat suffix')
    return data


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def transition(raw, flags):
    """Keep every unrelated typed tag and opaque byte; enable declared flags."""
    import nbtlib
    from bedrock_nbt import encode_root
    data = metadata(raw)
    original = copy.deepcopy(data)
    experiments = data.get('experiments', nbtlib.Compound())
    if not isinstance(experiments, nbtlib.Compound):
        raise ValueError('World experiments must be an NBT compound')
    changed = {}
    for name in sorted(set(flags) | (set(HISTORY_FLAGS) if flags else set())):
        previous = experiments.get(name)
        if previous is not None and (type(previous) is not nbtlib.Byte or int(previous) not in (0, 1)):
            raise ValueError('Invalid experiment flag representation: ' + name)
        if previous is None or int(previous) != 1:
            changed[name] = {'before': None if previous is None else int(previous), 'after': 1}
            experiments[name] = nbtlib.Byte(1)
    if changed:
        data['experiments'] = experiments
    # parse_root already refused any input that cannot round-trip losslessly.
    # Compare the entire typed root after reversing only our declared fields.
    restored = copy.deepcopy(data)
    if 'experiments' in original:
        restored['experiments'] = original['experiments']
    else:
        restored.pop('experiments', None)
    if encode_root(restored) != raw[8:]:
        raise ValueError('Unrelated level metadata changed')
    for name, value in original.get('experiments', {}).items():
        if name not in changed and encode_root(nbtlib.File({'value': value})) != encode_root(nbtlib.File({'value': experiments[name]})):
            raise ValueError('Unrelated experiment value changed: ' + name)
    body = encode_root(data)
    result = raw if not changed else raw[:4] + struct.pack('<I', len(body)) + body
    return result, {'required': flags, 'changed_flags': changed,
                    'source_level_dat_sha256': digest(raw), 'prepared_level_dat_sha256': digest(result),
                    'unrelated_nbt_byte_preserved': True}


def observe(raw, flags):
    if not flags:
        return None
    import nbtlib
    experiments = metadata(raw).get('experiments', {})
    expected = {name: 1 for name in [*flags, *HISTORY_FLAGS]}
    if any(type(experiments.get(name)) is not nbtlib.Byte or int(experiments[name]) != value
           for name, value in expected.items()):
        raise ValueError('Required native features missing; rehearse the source-declared world experiment migration: ' + ', '.join(flags))
    return expected


def write_metadata(path, raw):
    path = Path(path)
    temporary = path.with_name('level.dat.experiment-stage')
    if path.is_symlink() or temporary.exists() or temporary.is_symlink():
        raise ValueError('World metadata staging path is unsafe or occupied')
    with temporary.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    if path.read_bytes() != raw:
        raise ValueError('World experiment metadata write differs')


def prepare(world):
    flags = required()
    if not flags:
        return None
    expected = c.R / 'saved-world-engine/worlds/Saved World QA'
    if (Path(world) != expected or expected.resolve() != expected
            or expected.resolve() == c.W.resolve() or (expected / 'level.dat').is_symlink()):
        raise ValueError('Experiment preparation is confined to the existing saved-world QA copy')
    raw = (Path(world) / 'level.dat').read_bytes()
    if digest(raw) != c.sha(c.R / 'production-snapshot/level.dat'):
        raise ValueError('Experiment preparation must begin from this stopped snapshot metadata')
    result, proof = transition(raw, flags)
    if proof['changed_flags']:
        write_metadata(Path(world) / 'level.dat', result)
    observe(result, flags)
    return proof


def verify_rehearsal(evidence):
    flags = required()
    proof = evidence.get('world_experiments')
    if not flags:
        if proof is not None:
            raise ValueError('World experiment migration is not declared by this source')
        return None
    if c.CONFIG.get('fresh_world'):
        raise ValueError('Source requires experiments; fresh-world creation has no reviewed flag initialization. Use the existing stopped-save migration path.')
    _, expected = transition((c.R / 'production-snapshot/level.dat').read_bytes(), flags)
    if proof != expected:
        raise ValueError('World experiment transition differs from the exact stopped snapshot/source')
    runs = evidence['runs']
    if [run['phase'] for run in runs] != ['first', 'restart']:
        raise ValueError('World experiments require first-load and same-copy restart')
    observed = {name: 1 for name in [*flags, *HISTORY_FLAGS]}
    if (any(run.get('ok') is not True or any(not isinstance(run.get(field), str)
                    or not re.fullmatch('[0-9a-f]{64}', run[field])
                    for field in ('level_input_sha256', 'level_output_sha256')) for run in runs)
            or runs[0].get('level_input_sha256') != expected['prepared_level_dat_sha256']
            or runs[1].get('level_input_sha256') != runs[0].get('level_output_sha256')
            or any(run.get('world_experiments') != observed for run in runs)):
        raise ValueError('Native runs did not preserve the required world experiments on the same copy')
    return proof


def satisfied():
    """An identical pack inventory is not sufficient if native flags are absent."""
    flags = required()
    if not flags:
        return True
    try:
        observe((c.W / 'level.dat').read_bytes(), flags)
        return True
    except (OSError, ValueError):
        return False


def adoption_recorded():
    path = c.R / 'deployment-result.json'
    return path.is_file() and bool((c.read(path).get('world_experiments') or {}).get('required'))


def adopt(evidence):
    proof = verify_rehearsal(evidence)
    if proof is None:
        return None
    c.assert_lease()
    if c.summary()['status'] != 'STOPPED':
        raise ValueError('World experiment adoption requires the owned stopped maintenance window')
    raw = (c.W / 'level.dat').read_bytes()
    backup = c.read(c.R / 'production-before/backup-receipt.json')
    if digest(raw) != backup['level_dat_sha256'] or digest(raw) != proof['source_level_dat_sha256']:
        raise ValueError('World metadata changed after the consistent stopped backup')
    result, actual = transition(raw, required())
    if actual != proof:
        raise ValueError('Live experiment transition differs from its native rehearsal')
    # Persist before adoption even if all flags were already enabled: the new
    # native runtime may still migrate inventory/block data on first startup.
    # A later failure must never boot an incompatible old pack on that new DB.
    c.atomic(c.R / 'deployment-result.json', {'schema': 1, 'state': 'installing_stopped',
             'world_experiments': proof, 'client': False, 'production_ready': False})
    if proof['changed_flags']:
        write_metadata(c.W / 'level.dat', result)
    observe((c.W / 'level.dat').read_bytes(), required())
    return proof
