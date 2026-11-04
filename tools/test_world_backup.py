import tempfile
import os
import shutil
import unittest
from pathlib import Path

from family_guard import atomic, read
from world_backup import adopt, capture, register_alias


class WorldBackupTests(unittest.TestCase):
    def test_verified_replacement_retires_old_backup_and_preserves_original(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            world = root / 'original'
            (world / 'db').mkdir(parents=True)
            (world / 'level.dat').write_bytes(b'level')
            (world / 'db/CURRENT').write_bytes(b'MANIFEST-1')
            state = root / 'backups.json'
            atomic(state, {'backup_roots': [str(root)], 'protected_worlds': [str(world)]})
            for name in ('old', 'new'):
                capture(world, root / name, root / (name + '.json'))
                adopt(state, root / name, root / (name + '.json'))
                if name == 'old':
                    shutil.copytree(root / name, root / 'alias', copy_function=os.link)
                    register_alias(state, root / name, root / 'alias')
            self.assertFalse((root / 'old').exists())
            self.assertFalse((root / 'alias').exists())
            self.assertEqual((root / 'new/level.dat').read_bytes(), b'level')
            self.assertTrue((world / 'db/CURRENT').is_file())
            self.assertEqual(read(state)['pending_retirement'], [])
            with self.assertRaisesRegex(ValueError, 'protected'):
                adopt(state, root / 'new', root / 'new.json', [world])

    def test_changed_replacement_keeps_previous_backup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            world = root / 'original'
            (world / 'db').mkdir(parents=True)
            (world / 'level.dat').write_bytes(b'level')
            (world / 'db/CURRENT').write_bytes(b'manifest')
            state = root / 'backups.json'
            atomic(state, {'backup_roots': [str(root)], 'protected_worlds': [str(world)]})
            capture(world, root / 'old', root / 'old.json')
            adopt(state, root / 'old', root / 'old.json')
            capture(world, root / 'new', root / 'new.json')
            (root / 'new/level.dat').write_bytes(b'corrupt')
            with self.assertRaises(ValueError):
                adopt(state, root / 'new', root / 'new.json')
            self.assertTrue((root / 'old/level.dat').is_file())
            self.assertEqual(read(state)['current']['backup'], str(root / 'old'))


if __name__ == '__main__':
    unittest.main()
