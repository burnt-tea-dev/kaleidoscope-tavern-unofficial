"""Negative controls call the actual current resource validator."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from cultivation_source_contract import ROOT, BLOCKS, LOOT, check_resources


class CurrentCultivationResources(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in [*(f'runtime/BP/blocks/{name}.json' for name in BLOCKS), 'runtime/BP/' + LOOT]:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)

    def edit(self, name, mutate):
        path = self.root / name
        data = json.loads(path.read_text())
        mutate(data)
        path.write_text(json.dumps(data))

    def test_current_resources(self):
        check_resources(self.root)

    def test_block_item_and_tool_predicates_are_rejected(self):
        for change in (lambda pool: pool['entries'][0].update(name='kaleidoscope_tavern:wild_grapevine'),
                       lambda pool: pool.update(conditions=[{'condition': 'match_tool'}])):
            with self.subTest(change=change):
                path = self.root / 'runtime/BP' / LOOT
                shutil.copyfile(ROOT / 'runtime/BP' / LOOT, path)
                self.edit('runtime/BP/' + LOOT, lambda data: change(data['pools'][0]))
                with self.assertRaises(AssertionError):
                    check_resources(self.root)

    def test_disconnected_or_duplicate_loot_is_rejected(self):
        name = 'runtime/BP/blocks/wild_grapevine.json'
        for change in (lambda comp: comp.pop('minecraft:loot'),
                       lambda comp: comp.update({'kaleidoscope_tavern:natural_break': {}})):
            with self.subTest(change=change):
                shutil.copyfile(ROOT / name, self.root / name)
                self.edit(name, lambda data: change(data['minecraft:block']['components']))
                with self.assertRaises(AssertionError):
                    check_resources(self.root)


if __name__ == '__main__':
    unittest.main()
