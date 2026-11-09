"""Offline replay of the bounded wild-vine evidence. Never run legacy builders."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import runpy
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
sha = lambda raw: hashlib.sha256(raw).hexdigest()
read = lambda path: json.loads(path.read_text())


def main():
    if sys.flags.optimize or os.environ.get('PYTHONOPTIMIZE') not in (None, '', '0'):
        raise SystemExit('Assertions must remain active; do not use optimized Python.')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path)
    args = parser.parse_args()
    for line in (HERE/'ARTIFACT-SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1)
        assert sha((HERE/name).read_bytes()) == digest, name
    receipt = read(HERE/'gui-review.json')
    assert receipt['accepted_view_count'] == len(receipt['accepted']) == 20
    images = read(HERE/'images.json')
    assert len(images) == 26
    for category in ('accepted', 'excluded', 'diagnostics'):
        for row in receipt[category]:
            raw = (HERE/'images'/category/row['file']).read_bytes()
            assert raw[:2] == b'\xff\xd8' and raw[-2:] == b'\xff\xd9'
            assert sha(raw) == row['sha256'] and len(raw) == row['bytes']
    entries = read(HERE/'archive-entries.json')
    with tempfile.TemporaryDirectory(prefix='wild-vine-evidence-') as folder:
        root = Path(folder)
        with zipfile.ZipFile(HERE/'archives/review-inputs.zip') as archive:
            assert len(archive.namelist()) == len(set(archive.namelist()))
            assert set(archive.namelist()) == set(entries)
            for name in archive.namelist():
                path = PurePosixPath(name)
                assert not path.is_absolute() and '..' not in path.parts and '\\' not in name
                assert not name.endswith('.jar') and 'client_mappings' not in name
                raw = archive.read(name)
                assert {'sha256': sha(raw), 'bytes': len(raw)} == entries[name]
                target = root/name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
        review = root/'review'
        for row in receipt['accepted']:
            references = [row['scene_or_native_input'], row['texture'], *row.get('source_geometry_references', [])]
            for ref in references:
                raw = (review/ref['path']).read_bytes()
                assert sha(raw) == ref['sha256'] and len(raw) == ref['bytes']
        # This independent checker imports no builder/converter/scene helper.
        independent = review/'independent-candidate-review'
        old = read(independent/'independent-validation.json')
        subprocess.run([sys.executable, '-B', str(independent/'validate_candidate.py')],
                       check=True, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert read(independent/'independent-validation.json') == old
        canonical = root/'current-canonical'
        helper = runpy.run_path(str(canonical/'tools/wild_vine_surfaces.py'))
        surfaces = helper['check'](canonical)
        assert surfaces['directed_faces'] == 4 and surfaces['uv_corners'] == 16
        assert surfaces['texel_centers'] == 1024
        model = canonical/'runtime/RP/models/entity/wild_grapevine.geo.json'
        assert sha(model.read_bytes()) == receipt['candidate_sha256']
        changed = []
        for name in ('wild_grapevine', 'wild_grapevine_plant'):
            rel = 'runtime/BP/blocks/'+name+'.json'
            before = read(review/'inputs/canonical'/rel)
            after = read(canonical/rel)
            components = after['minecraft:block']['components']
            for material in (components['minecraft:material_instances']['*'],
                             components['minecraft:item_visual']['material_instances']['*']):
                assert material['render_method'] == 'alpha_test_single_sided'
                material['render_method'] = 'alpha_test'
            assert before == after, 'Scope expanded beyond two material scalars: '+rel
            changed.append(rel)
        for version in ('1.20.1', '1.21.1'):
            culling = read(review/f'material-route-review/java-{version}-culling.json')
            assert culling['class_execution'] is False
            for cls in culling['classes']:
                if cls['class'].endswith('CompositeStateBuilder'):
                    assert any(' CULL]' in line for method in cls['methods'] for line in method['instructions'])
                if cls['class'].endswith('RenderType'):
                    init = next(m for m in cls['methods'] if m['method'] == '<clinit>()V')
                    assert not any('CullState' in line for line in init['instructions'])
        if args.repository:
            for path in (canonical/'runtime').rglob('*'):
                if path.is_file():
                    assert (args.repository/path.relative_to(canonical)).read_bytes() == path.read_bytes(), str(path.relative_to(canonical))
            assert (args.repository/'tools/wild_vine_surfaces.py').read_bytes() == (canonical/'tools/wild_vine_surfaces.py').read_bytes()
    print(json.dumps({'accepted_gui_views': 20, 'excluded': 3, 'diagnostics': 3,
                      'archive_members': len(entries), 'independent_geometry_and_mutations': 'passed',
                      'current_surfaces': surfaces, 'exact_material_fields_changed': 4,
                      'repository_checked': bool(args.repository), 'client': False, 'bds': False}))


if __name__ == '__main__':
    main()
