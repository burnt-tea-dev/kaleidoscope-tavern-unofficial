#!/usr/bin/env python3
"""Validate untouched N02 evidence and replay its audits, without Git or networking."""
import argparse
import base64
import collections
import contextlib
import csv
import difflib
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
import zipfile

# Numerical libraries must remain single-threaded while the shared GUI is active.
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'
sys.dont_write_bytecode = True
from PIL import Image

HERE = Path(__file__).resolve().parent
REPORTS = {
    'validate_scenes.py': ['ordered-face-world-audit.json', 'structural-validation.json'],
    'finalize_provenance.py': ['prior-evidence-reuse.json', 'author-archive-verification.json',
                               'source-branch-semantics.json', 'routing-validation.json'],
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def gitblob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def sha(path):
    return digest(path.read_bytes())


def read(path):
    def finite_float(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError('Non-finite JSON number: ' + value)
        return result

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON object key: ' + key)
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=unique, parse_float=finite_float,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Non-finite JSON: ' + value)))


def relative_file(root, name):
    if not isinstance(name, str) or not name or any(c in name for c in ('\\', ':', '\0')):
        raise ValueError('Invalid relative evidence path')
    if name.startswith('/') or any(p in ('', '.', '..') for p in name.split('/')):
        raise ValueError('Unsafe relative evidence path')
    root = root.resolve()
    path = root
    for part in PurePosixPath(name).parts:
        path = path / part
        if path.is_symlink():
            raise ValueError('Symbolic links are not allowed in evidence paths')
    if not path.resolve().is_relative_to(root):
        raise ValueError('Evidence path escapes its declared root')
    return path


def output_location(path, repository=None):
    if '..' in path.parts:
        raise ValueError('Parent components are not allowed in output paths')
    target = path.resolve()
    for root in [HERE.resolve()] + ([repository.resolve()] if repository else []):
        if target == root or target.is_relative_to(root):
            raise ValueError('Output must be external to evidence and repository')
    for parent in [path.absolute(), *path.absolute().parents]:
        if parent.is_symlink():
            raise ValueError('Output paths may not contain symbolic links')
    for parent in [target, *target.parents]:
        marker = parent / '.git'
        if marker.is_file() or (marker.is_dir() and (marker / 'HEAD').is_file()):
            raise ValueError('Output must be outside every Git checkout')
    if path.exists() or path.is_symlink() or target.exists():
        raise FileExistsError('Output destination must not already exist')
    return target


def same_json_values_and_types(left, right):
    options = {'sort_keys': True, 'separators': (',', ':'), 'allow_nan': False}
    return json.dumps(left, **options) == json.dumps(right, **options)


def verify_inventory(root):
    inventory = read(relative_file(root, 'artifact-sha256.json'))
    seen = set()
    for row in inventory['files']:
        path = relative_file(root, row['file'])
        if path in seen:
            raise ValueError('Duplicate artifact inventory path')
        seen.add(path)
        raw = path.read_bytes()
        assert len(raw) == row['bytes'] and digest(raw) == row['sha256'] and gitblob(raw) == row['git_blob_sha1'], row['file']
    actual = set()
    for path in root.rglob('*'):
        if path.is_symlink():
            raise ValueError('Evidence payload contains a symbolic link')
        if path.is_file():
            actual.add(relative_file(root, path.relative_to(root).as_posix()))
    excluded = {root.resolve() / 'artifact-sha256.json'}
    if seen & excluded or actual != seen | excluded:
        raise ValueError('Artifact inventory has extra, missing or self-referential rows')


def extract_archives(work):
    archives = read(HERE / 'archive-entries.json')
    assert len(archives) == 2
    entries, archive_paths = {}, set()
    # Fully inspect every member before any extraction, including cross-ZIP duplicates.
    pending = []
    for archive in archives:
        path = relative_file(HERE, archive['file'])
        if path in archive_paths:
            raise ValueError('Duplicate archive path')
        archive_paths.add(path)
        raw = path.read_bytes()
        assert len(raw) == archive['bytes'] < 200000
        assert digest(raw) == archive['sha256'] and gitblob(raw) == archive['git_blob_sha1']
        expected = {}
        for row in archive['entries']:
            relative_file(work, row['file'])
            if row['file'] in expected:
                raise ValueError('Duplicate archive inventory entry')
            expected[row['file']] = row
        with zipfile.ZipFile(io.BytesIO(raw)) as source:
            names = source.namelist()
            if len(names) != len(set(names)) or set(names) != set(expected):
                raise ValueError('Archive member inventory is missing, extra or duplicated')
            assert source.testzip() is None
            for item in source.infolist():
                name = item.filename
                target = relative_file(work, name)
                mode = item.external_attr >> 16
                if item.is_dir() or (mode & 0o170000) not in (0, 0o100000):
                    raise ValueError('Archive member is not a regular file')
                if not name.startswith('review/') or name in entries:
                    raise ValueError('Unexpected or duplicate cross-archive member')
                row = expected[name]
                assert item.file_size == row['bytes'] < 1000000
                data = source.read(name)
                assert digest(data) == row['sha256'] and gitblob(data) == row['git_blob_sha1']
                entries[name] = row
                pending.append((target, data))
    assert len(entries) == 142
    assert archive_paths == {p.resolve() for p in (HERE / 'archives').glob('*.zip')}
    for target, data in pending:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(data)
    return entries


def verify_sources(work, manifest):
    index = read(HERE / 'source-snapshot-index.json')
    assert len(index) == 113
    seen = set()
    expected_inputs = {'review/' + name for name in manifest['inputs']}
    original_inputs = set()
    for row in index:
        name = row['file']
        if name in seen:
            raise ValueError('Duplicate source snapshot member')
        seen.add(name)
        raw = relative_file(work, name).read_bytes()
        assert len(raw) == row['bytes'] and digest(raw) == row['sha256'] and gitblob(raw) == row['git_blob_sha1']
        relative_file(work, row['path'])
        owner = row['owner']
        if name in expected_inputs:
            original_inputs.add(name)
            original = manifest['inputs'][name.removeprefix('review/')]
            assert original['owner'] == owner + ' ' + row['commit']
            assert original['original_path'] == row['path'] and original['sha256'] == row['sha256']
            assert original['bytes'] == row['bytes']
        elif owner == 'canonical prior held':
            assert row['commit'] == 'e58b5a421d101f83418b82a960faa1b94d0c2a73'
            assert name == 'review/prior-held/' + row['path']
        elif owner == 'locked author archive':
            assert name == 'review/locked-archive/' + row['path']
        else:
            assert owner in manifest['source_pins'] and row['commit'] == manifest['source_pins'][owner]
            assert row['path'] in ('LICENSE-ASSETS', 'LICENSE-CODE')
            assert name == 'review/licenses/' + owner + '/' + row['path']
    assert original_inputs == expected_inputs and len(original_inputs) == 94
    review = work / 'review'
    lock = read(review / 'snapshot/art/source-jar.lock.json')
    locked = {r['path']: r for r in lock['asset_files']}
    jar = [r for r in index if r['owner'] == 'locked author archive']
    assert len(jar) == 11
    for row in jar:
        entry = locked[row['path']]
        assert all(entry[k] == row[k] for k in ('bytes', 'sha256', 'git_blob_sha1'))
    # Recompute all 23 Forge/Neo source comparisons, including original text differences.
    comparisons = {}
    for name in manifest['source_comparison']:
        a = relative_file(review / 'inputs/forge', name).read_bytes()
        b = relative_file(review / 'inputs/neoforge', name).read_bytes()
        row = {'path_present': True, 'sha256': digest(b), 'bytes_equal': a == b}
        if name.endswith('.json'):
            row['json_equal'] = json.loads(a) == json.loads(b)
        elif name.endswith('.png'):
            with Image.open(io.BytesIO(a)) as aa, Image.open(io.BytesIO(b)) as bb:
                x, y = aa.convert('RGBA'), bb.convert('RGBA')
                row['pixels_equal'] = x.size == y.size and x.tobytes() == y.tobytes()
        else:
            row['text_equal_ignoring_line_endings'] = a.decode().splitlines() == b.decode().splitlines()
        comparisons[name] = row
    assert len(comparisons) == 23 and same_json_values_and_types(comparisons, manifest['source_comparison'])
    for name in ('LICENSE-ASSETS', 'LICENSE-CODE'):
        assert (HERE / name).read_bytes() == (review / 'licenses/Forge' / name).read_bytes()
    return index


def verify_keyframes(review, manifest):
    # Reevaluate exact source PUT channels and final-key clamping, not interpolation.
    path = 'inputs/forge/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/client/animation/ShakerAnimation.java'
    text = (review / path).read_text().split('public static final AnimationDefinition PUT =', 1)[1].split(').build();', 1)[0]
    number = r'-?\d+(?:\.\d+)?'
    channels = {}
    for bone, target, body in re.findall(r'\.addAnimation\("(\w+)", new AnimationChannel\(AnimationChannel.Targets\.(\w+),(.*?)(?=\.addAnimation|$)', text, re.S):
        values = {}
        for time, method, args in re.findall(r'new Keyframe\((' + number + r')F, KeyframeAnimations\.(degreeVec|posVec)\((.*?)\), AnimationChannel.Interpolations.CATMULLROM\)', body):
            values[float(time)] = [float(x) for x in re.findall(number, args)]
        channels.setdefault(bone, {})['rotation' if target == 'ROTATION' else 'position'] = values
    native = read(review / 'snapshot/runtime/RP/animations/shaker.animation.json')['animations']['animation.kt_assets_a8.shaker.put']['bones']
    assert channels and set(channels) == set(native)
    for bone, properties in channels.items():
        assert set(properties) == set(native[bone])
        for prop, frames in properties.items():
            # Original numerical equality accepts authored int/float spellings here,
            # while final saved audit comparisons below preserve exact JSON types.
            assert frames == {float(k): v['post'] for k, v in native[bone][prop].items()}
    cases = [c for c in manifest['cases'] if c['id'].startswith('shaker-put-')]
    assert [c['time_seconds'] for c in cases] == [0, 0.0833, 0.2083]
    for case in cases:
        t = case['time_seconds']
        evaluated = {}
        for bone, properties in native.items():
            evaluated[bone] = {}
            for prop, frames in properties.items():
                keys = sorted(float(k) for k in frames)
                key = t if t in keys else max(k for k in keys if k <= t)
                assert t in keys or t >= max(keys)
                evaluated[bone][prop] = next(v['post'] for k, v in frames.items() if float(k) == key)
        assert same_json_values_and_types(evaluated, case['evaluated_keyframe'])


def verify_gui(review, manifest):
    gui = read(HERE / 'gui-review.json')
    assert (HERE / 'gui-review.json').read_bytes() == (review / 'gui-review/review-report.json').read_bytes()
    assert (HERE / 'gui-review-README.md').read_bytes() == (review / 'gui-review/README.md').read_bytes()
    assert gui['gui_completed'] is True and gui['scene_count'] == 6 and gui['case_count'] == 10
    assert gui['main_evidence_pin'] == manifest['main'] and gui['runtime_tree'] == manifest['runtime_tree']
    assert gui['accepted_original_screenshots'] == len(gui['captures']) == 19
    assert gui['diagnostic_original_screenshots'] == len(gui['diagnostics']) == 5
    assert gui['all_scene_bytes_unchanged'] is True
    preflight = read(review / 'gui-review/preflight-input-hashes.json')
    assert preflight['input_count'] == 94 and preflight['mismatches'] == []
    assert len(preflight['checks']) == 94 and len({r['path'] for r in preflight['checks']}) == 94
    assert {r['path']: r['sha256'] for r in preflight['checks']} == {p: r['sha256'] for p, r in manifest['inputs'].items()}
    assert all(r['exists'] is True and r['matches'] is True for r in preflight['checks'])
    scenes = {'scenes/' + Path(r['file']).name: r for r in manifest['scenes']}
    assert len(scenes) == 6 and len(manifest['cases']) == 10
    assert gui['post_review_scene_hashes'] == {p: r['sha256'] for p, r in scenes.items()}
    texture_count = 0
    for name, row in scenes.items():
        path = relative_file(review, name)
        assert sha(path) == row['sha256']
        scene = read(path)
        assert scene['meta']['model_format'] == 'free'
        for texture in scene['textures']:
            assert texture['render_sides'] == 'front'
            assert texture['source'].startswith('data:image/png;base64,')
            data = base64.b64decode(texture['source'].split(',', 1)[1], validate=True)
            # Embedded original texture bytes must occur in the declared source inputs.
            matches = [r for p, r in manifest['inputs'].items() if p.endswith('.png') and r['sha256'] == digest(data)]
            assert matches
            texture_count += 1
    assert texture_count == 12
    all_images = gui['captures'] + gui['diagnostics']
    assert len({r['file'] for r in all_images}) == len({r['sha256'] for r in all_images}) == 24
    assert {r['file'] for r in all_images} == {p.relative_to(HERE / 'images').as_posix() for p in (HERE / 'images').rglob('*') if p.is_file()}
    for row in all_images:
        path = relative_file(HERE / 'images', row['file'])
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
        with Image.open(path) as image:
            assert image.format == row['format'] == 'JPEG' and image.size == tuple(row['dimensions']) == (1188, 848)
            image.verify()
    views = collections.Counter()
    for row in gui['captures']:
        assert row['status'] == 'accepted bounded preview observation'
        scene = scenes[row['scene']]
        assert row['scene_sha256'] == scene['sha256']
        expected = [{'id': c['id'], 'source_offset': c['source_offset'], 'current_offset': c['native_offset']}
                    for c in manifest['cases'] if c['scene'] == Path(row['scene']).name]
        assert same_json_values_and_types(row['case_positions'], expected)
        views[row['scene']] += 1
    assert views == {name: (4 if name == 'scenes/barrel-open.bbmodel' else 3) for name in scenes}
    assert all(r['status'] == 'excluded' and r['file'].startswith('diagnostic/') for r in gui['diagnostics'])
    with (HERE / 'capture-index.csv').open(newline='') as stream:
        captions = list(csv.DictReader(stream))
    assert len(captions) == len({r['image'] for r in captions}) == 24
    markdown = (HERE / 'scene-index.md').read_text()
    archived = {r['file']: a['file'] for a in read(HERE / 'archive-entries.json') for r in a['entries']}
    by_image = {'images/' + r['file']: r for r in all_images}
    for row in captions:
        original = by_image[row['image']]
        assert row['image_sha256'] == original['sha256'] and row['status'] == original['status']
        assert '(' + row['image'] + ')' in markdown and original['sha256'] in markdown
        if row['status'] == 'excluded':
            assert row['observation'] == original['reason'] and row['scene_member'] == row['scene_archive'] == row['scene_sha256'] == row['case_positions'] == ''
        else:
            assert row['scene_member'] == 'review/' + original['scene']
            assert row['scene_archive'] == archived[row['scene_member']]
            assert row['scene_sha256'] == original['scene_sha256']
            assert row['camera'] == original['camera'] and row['camera_numeric_coordinates'] == original['camera_numeric_coordinates']
            assert same_json_values_and_types(json.loads(row['case_positions']), original['case_positions'])
            assert row['observation'] == original['findings']
    return texture_count


def verify_current(review, manifest, repository):
    current = read(HERE / 'current-input-verification.json')
    assert current['original_input_count'] == 94 and current['canonical_input_count'] == 48
    assert current['historical_main'] == manifest['main'] and current['historical_runtime_tree'] == manifest['runtime_tree']
    assert current['all_canonical_inputs_unchanged'] is True
    rows = current['canonical_inputs']
    assert len(rows) == len({r['path'] for r in rows}) == 48
    expected = {p: r for p, r in manifest['inputs'].items() if p.startswith('snapshot/')}
    assert {r['original_input'] for r in rows} == set(expected)
    for row in rows:
        original = expected[row['original_input']]
        assert row['path'] == original['original_path']
        assert row['sha256'] == original['sha256'] and row['bytes'] == original['bytes'] and row['unchanged'] is True
        raw = relative_file(review, row['original_input']).read_bytes()
        assert digest(raw) == row['sha256'] and len(raw) == row['bytes']
        if repository:
            assert relative_file(repository, row['path']).read_bytes() == raw, row['path']
    return current


def replay_audits(work, index):
    review = work / 'review'
    original = {p: sha(p) for p in work.rglob('*') if p.is_file()}
    output = work / 'rerun'
    output.mkdir()
    sys.path.insert(0, str(HERE / 'audits'))
    from portable_context import configure, relocate
    configure(review, output, index)
    checks = []
    changes = read(HERE / 'audit-portability.json')
    assert len(changes) == 2 and {r['file'] for r in changes} == set(REPORTS)
    patch = []
    for row in changes:
        name = row['file']
        old, new = review / name, HERE / 'audits' / name
        assert sha(old) == row['original_sha256'] and sha(new) == row['portable_sha256']
        patch.extend(difflib.unified_diff(old.read_text().splitlines(True), new.read_text().splitlines(True),
                                        fromfile='original/' + name, tofile='audits/' + name, n=0))
    assert (HERE / 'audit-portability.patch').read_text() == ''.join(patch)
    for script, reports in REPORTS.items():
        code = (HERE / 'audits' / script).read_text()
        # Same Python process, exact numeric libraries, no builder or subprocess.
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(code, str(review / script), 'exec'), {'__name__': '__main__', '__file__': str(review / script)})
        for name in reports:
            assert same_json_values_and_types(read(output / name), relocate(read(review / name), review)), name
            checks.append({'audit': script, 'report': name, 'same_json_values_types_and_array_order': True,
                           'original_sha256': sha(review / name)})
    assert all(sha(path) == old for path, old in original.items()), 'Original archived files changed'
    assert {p for p in work.rglob('*') if p.is_file()} == set(original) | {output / r['report'] for r in checks}, 'Unexpected replay output'
    summary = read(output / 'ordered-face-world-audit.json')['summary']
    assert summary['cases'] == 10 and summary['paired_faces'] == 452
    assert summary['uv_mismatches'] == summary['pixel_mismatches'] == summary['shade_mismatches'] == 0
    structure = read(output / 'structural-validation.json')
    assert structure == {'input_hashes': 94, 'scenes': 6, 'textures': 12, 'cubes': 170, 'nested_group_vertices': 1360,
                         'direct_source_modelpart_vertices': 336, 'direct_source_json_vertices': 344,
                         'direct_modelpart_uv_faces': 208, 'direct_native_vertices': 680,
                         'direct_native_uv_faces': 496, 'gui_reviewed': False}
    return checks, summary


def verify(work, repository=None):
    if not __debug__:
        raise RuntimeError('Run without Python optimization; verification requires assertions')
    verify_inventory(HERE)
    entries = extract_archives(work)
    review = work / 'review'
    manifest = read(review / 'manifest.json')
    assert len(manifest['inputs']) == 94
    assert manifest['main'] == 'd42a39745f25082aa129f4d4bb823684e4174771'
    assert manifest['runtime_version'] == '0.6.213' and manifest['runtime_tree'] == '38c5977dd6bfe14b1824734612e3c601e1e41028'
    assert manifest['gui_reviewed'] is False
    artifacts = read(review / 'artifact-sha256.json')
    assert len(artifacts) == 117
    for name, expected in artifacts.items():
        assert sha(relative_file(review, name)) == expected
    for name, row in manifest['inputs'].items():
        raw = relative_file(review, name).read_bytes()
        assert len(raw) == row['bytes'] and digest(raw) == row['sha256']
    index = verify_sources(work, manifest)
    verify_keyframes(review, manifest)
    textures = verify_gui(review, manifest)
    current = verify_current(review, manifest, repository)
    checks, summary = replay_audits(work, index)
    return {'passed': True, 'documented_base_commit': current['base_commit'],
            'documented_runtime_version': current['runtime_version'], 'documented_runtime_tree': current['runtime_tree'],
            'archives': 2, 'archive_entries_verified': len(entries), 'original_review_files': 123,
            'source_snapshots_verified': len(index), 'source_branch_comparisons': 23, 'locked_archive_members': 11,
            'prior_held_source_blobs': 4, 'source_licenses': 4, 'original_inputs': 94,
            'canonical_inputs_unchanged': 48, 'current_repository_inputs_rechecked': 48 if repository else 0,
            'saved_scenes': 6, 'body_state_pairs': 10, 'embedded_original_png_entries': textures,
            'accepted_original_jpegs': 19, 'excluded_original_diagnostics': 5, 'image_dimensions': [1188, 848],
            'independent_face_summary': summary, 'exact_audit_replay': checks,
            'original_bytes_unchanged': True, 'scene_generation': False, 'gui_or_engine_execution': False,
            'runtime_changed': False, 'N03_contents_accepted_by_this_package': False}


def main():
    if not __debug__:
        raise RuntimeError('Run without Python optimization; verification requires assertions')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, help='Optional checkout; verify the 48 current canonical input files.')
    parser.add_argument('--work-dir', type=Path, help='New external extraction directory; existing paths are rejected.')
    parser.add_argument('--report', type=Path, help='New external JSON receipt; never used as a validation oracle.')
    args = parser.parse_args()
    repository = args.repository.resolve() if args.repository else None
    report = output_location(args.report, repository) if args.report else None
    if args.work_dir:
        work = output_location(args.work_dir, repository)
        if report and (report == work or report.is_relative_to(work) or work.is_relative_to(report)):
            raise ValueError('Receipt and extraction destinations must not overlap')
        work.mkdir(parents=True, exist_ok=False)
        result = verify(work, repository)
    else:
        with tempfile.TemporaryDirectory(prefix='tavern-machine-body-evidence-') as tmp:
            work = output_location(Path(tmp) / 'extracted', repository)
            work.mkdir()
            result = verify(work, repository)
    if report:
        report = output_location(report, repository)
        report.parent.mkdir(parents=True, exist_ok=True)
        with report.open('x') as stream:
            stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
