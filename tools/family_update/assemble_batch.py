"""Assemble a reviewed local batch from explicit generated and installed inputs."""
import argparse
import datetime
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from family_bundle import assemble, files_hash
from family_update.source_batch import generated_pack, pack_tree, source_provenance


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def assemble_batch(options):
    run, parent = (Path(options[key]) for key in ('run', 'parent'))
    installed_parent = Path(options.get('installed_parent', str(parent)))
    sources = {name: Path(path) for name, path in options['sources'].items()}
    config = read(installed_parent / 'staging-config.json')
    world = Path(config['world_dir'])
    generated = read(run / 'generated-inputs.json')
    generation = read(run / 'generation.json')
    batch = read(parent / 'source-batch.json')
    batch.update(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 parent_source_batch=str(parent / 'source-batch.json'), scope=options['scope'],
                 tests_executed=False, remote_delivery=False, deployed=False)
    for name, commit in generation['sources'].items():
        batch['source_commits'][name] = {'path': str(sources[name]), 'commit': commit}
    source_provenance(batch, {name: sources[name] for name in generation['sources']})
    replaced = set()
    for uid, generated_row in generated.items():
        name, side, source = generated_row['name'], generated_row['side'], Path(generated_row['path'])
        actual_uid, actual, files = generated_pack(name, side, source)
        assert actual_uid == uid and all(actual[key] == generated_row[key] for key in ('name', 'side', 'path', 'version', 'tree')), 'Generated output changed before assembly: ' + uid
        destination = run / 'batch-inputs' / name / side
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != destination.resolve():
            shutil.copytree(source, destination)
            copied_uid, copied, copied_files = generated_pack(name, side, destination)
            assert copied_uid == uid and copied_files == files, 'Batch input copy differs: ' + uid
        else:
            copied = {**actual, 'path': str(destination)}
        replaced.add(uid)
        batch['packs'][uid] = copied

    prior = read(installed_parent / 'release-candidate/family-receipt.json')
    previous = {row['uuid']: row for row in prior['packs']}
    source_prior = read(parent / 'release-candidate/family-receipt.json')
    source_previous = {row['uuid']: row for row in source_prior['packs']}
    replaced.update(uid for uid, row in batch['packs'].items() if row['version'] != previous[uid]['version'])
    order = {side: [row['pack_id'] for row in read(world / ('world_' + side + '_packs.json'))]
             for side in ('behavior', 'resource')}
    assert order == prior['order'], 'Installed selection order changed'
    paths, descriptors, changes = [], {}, []
    for side, uids in order.items():
        for uid in uids:
            installed = files_hash(world / (side + '_packs') / uid)
            assert installed == previous[uid]['files'], 'Installed content changed: ' + uid
            row = batch['packs'].get(uid)
            source = Path(row['path']) if row else world / (side + '_packs') / uid
            files = files_hash(source)
            if row:
                assert pack_tree(files) == row['tree'], 'Selected source input changed: ' + uid
            if uid not in replaced:
                assert files == installed, 'Unrelated payload would change: ' + uid
            else:
                changes.append({'uuid': uid, 'name': row['name'], 'side': row['side'],
                                'before': previous[uid]['version'], 'after': row['version']})
            paths.append(source)
            descriptors[uid] = {
                'owner': 'preserved',
                'role': 'reviewed_local_generated_input' if row else 'unchanged_external_dependency',
                'source_batch': str(run / 'source-batch.json'),
                'source_commits': {key: value['commit'] for key, value in batch['source_commits'].items()},
                'input_tree': pack_tree(files), 'working_candidate': True, 'official_author_release': False}
            if uid not in generated and uid in source_previous:
                assert files == source_previous[uid]['files'], 'Inherited input changed: ' + uid
                descriptors[uid] = source_previous[uid]['source']

    save(run / 'source-batch.json', batch)
    lock = read(sources['tavern'] / 'family/upstream.lock.json')
    lock['owned'], lock['upstream'], lock['order'] = [], [], order
    assemble(lock, {}, [], run / 'release-candidate', working=True,
             preserved=paths, reviewed_order=order, preserved_sources=descriptors)
    save(run / 'ASSEMBLY-RESULT.json', {
        'pack_count': len(paths), 'changed': changes,
        'preserved_identical_to_installed': len(paths) - len(replaced),
        'tests_executed': False, 'deployed': False})
    config['sources'] = {key: str(sources[key]) for key in config['sources']}
    config['extension'] = str(sources['private'])
    config['output_dir'] = str(run / 'deployment')
    config['memory_budget']['unit'] = options['memory_unit']
    config['staging_repair'].update(
        candidate_dir=str(run / 'release-candidate'), source_batch=str(run / 'source-batch.json'),
        review_file=str(run / 'source-review.json'))
    save(run / 'staging-config.json', config)
    return {'packs': len(paths), 'changed': changes, 'preserved': len(paths) - len(replaced)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('options', type=Path)
    options = read(parser.parse_args().options)
    print(json.dumps(assemble_batch(options)))


if __name__ == '__main__':
    main()
