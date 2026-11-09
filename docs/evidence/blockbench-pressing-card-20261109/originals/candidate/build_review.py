"""Build bounded source/before/after mesh fixtures using the audited N03 helpers."""
import json, hashlib
from pathlib import Path
import scene_helpers as B

H=Path(__file__).resolve().parent
M=json.loads((H/'manifest.json').read_text())
C=H/M['candidate']['file']
plan=[
 {'file':'01-upright-isolated','kind':'grape','count':64,'indices':[0],'tilt':None},
 {'file':'02-upright-helper-boundaries','kind':'grape','count':64,'indices':[0,7,8,63],'tilt':None},
 {'file':'03-north-tilt-layers','kind':'grape','count':64,'indices':[0,63],'tilt':0},
 {'file':'04-east-tilt-layers','kind':'grape','count':64,'indices':[0,63],'tilt':1},
 {'file':'05-animated-ice-grape-tick1','kind':'ice_grape','count':1,'indices':[0],'tilt':None},
]
for case in plan:
    sc=B.Scene(case['file']+' | SOURCE X=-24 BEFORE X=0 AFTER X=24')
    for index in case['indices']:
        for variant,x in [('source',-24),('before',0),('after',24)]:
            B.add_item(sc,'pressing_tub',case['kind'],index,0,[x,0,0],variant!='source',case['tilt'],case['count'],C if variant=='after' else None)
            g=sc.j['groups'][-1];g['name']=f'{variant.upper()} {case["kind"]} global={index} helper={index//8} local={index%8} tilt={case["tilt"]}'
            e=sc.j['elements'][-1];e['name']=g['name'];e['_review']['variant']=variant
    sc.j['_review']={'fixture_only':True,'front_sides_are_editor_hints':True,'actual_BP_execution':False,'item_scene_offsets':{'source':[-24,0,0],'before':[0,0,0],'after':[24,0,0]},'source_native_reference_frames_differ':True,'body_clearance_not_tested':True,'candidate_sha256':M['candidate']['after_sha256']}
    sc.save(case['file'],[case['file']])
sc=B.Scene('06 controls | unchanged barrel card and pressing cube')
for machine,kind,z in [('barrel','grape',0),('pressing_tub','stone',44)]:
    for variant,x in [('source',-24),('before',0),('after',24)]:
        B.add_item(sc,machine,kind,0,0,[x,0,z],variant!='source',None,1)
        sc.j['groups'][-1]['name']=f'{variant.upper()} UNCHANGED CONTROL {machine} {kind}'
        sc.j['elements'][-1]['_review']['variant']=variant
        sc.j['elements'][-1]['name']=sc.j['groups'][-1]['name']
sc.j['_review']={'fixture_only':True,'front_sides_are_editor_hints':True,'actual_BP_execution':False,'source_native_reference_frames_differ':True,'before_after_controls_identical_except_scene_x':True}
sc.save('06-unchanged-controls',['barrel-grape','pressing-stone-neutral-texture'])
M['scenes']=B.M['scenes'];M['scene_plan']=plan;M['derived_textures']=B.M['derived_textures']
M['helper_provenance']={name:hashlib.sha256((H/name).read_bytes()).hexdigest() for name in ['scene_helpers.py','audit_helpers.py']}
(H/'manifest.json').write_text(json.dumps(M,indent=2)+'\n')
print('Built',len(M['scenes']),'bounded fixtures; no GUI performed')
