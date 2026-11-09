"""Real temporary-file/ZIP corruption tests; no mocks or skipped checks."""
import importlib.util
import io
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile

sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('chalk_evidence',Path(__file__).with_name('validate_evidence.py'))
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)


class Boundaries(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='chalk-evidence-boundary-');self.root=Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()
    def row(self,name,raw): return {'file':name,'bytes':len(raw),'sha256':v.digest(raw)}
    def make_zip(self,names=('original/file',),mode=0o100644):
        stream=io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',UserWarning)
            with zipfile.ZipFile(stream,'w') as z:
                for name in names:
                    info=zipfile.ZipInfo(name);info.external_attr=mode<<16;z.writestr(info,b'payload')
        return stream.getvalue()
    def archive(self,names=('original/file',)):
        return {'label':'original','entries':[self.row(name,b'payload')for name in names]}
    def test_unsafe_paths(self):
        for name in ('/absolute','../escape','a/../escape','a\\escape','C:/escape','C:escape','a:escape','a//b','./file','a/','a\0b',''):
            with self.subTest(name=name),self.assertRaises(ValueError):v.relative_file(self.root,name)
    def test_symlink_paths(self):
        (self.root/'target').write_text('data');(self.root/'link').symlink_to(self.root/'target');(self.root/'dirlink').symlink_to(self.root,target_is_directory=True)
        for name in ('link','dirlink/target'):
            with self.assertRaises(ValueError):v.relative_file(self.root,name)
    def test_only_explicit_control_alias(self):
        self.assertEqual(v.scene_path(self.root,self.root,v.CONTROL_ALIAS),self.root/'controls/champagne.bbmodel')
        with self.assertRaises(ValueError):v.scene_path(self.root,self.root,'../other.bbmodel')
    def test_json_nonfinite_and_duplicate_keys(self):
        p=self.root/'value.json'
        for text in ('{"x":1,"x":2}','[NaN]','[Infinity]','[-Infinity]','[1e999]','[-1e999]'):
            p.write_text(text)
            with self.subTest(text=text),self.assertRaises(ValueError):v.read(p)
    def test_finite_numbers_and_exact_types(self):
        p=self.root/'value.json';p.write_text('[0.0,-0.0,1e2,1e-3,1]');j=v.read(p)
        self.assertEqual(j,[0.,-0.,100.,.001,1]);self.assertEqual(math.copysign(1.,j[1]),-1.)
        self.assertFalse(v.same_json_values_and_types(False,0));self.assertFalse(v.same_json_values_and_types(1,1.));self.assertFalse(v.same_json_values_and_types(1,'1'))
        with self.assertRaises(ValueError):v.same_json_values_and_types(float('nan'),float('nan'))
    def test_inventory_missing_extra_duplicate_tampered(self):
        p=self.root/'payload';p.write_bytes(b'payload');row=self.row('payload',b'payload');index=self.root/'artifact-sha256.json'
        index.write_text(json.dumps({'files':[row]}));v.verify_inventory(self.root)
        for rows,error in [([],AssertionError),([row,row],ValueError),([self.row('payload',b'bad')],AssertionError),([self.row('artifact-sha256.json',b'x')],ValueError)]:
            index.write_text(json.dumps({'files':rows}))
            with self.assertRaises(error):v.verify_inventory(self.root)
        index.write_text(json.dumps({'files':[row]}));(self.root/'extra').write_text('x')
        with self.assertRaises(AssertionError):v.verify_inventory(self.root)
    def test_valid_zip_is_inspected_without_writing(self):
        result=v.inspect_zip(self.make_zip(),self.archive(),self.root,set());self.assertEqual(len(result),1);self.assertFalse((self.root/'original').exists())
    def test_zip_traversal_and_nonregular(self):
        for name in ('../escape','original/../escape','/absolute','original/a//b'):
            with self.subTest(name=name),self.assertRaises(ValueError):v.inspect_zip(self.make_zip((name,)),self.archive((name,)),self.root,set())
        for mode in (0o120777,0o040755,0o020644):
            with self.subTest(mode=mode),self.assertRaises(ValueError):v.inspect_zip(self.make_zip(mode=mode),self.archive(),self.root,set())
    def test_zip_member_set_corruption(self):
        for names in ((),('original/file','original/extra'),('original/file','original/file')):
            with self.subTest(names=names),self.assertRaises(ValueError):v.inspect_zip(self.make_zip(names),self.archive(),self.root,set())
        archive=self.archive();archive['entries']*=2
        with self.assertRaises(ValueError):v.inspect_zip(self.make_zip(),archive,self.root,set())
        with self.assertRaises(ValueError):v.inspect_zip(self.make_zip(),self.archive(),self.root,{'original/file'})
    def test_zip_wrong_hash_or_size(self):
        for key,value in [('sha256','0'*64),('bytes',False),('bytes',8)]:
            archive=self.archive();archive['entries'][0][key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):v.inspect_zip(self.make_zip(),archive,self.root,set())
    def test_zip_json_is_checked_before_any_write(self):
        for value in ('{"x":1e999}', '{"x":1,"x":2}', '{"ignored":NaN}'):
            stream=io.BytesIO()
            with zipfile.ZipFile(stream,'w') as z:z.writestr('original/input.json',value)
            archive={'label':'original','entries':[self.row('original/input.json',value.encode())]}
            with self.subTest(value=value),self.assertRaises(ValueError):v.inspect_zip(stream.getvalue(),archive,self.root,set())
            self.assertFalse((self.root/'original').exists())
    def test_corrupt_zip_bytes_are_rejected(self):
        with self.assertRaises(zipfile.BadZipFile):v.inspect_zip(self.make_zip()[:-30],self.archive(),self.root,set())
    def test_symlink_root_ancestor_is_rejected(self):
        (self.root/'real').mkdir();(self.root/'real/sub').mkdir();(self.root/'link').symlink_to(self.root/'real',target_is_directory=True)
        with self.assertRaises(ValueError):v.relative_file(self.root/'link/sub','file')

    def test_zip_prohibited_payload(self):
        for name in ('original/x.jar','original/x.exe','candidate/wrong'):
            with self.subTest(name=name),self.assertRaises(ValueError):v.inspect_zip(self.make_zip((name,)),self.archive((name,)),self.root,set())
    def test_part_tampering_and_no_partial_extraction(self):
        package=self.root/'package';(package/'archives').mkdir(parents=True);work=self.root/'out';work.mkdir()
        raw=self.make_zip();path=package/'archives/part';path.write_bytes(raw)
        archive={**self.archive(),'bytes':len(raw),'sha256':v.digest(raw),'parts':[self.row('archives/part',raw)]}
        path.write_bytes(raw+b'corrupt')
        with self.assertRaises(AssertionError):v.extract_archives(package,work,[archive])
        self.assertEqual(list(work.rglob('*')),[])
        path.write_bytes(raw);(package/'archives/extra').write_bytes(b'x')
        with self.assertRaises(AssertionError):v.extract_archives(package,work,[archive])
        self.assertEqual(list(work.rglob('*')),[])
    def test_optimized_python_rejected(self):
        result=subprocess.run([sys.executable,'-O','-B',str(Path(v.__file__))],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0);self.assertIn('refuses optimized Python',result.stderr)


if __name__=='__main__':unittest.main()
