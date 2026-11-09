#!/usr/bin/env python3
"""Offline replay of immutable N05 evidence. No Git, network, GUI or engine."""
import contextlib
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import runpy
import shutil
import sys
import tempfile
import zipfile

for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
CONTROL_ALIAS='../tavern-bottle-review-20261108/scenes/champagne.bbmodel'


def digest(raw): return hashlib.sha256(raw).hexdigest()


def parse_json(text):
    def finite(value):
        number=float(value)
        if not math.isfinite(number): raise ValueError('Nonfinite JSON number')
        return number
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result: raise ValueError('Duplicate JSON key')
            result[key]=value
        return result
    return json.loads(text,object_pairs_hook=unique,parse_float=finite,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON constant')))


def read(path): return parse_json(path.read_text())

def relative_file(root,name):
    if not isinstance(name,str) or not name or any(c in name for c in ('\\',':','\0')):
        raise ValueError('Invalid relative evidence path')
    if name.startswith('/') or any(p in ('','.','..') for p in name.split('/')):
        raise ValueError('Unsafe relative evidence path')
    root=Path(root)
    if any(p.is_symlink() for p in (root.absolute(),*root.absolute().parents)):
        raise ValueError('Symlink evidence root')
    target=root
    for part in PurePosixPath(name).parts:
        target=target/part
        if target.is_symlink(): raise ValueError('Symlink evidence member')
    if not target.resolve().is_relative_to(root.resolve()): raise ValueError('Escaping evidence path')
    return target


def same_json_values_and_types(a,b):
    return json.dumps(a,sort_keys=True,separators=(',',':'),allow_nan=False)==json.dumps(b,sort_keys=True,separators=(',',':'),allow_nan=False)


def verify_bytes(raw,row):
    assert type(row['bytes']) is int and row['bytes']==len(raw)
    assert digest(raw)==row['sha256']


def verify_inventory(root):
    records=read(relative_file(root,'artifact-sha256.json'))['files']
    seen=set()
    for row in records:
        name=row['file'];path=relative_file(root,name)
        if name in seen or name=='artifact-sha256.json': raise ValueError('Duplicate/self-referential inventory')
        seen.add(name);verify_bytes(path.read_bytes(),row)
    actual=set()
    for path in root.rglob('*'):
        if path.is_symlink(): raise ValueError('Symlink in evidence package')
        if path.is_file(): actual.add(path.relative_to(root).as_posix())
    assert actual==seen|{'artifact-sha256.json'}, 'Missing or extra evidence payload'


def inspect_zip(raw,archive,work,seen):
    """Inspect all bytes before any extraction. Returned writes are inert data."""
    expected={};pending=[]
    for row in archive['entries']:
        name=row['file'];relative_file(work,name)
        if name in expected: raise ValueError('Duplicate archive inventory member')
        expected[name]=row
    with zipfile.ZipFile(io.BytesIO(raw)) as source:
        names=source.namelist()
        if len(names)!=len(set(names)) or set(names)!=set(expected): raise ValueError('Missing/extra/duplicate ZIP member')
        assert source.testzip() is None
        for item in source.infolist():
            name=item.filename;target=relative_file(work,name);mode=item.external_attr>>16
            if item.is_dir() or (mode&0o170000) not in (0,0o100000): raise ValueError('Nonregular ZIP member')
            if not name.startswith(archive['label']+'/') or name in seen: raise ValueError('Duplicate/cross-root archive member')
            if name.lower().endswith(('.jar','.class','.exe','.dll','.so')) or 'client_mappings' in name: raise ValueError('Disallowed executable/archive payload')
            assert item.file_size<2000000
            data=source.read(name);verify_bytes(data,expected[name])
            if name.endswith(('.json','.bbmodel')): parse_json(data.decode('utf-8-sig'))
            seen.add(name);pending.append((target,data))
    return pending


def archive_records(package):
    records=read(relative_file(package,'archive-entries.json'))
    seen=set()
    for row in records:
        name=row.pop('entries_file')
        if name in seen: raise ValueError('Duplicate member-list file')
        seen.add(name)
        row['entries']=read(relative_file(package,name))
    return records


def extract_archives(package,work,records=None):
    records=archive_records(package) if records is None else records
    seen=set();parts_seen=set();labels=set();pending=[]
    for archive in records:
        label=archive['label']
        if label not in ('original','candidate') or label in labels: raise ValueError('Duplicate/unknown archive label')
        labels.add(label);parts=[]
        for row in archive['parts']:
            name=row['file'];path=relative_file(package,name)
            if name in parts_seen or not name.startswith('archives/'): raise ValueError('Duplicate/invalid ZIP part')
            parts_seen.add(name);raw=path.read_bytes();verify_bytes(raw,row);assert 0<len(raw)<=180000;parts.append(raw)
        raw=b''.join(parts);verify_bytes(raw,archive)
        pending+=inspect_zip(raw,archive,work,seen)
    actual={p.relative_to(package).as_posix() for p in (package/'archives').rglob('*') if p.is_file()}
    assert parts_seen==actual, 'Unlisted or missing archive part'
    # No member is written until all ZIPs and every member have passed.
    for target,raw in pending:
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as out: out.write(raw)
    return seen


def hash_inventory(root,records):
    for name,row in records.items():
        raw=relative_file(root,name).read_bytes()
        if isinstance(row,dict): verify_bytes(raw,row)
        else: assert digest(raw)==row


def scene_path(package,root,name):
    if name==CONTROL_ALIAS: return relative_file(package,'controls/champagne.bbmodel')
    return relative_file(root,name)


def verify_gui(package,root,label):
    from PIL import Image
    gui=root/'gui-evidence-20261109';index=read(gui/'capture-index.json');receipt=read(gui/'completion-receipt.json')
    hash_inventory(root,read(root/'artifact-sha256.json'))
    inventory=read(gui/'artifact-sha256.json');hash_inventory(gui,inventory)
    assert digest((gui/'artifact-sha256.json').read_bytes())==receipt['artifact_manifest_sha256']
    assert receipt['status']=='bounded_editor_visual_review_complete'
    for key in ('canonical_written','engine_reviewed','remote_refreshed'): assert receipt[key] is False
    assert receipt['frozen_inputs_unchanged'] is True
    assert read(gui/'frozen-inputs-before.json')['sha256']==read(gui/'frozen-inputs-after.json')['sha256']
    before=read(gui/'frozen-inputs-before.json')['sha256'];hash_inventory(root,before)
    assert len(before)==(863 if label=='original' else 85)
    assert type(receipt['hashed_artifacts']) is int and receipt['hashed_artifacts']==len(inventory)
    rows=index['images']+index['excluded_images'] if label=='original' else index['images']+index['auxiliary_images']
    assert len(rows)==(29 if label=='original' else 52)
    assert type(receipt['screenshot_count']) is int and receipt['screenshot_count']==len(rows)
    assert len({r['file'] for r in rows})==len(rows)
    assert {r['file'] for r in rows}=={p.relative_to(gui).as_posix() for p in gui.rglob('*.jpg')}
    for row in rows:
        raw=relative_file(gui,row['file']).read_bytes();verify_bytes(raw,row)
        assert row['raw_unmodified_screenshot'] is True
        with Image.open(io.BytesIO(raw)) as im:
            assert im.format==row['format']=='JPEG' and list(im.size)==row['dimensions'];im.verify()
        if 'scene' in row: assert digest(scene_path(package,root,row['scene']).read_bytes())==row['scene_sha256']
    if label=='original':
        assert len(index['images'])==23 and len(index['excluded_images'])==6
        assert all(row['status'].startswith('excluded') for row in index['excluded_images'])
    else:
        assert index['engine_reviewed'] is False and len(index['images'])==36 and len(index['triplets'])==12
        byname={r['file']:r for r in index['images']};aux={r['file'] for r in index['auxiliary_images']};used=set()
        for triplet in index['triplets']:
            assert len(triplet['images'])==3 and triplet['camera']['same_camera_for_all_three'] is True
            assert triplet['camera']['readback_screenshot'] in aux
            for filename,variant in zip(triplet['images'],('SOURCE','BEFORE','AFTER')):
                row=byname[filename];assert filename not in used;used.add(filename)
                assert row['variant']==variant and row['case']==triplet['case']
                assert same_json_values_and_types(row['camera'],triplet['camera'])
                assert f'Exactly {variant} root' in row['visibility']
                assert row['status'] in ('discriminating_comparison','unchanged_broad_control')
        assert used==set(byname)
    return {'raw_jpegs':len(rows),'frozen_preparation_files':len(before),'bounded_editor_review':True,'engine_reviewed':False}


def replay(package=HERE):
    if sys.flags.optimize or os.environ.get('PYTHONOPTIMIZE') not in (None,'','0'):
        raise ValueError('Replay refuses optimized Python; assertions must remain active')
    verify_inventory(package)
    with tempfile.TemporaryDirectory(prefix='chalkboard-evidence-') as tmp:
        work=Path(tmp);entries=extract_archives(package,work)
        assert len(entries)==1043
        archives=read(package/'archive-entries.json')
        assert {a['label'] for a in archives}=={'original','candidate'}
        assert sum(len(a['parts']) for a in archives)==28
        summary={'status':'passed','archive_members':len(entries),'archive_parts':28,'gui':{},'audits':{},'engine_reviewed':False,'bottom_v_visual_proof':False}
        for label in ('original','candidate'): summary['gui'][label]=verify_gui(package,work/label,label)
        snapshot=work/'frozen-original';snapshot.mkdir()
        frozen=read(work/'candidate/original-integrity-before.json');assert len(frozen)==863
        for name,sha in frozen.items():
            raw=relative_file(work/'original',name).read_bytes();assert digest(raw)==sha
            out=relative_file(snapshot,name);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw)
        for label,script,report in [('original','original_validate_scenes.py','independent-saved-file-audit.json'),('candidate','candidate_audit_review.py','independent-review-audit.json')]:
            root=work/label;saved=read(root/report)
            extras={name:read(root/name) for name in ('pixel-discrimination.json','original-integrity-after.json') if (root/name).exists()}
            with contextlib.redirect_stdout(io.StringIO()):
                runpy.run_path(str(package/'replay'/script),init_globals={'WORK':root,'ORIGINAL_SNAPSHOT':snapshot})
            generated=read(root/report)
            assert same_json_values_and_types(generated,saved), label+' independent audit differs'
            for name,expected in extras.items(): assert same_json_values_and_types(read(root/name),expected),name
            assert generated['gui_reviewed'] is False
            summary['audits'][label]={k:v for k,v in generated.items() if k in ('inputs','scenes','meshes','faces','vertices','max_vertex_error','max_uv_error','inputs_verified','saved_scenes','saved_meshes','saved_faces','saved_vertices','original_files_preserved')}
        return summary


if __name__=='__main__':
    print(json.dumps(replay(),indent=2,allow_nan=False))
