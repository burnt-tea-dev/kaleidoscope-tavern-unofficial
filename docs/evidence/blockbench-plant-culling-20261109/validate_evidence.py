"""Offline bounded replay. No download, GUI, engine, or historical preparation."""
import argparse
import ast
import base64
import copy
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile
from PIL import Image, ImageChops

HERE = Path(__file__).resolve().parent
sha = lambda raw: hashlib.sha256(raw).hexdigest()
read = lambda path: json.loads(path.read_bytes())


def main():
    if sys.flags.optimize or os.environ.get('PYTHONOPTIMIZE') not in (None, '', '0'):
        raise SystemExit('Assertions must remain active; do not use optimized Python.')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path)
    args = parser.parse_args()
    artifacts = read(HERE / 'artifact-sha256.json')
    for name, row in artifacts.items():
        raw = (HERE / name).read_bytes()
        assert sha(raw) == row['sha256'] and len(raw) == row['bytes'], name
    entries = read(HERE / 'archive-entries.json')
    found = set()
    with tempfile.TemporaryDirectory(prefix='plant-culling-evidence-') as folder:
        root = Path(folder)
        for archive in read(HERE / 'archives.json'):
            parts = []
            for part in archive['parts']:
                raw = (HERE / part['path']).read_bytes()
                assert sha(raw) == part['sha256'] and len(raw) == part['bytes'] <= 180000
                parts.append(raw)
            raw = b''.join(parts)
            assert sha(raw) == archive['sha256'] and len(raw) == archive['bytes']
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                assert len(z.namelist()) == len(set(z.namelist())) == archive['members']
                for name in z.namelist():
                    path = PurePosixPath(name)
                    assert not path.is_absolute() and '..' not in path.parts and '\\' not in name
                    assert not name.endswith(('.jar', '.class', '.exe', '.dll', '.so')) and 'client_mappings' not in name
                    assert name not in found
                    found.add(name)
                    data = z.read(name)
                    assert entries[name] == {'archive': archive['path'], 'sha256': sha(data), 'bytes': len(data)}
                    target = root / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
        assert found == set(entries)
        review = root / 'review'
        # Load only the independently authored pure comparison functions. Do
        # not execute its historical absolute-path, Git-pin or output-writing
        # module body, and do not rewrite that original file.
        parsed = ast.parse((review / 'verify_controls.py').read_text())
        functions = ast.Module(body=[n for n in parsed.body if isinstance(n, ast.FunctionDef)], type_ignores=[])
        namespace = {'sha': sha, 'base64': base64}
        exec(compile(functions, 'preserved independent comparison functions', 'exec'), namespace)
        compare, validate = namespace['diff'], namespace['validate_pair']
        controls = read(review / 'control-manifest.json')
        negatives = 0
        for row in controls['scenes']:
            original_raw = (review / row['original_front']).read_bytes()
            assert sha(original_raw) == row['original_sha256']
            for previous in row['existing_front_captures']:
                raw = (review / 'reused-images' / previous['file']).read_bytes()
                assert sha(raw) == previous['sha256'] and len(raw) == previous['bytes']
            if row['role'] != 'candidate':
                continue
            original = json.loads(original_raw)
            front = read(review / row['policy_front'])
            double = read(review / row['old_policy_double'])
            assert sha((review / row['policy_front']).read_bytes()) == row['policy_front_sha256']
            assert sha((review / row['old_policy_double']).read_bytes()) == row['old_policy_double_sha256']
            assert validate(original, front, double, row) == 1
            mutants = [copy.deepcopy(double) for _ in range(3)]
            mutants[0]['elements'][0]['from'][0] += .01
            mutants[1]['textures'][row['source_texture_indices'][0]]['render_sides'] = 'double'
            mutants[2]['textures'][row['changed_texture_indices'][0]]['source'] += 'bad'
            for mutant in mutants:
                try:
                    validate(original, front, mutant, row)
                except AssertionError:
                    negatives += 1
                else:
                    raise AssertionError('Invalid one-factor control accepted')
        assert negatives == 12
        for row in read(root / 'input-local-map.json'):
            raw = (root / row['member']).read_bytes()
            assert sha(raw) == row['sha256'] and len(raw) == row['bytes']
        proposal = read(review / 'proposal.json')
        changed = 0
        canonical = root / 'current-canonical'
        for row in proposal['files']:
            before_raw = (root / 'inputs' / proposal['pin'] / row['path']).read_bytes()
            after_raw = (canonical / row['path']).read_bytes()
            assert sha(before_raw) == row['before_sha256'] and sha(after_raw) == row['after_sha256']
            delta = compare(json.loads(before_raw), json.loads(after_raw))
            paths = {'/' + '/'.join(map(str, path)) for path, old, new in delta}
            assert paths == {op['path'] for op in row['operations']}
            assert all(path[-1] == 'render_method' and old == 'alpha_test' and new == 'alpha_test_single_sided' for path, old, new in delta)
            changed += len(delta)
        assert changed == 36
        # Pure source-resource negatives run in one Python process, not a game.
        result = subprocess.run([sys.executable, '-B', str(canonical / 'tools/test_cultivation_source_contract.py')], cwd=canonical,
                                check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert 'Ran 11 tests' in result.stderr and 'OK' in result.stderr
        for version in ('1.20.1', '1.21.1'):
            proof = read(review / f'semantic-evidence/java-{version}-culling.json')
            assert proof['class_execution'] is False
            for cls in proof['classes']:
                if cls['class'].endswith('CompositeStateBuilder'):
                    assert any(' CULL]' in line for method in cls['methods'] for line in method['instructions'])
                if cls['class'].endswith('RenderType'):
                    init = next(m for m in cls['methods'] if m['method'] == '<clinit>()V')
                    assert not any('CullState' in line for line in init['instructions'])
        semantic = read(review / 'semantic-evidence/provenance.json')
        for row in semantic['local_sources']:
            path = review / (row['copy'] if 'copy' in row else 'semantic-evidence/loader-sources/' + row['file'])
            assert sha(path.read_bytes()) == row['sha256']
        if args.repository:
            for path in canonical.rglob('*'):
                if path.is_file():
                    assert (args.repository / path.relative_to(canonical)).read_bytes() == path.read_bytes(), str(path.relative_to(canonical))
            subprocess.run([sys.executable, '-B', str(HERE / 'validate_handoff.py'), '--repository', str(args.repository.resolve())], check=True)
        # The final GUI receipt and exact captures are validated below. Review
        # preparation reports keep their historical pending status unchanged.
        receipt = read(HERE / 'gui-review.json')
        assert receipt['accepted_model_view_count'] == 18
        for row in read(HERE / 'images.json'):
            raw = (HERE / row['path']).read_bytes()
            assert raw[:2] == b'\xff\xd8' and raw[-2:] == b'\xff\xd9'
            assert sha(raw) == row['sha256'] and len(raw) == row['bytes']
        assert len(receipt['pairs']) == 9 and receipt['native_engine_acceptance'] is False
        for pair in receipt['pairs']:
            front = Image.open(HERE / 'images/accepted' / pair['front_file']).convert('RGB')
            double = Image.open(HERE / 'images/accepted' / pair['double_file']).convert('RGB')
            assert front.size == double.size == (1188, 848)
            difference = ImageChops.difference(front, double)
            channels = difference.split()
            mask = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2]).point(lambda value: 255 if value else 0)
            count = lambda region: sum(mask.crop(region).histogram()[1:])
            report = pair['decoded_pixel_check']
            rectangle = report['review_rectangle_xyxy_exclusive']
            assert count(rectangle) == report['changed_pixels'] > 0
            box = mask.crop(rectangle).getbbox()
            assert [box[0] + rectangle[0], box[1] + rectangle[1], box[2] + rectangle[0] - 1, box[3] + rectangle[1] - 1] == report['changed_bbox_xyxy_inclusive']
            native_changes = 0
            for label, region in report['regions'].items():
                pixels = count(region['rectangle_xyxy_exclusive'])
                assert pixels == region['changed_decoded_pixels']
                if label.startswith('native_'):
                    assert pixels > 0
                    native_changes += pixels
                else:
                    assert pixels == 0, ('Source/connected control changed', pair['id'], label)
            assert report['changed_pixels'] - native_changes == report['changes_outside_native_control_rectangles'] == 0
    print(json.dumps({'archive_members': len(entries), 'changed_material_fields': changed,
                      'control_negative_mutations_rejected': negatives, 'cultivation_tests': 11,
                      'accepted_gui_views': 18, 'decoded_pixel_pairs': 9, 'repository_checked': bool(args.repository),
                      'class_execution': False, 'engine_execution': False, 'bds': False, 'client': False}))


if __name__ == '__main__':
    main()
