"""Exercise the canonical producer with small files, without a game world."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from family_update.assemble_batch import assemble_batch
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
            with contextlib.redirect_stdout(io.StringIO()):
                result = assemble_batch(options)
            self.assertEqual(len(result['changed']), 2)
            candidate = Path(options['run']) / 'release-candidate'
            for side, uid in ids.items():
                self.assertEqual((candidate / (labels[side] + '_packs') / uid / 'payload.txt').read_text(), 'Payload 2')
            receipt = json.loads((candidate / 'family-receipt.json').read_text())
            self.assertEqual(receipt['order'], order)
            self.assertTrue(all(row['source']['owner'] == 'preserved' for row in receipt['packs']))
            batch = json.loads((Path(options['run']) / 'source-batch.json').read_text())
            self.assertEqual({row['commit'] for row in batch['source_commits'].values()}, {generated_commit})

            changed = prepare('changed')
            (Path(changed['run']) / 'batch-inputs/Example/BP/payload.txt').write_text('Edited after generation')
            with self.assertRaisesRegex(AssertionError, 'Generated output changed before assembly'):
                assemble_batch(changed)
            self.assertFalse((Path(changed['run']) / 'release-candidate').exists())


if __name__ == '__main__':
    unittest.main()
