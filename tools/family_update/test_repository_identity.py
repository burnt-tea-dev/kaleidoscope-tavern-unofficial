"""A same-ID organization transfer must not admit a fork or private exposure."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from family_update import repository_identity as m


class RepositoryTransferTests(unittest.TestCase):
    def record(self, name='senluo-family-integration-private'):
        t = m.target('casama233/' + name)
        return {'full_name': t['repository'], 'id': t['repository_id'],
                'private': t['private'], 'owner': t['owner']}

    def test_all_four_logical_keys_bind_to_original_id_and_current_owner(self):
        for name in m.TARGETS:
            row = self.record(name)
            self.assertEqual(m.verify_remote(row, 'casama233/' + name)['repository'], row['full_name'])
            self.assertEqual(m.current_name(row['full_name']), row['full_name'])

    def test_name_id_visibility_and_owner_are_independent_requirements(self):
        for key, value in [('full_name', 'casama233/senluo-family-integration-private'),
                           ('id', 1), ('id', True), ('private', False),
                           ('owner', {**m.OWNER, 'id': 1}),
                           ('owner', {**m.OWNER, 'type': 'User'})]:
            row = {**self.record(), key: value}
            with self.subTest(key=key, value=value), self.assertRaises(AssertionError):
                m.verify_remote(row, 'casama233/senluo-family-integration-private')
        with self.assertRaises(AssertionError):
            m.target('unreviewed/kaleidoscope-tavern-unofficial')

    def test_preserved_parent_event_allows_only_reviewed_cross_repo_source_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            event = Path(tmp) / 'event.json'
            parent = self.record('kaleidoscope-tavern-unofficial')
            event.write_text(json.dumps({'repository': parent}))
            env = {'GITHUB_ACTIONS': 'true', 'GITHUB_REPOSITORY_OWNER': m.OWNER['login'],
                   'GITHUB_REPOSITORY_OWNER_ID': str(m.OWNER['id']), 'GITHUB_EVENT_PATH': str(event),
                   'GITHUB_REPOSITORY': m.current_name('casama233/kaleidoscope-world-liquor-unofficial'),
                   'GITHUB_REPOSITORY_ID': '1385218112', 'SENLUO_SOURCE_GATE': '1'}
            m.verify_ci('casama233/kaleidoscope-world-liquor-unofficial', env)
            with self.assertRaises(AssertionError):
                m.verify_ci('casama233/kaleidoscope-world-liquor-unofficial', {**env, 'SENLUO_SOURCE_GATE': '0'})
            for change in [{'id': 1}, {'full_name': 'fork/kaleidoscope-tavern-unofficial'},
                           {'private': True}, {'owner': {**m.OWNER, 'id': 1}}]:
                event.write_text(json.dumps({'repository': {**parent, **change}}))
                with self.subTest(change=change), self.assertRaises(AssertionError):
                    m.verify_ci('casama233/kaleidoscope-world-liquor-unofficial', env)


if __name__ == '__main__':
    unittest.main()
