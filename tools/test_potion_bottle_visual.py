#!/usr/bin/env python3
"""Reject real block regressions after retiring the old inverse-source guard."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from build_potion_bottle_visual import ROOT, MODEL, TEXTURE, outputs
from check_potion_bottle_visual import check


class PotionBlockContract(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for name in set(outputs())|{MODEL,TEXTURE,str(Path(TEXTURE).with_suffix('.texture_set.json'))}:
            target=self.root/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/name,target)
        self.block=self.root/'runtime/BP/blocks/potion_bottle.json'

    def rejects(self, mutate):
        value=json.loads(self.block.read_text());mutate(value['minecraft:block'])
        self.block.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
        with self.assertRaisesRegex(AssertionError,'Stale generated potion resource'):
            check(root=self.root)

    def test_natural_break_cannot_disappear(self):
        self.rejects(lambda block:block['components'].pop('kaleidoscope_tavern:natural_break'))

    def test_wrong_glass_material_is_rejected(self):
        self.rejects(lambda block:block['components']['minecraft:material_instances']['*'].update(texture='kt_wrong'))

    def test_placement_rotation_cannot_override_the_liquid_route(self):
        self.rejects(lambda block:block['permutations'][1]['components'].update({'minecraft:geometry':{'identifier':'geometry.wrong'}}))


if __name__=='__main__':unittest.main()
