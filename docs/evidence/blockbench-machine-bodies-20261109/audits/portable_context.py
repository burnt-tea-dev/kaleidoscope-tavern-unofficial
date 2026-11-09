"""Explicit paths and bounded immutable blob reads for the two original audits."""
import copy
import json
from pathlib import Path, PurePosixPath

HISTORICAL_ROOT = '/workspace/scratch/f31f84fbb9ff/tavern-machine-body-review-20261109'
_context = None
_blobs = None


def member(root, name):
    if not isinstance(name, str) or not name or any(c in name for c in ('\\', ':', '\0')):
        raise ValueError('Invalid relative member path')
    if name.startswith('/') or any(p in ('', '.', '..') for p in name.split('/')):
        raise ValueError('Unsafe relative member path')
    root = root.resolve()
    path = root
    for part in PurePosixPath(name).parts:
        path = path / part
        if path.is_symlink():
            raise ValueError('Symlinks are not evidence members')
    if not path.resolve().is_relative_to(root):
        raise ValueError('Member escapes its root')
    return path


def relocate(value, root):
    """Only the exact historical review root may move; no string normalization."""
    if isinstance(value, dict):
        return {relocate(k, root): relocate(v, root) for k, v in value.items()}
    if isinstance(value, list):
        return [relocate(v, root) for v in value]
    if isinstance(value, str) and value.startswith('/'):
        prefix = HISTORICAL_ROOT + '/'
        if not value.startswith(prefix):
            raise ValueError('Undeclared historical absolute path')
        return str(member(root, value[len(prefix):]))
    return value


def configure(review, output, index):
    global _context, _blobs
    _context = (review, output, relocate(json.loads((review / 'manifest.json').read_text()), review))
    blobs = {}
    for row in index:
        if row['owner'] == 'canonical prior held':
            key = ('show', row['commit'] + ':' + row['path'])
        elif row['owner'] == 'locked author archive':
            key = ('cat-file', 'blob', row['git_blob_sha1'])
        else:
            continue
        if key in blobs:
            raise ValueError('Duplicate bounded Git identity')
        blobs[key] = member(review.parent, row['file']).read_bytes()
    if len(blobs) != 15:
        raise ValueError('Expected four prior held inputs and eleven archive members')
    _blobs = blobs


def context():
    if _context is None:
        raise RuntimeError('Run the package verifier, not this historical audit directly')
    h, output, manifest = _context
    return h, output, copy.deepcopy(manifest)


def git(*args):
    if _blobs is None or args not in _blobs:
        raise ValueError('Git request is not a declared bounded blob: ' + repr(args))
    return _blobs[args]
