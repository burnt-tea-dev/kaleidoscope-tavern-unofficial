"""Exercise source admission, strict assembly and rollback without a server."""
from contextlib import ExitStack
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from family_bundle import assemble
from family_guard import hashes
from family_update import common as c, deploy_live, selected_repair
from family_update.repository_identity import target
from family_update.source_batch import pack_tree


class SelectedRepairTests(unittest.TestCase):
    def git(self, *args):
        subprocess.run(['git', '-C', str(self.private), *args], check=True, capture_output=True)

    def write(self, path, document):
        path.write_text(json.dumps(document, indent=2) + '\n')
        return path

    def pack(self, base, side, uid, version):
        root = base / (side + '_packs') / uid
        root.mkdir(parents=True)
        self.write(root / 'manifest.json', {'header': {'uuid': uid, 'version': version},
                    'modules': [{'type': 'resources' if side == 'resource' else 'data', 'version': version}]})
        return root

    def setUp(self):
        stack = self.enterContext(ExitStack())
        root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        self.server = root / 'bds'
        self.world = self.server / 'worlds' / 'test'
        self.private = root / 'private'
        self.quality = root / 'quality'
        self.out = root / 'out'
        for path in (self.world, self.private / 'maintenance', self.quality, self.out):
            path.mkdir(parents=True)
        self.git('init', '-q')
        identity = target('casama233/senluo-family-integration-private')
        self.write(self.private / '.repo-target.json', identity)
        self.git('remote', 'add', 'origin', 'https://github.com/' + identity['repository'])
        self.original_file = root / 'owned-release.json'
        self.write(self.original_file, {'release': [1, 0, 2]})
        self.rows = []
        self.refs = {'behavior': [], 'resource': []}
        proof = {'schema': 1, 'kind': 'selected_pack_source', 'origin': 'owned_release',
                 'source': 'Fixture release', 'original': c.report_ref(self.original_file), 'packs': {}}
        replacements = {}
        for uid, side in (('retained', 'behavior'), ('paired-bp', 'behavior'), ('paired-rp', 'resource')):
            version = [1, 0, 1]
            path = self.pack(self.world, side, uid, version)
            self.rows.append({'uuid': uid, 'side': side, 'version': version, 'files': hashes(path),
                              'source': {'owner': 'upstream'}})
            self.refs[side].append({'pack_id': uid, 'version': version})
            if uid != 'retained':
                version = [1, 0, 2]
                artifact = self.pack(root / 'source', side, uid, version)
                pin = {'version': version, 'tree': pack_tree(hashes(artifact))}
                proof['packs'][uid] = {'side': side, **pin}
                replacements[uid] = {'artifact': str(artifact), **pin}
        for side, refs in self.refs.items():
            self.write(self.world / ('world_' + side + '_packs.json'), refs)
        evidence = self.write(self.private / 'maintenance' / 'source.json', proof)
        for row in replacements.values():
            row['evidence'] = {'path': 'maintenance/source.json', 'sha256': c.sha(evidence)}
        approved = self.write(root / 'approved.json', {'packs': self.rows + [{'uuid': 'retired'}],
                                                      'order': {'behavior': ['retained', 'paired-bp', 'retired'],
                                                                'resource': ['paired-rp']}})
        self.policy = {'approved_receipt': str(approved), 'managed_uuids': ['retired', 'paired-bp', 'paired-rp']}
        self.write(self.quality / 'senluo-policy.json', self.policy)
        self.review_file = self.private / 'maintenance' / 'review.json'
        self.review = {'schema': 1, 'kind': 'live_selected_repair',
                       'site': {'server': 'test', 'bds_root': str(self.server), 'world_dir': str(self.world)},
                       'approved_receipt_sha256': c.sha(approved), 'refs': self.refs, 'removed': ['retired'],
                       'observed_sources': {}, 'replacements': replacements}
        self.commit_review()
        self.config = {'live_selected_repair': str(self.review_file), 'normal_idle_update': str(root / 'idle.json')}
        for module in (c, deploy_live):
            stack.enter_context(patch.multiple(module, CONFIG=self.config, R=self.out, W=self.world, B=self.server,
                                               Q=self.quality, SERVER='test', EXTENSION=self.private, SOURCES={},
                                               G={'hashes': hashes}))

    def commit_review(self):
        self.write(self.review_file, self.review)
        self.git('add', '.')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'Review')

    def inventory(self):
        return c.pack_inventory(self.world, self.server, hash_files=hashes)

    def test_reviewed_removal_allows_strict_assembly_and_only_replaces_pair(self):
        inventory = self.inventory()
        with patch.object(c, 'CONFIG', {}):
            with self.assertRaisesRegex(AssertionError, 'Preserved review cannot remove packs'):
                c.check_live_against_policy(inventory)
        self.assertEqual(c.check_live_against_policy(inventory), self.policy)
        roots, sources, _, _ = selected_repair.inputs(inventory, self.policy)
        order = {side: [ref['pack_id'] for ref in rows] for side, rows in self.refs.items()}
        receipt = assemble({'owned': [], 'upstream': [], 'order': order}, {}, [], self.out / 'candidate',
                           preserved=roots, preserved_sources=sources, reviewed_order=order)
        selected_repair.verify_candidate(receipt, inventory, self.policy)
        changed, retained = deploy_live.installation_selection(receipt, inventory)
        self.assertEqual([row['uuid'] for row in changed], ['paired-bp', 'paired-rp'])
        self.assertEqual([row['uuid'] for row in retained], ['retained'])

    def test_rejects_wrong_site_missing_original_and_drift(self):
        original = self.inventory()
        with patch.object(c, 'SERVER', 'other'):
            with self.assertRaisesRegex(AssertionError, 'site differs'):
                selected_repair.inputs(original, self.policy)
        saved = self.original_file.read_bytes()
        self.original_file.write_text('different source')
        with self.assertRaisesRegex(AssertionError, 'Original source evidence changed'):
            selected_repair.inputs(original, self.policy)
        self.original_file.write_bytes(saved)
        original['refs']['behavior'].reverse()
        with self.assertRaisesRegex(AssertionError, 'references or order changed'):
            selected_repair.inputs(original, self.policy)
        (self.world / 'behavior_packs/retained/drift').write_text('unknown')
        with self.assertRaisesRegex(AssertionError, 'source changes differ'):
            selected_repair.inputs(self.inventory(), self.policy)

    def test_running_handoff_requires_this_site_and_zero_players(self):
        running = {'name': 'test', 'status': 'RUNNING', 'player_count': 0}
        deploy_live.require_empty_running_server(running)
        for state in ({**running, 'name': 'other'}, {**running, 'status': 'STOPPED'},
                      {**running, 'player_count': 1}, {**running, 'player_count': None}):
            with self.subTest(state=state), self.assertRaises(AssertionError):
                deploy_live.require_empty_running_server(state)

    def test_installation_rollback_reads_original_selection_bytes(self):
        original = self.inventory()
        snapshot = self.out / 'production-snapshot'
        snapshot.mkdir()
        capture = self.out / 'production-before'
        capture.mkdir()
        shutil.copy2(self.quality / 'senluo-policy.json', capture)
        names = ['world_behavior_packs.json', 'world_resource_packs.json']
        for name in names:
            shutil.copy2(self.world / name, snapshot)
            (self.world / name).write_text('[]')
        self.write(capture / 'backup-receipt.json', {'files': hashes(snapshot)})
        with patch.object(deploy_live, 'live_inventory', self.inventory):
            deploy_live.restore_packs(original, [], [])
        for name in names:
            self.assertEqual((self.world / name).read_bytes(), (snapshot / name).read_bytes())


if __name__ == '__main__':
    unittest.main()
