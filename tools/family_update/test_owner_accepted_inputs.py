"""Current-byte preservation must survive assembly and cached-candidate reuse."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from family_update import common as c
from family_update import build_candidate as build
from family_update import identity_migration
from family_update import managed_drift_recovery as m
from family_update import storage
from family_update.cookery_cache_validation import tree


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + '\n')


class AcceptedInputTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.private = self.root / 'private'; self.private.mkdir()
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(self.private)], check=True)
        self.uid = '5f808eda-2eed-47b9-94ca-8486af1c5c14'
        # Synthetic file hashes model the actual seven-file author / eight-file
        # accepted-chain distinction without carrying any private script body.
        self.files = {name: hashlib.sha256(name.encode()).hexdigest() for name in (
            'manifest.json', 'pack_icon.png', 'items/flashlight.json',
            'recipes/flashlight.json', 'scripts/main.js', 'scripts/treeCapitator.js',
            'scripts/veinMiner.js', 'scripts/senluo_chain.js')}
        row = {'uuid': self.uid, 'side': 'behavior', 'version': [1, 8, 10070],
               'files': self.files, 'source': {'owner': 'preserved'}}
        self.original = {'packs': [copy.deepcopy(row)], 'refs': {
            'behavior': [{'pack_id': self.uid, 'version': row['version']}], 'resource': []}}
        self.candidate = {'packs': [copy.deepcopy(row)], 'order': {'behavior': [self.uid], 'resource': []}}
        self.proof = {'schema': 1, 'kind': 'owner_accepted_current_exact_bytes',
                      'original_archive_verified': False, 'latest_stable_verified': False,
                      'official_author_release': False,
                      'packs': {'essentials_behavior': {key: copy.deepcopy(row[key]) for key in ('uuid', 'side', 'version')}}}
        self.proof['packs']['essentials_behavior']['tree'] = tree(self.files)
        self.proof_path = self.private / 'maintenance/current/accepted.safe.json'
        self.review = {'proofs': []}
        self.save_proof()
        self.enterContext(patch.multiple(c, EXTENSION=self.private,
                         CONFIG={'managed_drift_recovery': str(self.private / 'maintenance/review.json')}))
        self.enterContext(patch.object(m, 'load_review', side_effect=lambda: (self.review, {'path': 'committed-review'})))

    def save_proof(self):
        write(self.proof_path, self.proof)
        subprocess.run(['git', 'add', 'maintenance'], cwd=self.private, check=True)
        subprocess.run(['git', '-c', 'user.name=Source Test', '-c', 'user.email=source-test@example.invalid',
                        'commit', '-q', '--allow-empty', '-m', 'Reviewed accepted input'], cwd=self.private, check=True)
        self.review['proofs'] = [{'path': self.proof_path.relative_to(self.private).as_posix(),
                                 'sha256': c.sha(self.proof_path)}]

    def check(self):
        return m.verify_owner_accepted_inputs(self.candidate, self.original)

    def clean_author_substitution(self):
        self.candidate['packs'][0]['files'].pop('scripts/senluo_chain.js')
        self.candidate['packs'][0]['source'] = {'owner': 'upstream_extended'}

    def test_exact_whole_pack_passes_without_mutating_source_claims_or_evidence(self):
        before = copy.deepcopy((self.original, self.candidate, self.proof, self.review))
        self.check()
        self.assertEqual((self.original, self.candidate, self.proof, self.review), before)
        self.assertEqual(list(self.root.iterdir()), [self.private])

    def test_clean_author_with_same_uuid_and_version_cannot_remove_chain_module(self):
        self.clean_author_substitution()
        with self.assertRaisesRegex(AssertionError, 'candidate: essentials_behavior'):
            self.check()

    def test_full_tree_detects_changed_body_even_when_file_count_is_unchanged(self):
        self.candidate['packs'][0]['files']['scripts/main.js'] = 'f' * 64
        with self.assertRaisesRegex(AssertionError, 'candidate: essentials_behavior'):
            self.check()

    def test_uuid_side_and_version_are_all_required(self):
        for key, value in [('uuid', '00000000-0000-0000-0000-000000000001'),
                           ('side', 'resource'), ('version', [1, 8, 3])]:
            with self.subTest(key=key):
                changed = copy.deepcopy(self.candidate); changed['packs'][0][key] = value
                with self.assertRaisesRegex(AssertionError, 'candidate: essentials_behavior'):
                    m.verify_owner_accepted_inputs(changed, self.original)

    def test_captured_input_must_also_match_the_accepted_full_tree(self):
        self.original['packs'][0]['files']['scripts/main.js'] = 'e' * 64
        with self.assertRaisesRegex(AssertionError, 'captured input: essentials_behavior'):
            self.check()

    def test_missing_or_duplicate_candidate_identity_is_rejected(self):
        for packs in [[], self.candidate['packs'] * 2]:
            with self.subTest(packs=len(packs)), self.assertRaises(AssertionError):
                m.verify_owner_accepted_inputs({'packs': packs}, self.original)

    def test_accepted_bytes_do_not_become_verified_author_provenance(self):
        self.proof['official_author_release'] = True; self.save_proof()
        with self.assertRaisesRegex(AssertionError, 'do not establish author provenance'):
            self.check()

    def test_committed_proof_hash_and_worktree_bytes_must_agree(self):
        self.proof['packs']['essentials_behavior']['version'] = [1, 8, 10071]
        write(self.proof_path, self.proof)
        with self.assertRaisesRegex(AssertionError, 'not committed unchanged'):
            self.check()
        self.save_proof(); self.review['proofs'][0]['sha256'] = '0' * 64
        with self.assertRaisesRegex(AssertionError, 'proof differs'):
            self.check()

    def test_relative_path_and_symlink_boundaries_are_enforced(self):
        for name in ['../outside.json', '/tmp/outside.json', 'maintenance/../outside.json', 'maintenance\\outside.json']:
            with self.subTest(path=name):
                self.review['proofs'][0]['path'] = name
                with self.assertRaisesRegex(AssertionError, 'Unsafe owner-input proof path'):
                    self.check()
        link = self.private / 'maintenance/linked.safe.json'; link.symlink_to(self.proof_path)
        self.review['proofs'][0]['path'] = 'maintenance/linked.safe.json'
        with self.assertRaisesRegex(AssertionError, 'regular paths'):
            self.check()
        directory = self.private / 'maintenance/linked'; directory.symlink_to(self.proof_path.parent, target_is_directory=True)
        self.review['proofs'][0]['path'] = 'maintenance/linked/accepted.safe.json'
        with self.assertRaisesRegex(AssertionError, 'private maintenance source'):
            self.check()

    def test_a_new_reviewed_owner_decision_can_advance_the_accepted_source(self):
        for row in [self.original['packs'][0], self.candidate['packs'][0]]:
            row['version'] = [1, 8, 10071]
            row['files']['scripts/main.js'] = 'a' * 64
        self.proof['packs']['essentials_behavior'].update(version=[1, 8, 10071], tree=tree(self.candidate['packs'][0]['files']))
        self.save_proof(); self.check()

    def test_reviews_without_an_exact_byte_decision_keep_their_existing_behavior(self):
        self.proof = {'kind': 'historical_provenance'}; self.save_proof()
        m.verify_owner_accepted_inputs({}, {})
        text = self.private / 'maintenance/provenance.md'; text.write_text('Historical source record\n')
        subprocess.run(['git', 'add', 'maintenance'], cwd=self.private, check=True)
        subprocess.run(['git', '-c', 'user.name=Source Test', '-c', 'user.email=source-test@example.invalid',
                        'commit', '-q', '-m', 'Historical provenance'], cwd=self.private, check=True)
        self.review['proofs'] = [{'path': 'maintenance/provenance.md', 'sha256': c.sha(text)}]
        m.verify_owner_accepted_inputs({}, {})
        with patch.object(c, 'CONFIG', {}), patch.object(m, 'load_review') as load:
            m.verify_owner_accepted_inputs({}, {})
            load.assert_not_called()

    def test_build_rejects_clean_substitution_before_static_evidence(self):
        self.clean_author_substitution()
        output = self.root / 'build'; output.mkdir()
        def read(path):
            return [] if Path(path).name == 'preserved-packs.json' else {'owned': [], 'upstream': []}
        with patch.multiple(build, R=output, C=output / 'candidate', T=self.root, SOURCES={}, EXTENSION=None,
                            CONFIG=c.CONFIG), patch.object(build, 'lease_available'), \
                patch.object(build, 'verify_predeploy', return_value=self.original), \
                patch.object(build, 'source_state', return_value={}), patch.object(build, 'archive_paths', return_value=[]), \
                patch.object(build, 'read', side_effect=read), patch.object(storage, 'require_space'), \
                patch.object(identity_migration, 'assembly_order', return_value=self.candidate['order']), \
                patch.object(m, 'select_local_inputs', return_value=([], {}, None)), \
                patch.object(build, 'assemble', return_value=self.candidate), patch.object(build, 'quality') as quality:
            with self.assertRaisesRegex(AssertionError, 'candidate: essentials_behavior'):
                build.main(['--execute'])
            quality.assert_not_called()
        self.assertFalse((output / 'build-evidence.json').exists())

    def cached_environment(self):
        output = self.root / 'cached'; candidate = output / 'candidate'
        config_path = output / 'config.json'; write(config_path, {})
        write(self.root / 'family/upstream.lock.json', {})
        write(candidate / 'family-receipt.json', self.candidate)
        write(output / 'production-before/inventory.json', self.original)
        write(output / 'build-evidence.json', {
            'config_sha256': c.sha(config_path), 'orchestration_sha256': {}, 'external_input_sha256': {},
            'sources': {}, 'upstream_lock_sha256': c.sha(self.root / 'family/upstream.lock.json'),
            'tool_sha256': {}, 'candidate_receipt_sha256': c.sha(candidate / 'family-receipt.json')})
        self.enterContext(patch.multiple(c, R=output, C=candidate, T=self.root, CONFIG_PATH=config_path))
        self.enterContext(patch.object(c, 'orchestration_hashes', return_value={}))
        self.enterContext(patch.object(c, 'external_input_hashes', return_value={}))
        self.enterContext(patch.object(c, 'source_state', return_value={}))
        return output, candidate

    def test_cached_candidate_cannot_skip_accepted_pack_preservation(self):
        self.clean_author_substitution(); self.cached_environment()
        with patch.object(c, 'audit_candidate') as audit:
            with self.assertRaisesRegex(AssertionError, 'candidate: essentials_behavior'):
                c.verify_candidate_sources()
            audit.assert_not_called()

    def test_receipt_tampering_still_fails_the_existing_receipt_hash_gate_first(self):
        _, candidate = self.cached_environment()
        self.clean_author_substitution(); write(candidate / 'family-receipt.json', self.candidate)
        with patch.object(m, 'verify_owner_accepted_inputs') as accepted:
            with self.assertRaisesRegex(AssertionError, 'Assembled receipt changed'):
                c.verify_candidate_sources()
            accepted.assert_not_called()

    def test_accepted_receipt_still_requires_the_actual_assembled_files(self):
        _, candidate = self.cached_environment()
        root = candidate / 'behavior_packs' / self.uid
        for name in self.files:
            path = root / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(name.encode())
        for side, refs in self.original['refs'].items():
            write(candidate / ('world_' + side + '_packs.json'), refs)
        self.assertEqual(c.verify_candidate_sources(), self.candidate)
        (root / 'scripts/senluo_chain.js').unlink()
        with self.assertRaisesRegex(SystemExit, 'scripts/senluo_chain.js'):
            c.verify_candidate_sources()


class ReplacementSelectionTests(unittest.TestCase):
    def selection(self):
        return {'authors': {'Essentials': {'behavior_uuid': 'bp', 'resource_uuid': 'rp'}},
                'replacement_packs': {'Essentials': {
                    'BP': {'uuid': 'bp', 'version': [1, 8, 10070], 'tree': {'sha256': 'a' * 64, 'files': 8}},
                    'RP': {'uuid': 'rp', 'version': [1, 8, 10070], 'tree': {'sha256': 'b' * 64, 'files': 4}}}}}

    def test_complete_reviewed_pair_is_selected_as_one_replacement(self):
        from family_update import current_author_validation as v
        with patch.object(v, 'curated_selected', return_value=True), patch.object(v, 'current_selection', return_value=self.selection()):
            rows = v.replacement_rows()
        self.assertEqual(set(rows), {'bp', 'rp'})
        self.assertEqual({row['author'] for row in rows.values()}, {'Essentials'})

    def test_split_or_mismatched_replacement_fails_closed(self):
        from family_update import current_author_validation as v
        selection = self.selection()
        selection['replacement_packs']['Essentials']['RP']['uuid'] = 'wrong'
        with patch.object(v, 'curated_selected', return_value=True), patch.object(v, 'current_selection', return_value=selection):
            with self.assertRaisesRegex(AssertionError, 'Replacement identity'):
                v.replacement_rows()


if __name__ == '__main__':
    unittest.main()
