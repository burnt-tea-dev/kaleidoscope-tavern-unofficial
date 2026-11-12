"""Mutations exercise pinned-source painting vertices, UVs and all consumers."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from painting_geometry import ROOT, SOURCE, MODELS, check, resource_paths


class PaintingContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        for name in resource_paths():
            path = cls.root/name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/name, path)
        shutil.copytree(ROOT/SOURCE, cls.root/SOURCE)

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def rejects(self, name, mutation):
        p = self.root/name
        before = p.read_bytes()
        try:
            d = json.loads(before)
            mutation(d)
            p.write_text(json.dumps(d))
            with self.assertRaises(AssertionError): check(self.root)
        finally:
            p.write_bytes(before)

    @staticmethod
    def cube(d): return d['minecraft:geometry'][0]['bones'][0]['cubes'][0]

    def test_all_fourteen_consumers_twelve_placements(self):
        report = check(self.root)
        self.assertEqual(14, report['consumers'])
        self.assertEqual(168, report['placement_cases'])
        self.assertEqual(1008, report['faces'])
        self.assertEqual(4032, report['vertex_uv_pairs'])
        self.assertFalse(report['engine_verified'])

    def test_each_repaired_face_rejects_wrong_uv(self):
        for model, face in [('painting_wall','up'), ('painting_wall','down'),
                            ('painting_ceiling','up'), ('painting_ceiling','north'),
                            ('painting_ceiling','south'), ('painting_ceiling','west')]:
            with self.subTest(model=model, face=face):
                self.rejects(MODELS[model], lambda d: self.cube(d)['uv'][face]['uv'].__setitem__(0,
                    self.cube(d)['uv'][face]['uv'][0]+1))
                self.rejects(MODELS[model], lambda d: self.cube(d)['uv'][face].update(
                    uv_rotation=(self.cube(d)['uv'][face].get('uv_rotation',0)+180)%360))

    def test_floor_six_faces_preserved(self):
        for face in ('north','east','south','west','up','down'):
            with self.subTest(face=face):
                self.rejects(MODELS['painting_base'], lambda d: self.cube(d)['uv'][face]['uv_size'].__setitem__(1,
                    -self.cube(d)['uv'][face]['uv_size'][1]))

    def test_each_consumer_each_permutation_rotation(self):
        names=json.loads((self.root/SOURCE/'manifest.json').read_text())['consumers']
        for name in names:
            for index in range(12):
                with self.subTest(name=name, permutation=index):
                    self.rejects(f'runtime/BP/blocks/{name}.json', lambda d: d['minecraft:block']['permutations'][index]
                        ['components']['minecraft:transformation']['rotation'].__setitem__(1,
                        (d['minecraft:block']['permutations'][index]['components']['minecraft:transformation']['rotation'][1]+90)%360))

    def test_geometry_vertices_and_unsupported_deformation(self):
        for path in MODELS.values():
            for field in ('origin','size'):
                for axis in range(3):
                    self.rejects(path, lambda d: self.cube(d)[field].__setitem__(axis,self.cube(d)[field][axis]+1))
            self.rejects(path, lambda d: self.cube(d).update(mirror=True))
            self.rejects(path, lambda d: self.cube(d)['origin'].__setitem__(0,float('nan')))
            self.rejects(path, lambda d: self.cube(d)['size'].__setitem__(0,True))

    def test_source_bytes_and_missing_consumer_are_rejected(self):
        self.rejects(SOURCE+'/base.json', lambda d: d['elements'][0]['faces']['up']['uv'].__setitem__(0,0))
        self.rejects(SOURCE+'/tartaric_acid_painting.json', lambda d: d['variants'].pop(next(iter(d['variants']))))
        self.rejects('runtime/BP/blocks/tartaric_acid_painting.json', lambda d: d['minecraft:block']['permutations'].pop())


if __name__ == '__main__': unittest.main()
