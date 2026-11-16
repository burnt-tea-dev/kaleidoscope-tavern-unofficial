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
