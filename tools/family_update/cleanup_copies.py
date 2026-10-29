"""Delete retired deployment copies; current configuration and references stay protected."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

from family_update import common as c
from family_update import retention


def absolute_paths(value):
    if isinstance(value, dict):
        for key, child in value.items():
            # The scan boundary and recorded command arguments are metadata.
            # CI argv paths are not local evidence; explicit report/source refs are.
            if key not in {'retention_root', 'command', 'test_command'}:
                yield from absolute_paths(child)
    elif isinstance(value, list):
        for child in value:
            yield from absolute_paths(child)
    elif isinstance(value, str) and value.startswith('/') and '\n' not in value:
        yield Path(value)


def frozen_source_reports(path, value, read):
    """Read source evidence at the receipt's original commit, never today's file."""
    if path.name != 'reviewed-family-receipt.json':
        return {}
    reports = value.get('evidence', {}).get('reports', [])
    roots = set(c.SOURCES.values()) | ({c.EXTENSION} if c.EXTENSION else set())
    owned = [(row, root) for row in reports for root in roots
             if Path(row['path']).is_relative_to(root)]
    if not owned:
        return {}
    build_path = path.parent / 'build-evidence.json'
    build_ref = next(row for row in reports if row['path'] == str(build_path))
    build = read(build_path)
    assert c.sha(build_path) == build_ref['sha256'], 'Frozen cleanup build evidence changed'
    sources = {Path(row['path']): row for row in build['sources'].values()}
    result = {}
    for row, root in owned:
        reference = Path(row['path'])
        if reference.suffix != '.json':
            continue
        revision = sources[root]['commit']
        assert re.fullmatch(r'[0-9a-f]{40}', revision), 'Invalid frozen cleanup source commit'
        relative = reference.relative_to(root)
        assert '..' not in relative.parts, 'Invalid frozen cleanup source path'
        raw = subprocess.check_output(['git', '-C', str(root), 'show', revision + ':' + relative.as_posix()])
        assert hashlib.sha256(raw).hexdigest() == row['sha256'], 'Frozen cleanup source evidence changed'
        result[reference] = (row['sha256'], json.loads(raw))
    return result


def cleanup_context(track=None):
    # Config changes require a new plan. Policy/lease/source references are read
    # again at each deletion boundary rather than frozen at an earlier dry run.
    def read(path):
        if track:
            track(path, document=True)
        value = c.read(path)
        if track:
            track(path, document=True)
        return value
    def resolve(path):
        if track:
            track(path)
        value = path.resolve()
        if track:
            track(path)
        return value
    current = read(c.CONFIG_PATH)
    if current != c.CONFIG:
        raise RuntimeError('Cleanup configuration changed; plan again')
    paths = set(absolute_paths({key: value for key, value in current.items() if key != 'retention_root'}))
    paths.update(resolve(path) for path in tuple(paths))
    protected = {c.R, c.B, c.W, c.Q, *c.SOURCES.values(), c.CONFIG_PATH}
    if c.EXTENSION:
        protected.add(c.EXTENSION)
    policy_path = c.Q / 'senluo-policy.json'
    historical = set()
    pending = [(path, None) for path in [policy_path, c.T / 'family/upstream.lock.json']]
    pending += [(Path(current[key]), None) for key in ['extension_validation', 'preserved_reconciliation', 'preserved_additions', 'identity_migration', 'container_recovery_plan', 'translation_reconciliation'] if current.get(key)]
    # Follow actual JSON evidence references, including the private validation's
    # still-used source snapshot. Do not traverse arbitrary source/archive dirs.
    seen = set()
    while pending:
        path, frozen = pending.pop()
        # Two historical receipts can bind different bytes at the same path.
        identity = (path, frozen[0] if frozen else None)
        if identity in seen:
            continue
        if len(seen) >= 256:
            raise RuntimeError('Too many cleanup evidence references; review explicitly')
        seen.add(identity)
        value = frozen[1] if frozen else read(path)
        source_reports = frozen_source_reports(path, value, read)
        if path == policy_path or (path.name == policy_path.name and path.parent.name == 'production-before'):
            # Stopped policy snapshots carry the same historical client leaves.
            # Historical client records stay as leaves, not a live dependency
            # chain through an obsolete repair deployment and its rollback.
            history = {key: value[key] for key in ('client_failure_reports', 'client_hud_observations') if key in value}
            leaves = set(absolute_paths(history))
            leaves.update(resolve(ref) for ref in tuple(leaves))
            historical.update(leaves)
            protected.update(leaves)
            value = {key: child for key, child in value.items() if key not in history}
        refs = set(absolute_paths(value))
        refs.update(resolve(ref) for ref in tuple(refs))
        paths.update(refs)
        # Missing transitive evidence cannot silently discard the snapshot it
        # used to reference. Every JSON reference must be readable before prune.
        pending.extend((ref, source_reports.get(ref)) for ref in refs if ref.suffix == '.json')
    return {'protected': sorted(protected), 'references': sorted(paths), 'lease': c.LEASE,
            'historical_records': sorted(historical - paths)}


def context_path_identity(paths, documents=()):
    """Track namespace identity; only parsed JSON contents require full stat."""
    paths, documents = set(map(Path, paths)), set(map(Path, documents))
    resolved = {path: path.resolve() for path in paths | documents}
    pending = set(resolved) | set(resolved.values())
    identities = {}
    while pending:
        path = pending.pop()
        for node in [path, *path.parents]:
            if node in identities:
                continue
            try:
                info = node.lstat()
            except FileNotFoundError:
                identities[node] = None
                continue
            link = os.readlink(node) if stat.S_ISLNK(info.st_mode) else None
            # A running protected world may append data or create children.
            # Its unchanged namespace still protects the same subtree.
            identities[node] = (info.st_dev, info.st_ino, info.st_mode,
                                (link, info.st_mtime_ns, info.st_ctime_ns) if link is not None else None)
            if link is not None:
                target = Path(link)
                pending.add(target if target.is_absolute() else node.parent / target)
    contents = {}
    for path in documents:
        info = resolved[path].lstat()
        contents[path] = (info.st_dev, info.st_ino, info.st_mode, info.st_size,
                          info.st_mtime_ns, info.st_ctime_ns)
    return {'resolved': resolved, 'identities': identities, 'documents': contents}


def execution_context_provider():
    """Reuse parsed context only within this cleanup; recheck all path identities."""
    cached = expected = None
    def reader():
        nonlocal cached, expected
        if cached is None:
            expected = {'resolved': {}, 'identities': {}, 'documents': {}}
            def track(path, document=False):
                snapshot = context_path_identity([path], [path] if document else [])
                for group, values in snapshot.items():
                    for key, value in values.items():
                        if key in expected[group] and expected[group][key] != value:
                            raise RuntimeError('Cleanup context paths changed while reading; plan again')
                        expected[group][key] = value
            value = cleanup_context(track)
            for path in [*value['protected'], *value['references']]:
                track(path)
            # Never bind old parsed JSON to metadata collected after it changed.
            if context_path_identity(expected['resolved'], expected['documents']) != expected:
                raise RuntimeError('Cleanup context paths changed while reading; plan again')
            cached = value
        elif context_path_identity(expected['resolved'], expected['documents']) != expected:
            raise RuntimeError('Cleanup context paths changed; plan again')
        return cached
    return lambda: execution_context(reader)


def execution_context(reader=None):
    expected = c.CONFIG.get('retention_pid_namespace')
    if not isinstance(expected, str) or not expected.startswith('pid:[') or not expected.endswith(']'):
        raise ValueError('Set retention_pid_namespace from the actual host /proc/1/ns/pid before deletion')
    if os.readlink('/proc/self/ns/pid') != expected:
        raise RuntimeError('Cleanup is outside the configured host process namespace; cannot prove copies are idle')
    return (reader or cleanup_context)()


def perform(*, execute=False, retire_outputs=None):
    root = c.CONFIG.get('retention_root')
    if not root:
        raise ValueError('Set retention_root explicitly before cleanup-copies')
    provider = execution_context_provider() if execute else cleanup_context
    context = provider()
    planned = retention.plan(Path(root), retire_outputs=retire_outputs, **context)
    if not execute:
        if retire_outputs is not None:
            return {**planned, 'read_only_summary_not_executable_plan': True,
                    'outputs': retention.reviewed_output_summaries(planned['outputs'])}
        return planned
    result = retention.execute(planned, **context, context=provider)
    c.R.mkdir(parents=True, exist_ok=True)
    c.atomic(c.R / 'retention-cleanup.json', result)
    if result.get('state') != 'completed':
        raise RuntimeError('Cleanup is partial; inspect ' + str(c.R / 'retention-cleanup.json'))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--retire-outputs', type=Path)
    args = parser.parse_args(argv)
    if not args.execute:
        return perform(retire_outputs=args.retire_outputs)
    # The same lock and visible lease exclude deployment while cleanup runs.
    with c.LOCK.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        c.lease_available()
        return perform(execute=True, retire_outputs=args.retire_outputs)


def after_deployment():
    if not c.CONFIG.get('retention_root'):
        return
    try:
        main(['--execute'])
    except Exception as error:
        warning = {'cleanup_failed': True, 'error': str(error), 'live_deployment_unchanged': True, 'recorded_at': c.now()}
        try:
            c.atomic(c.R / 'retention-cleanup-warning.json', warning)
        except OSError:
            pass
        print('RETIRED_COPY_CLEANUP_PENDING: ' + str(error), flush=True)
