"""P51-P54 retained identities and assembly coverage without copied suites."""
import copy, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from retained_host_profiles import P51_PROFILES, PROFILES, retained_host_source

class LaterRetainedHostTests(unittest.TestCase):

    def _assert_map(self, source_version):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'spec'
            p.write_bytes(b'synthetic')
            config = {'repository': 'local/senluo-amw-cuisine', 'version': source_version, 'retained_host_profiles': copy.deepcopy(P51_PROFILES)}
            for kind, profile in P51_PROFILES.items():
                spec = {'kind': kind, 'owner_version': profile['owner_version']}
                with patch('retained_host_profiles.hashlib.sha256') as h:
                    h.return_value.hexdigest.return_value = profile['spec_sha256']
                    self.assertEqual(retained_host_source(config, spec, p), profile)
                with self.assertRaises(ValueError):
                    retained_host_source(config, spec, p)
            for field in ('repository', 'version', 'retained_host_profiles'):
                bad = copy.deepcopy(config)
                bad[field] = {'repository': 'foreign', 'version': [1, 0, 55], 'retained_host_profiles': {}}[field]
                with self.assertRaisesRegex(ValueError, 'unsupported retained host source profile'):
                    retained_host_source(bad, spec, p)

    def test_unlisted_owner_versions_never_enter_retention(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'spec'
            p.write_bytes(b'synthetic')
            kind = next(iter(P51_PROFILES))
            profile = P51_PROFILES[kind]
            spec = {'kind': kind, 'owner_version': profile['owner_version']}
            for version in ([1, 0, 55], [1, 0, 99], [1, 1, 54], [2, 0, 54], [1, 0, 54, 0], '1.0.54', None):
                config = {'repository': 'local/senluo-amw-cuisine', 'version': version, 'retained_host_profiles': copy.deepcopy(P51_PROFILES)}
                with self.subTest(version=version), patch('retained_host_profiles.hashlib.sha256') as h:
                    h.return_value.hexdigest.return_value = profile['spec_sha256']
                    with self.assertRaisesRegex(ValueError, 'unsupported retained host source profile'):
                        retained_host_source(config, spec, p)

    def _assert_assembly(self, source_version):
        import contextlib
        import hashlib
        import io
        import json
        import zipfile
        from family_bundle import assemble
        for kind, profile in P51_PROFILES.items():
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                repo = root / 'owned'
                config = {'repository': 'local/senluo-amw-cuisine', 'version': source_version, 'runtime': {'BP': 'runtime/BP', 'RP': 'runtime/RP'}, 'source_trees': {}, 'packs': {}, 'retained_host_profiles': copy.deepcopy(P51_PROFILES)}
                for side, module in [('BP', 'data'), ('RP', 'resources')]:
                    pack = repo / 'runtime' / side
                    pack.mkdir(parents=True)
                    uid = 'owned-' + side
                    config['packs'][side] = {'uuid': uid}
                    (pack / 'manifest.json').write_text(json.dumps({'header': {'uuid': uid, 'version': source_version}, 'modules': [{'type': module}]}))
                (repo / 'baseline.json').write_text(json.dumps(config))
                declarations = repo / 'runtime/BP/host-extensions'
                declarations.mkdir()
                spec = {'id': 'synthetic-' + kind, 'kind': kind, 'owner_version': profile['owner_version'], 'host_uuid': 'author-RP' if kind.startswith('chinesefood') else 'author-BP', 'behavior_uuid': 'author-BP', 'resource_uuid': 'author-RP'}
                (declarations / 'synthetic.json').write_text(json.dumps(spec))
                archive = root / 'author.mcaddon'
                author = []
                with zipfile.ZipFile(archive, 'w') as stream:
                    for side, module in [('BP', 'data'), ('RP', 'resources')]:
                        uid = 'author-' + side
                        author.append({'uuid': uid, 'version': [1, 0, 1]})
                        stream.writestr(side + '/manifest.json', json.dumps({'header': author[-1], 'modules': [{'type': module}]}))
                lock = {'owned': [], 'upstream': [{'name': 'synthetic-author', 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'project_id': 1, 'file_id': 1, 'packs': author}], 'order': {'behavior': ['author-BP'], 'resource': ['author-RP']}}
                paired = kind in PROFILES
                module = ('doll_renderer_extension.apply_renderer_extension' if kind.startswith('chinesefood') else 'nether_placeable_extension.apply_nether_extension') if paired else 'family_bundle.apply_host_extension'

                def apply(spec, *args):
                    self.assertEqual(spec['owner_version'], profile['owner_version'])
                    if paired:
                        self.assertEqual(args[-1], profile['owner_version'])
                    else:
                        self.assertEqual(len(args), 3)
                    return {'id': spec['id'], 'owner_version': profile['owner_version']}
                with patch('family_bundle.retained_host_source', return_value=copy.deepcopy(profile)), patch(module, side_effect=apply), patch('family_bundle.subprocess.check_output', return_value='source-commit'), contextlib.redirect_stdout(io.StringIO()):
                    receipt = assemble(lock, {}, [archive], root / 'candidate', working=True, extensions=[repo])
                extended = [row for row in receipt['packs'] if row['uuid'].startswith('author-')]
                extended = [row for row in extended if row['source'].get('reviewed_extensions')]
                self.assertEqual(len(extended), 2 if paired else 1)
                for row in extended:
                    proof = row['source']['reviewed_extensions'][0]
                    self.assertEqual(proof['owner_version'], profile['owner_version'])
                    self.assertEqual(proof['source_package_version'], source_version)
                    self.assertEqual(proof['retained_host_profile'], profile)
                    if profile['owner_version'] == [1, 0, 50]:
                        self.assertEqual(proof['retained_host_profile']['source_scope'], 'reviewed_local_candidate')
                    self.assertNotIn('retained_renderer_profile', proof)
                    self.assertEqual(row['version'], [1, 0, 1])

    def test_reviewed_owner_maps_and_rejected_drift(self):
        for patch_version in (51, 52, 53, 54):
            source_version = [1, 0, patch_version]
            with self.subTest(version=source_version):
                self._assert_map(source_version)

    def test_actual_assembly_preserves_each_reviewed_owner(self):
        for patch_version in (51, 52, 53, 54):
            source_version = [1, 0, patch_version]
            with self.subTest(version=source_version):
                self._assert_assembly(source_version)
if __name__ == '__main__':
    unittest.main()
