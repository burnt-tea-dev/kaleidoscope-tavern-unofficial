"""Legacy addon catalog labels are owned by Tavern, not a UI overlay.

Does not assert engine group selection, icon precedence or client acceptance.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'kaleidoscope_tavern:itemGroup.name.'


class LegacyCreativeLabels(unittest.TestCase):
    def test_legacy_addon_labels_exist_once_in_supported_locales(self):
        for locale in ('en_US', 'zh_CN', 'zh_TW', 'ja_JP', 'ru_RU'):
            with self.subTest(locale=locale):
                lines = (ROOT / 'runtime/RP/texts' / (locale + '.lang')).read_text().splitlines()
                for name in ('wines_spirits', 'cultivation', 'barware_bottles', 'decorations_lighting'):
                    values = [line.split('=', 1)[1] for line in lines
                              if line.startswith(PREFIX + name + '=')]
                    self.assertEqual(len(values), 1)
                    self.assertTrue(values[0].strip())
                    self.assertNotIn(PREFIX, values[0])

    def test_legacy_labels_reuse_existing_canonical_locale_meanings(self):
        for locale in ('en_US', 'zh_CN', 'zh_TW', 'ja_JP', 'ru_RU'):
            with self.subTest(locale=locale):
                labels = dict(line.split('=', 1) for line in
                              (ROOT / 'runtime/RP/texts' / (locale + '.lang')).read_text().splitlines()
                              if '=' in line and not line.startswith('#'))
                for legacy, current in {'wines_spirits': 'wines', 'cultivation': 'tavern_cultivation',
                                        'barware_bottles': 'empty_bottles',
                                        'decorations_lighting': 'tavern_decor'}.items():
                    self.assertEqual(labels[PREFIX + legacy], labels[PREFIX + current])


if __name__ == '__main__':
    unittest.main()
