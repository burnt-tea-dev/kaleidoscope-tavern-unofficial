"""Offline sequential replay. No network, Git, GUI, engine, or original-workspace dependency.
Only temporary work copies under this package are written; originals remain immutable.
"""
import sys
if sys.flags.optimize:
    raise SystemExit("Replay refuses Python optimization (-O/-OO): integrity assertions must remain enabled.")

from pathlib import Path
import contextlib, copy, hashlib, io, json, runpy, shutil, sys, tempfile
from PIL import Image
from census import verify_census
from path_guard import safe_path, reject_symlinks
P = Path(__file__).resolve().parent.parent
reject_symlinks(P)
read = lambda p:json.loads(p.read_text())
sha = lambda b:hashlib.sha256(b).hexdigest()

def hash_inventory(root, manifest):
    for name, expected in manifest.items():
        b = safe_path(root,name).read_bytes()
        if isinstance(expected, dict):
            assert len(b) == expected['bytes'], name
            expected = expected['sha256']
        assert sha(b) == expected, name

def typed(value, expected):
    assert type(value) is type(expected) and value == expected, (value, expected)

negative = []
def rejects(label, fn):
    try:
        fn()
    except (AssertionError, ValueError, KeyError):
        negative.append({'tamper':label,'rejected':True})
        return
    raise AssertionError('Accepted negative control: '+label)

manifest = read(P/'portable-manifest.json')
for name, record in manifest['files'].items():
    b=safe_path(P,name).read_bytes()
    assert len(b)==record['bytes'] and sha(b)==record['sha256'], name
actual={str(f.relative_to(P)) for f in P.rglob('*') if f.is_file() and '.replay-' not in str(f.relative_to(P)) and '__pycache__' not in f.parts}
assert actual == set(manifest['files']) | {'portable-manifest.json'}, 'Unmanifested package file'
rejects('parent traversal path',lambda:safe_path(P,'../outside'))
rejects('absolute payload path',lambda:safe_path(P,'/tmp/outside'))
rejects('embedded parent traversal path',lambda:safe_path(P,'originals/../README.md'))
with tempfile.TemporaryDirectory(prefix='.replay-',dir=P) as guard_tmp:
    link=Path(guard_tmp)/'linked-original'
    link.symlink_to(P/'originals',target_is_directory=True)
    rejects('symlink payload path',lambda:safe_path(P,str(link.relative_to(P))+'/candidate/manifest.json'))
rejects('typed false replaced by numeric zero',lambda:typed(0,False))
rejects('typed count replaced by string',lambda:typed('7',7))
consumers=verify_census(P)
payload={str(p.relative_to(P/'census')):p.read_bytes() for p in (P/'census').rglob('*') if p.is_file()}
bad=dict(payload);bad.pop(next(iter(bad)))
rejects('omitted nonconsumer census resource',lambda:verify_census(P,bad))
bad=dict(payload);bad['runtime/RP/entity/extra.json']=b'{}'
rejects('extra census resource',lambda:verify_census(P,bad))
bad=dict(payload);name=next(n for n in bad if n not in consumers);bad[name]+=b'geometry.kt_runtime.pressing_card'
rejects('hidden extra consumer in canonical resource',lambda:verify_census(P,bad))

summary={'status':'passed','mode':'offline saved-input audit replay, no new GUI or gameplay acceptance','candidate_sha256':'d93249923210a8711fa038105816380407b9d70811c23313d4ddb56d68b83eea','census':{'canonical_entity_attachable_json_files':len(payload),'pressing_card_consumers':len(consumers),'proof':'all 129 canonical paths and Git blob hashes checked against saved canonical-runtime-tree; eight exact input consumers checked'},'gui':{},'audits':{}}
for label, gui_dir, report_file, camera_key, accepted, excluded in [('candidate','gui-evidence-20261109','review-index.json','numeric_camera_evidence',7,2),('n03','gui-review','review-report.json','camera_evidence',14,7)]:
    root=P/'originals'/label;gui=root/gui_dir
    hash_inventory(root,read(root/'artifact-sha256.json'))
    hash_inventory(gui,read(gui/'artifact-sha256.json'))
    original=read(root/'manifest.json');audit=read(root/'independent-audit.json');report=read(gui/report_file)
    typed(original['gui_reviewed'],False);typed(audit['gui_reviewed'],False);typed(report['gui_completed'],True)
    typed(report['accepted_original_screenshots'],accepted);typed(report['excluded_original_diagnostics'],excluded)
    assert len(report['captures'])==accepted and len(report['diagnostics'])==excluded and len(report[camera_key])==1
    if label=='candidate':
        typed(original['runtime_applied'],False);typed(audit['runtime_applied'],False);typed(audit['native_execution'],False);typed(report['runtime_applied'],False)
        assert report['candidate_sha256']==summary['candidate_sha256']
        for flag in ['all_originals_unchanged','all_screenshots_original_bytes']:typed(read(gui/'final-integrity.json')[flag],True)
        assert read(gui/'final-integrity.json')['errors']==[]
        typed(read(gui/'final-integrity.json')['checked_original_artifacts'],280)
    rows=report['captures']+report['diagnostics']+report[camera_key]
    assert len({r['file'] for r in rows})==len(rows)
    for row in rows:
        b=safe_path(gui,row['file']).read_bytes()
        assert len(b)==row['bytes'] and sha(b)==row['sha256']
        with Image.open(io.BytesIO(b)) as im:
            assert im.format==row['format']=='JPEG' and list(im.size)==row['dimensions'];im.verify()
        if 'scene_sha256' in row:assert sha(safe_path(root,row['scene']).read_bytes())==row['scene_sha256']
    for row in report['captures']:
        assert 'excluded' not in row['status']
        for key in ['camera','visibility','status']:assert isinstance(row[key],str) and row[key]
        for key in (['caption','observations','capture_specific_limits'] if label=='candidate' else ['findings','source_current_identity']):assert isinstance(row[key],str) and row[key]
    for row in report['diagnostics']:assert 'excluded' in row['status'] and isinstance(row['reason'],str) and row['reason']
    for row in report[camera_key]:assert row['related_capture'] in {r['file'] for r in report['captures']}
    identities=read(gui/'scene-identity-index.json')
    assert len(identities)==(6 if label=='candidate' else 8)
    for rec in identities:
        assert sha(safe_path(root,rec['scene']).read_bytes())==rec['sha256']
        doc=read(safe_path(root,rec['scene']));elems={e['uuid']:e for e in doc['elements']}
        if label=='candidate':
            assert rec['metadata']==doc['_review']
            assert {m['uuid'] for m in rec['meshes']}==set(elems)
            for m in rec['meshes']:
                e=elems[m['uuid']];assert m['review']==e['_review'] and m['name']==e['name'] and m['faces']==len(e['faces'])
        else:
            for m in rec['content_meshes']:
                e=elems[m['uuid']];assert m['name']==e['name'] and m['face_count']==len(e['faces']) and m['matrix']==e['_review']['matrix']
    summary['gui'][label]={'accepted':accepted,'excluded':excluded,'camera_only':1,'raw_jpeg_integrity':True,'annotations_and_scene_identities_verified':True,'original_pending_flags_preserved':True,'completed_supplement_is_separate':True}

# Run ONLY adapted independent validators against disposable copies. Do not run
# prepare/build/finalize or GUI scripts: their original path and status history stays intact.
with tempfile.TemporaryDirectory(prefix='.replay-',dir=P) as tmp:
    for label, script in [('candidate','audit_review.py'),('n03','validate_n03.py')]:
        work=Path(tmp)/label;shutil.copytree(P/'originals'/label,work)
        sys.path.insert(0,str(work))
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                runpy.run_path(str(P/'replay'/script),init_globals={'WORK':work,'PACKAGE':P})
        finally:
            sys.path.remove(str(work));sys.modules.pop('audit_helpers',None)
        generated=read(work/'independent-audit.json');saved=read(P/'originals'/label/'independent-audit.json')
        assert generated==saved, label+' audit replay must match saved typed result'
        if label=='candidate':
            assert read(work/'pose-bounds-audit.json')==read(P/'originals/candidate/pose-bounds-audit.json')
            typed(generated['mesh_count'],36);typed(generated['directed_faces'],455)
            typed(generated['all_card_pose_dimensions']['poses_checked'],320)
            typed(generated['all_card_pose_dimensions']['selected_seed_all_poses_inside_declared_bounds'],False)
            typed(generated['all_card_pose_dimensions']['before_all_poses_inside_declared_bounds'],False)
            assert len(generated['negative_controls'])==8 and all(type(r['rejected']) is bool and r['rejected'] for r in generated['negative_controls'])
            summary['audits'][label]={k:generated[k] for k in ['hashes','mesh_count','directed_faces','vertices','max_matrix_error','max_vertex_error','negative_controls']}
            summary['audits'][label]['poses']=320
        else:
            summary['audits'][label]={k:generated[k] for k in ['hashes','meshes','directed_faces','vertices','body_instances']}
summary['portable_negative_controls']=negative
summary['limitations']=manifest['limitations']
print(json.dumps(summary,indent=2))
