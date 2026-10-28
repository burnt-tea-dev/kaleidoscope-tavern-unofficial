"""Preservation and failure boundaries for source-declared native world flags."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

import nbtlib
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bedrock_nbt import encode_root
from family_update import common as c, world_experiments as m

FLAGS = {'upcoming_creator_features': True}


def level():
    data = nbtlib.File({'LevelName': nbtlib.String('Existing Better Biomes'),
                       'RandomSeed': nbtlib.Long(-4567891234), 'SpawnX': nbtlib.Int(-42),
                       'Opaque': nbtlib.String('preserved-\udcff-\udc80'),
                       'Nested': nbtlib.Compound({'values': nbtlib.List[nbtlib.Int]([1, -2, 3])}),
                       'experiments': nbtlib.Compound({'gametest': nbtlib.Byte(0),
                           'foreign_feature': nbtlib.Byte(1), 'upcoming_creator_features': nbtlib.Byte(0)})},
                      root_name='Level')
    raw = encode_root(data)
    return struct.pack('<II', 10, len(raw)) + raw


class WorldExperimentTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name); self.output = self.root / 'run'; self.live = self.root / 'live'
        self.world = self.output / 'saved-world-engine/worlds/Saved World QA'
        self.snapshot = self.output / 'production-snapshot'
        self.raw = level()
        for directory in [self.world, self.snapshot, self.live]:
            directory.mkdir(parents=True); (directory / 'level.dat').write_bytes(self.raw)
        before = self.output / 'production-before'; before.mkdir()
        (before / 'backup-receipt.json').write_text(json.dumps({'level_dat_sha256': m.digest(self.raw)}))
        self.addCleanup(patch.stopall)
        patch.multiple(c, R=self.output, W=self.live, CONFIG={}).start()
        patch.object(m, 'required', return_value=FLAGS).start()

    def rehearsal(self):
        proof = m.prepare(self.world); raw = (self.world / 'level.dat').read_bytes()
        observed = m.observe(raw, FLAGS); digest = m.digest(raw)
        runs = [{'phase': phase, 'ok': True, 'level_input_sha256': digest,
                 'level_output_sha256': digest, 'world_experiments': observed}
                for phase in ['first', 'restart']]
        return {'world_experiments': proof, 'runs': runs}

    def live_boundary(self):
        patch.object(c, 'assert_lease', return_value=None).start()
        patch.object(c, 'summary', return_value={'status': 'STOPPED'}).start()
        patch.object(c, 'atomic', side_effect=lambda path, value:
                     Path(path).write_text(json.dumps(value))).start()

    def test_transition_preserves_root_name_opaque_bytes_other_flags_and_all_unrelated_tags(self):
        after, proof = m.transition(self.raw, FLAGS)
        before_tag, after_tag = m.metadata(self.raw), m.metadata(after)
        self.assertEqual(set(proof['changed_flags']), set(FLAGS) | set(m.HISTORY_FLAGS))
        after_tag['experiments'] = before_tag['experiments']
        self.assertEqual(encode_root(after_tag), self.raw[8:])
        self.assertEqual(m.metadata(after)['experiments']['gametest'], 0)
        self.assertEqual(m.metadata(after)['experiments']['foreign_feature'], 1)
        repeated, repeated_proof = m.transition(after, FLAGS)
        self.assertEqual(repeated, after); self.assertEqual(repeated_proof['changed_flags'], {})

    def test_copy_then_same_copy_restart_and_matching_adoption_keep_original_backup_and_db(self):
        report = self.rehearsal(); self.assertEqual(m.verify_rehearsal(report), report['world_experiments'])
        self.assertEqual((self.live / 'level.dat').read_bytes(), self.raw)
        (self.live / 'level.dat_old').write_bytes(b'existing older metadata')
        (self.live / 'db').mkdir(); (self.live / 'db/player').write_bytes(b'opaque player bytes')
        self.live_boundary(); proof = m.adopt(report)
        self.assertTrue(m.adoption_recorded())
        self.assertEqual((self.live / 'level.dat').read_bytes(), (self.world / 'level.dat').read_bytes())
        self.assertEqual((self.snapshot / 'level.dat').read_bytes(), self.raw)
        self.assertEqual((self.live / 'level.dat_old').read_bytes(), b'existing older metadata')
        self.assertEqual((self.live / 'db/player').read_bytes(), b'opaque player bytes')
        self.assertEqual(c.read(self.output / 'deployment-result.json')['world_experiments'], proof)

    def test_wrong_restart_metadata_or_missing_flags_cannot_admit(self):
        for fault in ['chain', 'flags', 'failed', 'missing_hash']:
            with self.subTest(fault=fault):
                report = self.rehearsal()
                if fault == 'chain': report['runs'][1]['level_input_sha256'] = '0' * 64
                elif fault == 'flags': report['runs'][1]['world_experiments']['upcoming_creator_features'] = 0
                elif fault == 'failed': report['runs'][0]['ok'] = False
                else: report['runs'][0].pop('level_output_sha256')
                with self.assertRaisesRegex(ValueError, 'Native runs'): m.verify_rehearsal(report)
                (self.world / 'level.dat').write_bytes(self.raw)

    def test_changed_live_metadata_is_rejected_before_any_write(self):
        report = self.rehearsal(); self.live_boundary()
        changed = self.raw.replace(b'Existing Better Biomes', b'Different world bytes')
        (self.live / 'level.dat').write_bytes(changed)
        with patch.object(m, 'write_metadata') as write, self.assertRaisesRegex(ValueError, 'changed after'):
            m.adopt(report)
        write.assert_not_called(); self.assertFalse(m.adoption_recorded())

    def test_adoption_failure_persists_stop_only_marker_before_attempted_write(self):
        report = self.rehearsal(); self.live_boundary()
        with patch.object(m, 'write_metadata', side_effect=OSError('injected disk failure')):
            with self.assertRaisesRegex(OSError, 'injected'): m.adopt(report)
        self.assertTrue(m.adoption_recorded())
        self.assertEqual((self.live / 'level.dat').read_bytes(), self.raw)
        self.assertEqual((self.snapshot / 'level.dat').read_bytes(), self.raw)

    def test_existing_flags_need_no_metadata_write_but_still_fence_runtime_adoption(self):
        self.assertFalse(m.satisfied())
        enabled, _ = m.transition(self.raw, FLAGS)
        for directory in [self.snapshot, self.world, self.live]: (directory / 'level.dat').write_bytes(enabled)
        (self.output / 'production-before/backup-receipt.json').write_text(json.dumps({'level_dat_sha256': m.digest(enabled)}))
        self.assertTrue(m.satisfied()); report = self.rehearsal(); self.live_boundary()
        with patch.object(m, 'write_metadata') as write: m.adopt(report)
        write.assert_not_called(); self.assertTrue(m.adoption_recorded())

    def test_malformed_metadata_and_unreviewed_flag_types_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'header'): m.transition(self.raw[:-1], FLAGS)
        tag = m.metadata(self.raw); tag['experiments']['upcoming_creator_features'] = nbtlib.Int(0)
        body = encode_root(tag); raw = struct.pack('<II', 10, len(body)) + body
        with self.assertRaisesRegex(ValueError, 'representation'): m.transition(raw, FLAGS)

    def test_world_preparation_cannot_follow_a_metadata_link_outside_the_qa_copy(self):
        path = self.world / 'level.dat'; path.unlink(); path.symlink_to(self.live / 'level.dat')
        with self.assertRaisesRegex(ValueError, 'confined'): m.prepare(self.world)
        self.assertEqual((self.live / 'level.dat').read_bytes(), self.raw)

    def test_fresh_generation_with_required_flags_is_explicitly_refused_before_engine_setup(self):
        from family_update import rehearse_saved_world as rehearsal
        with patch.object(rehearsal, 'setup_engine') as setup:
            with self.assertRaisesRegex(ValueError, 'fresh-world creation'):
                rehearsal.rehearse_fresh_world(self.output / 'engine', 23910, {}, {})
            setup.assert_not_called()


class SourceRequirementTests(unittest.TestCase):
    def test_only_exact_reviewed_selection_supplies_flags_not_runner_configuration(self):
        from family_update import current_author_validation as admission
        with patch.multiple(c, EXTENSION=Path('/reviewed-source'), CONFIG={'required_experiments': {'invented': True}}), \
             patch.object(admission, 'curated_selected', return_value=True), \
             patch.object(admission, 'current_selection', return_value={'required_experiments': FLAGS}) as selected:
            self.assertEqual(m.required(), FLAGS); selected.assert_called_once_with()
            for invalid in [{'gametest': False}, {'experiments_ever_used': True}, {'bad-name': True}, []]:
                selected.return_value = {'required_experiments': invalid}
                with self.assertRaises(ValueError): m.required()


if __name__ == '__main__': unittest.main()
