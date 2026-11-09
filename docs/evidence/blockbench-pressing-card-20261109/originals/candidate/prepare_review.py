"""Offline, bounded snapshot and exact minimal candidate. Writes only this directory."""
from pathlib import Path
import ast, copy, hashlib, json, subprocess

H=Path(__file__).resolve().parent
W=H.parent
OLD=W/'tavern-machine-content-review-20261109'
REPO=W/'tavern-wild-vine-repair-20261109'
PIN='682a9dd01cc8d5ad26b714c0b279d04cbafeb205'
TARGET='runtime/RP/models/entity/runtime_pressing_card.geo.json'
sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args])
def write(path,data):
    p=H/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
def dump(path,value):write(path,(json.dumps(value,indent=2)+'\n').encode())
assert git('rev-parse',PIN+'^{tree}')==git('rev-parse','HEAD^{tree}')
assert not git('status','--porcelain')
prior=json.loads((OLD/'manifest.json').read_text())
M={'canonical':PIN,'canonical_tree':git('rev-parse',PIN+'^{tree}').decode().strip(),'runtime_tree':git('rev-parse',PIN+':runtime').decode().strip(),'shared_checkout_head':git('rev-parse','HEAD').decode().strip(),'version':'0.6.214','forge':prior['forge'],'neoforge':prior['neoforge'],'official_archives':prior['official_archives'],'inputs':{},'prior_preparation':str(OLD),'gui_reviewed':False,'runtime_applied':False,'source_refresh':'Reuses recorded N03 refs. No network refresh in this offline task.'}
for path,info in prior['inputs'].items():
    b=(OLD/path).read_bytes();assert sha(b)==info['sha256']
    if path.startswith('inputs/current/'):
        current=git('show',PIN+':'+info['original_path'])
        assert current==b,('N03 input changed',path)
        info={**info,'owner':PIN,'reused_N03_unchanged':True}
    write(path,b);M['inputs'][path]=info
extra=['runtime/BP/scripts/bedrock/pressing-ingredients.js','runtime/BP/scripts/core/ingredient-layout.js','runtime/BP/scripts/data/pressing-ingredient-visuals.js','runtime/BP/scripts/data/visuals.js','runtime/BP/scripts/bedrock/barrel-ingredients.js','tools/check_machine_ingredient_animation.py','tools/machine_ingredient_animation.py','tools/baseline_reference.py']
paths=git('ls-tree','-r','--name-only',PIN,'runtime').decode().splitlines()
reuse_path=W/'tavern-machine-body-review-20261109/prior-evidence-reuse.json'
reuse=json.loads(reuse_path.read_text())
write('provenance/n02-prior-evidence-reuse.json',reuse_path.read_bytes())
held=[v['file'] for v in reuse['shaker_held']]+[reuse['tilted_rack']['file']]
for p in sorted(set(extra+held)):
    b=git('show',PIN+':'+p);path='inputs/current/'+p;write(path,b)
    M['inputs'][path]={'sha256':sha(b),'bytes':len(b),'owner':PIN,'original_path':p}
M['held_control_paths']=held
M['held_reuse_receipt']={'file':'provenance/n02-prior-evidence-reuse.json','sha256':sha(reuse_path.read_bytes()),'tilted_rack_note':'+6 means accepted first-person Y lift, not six poses.'}
write('provenance/canonical-runtime-tree.txt',git('ls-tree','-r',PIN,'runtime'))
for p in ['build_scenes.py','validate_scenes.py','routing-and-source-audit.json','independent-audit.json','README.md','ItemModelGenerator.bytecode.txt','fkz$1.bytecode.txt','fkz$b.bytecode.txt','manifest.json']:
    b=(OLD/p).read_bytes();write('provenance/n03-'+p,b)
    M.setdefault('provenance',{})['provenance/n03-'+p]={'sha256':sha(b),'original':str(OLD/p)}

original=(H/'inputs/current'/TARGET).read_bytes();doc=json.loads(original);candidate=copy.deepcopy(doc);proposal=[]
for bi,b in enumerate(candidate['minecraft:geometry'][0]['bones']):
    for ci,c in enumerate(b.get('cubes',[])):
        assert c['origin']==[-2,-2,-.125] and c['size']==[4,4,.25]
        assert b['name']==f'item_z_{len(proposal)//2}'
        for field in ('origin','size'):
            before=c[field];after=[v*2 for v in before];c[field]=after
            proposal.append({'json_pointer':f'/minecraft:geometry/0/bones/{bi}/cubes/{ci}/{field}','bone':b['name'],'before':before,'after':after})
assert len(proposal)==16
cb=(json.dumps(candidate,indent=2)+'\n').encode()
write('candidate/'+TARGET,cb)
M['candidate']={'file':'candidate/'+TARGET,'runtime_target':TARGET,'before_sha256':sha(original),'after_sha256':sha(cb),'changed_vectors':16,'changed_scalars':48,'cube_count':8}
dump('changed-field-proposal.json',{'candidate':M['candidate'],'changes':proposal,'preserved':'All other fields, centers, UVs, textures, bones, transforms, controller timing, routes, held assets, versions and metadata remain unchanged.'})

# Reuse only pure current N03 definitions, not its executable scene-generation loops.
text=(OLD/'build_scenes.py').read_text();tree=ast.parse(text)
names={'read','T','Q','scale','apply','quad','Scene','derived','rnd','layout','source_item_quads','add_item'}
parts=[ast.get_source_segment(text,n) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
head='''from pathlib import Path
import json, math, copy, hashlib, base64, io, uuid, re
import numpy as np
from PIL import Image
H=Path(__file__).resolve().parent; I=H/'inputs'; R=I/'current/runtime/RP'; S=I/'forge/src/main/resources/assets/kaleidoscope_tavern'; V=I/'mojang-1.20.1/assets/minecraft'
M={'scenes':[],'derived_textures':[]}
uid=lambda:str(uuid.uuid4()); sha=lambda b:hashlib.sha256(b).hexdigest()
f=lambda x:float(np.float32(x)); mask=(1<<64)-1
location={'x':3,'y':64,'z':-5}; seed=((3&0x3ffffff)<<38)|((-5&0x3ffffff)<<12)|64
'''
helper=head+'\n\n'.join(parts)+'\n'
helper=helper.replace('tilt=None,count=64):','tilt=None,count=64,geometry_override=None):')
helper=helper.replace("gp=R/'models/entity'/f'{stem}.geo.json'", "gp=geometry_override or R/'models/entity'/f'{stem}.geo.json'")
helper=helper.replace("bone=next(b for b in geo['bones']if b.get('cubes'))", "bone=next(b for b in geo['bones']if b.get('cubes') and (machine=='barrel' or b['name']==f'item_z_{index%8}'))")
write('scene_helpers.py',helper.encode())

text=(OLD/'validate_scenes.py').read_text();tree=ast.parse(text)
names={'trans','rot','scl','apply','close','signed64','unsigned64','rng','source_values','properties','expression','native_matrix','face','source_quads'}
parts=[ast.get_source_segment(text,n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
head='''from pathlib import Path
import json, math, struct, re, ast, operator
import numpy as np
from scipy.spatial.transform import Rotation
from PIL import Image
H=Path(__file__).resolve().parent; I=H/'inputs'; R=I/'current/runtime/RP'; V=I/'mojang-1.20.1/assets/minecraft'; S=I/'forge/src/main/resources/assets/kaleidoscope_tavern'
rd=lambda p:json.loads(p.read_text())
f32=lambda n:struct.unpack('f',struct.pack('f',n))[0]
'''
helper=head+'\n\n'.join(parts)+'\n'
# Resolve the actual selected local bone, rather than applying a first-cube template.
helper=helper.replace("name=re.sub(r'_0$',f'_{idx}',name)","name=name")
helper=helper.replace("for b in geo['bones']:\n  name=", "target_name=next(b['name'] for b in geo['bones'] if b.get('cubes') and (a['machine']=='barrel' or b['name']==f'item_z_{idx}'))\n bones={b['name']:b for b in geo['bones']}; needed=set(); cursor=target_name\n while cursor is not None:\n  needed.add(cursor); cursor=bones[cursor].get('parent')\n for b in geo['bones']:\n  if b['name'] not in needed:continue\n  name=")
helper=helper.replace("if b.get('cubes'):target=chain[oldname]@trans(-p);break", "if b.get('cubes') and (a['machine']=='barrel' or b['name']==f'item_z_{idx}'):target=chain[oldname]@trans(-p);break")
write('audit_helpers.py',helper.encode())
dump('manifest.json',M)
print('Prepared',len(M['inputs']),'exact input files; candidate',M['candidate']['after_sha256'])
