"""Negative controls exercise the real current font contract on isolated copies."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from board_font_contract import (ROOT, ENTITY, METRICS, CONTROLLERS, ATLAS_DIRECTORY,
                                check, owned_sources, runtime_sources, retired_sources)
from build_board_font import SOURCE, generate

RENDERING = ('runtime/RP/models/entity/board_glyph_line.geo.json',
             'runtime/RP/models/entity/board_glyph_outline.geo.json',
             'runtime/RP/animations/board_glyph_line.animation.json')


class BoardFontContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        for name in runtime_sources() | {METRICS, SOURCE, CONTROLLERS, *RENDERING,
                                        'data/baseline-reconciliation.json',
                                        'data/launch-repair-reference.json',
                                        'data/efficiency-repair-reference.json'}:
            target = cls.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)

    def rejected(self, name, mutate, message):
        path = self.root / name; original = path.read_bytes()
        try:
            mutate(path)
            with self.assertRaisesRegex(AssertionError, message):
                check(self.root)
        finally:
            path.write_bytes(original)

    @staticmethod
    def json_edit(path, mutate):
        data = json.loads(path.read_text()); mutate(data); path.write_text(json.dumps(data))

    def test_complete_source_and_exact_retirement(self):
        result = check(self.root)
        self.assertEqual((result['logicalPages'], result['physicalAtlases'], result['glyphs']), (256, 224, 65536))
        self.assertEqual(result['sourceRgbaBytes'], 224 * 256 * 256 * 4)
        self.assertEqual(retired_sources(self.root), {
            f'{ATLAS_DIRECTORY}/glyph_{page:02X}.png' for page in range(0xd9, 0xf9)})
        self.assertEqual(owned_sources(), runtime_sources(self.root) | retired_sources(self.root))
        self.assertFalse(runtime_sources(self.root) & retired_sources(self.root))

    def test_regeneration_and_metrics_only_preserve_the_complete_output(self):
        paths = runtime_sources(self.root) | {METRICS}
        original = {name: (self.root / name).read_bytes() for name in paths}
        for metrics_only in (False, False, True):
            self.assertEqual(generate(self.root, metrics_only=metrics_only), 224)
            self.assertEqual({name: (self.root / name).read_bytes() for name in paths}, original)
            check(self.root)

    def test_wrong_and_missing_logical_pages_are_rejected(self):
        for mutate in (lambda textures: textures.update(page_1='textures/board_font/glyph_00'),
                       lambda textures: textures.pop('page_217')):
            self.rejected(ENTITY, lambda path: self.json_edit(path, lambda d: mutate(
                d['minecraft:client_entity']['description']['textures'])), 'logical page binding')

    def test_missing_canonical_and_returned_alias_atlases_are_rejected(self):
        self.rejected(f'{ATLAS_DIRECTORY}/glyph_00.png', lambda path: path.unlink(), 'Missing, extra or retired')
        for name in ('glyph_D9.png', 'unlisted.png'):
            path = self.root / ATLAS_DIRECTORY / name
            try:
                shutil.copyfile(self.root / ATLAS_DIRECTORY / 'glyph_D8.png', path)
                with self.assertRaisesRegex(AssertionError, 'Missing, extra or retired'):
                    check(self.root)
            finally:
                path.unlink()

    def test_rgba_changes_and_missing_glyph_ink_are_rejected(self):
        def pixel(path, channel):
            with Image.open(path) as source:
                image = source.copy()
            color = list(image.getpixel((0, 0))); color[channel] ^= 255
            image.putpixel((0, 0), tuple(color)); image.save(path)
        for channel in range(4):
            with self.subTest(channel=channel):
                self.rejected(f'{ATLAS_DIRECTORY}/glyph_00.png', lambda path: pixel(path, channel), 'source RGBA')
        def remove_a(path):
            with Image.open(path) as source:
                image = source.copy()
            image.paste((255, 255, 255, 0), (16, 64, 32, 80)); image.save(path)
        self.rejected(f'{ATLAS_DIRECTORY}/glyph_00.png', remove_a, 'source RGBA')

    def test_page_order_and_selectors_are_rejected_on_both_passes(self):
        for kind in ('glyph', 'outline'):
            mutations = (
                (lambda c: c['arrays']['textures']['Array.pages'].reverse(), 'page order'),
                (lambda c: c['arrays']['geometries']['Array.cells'].reverse(), 'cell order'),
                (lambda c: c.update(textures=['Texture.page_0']), 'page selector'),
                (lambda c: c.update(geometry='Geometry.cell_0'), 'cell selector'))
            for mutate, message in mutations:
                with self.subTest(kind=kind, mutation=message):
                    self.rejected(CONTROLLERS, lambda path: self.json_edit(path, lambda d: mutate(
                        d['render_controllers']['controller.render.kt_runtime.board_' + kind])), message)

    def test_missing_geometry_and_changed_uv_tint_or_outline_are_rejected(self):
        self.rejected(ENTITY, lambda path: self.json_edit(path, lambda d:
            d['minecraft:client_entity']['description']['geometry'].pop('cell_65')), 'geometry bindings')
        self.rejected(RENDERING[0], lambda path: self.json_edit(path, lambda d:
            d['minecraft:geometry'][65]['bones'][2]['cubes'][0]['uv']['north'].update(uv=[0, 0])), 'Stale board render output')
        self.rejected(CONTROLLERS, lambda path: self.json_edit(path, lambda d:
            d['render_controllers']['controller.render.kt_runtime.board_glyph']['overlay_color'].update(r='0')), 'Stale board render output')
        self.rejected(RENDERING[2], lambda path: self.json_edit(path, lambda d:
            d['animations']['animation.kt_runtime.board_glyph_line']['bones']['outline_0'].update(position=[0, 0, 0])), 'Stale board render output')

    def test_metrics_and_pinned_source_cannot_drift(self):
        self.rejected(METRICS, lambda path: path.write_text(path.read_text().replace("const FONT_ADVANCE_DIGITS='", "const FONT_ADVANCE_DIGITS='0", 1)), 'advances or bold offset')
        self.rejected(SOURCE, lambda path: path.write_bytes(path.read_bytes() + b'changed'), 'GNU Unifont source differs')

    def test_retired_inverse_guard_cannot_return(self):
        self.rejected('data/baseline-reconciliation.json', lambda path: self.json_edit(path, lambda d:
            d['files'].update({ENTITY: {}})), 'historical postimage')


if __name__ == '__main__':
    unittest.main()
