"""Exercise real baseline/geometry boundaries without site or user packages.

-I -S removes installed dependencies rather than mocking Pillow imports. The
release gate must still enforce a clean checkout; dirty development work is
expected to reach and fail that real boundary, not an import or identity error.
"""
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = """
import importlib.util, runpy, sys
from pathlib import Path
assert sys.flags.isolated and sys.flags.no_site
assert importlib.util.find_spec('PIL') is None, 'Pillow unexpectedly available'
tools = Path(sys.argv.pop(1))
sys.path.insert(0, str(tools))
script = tools / sys.argv.pop(1)
sys.argv[0] = str(script)
runpy.run_path(str(script), run_name='__main__')
"""


class MinimalBaselineDependencies(unittest.TestCase):
    def run_isolated(self, script, *args):
        return subprocess.run([sys.executable, '-I', '-S', '-B', '-c', BOOTSTRAP,
                               str(ROOT / 'tools'), script, *args], cwd=ROOT,
                              capture_output=True, text=True)

    def test_real_frozen_identity_without_pillow(self):
        result = self.run_isolated('baseline_gate.py', 'check', '--identity')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Canonical baseline verified:', result.stdout)

    def test_real_release_gate_without_pillow_preserves_clean_commit_requirement(self):
        dirty = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'],
                                        cwd=ROOT, text=True).strip()
        result = self.run_isolated('baseline_gate.py', 'check', '--release')
        if dirty:
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stderr.strip(), 'BASELINE: commit reviewed changes before release packaging')
        else:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('Canonical baseline verified:', result.stdout)

    def test_full_current_geometry_contract_runs_without_image_packages(self):
        result = self.run_isolated('machine_ingredient_geometry.py')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"card_ids": 22', result.stdout)
        self.assertIn('"native_frame_culling_verified": false', result.stdout)

    def test_chalkboard_contract_runs_without_image_packages(self):
        result = self.run_isolated('chalkboard_geometry.py')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"slices": 8', result.stdout)
        self.assertIn('"bottom_v_visual_proof": false', result.stdout)

    def test_shared_bindings_stay_pure_and_pixel_generation_still_requires_pillow(self):
        script = """
import importlib.util, sys
assert sys.flags.isolated and sys.flags.no_site
assert importlib.util.find_spec('PIL') is None
sys.path.insert(0, sys.argv[1])
import machine_ingredient_animation as animation
assert len(animation.bindings()) == 24
assert 'PIL' not in sys.modules and 'refresh_visual_compat' not in sys.modules
try:
    animation.ice_grape_frames()
except ModuleNotFoundError as error:
    assert error.name == 'PIL'
else:
    raise AssertionError('Pixel generation silently bypassed its image dependency')
"""
        result = subprocess.run([sys.executable, '-I', '-S', '-B', '-c', script,
                                 str(ROOT / 'tools')], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
