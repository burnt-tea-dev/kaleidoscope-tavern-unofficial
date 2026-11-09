#!/usr/bin/env python3
"""Validate untouched N04 evidence and replay bounded checks without GUI, Git or downloads."""
import argparse
import ast
import shutil
import subprocess
import collections
import contextlib
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import sys
import tempfile
import zipfile

# Keep numerical replay bounded and sequential.
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'
sys.dont_write_bytecode = True
from PIL import Image

HERE = Path(__file__).resolve().parent
REPORTS = {'audit_routes.py': 'routing-and-transform-audit.json',
           'validate_scenes.py': 'independent-geometric-uv-audit.json'}


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


def check_bytes(raw, row):
    assert len(raw) == row['bytes'] and digest(raw) == row['sha256'] and gitblob(raw) == row['git_blob_sha1']


def extract_archives(work):
    archives = read(HERE / 'archive-entries.json')
    entries, archive_paths, pending = {}, set(), []
    total = 0
    # Inspect every member in every ZIP before writing anything.
    for archive in archives:
        path = relative_file(HERE, archive['file'])
        if path in archive_paths or not archive['file'].startswith('archives/'):
            raise ValueError('Duplicate or unexpected archive path')
        archive_paths.add(path)
        raw = path.read_bytes()
        check_bytes(raw, archive)
        assert len(raw) < 200000
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
            for item in source.infolist():
                name = item.filename
                target = relative_file(work, name)
                mode = item.external_attr >> 16
                if item.is_dir() or (mode & 0o170000) not in (0, 0o100000):
                    raise ValueError('Archive member is not a regular file')
                if not name.startswith('review/') or name in entries:
                    raise ValueError('Unexpected or duplicate cross-archive member')
                row = expected[name]
                assert 0 <= item.file_size == row['bytes'] < 2000000
                total += item.file_size
                assert total < 20000000
                data = source.read(name)
                check_bytes(data, row)
                entries[name] = row
                pending.append((target, data))
    assert archive_paths == {p.resolve() for p in (HERE / 'archives').glob('*.zip')}
    for target, data in pending:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(data)
    return entries


def equal_json(left, right):
    assert same_json_values_and_types(left, right), 'JSON values, scalar types or array order differ'


def verify_sources(review, manifest):
    index = read(HERE / 'source-snapshot-index.json')
    assert len(index) == 250
    names = set()
    for row in index:
        assert row['file'] not in names
        names.add(row['file'])
        assert row['file'].startswith('review/')
        check_bytes(relative_file(review.parent, row['file']).read_bytes(), row)
    assert {'review/' + n for n in manifest['inputs']} <= names
    for name, row in manifest['inputs'].items():
        raw = relative_file(review, name).read_bytes()
        assert len(raw) == row['bytes'] and digest(raw) == row['sha256']
        indexed = next(r for r in index if r['file'] == 'review/' + name)
        assert indexed['owner'] == row['owner'] and indexed['original_path'] == row['original_path']
        if name.startswith('inputs/forge/'):
            assert row['owner'] == manifest['source_pins']['Forge']
        if name.startswith('inputs/neoforge/'):
            assert row['owner'] == manifest['source_pins']['NeoForge']
    licences = [r for r in index if r['file'].startswith('review/licenses/')]
    assert len(licences) == 4
    for row in licences:
        assert row['commit'] == manifest['source_pins'][row['owner']]
        if row['owner'] == 'Forge':
            assert relative_file(HERE, row['original_path']).read_bytes() == relative_file(review.parent, row['file']).read_bytes()
    comparisons = {}
    for path in manifest['source_branch_comparison']:
        a = relative_file(review / 'inputs/forge', path).read_bytes()
        b = relative_file(review / 'inputs/neoforge', path).read_bytes()
        row = {'present': True, 'bytes_equal': a == b}
        if path.endswith('.json'):
            row['semantic_json_equal'] = read(review / 'inputs/forge' / path) == read(review / 'inputs/neoforge' / path)
        elif path.endswith('.png'):
            x, y = Image.open(io.BytesIO(a)).convert('RGBA'), Image.open(io.BytesIO(b)).convert('RGBA')
            row['pixels_equal'] = x.size == y.size and x.tobytes() == y.tobytes()
        else:
            row['text_equal_ignoring_line_endings'] = a.decode().splitlines() == b.decode().splitlines()
        comparisons[path] = row
    equal_json(comparisons, manifest['source_branch_comparison'])
    assert len(comparisons) == 51
    renderers = []
    for name in ['Storage', 'CircularRack', 'TiltedRack', 'BarCabinet', 'CellarCabinet', 'Holder', 'GlasswareHolder']:
        path = 'src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/client/render/block/' + name + 'BlockEntityRender.java'
        texts = [(review / 'inputs' / branch / path).read_text() for branch in ['forge', 'neoforge']]
        assert ['\n'.join(x for x in t.splitlines() if not x.startswith('import ')) for t in texts][0] == \
               ['\n'.join(x for x in t.splitlines() if not x.startswith('import ')) for t in texts][1]
        renderers.append({'renderer': name, 'body_identical_excluding_import_lines': True})
    material_path = 'src/main/resources/assets/kaleidoscope_tavern/models/block/mixology/empty_glassware.json'
    forge_model, neo_model = [read(review / 'inputs' / branch / material_path) for branch in ['forge', 'neoforge']]
    forge_material, neo_material = forge_model.pop('render_type'), neo_model.pop('render_type')
    equal_json(forge_model, neo_model)
    for branch in ['forge', 'neoforge']:
        assert 'RenderType.cutout()' in (review / 'inputs' / branch / 'src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/client/render/block/GlasswareHolderBlockEntityRender.java').read_text()
    equal_json({'renderers': renderers, 'full_mod_parity_claimed': False,
                'occupied_glassware_material_override': {
                    'Forge_model': forge_material, 'NeoForge_model': neo_material,
                    'other_model_fields_identical': True, 'both_renderers': 'explicit RenderType.cutout()',
                    'other_contexts_accepted': False}}, read(review / 'source-branch-renderer-audit.json'))
    lock = read(review / 'supplemental/source-jar.lock.json')
    locked = {r['path']: r for r in lock['asset_files']}
    report = read(review / 'author-resource-verification.json')
    equal_json(lock['input'], report['archive_identity'])
    verified, absent = 0, 0
    for row in report['checks']:
        if 'status' in row:
            absent += 1
            assert not (review / 'inputs/author-resources' / row['author_member']).exists()
            continue
        path = row['author_resource']
        raw = relative_file(review, path).read_bytes()
        entry = locked[path.removeprefix('inputs/author-resources/')]
        assert len(raw) == entry['bytes'] and digest(raw) == entry['sha256'] == row['archive_sha256']
        source = relative_file(review, row['source'])
        assert (raw == source.read_bytes()) is row['exact_bytes_equal']
        if path.endswith('.json'):
            equal = read(review / path) == read(source)
        else:
            a, b = Image.open(io.BytesIO(raw)).convert('RGBA'), Image.open(source).convert('RGBA')
            equal = a.size == b.size and a.tobytes() == b.tobytes()
        assert equal is True and row['equal_json_or_pixels'] is True
        verified += 1
    assert (verified, absent) == (6, 26) and report['jar_included'] is False
    proof = read(review / 'luminous-adaptation-reuse.json')
    prior = review / 'prior-luminous/face-adaptation-verification.json'
    assert sha(prior) == proof['prior_proof_sha256']
    old = read(prior)
    equal_json(proof['method'], old['method'])
    equal_json(proof['count1_proof'], next(s for s in old['states'] if s['family'] == 'luminous_bride' and s['count'] == 1))
    for row in proof['verified_reused_inputs']:
        field = row['field']
        suffix = '.png' if field.endswith('texture') else '.json'
        a = (review / 'prior-luminous' / (field + suffix)).read_bytes()
        b = relative_file(review, row['input']).read_bytes()
        assert digest(a) == row['prior_sha256'] and digest(b) == row['current_sha256']
        assert (a == b) is row['same_exact_bytes_as_prior_proof']
        assert (a != b) is row['line_endings_only_if_bytes_differ']
        assert a == b or field == 'java_model' and a.replace(b'\r\n', b'\n') == b.replace(b'\r\n', b'\n')
    held = read(review / 'held-pose-preservation.json')
    accepted = read(review / 'inputs/current/docs/evidence/t175-rack-lift/native-review.json')
    assert sha(relative_file(review / 'inputs/current', held['runtime_file'])) == held['sha256'] == accepted['runtime_sha256']
    assert sha(review / 'inputs/current/docs/evidence/t175-rack-lift/native-review.json') == held['accepted_evidence_sha256']
    assert held['selected_y_lift'] == accepted['selected_y_lift'] == 6
    return {'pinned_input_snapshots': len(index), 'branch_comparisons': len(comparisons),
            'renderer_bodies': len(renderers), 'locked_author_members': verified, 'optional_author_members_not_run': absent}


def verify_gui(review, manifest):
    gui = HERE / 'gui'
    originals = read(gui / 'artifact-sha256.json')
    actual = {p.relative_to(gui).as_posix() for p in gui.rglob('*') if p.is_file()}
    assert actual == set(originals) | {'artifact-sha256.json'}
    for name, expected in originals.items():
        assert sha(relative_file(gui, name)) == expected
    index = read(gui / 'gui-index.json')
    assert (index['accepted_images'], index['scene_count'], index['case_count']) == (27, 8, 12)
    assert index['frozen_source_manifest_sha256'] == sha(review / 'manifest.json')
    assert index['frozen_preparation_inventory_sha256'] == sha(review / 'artifact-sha256.json')
    scenes = {r['file']: r for r in manifest['scenes']}
    seen, covered, by_hash = set(), set(), collections.defaultdict(list)
    for row in index['captures'] + index['diagnostics']:
        assert row['file'] not in seen
        seen.add(row['file'])
        raw = relative_file(gui, row['file']).read_bytes()
        assert len(raw) == row['bytes'] and digest(raw) == row['sha256']
        with Image.open(io.BytesIO(raw)) as im:
            assert im.format == row['format'] == 'JPEG' and list(im.size) == row['dimensions'] == [1188, 848]
            im.verify()
        if row in index['captures']:
            # Historical GUI relative scene links are provenance, never joined unchecked.
            assert row['scene'].startswith('../scenes/')
            scene_name = row['scene'][3:]
            relative_file(review, scene_name)
            assert scene_name in scenes and row['scene_sha256'] == scenes[scene_name]['sha256']
            equal_json(row['scene_case_ids'], scenes[scene_name]['cases'])
            covered.add(scene_name)
            by_hash[row['sha256']].append(row['file'])
        else:
            assert row['accepted_visual_evidence'] is False
    assert len(seen) == 46 and len(index['captures']) == 27 and len(index['diagnostics']) == 19 and covered == set(scenes)
    assert seen == {n for n in actual if n.endswith('.jpg')}
    identical = [names for names in by_hash.values() if len(names) > 1]
    assert identical == [['18-cellar-east-source-bottles-only.jpg', '19-cellar-east-current-bottles-only.jpg']]
    receipt = read(gui / 'validation-receipt.json')
    assert receipt['accepted_jpegs'] == 27 and receipt['diagnostic_jpegs_excluded'] == 19
    assert receipt['errors'] == [] and receipt['all_scenes_and_frozen_inputs_unchanged'] is True
    equal_json(receipt['identical_raw_capture_groups'], identical)
    pre, post = read(gui / 'preflight.json'), read(gui / 'postflight.json')
    assert pre['verified_artifact_count'] == post['frozen_artifacts_checked'] == 266
    assert pre['mismatches'] == post['frozen_mismatches'] == post['selected_local_worktree_mismatches'] == []
    frozen = read(review / 'artifact-sha256.json')
    equal_json(pre['inventory'], frozen)
    assert len(post['records']) == 266
    assert {r['file'] for r in post['records']} == set(frozen)
    for row in post['records']:
        assert row['unchanged'] is True and row['sha256'] == row['expected_sha256'] == frozen[row['file']]
    assert post['selected_local_worktree_files_checked'] == len(post['selected_local_worktree_records']) == 131
    for row in post['selected_local_worktree_records']:
        assert row['equal'] is True
        assert row['snapshot_sha256'] == row['worktree_sha256'] == sha(relative_file(review / 'inputs/current', row['path']))
    return {'accepted_raw_jpegs': 27, 'excluded_raw_diagnostics': 19,
            'identical_separately_captured_events': identical, 'dimensions': [1188, 848]}


def verify_current(review, manifest, repository):
    current = read(HERE / 'current-input-verification.json')
    expected = {name.removeprefix('inputs/current/'): row for name, row in manifest['inputs'].items() if name.startswith('inputs/current/')}
    assert len(current['files']) == current['relevant_canonical_input_count'] == len(expected) == 131
    assert {r['file'] for r in current['files']} == set(expected)
    assert current['all_unchanged'] is True
    for row in current['files']:
        assert row['unchanged'] is True and row['original_input'] == 'inputs/current/' + row['file']
        check_bytes(relative_file(review, row['original_input']).read_bytes(), row)
        if repository:
            check_bytes(relative_file(repository, row['file']).read_bytes(), row)
    return current


def replay_audits(work):
    review = work / 'review'
    originals = {p: sha(p) for p in review.rglob('*') if p.is_file()}
    rerun = work / 'replay'
    shutil.copytree(review, rerun)
    checks = []
    # Execute the unchanged saved independent audits only in a disposable copy.
    # Builders and historical preparation/Git materializers are never executed.
    for script, report in REPORTS.items():
        path = rerun / script
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(path.read_text(), str(path), 'exec'), {'__file__': str(path), '__name__': '__main__'})
        equal_json(read(rerun / report), read(review / report))
        checks.append(report)
    path = review / 'inputs/current/tools/check_glassware_slots.py'
    namespace = {'__name__': 'archived_slot_audit', '__file__': str(path)}
    exec(compile(path.read_text(), str(path), 'exec'), namespace)
    slots = namespace['audit'](review / 'inputs/current/runtime/BP/blocks/glassware_holder.json',
                               review / 'inputs/current/runtime/RP/models/entity/runtime_glassware_holder.geo.json')
    equal_json(slots, read(review / 'glassware-world-slot-audit.json'))
    checks.append('glassware-world-slot-audit.json')
    tree = ast.parse((review / 'inputs/current/tools/check_storage_rendering.py').read_text())
    code = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'NODE_SNAPSHOT' for t in n.targets))
    root = rerun / 'inputs/current'
    # Declare module parsing only in the disposable replay copy; no install or imports from a registry.
    (root / 'package.json').write_text('{"type":"module"}\n')
    node = shutil.which('node')
    if not node:
        raise RuntimeError('Node.js is required for the original pure core pose snapshot')
    snapshot = subprocess.check_output([node, '--input-type=module', '-e', code], cwd=root,
                                       env={**os.environ, 'NODE_OPTIONS': '', 'NODE_PATH': ''}, timeout=30)
    generated = rerun / 'pose-snapshot-replayed.json'
    generated.write_bytes(snapshot)
    equal_json(read(generated), read(review / 'pose-snapshot.json'))
    checks.append('pose-snapshot.json')
    assert all(sha(p) == old for p, old in originals.items()), 'Archived originals changed'
    assert {p for p in review.rglob('*') if p.is_file()} == set(originals)
    changed = {p.relative_to(rerun).as_posix() for p in rerun.rglob('*') if p.is_file()
               and (review / p.relative_to(rerun)) in originals and sha(p) != originals[review / p.relative_to(rerun)]}
    assert changed <= set(REPORTS.values())
    return checks, read(rerun / 'independent-geometric-uv-audit.json')


def verify(work, repository=None):
    if not __debug__:
        raise RuntimeError('Run without Python optimization; verification requires assertions')
    verify_inventory(HERE)
    entries = extract_archives(work)
    assert len(entries) == 277 and len(read(HERE / 'archive-entries.json')) == 5
    review = work / 'review'
    # Reject duplicate keys and non-finite numeric payloads before executing any audit.
    for root in [HERE, review]:
        for path in root.rglob('*'):
            if path.is_file() and path.suffix in ('.json', '.bbmodel'):
                read(path)
    manifest = read(review / 'manifest.json')
    assert len(manifest['inputs']) == 240 and len(manifest['scenes']) == 8 and len(manifest['cases']) == 12
    assert manifest['canonical_commit'] == 'cb2b37dfa2181ee042a090d8dbd434758a762afb'
    assert manifest['runtime_version'] == '0.6.213' and manifest['gui_reviewed'] is False
    frozen = read(review / 'artifact-sha256.json')
    assert len(frozen) == 266
    for name, expected in frozen.items():
        assert sha(relative_file(review, name)) == expected
    assert {n.removeprefix('review/') for n in entries if not n.startswith(('review/licenses/', 'review/prior-luminous/', 'review/supplemental/'))} == set(frozen) | {'artifact-sha256.json'}
    for row in manifest['scenes']:
        scene = relative_file(review, row['file'])
        assert sha(scene) == row['sha256'] and row['gui_reviewed'] is False
        model = read(scene)
        for texture in model['textures']:
            assert texture['_review_input'] in manifest['inputs']
        for element in model['elements']:
            assert element['_review']['input'] in manifest['inputs']
    sources = verify_sources(review, manifest)
    gui = verify_gui(review, manifest)
    current = verify_current(review, manifest, repository)
    checks, summary = replay_audits(work)
    return {'passed': True, 'documented_base_commit': current['base_commit'],
            'documented_base_tree': current['base_tree'], 'runtime_tree': current['runtime_tree'],
            'runtime_version': current['runtime_version'], 'archive_entries_verified': len(entries),
            'original_frozen_artifacts': 266, 'sources': sources, 'gui': gui,
            'current_repository_inputs_rechecked': 131 if repository else 0,
            'relevant_canonical_inputs_unchanged': 131, 'exact_audit_replay': checks,
            'independent_scene_audit': summary, 'original_bytes_unchanged': True,
            'scene_generation': False, 'gui_or_engine_execution': False, 'runtime_changed': False,
            'native_facing_materials_or_all_addon_acceptance': False}


def main():
    if not __debug__:
        raise RuntimeError('Run without Python optimization; verification requires assertions')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, help='Optional checkout; verify the 131 current canonical input files.')
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
        with tempfile.TemporaryDirectory(prefix='tavern-occupied-furniture-evidence-') as tmp:
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
