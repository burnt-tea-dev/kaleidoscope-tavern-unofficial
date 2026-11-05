"""A fixed completed batch can remain on an older merged source."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from family_update.common import require_merged_source


class SelectedSource(unittest.TestCase):
    def test_detached_merged_source_is_usable_but_unmerged_work_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);remote=root/'origin';source=root/'source'
            subprocess.run(['git','init','--quiet','--bare','--initial-branch=main',str(remote)],check=True)
            subprocess.run(['git','init','--quiet','--initial-branch=main',str(source)],check=True)
            def git(*args):
                return subprocess.check_output(['git','-C',str(source),'-c','user.name=Fixture',
                    '-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false',*args],
                    text=True,stderr=subprocess.PIPE).strip()
            git('remote','add','origin',str(remote))
            (source/'runtime.txt').write_text('selected runtime')
            git('add','.');git('commit','--quiet','-m','Selected source')
            selected=git('rev-parse','HEAD');git('push','--quiet','origin','main')
            (source/'later.txt').write_text('next batch')
            git('add','.');git('commit','--quiet','-m','Later source')
            latest=git('rev-parse','HEAD');git('push','--quiet','origin','main')
            git('checkout','--quiet','--detach',selected)
            require_merged_source(source,selected,latest)
            self.assertEqual(git('rev-parse','HEAD'),selected)
            (source/'local.txt').write_text('unreviewed work')
            git('add','.');git('commit','--quiet','-m','Unmerged local source')
            with self.assertRaisesRegex(AssertionError,'not merged'):
                require_merged_source(source,git('rev-parse','HEAD'),latest)


if __name__ == '__main__':
    unittest.main()
