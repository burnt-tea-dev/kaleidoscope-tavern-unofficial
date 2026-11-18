"""Assemble a staging update from generated payloads and the current world."""
import argparse
import datetime
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from family_bundle import assemble
from family_update import common as c
from family_update.source_batch import (
    generated_pack, pack_tree, project_staging, source_provenance,
    staging_advisories,
)


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def assemble_batch(options):
    run, parent = (Path(options[key]) for key in ('run', 'parent'))
    installed_parent = Path(options.get('installed_parent', str(parent)))
    sources = {name: Path(path) for name, path in options['sources'].items()}
    config = c.read(installed_parent / 'staging-config.json')
    world = Path(config['world_dir'])
    bds = Path(config.get('bds_root', world))
    generated = c.read(run / 'generated-inputs.json')
    generation = c.read(run / 'generation.json')
    batch = c.read(parent / 'source-batch.json')
    inherited = batch['packs']
    batch.update(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 parent_source_batch=str(parent / 'source-batch.json'), scope=options['scope'],
                 tests_executed=False, remote_delivery=False, deployed=False, packs={})
    for name, commit in generation['sources'].items():
        batch['source_commits'][name] = {'path': str(sources[name]), 'commit': commit}
    source_provenance(batch, {name: sources[name] for name in generation['sources']})

    updates = {}
    for uid, recorded in generated.items():
        actual_uid, row, files = generated_pack(recorded['name'], recorded['side'], recorded['path'])
        assert actual_uid == uid and all(recorded[key] == row[key] for key in ('name', 'side', 'path', 'version', 'tree')), 'Generated output changed before assembly: ' + uid
        source = Path(row['path'])
        destination = run / 'batch-inputs' / row['name'] / row['side']
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != destination.resolve():
            shutil.copytree(source, destination)
            copied_uid, row, copied_files = generated_pack(row['name'], row['side'], destination)
            assert copied_uid == uid and copied_files == files, 'Batch input copy differs: ' + uid
        batch['packs'][uid] = row
        updates[uid] = {
            'uuid': uid, 'side': {'BP': 'behavior', 'RP': 'resource'}[row['side']],
            'version': row['version'], 'dependencies': row['dependencies'], 'files': files,
            'source': {'owner': 'preserved', 'role': 'reviewed_local_generated_input',
                       'source_batch': str(run / 'source-batch.json'), 'input_tree': row['tree'],
                       'working_candidate': True, 'official_author_release': False},
        }

    prior = c.read(installed_parent / 'release-candidate/family-receipt.json')
    retired = options.get('retire_uuids', [])
    candidate = run / 'release-candidate'
    lock = c.read(sources['tavern'] / 'family/upstream.lock.json')
    lock.update(owned=[], upstream=[])
    inventory = c.pack_inventory(world, bds, include_manifest=True)
    projected, changed = project_staging(inventory, updates, retired)
    paths, descriptors, kept = candidate_sources(projected, updates, batch['packs'], inherited, prior)
    order = {side: [ref['pack_id'] for ref in refs] for side, refs in projected['refs'].items()}
    preserved = {Path(row['path']): row for row in projected['packs'] if row['uuid'] not in updates}
    receipt = assemble(lock, {}, [], candidate, working=True, preserved=paths,
                       reviewed_order=order, preserved_sources=descriptors,
                       staging_updates=updates, staging_inventory=preserved)
    snapshot_differences = receipt['staging_snapshot_differences']
    changed_snapshots = {row['uuid'] for row in snapshot_differences if row['differs_from_initial']}
    batch['packs'].update({uid: row for uid, row in kept.items() if uid not in changed_snapshots})
    advisories = staging_advisories(prior, inventory, updates)
    save(run / 'source-batch.json', batch)
    save(candidate / 'family-receipt.json', receipt)
    for side, refs in projected['refs'].items():
        save(candidate / ('world_' + side + '_packs.json'), refs)
    installed = {row['uuid']: row for row in inventory['packs']}
    changes = [{'uuid': uid, 'name': generated[uid]['name'], 'side': generated[uid]['side'],
                'before': installed[uid]['version'], 'after': updates[uid]['version']}
               for uid in changed]
    result = {'packs': len(projected['packs']), 'changed': changes, 'update_uuids': list(updates),
              'preserved': len(projected['packs']) - len(changed) - len(snapshot_differences),
              'installed_advisories': advisories, 'snapshot_differences': snapshot_differences,
              'dependency_check': receipt['dependency_check']}
    save(run / 'ASSEMBLY-RESULT.json', {
        **result, 'pack_count': result['packs'], 'preserved_identical_to_installed': result['preserved'],
        'tests_executed': False, 'deployed': False})
    config['sources'] = {key: str(sources[key]) for key in config['sources']}
    config['extension'] = str(sources['private'])
    config['output_dir'] = str(run / 'deployment')
    config['memory_budget']['unit'] = options['memory_unit']
    config['staging_repair'].update(
        candidate_dir=str(candidate), source_batch=str(run / 'source-batch.json'),
        review_file=str(run / 'source-review.json'), retire_uuids=retired)
    save(run / 'staging-config.json', config)
    return result


def candidate_sources(projected, updates, generated, inherited, prior):
    previous = {row['uuid']: row for row in prior['packs']}
    paths, descriptors, kept = [], {}, {}
    for row in projected['packs']:
        uid = row['uuid']
        if uid in updates:
            paths.append(Path(generated[uid]['path']))
            descriptors[uid] = row['source']
            continue
        tree = pack_tree(row['files'])
        old = previous.get(uid)
        previous_source = old['source'] if old and old['files'] == row['files'] else None
        if previous_source and previous_source['owner'] == 'preserved' and not previous_source.get('official_author_release'):
            descriptors[uid] = previous_source
        else:
            descriptors[uid] = {'owner': 'preserved', 'role': 'installed_staging_pack',
                                'input_tree': tree, 'official_author_release': False}
        if uid in inherited and inherited[uid]['tree'] == tree:
            kept[uid] = inherited[uid]
        paths.append(Path(row['path']))
    return paths, descriptors, kept


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('options', type=Path)
    options = c.read(parser.parse_args().options)
    print(json.dumps(assemble_batch(options)))


if __name__ == '__main__':
    main()
