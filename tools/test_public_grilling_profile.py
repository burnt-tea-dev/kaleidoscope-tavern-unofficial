"""Dependency closure and rejected public inputs, using small independent packs."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from family_bundle import packs
from public_grilling_profile import (COOKERY_BP, COOKERY_RP, COOKERY_SHA,
                                    export_local_mcaddon, select_public_grilling_lock,
                                    validate_public_archive)


class PublicGrillingProfileTests(unittest.TestCase):
    def source(self, root, key, version, pair, dependencies):
        repo = root / key
        config = {'repository': 'casama233/kaleidoscope-' + key + '-unofficial',
                  'repository_id': 1377218440 if key == 'grilling' else 1377171148,
                  'version': version, 'source_trees': {'BP': {'fixture': 'bp'}, 'RP': {'fixture': 'rp'}},
                  'runtime': {'BP': 'BP', 'RP': 'RP'}, 'packs': {}}
        for side, uid in zip(['BP', 'RP'], pair):
            path = repo / side
            path.mkdir(parents=True)
            (path / 'manifest.json').write_text(json.dumps({'header': {'uuid': uid, 'version': version}, 'dependencies': dependencies[side]}))
            config['packs'][side] = {'uuid': uid, 'dependencies': dependencies[side]}
        (repo / 'baseline.json').write_text(json.dumps(config))
        if key == 'grilling':
            p = repo / 'BP/host-extensions/board-api.json'
            p.parent.mkdir()
            p.write_text(json.dumps({'id': 'kaleidoscope_grilling:family-api-0.2.13', 'archive_sha256': COOKERY_SHA, 'host_uuid': COOKERY_BP}))
        return repo, {'key': key, 'repository': config['repository'], 'version': version, 'source_trees': config['source_trees']}

    def profile(self, root):
        dependencies = {'BP': [{'uuid': 'g-rp', 'version': [2, 8, 154]}, {'uuid': COOKERY_BP, 'version': [1, 6, 2]}],
                        'RP': [{'uuid': COOKERY_RP, 'version': [1, 6, 2]}]}
        g, own = self.source(root, 'grilling', [2, 8, 154], ['g-bp', 'g-rp'], dependencies)
        host = {'name': 'Cookery', 'project_id': 1673664, 'file_id': 9227406, 'sha256': COOKERY_SHA,
                'packs': [{'uuid': COOKERY_BP, 'version': [1, 6, 2]}, {'uuid': COOKERY_RP, 'version': [1, 6, 2]}]}
        lock = {'owned': [own, {'key': 'world-liquor'}], 'upstream': [host, {'name': 'Unrelated'}],
                'order': {'behavior': ['private-bp', 'g-bp', COOKERY_BP], 'resource': ['g-rp', COOKERY_RP, 'private-rp']}}
        return g, lock

    def test_minimal_and_optional_tavern_close_without_private_or_world_liquor(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            g, lock = self.profile(root)
            before = copy.deepcopy(lock)
            selected = select_public_grilling_lock(lock, {'grilling': g})
            self.assertEqual(selected['order']['behavior'], ['g-bp', COOKERY_BP])
            self.assertEqual([x['key'] for x in selected['owned']], ['grilling'])
            self.assertEqual(lock, before)
            t, own = self.source(root, 'tavern', [0, 6, 176], ['t-bp', 't-rp'], {'BP': [{'uuid': 't-rp', 'version': [0, 6, 176]}], 'RP': []})
            lock['owned'].append(own)
            lock['order']['behavior'].insert(0, 't-bp')
            lock['order']['resource'].insert(0, 't-rp')
            selected = select_public_grilling_lock(lock, {'grilling': g, 'tavern': t})
            self.assertIn('t-bp', selected['order']['behavior'])
            self.assertEqual({x['key'] for x in selected['owned']}, {'grilling', 'tavern'})

    def test_wrong_host_extra_source_and_missing_exact_dependency_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            g, lock = self.profile(Path(temp))
            changed = copy.deepcopy(lock)
            changed['upstream'][0]['file_id'] = 9123386
            with self.assertRaisesRegex(ValueError, 'clean Cookery'):
                select_public_grilling_lock(changed, {'grilling': g})
            with self.assertRaisesRegex(ValueError, 'only Grilling'):
                select_public_grilling_lock(lock, {'grilling': g, 'private': g})
            for p in [g / 'baseline.json', g / 'RP/manifest.json']:
                row = json.loads(p.read_text())
                deps = row['packs']['RP']['dependencies'] if p.name == 'baseline.json' else row['dependencies']
                deps.append({'uuid': 'unpublished-missing-pack', 'version': [1, 0, 0]})
                p.write_text(json.dumps(row))
            with self.assertRaisesRegex(ValueError, 'unresolved exact dependency'):
                select_public_grilling_lock(lock, {'grilling': g})

    def test_wrong_archive_and_extra_embedded_pack_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / 'owner.mcaddon'
            def write(extra=False):
                with zipfile.ZipFile(archive, 'w') as z:
                    for uid in ['fixture-bp', 'fixture-rp'] + (['unexpected-extra'] if extra else []):
                        m = {'header': {'uuid': uid, 'version': [1, 6, 2]}, 'modules': [{'type': 'data'}]}
                        z.writestr(uid + '/manifest.json', json.dumps(m))
            write()
            host = {'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'packs': [{'uuid': uid, 'version': [1, 6, 2]} for uid in ['fixture-bp', 'fixture-rp']]}
            validate_public_archive([archive], host, packs)
            with self.assertRaisesRegex(ValueError, 'exactly one'):
                validate_public_archive([archive, archive], host, packs)
            with self.assertRaisesRegex(ValueError, 'checksum differs'):
                validate_public_archive([archive], {**host, 'sha256': '0' * 64}, packs)
            write(extra=True)
            host['sha256'] = hashlib.sha256(archive.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, 'extra, missing or changed pack'):
                validate_public_archive([archive], host, packs)

    def test_local_export_reads_exact_receipted_bytes_and_refuses_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            root = out / 'behavior_packs/fixture'
            root.mkdir(parents=True)
            raw = b'{"fixture":true}'
            (root / 'manifest.json').write_bytes(raw)
            receipt = {'packs': [{'uuid': 'fixture', 'side': 'behavior', 'files': {'manifest.json': hashlib.sha256(raw).hexdigest()}}]}
            archive = export_local_mcaddon(out, receipt, 'owner-local.mcaddon')
            with zipfile.ZipFile(archive) as z:
                self.assertEqual(z.read('behavior_packs/fixture/manifest.json'), raw)
            (root / 'manifest.json').write_bytes(b'changed after assembly')
            with self.assertRaisesRegex(ValueError, 'bytes changed'):
                export_local_mcaddon(out, receipt, 'must-fail.mcaddon')


if __name__ == '__main__':
    unittest.main()
