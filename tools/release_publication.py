"""Select explicit publication and optional public prose; never publish anything."""
import argparse
import json
import os
import re
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]


def validate_request_identity(request, release):
    """Check the current request even when publication remains disabled.

    Runtime and family source identities still belong to their existing locks.
    This only binds the publication-facing version, tag and title to release.json.
    """
    version = release.get('version')
    if not isinstance(version, str) or not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Release version must contain three numeric components')
    if request.get('version') != version:
        raise ValueError('Release request version differs from release.json')
    prerelease = request.get('prerelease')
    if type(prerelease) is not bool:
        raise ValueError('Release request prerelease flag must be a boolean')
    if request.get('tag') != f'v{version}' + ('-beta.1' if prerelease else ''):
        raise ValueError('Release request tag differs from the declared version/channel')
    title = request.get('title')
    if not isinstance(title, str) or '\n' in title or '\r' in title:
        raise ValueError('Release request title must be a single line')
    named_version = re.match(r'^Tavern (\d+\.\d+\.\d+)(?=\s|:|$)', title)
    if not named_version or named_version.group(1) != version:
        raise ValueError('Release request title must name the declared Tavern version')


def publication_enabled(request, event_name, publish_release=False):
    automatic = request.get('publication_request', True)
    if type(automatic) is not bool or type(publish_release) is not bool:
        raise ValueError('Publication flags must be booleans')
    if event_name == 'workflow_dispatch':
        return publish_release
    return event_name == 'push' and automatic


def public_notes(root, request):
    name = request.get('public_notes_path')
    if name is None:
        return None
    if not isinstance(name, str) or not name:
        raise ValueError('Public notes must name a Markdown document')
    relative = PurePosixPath(name)
    if (relative.is_absolute() or '..' in relative.parts or '\\' in name or
            not relative.parts or (relative.parts[0] != 'docs' and name != 'CHANGELOG.md') or relative.suffix != '.md'):
        raise ValueError('Public notes must remain under docs or use the existing CHANGELOG.md')
    root = Path(root).resolve()
    path = root / str(relative)
    if (not path.is_file() or not path.resolve().is_relative_to(root) or
            any(p.is_symlink() for p in [path, *path.parents] if p == root or root in p.parents)):
        raise ValueError('Public notes must be an existing regular source document')
    return path

def public_notes_text(root, request):
    inline = request.get('public_notes_inline')
    if inline is not None:
        if (not isinstance(inline, str) or not inline.strip() or len(inline) > 4096 or
                '\x00' in inline or re.search(r'/root/|/var/|file://', inline)):
            raise ValueError('Inline public notes must be short public text without private filesystem paths')
        return inline.strip() + '\n'
    path = public_notes(root, request)
    return path.read_text(encoding='utf-8') if path else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--event', required=True)
    parser.add_argument('--publish-release', choices=('true', 'false'), default='false')
    args = parser.parse_args()
    request = json.loads((ROOT / '.github/release-request.json').read_text())
    release = json.loads((ROOT / 'release.json').read_text())
    validate_request_identity(request, release)
    enabled = publication_enabled(request, args.event, args.publish_release == 'true')
    notes = public_notes(ROOT, request)
    if output := os.environ.get('GITHUB_OUTPUT'):
        with open(output, 'a') as stream:
            stream.write('publish=' + str(enabled).lower() + '\n')
    print(json.dumps({'publication_enabled': enabled,
                      'public_notes_path': str(notes.relative_to(ROOT)) if notes else None}))


if __name__ == '__main__':
    main()
