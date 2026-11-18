"""The generated pack inputs shared by batch assembly and staging installation."""
import hashlib
import json
from pathlib import Path
import subprocess

from family_guard import hashes, read


def source_provenance(batch, sources, extension=None):
    """Resolve recorded generation commits, independently of current work."""
    selected = batch['source_commits']
    for name, path in sources.items():
        assert Path(selected[name]['path']).resolve() == Path(path).resolve(), 'Batch source path differs: ' + name
    if extension:
        assert any(Path(row['path']).resolve() == Path(extension).resolve() for row in selected.values()), 'Batch omits the configured private integration'
    states = {}
    for name, row in selected.items():
        path = Path(row['path'])
        assert path.is_absolute(), 'Batch source paths must be absolute'
        path = path.resolve()

        def git(*args):
            return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()

        assert git('rev-parse', row['commit'] + '^{commit}') == row['commit'], 'Batch requires a literal source commit: ' + name
        states[name] = {'path': str(path), 'commit': row['commit'], 'tree': git('rev-parse', row['commit'] + '^{tree}')}
        if git('ls-tree', row['commit'], '--', 'baseline.json'):
            states[name]['repository'] = json.loads(git('show', row['commit'] + ':baseline.json'))['repository']
    return states


def pack_tree(files):
    return {'sha256': hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
            'files': len(files)}


def generated_pack(name, side, path):
    """Return the UUID, batch row and file hashes from one generated pack."""
    path = Path(path)
    assert path.is_absolute() and side in {'BP', 'RP'}, 'Generated input needs an absolute pack path and BP/RP side'
    files = hashes(path)
    manifest = read(path / 'manifest.json')
    return manifest['header']['uuid'], {
        'name': name, 'side': side, 'path': str(path),
        'version': manifest['header']['version'], 'modules': manifest['modules'],
        'dependencies': manifest.get('dependencies', []), 'tree': pack_tree(files)}, files


def project_staging(inventory, updates, retired):
    """Replace only explicit payloads and keep the observed selection order."""
    installed = {row['uuid']: row for row in inventory['packs']}
    assert len(installed) == len(inventory['packs']), 'Installed identities are ambiguous'
    assert set(updates) <= installed.keys(), 'Specified replacement has no selected destination'
    assert not set(updates).intersection(retired), 'A pack cannot be updated and retired together'
    changed, packs, refs = [], [], {}
    for side, rows in inventory['refs'].items():
        refs[side] = []
        for ref in rows:
            uid = ref['pack_id']
            if uid in retired:
                continue
            old = installed[uid]
            target = updates.get(uid)
            if target is None:
                packs.append(old)
                refs[side].append(ref)
                continue
            assert old['side'] == target['side'], 'Pack side migration is not supported: ' + uid
            packs.append({**target, 'path': old['path']})
            refs[side].append({**ref, 'version': target['version']})
            if old['files'] != target['files']:
                changed.append(uid)
    return {'packs': packs, 'refs': refs}, changed


def staging_advisories(prior, inventory, updates):
    previous = {row['uuid']: row for row in prior['packs']}
    current = {row['uuid']: row for row in inventory['packs']}
    order = {side: [ref['pack_id'] for ref in refs] for side, refs in inventory['refs'].items()}
    old_order = prior.get('order')
    if old_order is None:
        old_order = {side: [ref['pack_id'] for ref in refs] for side, refs in prior['refs'].items()}
    drift = []
    for uid, row in current.items():
        old = previous.get(uid)
        if old is None or any(row[key] != old[key] for key in ('version', 'side', 'files')):
            drift.append({'uuid': uid, 'previous': old['version'] if old else None,
                          'installed': row['version'], 'specified_update': uid in updates})
    versions = [{'uuid': uid, 'installed': current[uid]['version'], 'requested': row['version']}
                for uid, row in updates.items()
                if current[uid]['files'] != row['files'] and current[uid]['version'] >= row['version']]
    ref_versions = [{'uuid': ref['pack_id'], 'ref': ref['version'],
                     'installed': current[ref['pack_id']]['version']}
                    for refs in inventory['refs'].values() for ref in refs
                    if ref['version'] != current[ref['pack_id']]['version']]
    return {'installed_changes': drift, 'removed': sorted(previous.keys() - current.keys()),
            'order_changed': [side for side in order if order[side] != old_order[side]],
            'replacement_versions': versions, 'reference_versions': ref_versions}
