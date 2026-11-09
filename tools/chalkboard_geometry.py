"""Current chalkboard resource contract. Canonical JSON is the authoring owner.

The old rebuild_java_wall_decor.py lives only in archived pre-release history.
This validator independently reconstructs ModelPart surfaces and the official
Bedrock cube decode, without changing exporters or unrelated models. Standard
library only: baseline and identity checks must not require pixel libraries.
"""
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'data/chalkboard-source'
BLOCK = 'runtime/BP/blocks/chalkboard.json'
TERRAIN = 'runtime/RP/textures/terrain_texture.json'
JA = 'src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/'
AS = 'src/main/resources/assets/kaleidoscope_tavern/'
N = 'kaleidoscope_tavern:'


def read(path):
    return json.loads(path.read_text(), parse_constant=lambda s: (_ for _ in ()).throw(AssertionError('Nonfinite JSON')))


def runtime_sources():
    return frozenset(f'runtime/RP/models/entity/java_chalk_{size}_{panel}_{half}.geo.json'
                     for size, count in [('small', 1), ('large', 3)]
                     for panel in range(count) for half in range(2))


def resource_paths():
    return runtime_sources() | {BLOCK, TERRAIN, 'data/baseline-reconciliation.json',
                                'data/launch-repair-reference.json'} | {
        f'runtime/RP/textures/kaleidoscope_tavern_jar/entity/deco/{size}_chalkboard.png'
        for size in ('small', 'large')}


def nums(text):
    return [float(x.rstrip('F')) for x in re.findall(r'-?\d+(?:\.\d+)?F?', text)]


def source_contract(root, branch, size):
    base = root / SOURCE / branch
    text = (base / (JA + f'client/model/deco/{size.title()}ChalkboardModel.java')).read_text()
    assert '.mirror(' not in text and 'new CubeDeformation(0.0F)' in text
    assert 'texOffs(0, 0)' in text and 'RenderType::entityCutoutNoCull' in text
    assert 'root.getChild("bone")' in text
    box = nums(re.search(r'addBox\((.*?)new CubeDeformation', text)[1])
    offset = nums(re.search(r'PartPose.offset\((.*?)\)', text)[1])
    dimensions = nums(re.search(r'LayerDefinition.create\(meshdefinition, (.*?)\)', text)[1])
    assert box == ([-16, -30, 15, 16, 28, 1] if size == 'small' else [-32, -30, 15, 48, 28, 1])
    assert offset == [8, 24, -8] and dimensions == ([64, 64] if size == 'small' else [128, 64])
    renderer = (base / (JA + 'client/render/block/ChalkboardBlockEntityRender.java')).read_text()
    for s in ('SmallChalkboardModel(context.bakeLayer(SmallChalkboardModel.LAYER_LOCATION))',
              'SmallChalkboardModel(context.bakeLayer(LargeChalkboardModel.LAYER_LOCATION))'):
        assert s in renderer
    body = renderer.split('protected void renderModel')[1].split('protected void renderText')[0]
    for s in ('poseStack.translate(0.5, 1.5, 0.5)', 'Axis.ZN.rotationDegrees(180)',
              'Axis.YN.rotationDegrees(180 - facing.get2DDataValue() * 90)',
              'RenderType.entityCutoutNoCull(LARGE_TEXTURE)', 'RenderType.entityCutoutNoCull(SMALL_TEXTURE)'):
        assert s in body
    assert '1.0F, 1.0F, 1.0F, 1.0F' in body if branch == 'forge' else '-1' in body
    return box, offset, dimensions


def add(a, b): return [x+y for x, y in zip(a, b)]
def sub(a, b): return [x-y for x, y in zip(a, b)]
def dot(a, b): return sum(x*y for x, y in zip(a, b))
def norm(a): return math.sqrt(dot(a, a))
def rotate(p, angle, axis):
    p = list(p)
    i, j = {'y': (2, 0), 'z': (0, 1)}[axis]
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    p[i], p[j] = p[i]*c-p[j]*s, p[i]*s+p[j]*c
    return p


def source_faces(contract, facing):
    box, offset, _ = contract
    x, y, z, w, h, d = box
    X, Y, Z = x+w, y+h, z+d
    vs = [[x,y,z],[X,y,z],[X,Y,z],[x,Y,z],[x,y,Z],[X,y,Z],[X,Y,Z],[x,Y,Z]]
    table = [([5,4,0,1], [d,0,d+w,d]), ([2,3,7,6], [d+w,d,d+2*w,0]),
             ([0,4,7,3], [0,d,d,d+h]), ([1,0,3,2], [d,d,d+w,d+h]),
             ([5,1,2,6], [d+w,d,2*d+w,d+h]), ([4,5,6,7], [2*d+w,d,2*d+2*w,d+h])]
    out = []
    for indices, (u,v,U,V) in table:
        points = [add(rotate(rotate(add(vs[i], offset), -(180-{'north':2,'east':3}[facing]*90), 'y'), -180, 'z'), [0,24,0]) for i in indices]
        out.append((points, [[U,v],[u,v],[u,V],[U,V]]))
    return out


def native_faces(cube, corners, panel, half, size, facing, yaw):
    origin, dims = cube['origin'], cube['size']
    lo = [-origin[0]-dims[0], origin[1], origin[2]]
    hi = add(lo, dims)
    pos = 0 if size == 'small' else 3-panel
    lateral = (pos-2)*16 if size == 'large' else 0
    offset = [lateral, half*16, 0] if facing == 'north' else [0, half*16, lateral]
    out = []
    for side, face in cube['uv'].items():
        ps = [[{'from':lo, 'to':hi}[name][int(axis)] for name, axis in corner] for corner in corners[side]]
        u,v = face['uv']; du,dv = face['uv_size']
        a,b,U,V = [u+du,v+dv,u,v] if side in ('up','down') else [u,v,u+du,v+dv]
        us = [[a,b],[U,b],[a,V],[U,V]]
        out.append(([add(rotate(ps[i], yaw, 'y'), offset) for i in (0,2,3,1)], [us[i] for i in (0,2,3,1)]))
    return out


def verify_surfaces(source, native):
    areas = [0.] * len(source)
    for points, uv in native:
        matches = []
        for i, (ps, us) in enumerate(source):
            e, f = sub(ps[1], ps[0]), sub(ps[3], ps[0])
            pairs = [(dot(sub(p, ps[0]), e)/dot(e,e), dot(sub(p, ps[0]),f)/dot(f,f)) for p in points]
            if any(min(a,b)<-1e-8 or max(a,b)>1+1e-8 for a,b in pairs): continue
            if any(norm(sub(p, [ps[0][k]+a*e[k]+b*f[k] for k in range(3)]))>1e-8 for p,(a,b) in zip(points,pairs)): continue
            expected = [[us[0][k]+a*(us[1][k]-us[0][k])+b*(us[3][k]-us[0][k]) for k in range(2)] for a,b in pairs]
            if max(abs(a-b) for p,q in zip(uv,expected) for a,b in zip(p,q))<1e-8: matches.append(i)
        assert len(matches)==1, 'Face location or directed UV does not match source exterior'
        areas[matches[0]] += norm(sub(points[1],points[0]))*norm(sub(points[3],points[0]))
    expected = [norm(sub(p[1],p[0]))*norm(sub(p[3],p[0])) for p,u in source]
    assert all(abs(a-b)<1e-8 for a,b in zip(areas,expected)), 'Missing/duplicated source exterior'
    return areas


def check(root=ROOT):
    root = Path(root)
    fixture = root / SOURCE
    records = read(fixture/'source.json')
    assert records['source_pins'] == {'Forge':'c4ec1880bd44cf3139d3ba744ab30bb379cf1416', 'NeoForge':'a1afba34981a00e89d57130d3dc8f1e64f1820a2'}
    for name, row in records['files'].items():
        raw = (fixture/name).read_bytes()
        assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'], ('Source fixture changed', name)
    bb = (fixture/'reference/js__formats__bedrock__bedrock.js.txt').read_text()
    for token in ('base_cube.from[0] = -(base_cube.from[0] + s.size[0])', "if (key == 'up' || key == 'down')", 'face.uv = [face.uv[2], face.uv[3], face.uv[0], face.uv[1]]'):
        assert token in bb
    shape = (fixture/'reference/three-shape.official.txt').read_text()
    corners = {}
    for side, tokens in re.findall(r'// (East|West|Up|Down|South|North)\s+position.array.set\(\[([\s\S]*?)\], \d+\)', shape):
        tokens = re.findall(r'(from|to)\[(\d)\]', tokens)
        assert len(tokens)==12
        corners[side.lower()] = [tokens[i:i+3] for i in range(0,12,3)]
    assert len(corners)==6
    mp = (fixture/'reference/ModelPart.java.reference.txt').read_text()
    for token in ('new ModelPart.Vertex[]{var9, var8, var4, var5}, var13, var18, var14, var19',
                  'new ModelPart.Vertex[]{var6, var7, var11, var10}, var14, var19, var15, var18',
                  'param0[0] = param0[0].remap(param3 / param5 - var0, param2 / param6 + var1)'):
        assert token in mp
    block = read(root/BLOCK)['minecraft:block']
    terrain = read(root/TERRAIN)['texture_data']
    assert block['components']['minecraft:geometry']=={'identifier':'geometry.kt_java.chalk_small_0_0'}
    assert len(block['permutations'])==12
    results = {}
    for size, count in [('small',1), ('large',3)]:
        source = source_contract(root,'forge',size)
        assert source == source_contract(root,'neoforge',size)
        texture = f'textures/entity/deco/{size}_chalkboard.png'
        # PNG encoding differs across loaders; pixel parity is checked separately.
        raw = (fixture/'neoforge'/AS/texture).read_bytes()
        binding = terrain[f'kt_assets_a17_chalkboard_{size}']['textures']
        assert binding == f'textures/kaleidoscope_tavern_jar/entity/deco/{size}_chalkboard'
        assert raw == (root/'runtime/RP'/(binding+'.png')).read_bytes()
        all_faces = {f:[] for f in ('north','east')}
        for panel in range(count):
            for half in range(2):
                identifier = f'geometry.kt_java.chalk_{size}_{panel}_{half}'
                model = read(root/f'runtime/RP/models/entity/java_chalk_{size}_{panel}_{half}.geo.json')
                assert not re.search(r'\b(?:true|false|NaN|Infinity)\b', json.dumps(model)), 'Invalid geometry numeric type'
                assert model['format_version']=='1.21.0' and len(model['minecraft:geometry'])==1
                g = model['minecraft:geometry'][0]
                assert g['description']=={'identifier':identifier,'texture_width':source[2][0], 'texture_height':64, 'visible_bounds_width':2,'visible_bounds_height':2,'visible_bounds_offset':[0,.5,0]}
                assert len(g['bones'])==1
                bone = g['bones'][0]
                assert set(bone)=={'name','pivot','cubes'} and bone['name']=='root' and bone['pivot']==[0,0,0] and len(bone['cubes'])==1
                cube = bone['cubes'][0]
                assert set(cube)=={'origin','size','uv'} and cube['origin']==[-8,2 if half==0 else 0,7] and cube['size']==[16,14,1]
                assert set(cube['uv']) <= set(corners), 'Unknown face'
                for face in cube['uv'].values():
                    assert set(face)=={'uv','uv_size'}
                    assert all(len(face[k])==2 and all(type(n) in (int,float) and math.isfinite(n) for n in face[k]) for k in face)
                pos = 0 if size=='small' else 3-panel
                condition = f"q.block_state('{N}position') == {pos} && q.block_state('{N}half') == {half}"
                perm = next(p['components'] for p in block['permutations'] if p['condition']==condition)
                box = {'origin':[-8,2 if half==0 else 0,7], 'size':[16,14,1]}
                assert perm=={'minecraft:geometry':{'identifier':identifier},'minecraft:material_instances':{'*':{'texture':f'kt_assets_a17_chalkboard_{size}','render_method':'alpha_test'}},'minecraft:collision_box':box,'minecraft:selection_box':box}
                for facing, yaw in [('north',0),('east',270)]:
                    rotation = next(p['components'] for p in block['permutations'] if p['condition']==f"q.block_state('minecraft:cardinal_direction') == '{facing}'")
                    assert rotation=={'minecraft:transformation':{'rotation':[0,yaw,0]}}
                    all_faces[facing] += native_faces(cube,corners,panel,half,size,facing,yaw)
        for facing, faces in all_faces.items():
            results[size+'_'+facing] = verify_surfaces(source_faces(source,facing),faces)
    identifiers = {'geometry.kt_java.' + Path(p).name.removeprefix('java_').removesuffix('.geo.json') for p in runtime_sources()}
    consumers = set()
    for folder in ('BP/blocks', 'RP/entity', 'RP/attachables'):
        for path in (root/'runtime'/folder).glob('*.json'):
            if any(identifier in path.read_text() for identifier in identifiers):
                consumers.add(path.relative_to(root).as_posix())
    assert consumers == {BLOCK}, ('Chalkboard route ownership changed', consumers)
    # Retire this domain's old source projections, not an inverse repair ledger.
    ledger = read(root/'data/baseline-reconciliation.json')
    for section in ('files','reviewedFunctionalDeltas'):
        assert not runtime_sources() & set(ledger.get(section,{}))
    for section in ('reviewedFunctionalDeltaLayers','reviewedAssetDeltaLayers'):
        for layer in ledger.get(section,[]): assert not runtime_sources() & set(layer['files'])
    launch = read(root/'data/launch-repair-reference.json')
    for section in ('reviewedChanges','newRuntimeFiles'):
        assert not runtime_sources() & set(launch.get(section,{}))
    return {'slices':8,'cardinal_representatives':['north','east'],'source_exterior_areas':results,
            'source_mirror':False,'engine_verified':False,'bottom_v_visual_proof':False}


if __name__ == '__main__':
    print(json.dumps(check(),indent=2))
