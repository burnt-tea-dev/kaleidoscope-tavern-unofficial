"""Exercise the canonical producer with small files, without a game world."""
import contextlib
import io
import json
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from family_bundle import assemble
from family_update import common as c
from family_update.assemble_batch import assemble_batch
from family_update.staging_repair import selection
from family_update.source_batch import generated_pack


class AssembleBatchTests(unittest.TestCase):
    def test_assemble_fixed_inputs_and_reject_changed_generation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source'
            (source / 'family').mkdir(parents=True)
            ids = {'BP': '11111111-1111-4111-8111-111111111111',
                   'RP': '22222222-2222-4222-8222-222222222222'}
            labels = {'BP': 'behavior', 'RP': 'resource'}
            order = {labels[side]: [uid] for side, uid in ids.items()}

            def write(path, value):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value))

            def pack(path, side, version):
                other = ids['RP' if side == 'BP' else 'BP']
                write(path / 'manifest.json', {
                    'format_version': 2, 'header': {'uuid': ids[side], 'version': [1, 0, version],
                                                   'name': 'Example', 'description': 'Small pack'},
                    'modules': [{'uuid': '33333333-3333-4333-8333-33333333333' + str(side == 'RP' and 1 or 0),
                                 'version': [1, 0, version], 'type': 'data' if side == 'BP' else 'resources'}],
                    'dependencies': [{'uuid': other, 'version': [1, 0, version]}]})
                (path / 'payload.txt').write_text('Payload ' + str(version))
                return generated_pack('Example', side, path)

            write(source / 'family/upstream.lock.json', {'schema': 1, 'owned': [], 'upstream': [], 'order': order})
            subprocess.run(['git', '-C', str(source), 'init', '-q'], check=True)
            subprocess.run(['git', '-C', str(source), 'add', '.'], check=True)
            subprocess.run(['git', '-C', str(source), '-c', 'user.name=Batch test',
                            '-c', 'user.email=batch@example.invalid', '-c', 'commit.gpgsign=false',
                            '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'Selected generation source'], check=True)
            generated_commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
            prior = root / 'installed'
            selected = root / 'selected-packs'
            previous = []
            for side, uid in ids.items():
                _, row, files = pack(selected / (labels[side] + '_packs') / uid, side, 1)
                previous.append({'uuid': uid, 'side': labels[side], 'files': files, 'version': row['version'],
                                 'source': {'owner': 'preserved', 'role': 'unchanged_external_dependency'}})
                write(selected / ('world_' + labels[side] + '_packs.json'), [{'pack_id': uid, 'version': row['version']}])
            write(prior / 'release-candidate/family-receipt.json', {'packs': previous, 'order': order})
            write(prior / 'source-batch.json', {'source_commits': {}, 'packs': {}})
            sources = {name: str(source) for name in ('tavern', 'grilling', 'world-liquor', 'private')}
            write(prior / 'staging-config.json', {
                'world_dir': str(selected), 'sources': {name: str(source) for name in sources if name != 'private'},
                'memory_budget': {'unit': 'previous'}, 'staging_repair': {}})

            def prepare(name):
                run = root / name
                generated = {}
                for side in ids:
                    uid, row, _ = pack(run / 'batch-inputs/Example' / side, side, 2)
                    generated[uid] = row
                write(run / 'generated-inputs.json', generated)
                write(run / 'generation.json', {'sources': {name: generated_commit for name in sources}})
                return {'run': str(run), 'parent': str(prior), 'sources': sources,
                        'scope': 'Reviewed fixed inputs', 'memory_unit': 'example.service'}

            options = prepare('valid')
            (source / 'notes.txt').write_text('Unrelated work after generation')
            subprocess.run(['git', '-C', str(source), 'add', 'notes.txt'], check=True)
            subprocess.run(['git', '-C', str(source), '-c', 'user.name=Batch test',
                            '-c', 'user.email=batch@example.invalid', '-c', 'commit.gpgsign=false',
                            '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'Later unrelated work'], check=True)
            external_uid = '44444444-4444-4444-8444-444444444444'
            external = selected / 'behavior_packs' / external_uid
            external_manifest = {'header': {'uuid': external_uid, 'version': [1, 0, 1]},
                                 'modules': [{'uuid': external_uid, 'type': 'data', 'version': [1, 0, 1]}],
                                 'dependencies': [{'uuid': ids['BP'], 'version': [1, 0, 1]}]}
            write(external / 'manifest.json', external_manifest)
            external_ref = {'pack_id': external_uid, 'version': [1, 0, 1]}
            old_bp_ref = {'pack_id': ids['BP'], 'version': [1, 0, 1]}
            write(selected / 'world_behavior_packs.json', [external_ref, old_bp_ref])
            (external / 'payload.txt').write_text('Initially selected')
            external_copies = []

            def copy_during_external_edit(src, dst):
                if src != external:
                    return shutil.copytree(src, dst)
                external_copies.append(src)
                (external / 'payload.txt').write_text('Observed in the candidate copy')
                shutil.copytree(src, dst)
                (external / 'payload.txt').write_text('Most recent staging content')

            with contextlib.redirect_stdout(io.StringIO()), patch(
                    'family_bundle.shutil', SimpleNamespace(copytree=copy_during_external_edit)):
                result = assemble_batch(options)
            self.assertEqual(len(result['changed']), 2)
            self.assertEqual(external_copies, [external])
            self.assertEqual(result['packs'], 3)
            self.assertEqual(result['snapshot_differences'], [{
                'uuid': external_uid, 'observed_version': [1, 0, 1], 'candidate_version': [1, 0, 1],
                'differs_from_initial': True, 'differs_from_source_after_copy': True}])
            candidate = Path(options['run']) / 'release-candidate'
            for side, uid in ids.items():
                self.assertEqual((candidate / (labels[side] + '_packs') / uid / 'payload.txt').read_text(), 'Payload 2')
            self.assertEqual((candidate / 'behavior_packs' / external_uid / 'payload.txt').read_text(),
                             'Observed in the candidate copy')
            receipt = json.loads((candidate / 'family-receipt.json').read_text())
            self.assertEqual(receipt['order'], {**order, 'behavior': [external_uid, ids['BP']]})
            self.assertTrue(all(row['source']['owner'] == 'preserved' for row in receipt['packs']))
            self.assertEqual(receipt['dependency_check'], {'mode': 'advisory', 'differences': [{
                'uuid': external_uid, 'dependency': ids['BP'], 'required': [1, 0, 1], 'selected': [1, 0, 2]}]})
            self.assertFalse(receipt['acceptance']['static'])
            with self.assertRaisesRegex(SystemExit, 'unresolved exact dependency'):
                assemble({'owned': [], 'upstream': [], 'order': receipt['order']}, {}, [], root / 'strict',
                         working=True, preserved=[candidate / (row['side'] + '_packs') / row['uuid'] for row in receipt['packs']])

            batch = json.loads((Path(options['run']) / 'source-batch.json').read_text())
            self.assertEqual({row['commit'] for row in batch['source_commits'].values()}, {generated_commit})
            updates = {row['uuid']: row for row in receipt['packs'] if row['uuid'] in receipt['staging_updates']}
            # A later writer changes both the targeted version and the order.
            pack(selected / 'behavior_packs' / ids['BP'], 'BP', 3)
            write(selected / 'world_behavior_packs.json', [{**old_bp_ref, 'version': [1, 0, 3]}, external_ref])
            latest = c.pack_inventory(selected, selected, include_manifest=True)
            applied, pending = selection(latest, updates, batch, [])
            self.assertEqual(set(pending), set(ids.values()))
            self.assertEqual(applied['refs']['behavior'], [{**old_bp_ref, 'version': [1, 0, 2]}, external_ref])
            self.assertEqual(next(row for row in applied['packs'] if row['uuid'] == external_uid),
                             next(row for row in latest['packs'] if row['uuid'] == external_uid))

            # Selections made after the candidate exists survive installation.
            added_uid = '55555555-5555-4555-8555-555555555555'
            added = selected / 'behavior_packs' / added_uid
            write(added / 'manifest.json', {**external_manifest,
                  'header': {**external_manifest['header'], 'uuid': added_uid}})
            added_ref = {'pack_id': added_uid, 'version': [1, 0, 1]}
            write(selected / 'world_behavior_packs.json', [added_ref, {**old_bp_ref, 'version': [1, 0, 3]}])
            applied, pending = selection(c.pack_inventory(selected, selected, include_manifest=True), updates, batch, [])
            self.assertEqual(set(pending), set(ids.values()))
            self.assertEqual(applied['refs']['behavior'], [added_ref, {**old_bp_ref, 'version': [1, 0, 2]}])
            self.assertNotIn(external_uid, {row['uuid'] for row in applied['packs']})

            changed = prepare('changed')
            (Path(changed['run']) / 'batch-inputs/Example/BP/payload.txt').write_text('Edited after generation')
            with self.assertRaisesRegex(AssertionError, 'Generated output changed before assembly'):
                assemble_batch(changed)
            self.assertFalse((Path(changed['run']) / 'release-candidate').exists())


if __name__ == '__main__':
    unittest.main()
