"""Reject nonportable, escaping and symlink evidence paths before payload reads."""
from pathlib import Path, PurePosixPath

def safe_path(root, name):
    if not isinstance(name, str) or not name or '\\' in name or '\x00' in name:
        raise ValueError('Invalid evidence path')
    rel = PurePosixPath(name)
    if rel.is_absolute() or any(part in ('', '.', '..') for part in name.split('/')):
        raise ValueError('Evidence path must be a normalized relative path: '+name)
    root = Path(root)
    cursor = root
    for part in rel.parts:
        cursor = cursor/part
        if cursor.is_symlink():
            raise ValueError('Symlink evidence payload rejected: '+name)
    if not cursor.resolve().is_relative_to(root.resolve()):
        raise ValueError('Evidence path escapes package root: '+name)
    return cursor

def reject_symlinks(root):
    root = Path(root)
    if root.is_symlink():
        raise ValueError('Symlink evidence root rejected')
    for entry in root.rglob('*'):
        if entry.is_symlink():
            raise ValueError('Symlink evidence payload rejected: '+str(entry))
