"""Replay catalog-reviewed paired author data changes without importing author code."""
import copy
import hashlib
import json
from datetime import date
from pathlib import Path, PurePosixPath

import stable_host_profiles as stable

DATA_REPAIRS = {
    'dimensions-wine-snow-repair': {
        'author': 'DimensionsWine',
        'files': ('BP/manifest.json', 'RP/manifest.json',
                  'BP/scripts/data/tavern-extension.js', 'BP/scripts/data/guidebook.js',
                  'BP/scripts/custom_components/netherGrapevine.js'),
        'text_replacements': [
            {'path': 'BP/scripts/data/tavern-extension.js',
             'before': '"minecraft:snow_block"', 'after': '"minecraft:snow"'},
            {'path': 'BP/scripts/data/guidebook.js',
             'before': '"minecraft:blue_ice","minecraft:snow_block"]',
             'after': '"minecraft:blue_ice","minecraft:snow"]'},
            {'path': 'BP/scripts/data/guidebook.js',
             'before': '"minecraft:snow_block":"Snow Block"',
             'after': '"minecraft:snow":"Snow Block"'},
            {'path': 'BP/scripts/custom_components/netherGrapevine.js',
             'before': 'onTick({block}){if(!attached(block,c))',
             'after': 'onTick({block}){if(!block.isValid)return;if(!attached(block,c))'},
        ],
    },
}
PAIRED_KINDS = frozenset({
    'chinesefood-doll-renderer-cleanup', 'nether-placeable-drinks-schema-repair',
    'essentials-manifest-compatibility', 'addon-owned-data', *DATA_REPAIRS,
})


def pair_uuids(spec):
    if spec.get('kind') not in PAIRED_KINDS:
        raise ValueError('unknown paired host extension')
    resource = (spec['host_uuid'] if spec['kind'] == 'chinesefood-doll-renderer-cleanup'
                else spec['resource_uuid'])
    return spec['behavior_uuid'], resource


def validate_pair_receipt(spec, receipt, owner_version, pack_version, behavior_uuid, resource_uuid):
    """Schema revision and installed pair version are independent identities."""
    if pair_uuids(spec) != (behavior_uuid, resource_uuid):
        raise ValueError('paired receipt targets another author pair')
    if 'version' in spec and (not _version(receipt.get('version')) or receipt.get('version') != spec['version']):
        raise ValueError('paired receipt declaration revision differs')
    if (not _version(receipt.get('owner_version')) or not _version(receipt.get('local_pack_version'))
            or receipt.get('owner_version') != spec.get('owner_version')
            or receipt.get('owner_version') != owner_version
            or receipt.get('local_pack_version') != spec.get('local_pack_version')
            or receipt.get('local_pack_version') != pack_version):
        raise ValueError('paired receipt owner or installed version differs')
    if spec.get('kind') in DATA_REPAIRS or spec.get('kind') == 'addon-owned-data':
        if receipt.get('official_author_release') is not False:
            raise ValueError('paired data receipt must retain its local author identity')
        for key in ('kind', 'host_uuid', 'behavior_uuid', 'resource_uuid', 'official_author_release'):
            if receipt.get(key) != spec.get(key):
                raise ValueError('paired data receipt identity differs: ' + key)


def _version(value):
    return (isinstance(value, list) and len(value) == 3
            and all(type(part) is int and part >= 0 for part in value))


def _manifest_updates(original, uuids, author_version, local_version, manifest_names):
    """Only own versions and the exact reviewed display names may change."""
    updates = []
    for side in ('BP', 'RP'):
        name = side + '/manifest.json'
        manifest = json.loads(original[name])
        header = manifest.get('header', {})
        if (header.get('uuid') != uuids[side] or not _version(header.get('version'))
                or header.get('version') != author_version):
            raise ValueError('paired author manifest identity differs: ' + side)
        modules = manifest.get('modules')
        dependencies = manifest.get('dependencies', [])
        if (not isinstance(modules, list) or not modules
                or any(not isinstance(row, dict) or not _version(row.get('version'))
                       or row.get('version') != author_version for row in modules)
                or not isinstance(dependencies, list)
                or any(not isinstance(row, dict) for row in dependencies)):
            raise ValueError('paired author module or dependency declaration differs')
        pointers = [['header', 'version']]
        pointers += [['modules', str(index), 'version'] for index in range(len(modules))]
        for index, dependency in enumerate(dependencies):
            if dependency.get('uuid') in uuids.values():
                if not _version(dependency.get('version')) or dependency.get('version') != author_version:
                    raise ValueError('paired author dependency version differs')
                pointers.append(['dependencies', str(index), 'version'])
        updates.extend({'path': name, 'pointer': pointer, 'mode': 'reviewed_set',
                        'value': local_version} for pointer in pointers)
        updates.append({'path': name, 'pointer': ['header', 'name'], 'mode': 'reviewed_set',
                        'value': manifest_names[side]})
    return updates


def apply_owned_data_extension(spec, owned_root, bp_root, rp_root, bp_source, rp_source, owner_version):
    """Install committed data into its owning pair after the host's script repairs.

    Exact preimages prevent a full definition from hiding a newer host change.
    Source files are ordinary addon data, not another patch implementation.
    """
    if (spec.get('kind') != 'addon-owned-data' or spec.get('schema') != 1
            or spec.get('owner_version') != owner_version
            or any(not _version(spec.get(key)) for key in ('version', 'owner_version', 'local_pack_version'))
            or spec.get('official_author_release') is not False):
        raise ValueError('invalid addon-owned data identity')
    profile = stable.match_stable_profile(spec, owned_root)
    if profile is None or profile.get('admission') != stable.CURATED:
        raise ValueError('addon-owned data requires its committed reviewed declaration')
    stable.validate_stable_source(profile, bp_source)
    if any(source.get('archive_sha256') != spec.get('archive_sha256')
           or source.get('owner') not in ('upstream', 'upstream_extended', 'preserved')
           for source in (bp_source, rp_source)):
        raise ValueError('addon-owned data targets another source pair')
    if any(source.get('owner') == 'preserved' for source in (bp_source, rp_source)):
        if any(source.get('owner') != 'preserved'
               or source.get('role') != 'owner_accepted_author_replacement'
               or source.get('official_author_release') is not False
               for source in (bp_source, rp_source)):
            raise ValueError('addon-owned data requires the complete accepted replacement pair')
    sources = spec.get('source_files')
    before, after = spec.get('original_files'), spec.get('patched_files')
    if (not isinstance(sources, dict) or not sources or set(sources) != set(before or {})
            or set(sources) != set(after or {})
            or not {'BP/manifest.json', 'RP/manifest.json'} <= set(sources)
            or spec.get('copies', {}) or spec.get('removed_files', {})):
        raise ValueError('addon-owned data requires exact paired input and output files')
    roots = {'BP': Path(bp_root), 'RP': Path(rp_root)}
    def local_path(root, name, *, must_exist=True):
        if not isinstance(name, str) or '\\' in name:
            raise ValueError('invalid addon-owned data path')
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or relative.as_posix() != name:
            raise ValueError('addon-owned data path escapes source')
        path = root
        for part in relative.parts:
            path = path / part
            if path.is_symlink():
                raise ValueError('linked addon-owned data path')
        if must_exist and not path.is_file():
            raise ValueError('addon-owned data file is missing: ' + name)
        return path
    paths, originals, changed = {}, {}, {}
    for name, source_name in sources.items():
        side, relative = name.split('/', 1)
        if side not in roots:
            raise ValueError('unknown addon-owned data pack side')
        path = local_path(roots[side], relative, must_exist=before[name] is not None)
        if before[name] is None and path.exists():
            raise ValueError('addon-owned data addition is occupied: ' + name)
        raw = path.read_bytes() if before[name] is not None else None
        replacement = local_path(Path(owned_root), source_name).read_bytes()
        if (hashlib.sha256(raw).hexdigest() if raw is not None else None) != before[name]:
            raise ValueError('addon-owned data preimage differs: ' + name)
        if hashlib.sha256(replacement).hexdigest() != after[name]:
            raise ValueError('addon-owned data source differs: ' + name)
        paths[name], originals[name], changed[name] = path, raw, replacement
    uuids = dict(zip(('BP', 'RP'), pair_uuids(spec)))
    author_version = json.loads(originals['BP/manifest.json'])['header']['version']
    updates = _manifest_updates(originals, uuids, author_version, spec['local_pack_version'], spec['manifest_names'])
    for side in ('BP', 'RP'):
        name = side + '/manifest.json'
        expected = json.loads(originals[name])
        for operation in updates:
            if operation['path'] != name:
                continue
            target = expected
            for key in operation['pointer'][:-1]:
                target = target[int(key)] if isinstance(target, list) else target[key]
            target[operation['pointer'][-1]] = copy.deepcopy(operation['value'])
        if json.loads(changed[name]) != expected:
            raise ValueError('addon-owned data changes manifest identity or unrelated metadata')
    for name, raw in changed.items():
        paths[name].parent.mkdir(parents=True, exist_ok=True)
        paths[name].write_bytes(raw)
    return {key: copy.deepcopy(value) for key, value in spec.items() if key != 'source_files'}


def apply_paired_data_extension(spec, bp_root, rp_root, bp_source, rp_source, owner_version):
    """Validate both inputs and all reviewed outputs before writing the candidate."""
    policy = DATA_REPAIRS.get(spec.get('kind'))
    if (policy is None or type(spec.get('schema')) is not int or spec['schema'] != 1
            or spec.get('id') != 'senluo:' + spec['kind']):
        raise ValueError('unknown paired data extension')
    if any(not _version(value) for value in (spec.get('version'), owner_version,
                                             spec.get('owner_version'), spec.get('local_pack_version'))):
        raise ValueError('paired data extension needs explicit version triples')
    profile = stable.match_stable_profile(spec)
    if profile is None or profile.get('admission') != stable.CURATED:
        raise ValueError('paired data extension requires its exact reviewed profile')
    author = stable.CATALOG[stable.CURATED_KEY]['authors'][policy['author']]
    uuids = {'BP': author['behavior_uuid'], 'RP': author['resource_uuid']}
    if (pair_uuids(spec) != (uuids['BP'], uuids['RP']) or spec.get('host_uuid') != uuids['RP']
            or any(profile.get(key) != spec.get(key) for key in
                   ('id', 'kind', 'version', 'host_uuid', 'behavior_uuid', 'resource_uuid',
                    'owner_version', 'local_pack_version', 'archive_sha256'))
            or profile.get('owner_version') != owner_version or profile.get('copies') != {}
            or spec['local_pack_version'] == author['author_version']
            or spec.get('archive_sha256') != author['sha256']
            or spec.get('official_author_release') is not False
            or profile.get('official_author_release') is not False):
        raise ValueError('paired data identity differs from the reviewed author/owner')
    names = profile.get('manifest_names')
    if (not isinstance(names, dict) or set(names) != {'BP', 'RP'}
            or any(not isinstance(value, str) or not value.strip() or '\n' in value or '\x00' in value
                   for value in names.values())):
        raise ValueError('paired data requires exact reviewed manifest names')
    if date.fromisoformat(spec['expires']) < date.today():
        raise ValueError('paired data extension expired')
    for key in ('authorization', 'feedback', 'removal_condition'):
        if not isinstance(spec.get(key), str) or not spec[key].strip():
            raise ValueError('paired data review metadata missing: ' + key)
    for source in (bp_source, rp_source):
        if (source.get('owner') != 'upstream' or source.get('project_id') != author['project_id']
                or source.get('file_id') != author['file_id'] or source.get('archive_sha256') != author['sha256']
                or source.get('reviewed_extensions', []) != []):
            raise ValueError('paired data requires both exact clean author sources')
        stable.validate_stable_source(profile, source)
    if (set(spec.get('original_files', {})) != set(policy['files'])
            or set(spec.get('patched_files', {})) != set(policy['files'])
            or spec.get('copies') != {} or spec.get('imports') != {} or spec.get('insertions') != []
            or spec.get('removed_files', {}) or spec.get('host_copies', {})
            or spec.get('text_replacements') != policy['text_replacements']):
        raise ValueError('paired data paths or operations exceed the reviewed repair')
    roots = {'BP': Path(bp_root), 'RP': Path(rp_root)}
    paths, original = {}, {}
    for name in policy['files']:
        side, relative = name.split('/', 1)
        root = roots[side]
        path = root / relative
        chain = [root, *[root.joinpath(*Path(relative).parts[:index])
                         for index in range(1, len(Path(relative).parts) + 1)]]
        if any(part.is_symlink() for part in chain) or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('paired data preimage missing or outside pack: ' + name)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != spec['original_files'][name]:
            raise ValueError('paired data preimage differs: ' + name)
        paths[name], original[name] = path, raw
    expected_updates = _manifest_updates(original, uuids, author['author_version'], spec['local_pack_version'], names)
    if spec.get('json_updates') != expected_updates:
        raise ValueError('paired data permits only reviewed own manifest version updates')
    changed = {}
    for name, raw in original.items():
        text = raw.decode('utf-8-sig')
        updates = [op for op in expected_updates if op['path'] == name]
        if updates:
            value = json.loads(text)
            for operation in updates:
                target = value
                for key in operation['pointer'][:-1]:
                    target = target[int(key)] if isinstance(target, list) else target[key]
                target[operation['pointer'][-1]] = copy.deepcopy(operation['value'])
            text = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
        for operation in spec['text_replacements']:
            if operation['path'] == name:
                if text.count(operation['before']) != 1:
                    raise ValueError('paired data replacement anchor is not unique: ' + name)
                text = text.replace(operation['before'], operation['after'], 1)
        changed[name] = text.encode()
        if hashlib.sha256(changed[name]).hexdigest() != spec['patched_files'][name]:
            raise ValueError('paired data reviewed output differs: ' + name)
    for name, raw in changed.items():
        paths[name].write_bytes(raw)
    receipt = {key: copy.deepcopy(value) for key, value in spec.items()
               if key not in ('imports', 'insertions', 'json_updates', 'text_replacements')}
    receipt['spec_sha256'] = stable.declaration_sha(spec)
    return receipt
