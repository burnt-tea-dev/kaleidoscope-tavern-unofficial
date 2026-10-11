"""Deletion guards for completed QA inputs; no Minecraft execution."""
import json
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from family_update import cleanup_engine_inputs as cleanup


class EngineInputCleanup(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.engine = self.root / 'task/closed-probe'
        self.engine.mkdir(parents=True)
        (self.engine / 'bedrock_server').write_bytes(b'reproducible test engine')
        (self.engine / 'definitions').mkdir()
        (self.engine / 'definitions/original.json').write_text('{}')
        (self.engine / 'worlds').mkdir()
        (self.engine / 'worlds/probe-source.js').write_text('unique observer source')
        (self.engine / 'first.log').write_text('original diagnostic evidence')
        self.report = self.engine / 'report.json'
        self.report.write_text(json.dumps({'ok': True, 'normal_stop': True,
                                         'exit_code': 0, 'errors': []}))
        self.context = {'protected': [], 'references': [], 'lease': {}}
        writer = patch.object(cleanup.c, 'atomic', lambda p, v: Path(p).write_text(json.dumps(v)))
        writer.start()
        self.addCleanup(writer.stop)
        reference = patch.object(cleanup, 'asset_reference', return_value=None)
        self.reference = reference.start()
        self.addCleanup(reference.stop)

    def test_closed_inputs_retire_but_world_source_and_evidence_remain(self):
        (self.root / 'release-candidate').mkdir()
        (self.root / 'release-candidate/family-receipt.json').write_text('{}')
        plan = cleanup.plan(self.root, self.context)
        self.assertEqual(len(plan['selected']), 1)
        result = cleanup.execute(plan, lambda: self.context)
        self.assertEqual(result['state'], 'completed')
        self.assertFalse((self.engine / 'bedrock_server').exists())
        self.assertFalse((self.engine / 'definitions').exists())
        self.assertEqual((self.engine / 'worlds/probe-source.js').read_text(), 'unique observer source')
        self.assertEqual((self.engine / 'first.log').read_text(), 'original diagnostic evidence')
        self.assertTrue(self.report.exists())

    def test_new_reference_after_plan_prevents_deletion(self):
        plan = cleanup.plan(self.root, self.context)
        self.context['references'] = [self.engine / 'worlds/probe-source.js']
        result = cleanup.execute(plan, lambda: self.context)
        self.assertEqual(result['deleted'], [])
        self.assertTrue((self.engine / 'bedrock_server').exists())

    def test_failed_unknown_and_managed_unretired_engines_stay(self):
        for value in [{'ok': False, 'normal_stop': True, 'exit_code': 0, 'errors': []},
                      {'ok': True, 'exit_code': 0, 'errors': []}]:
            self.report.write_text(json.dumps(value))
            self.assertEqual(cleanup.plan(self.root, self.context)['selected'], [])
        self.report.write_text(json.dumps({'ok': True, 'normal_stop': True, 'exit_code': 0, 'errors': []}))
        (self.engine.parent / 'build-evidence.json').write_text('{}')
        self.assertEqual(cleanup.plan(self.root, self.context)['selected'], [])

    def test_identical_assets_retire_but_different_assets_and_source_remain(self):
        source = self.root / 'retained/resource_packs/uuid'
        copied = self.engine / 'worlds/QA/resource_packs/uuid'
        for pack in [source, copied]:
            (pack / 'textures/items').mkdir(parents=True)
            (pack / 'sounds').mkdir()
            (pack / 'textures/items/icon.png').write_bytes(b'original image')
        (source / 'textures/item_texture.json').write_bytes(b'new atlas')
        (copied / 'textures/item_texture.json').write_bytes(b'old atlas retained')
        (copied / 'manifest.json').write_text(json.dumps({'header': {'uuid': 'uuid'}}))
        (source / 'sounds/unique.ogg').write_bytes(b'original sound')
        (copied / 'sounds/unique.ogg').write_bytes(b'unique diagnostic sound')
        files = {'textures/item_texture.json': hashlib.sha256(b'new atlas').hexdigest(),
                 'textures/items/icon.png': hashlib.sha256(b'original image').hexdigest(),
                 'sounds/unique.ogg': hashlib.sha256(b'original sound').hexdigest()}
        self.reference.return_value = (self.root / 'receipt.json', self.root / 'retained',
                                       {('resource', 'uuid'): {'files': files}})
        cache = {}
        plan = cleanup.plan(self.root, self.context, cache)
        result = cleanup.execute(plan, lambda: self.context, cache)
        self.assertEqual(result['state'], 'completed')
        self.assertFalse((copied / 'textures/items').exists())
        self.assertEqual((copied / 'textures/item_texture.json').read_bytes(), b'old atlas retained')
        self.assertEqual((copied / 'sounds/unique.ogg').read_bytes(), b'unique diagnostic sound')
        self.assertEqual((source / 'textures/items/icon.png').read_bytes(), b'original image')
        self.assertTrue((copied / 'manifest.json').exists())
        self.assertTrue((self.engine / 'worlds/probe-source.js').exists())

    def structure_copy(self):
        source = self.root / 'retained/behavior_packs/uuid'
        copied = self.engine / 'worlds/QA/behavior_packs/uuid'
        structure = 'structures/reusable/hall.mcstructure'
        original = b'original binary structure'
        for pack in [source, copied]:
            (pack / structure).parent.mkdir(parents=True)
            (pack / structure).write_bytes(original)
        (copied / 'manifest.json').write_text(json.dumps({'header': {'uuid': 'uuid'}}))
        self.reference.return_value = (self.root / 'receipt.json', self.root / 'retained',
                                       {('behavior', 'uuid'): {'files': {structure: hashlib.sha256(original).hexdigest()}}})
        return source, copied, structure

    def test_reconstructible_bp_structures_retire_with_db_scripts_json_and_foreign_side_preserved(self):
        source, copied, structure = self.structure_copy()
        # Even a receipt-backed JSON copy stays outside the binary asset scope.
        for pack in [source, copied]:
            (pack / 'structures/metadata.json').write_bytes(b'original metadata')
        self.reference.return_value[2][('behavior', 'uuid')]['files']['structures/metadata.json'] = hashlib.sha256(b'original metadata').hexdigest()
        (copied / 'scripts').mkdir()
        (copied / 'scripts/observer.js').write_text('unique observer script')
        (copied / 'models').mkdir()
        (copied / 'models/unique.json').write_text('unique diagnostic model')
        db = copied.parents[1] / 'db'
        db.mkdir();(db / 'CURRENT').write_bytes(b'original world database')
        foreign = copied.parent / 'foreign'
        (foreign / structure).parent.mkdir(parents=True)
        (foreign / structure).write_bytes((source / structure).read_bytes())
        (foreign / 'manifest.json').write_text(json.dumps({'header': {'uuid': 'foreign'}}))
        # An admitted RP with the same UUID cannot authorize a BP deletion.
        self.reference.return_value[2][('resource', 'foreign')] = self.reference.return_value[2][('behavior', 'uuid')]
        cache = {}
        plan = cleanup.plan(self.root, self.context, cache)
        result = cleanup.execute(plan, lambda: self.context, cache)
        self.assertEqual(result['state'], 'completed')
        self.assertFalse((copied / 'structures/reusable').exists())
        self.assertEqual((source / structure).read_bytes(), b'original binary structure')
        self.assertEqual((copied / 'structures/metadata.json').read_bytes(), b'original metadata')
        self.assertEqual((copied / 'scripts/observer.js').read_text(), 'unique observer script')
        self.assertEqual((copied / 'models/unique.json').read_text(), 'unique diagnostic model')
        self.assertEqual((db / 'CURRENT').read_bytes(), b'original world database')
        self.assertTrue((copied / 'manifest.json').exists())
        self.assertTrue((foreign / structure).exists())
        self.assertTrue(self.report.exists())

    def test_changed_admitted_structure_source_prevents_retirement(self):
        source, copied, structure = self.structure_copy()
        cache = {}
        plan = cleanup.plan(self.root, self.context, cache)
        self.assertTrue(any('asset_reference' in t for r in plan['selected'] for t in r['targets']))
        (source / structure).write_bytes(b'changed source is outside the admitted receipt')
        result = cleanup.execute(plan, lambda: self.context, cache)
        self.assertEqual(result['deleted'], [])
        self.assertEqual((copied / structure).read_bytes(), b'original binary structure')

    def test_symlink_payload_rejected_and_active_lease_preserved(self):
        (self.engine / 'definitions/link').symlink_to(self.root / 'outside')
        self.assertEqual(cleanup.plan(self.root, self.context)['selected'], [])
        (self.engine / 'definitions/link').unlink()
        self.context['lease'] = {'state': 'active'}
        self.assertEqual(cleanup.plan(self.root, self.context)['selected'], [])

    def retirement_list(self):
        path = self.root / 'retired-diagnostics.json'
        path.write_text(json.dumps({'schema': 1, 'engines': [
            {'engine': str(self.engine), 'reason': 'Superseded diagnostic; owner reviewed closure'}]}))
        return path

    def diagnostic_world(self):
        world = self.engine / 'worlds/QA'
        db = world / 'db'
        db.mkdir(parents=True)
        (db / '000001.ldb').write_bytes(b'temporary database')
        (db / 'CURRENT').write_text('MANIFEST-000001')
        (db / 'LOG').write_text('original DB diagnostic log')
        pack = world / 'behavior_packs/uuid'
        (pack / 'scripts').mkdir(parents=True)
        (pack / 'scripts/observer.js').write_text('unique observer source')
        (pack / 'structures').mkdir()
        (pack / 'structures/hall.mcstructure').write_bytes(b'generated asset')
        (pack / 'structures/metadata.json').write_text('unique diagnostic JSON')
        (pack / 'manifest.json').write_text('{}')
        (pack / 'models').mkdir()
        (pack / 'models/diagnostic.png').write_bytes(b'keep assets outside approved directories')
        return db, pack

    def test_explicit_failed_retirement_removes_generated_data_preserving_failure_and_sources(self):
        self.report.write_text(json.dumps({'ok': False, 'normal_stop': True, 'exit_code': 0, 'errors': ['known failure']}))
        original_report = self.report.read_bytes()
        db, pack = self.diagnostic_world()
        review = self.retirement_list()
        with patch.object(cleanup.retention, 'plan', side_effect=AssertionError('No deployment scan for explicit probes')):
            plan = cleanup.plan(self.root, self.context, retire_diagnostics=review)
            result = cleanup.execute(plan, lambda: self.context)
        self.assertFalse((db / '000001.ldb').exists())
        self.assertFalse((db / 'CURRENT').exists())
        self.assertFalse((pack / 'structures/hall.mcstructure').exists())
        self.assertTrue(result['test_world_database_files_removed'])
        for path in [db / 'LOG', pack / 'scripts/observer.js', pack / 'structures/metadata.json',
                     pack / 'manifest.json', pack / 'models/diagnostic.png', self.engine / 'first.log']:
            self.assertTrue(path.exists(), str(path))
        self.assertEqual(self.report.read_bytes(), original_report)
        marker = json.loads((self.engine / cleanup.MARKER).read_text())
        self.assertIsNone(marker['report'])
        self.assertFalse(marker['diagnostic_retirement']['reports'][0]['original_status']['ok'])

    def test_explicit_unknown_report_requires_review_and_preserves_source(self):
        self.report.unlink()
        self.assertEqual(cleanup.plan(self.root, self.context)['selected'], [])
        db, pack = self.diagnostic_world()
        plan = cleanup.plan(self.root, self.context, retire_diagnostics=self.retirement_list())
        self.assertEqual(len(plan['selected']), 1)
        self.assertEqual(plan['selected'][0]['diagnostic_retirement']['reports'], [])
        cleanup.execute(plan, lambda: self.context)
        self.assertFalse((db / '000001.ldb').exists())
        self.assertTrue((pack / 'scripts/observer.js').exists())

    def test_explicit_list_report_or_asset_change_before_execute_preserves_targets(self):
        db, pack = self.diagnostic_world()
        review = self.retirement_list()
        plan = cleanup.plan(self.root, self.context, retire_diagnostics=review)
        review.write_text(review.read_text() + '\n')
        with self.assertRaisesRegex(RuntimeError, 'list changed'):
            cleanup.execute(plan, lambda: self.context)
        self.assertTrue((db / '000001.ldb').exists())
        plan = cleanup.plan(self.root, self.context, retire_diagnostics=review)
        self.report.write_text('{}')
        self.assertEqual(cleanup.execute(plan, lambda: self.context)['deleted'], [])
        # Bind every leaf in a wholly generated directory: a same-size rewrite
        # with restored mtime leaves the parent metadata and allocation intact.
        (pack / 'structures/metadata.json').unlink()
        plan = cleanup.plan(self.root, self.context, retire_diagnostics=review)
        asset = pack / 'structures/hall.mcstructure'
        before = asset.stat()
        asset.write_bytes(b'x' * before.st_size)
        os.utime(asset, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertEqual(cleanup.execute(plan, lambda: self.context)['deleted'], [])

    def test_explicit_review_cannot_override_sources_mounts_links_or_active_context(self):
        db, pack = self.diagnostic_world()
        review = self.retirement_list()
        for guard in [self.engine / 'worlds/QA', self.engine.parent]:
            self.context['protected'] = [guard]
            self.assertEqual(cleanup.plan(self.root, self.context, retire_diagnostics=review)['selected'], [])
        self.context['protected'] = []
        self.context['lease'] = {'state': 'active'}
        self.assertEqual(cleanup.plan(self.root, self.context, retire_diagnostics=review)['selected'], [])
        self.context['lease'] = {}
        with patch.object(cleanup, 'assert_idle', side_effect=RuntimeError('active process')):
            self.assertEqual(cleanup.plan(self.root, self.context, retire_diagnostics=review)['selected'], [])
        with patch.object(cleanup.retention, '_mount_paths', return_value={pack}):
            self.assertEqual(cleanup.plan(self.root, self.context, retire_diagnostics=review)['selected'], [])
        (pack / 'structures/link').symlink_to(self.root / 'outside')
        self.assertEqual(cleanup.plan(self.root, self.context, retire_diagnostics=review)['selected'], [])
        (pack / 'structures/link').unlink()
        (self.engine.parent / '.git').mkdir()
        self.assertEqual(cleanup.plan(self.root, self.context, retire_diagnostics=review)['selected'], [])

    def test_explicit_review_rejects_managed_ancestor_beyond_two_levels(self):
        self.engine = self.root / 'deployment/a/b/c/probe'
        self.engine.mkdir(parents=True)
        (self.engine / 'bedrock_server').write_bytes(b'test executable')
        (self.root / 'deployment/build-evidence.json').write_text('{}')
        plan = cleanup.plan(self.root, self.context, retire_diagnostics=self.retirement_list())
        self.assertEqual(plan['selected'], [])
        self.assertIn('managed deployment', plan['preserved'][0]['reason'])

    def test_each_explicit_deletion_boundary_rechecks_ancestry_and_mounts(self):
        db, pack = self.diagnostic_world()
        plan = cleanup.plan(self.root, self.context, retire_diagnostics=self.retirement_list())
        calls = 0
        def context():
            nonlocal calls
            calls += 1
            if calls == 3:
                (self.engine.parent / 'build-evidence.json').write_text('{}')
            return self.context
        with self.assertRaisesRegex(RuntimeError, 'ancestry changed'):
            cleanup.execute(plan, context)
        self.assertTrue((self.engine / 'bedrock_server').exists())
        self.assertTrue((db / '000001.ldb').exists())
        (self.engine.parent / 'build-evidence.json').unlink()
        plan = cleanup.plan(self.root, self.context, retire_diagnostics=self.retirement_list())
        calls = 0
        def context_with_mount():
            nonlocal calls
            calls += 1
            return self.context
        def mounts():
            return {self.engine} if calls >= 3 else set()
        with patch.object(cleanup.retention, '_mount_paths', side_effect=mounts):
            with self.assertRaisesRegex(ValueError, 'Mounted'):
                cleanup.execute(plan, context_with_mount)
        self.assertTrue((db / '000001.ldb').exists())

    def test_same_size_leaf_rewrite_during_deletion_is_detected_by_ctime(self):
        db, pack = self.diagnostic_world()
        (pack / 'structures/metadata.json').unlink()
        asset = pack / 'structures/hall.mcstructure'
        before = asset.stat()
        plan = cleanup.plan(self.root, self.context, retire_diagnostics=self.retirement_list())
        calls = 0
        def context():
            nonlocal calls
            calls += 1
            if calls == 3:
                asset.write_bytes(b'x' * before.st_size)
                os.utime(asset, ns=(before.st_atime_ns, before.st_mtime_ns))
            return self.context
        with self.assertRaisesRegex(RuntimeError, 'QA input changed'):
            cleanup.execute(plan, context)
        self.assertEqual(asset.read_bytes(), b'x' * before.st_size)
        self.assertTrue((pack / 'scripts/observer.js').exists())
        self.assertTrue(self.report.exists())


if __name__ == '__main__':
    unittest.main()
