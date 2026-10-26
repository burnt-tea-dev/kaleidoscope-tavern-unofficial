"""Publication authorization and source-document boundaries; no remote writes."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

import release_publication
from release_publication import publication_enabled, public_notes, public_notes_text, validate_request_identity


class ReleasePublication(unittest.TestCase):
    def identity_request(self):
        return {'version': '1.2.3', 'tag': 'v1.2.3', 'prerelease': False,
                'title': 'Tavern 1.2.3: reviewed source', 'publication_request': False}

    def test_current_identity_checks_do_not_enable_publication(self):
        request = self.identity_request()
        validate_request_identity(request, {'version': '1.2.3'})
        self.assertFalse(publication_enabled(request, 'push'))
        request.update(prerelease=True, tag='v1.2.3-beta.1')
        validate_request_identity(request, {'version': '1.2.3'})

    def test_stale_request_version_tag_and_title_are_rejected(self):
        for key, value in (('version', '1.2.2'), ('tag', 'v1.2.2'),
                           ('title', 'Tavern 1.2.2: prior repair'),
                           ('title', 'Tavern 1.2.30: different release'),
                           ('title', 'Tavern 1.2.3\nother line'),
                           ('title', False), ('prerelease', 'false')):
            request = self.identity_request()
            request[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validate_request_identity(request, {'version': '1.2.3'})

    def test_disabled_request_rejects_stale_title_before_writing_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / '.github').mkdir()
            request = self.identity_request()
            request['title'] = 'Tavern 1.2.2: stale title'
            (root / '.github/release-request.json').write_text(json.dumps(request))
            (root / 'release.json').write_text(json.dumps({'version': '1.2.3'}))
            output = root / 'github-output'
            with patch.object(release_publication, 'ROOT', root), \
                    patch('sys.argv', ['release_publication.py', '--event', 'push']), \
                    patch.dict(release_publication.os.environ, {'GITHUB_OUTPUT': str(output)}):
                with self.assertRaisesRegex(ValueError, 'title'):
                    release_publication.main()
            self.assertFalse(output.exists())

    def test_inline_notes_are_short_public_text_and_preserve_path_mode(self):
        self.assertEqual(public_notes_text(Path('.'), {'public_notes_inline': 'Current repair.\n\nClient confirmation pending.'}),
                         'Current repair.\n\nClient confirmation pending.\n')
        for text in ['', '/root/private/source', 'file:///world', '\x00', 'x' * 4097, False]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                public_notes_text(Path('.'), {'public_notes_inline': text})

    def test_new_request_requires_explicit_manual_publication(self):
        request = {'publication_request': False}
        self.assertFalse(publication_enabled(request, 'push'))
        self.assertFalse(publication_enabled(request, 'workflow_dispatch'))
        self.assertTrue(publication_enabled(request, 'workflow_dispatch', True))
        self.assertFalse(publication_enabled(request, 'pull_request', True))

    def test_old_requests_keep_automatic_push_behavior(self):
        self.assertTrue(publication_enabled({}, 'push'))
        self.assertFalse(publication_enabled({}, 'workflow_dispatch'))
        self.assertTrue(publication_enabled({}, 'workflow_dispatch', True))

    def test_strings_cannot_turn_false_into_publication(self):
        with self.assertRaises(ValueError):
            publication_enabled({'publication_request': 'false'}, 'push')
        with self.assertRaises(ValueError):
            publication_enabled({'publication_request': False}, 'workflow_dispatch', 'false')

    def test_optional_notes_preserve_original_and_reject_path_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'docs').mkdir()
            original = root / 'docs/RELEASE-NOTES-0.6.147.md'
            original.write_text('Immutable diagnostic draft evidence')
            public = root / 'docs/PUBLICATION-T147.md'
            public.write_text('Current bounded public release explanation')
            self.assertIsNone(public_notes(root, {}))
            self.assertEqual(public_notes(root, {'public_notes_path': 'docs/PUBLICATION-T147.md'}), public)
            changelog = root / 'CHANGELOG.md'
            changelog.write_text('Current release entry')
            self.assertEqual(public_notes(root, {'public_notes_path': 'CHANGELOG.md'}), changelog)
            self.assertEqual(original.read_text(), 'Immutable diagnostic draft evidence')
            for name in ('../outside.md', 'docs/../outside.md', str(public), 'runtime/RP/notes.md',
                         'docs\\PUBLICATION-T147.md', 'docs/missing.md'):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    public_notes(root, {'public_notes_path': name})
            (root / 'docs/link.md').symlink_to(public)
            with self.assertRaises(ValueError):
                public_notes(root, {'public_notes_path': 'docs/link.md'})


if __name__ == '__main__':
    unittest.main()
