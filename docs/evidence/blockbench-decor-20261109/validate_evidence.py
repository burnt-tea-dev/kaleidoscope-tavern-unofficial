#!/usr/bin/env python3
"""Check saved evidence and rerun existing audits in a fresh extraction.

No GUI actions, scene generation, runtime edits, or changes to saved evidence.
"""
import argparse
import collections
import csv
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import zipfile

from PIL import Image

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(path.read_bytes())


def read(path):
    return json.loads(path.read_text())


def relative_file(root, name):
    """Resolve only canonical relative names within the declared input root."""
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise ValueError("Invalid relative evidence path")
    relative = PurePosixPath(name)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in name.split("/")):
        raise ValueError("Absolute, empty, dot or parent path components are not allowed")
    root = root.resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError("Evidence path resolves outside its declared root")
    return path


def verify_inventory(root):
    root = root.resolve()
    inventory = read(relative_file(root, "artifact-sha256.json"))
    listed = set()
    for row in inventory["files"]:
        path = relative_file(root, row["file"])
        if path in listed:
            raise ValueError("Duplicate artifact inventory path")
        listed.add(path)
        assert path.stat().st_size == row["bytes"] and sha(path) == row["sha256"], row["file"]
    actual = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("Evidence payload must not contain symbolic links")
        if path.is_file():
            actual.add(relative_file(root, path.relative_to(root).as_posix()))
    excluded = {root / "artifact-sha256.json", root / "verification.json"}
    if listed & excluded or actual != listed | excluded:
        raise ValueError("Artifact inventory has missing, extra or excluded-file rows")


def output_location(path, repository=None):
    """Allow only new external outputs, never evidence or a Git checkout."""
    target = path.resolve()
    blocked = [HERE.resolve()]
    if repository:
        blocked.append(repository.resolve())
    if any(target == root or target.is_relative_to(root) for root in blocked):
        raise ValueError("Output must be outside the evidence and repository roots")
    # This also covers an omitted --repository, other worktrees and symlink aliases.
    markers = [parent / ".git" for parent in [target, *target.parents]]
    if any(marker.is_file() or (marker.is_dir() and (marker / "HEAD").is_file()) for marker in markers):
        raise ValueError("Output must be outside every Git checkout")
    if path.exists() or path.is_symlink() or target.exists() or target.is_symlink():
        raise FileExistsError("Output destination must not already exist")
    return target


def same_json_values_and_types(left, right):
    # Compare in memory only. Preserve array order, scalar types and exact numbers;
    # ignore only JSON object-key ordering. Never rewrite the saved evidence.
    options = {"sort_keys": True, "separators": (",", ":"), "allow_nan": False}
    return json.dumps(left, **options) == json.dumps(right, **options)


def extract_archives(work):
    archives = read(HERE / 'archive-entries.json')
    assert len(archives) == 8
    entries, archive_paths = {}, set()
    for archive in archives:
        path = relative_file(HERE, archive['file'])
        if path in archive_paths:
            raise ValueError('Duplicate archive path')
        archive_paths.add(path)
        assert path.stat().st_size == archive['bytes'] < 200000
        assert sha(path) == archive['sha256']
        with zipfile.ZipFile(path) as source:
            expected = {row['file']: row for row in archive['entries']}
            if len(expected) != len(archive['entries']):
                raise ValueError('Duplicate archive inventory entry')
            names = source.namelist()
            if len(names) != len(set(names)) or set(names) != set(expected):
                raise ValueError('Archive member inventory is incomplete or duplicated')
            assert source.testzip() is None
            for item in source.infolist():
                name = item.filename
                target = relative_file(work, name)
                mode = item.external_attr >> 16
                assert not item.is_dir() and (mode & 0o170000) in (0, 0o100000)
                assert name.startswith('review/') and name not in entries
                row = expected[name]
                assert item.file_size == row['bytes'] < 1000000
                raw = source.read(name)
                assert digest(raw) == row['sha256']
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as stream:
                    stream.write(raw)
                entries[name] = row
    assert len(entries) == 1085
    assert archive_paths == {p.resolve() for p in (HERE / 'archives').glob('*.zip')}
    return entries


def verify_pinned_sources(work, manifest):
    """Replay recorded Git/JAR comparisons from bounded exact blob snapshots."""
    index = read(HERE / 'source-snapshot-index.json')
    assert len(index) == 468 and sum(row['present'] for row in index) == 444
    lookup = {}
    for row in index:
        key = (row['branch'], row['path'])
        if key in lookup:
            raise ValueError('Duplicate pinned-source identity')
        lookup[key] = row
        relative_file(work, row['path'])
        assert row['commit'] == manifest['source_pins'][row['branch']]
        if row['present']:
            expected = 'review/pinned-source/' + row['branch'] + '/' + row['path']
            assert row['file'] == expected
            assert sha(relative_file(work, row['file'])) == row['sha256']
        else:
            assert row['file'] is None and row['sha256'] is None
    actual = {p.relative_to(work).as_posix() for p in (work / 'review/pinned-source').rglob('*') if p.is_file()}
    assert actual == {row['file'] for row in index if row['present']}
    review = work / 'review'
    java = review / 'tavern-visual-review-20261108/java-reference'
    lock = read(review / 'tavern-visual-review-20261108/source/art/source-jar.lock.json')
    locked = {r['path']: r for r in lock['asset_files']}
    assert len(manifest['source_verification']) == 134
    for name, records in manifest['source_verification'].items():
        path = Path(name)
        rel = path.relative_to(java).as_posix()
        current = path.read_bytes()
        for branch in ('Forge', 'NeoForge', 'unpublished_26_1_2'):
            row = lookup[(branch, rel)]
            record = records[branch]
            assert row['present'] == record.get('path_present', True)
            if not row['present']:
                continue
            raw = relative_file(work, row['file']).read_bytes()
            assert digest(raw) == record.get('sha256', record.get('git_bytes_sha256'))
            assert (raw == current) == record.get('bytes_equal', record.get('worktree_bytes_equal'))
            if path.suffix == '.json':
                assert (json.loads(raw) == json.loads(current)) == record['json_equal']
            elif 'pixels_equal' in record:
                import io
                with Image.open(io.BytesIO(raw)) as left, Image.open(path) as right:
                    a, b = left.convert('RGBA'), right.convert('RGBA')
                    assert (a.size == b.size and a.tobytes() == b.tobytes()) == record['pixels_equal']
        jar = records['jar']
        blob = Path(jar['path']).read_bytes()
        reljar = Path(jar['path']).relative_to(review / 'tavern-next-decor-review-20261108/verified-jar-assets').as_posix()
        identity = locked[reljar]
        assert len(blob) == identity['bytes'] and digest(blob) == identity['sha256'] == jar['sha256']
        assert hashlib.sha1(b'blob ' + str(len(blob)).encode() + b'\0' + blob).hexdigest() == identity['git_blob_sha1'] == jar['git_blob_sha1']
        assert (blob == current) == jar['bytes_equal']
        if path.suffix == '.json':
            assert (json.loads(blob) == json.loads(current)) == jar['json_equal']
        elif 'pixels_equal' in jar:
            import io
            with Image.open(io.BytesIO(blob)) as left, Image.open(path) as right:
                a, b = left.convert('RGBA'), right.convert('RGBA')
                assert (a.size == b.size and a.tobytes() == b.tobytes()) == jar['pixels_equal']
    return {'source_assets': 134, 'pinned_asset_and_blockstate_blobs': 444, 'documented_absent_unpublished_assets': 24, 'jar_asset_blobs': 134}


def verify(work, repository):
    verify_inventory(HERE)
    entries = extract_archives(work)
    review = work / 'review'
    decor = review / 'tavern-next-decor-review-20261108'
    original = {p: sha(p) for p in work.rglob('*') if p.is_file()}
    for name, expected in read(decor / 'artifact-hashes.json').items():
        assert sha(relative_file(decor, name)) == expected
    sys.path.insert(0, str(HERE / 'audits'))
    from portable_context import relocate
    manifest = relocate(read(decor / 'manifest.json'), review)
    reuse = relocate(read(HERE / 'latest-input-reuse.json'), review)
    assert read(HERE / 'latest-input-reuse.json') == read(decor / 'latest-input-reuse-20261109.json')
    assert len(manifest['inputs']) == reuse['saved_inputs_verified'] == 417
    for name, row in manifest['inputs'].items():
        path = Path(name)
        assert path.is_relative_to(review) and path.is_file()
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
    # Every path consumed by the historical audits must be a declared input,
    # not merely a path found inside a trusted-looking JSON document.
    for case in manifest['cases']:
        for name in [case['source_model'], case['binding']['block'], case['binding']['geometry']]:
            assert name in manifest['inputs']
        for material in case['binding']['materials'].values():
            assert material['_path'] in manifest['inputs']
    for name, records in manifest['source_verification'].items():
        assert name in manifest['inputs'] and records['jar']['path'] in manifest['inputs']
    for row in manifest['scenes']:
        name = Path(row['file']).name
        assert row['file'] == str(relative_file(decor / 'scenes', name))
    assert len(reuse['inputs']) == len({row['input'] for row in reuse['inputs']}) == 417
    assert {row['input']: row['prepared_sha256'] for row in reuse['inputs']} == {name: row['sha256'] for name, row in manifest['inputs'].items()}
    current = [row for row in reuse['inputs'] if 'repository_path' in row]
    assert len(current) == len({row['repository_path'] for row in current}) == 149
    differences = [row for row in current if not row['current_equals_prepared']]
    assert differences == reuse['canonical_differences'] and len(differences) == 2
    assert {row['repository_path'] for row in differences} == {'runtime/RP/models/entity/incense_closed.geo.json', 'runtime/RP/models/entity/incense_open.geo.json'}
    for row in current:
        assert row['saved_input_bytes_still_match']
        path = relative_file(work / 'review/current', row['repository_path']) if not row['current_equals_prepared'] else Path(row['input'])
        assert sha(path) == row['current_sha256']
        assert (row['prepared_sha256'] == row['current_sha256']) == row['current_equals_prepared']
        if repository:
            assert sha(relative_file(repository, row['repository_path'])) == row['current_sha256'], row['repository_path']
    assert reuse['latest_runtime_tree'] == '38c5977dd6bfe14b1824734612e3c601e1e41028'
    assert reuse['latest_remote_main'] == 'd42a39745f25082aa129f4d4bb823684e4174771'
    assert manifest['runtime_version'] == reuse['original_runtime_version'] == '0.6.212'
    assert reuse['current_runtime_version'] == '0.6.213'
    source_checks = verify_pinned_sources(work, manifest)

    gui = read(HERE / 'gui-review.json')
    assert sha(HERE / 'gui-review.json') == '4c2cc47ec511ada4b81181083fc4d50a955fe2e0fc89457d387282f57b7c795c'
    assert (HERE / 'gui-review.json').read_bytes() == (decor / 'gui-evidence-20261109/review.json').read_bytes()
    assert gui['input_reuse_report']['sha256'] == sha(HERE / 'latest-input-reuse.json')
    assert gui['ordinary_pairs'] == 79 and gui['target_scenes'] == gui['reviewed_scenes'] == 25
    assert gui['image_count'] == len(gui['images']) == 84
    images = {row['file']: row for row in gui['images']}
    assert len(images) == len({row['sha256'] for row in images.values()}) == 84
    assert set(images) == {p.name for p in (HERE / 'images').glob('*.jpg')}
    for name, row in images.items():
        path = relative_file(HERE / 'images', name)
        assert row['accepted_evidence'] and row['visually_reviewed']
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
        with Image.open(path) as image:
            assert image.format == 'JPEG' and image.size == tuple(row['dimensions']) == (1188, 848)
            image.verify()
    scene_by_name = {Path(row['file']).stem: row for row in manifest['scenes']}
    assert len(scene_by_name) == 28 and len(manifest['cases']) == 95
    scenes = {row['scene']: row for row in gui['scenes']}
    assert len(scenes) == 25 and not any('incense' in name or 'catnip' in name for name in scenes)
    used_images, pair_count, four_views = [], 0, 0
    for name, row in scenes.items():
        assert row['scene_file'] == '../scenes/' + name + '.bbmodel'
        path = relative_file(decor / 'scenes', name + '.bbmodel')
        assert sha(path) == row['scene_sha256'] and row['manifest_hash_matches']
        assert row['status'] == 'reviewed_bounded_editor'
        views = {images[n]['view'] for n in row['evidence']}
        used_images.extend(row['evidence'])
        if 'grapevine' in name:
            assert views == {'perspective', 'oblique-orthographic', 'reverse-orthographic', 'reverse-low-orthographic'}
            assert len(row['evidence']) == 4
            four_views += 1
        else:
            assert len(row['evidence']) == len(views) == 3
            if name.startswith(('tables-', 'bare-trellises-')):
                assert views == {'perspective', 'top', 'bottom'}
            elif name == 'magenta-three-way-branch-difference':
                assert views == {'perspective', 'bottom', 'low-underside-perspective'}
            else:
                assert views == {'perspective', 'oblique-orthographic', 'reverse-orthographic'}
        if name in scene_by_name:
            expected = scene_by_name[name]
            assert expected['sha256'] == row['scene_sha256'] and expected['cases'] == row['cases']
            cases = [c for c in manifest['cases'] if c['scene'] == name + '.bbmodel']
            offsets = [{k: c[k] for k in ['label', 'source_world_offset', 'native_world_offset']} for c in cases]
            assert row['case_offsets'] == offsets
            excluded_paths = {entry['input'] for entry in differences}
            assert all(case['binding']['geometry'] not in excluded_paths for case in cases)
            pair_count += len(cases)
    assert four_views == 9 and pair_count == 79
    assert len(used_images) == len(set(used_images)) == 84 and set(used_images) == set(images)
    with (HERE / 'capture-index.csv').open(newline='') as stream:
        captions = list(csv.DictReader(stream))
    assert len(captions) == len({row['image'] for row in captions}) == 84
    assert {row['image'] for row in captions} == {'images/' + name for name in images}
    markdown = (HERE / 'scene-index.md').read_text()
    for row in captions:
        image_name = row['image'].removeprefix('images/')
        image = images[image_name]
        scene = scenes[row['scene']]
        assert image_name in scene['evidence']
        assert row['image_sha256'] == image['sha256'] and row['view'] == image['view']
        assert row['camera_orientation'] == image['direction']
        assert row['capture_time_utc'] == image['captured_utc']
        assert row['scene_sha256'] == scene['scene_sha256'] and row['observation'] == scene['observation']
        assert '(' + row['image'] + ')' in markdown and image['sha256'] in markdown
        assert relative_file(work, row['scene_file_in_archive']).is_file()
    for row in manifest['scenes']:
        assert sha(Path(row['file'])) == row['sha256']
    for row in reuse['non_incense_main_scenes_verified'] + [reuse['magenta_scene_verified']]:
        assert row['unchanged'] and sha(relative_file(decor, row['file'])) == row['sha256']

    # Audits are copied only into the fresh extraction. Saved scripts and reports
    # remain intact; no GUI or scene save is invoked.
    (review / 'rerun').mkdir()
    changes = read(HERE / 'audit-portability.json')
    for row in changes:
        assert sha(decor / row['file']) == row['original_sha256']
        assert sha(HERE / 'audits' / row['file']) == row['portable_sha256']
    # Execute portable source with __file__ set to the archived original path.
    # That preserves all original sibling-path calculations without overwriting it.
    helper = HERE / 'audits'
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONOPTIMIZE='0')
    env['PYTHONPATH'] = str(helper) + os.pathsep + str(decor)
    checks = []
    for script, reports in [
        ('validate_scenes.py', ['ordered-face-audit.json', 'structural-validation.json']),
        ('check_routing.py', ['routing-validation.json']),
        ('check_incense_underside.py', ['incense-underside-candidate.json']),
        ('make_magenta_branch_scene.py', ['magenta-branch-difference.json']),
    ]:
        source = HERE / 'audits' / script
        code = "import sys; p=sys.argv[1]; original=sys.argv[2]; exec(compile(open(p).read(),original,'exec'),{'__name__':'__main__','__file__':original})"
        result = subprocess.run([sys.executable, '-c', code, str(source), str(decor / script)], cwd=work, env=env, capture_output=True, text=True)
        assert result.returncode == 0, script + ': ' + result.stderr.replace(str(work), '.')
        for report in reports:
            generated = review / 'rerun' / report
            saved = decor / report
            assert same_json_values_and_types(read(generated), relocate(read(saved), review)), report
            checks.append({'audit': script, 'report': report, 'same_json_values_types_and_array_order_after_explicit_path_relocation': True, 'saved_sha256': sha(saved), 'historical_scope_preserved': True})
    assert all(sha(path) == expected for path, expected in original.items()), 'Archived evidence changed during replay'
    expected_new = {review / 'rerun' / row['report'] for row in checks}
    assert {p for p in work.rglob('*') if p.is_file()} == set(original) | expected_new, 'Unexpected audit output'
    return {
        'passed': True, 'base_commit': reuse['latest_remote_main'], 'base_runtime_tree': reuse['latest_runtime_tree'],
        'archives': 8, 'archive_entries_verified': len(entries), 'archives_below_200000_bytes': True,
        'original_inputs_verified': 417, 'canonical_inputs_checked': 149,
        'canonical_inputs_unchanged': 147, 'excluded_repaired_incense_inputs': 2,
        'current_repository_inputs_rechecked': 149 if repository else 0,
        'historical_scenes_preserved': 29, 'current_gui_scenes': 25, 'ordinary_pairs': 79,
        'accepted_original_jpegs': 84, 'dimensions': [1188, 848], 'nine_vine_scenes_four_views': True,
        'source_verification': source_checks, 'numerical_audits': checks,
        'scene_bytes_unchanged': True, 'gui_or_engine_execution': False, 'runtime_changed': False,
        'historical_incense_results_are_not_current_defects': True,
    }


def main():
    if not __debug__:
        raise RuntimeError('Run without Python optimization; verification requires assertions')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, help='Optional canonical checkout; recheck all 149 current input hashes.')
    parser.add_argument('--work-dir', type=Path, help='New external extraction directory, outside all Git checkouts.')
    parser.add_argument('--report', type=Path, help='New external summary file. Existing files are never overwritten.')
    args = parser.parse_args()
    repository = args.repository.resolve() if args.repository else None
    report = output_location(args.report, repository) if args.report else None
    if args.work_dir:
        work = output_location(args.work_dir, repository)
        work.mkdir(parents=True, exist_ok=False)
        result = verify(work, repository)
    else:
        with tempfile.TemporaryDirectory(prefix='tavern-decor-evidence-') as tmp:
            result = verify(Path(tmp), repository)
    if report:
        report = output_location(report, repository)
        report.parent.mkdir(parents=True, exist_ok=True)
        with report.open('x') as stream:
            stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
