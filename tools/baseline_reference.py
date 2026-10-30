"""Test-only view of the last reviewed baseline, with exact current/preimage hashes.

Legacy preservation guards keep their original assertions. The new canonical
baseline gate and functional regressions check the reconciled runtime separately.
Never use this projection in packaging or deployment.
"""
from pathlib import Path
import base64,gzip,hashlib,json,subprocess
from functools import lru_cache
from collision_shape_projection import collision_preimage
from current_extension_source_contract import check as check_current_extensions, runtime_sources as extension_runtime_sources
from cultivation_source_contract import check as check_cultivation, runtime_sources as cultivation_runtime_sources

# Only exact reviewed non-script assets and opt-in command entry points.
# T134 visual semantics are checked by the board, source-texel and animation
# generators; no directory wildcard admits unrelated resources or functions.
# New arbitrary blocks/UI/locales are not admitted by a directory wildcard.
COCKTAIL_ASSET_PATHS=frozenset({
 'runtime/BP/blocks/'+name+'.json' for name in (
  'cup_allium_garden','cup_bloody_mary','cup_brass_heart','cup_depth_charge',
  'cup_emerald','cup_empty_glassware','cup_godfather','cup_grasshopper',
  'cup_mojito','cup_mystery_cocktail','cup_nether_special','cup_screwdriver',
  'cup_sculk_special','cup_signature_cocktail','cup_white_lady','shaker_station')
}|{'runtime/RP/texts/languages.json',
   'runtime/RP/ui/hud_screen.json',
   'runtime/RP/ui/_global_variables.json',
   'runtime/RP/ui/kt_tavern_hud.json',
   'runtime/RP/ui/server_form.json',
   'runtime/RP/manifest.json',
   'runtime/BP/items/depth_charge.json',
   'runtime/BP/items/mystery_cocktail.json',
   'runtime/BP/items/nether_special.json',
   'runtime/BP/items/ice_grape.json',
   'runtime/BP/items/shaker.json',
   'runtime/RP/attachables/shaker.attachable.json',
   'runtime/RP/attachables/shaker_active.attachable.json',
   'runtime/RP/attachables/shaker_pouring.attachable.json',
   'runtime/RP/textures/terrain_texture.json',
   'runtime/RP/animations/board_glyph_line.animation.json',
   'runtime/RP/entity/board_glyph_visual.entity.json',
   'runtime/RP/entity/rig_signature_color.entity.json',
   'runtime/RP/entity/runtime_pressing_tub_ingredients.entity.json',
   'runtime/RP/entity/runtime_pressing_tub_ingredients_1.entity.json',
   'runtime/RP/entity/runtime_pressing_tub_ingredients_2.entity.json',
   'runtime/RP/entity/runtime_pressing_tub_ingredients_3.entity.json',
   'runtime/RP/entity/runtime_pressing_tub_ingredients_4.entity.json',
   'runtime/RP/entity/runtime_pressing_tub_ingredients_5.entity.json',
   'runtime/RP/entity/runtime_pressing_tub_ingredients_6.entity.json',
   'runtime/RP/entity/runtime_pressing_tub_ingredients_7.entity.json',
   'runtime/RP/entity/runtime_signature_cup.entity.json',
   'runtime/RP/models/entity/board_glyph_line.geo.json',
   'runtime/RP/render_controllers/board_glyph_visual.render_controllers.json',
   'runtime/RP/render_controllers/runtime_pressing_ingredients.render_controllers.json',
   'runtime/RP/render_controllers/signature_tint.json',
   'runtime/BP/functions/kt_tipsy_motion_off.mcfunction',
   'runtime/BP/functions/kt_tipsy_motion_on.mcfunction'})

# T158: exact eight incense blocks and their two shared geometries.
INCENSE_ASSET_PATHS=frozenset({'runtime/BP/blocks/'+kind+'_incense.json'
 for kind in ('butterfly','catnip','firefly','ginkgo','pine','sakura','snow','spore')}
 |{'runtime/RP/models/entity/incense_closed.geo.json',
   'runtime/RP/models/entity/incense_open.geo.json'})

ANIMATED_SPRITE_ASSET_PATHS=frozenset('runtime/RP/models/entity/item_sprite_'+name+'.geo.json'
 for name in ('depth_charge','mystery_cocktail','nether_special','ice_grape'))

# W145: four exact source-backed freezer sprite routes. Only frame selection,
# material binding and strip dimensions change; PNG changes are bound to the
# selected original Java water/lava sources. No wildcard admits other assets.
FREEZER_SURFACE_ASSET_PATHS=frozenset(
 'runtime/RP/'+pattern.format(kind=kind)
 for kind in ('water','lava','milk_still','magma')
 for pattern in ('entity/freezer_{kind}.entity.json',
                 'render_controllers/freezer_{kind}.json',
                 'models/entity/freezer_{kind}.geo.json')
)|frozenset('runtime/RP/textures/repair/freezer_'+kind+'.png'
 for kind in ('water','lava'))

# Tavern's four known liquid helpers use the original Java water/lava strips.
# Lava's source strip has twenty frames; only its two exact UV descriptions
# change height. Preserve all surface geometry, tint and level animation.
LIQUID_SURFACE_ASSET_PATHS=frozenset(
 'runtime/RP/entity/liquid_'+family+'_'+kind+'.entity.json'
 for family in ('barrel','pressing_tub') for kind in ('water','lava')
)|frozenset('runtime/RP/'+pattern.format(kind=kind)
 for kind in ('water','lava')
 for pattern in ('render_controllers/liquid_{kind}.json','textures/repair/{kind}.png')
)|frozenset('runtime/RP/models/entity/liquid_'+family+'_lava.geo.json'
 for family in ('barrel','pressing_tub')
)|frozenset({'runtime/RP/materials/entity.material'})

T169_PATH='runtime/RP/ui/kt_tavern_hud.json'
T169_BEFORE='1c09a9735eba14b03137ebbb852fcf54ec9c4e04'
T169_AFTER='08ccd47b93dc60dd0b935a8d5e812d4195858e9d'
T176_BEFORE='2810a59c08e52004bb69522a8900a8da1dcc2c16'
T176_AFTER='fd791c0faa839b4317e7e07ad332b97c34ad9758'
T176_PATHS=frozenset('runtime/BP/scripts/'+name for name in (
 'bedrock/bottles.js','bedrock/display-projectiles.js','bedrock/machines.js',
 'core/bottle-display-schema.js','core/extension-content.js',
 'core/native-storage-anchor.js','core/registry.js'))

# Public history was rewritten without changing these complete runtime trees.
# Keep the historical review IDs/ledger intact; bind each replacement to the
# exact original runtime tree instead of accepting a moving branch or HEAD.
HISTORICAL_RUNTIME_ALIASES = {
 '1c09a9735eba14b03137ebbb852fcf54ec9c4e04': ('b28cbe72dc96d2b8fae3c8a33cb5e1a2fe6cde02', '464000530cfe99e233010fb5da5e3e7a069756c5'),
 '08ccd47b93dc60dd0b935a8d5e812d4195858e9d': ('bb87a87e1f9061d1f1b0de215f4639739d672fb3', 'b5dbb4b44a63a1e25784227a84e34e6fc5c1faf2'),
 '2810a59c08e52004bb69522a8900a8da1dcc2c16': ('ac65c09d31fddfc33032a6045f59bb7d62c18819', '6b5cefe874a2bfd8aaf0269944d315549868447b'),
 'fd791c0faa839b4317e7e07ad332b97c34ad9758': ('91cf818d62feec806817d4e0c4c17f79573c2d28', 'cbb2be14a78294983cd82de00646de769478ab96'),
}

@lru_cache(maxsize=24)
def historical_runtime_source(root,commit,name):
 assert commit in HISTORICAL_RUNTIME_ALIASES and name in T176_PATHS|{T169_PATH}, 'Outside the immutable runtime history'
 replacement,expected_tree=HISTORICAL_RUNTIME_ALIASES[commit]
 actual=subprocess.check_output(['git','rev-parse',replacement+':runtime'],cwd=root,text=True).strip()
 assert actual==expected_tree, 'Historical runtime alias tree differs'
 return subprocess.check_output(['git','show',replacement+':'+name],cwd=root)

@lru_cache(maxsize=16)
def t176_source(root,commit,name):
 assert commit in (T176_BEFORE,T176_AFTER) and name in T176_PATHS,'Outside the T176 reviewed source edge'
 return historical_runtime_source(root,commit,name)

def t176_preimage(root,name,data):
 # Exact immutable Orchard quality-block/storage and unloaded-projectile repairs.
 # Leave the old ledger and all its older preimages intact. Actual T176 behavior
 # is exercised by current-source tests, never this test-only historical view.
 if Path(root).resolve()!=Path(__file__).resolve().parents[1] or name not in T176_PATHS:return data
 before,after=(t176_source(str(root),commit,name) for commit in (T176_BEFORE,T176_AFTER))
 assert data in (before,after),('Unreviewed T176 source postimage',name)
 return before

@lru_cache(maxsize=4)
def t169_source(root,commit):
 assert commit in (T169_BEFORE,T169_AFTER)
 return historical_runtime_source(root,commit,T169_PATH)

def reverse_t169_delta(root,name,data,row):
 """Only the frozen three-field HUD repair may cross this historical edge."""
 assert name==T169_PATH
 before,after=(t169_source(str(root),commit) for commit in (T169_BEFORE,T169_AFTER))
 assert data==after,('T169 immutable postimage differs',name)
 assert row['before']==hashlib.sha256(before).hexdigest() and row['after']==hashlib.sha256(after).hexdigest(), 'T169 immutable source identities differ'
 restored=gzip.decompress(base64.b64decode(row['beforeGzipBase64'],validate=True))
 assert restored==before,('T169 immutable predecessor differs',name)
 return restored

@lru_cache(maxsize=4)
def rows(root):
 p=Path(root)/'data/baseline-reconciliation.json'
 return json.loads(p.read_text())['files'] if p.exists() else {}
@lru_cache(maxsize=4)
def release_projections(root):
 p=Path(root)/'data/baseline-reconciliation.json'
 return json.loads(p.read_text()).get('releaseVersionProjections',{}) if p.exists() else {}
@lru_cache(maxsize=4)
def functional_rows(root):
 p=Path(root)/'data/baseline-reconciliation.json'
 if not p.exists():return {}
 ledger=json.loads(p.read_text());reviews=ledger.get('reviewedFunctionalDeltas',{})
 if reviews:assert ledger.get('schema')==1 and ledger.get('testOnly') is True,'Unsupported functional review ledger'
 return reviews
@lru_cache(maxsize=4)
def functional_layers(root):
 p=Path(root)/'data/baseline-reconciliation.json'
 if not p.exists():return []
 ledger=json.loads(p.read_text());layers=ledger.get('reviewedFunctionalDeltaLayers',[])
 if layers:assert ledger.get('schema')==1 and ledger.get('testOnly') is True,'Unsupported functional review ledger'
 assert isinstance(layers,list),'Unsupported functional review layers'
 for layer in layers:
  assert isinstance(layer.get('release'),str) and layer['release'].strip()
  assert isinstance(layer.get('files'),dict) and layer['files']
 return layers
@lru_cache(maxsize=4)
def asset_layers(root):
 p=Path(root)/'data/baseline-reconciliation.json'
 if not p.exists():return []
 ledger=json.loads(p.read_text());layers=ledger.get('reviewedAssetDeltaLayers',[])
 if layers:assert ledger.get('schema')==1 and ledger.get('testOnly') is True,'Unsupported asset review ledger'
 assert isinstance(layers,list),'Unsupported asset review layers'
 for layer in layers:
  assert isinstance(layer.get('release'),str) and layer['release'].strip()
  assert isinstance(layer.get('files'),dict) and layer['files']
  assert set(layer['files'])<=(COCKTAIL_ASSET_PATHS|INCENSE_ASSET_PATHS|ANIMATED_SPRITE_ASSET_PATHS|frozenset({'runtime/BP/blocks/xp_bottle.json','runtime/RP/models/entity/item_display_tilted_rack.geo.json'})|FREEZER_SURFACE_ASSET_PATHS|LIQUID_SURFACE_ASSET_PATHS),'Unsupported reviewed asset path'
  if layer['release']=='0.6.169':
   assert set(layer['files'])=={T169_PATH},'T169 review scope differs'
   assert layer['reviewedPredecessorCommit']==T169_BEFORE and layer['reviewedSourceCommit']==T169_AFTER,'T169 immutable review commits differ'
 return layers
def asset_projection(root,name,data):
 # Minified HUD JSON is one large line. Preserve its exact compressed prior
 # bytes instead of broad JSON transforms or changing the historical witness.
 for layer in reversed(asset_layers(root)):
  row=layer['files'].get(name)
  if not row:continue
  assert isinstance(row['reason'],str) and row['reason'].strip()
  assert row['before'] is not None and row['before']!=row['after']
  if layer['release']=='0.6.169':
   data=reverse_t169_delta(root,name,data,row)
   continue
  assert hashlib.sha256(data).hexdigest()==row['after'],('Reviewed asset source mutated',name)
  restored=gzip.decompress(base64.b64decode(row['beforeGzipBase64'],validate=True))
  assert hashlib.sha256(restored).hexdigest()==row['before'],('Asset predecessor mismatch',name)
  data=restored
 return data
def reverse_functional_delta(name,data,row):
 """Reverse only an exact reviewed delta before the unchanged old guards.

 This view is test-only. It never writes historical gameplay into runtime.
 """
 assert (name.startswith('runtime/BP/scripts/') or name=='runtime/RP/animations/runtime_shaker.animation.json') and isinstance(row['reason'],str) and row['reason'].strip()
 assert row['before']!=row['after']
 assert hashlib.sha256(data).hexdigest()==row['after'],('Reviewed functional source mutated',name)
 lines=data.decode('utf-8').splitlines(keepends=True);ops=row['reverseOps']
 assert ops,('Missing functional reverse delta',name)
 previous_end=-1
 for start,end,replacement in ops:
  assert type(start) is int and type(end) is int and isinstance(replacement,str)
  assert 0<=start<=end<=len(lines) and start>=previous_end,('Invalid functional reverse delta',name)
  previous_end=end
 for start,end,replacement in reversed(ops):lines[start:end]=[replacement]
 restored=''.join(lines).encode('utf-8')
 assert hashlib.sha256(restored).hexdigest()==row['before'],('Functional predecessor mismatch',name)
 return restored
def functional_projection(root,name,data):
 # New reviews append to the ledger. Resolve newest-to-oldest without rewriting
 # any earlier review, then apply the original functional and baseline guards.
 for layer in reversed(functional_layers(root)):
  row=layer['files'].get(name)
  if row:data=reverse_functional_delta(name,data,row)
 row=functional_rows(root).get(name)
 return reverse_functional_delta(name,data,row) if row else data
def version_projection(root,name,data,spec):
 current=json.loads((root/'package.json').read_text())['version']
 assert current==json.loads((root/'release.json').read_text())['version']
 version=list(map(int,current.split('.')))
 assert version==json.loads((root/'baseline.json').read_text())['version']
 kind=spec['kind']
 if kind=='owned_manifest':
  value=json.loads(data);assert value['header']['version']==version
  value['header']['version']=spec['reviewedVersion']
  for module in value['modules']:
   assert module['version']==version;module['version']=spec['reviewedVersion']
  for dependency in value.get('dependencies',[]):
   if dependency.get('uuid') in spec['ownedUuids']:
    assert dependency['version']==version;dependency['version']=spec['reviewedVersion']
  return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
 if kind=='payload_version':
  old=('"version": '+json.dumps(current)).encode()
  new=('"version": '+json.dumps(spec['reviewedVersion'])).encode()
 elif kind=='build_identity':
  old=("BUILD_VERSION='"+current+"-baseline.1'").encode()
  new=("BUILD_VERSION='"+spec['reviewedVersion']+"-baseline.1'").encode()
 else:raise AssertionError('Unsupported reviewed version projection')
 assert data.count(old)==1,(name,'ambiguous/unbound release identity')
 return data.replace(old,new,1)

def previous_bytes(root,path):
 root=Path(root).resolve();path=Path(path).resolve();name=path.relative_to(root).as_posix();data=path.read_bytes();row=rows(root).get(name)
 # Current extension owners are checked against their live wiring and behavior
 # suites. Their bodies no longer participate in the historical source view.
 if root==Path(__file__).resolve().parents[1] and name in extension_runtime_sources():
  check_current_extensions(root,syntax=False,localization=False)
  return data
 if root==Path(__file__).resolve().parents[1] and name in cultivation_runtime_sources():
  check_cultivation(root,syntax=False)
  return data
 data=t176_preimage(root,name,data)
 data=collision_preimage(root,name,data)
 # Bind and normalize the current release identity before any body delta.
 # This keeps a reviewed guide-body change separate from later pure version
 # bumps while retaining all existing version/dependency assertions.
 spec=release_projections(root).get(name)
 if spec:data=version_projection(root,name,data,spec)
 data=asset_projection(root,name,data)
 data=functional_projection(root,name,data)
 if not row:return data
 assert hashlib.sha256(data).hexdigest()==row['after'],('Reconciled source mutated',name)
 if row['before'] is None:return data
 original=gzip.decompress(base64.b64decode(row['beforeGzipBase64'])) if 'beforeGzipBase64' in row else row['beforeContent'].encode()
 assert hashlib.sha256(original).hexdigest()==row['before'],('Baseline preimage corrupt',name)
 return original
def additions(root):return {name for name,row in rows(root).items() if row['before'] is None}
