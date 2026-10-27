"""Compile a reviewed author pair's manifest-only compatibility release."""
import copy
import hashlib
import json

from family_update.cookery_cache_validation import tree


def compile_pair(author_packs, version, resource_min_engine):
    for value in (version, resource_min_engine):
        if not isinstance(value, list) or len(value) != 3 or any(type(n) is not int or n < 0 for n in value):
            raise ValueError('Manifest compatibility requires explicit version triples')
    by_side = {}
    for manifest, data in author_packs:
        kinds = {module['type'] for module in manifest['modules']}
        side = 'BP' if 'data' in kinds else 'RP' if kinds == {'resources'} else None
        if side is None or side in by_side:
            raise ValueError('Manifest compatibility requires exactly one author BP/RP pair')
        by_side[side] = (manifest, data)
    if set(by_side) != {'BP', 'RP'}:
        raise ValueError('Manifest compatibility requires both author sides')
    uuids = {manifest['header']['uuid'] for manifest, _ in by_side.values()}
    changed = []; before = {}; after = {}; originals = {}; patched = {}
    for side, (manifest, data) in by_side.items():
        original_version = manifest['header']['version']
        if version <= original_version or any(module['version'] != original_version for module in manifest['modules']):
            raise ValueError('Compatibility release requires a fresh paired identity')
        result = copy.deepcopy(manifest)
        result['header']['version'] = version.copy()
        for module in result['modules']:
            module['version'] = version.copy()
        for dependency in result.get('dependencies', []):
            if dependency.get('uuid') in uuids:
                dependency['version'] = version.copy()
        if side == 'RP':
            if 'pbr' not in result.get('capabilities', []) or resource_min_engine < result['header']['min_engine_version']:
                raise ValueError('Compatibility cannot invent PBR support or lower the engine requirement')
            result['header']['min_engine_version'] = resource_min_engine.copy()
        raw = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode()
        payload = {**data, 'manifest.json': raw}
        before[side] = tree({name: hashlib.sha256(value).hexdigest() for name, value in data.items()})
        after[side] = tree({name: hashlib.sha256(value).hexdigest() for name, value in payload.items()})
        originals[side] = hashlib.sha256(data['manifest.json']).hexdigest()
        patched[side] = hashlib.sha256(raw).hexdigest()
        changed.append((result, payload))
    return changed, {'source_trees': before, 'output_trees': after,
                     'original_manifests': originals, 'patched_manifests': patched}


def reviewed_pair(upstream, author_packs, releases):
    release = releases[upstream['manifest_compatibility_release']]
    if any(release[key] != upstream[key] for key in ('project_id', 'file_id', 'sha256')):
        raise ValueError('Compatibility release belongs to a different author archive')
    changed, evidence = compile_pair(author_packs, release['version'], release['resource_min_engine'])
    if any(release[key] != value for key, value in evidence.items()):
        raise ValueError('Compatibility manifests or complete payload trees differ from the reviewed release')
    return changed, copy.deepcopy(release)
