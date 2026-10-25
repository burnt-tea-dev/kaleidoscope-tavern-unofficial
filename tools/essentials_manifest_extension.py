"""Exact Essentials 1.8.3 paired identity and PBR manifest compatibility.

The clean author archive owns every script and asset. This declaration changes
only paired versions and the two RP fields required by the current PBR stack.
"""
import copy
import hashlib
import json
from datetime import date
from pathlib import Path

KIND = 'essentials-manifest-compatibility'
IDENTITY = 'senluo:' + KIND
ARCHIVE = '7b8a599d7d4ceda6ae403e66e2897fe6262e98d4b7e45c1628bd756d0240413c'
UUIDS = {'BP': '5f808eda-2eed-47b9-94ca-8486af1c5c14',
         'RP': '537af6fe-a865-4603-8847-37791b81249d'}
ORIGINALS = {'BP/manifest.json': '1e28288471494a49c3368aa25ae7ae6eba08bc17247215996c164c9c417dfc7f',
             'RP/manifest.json': '4e1b0f45dcfef21d533e2ffc9cc5293c97d8061b670452b30eee3b161cd0ccf5'}
OWNER = [1, 0, 66]
TARGET = [1, 8, 10066]


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def compile_spec(raw_pair, owner_version, local_pack_version):
    """Compile the explicitly allocated pair from its exact official manifests."""
    if owner_version != OWNER or local_pack_version != TARGET:
        raise ValueError('Essentials requires the explicitly reviewed owner and paired version')
    if set(raw_pair) != {'BP', 'RP'}:
        raise ValueError('Essentials requires both clean author manifests')
    changed = {}
    for side, raw in raw_pair.items():
        name = side + '/manifest.json'
        if _sha(raw) != ORIGINALS[name]:
            raise ValueError('Essentials clean author manifest differs: ' + side)
        value = json.loads(raw)
        value['header']['version'] = TARGET.copy()
        for module in value['modules']:
            module['version'] = TARGET.copy()
        for dependency in value.get('dependencies', []):
            if dependency.get('uuid') in UUIDS.values():
                dependency['version'] = TARGET.copy()
        if side == 'RP':
            value['capabilities'] = ['pbr']
            value['header']['min_engine_version'] = [1, 21, 120]
        changed[name] = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
    spec = {
        'schema': 1, 'kind': KIND, 'id': IDENTITY, 'version': [1, 0, 1],
        'host_uuid': UUIDS['RP'], 'behavior_uuid': UUIDS['BP'], 'resource_uuid': UUIDS['RP'],
        'archive_sha256': ARCHIVE, 'owner_version': OWNER.copy(), 'local_pack_version': TARGET.copy(),
        'official_author_release': False, 'expires': '2026-11-24',
        'authorization': 'Owner explicitly allocates Essentials 1.8.10066 for fresh-world manifest compatibility with private owner 1.0.66; clean official 8837761 scripts and assets remain unchanged.',
        'feedback': 'Manifest compatibility only; upstream feedback pending.',
        'removal_condition': 'Re-review on an author update; remove the compatibility fields when the clean official RP satisfies the reviewed PBR stack.',
        'original_files': ORIGINALS.copy(),
        'patched_files': {name: _sha(raw) for name, raw in changed.items()},
        'copies': {}, 'imports': {}, 'insertions': [],
    }
    return spec, changed


def apply_manifest_extension(spec, bp_root, rp_root, bp_source, rp_source, owner_version):
    """Validate the complete reviewed pair before changing either manifest."""
    from stable_host_profiles import CURATED, declaration_sha, match_stable_profile, validate_stable_source
    roots = {'BP': Path(bp_root), 'RP': Path(rp_root)}
    raw_pair = {side: (root / 'manifest.json').read_bytes() for side, root in roots.items()}
    expected, changed = compile_spec(raw_pair, owner_version, spec.get('local_pack_version'))
    if spec != expected:
        raise ValueError('Essentials declaration changes more than the reviewed manifests')
    if date.fromisoformat(spec['expires']) < date.today():
        raise ValueError('Essentials manifest compatibility expired')
    profile = match_stable_profile(spec)
    if profile is None or profile.get('admission') != CURATED or profile.get('owner_version') != OWNER:
        raise ValueError('Essentials manifest compatibility requires its reviewed current profile')
    for source in (bp_source, rp_source):
        if (source.get('owner') != 'upstream' or source.get('archive_sha256') != ARCHIVE
                or source.get('project_id') != 1285412 or source.get('file_id') != 8837761):
            raise ValueError('Essentials requires the exact clean official source')
        validate_stable_source(profile, source)
    for name, raw in changed.items():
        side, relative = name.split('/', 1)
        (roots[side] / relative).write_bytes(raw)
    receipt = {key: copy.deepcopy(value) for key, value in spec.items()
               if key not in ('imports', 'insertions')}
    receipt['spec_sha256'] = declaration_sha(spec)
    return receipt
