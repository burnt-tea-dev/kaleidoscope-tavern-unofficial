"""Selected native fields and the exported incense countdown, not BDS evidence."""
import json
import unittest
from build_incense_native_entities import SOURCE, ROOT, NAMES, GROUP, EVENT, outputs
from family_bundle import read_definition


class NativeIncenseEntities(unittest.TestCase):
    def test_exports_are_generated_from_the_selected_sources(self):
        for path, expected in outputs().items():
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertEqual(path.read_text(), expected)

    def test_native_actors_are_retained_and_only_incense_gets_the_short_conversion(self):
        for name in NAMES:
            with self.subTest(entity=name):
                source = read_definition(SOURCE / (name + '.json'), jsonc=True)
                exported = json.loads((ROOT / 'runtime/BP/entities' / (name + '.json')).read_text())
                actor = exported['minecraft:entity']
                group = actor['component_groups'].pop(GROUP)
                actor['events'].pop(EVENT)
                # Whole-document equality includes the normal cure event,
                # profession/trade groups, spawning, equipment and animations.
                self.assertEqual(exported, source)
                transformation = group['minecraft:transformation']
                delay = transformation.pop('delay')
                self.assertEqual(delay['value'], 3)
                self.assertNotIn('range_min', delay)
                self.assertNotIn('range_max', delay)
                retained = source['minecraft:entity']['component_groups']['to_villager']
                expected_delay = dict(retained['minecraft:transformation']['delay'])
                for key in ('value', 'range_min', 'range_max'):
                    delay.pop(key, None)
                    expected_delay.pop(key, None)
                self.assertEqual(delay, expected_delay)
                retained = json.loads(json.dumps(retained))
                retained['minecraft:transformation'].pop('delay')
                self.assertEqual(group, retained)


if __name__ == '__main__':
    unittest.main()
