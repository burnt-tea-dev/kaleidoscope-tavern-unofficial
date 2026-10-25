"""Fixed overlay boundary and evidence-parser counterexamples; no BDS or world DB.

Native logs below are explicitly synthetic protocol fixtures. They do not
certify native loading, persistence, Players or any gameplay outcome.
"""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from family_update import common as c
from family_update import fishing_native_observer as m
from family_bundle import audit as canonical_audit


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + '\n')


def hashes(root):
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob('*') if path.is_file()}


class FishingObserverTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.output = self.base / 'output'; self.private = self.base / 'private'
        self.candidate = self.output / 'release-candidate'
        self.engine = self.output / 'saved-world-engine'
        self.world = self.engine / 'worlds/Saved World QA'
        self.private.mkdir(); self.world.mkdir(parents=True)
        self.recipe = {'schema': 1, 'kind': 'canonical_local_fishing_repair', 'version': [1, 3, 10005],
                       'historical_origin_status': 'unknown', 'original_archive_verified': False, 'latest_stable_verified': False,
                       'native_loading': False, 'saved_world_migration': False, 'client': False, 'production_ready': False}
        input_recipe = self.private / m.INPUT_RECIPE
        write(input_recipe, {'kind': 'exact current input fixture'})
        self.recipe['input_recipe'] = {'path': m.INPUT_RECIPE, 'sha256': c.sha(input_recipe)}
        for name in [m.PROBE, *m.HELPERS, m.MAIN_SOURCE, m.TANKS_SOURCE]:
            path = self.private / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('// explicit test source ' + name + '\n')
        (self.private / m.TANKS_SOURCE).write_bytes(m.QA_ORPHAN_BEFORE + b'\n')
        write(self.private / '.repo-target.json', {'repository': 'burnt-tea-dev/senluo-family-integration-private',
              'repository_id': 1406868911, 'private': True, 'owner': {'login': 'burnt-tea-dev', 'id': 344456559, 'type': 'Organization'}})
        self.receipt = {'packs': [], 'order': {'behavior': [], 'resource': []}}
        for side, uid in [('behavior', m.BP), ('resource', m.RP), ('behavior', 'unrelated-pack')]:
            pack = self.candidate / (side + '_packs') / uid
            write(pack / 'manifest.json', {'header': {'uuid': uid, 'version': [1, 3, 10005]}})
            if uid == m.BP:
                for name in [m.MAIN_SOURCE, m.TANKS_SOURCE, *m.HELPERS]:
                    relative = name.split('/BP/', 1)[1]; target = pack / relative
                    target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes((self.private / name).read_bytes())
            if uid == 'unrelated-pack':
                (pack / 'sentinel.bin').write_bytes(b'unchanged original payload')
            row = {'uuid': uid, 'side': side, 'version': [1, 3, 10005], 'files': hashes(pack)}
            self.receipt['packs'].append(row); self.receipt['order'][side].append(uid)
        self.recipe['output_hashes'] = {label: next(row['files'] for row in self.receipt['packs'] if row['uuid'] == uid)
                                        for label, uid in [('BP', m.BP), ('RP', m.RP)]}
        write(self.private / m.RECIPE, self.recipe)
        subprocess.run(['git', 'init', '-q', str(self.private)], check=True)
        subprocess.run(['git', '-C', str(self.private), 'add', '.'], check=True)
        self.commit('fixture source')
        write(self.candidate / 'family-receipt.json', self.receipt)
        for side, order in self.receipt['order'].items():
            write(self.candidate / ('world_' + side + '_packs.json'), [{'pack_id': uid, 'version': [1, 3, 10005]} for uid in order])
        for source in self.candidate.iterdir():
            if source.is_dir(): shutil.copytree(source, self.world / source.name)
            else: shutil.copy2(source, self.world / source.name)
        write(self.output / 'production-before/backup-receipt.json', {'consistent_stopped_backup': True, 'source': 'synthetic'})
        self.review = self.private / 'maintenance/review.json'
        write(self.review, {'profile': 'reviewed-same-uuid-local-input-repair-v1', 'local_existing_input': {'action': 'repair_forward'}})
        self.stack = self.enterContext(contextlib.ExitStack())
        self.stack.enter_context(patch.multiple(c, R=self.output, C=self.candidate, EXTENSION=self.private,
                                               CONFIG={'managed_drift_recovery': str(self.review)}))
        self.stack.enter_context(patch.object(c, 'assert_lease'))
        self.stack.enter_context(patch.object(c, 'atomic', side_effect=write))
        self.stack.enter_context(patch.object(c, 'audit_candidate', side_effect=self.audit))

    def commit(self, message):
        subprocess.run(['git', '-C', str(self.private), '-c', 'user.name=Observer fixture', '-c', 'user.email=observer@example.invalid', 'commit', '-qm', message], check=True)

    def audit(self, world, receipt):
        with contextlib.redirect_stdout(io.StringIO()):
            return canonical_audit(world, receipt)

    def install(self):
        self.overlay = m.install(self.world, self.receipt)
        return self.overlay

    def log_rows(self, phase):
        key = 'kfv:qa:contents:minecraft:overworld:24,300,8'
        stacks = [{'id': identifier, 'amount': 1, 'name': 'Native fish ' + str(index), 'lore': ['whole native payload'],
                   'rawLore': [{'text': 'whole native payload'}], 'canDestroy': ['minecraft:stone'], 'canPlaceOn': ['minecraft:glass'],
                   'keep': True, 'lock': 'inventory', 'properties': [], 'damage': None, 'enchantments': None}
                  for index, identifier in enumerate(['kaleidoscope_fishing:carp', 'kaleidoscope_fishing:carp', 'kaleidoscope_fishing:grass_carp'])]
        native = {'schema': 1, 'key': key, 'dimension': 'minecraft:overworld', 'position': m.POSITION,
                  'ids': [stack['id'] for stack in stacks] + [None], 'entity': 'original-carrier', 'token': 'original-token', 'retired': False}
        persistence = {'mode': 'native-fishing-persistence', 'phase': phase, 'fixture': 'same-fixture', 'key': key,
                       'carrier': 'original-carrier', 'nativeRecord': native, 'nativeStacks': stacks + [None], 'nativeCarrierCount': 1,
                       'playerUse': False, 'actualFishingOwnerScope': True, 'opaqueDynamicPropertiesConstructed': False,
                       'completeNbtByteComparison': False, 'client': False}
        if phase == 'first':
            cases = [{'mode': 'native-fishing-DP-write-rollback', 'phase': phase, 'fault': fault, 'nativeContainers': True,
                      'injectedDPWrite': True, 'playerUse': False, 'client': False} for fault in ['before', 'after']] + [persistence]
        else:
            cases = [persistence, {'mode': 'native-fishing-recovery', 'phase': phase, 'fixture': 'same-fixture',
                      'receiptSlots': m.SLOTS, 'recoveredStacks': stacks, 'retiredTombstone': {**native, 'ids': [None] * 4, 'entity': None, 'retired': True},
                      'repeatedReturnRejected': True, 'playerUse': False, 'client': False}]
        envelope = {'schema': 1, 'binding_id': self.overlay['binding_id'], 'phase': phase}
        rows = [{**envelope, 'type': 'case', 'case': case} for case in cases]
        rows.append({**envelope, 'type': 'done', 'ok': True, 'cases': len(cases), 'safe_scene': {
            'binding_id': self.overlay['binding_id'], 'before_type': 'minecraft:air', 'before_entities': 0,
            'position': m.POSITION, 'block_type': 'minecraft:chest', 'receipt_slots': m.SLOTS},
            'players': 0, 'simulated_players': False, 'player_use': False, 'client': False})
        return rows

    def put_log(self, phase, rows=None):
        rows = self.log_rows(phase) if rows is None else rows
        text = 'Server started.\n' + ''.join('[Scripting][warning] ' + m.PREFIX + json.dumps(row) + '\n' for row in rows)
        (self.engine / (phase + '.log')).write_text(text)

    def evidence(self):
        runs = []
        for phase in ['first', 'restart']:
            self.put_log(phase); m.verify(self.engine, self.world, phase, self.overlay)
            runs.append({'phase': phase, 'ok': True, 'started': True, 'family_initialized': True, 'exit_code': 0,
                         'errors': [], 'real_player_connections': 0, 'log_sha256': c.sha(self.engine / (phase + '.log'))})
        evidence = {'test_only_overlays': [self.overlay], 'candidate_receipt_sha256': c.sha(self.candidate / 'family-receipt.json'), 'runs': runs}
        evidence['test_only_overlay_removal'] = m.remove(self.world, self.receipt, self.overlay, evidence=evidence)
        return evidence

    def test_exact_four_path_overlay_preserves_original_payload_and_candidate_receipt(self):
        before = hashes(self.candidate); original = copy.deepcopy(self.receipt)
        overlay = self.install()
        self.assertEqual(len(overlay['files']), 4)
        self.assertTrue(overlay['actual_fishing_owner_scope']); self.assertTrue(overlay['helpers_unchanged'])
        m.audit(self.world, self.receipt, overlay)
        self.assertEqual(hashes(self.candidate), before); self.assertEqual(self.receipt, original)

    def test_orphan_exclusion_is_one_exact_qa_key_in_the_reviewed_function(self):
        self.install(); projected = (self.world / 'behavior_packs' / m.BP / m.TANKS).read_bytes()
        self.assertIn(m.QA_ORPHAN_AFTER, projected)
        self.assertEqual(projected.count(b"if (key === 'kfv:qa:contents:minecraft:overworld:24,300,8') return;"), 1)
        self.assertNotIn(b"startsWith('kfv:qa", projected)
        forged = copy.deepcopy(self.overlay)
        next(row for row in forged['files'] if row['path'].endswith(m.TANKS))['after_sha256'] = 'f' * 64
        with self.assertRaises(AssertionError): m.audit(self.world, self.receipt, forged)

    def test_removal_restores_all_original_bytes_mode_and_mtime(self):
        self.install(); evidence = self.evidence()
        self.assertEqual(hashes(self.world / 'behavior_packs'), hashes(self.candidate / 'behavior_packs'))
        for name in [m.MAIN, m.TANKS]:
            self.assertEqual(m._metadata(self.world / 'behavior_packs' / m.BP / name), m._metadata(self.candidate / 'behavior_packs' / m.BP / name))
        self.assertTrue(m.validate_native_evidence(evidence)['ok'])

    def test_removal_refuses_an_active_engine_or_missing_second_phase(self):
        self.install()
        with patch('family_update.storage.assert_idle', side_effect=RuntimeError('active BDS')):
            with self.assertRaises(RuntimeError): m.remove(self.world, self.receipt, self.overlay, evidence={})
        self.put_log('first'); m.verify(self.engine, self.world, 'first', self.overlay)
        with self.assertRaises(FileNotFoundError): m.remove(self.world, self.receipt, self.overlay, evidence={})
        m.audit(self.world, self.receipt, self.overlay)

    def test_forged_removal_reference_cannot_skip_canonical_restore(self):
        self.install(); evidence = self.evidence()
        path = self.output / 'fishing-native-observer-removal.json'; record = json.loads(path.read_text())
        record['canonical_candidate_audited'] = False; write(path, record)
        evidence['test_only_overlay_removal']['sha256'] = c.sha(path)
        with self.assertRaises(AssertionError): m.validate_native_evidence(evidence)

    def test_unrelated_payload_change_is_not_hidden_by_projection(self):
        self.install(); (self.world / 'behavior_packs/unrelated-pack/sentinel.bin').write_bytes(b'changed')
        with self.assertRaises(SystemExit): m.audit(self.world, self.receipt, self.overlay)

    def test_helper_change_in_actual_fishing_scope_is_rejected(self):
        self.install(); (self.world / 'behavior_packs' / m.BP / 'scripts/blocks/tank-contents.js').write_bytes(b'changed')
        with self.assertRaises(SystemExit): m.audit(self.world, self.receipt, self.overlay)

    def test_arbitrary_main_append_is_rejected(self):
        self.install(); main = self.world / 'behavior_packs' / m.BP / m.MAIN
        main.write_bytes(main.read_bytes() + b'\nother_code();\n')
        with self.assertRaises(AssertionError): m.audit(self.world, self.receipt, self.overlay)

    def test_forged_added_file_hash_and_overlay_reference_do_not_authorize_bytes(self):
        self.install(); path = self.world / 'behavior_packs' / m.BP / m.PROBE_TARGET; path.write_bytes(b'forged')
        forged = copy.deepcopy(self.overlay)
        next(row for row in forged['files'] if row['path'].endswith(m.PROBE_TARGET))['after_sha256'] = c.sha(path)
        record = {key: value for key, value in forged.items() if key != 'evidence'}
        declaration = self.output / 'fishing-native-observer-overlay.json'; write(declaration, record)
        forged['evidence']['sha256'] = c.sha(declaration)
        with self.assertRaises(AssertionError): m.audit(self.world, self.receipt, forged)

    def test_symlinked_observer_is_rejected_even_when_bytes_match(self):
        self.install(); path = self.world / 'behavior_packs' / m.BP / m.PROBE_TARGET
        path.unlink(); path.symlink_to(self.private / m.PROBE)
        with self.assertRaises(AssertionError): m.audit(self.world, self.receipt, self.overlay)

    def test_uncommitted_private_source_is_rejected_before_overlay(self):
        (self.private / m.PROBE).write_bytes(b'uncommitted')
        with self.assertRaises(AssertionError): self.install()

    def test_commands_only_load_fixed_area_and_call_bound_server_event(self):
        self.install(); commands = m.commands('first')
        self.assertEqual(commands[0], 'tickingarea add circle 24 300 8 1 fishing_native_observer')
        self.assertTrue(commands[1].startswith('scriptevent ' + m.EVENT + ' '))
        self.assertNotIn('setblock', '\n'.join(commands))
        subprocess.run(['node', '--input-type=module', '--check'], input=m.LISTENER.replace('__BINDING__', 'a' * 64), text=True, check=True, capture_output=True)

    def test_two_phase_protocol_authenticates_exact_logs_and_native_payload(self):
        self.install(); evidence = self.evidence(); result = m.validate_native_evidence(evidence)
        self.assertTrue(result['ok']); self.assertTrue(result['actual_fishing_owner_scope'])
        self.assertFalse(result['complete_nbt_byte_comparison']); self.assertFalse(result['player_use'])

    def test_missing_or_duplicate_named_cases_are_rejected(self):
        self.install()
        for transform in [lambda rows: rows[1:], lambda rows: [rows[0], *rows]]:
            self.put_log('first', transform(self.log_rows('first')))
            with self.assertRaises(AssertionError): m.verify(self.engine, self.world, 'first', self.overlay)

    def test_native_fail_marker_wrong_binding_and_unsafe_original_cell_are_rejected(self):
        self.install()
        for change in ['fail', 'binding', 'unsafe']:
            rows = self.log_rows('first')
            if change == 'fail': rows[-1]['type'] = 'fail'
            if change == 'binding': rows[0]['binding_id'] = 'b' * 64
            if change == 'unsafe': rows[-1]['safe_scene']['before_type'] = 'minecraft:stone'
            self.put_log('first', rows)
            with self.assertRaises(AssertionError): m.verify(self.engine, self.world, 'first', self.overlay)

    def test_extra_overlay_and_changed_parent_lifecycle_are_rejected(self):
        self.install(); evidence = self.evidence()
        extra = copy.deepcopy(evidence); extra['test_only_overlays'].append(copy.deepcopy(self.overlay))
        with self.assertRaises(AssertionError): m.validate_native_evidence(extra)
        bad = copy.deepcopy(evidence); bad['runs'][1]['exit_code'] = 1
        with self.assertRaises(AssertionError): m.validate_native_evidence(bad)

    def test_changed_restart_payload_is_rejected_even_with_fresh_local_log_hash(self):
        self.install(); evidence = self.evidence()
        rows = self.log_rows('restart'); rows[0]['case']['nativeStacks'][0]['name'] = 'different saved payload'
        rows[1]['case']['recoveredStacks'][0]['name'] = 'different saved payload'; self.put_log('restart', rows)
        evidence['runs'][1]['log_sha256'] = c.sha(self.engine / 'restart.log')
        parsed = m._parse(self.engine, 'restart', self.overlay); write(self.output / 'fishing-native-observer-restart.json', parsed)
        with self.assertRaises(AssertionError): m.validate_native_evidence(evidence)

    def test_extra_protocol_case_fields_and_complete_nbt_claim_are_rejected(self):
        self.install()
        for change in ['extra', 'nbt']:
            rows = self.log_rows('first')
            if change == 'extra': rows[0]['case']['arbitraryApproval'] = True
            else: rows[2]['case']['completeNbtByteComparison'] = True
            self.put_log('first', rows)
            with self.assertRaises(AssertionError): m.verify(self.engine, self.world, 'first', self.overlay)


if __name__ == '__main__':
    unittest.main()
