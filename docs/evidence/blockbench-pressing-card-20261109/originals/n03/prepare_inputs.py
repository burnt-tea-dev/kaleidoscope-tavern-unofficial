from pathlib import Path
import subprocess,json,hashlib,zipfile
H=Path(__file__).resolve().parent;W=H.parent;R=W/'tavern-bottles-publication-20261109';J=W/'tavern-visual-review-20261108/java-reference'
MAIN='1bd3d70f94d142630b05a655008a296bc0bcd387';F='c4ec1880bd44cf3139d3ba744ab30bb379cf1416';N='a1afba34981a00e89d57130d3dc8f1e64f1820a2';MAN={'canonical':MAIN,'runtime_tree':'38c5977dd6bfe14b1824734612e3c601e1e41028','version':'0.6.213','forge':F,'neoforge':N,'inputs':{}}
sha=lambda b:hashlib.sha256(b).hexdigest()
def save(dst,b,owner,orig):
 p=H/dst;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);MAN['inputs'][dst]={'sha256':sha(b),'bytes':len(b),'owner':owner,'original_path':orig}
def git(r,*a):return subprocess.check_output(['git','-C',str(r),*a])
assert git(R,'rev-parse',MAIN+':runtime').decode().strip()==MAN['runtime_tree']
heads=git(J,'ls-remote','origin','refs/heads/main','refs/heads/1.21.1').decode();assert F in heads and N in heads
save('upstream-refresh.txt',heads.encode(),'live refs','KaleidoscopeMods/KaleidoscopeTavern')
paths=git(R,'ls-tree','-r','--name-only',MAIN).decode().splitlines()
for p in paths:
 relevant=(p.startswith('runtime/') and (any(x in p for x in ['liquid','ingredient','rig_liquid','runtime_pressing_']) or p.endswith(('scripts/bedrock/machines.js','scripts/core/machine-visuals.js','scripts/data/fluids.js','render_controllers/static.render_controllers.json')))) or p in ['data/liquid-surface-source.json','data/liquid-surface-source/water.png.mcmeta','data/liquid-surface-source/lava.png.mcmeta','runtime/RP/materials/kt_animated.material']
 if relevant:save('inputs/current/'+p,git(R,'show',MAIN+':'+p),MAIN,p)
# Every active helper and animation copied above. Resolve texture paths actually referenced.
for ep in (H/'inputs/current/runtime/RP/entity').glob('*.json'):
 d=json.loads(ep.read_text())['minecraft:client_entity']['description']
 for t in d.get('textures',{}).values():
  p='runtime/RP/'+t+'.png'
  if p in paths:save('inputs/current/'+p,git(R,'show',MAIN+':'+p),MAIN,p)
for p in paths:
 if p.startswith('runtime/RP/materials/'):
  save('inputs/current/'+p,git(R,'show',MAIN+':'+p),MAIN,p)
java=['client/render/block/BarrelBlockEntityRender.java','client/render/block/PressingTubBlockEntityRender.java','util/RenderUtils.java','fluid/JuiceFluidType.java','init/ModFluids.java','api/blockentity/IBarrel.java','api/blockentity/IPressingTub.java']
for pin,branch in [(F,'forge'),(N,'neoforge')]:
 for p in java:
  path='src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/'+p;save('inputs/'+branch+'/'+path,git(J,'show',pin+':'+path),pin,path)
 for p in ['models/item/grape.json','models/item/ice_grape.json']:
  path='src/generated/resources/assets/kaleidoscope_tavern/'+p;save('inputs/'+branch+'/'+path,git(J,'show',pin+':'+path),pin,path)
 for p in ['textures/item/grape.png','textures/item/ice_grape.png','textures/item/ice_grape.png.mcmeta','textures/block/grape_juice_still.png']:
  path='src/main/resources/assets/kaleidoscope_tavern/'+p;save('inputs/'+branch+'/'+path,git(J,'show',pin+':'+path),pin,path)
for ver,jp,expected in [('1.20.1',W/'otc-dishwasher-material-audit-20261108/evidence/java-1.20.1-client.jar','0c3ec587af28e5a785c0b4a7b8a30f9a8f78f838'),('1.21.1',W/'tavern-wild-vine-review-20261109/official-parent-source/java-1.21.1-client-data.jar','30c73b1c5da787909b2f73340419fdf13b9def88')]:
 b=jp.read_bytes();assert hashlib.sha1(b).hexdigest()==expected;MAN.setdefault('official_archives',{})[ver]={'sha1':expected,'sha256':sha(b),'executed':False,'input_path':str(jp)}
 with zipfile.ZipFile(jp)as z:
  for p in ['models/item/generated.json','models/item/ice.json','models/block/ice.json','models/item/stone.json','models/block/stone.json','models/block/cube_all.json','models/block/cube.json','models/block/block.json','textures/block/ice.png','textures/block/stone.png','textures/block/water_still.png','textures/block/lava_still.png','textures/block/water_still.png.mcmeta','textures/block/lava_still.png.mcmeta']:
   path='assets/minecraft/'+p;save('inputs/mojang-'+ver+'/'+path,z.read(path),expected,path)
  if ver=='1.20.1':
   for c in ['fkz','fkz$1','fkz$a','fkz$b','fpw','flc','fkv']:
    save('inputs/mojang-bytecode/'+c+'.class',z.read(c+'.class'),expected,c+'.class')
for file in ['scenes/barrel-open.bbmodel','scenes/pressing-tubs.bbmodel','ordered-face-world-audit.json','manifest.json','codec-provenance.json','review_codec.py']:
 p=W/'tavern-machine-body-review-20261109'/file;save('inputs/n02/'+file,p.read_bytes(),'N02 verified body preparation',file)
# Prior public evidence scope only, not machine acceptance.
prior=[]
for p in paths:
 if p.startswith('docs/evidence/') and p.endswith('README.md'):
  t=git(R,'show',MAIN+':'+p).decode(); hits=[l for l in t.splitlines() if any(s in l.lower() for s in ['barrel','pressing','ingredient','liquid'])]
  if hits:prior.append({'path':p,'sha256':sha(t.encode()),'relevant_lines':hits})
MAN['prior_evidence_scope']=prior
(H/'manifest.json').write_text(json.dumps(MAN,indent=2)+'\n')
print('Inputs:',len(MAN['inputs']))
