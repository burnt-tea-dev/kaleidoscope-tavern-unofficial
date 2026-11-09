"""Mutations of actual resource files exercise the source surface contract."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from chalkboard_geometry import ROOT, SOURCE, BLOCK, TERRAIN, AS, check, resource_paths, runtime_sources


class ChalkboardContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        for name in resource_paths():
            p = cls.root/name
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/name,p)
        shutil.copytree(ROOT/SOURCE,cls.root/SOURCE)

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def rejects(self,name,change):
        p = self.root/name
        before = p.read_bytes()
        try:
            doc = json.loads(before)
            change(doc)
            p.write_text(json.dumps(doc))
            with self.assertRaises(AssertionError): check(self.root)
        finally: p.write_bytes(before)

    def test_source_surfaces_and_both_cardinal_routes(self):
        report = check(self.root)
        self.assertEqual(report['slices'],8)
        self.assertEqual(report['source_exterior_areas']['small_north'],[16,16,28,448,28,448])
        self.assertEqual(report['source_exterior_areas']['large_east'],[48,48,28,1344,28,1344])
        self.assertFalse(report['engine_verified'])
        self.assertFalse(report['bottom_v_visual_proof'])

    def test_all_slices_faces_and_geometry_fields(self):
        for name in sorted(runtime_sources()):
            def cube(d): return d['minecraft:geometry'][0]['bones'][0]['cubes'][0]
            data = json.loads((self.root/name).read_text())
            for face in cube(data)['uv']:
                for field in ('uv','uv_size'):
                    for axis in range(2):
                        with self.subTest(name=name,face=face,field=field,axis=axis):
                            self.rejects(name,lambda d: cube(d)['uv'][face][field].__setitem__(axis,cube(d)['uv'][face][field][axis]+1))
            for field in ('origin','size'):
                for axis in range(3):
                    self.rejects(name,lambda d: cube(d)[field].__setitem__(axis,cube(d)[field][axis]+1))
            self.rejects(name,lambda d: cube(d).update(mirror=True))
            self.rejects(name,lambda d: cube(d).update(rotation=[0,180,0]))
            self.rejects(name,lambda d: d['minecraft:geometry'][0]['bones'][0]['pivot'].__setitem__(0,1))
            self.rejects(name,lambda d: cube(d)['uv']['north']['uv'].__setitem__(0,float('nan')))
            self.rejects(name,lambda d: cube(d)['origin'].__setitem__(1,False))

    def test_caps_cannot_move_back_to_internal_seams(self):
        for panel,side,opposite in [(0,'east','west'),(2,'west','east')]:
            for half in (0,1):
                name=f'runtime/RP/models/entity/java_chalk_large_{panel}_{half}.geo.json'
                def move(d):
                    uv=d['minecraft:geometry'][0]['bones'][0]['cubes'][0]['uv']
                    uv[opposite]=uv.pop(side)
                self.rejects(name,move)

    def test_route_material_and_facing_mutations(self):
        for i in range(8):
            self.rejects(BLOCK,lambda d: d['minecraft:block']['permutations'][i]['components']['minecraft:geometry'].update(identifier='geometry.wrong'))
            self.rejects(BLOCK,lambda d: d['minecraft:block']['permutations'][i]['components']['minecraft:material_instances']['*'].update(render_method='blend'))
            self.rejects(BLOCK,lambda d: d['minecraft:block']['permutations'][i]['components']['minecraft:material_instances']['*'].update(face_dimming=False))
        for i in (8,9):
            self.rejects(BLOCK,lambda d: d['minecraft:block']['permutations'][i]['components']['minecraft:transformation']['rotation'].__setitem__(1,180))
        self.rejects(TERRAIN,lambda d:d['texture_data']['kt_assets_a17_chalkboard_small'].update(textures='wrong'))

    def test_duplicate_consumers_and_ledger_reclaim_rejected(self):
        path=self.root/'runtime/RP/entity/unexpected.json'
        path.parent.mkdir(parents=True,exist_ok=True)
        try:
            path.write_text('{"geometry":"geometry.kt_java.chalk_small_0_0"}')
            with self.assertRaisesRegex(AssertionError,'route ownership'): check(self.root)
        finally: path.unlink()
        name=sorted(runtime_sources())[0]
        self.rejects('data/baseline-reconciliation.json',lambda d:d['files'].update({name:{'after':'unreviewed'}}))
        self.rejects('data/launch-repair-reference.json',lambda d:d['reviewedChanges'].update({name:{'after':'unreviewed'}}))

    def test_source_png_pixel_parity(self):
        # Pixel processing belongs at this explicit boundary, not baseline imports.
        from PIL import Image
        for size in ('small','large'):
            rel=AS+f'textures/entity/deco/{size}_chalkboard.png'
            a=Image.open(self.root/SOURCE/'forge'/rel).convert('RGBA')
            b=Image.open(self.root/SOURCE/'neoforge'/rel).convert('RGBA')
            self.assertEqual(a.size,b.size)
            self.assertEqual(a.tobytes(),b.tobytes())

    def test_no_site_contract_execution(self):
        script='import sys;sys.path.insert(0,sys.argv[1]);from chalkboard_geometry import check;check();assert "PIL" not in sys.modules'
        result=subprocess.run([sys.executable,'-I','-S','-B','-c',script,str(ROOT/'tools')],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__': unittest.main()
