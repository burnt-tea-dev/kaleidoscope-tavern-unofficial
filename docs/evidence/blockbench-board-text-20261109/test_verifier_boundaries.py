#!/usr/bin/env python3
"""Small synthetic security-boundary tests. Never modify published evidence."""
import importlib.util
import json
import os
from pathlib import Path
import stat
import struct
import sys
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile
import zlib

sys.dont_write_bytecode = True
spec=importlib.util.spec_from_file_location('n06_validator',Path(__file__).with_name('validate_evidence.py'))
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)


class Boundaries(unittest.TestCase):
    def test_paths(self):
        for p in ('../x','/x','a/../b','a//b','a/./b','a\\b','C:/x','', 'a/','a\0b'):
            with self.subTest(p=p), self.assertRaises(ValueError):v.safe_name(p)
        self.assertEqual(v.safe_name('prep/inputs/file.json'),'prep/inputs/file.json')

    def test_json(self):
        for s in ('{"a":1,"a":2}','[NaN]','[Infinity]','[-Infinity]','{"a":1e999}'):
            with self.subTest(s=s), self.assertRaises(ValueError):v.loads(s)
        self.assertEqual(v.loads('{"x":[1,2.5]}'),{'x':[1,2.5]})

    def test_outputs(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);package=root/'package';package.mkdir()
            for p in (package, package/'child', root):
                with self.assertRaises(ValueError):v.new_output(p,package)
            link=root/'link';link.symlink_to(package,target_is_directory=True)
            with self.assertRaises(ValueError):v.new_output(link/'child',package)
            repo=root/'repo';repo.mkdir();(repo/'.git').write_text('gitdir: somewhere')
            with self.assertRaises(ValueError):v.new_output(repo/'out',package)
            self.assertEqual(v.new_output(root/'fresh',package),root/'fresh')

    def fixture(self,root,kind):
        package=root/'package';package.mkdir();dest=root/'extract';dest.mkdir()
        payload=b'{"test":1}';name='prep/file.json';membername=name;mode=stat.S_IFREG|0o644
        if kind=='traversal':membername='../file.json'
        if kind=='absolute':membername='/file.json'
        if kind=='symlink':mode=stat.S_IFLNK|0o777
        archive=package/'chunk.zip'
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',UserWarning)
            with zipfile.ZipFile(archive,'w') as z:
                zi=zipfile.ZipInfo(membername);zi.external_attr=mode<<16;z.writestr(zi,payload)
                if kind=='duplicate':z.writestr(zi,payload)
                if kind=='extra':z.writestr('prep/extra.json',payload)
        entry={'archive':'chunk.zip','path':name,'bytes':len(payload),'sha256':v.sha(payload),'git_blob_sha1':v.blob(payload),'mode':'100644'}
        if kind=='payload_hash':entry['sha256']='0'*64
        if kind=='blob_hash':entry['git_blob_sha1']='0'*40
        if kind=='size':entry['bytes']+=1
        entries=[entry]
        if kind=='missing':entries.append(dict(entry,path='prep/missing.json'))
        if kind=='duplicate_inventory':entries.append(dict(entry))
        if kind=='corrupt_zip':archive.write_bytes(b'not zip')
        adata=archive.read_bytes();index={'archives':[{'path':'chunk.zip','bytes':len(adata),'sha256':v.sha(adata)}],'members':entries}
        if kind=='archive_hash':index['archives'][0]['sha256']='0'*64
        if kind=='duplicate_archive':index['archives'].append(dict(index['archives'][0]))
        (package/'archive-entries.json').write_text(json.dumps(index))
        return package,dest

    def test_archives(self):
        for kind in ('good','traversal','absolute','symlink','duplicate','extra','missing','duplicate_inventory','duplicate_archive','payload_hash','blob_hash','size','corrupt_zip','archive_hash'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as tmp:
                package,dest=self.fixture(Path(tmp),kind)
                if kind=='good':self.assertEqual(v.extract(package,dest),dest/'prep')
                else:
                    with self.assertRaises((ValueError,zipfile.BadZipFile)):v.extract(package,dest)

    def test_direct_inventory(self):
        with tempfile.TemporaryDirectory() as t:
            r=Path(t);(r/'artifact-sha256.json').write_text('{}');(r/'x').write_bytes(b'x')
            m={'x':{'bytes':1,'sha256':v.sha(b'x')}};v.inventory(r,m)
            (r/'extra').write_bytes(b'')
            with self.assertRaises(ValueError):v.inventory(r,m)

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'FIFO requires POSIX')
    def test_direct_fifo_rejected_without_read(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'artifact-sha256.json').write_text('{}')
            os.mkfifo(root/'extra_fifo')
            with mock.patch.object(Path, 'read_bytes', side_effect=AssertionError('FIFO must not be read')):
                for manifest in ({}, {'extra_fifo': {'bytes':0,'sha256':v.sha(b'')}}):
                    with self.subTest(listed=bool(manifest)), self.assertRaisesRegex(ValueError, 'nonregular'):
                        v.inventory(root,manifest)
                with self.assertRaisesRegex(ValueError, 'regular file'):
                    v.read(root/'extra_fifo')

    def test_other_direct_nonregular_modes(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'artifact-sha256.json').write_text('{}');entry=root/'special';entry.touch()
            original_lstat=Path.lstat
            for kind in (stat.S_IFSOCK,stat.S_IFCHR,stat.S_IFBLK):
                def fake_lstat(path, **kwargs):
                    if path==entry:return os.stat_result((kind|0o600,0,0,1,0,0,0,0,0,0))
                    return original_lstat(path,**kwargs)
                with self.subTest(kind=kind), mock.patch.object(Path,'lstat',fake_lstat), mock.patch.object(Path,'read_bytes',side_effect=AssertionError('nonregular must not be read')):
                    with self.assertRaisesRegex(ValueError,'nonregular'):v.inventory(root,{})

    def test_png_corruption(self):
        def chunk(name,data):return struct.pack('>I',len(data))+name+data+struct.pack('>I',zlib.crc32(name+data)&0xffffffff)
        b=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b'\0\xff\xff\xff\xff'))+chunk(b'IEND',b'')
        self.assertEqual(v.png(b,True),[b'\xff'])
        bad=bytearray(b);bad[-1]^=1
        for corrupt in (bytes(bad),b[:-1],b+b'extra'):
            with self.assertRaises(ValueError):v.png(corrupt)

    def test_jpeg_boundary(self):
        with self.assertRaises(ValueError):v.jpeg_size(b'not JPEG')
        with self.assertRaises(ValueError):v.jpeg_size(b'\xff\xd8\xff\xd9')


if __name__=='__main__':
    if sys.flags.optimize or os.environ.get('PYTHONOPTIMIZE'):
        raise SystemExit('FAIL: optimized Python is unsupported')
    unittest.main(verbosity=2)
