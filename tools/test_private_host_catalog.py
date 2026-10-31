"""Actual Git-backed catalog loading; fixtures contain no private inputs."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import stable_host_profiles as stable


class PrivateHostCatalog(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.addCleanup(stable.bind_source_catalog, None)
        self.root = Path(self.temporary.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Catalog Test')
        self.git('config', 'user.email', 'catalog@example.invalid')
        public = copy.deepcopy(stable._PUBLIC_CATALOG)
        selection = public[stable.CURATED_KEY]
        old_station = selection['selection']['value']['station_profile']
        self.station = 'fixture-private-station'
        selection['profile'] = selection['selection']['value']['profile'] = 'fixture-owner'
        selection['selection']['value']['station_profile'] = self.station
        self.catalog = {'schema': 1, 'profiles': {self.station: public['profiles'][old_station]},
                        stable.CURATED_KEY: selection}
        self.path = self.root / 'private-catalog.json'
        self.write_catalog()
        self.commit()

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.root, stderr=subprocess.PIPE)

    def write_catalog(self):
        raw = (json.dumps(self.catalog, indent=2) + '\n').encode()
        self.path.write_bytes(raw)
        self.baseline = {'host_catalog': {'path': self.path.name, 'sha256': hashlib.sha256(raw).hexdigest()}}
        self.write_baseline()

    def write_baseline(self):
        (self.root / 'baseline.json').write_text(json.dumps(self.baseline, indent=2) + '\n')

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'Reviewed catalog fixture')

    def test_exact_committed_catalog_binds_existing_validator_references_and_resets(self):
        catalog_reference, profiles_reference = stable.CATALOG, stable.PROFILES
        binding = stable.bind_source_catalog(self.root)
        self.assertEqual(binding, self.baseline['host_catalog'])
        self.assertIs(stable.CATALOG, catalog_reference)
        self.assertIs(stable.PROFILES, profiles_reference)
        self.assertEqual(stable.curated_profile()['profile'], 'fixture-owner')
        self.assertIn(self.station, profiles_reference)
        stable.bind_source_catalog(None)
        self.assertNotIn(self.station, profiles_reference)
        self.assertEqual(stable.CATALOG, stable._PUBLIC_CATALOG)

    def test_dirty_catalog_is_rejected_before_changing_active_profiles(self):
        before = copy.deepcopy(stable.CATALOG)
        self.path.write_bytes(self.path.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'committed together'):
            stable.bind_source_catalog(self.root)
        self.assertEqual(stable.CATALOG, before)

    def test_committed_wrong_digest_is_rejected(self):
        self.baseline['host_catalog']['sha256'] = '0' * 64
        self.write_baseline()
        self.commit()
        with self.assertRaisesRegex(ValueError, 'digest differs'):
            stable.bind_source_catalog(self.root)

    def test_owner_cannot_replace_public_declarations(self):
        name = next(iter(stable._PUBLIC_CATALOG['profiles']))
        self.catalog['profiles'][name] = {'fixture': 'unreviewed replacement'}
        self.write_catalog()
        self.commit()
        with self.assertRaisesRegex(ValueError, 'cannot replace public profiles'):
            stable.bind_source_catalog(self.root)

    def test_catalog_path_must_stay_within_its_source(self):
        self.baseline['host_catalog']['path'] = '../outside.json'
        self.write_baseline()
        self.commit()
        with self.assertRaisesRegex(ValueError, 'path is unsafe'):
            stable.bind_source_catalog(self.root)


if __name__ == '__main__':
    unittest.main()
