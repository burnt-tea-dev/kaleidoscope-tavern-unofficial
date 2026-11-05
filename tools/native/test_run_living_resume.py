"""Resume real files without replacing the saved fixture; mock only BDS launch."""
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import run_living_effects as runner


class ResumeSavedQA(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.source, self.work, self.engine = root/'source', root/'qa', root/'engine'
        self.world = self.work/'worlds/living-effect-qa'
        self.host = self.world/'behavior_packs/tavern'
        self.engine.mkdir()
        self.source.mkdir()
        self.canonical = {'BP': {'scripts/main.js': b'// canonical entry\n'}, 'RP': {'manifest.json': b'{"resource":true}\n'}}
        for kind, files in self.canonical.items():
            target = self.world/('behavior_packs' if kind == 'BP' else 'resource_packs')/'tavern'
            for name, content in files.items():
                src = self.source/'runtime'/kind/name
                src.parent.mkdir(parents=True, exist_ok=True)
                src.write_bytes(content)
                dst = target/name
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(content)
        with (self.host/'scripts/main.js').open('ab') as out:
            out.write(b"\n// Disposable native observer; not release content.\nimport './living-effects-probe.js';\n")
        (self.host/'scripts/living-effects-probe.js').write_bytes(b'old observer')
        self.db = self.world/'db/CURRENT'
        self.db.parent.mkdir()
        self.db.write_bytes(b'original saved-world data')
        for name in ('first.log', 'restart.log'):
            (self.work/name).write_text('original '+name)
        self.probe = root/'new-probe.js'
        self.probe.write_bytes(b'new saved-state observer')
        self.identity = {'executable_sha256': 'selected engine'}
        baseline = {'repository': 'selected source', 'version': [0, 6, 203], 'source_trees': {kind: runner.fingerprint(self.source/'runtime'/kind)[0] for kind in ('BP', 'RP')}}
        (self.source/'baseline.json').write_text(json.dumps(baseline))
        original = {'engine': self.identity, 'sources': {'tavern': baseline},
                    'test_only_overlays': {'scripts/main.js': 'declared append', 'scripts/living-effects-probe.js': hashlib.sha256(b'old observer').hexdigest()},
                    'reports': [{'normal_stop': True, 'player_connections': 0, 'errors': [], 'ok': False}]}
        self.original = json.dumps(original).encode()
        (self.work/'native-living-report.json').write_bytes(self.original)
        self.args = SimpleNamespace(phases=['restart'], probe=self.probe, timeout_seconds=180)

    def test_resume_runs_only_restart_and_preserves_original_world_and_evidence(self):
        result = {'phase': 'restart', 'ok': True}
        with patch.object(runner, 'ROOT', self.source), patch.object(runner, 'run_phase', return_value=result) as launch:
            runner.resume_restart(self.args, self.engine, self.work, None, self.identity)
        launch.assert_called_once_with(self.engine, self.work, 'restart', 180, 'restart-resume.log')
        self.assertEqual((self.work/'native-living-report.json').read_bytes(), self.original)
        for name in ('first.log', 'restart.log'):
            self.assertEqual((self.work/name).read_text(), 'original '+name)
        self.assertEqual(self.db.read_bytes(), b'original saved-world data')
        self.assertEqual((self.host/'scripts/living-effects-probe.js').read_bytes(), self.probe.read_bytes())
        report = json.loads((self.work/'native-living-resume-report.json').read_text())
        self.assertEqual(report['reports'], [result])
        self.assertEqual(report['original_report'], 'native-living-report.json')

    def test_changed_runtime_is_rejected_before_launch_or_observer_replacement(self):
        (self.host/'scripts/main.js').write_bytes(b'accidentally changed runtime')
        with patch.object(runner, 'ROOT', self.source), patch.object(runner, 'run_phase') as launch:
            with self.assertRaisesRegex(AssertionError, 'Resume runtime differs'):
                runner.resume_restart(self.args, self.engine, self.work, None, self.identity)
        launch.assert_not_called()
        self.assertEqual((self.host/'scripts/living-effects-probe.js').read_bytes(), b'old observer')

    def test_resume_rejects_replaying_first(self):
        self.args.phases = ['first', 'restart']
        with self.assertRaisesRegex(AssertionError, 'only permits'):
            runner.resume_restart(self.args, self.engine, self.work, None, self.identity)


if __name__ == '__main__':
    unittest.main()
