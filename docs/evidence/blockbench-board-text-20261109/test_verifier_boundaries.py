#!/usr/bin/env python3
"""Small synthetic security-boundary tests. Never modify published evidence."""
import hashlib
import importlib.util
import json
import os
import shutil
from pathlib import Path
import stat
import struct
import subprocess
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

    @staticmethod
    def snapshot(root):
        result = {}
        for path in sorted(root.rglob('*')):
            mode = path.lstat().st_mode
            name = path.relative_to(root).as_posix()
            if stat.S_ISLNK(mode): result[name] = ('link', os.readlink(path))
            elif stat.S_ISREG(mode): result[name] = ('file', hashlib.sha256(path.read_bytes()).hexdigest())
            else: result[name] = ('mode', mode)
        return result

    def test_cli_isolation_rejects_without_any_writes(self):
        # Audit events catch transient tempfile probe files as well as final outputs.
        driver = r'''import json, os, runpy, sys
writes = []
def audit(event, args):
    if event == 'open' and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
        writes.append([event, str(args[0])])
    elif event in ('os.mkdir', 'os.remove', 'os.rmdir', 'os.rename', 'os.symlink', 'os.link'):
        writes.append([event, str(args[0])])
sys.addaudithook(audit)
sys.argv = sys.argv[1:]
try: runpy.run_path(sys.argv[0], run_name='__main__')
finally: print('WRITE_AUDIT=' + json.dumps(writes))
'''
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);package=root/'package';package.mkdir()
            script=package/'validate_evidence.py';shutil.copyfile(Path(v.__file__),script)
            source=root/'plain-source';source.mkdir();(source/'nested').mkdir()
            (source/'input.json').write_text('{"unchanged":true}\n')
            git=root/'git';(git/'.git').mkdir(parents=True);(git/'.git/HEAD').write_text('ref: refs/heads/main\n')
            alias=root/'source-alias';alias.symlink_to(source,target_is_directory=True)
            package_alias=root/'package-alias';package_alias.symlink_to(package,target_is_directory=True)
            existing=root/'existing';existing.write_text('unchanged\n')
            external=root/'external-work';report=root/'external-report.json'
            cases=[]
            for option in ('--work-dir','--report'):
                for name,path in (('repository-root',source),('repository-child',source/'output'),
                                  ('repository-descendant',source/'nested/output'),('repository-ancestor',root),
                                  ('package-root',package),('package-child',package/'output'),
                                  ('symlink-source',alias/'output'),('symlink-package',package_alias/'output'),
                                  ('git-child',git/'output'),('existing',existing),
                                  ('traversal',root/'missing/../output'),('missing-parent',root/'missing/output')):
                    args=[option,str(path)]
                    if option=='--report':args=['--work-dir',str(external),*args]
                    cases.append((option+'-'+name,args,{}))
            for name,path in (('source',source),('source-child',source/'nested'),('package',package),
                              ('source-symlink',alias),('package-symlink',package_alias),('git',git)):
                cases.append(('tmpdir-'+name,['--report',str(report)],{'TMPDIR':str(path)}))
            cases.extend([
                ('temp-source',[],{'TEMP':str(source)}),('tmp-source',[],{'TMP':str(source)}),
                ('outputs-identical',['--work-dir',str(external),'--report',str(external)],{}),
                ('report-in-work',['--work-dir',str(external),'--report',str(external/'report.json')],{}),
                ('work-in-report',['--work-dir',str(report/'work'),'--report',str(report)],{}),
                ('repository-symlink',['--repository',str(alias),'--work-dir',str(external)],{}),
                ('repository-missing',['--repository',str(root/'missing'),'--work-dir',str(external)],{}),
                ('repository-file',['--repository',str(existing),'--work-dir',str(external)],{}),
                ('optimized-environment',['--work-dir',str(external)],{'PYTHONOPTIMIZE':'1'}),
                ('optimized-flag',['--work-dir',str(external)],{}),
            ])
            if hasattr(os,'mkfifo'):
                fifo=root/'repository-fifo';os.mkfifo(fifo)
                cases.append(('repository-fifo',['--repository',str(fifo),'--work-dir',str(external)],{}))
            base_env=dict(os.environ)
            for key in ('TMPDIR','TEMP','TMP','PYTHONOPTIMIZE'):base_env.pop(key,None)
            for name,args,environment in cases:
                with self.subTest(case=name):
                    before=self.snapshot(root)
                    flags=['-O'] if name=='optimized-flag' else []
                    result=subprocess.run([sys.executable,'-B',*flags,'-c',driver,str(script),'--repository',str(source),*args],
                                          cwd=root,env={**base_env,**environment},capture_output=True,text=True,timeout=10)
                    self.assertEqual(result.returncode,1,result.stdout+result.stderr)
                    self.assertIn('FAIL:',result.stderr)
                    audit_lines=[line for line in result.stdout.splitlines() if line.startswith('WRITE_AUDIT=')]
                    self.assertEqual(audit_lines,['WRITE_AUDIT=[]'],result.stdout+result.stderr)
                    self.assertEqual(self.snapshot(root),before)
                    self.assertFalse(external.exists());self.assertFalse(report.exists())

    def test_default_temp_common_ancestor_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);package=root/'package';package.mkdir();source=root/'source';source.mkdir()
            before=self.snapshot(root)
            def validate(package_arg,work,repository):
                self.assertEqual(package_arg,package);self.assertEqual(repository,source)
                self.assertEqual(work.parent,root);self.assertTrue(work.is_dir())
                if os.name=='posix':self.assertEqual(stat.S_IMODE(work.stat().st_mode),0o700)
                (work/'owned-result').write_text('temporary\n')
                return {'status':'synthetic success'}
            with mock.patch.object(v,'__file__',str(package/'validate_evidence.py')), \
                 mock.patch.object(sys,'argv',['validate_evidence.py','--repository',str(source)]), \
                 mock.patch.dict(os.environ,{'TMPDIR':str(root)}), \
                 mock.patch.object(v,'validate',side_effect=validate),mock.patch('builtins.print'):
                v.main()
            self.assertEqual(self.snapshot(root),before)

    def test_default_report_overlap_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);package=root/'package';package.mkdir();before=self.snapshot(root)
            report=root/'n06-portable-fixed'
            with mock.patch.object(v,'__file__',str(package/'validate_evidence.py')), \
                 mock.patch.object(sys,'argv',['validate_evidence.py','--report',str(report)]), \
                 mock.patch.dict(os.environ,{'TMPDIR':str(root)}), \
                 mock.patch.object(v.uuid,'uuid4',return_value=mock.Mock(hex='fixed')), \
                 mock.patch.object(v,'validate') as validate:
                with self.assertRaisesRegex(ValueError,'outputs overlap'):v.main()
                validate.assert_not_called()
            self.assertEqual(self.snapshot(root),before)

    def test_default_temp_cleanup_on_validation_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);package=root/'package';package.mkdir();before=self.snapshot(root)
            with mock.patch.object(v,'__file__',str(package/'validate_evidence.py')), \
                 mock.patch.object(sys,'argv',['validate_evidence.py']), \
                 mock.patch.dict(os.environ,{'TMPDIR':str(root)}), \
                 mock.patch.object(v,'validate',side_effect=ValueError('synthetic validation failure')):
                with self.assertRaisesRegex(ValueError,'synthetic validation failure'):v.main()
            self.assertEqual(self.snapshot(root),before)

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
