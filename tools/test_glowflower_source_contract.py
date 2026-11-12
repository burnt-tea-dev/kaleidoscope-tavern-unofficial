"""Source-based regression and mutations for the shared hidden-base repair."""
import copy
import json
import shutil
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from glowflower_source_contract import ROOT, SOURCE, GEOMETRIES, check, read, resource_paths, runtime_sources, source_faces
from normalize_luminous_base import normalize
from PIL import Image


class GlowflowerSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        for name in resource_paths():
            p = cls.root/name
            p.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/name,p)
        shutil.copytree(ROOT/SOURCE, cls.root/SOURCE)

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def rejects(self, name, mutation):
        p = self.root/name
        before = p.read_bytes()
        try:
            doc = json.loads(before)
            mutation(doc)
            p.write_text(json.dumps(doc))
            with self.assertRaises(AssertionError): check(self.root)
        finally: p.write_bytes(before)

    def test_source_faces_all_four_counts(self):
        report = check(self.root)
        self.assertEqual(4,report['meshes'])
        self.assertEqual(40,report['cropped_occluded_shell_faces'])
        self.assertEqual(20,report['removed_legacy_x_offsets'])
        self.assertEqual(240,report['ordered_faces'])
        self.assertFalse(report['engine_accepted'])

    def test_each_trimmed_face_rejects_legacy_shift_crop_and_uv_errors(self):
        for name in GEOMETRIES:
            doc = read(self.root/name)
            cubes = doc['minecraft:geometry'][0]['bones'][0]['cubes']
            indices = [i for i,c in enumerate(cubes) if c['origin'][1] == 1.1 and c['size'][1] == 10 and len(c['uv']) == 1]
            self.assertTrue(indices)
            for i in indices:
                side = next(iter(cubes[i]['uv']))
                def cube(d): return d['minecraft:geometry'][0]['bones'][0]['cubes'][i]
                with self.subTest(name=name,cube=i,face=side):
                    self.rejects(name,lambda d: cube(d)['origin'].__setitem__(0,cube(d)['origin'][0]+.0625))
                    self.rejects(name,lambda d: cube(d)['origin'].__setitem__(1,.1))
                    self.rejects(name,lambda d: cube(d)['size'].__setitem__(1,11))
                    self.rejects(name,lambda d: cube(d)['uv'][side]['uv_size'].__setitem__(1,11))
                    self.rejects(name,lambda d: cube(d)['uv'][side]['uv'].__setitem__(1,6))

    def test_every_retained_sheet_keeps_exact_thickness_and_uv(self):
        for name in GEOMETRIES:
            doc = read(self.root/name)
            cubes = doc['minecraft:geometry'][0]['bones'][0]['cubes']
            for i,c in enumerate(cubes):
                if c['size'][1] != .125: continue
                def cube(d): return d['minecraft:geometry'][0]['bones'][0]['cubes'][i]
                self.rejects(name,lambda d: cube(d)['size'].__setitem__(1,0))
                self.rejects(name,lambda d: cube(d)['uv']['up']['uv'].__setitem__(0,cube(d)['uv']['up']['uv'][0]+1))

    def test_occlusion_requires_source_base_and_opaque_texels(self):
        p = ROOT/SOURCE
        with Image.open(p/'glowflower_brew.png') as im: image = im.convert('RGBA')
        for count in range(1,5):
            model = read(p/f'count{count}.json')
            for pixel in ((11,15),(0,12),(6,12)):
                changed = image.copy();changed.putpixel(pixel,(0,0,0,0))
                with self.assertRaisesRegex(AssertionError,'not fully opaque'): source_faces(model,changed,count)
            model['elements'] = [e for e in model['elements'] if not(e['from'][1] == .1 and e['to'][1] == 1.1)]
            with self.assertRaisesRegex(AssertionError,'covering base'): source_faces(model,image,count)

    def test_normalizer_restores_only_legacy_shell_and_is_idempotent(self):
        for name in GEOMETRIES:
            actual = read(self.root/name)
            expected = copy.deepcopy(actual)
            strips = 0
            for cube in expected['minecraft:geometry'][0]['bones'][0]['cubes']:
                if cube['origin'][1] != 1.1 or cube['size'][1] != 10 or len(cube['uv']) != 1: continue
                side = next(iter(cube['uv']))
                cube['origin'][1] = .1;cube['size'][1] = 11;cube['uv'][side]['uv_size'][1] = 11
                if side == 'east': cube['origin'][0] += .0625
                if side == 'west': cube['origin'][0] -= .0625
                strips += 1
            self.assertEqual(strips,normalize(expected))
            self.assertEqual(actual,expected)
            self.assertEqual(0,normalize(expected))

    def test_current_owner_cannot_return_to_historical_projection(self):
        for name in runtime_sources():
            for section in ('files','reviewedFunctionalDeltas'):
                self.rejects('data/baseline-reconciliation.json', lambda d, section=section, name=name:
                    d.setdefault(section,{}).__setitem__(name,{}))
            for section in ('reviewedFunctionalDeltaLayers','reviewedAssetDeltaLayers'):
                self.rejects('data/baseline-reconciliation.json', lambda d, section=section, name=name:
                    d.setdefault(section,[]).append({'release':'fixture','files':{name:{}}}))
            for ledger in ('launch-repair-reference.json','efficiency-repair-reference.json'):
                for section in ('reviewedChanges','newRuntimeFiles','removedRuntimeFiles'):
                    self.rejects('data/'+ledger, lambda d, section=section, name=name:
                        d.setdefault(section,{}).__setitem__(name,{}))
            self.rejects('data/drink-surface-review.json', lambda d, name=name:
                d['files'].__setitem__(name,{}))

    def test_baseline_reader_validates_current_source_before_returning_bytes(self):
        import baseline_reference as reference
        with mock.patch.object(reference,'__file__',str(self.root/'tools/baseline_reference.py')):
            for name in runtime_sources():
                p = self.root/name
                original = p.read_bytes()
                try:
                    self.assertEqual(original,reference.previous_bytes(self.root,p))
                    doc = json.loads(original)
                    doc['minecraft:geometry'][0]['bones'][0]['cubes'][0]['origin'][0] += .0625
                    p.write_text(json.dumps(doc))
                    with self.assertRaisesRegex(AssertionError,'Source ordered vertex/UV mismatch'):
                        reference.previous_bytes(self.root,p)
                finally: p.write_bytes(original)

    def test_launch_reaches_actual_source_after_valid_incense_and_pressing(self):
        import check_launch
        import check_incense_surfaces as incense
        import machine_ingredient_geometry as pressing
        # Preserve the existing launch order and exercise real validators.
        # Copy their bounded input contracts rather than mocking prerequisites.
        paths = set(pressing.resource_paths()) | set(incense.runtime_sources()) | {
            'runtime/RP/textures/terrain_texture.json',
            'data/incense-surfaces/source.json', 'data/incense-surfaces/java-closed.json',
            'data/incense-surfaces/java-open.json',
        } | {f'runtime/RP/textures/kaleidoscope_tavern/block/deco/incense/{kind}_incense.png'
             for kind in incense.KINDS}
        for name in paths:
            path = self.root/name
            path.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/name,path)
        shutil.copytree(ROOT/pressing.SOURCE,self.root/pressing.SOURCE,dirs_exist_ok=True)
        self.assertEqual(256,incense.check(self.root)['firstVisibleUndersideRays'])
        self.assertEqual([8,8,.5],pressing.check(self.root)['card_dimensions'])
        p = self.root/GEOMETRIES[0]
        original = p.read_bytes()
        try:
            doc = json.loads(original)
            doc['minecraft:geometry'][0]['bones'][0]['cubes'][0]['uv']['south']['uv_size'][1] += 1
            p.write_text(json.dumps(doc))
            with mock.patch.object(check_launch,'ROOT',self.root), mock.patch('sys.argv',['check_launch.py']):
                with self.assertRaisesRegex(AssertionError,'Source ordered vertex/UV mismatch'):
                    check_launch.main()
        finally: p.write_bytes(original)

    def test_source_fixture_mutation_and_face_removal_are_rejected(self):
        self.rejects(SOURCE+'/count1.json',lambda d: d['elements'][0]['faces']['east']['uv'].__setitem__(0,0))
        for name in GEOMETRIES:
            self.rejects(name,lambda d: d['minecraft:geometry'][0]['bones'][0]['cubes'].pop())


if __name__ == '__main__': unittest.main()
