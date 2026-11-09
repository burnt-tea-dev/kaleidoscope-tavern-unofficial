"""Relocate only declared historical path prefixes, never saved evidence bytes."""
import json
from pathlib import Path, PurePosixPath

HISTORICAL_ROOT = '/workspace/scratch/f31f84fbb9ff/'
ROOTS = ('tavern-next-decor-review-20261108', 'tavern-visual-review-20261108')


def relative_file(root, name):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name:
        raise ValueError('Invalid relative evidence path')
    if PurePosixPath(name).is_absolute() or any(p in ('', '.', '..') for p in name.split('/')):
        raise ValueError('Noncanonical relative evidence path')
    root = root.resolve()
    target = (root / name).resolve()
    if target == root or not target.is_relative_to(root):
        raise ValueError('Path resolves outside its declared root')
    return target


def relocate(value, review_root):
    if isinstance(value, dict):
        return {relocate(k, review_root): relocate(v, review_root) for k, v in value.items()}
    if isinstance(value, list):
        return [relocate(v, review_root) for v in value]
    if isinstance(value, str) and value.startswith(HISTORICAL_ROOT):
        relative = value.removeprefix(HISTORICAL_ROOT)
        if relative.split('/')[0] not in ROOTS:
            raise ValueError('Undeclared historical input root')
        return str(relative_file(review_root, relative))
    return value


def mapped_manifest(path):
    return relocate(json.loads(path.read_text()), path.parent.parent)
