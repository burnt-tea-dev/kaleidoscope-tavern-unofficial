#!/usr/bin/env python3
"""Replace the one retained world backup after verifying its replacement.

The local state names backup roots and protected original worlds. Producers
share this index; old operation logs are not dependencies of backup retention.
"""
import argparse
import datetime
import fcntl
import json
import os
from pathlib import Path
import shutil

from family_guard import atomic, hashes, read


def capture(world, destination, receipt):
    world, destination, receipt = map(Path, (world, destination, receipt))
    if not (world / 'level.dat').is_file() or not (world / 'db/CURRENT').is_file():
        raise ValueError('Source is not a complete world')
    files = hashes(world)
    shutil.copytree(world, destination)
    if hashes(destination) != files or hashes(world) != files:
        raise ValueError('World changed or backup copy differs')
    atomic(receipt, {'world': str(world.resolve()),
                     'consistent_stopped_snapshot': str(destination.resolve()),
                     'status': 'consistent_stopped_backup', 'live_status': 'STOPPED',
                     'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     'files': files})


def verify(backup, receipt):
    backup, receipt = Path(backup), Path(receipt)
    data = read(receipt)
    files = data['files']
    if (backup.is_symlink() or receipt.is_symlink()
            or not {'level.dat', 'db/CURRENT'} <= files.keys()
            or hashes(backup) != files):
        raise ValueError('Replacement world backup is incomplete or changed')
    return data


def overlaps(first, second):
    return first == second or first in second.parents or second in first.parents


def retirement_target(path, roots, protected):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('Backup paths must be explicit absolute paths')
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise ValueError('Backup retirement cannot follow symlinks: ' + str(path))
    if not any(root in path.parents for root in roots):
        raise ValueError('Backup is outside the configured backup roots: ' + str(path))
    if any(overlaps(path, keep) for keep in protected):
        raise ValueError('Backup retirement overlaps a protected world or replacement')
    if not path.exists():
        return path
    if path.is_file():
        if not path.name.endswith(('.tar', '.tar.gz', '.tgz', '.zip', '.mcworld')):
            raise ValueError('Only complete-world archive payloads may be retired')
    elif not path.is_dir() or not (path / 'level.dat').is_file() or not (path / 'db').is_dir():
        raise ValueError('Only a complete-world backup directory may be retired')
    for current, directories, files in os.walk(path):
        for name in directories + files:
            child = Path(current) / name
            if child.is_symlink() or os.path.ismount(child):
                raise ValueError('Backup contains a symlink or mount: ' + str(child))
    if os.path.ismount(path):
        raise ValueError('Backup is a mount')
    return path


def register_alias(state_path, backup, alias):
    """Track a verified hardlink view so replacing the snapshot retires it too."""
    state_path = Path(state_path)
    with state_path.with_suffix('.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        state = read(state_path)
        current = state['current']
        if Path(current['backup']).resolve() != Path(backup).resolve():
            raise ValueError('Rollback alias belongs to a different retained backup')
        aliases = current.setdefault('aliases', [])
        if str(Path(alias).resolve()) not in aliases:
            aliases.append(str(Path(alias).resolve()))
        atomic(state_path, state)


def adopt(state_path, backup, receipt, retire=()):
    state_path, backup, receipt = map(Path, (state_path, backup, receipt))
    with state_path.with_suffix('.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        state = read(state_path)
        verified = verify(backup, receipt)
        roots = [Path(p).resolve() for p in state['backup_roots']]
        protected = [Path(p).resolve() for p in state['protected_worlds']]
        protected += [Path(verified['world']).resolve(), backup.resolve()]
        previous = state.get('current', {}).get('backup')
        requested = list(state.get('pending_retirement', [])) + list(retire)
        if previous and Path(previous).resolve() != backup.resolve():
            requested.append(previous)
            requested.extend(state['current'].get('aliases', []))
        aliases = state.get('current', {}).get('aliases', []) if previous == str(backup.resolve()) else []
        targets = [retirement_target(p, roots, protected) for p in dict.fromkeys(map(str, requested))]
        state['current'] = {'backup': str(backup.resolve()), 'receipt': str(receipt.resolve()),
                            'aliases': aliases,
                            'world': verified['world'], 'verified_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
        state['pending_retirement'] = [str(p) for p in targets]
        atomic(state_path, state)
        removed = []
        for path in targets:
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
            removed.append(str(path))
            state['pending_retirement'].remove(str(path))
            atomic(state_path, state)
        if removed:
            with state_path.with_suffix('.retired.jsonl').open('a') as log:
                log.write(json.dumps({'at': state['current']['verified_at'], 'kept': str(backup), 'removed': removed}) + '\n')
        return {'retained': str(backup.resolve()), 'retired': removed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--backup', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--capture-stopped-world', type=Path)
    parser.add_argument('--retire-list', type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    retire = read(args.retire_list) if args.retire_list else []
    if not args.execute:
        print(json.dumps({'backup': str(args.backup), 'retire': retire, 'execute': False}))
        return
    if args.capture_stopped_world:
        capture(args.capture_stopped_world, args.backup, args.receipt)
    print(json.dumps(adopt(args.state, args.backup, args.receipt, retire)))


if __name__ == '__main__':
    main()
