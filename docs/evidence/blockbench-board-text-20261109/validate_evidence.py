#!/usr/bin/env python3
"""Offline, read-only validation of N06 evidence. No historical scripts are executed."""
import argparse, base64, gzip, hashlib, json, math, os, re, shutil, stat, struct, sys, uuid, zipfile, zlib
from pathlib import Path, PurePosixPath
MAX_FILE = 16 * 1024 * 1024
MAX_TOTAL = 128 * 1024 * 1024


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def pairs(items):
    out = {}
    for k, v in items:
        require(k not in out, 'duplicate JSON key: ' + k)
        out[k] = v
    return out


def reject_constant(value):
    raise ValueError('nonfinite JSON: ' + value)


def finite(value):
    if isinstance(value, float):
        require(math.isfinite(value), 'nonfinite JSON number')
    elif isinstance(value, dict):
        for v in value.values(): finite(v)
    elif isinstance(value, list):
        for v in value: finite(v)


def loads(data):
    value = json.loads(data, object_pairs_hook=pairs, parse_constant=reject_constant)
    finite(value)
    return value


def read(path):
    return loads(checked_file(path.parent, path.name))


def safe_name(name):
    require(isinstance(name, str) and name and '\\' not in name and ':' not in name and '\x00' not in name, 'invalid path')
    p = PurePosixPath(name)
    require(not p.is_absolute() and all(x not in ('', '.', '..') for x in name.split('/')), 'unsafe path: ' + name)
    require(str(p) == name, 'noncanonical path: ' + name)
    return name


def no_links(path):
    require('..' not in Path(path).parts, 'parent traversal in filesystem path')
    path = Path(path).absolute()
    for p in (path, *path.parents):
        require(not p.is_symlink(), 'symlink path: ' + str(p))
    return path


def overlaps(a, b):
    return a == b or a in b.parents or b in a.parents


def new_output(path, package, repository=None):
    p = no_links(path).resolve()
    for label, root in (('package', package), ('repository', repository)):
        if root is not None:
            require(not overlaps(p, root), 'output overlaps ' + label)
    require(not p.exists(), 'output already exists')
    for parent in p.parents:
        marker = parent / '.git'
        require(not (marker.is_file() or (marker.is_dir() and (marker/'HEAD').is_file())), 'output is inside a Git checkout')
    require(p.parent.is_dir(), 'output parent does not exist')
    return p


def checked_file(root, name):
    p = no_links(root / safe_name(name))
    info = p.lstat()
    require(stat.S_ISREG(info.st_mode), 'missing regular file: ' + name)
    require(info.st_size <= MAX_FILE, 'file exceeds bound: ' + name)
    return p.read_bytes()


def check_bytes(data, entry, label):
    require(len(data) == entry['bytes'] and sha(data) == entry['sha256'], 'size/hash mismatch: ' + label)


def inventory(root, manifest):
    actual = set()
    for p in root.rglob('*'):
        mode = p.lstat().st_mode
        require(not stat.S_ISLNK(mode), 'symlink within package')
        require(stat.S_ISDIR(mode) or stat.S_ISREG(mode), 'nonregular entry within package')
        if stat.S_ISREG(mode): actual.add(p.relative_to(root).as_posix())
    require(actual == set(manifest) | {'artifact-sha256.json'}, 'direct inventory differs')
    for name, entry in manifest.items():
        data = checked_file(root, name)
        check_bytes(data, entry, name)
        if name.endswith(('.json', '.bbmodel')): loads(data)


def extract(root, destination):
    index = read(root / 'archive-entries.json')
    expected = {}
    for m in index['members']:
        name = safe_name(m['path'])
        require(name.startswith(('prep/','supplement/')) and name not in expected, 'duplicate or unexpected member')
        require(m['mode'] == '100644' and 0 <= m['bytes'] <= MAX_FILE, 'unsupported member mode/size')
        expected[name] = m
    require(sum(m['bytes'] for m in expected.values()) <= MAX_TOTAL, 'expanded archive exceeds bound')
    seen, archives = set(), set()
    for archive in index['archives']:
        name = safe_name(archive['path'])
        require(name not in archives, 'duplicate archive')
        archives.add(name)
        data = checked_file(root, name); check_bytes(data, archive, name)
        with zipfile.ZipFile(root / name) as z:
            for member in z.infolist():
                key = safe_name(member.filename)
                require(key not in seen and key in expected, 'duplicate/extra archive member')
                m = expected[key]
                require(m['archive'] == name, 'member in wrong archive')
                require(not member.is_dir() and not member.flag_bits & 1, 'directory/encrypted member')
                mode = member.external_attr >> 16
                require(stat.S_IFMT(mode) in (0, stat.S_IFREG) and not stat.S_ISLNK(mode), 'nonregular archive member')
                require(member.file_size == m['bytes'] and member.file_size <= MAX_FILE, 'invalid expanded size')
                b = z.read(member); check_bytes(b, m, key)
                require(blob(b) == m['git_blob_sha1'], 'Git blob mismatch')
                if key.endswith(('.json', '.bbmodel')): loads(b)
                target = destination / key
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as f: f.write(b)
                seen.add(key)
    require(seen == set(expected), 'missing archive members')
    require(all(m['archive'] in archives for m in expected.values()), 'unknown archive reference')
    return destination / 'prep'


def png(data, alpha=False):
    require(data[:8] == b'\x89PNG\r\n\x1a\n', 'not PNG')
    offset, compressed, dims, done = 8, bytearray(), None, False
    while offset < len(data):
        require(offset + 12 <= len(data), 'truncated PNG')
        n = struct.unpack('>I', data[offset:offset+4])[0]; kind = data[offset+4:offset+8]
        end = offset + 12 + n
        require(end <= len(data), 'truncated PNG chunk')
        body = data[offset+8:offset+8+n]
        require(zlib.crc32(kind + body) & 0xffffffff == struct.unpack('>I', data[end-4:end])[0], 'PNG CRC mismatch')
        if kind == b'IHDR':
            require(dims is None and n == 13, 'invalid PNG IHDR')
            dims = struct.unpack('>IIBBBBB', body)
        if kind == b'IDAT': compressed.extend(body)
        offset = end
        if kind == b'IEND':
            require(n == 0 and offset == len(data), 'PNG trailing payload')
            done = True; break
    require(done and dims and 0 < dims[0] <= 4096 and 0 < dims[1] <= 4096, 'invalid PNG bounds')
    if not alpha: return dims[:2]
    w,h,depth,color,compression,filtering,interlace = dims
    require((depth,color,compression,filtering,interlace) == (8,6,0,0,0), 'atlas must be noninterlaced RGBA8')
    require(w*h <= 1024*1024, 'atlas exceeds bound')
    d = zlib.decompressobj(); raw = d.decompress(bytes(compressed), h*(w*4+1)+1)
    require(d.eof and not d.unused_data and not d.unconsumed_tail and len(raw) == h*(w*4+1), 'PNG stream length')
    rows, previous = [], bytearray(w*4)
    for y in range(h):
        at=y*(w*4+1); ft=raw[at]; row=bytearray(raw[at+1:at+1+w*4]); require(ft in range(5), 'unknown PNG filter')
        for x in range(len(row)):
            a=row[x-4] if x>=4 else 0; b=previous[x]; c=previous[x-4] if x>=4 else 0
            if ft==1: add=a
            elif ft==2: add=b
            elif ft==3: add=(a+b)//2
            elif ft==4:
                p=a+b-c; pa,pb,pc=abs(p-a),abs(p-b),abs(p-c); add=a if pa<=pb and pa<=pc else b if pb<=pc else c
            else: add=0
            row[x]=(row[x]+add)&255
        rows.append(bytes(row[3::4])); previous=row
    return rows


def jpeg_size(data):
    require(data[:2] == b'\xff\xd8' and data[-2:] == b'\xff\xd9', 'not complete JPEG')
    p=2
    while p<len(data):
        require(data[p]==255, 'JPEG marker expected')
        while data[p]==255: p+=1
        marker=data[p];p+=1
        if marker in (1,*range(0xd0,0xda)): continue
        n=int.from_bytes(data[p:p+2], 'big'); require(n>=2 and p+n<=len(data), 'truncated JPEG')
        if marker in (0xc0,0xc1,0xc2): return (int.from_bytes(data[p+5:p+7],'big'), int.from_bytes(data[p+3:p+5],'big'))
        require(marker!=0xda, 'missing JPEG frame');p+=n
    raise ValueError('missing JPEG dimensions')


def plus(a,b): return [x+y for x,y in zip(a,b)]
def mul(a,s): return [x*s for x in a]
def error(a,b): return max(abs(x-y) for x,y in zip(a,b))
def cross(a,b): return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]


def replay(h):
    manifest=read(h/'manifest.json'); current=h/'inputs/current'
    for name, entry in manifest['inputs'].items(): require(sha(checked_file(h,name))==entry['sha256'], 'historical input mismatch')
    frozen=read(h/'artifact-sha256.json')
    for name,entry in frozen.items(): check_bytes(checked_file(h,name),entry,name)
    require({p.relative_to(h).as_posix() for p in h.rglob('*') if p.is_file()}==set(frozen)|{'artifact-sha256.json'}, 'preparation inventory differs')
    layouts={x['id']:x for x in read(h/'layouts.json')};count=hosts=pngs=0;maxerr=poseerr=0.0
    for q in read(h/'capture-queue.json')['scenes']:
        d=read(h/q['file']);c=layouts[q['id']];info=c['info'];sand=info['kind']=='sandwich'
        yaw=math.radians(180 if sand or info['facing']=='north' else 270); t=math.radians(22.5 if sand else 0);scale=.01 if sand else .012
        host=read(h/('inputs/host/'+('sandwich-bodies-1' if sand else 'chalkboard-'+info['facing'])+'.bbmodel'));he={e['uuid']:e for e in host['elements']}
        for texture in d['textures']:
            b=base64.b64decode(texture['source'].split(',')[1],validate=True)
            require(png(b)==(texture['uv_width'],texture['uv_height']), 'PNG dimensions differ');pngs+=1
            if texture.get('_review_input','').startswith('inputs/current/runtime/RP/textures/board_font'): require(b==checked_file(h,texture['_review_input']), 'atlas PNG bytes differ')
            else: require(any(texture['source']==v['source'] for v in host['textures']), 'host PNG bytes differ')
        for e in d['elements']:
            r=e['_review']
            if r['kind']=='native_geometry':
                old=he[e['uuid']];require(e['faces']==old['faces'], 'host UV/faces differ')
                for k,v in e['vertices'].items(): require(error(v,plus(old['vertices'][k],r['N06_host_translation']))<=1e-12,'host vertex differs')
                hosts+=1;continue
            en=c['entities'][r['entity_index']];cp=en['props']['char_0'];require(r['cell']==cp%256 and r['page']==cp//256,'glyph index differs')
            geom=read(current/('runtime/RP/models/entity/board_glyph_'+r['geometry_kind']+'.geo.json'))['minecraft:geometry'][cp%256]
            bone=next(b for b in geom['bones'] if b['name']==r['bone']);cube=bone['cubes'][r['cube']];o=cube['origin'];s=cube['size'];dx=dy=0
            if r['bone']=='bold':dx=-.5
            if r['bone'].startswith('outline_'):
                offsets=[(x,y) for x in [-1,0,1] for y in [-1,0,1] if (x,y)!=(0,0)];dx,dy=mul(offsets[int(r['bone'].split('_')[-1])],.5)
                if 'bold' in r['bone']:dx-=.5
            loc=loads(en['dyn']['kt:writingBoard/signature'])['location'];anchor=[loc['x']*16-8,loc['y']*16,loc['z']*16-8]
            u=[math.cos(yaw),0,math.sin(yaw)];v=[math.sin(yaw)*math.sin(t),math.cos(t),-math.cos(yaw)*math.sin(t)];w=[math.sin(yaw)*math.cos(t),-math.sin(t),-math.cos(yaw)*math.cos(t)]
            coords=[(o[0]+dx,o[1]+s[1]+dy,o[2]),(o[0]+dx,o[1]+dy,o[2]),(o[0]+s[0]+dx,o[1]+dy,o[2]),(o[0]+s[0]+dx,o[1]+s[1]+dy,o[2])]
            for k,(x,y,z) in enumerate(coords):
                expected=plus(anchor,mul(plus(plus(mul(u,x),mul(v,y)),mul(w,z)),16*scale));maxerr=max(maxerr,error(e['vertices'][str(k)],expected));count+=1
            a,b=cube['uv']['north']['uv'];du,dv=cube['uv']['north']['uv_size'];require(list(e['faces']['north']['uv'].values())==[[a,b],[a,b+dv],[a+du,b+dv],[a+du,b]],'glyph UV differs')
        axis=[-math.cos(yaw),0,-math.sin(yaw)]
        base=[.5-math.sin(yaw)*.06,1.06,.5+math.cos(yaw)*.06] if sand else [.5+math.sin(yaw)*.42,1.535,.5-math.cos(yaw)*.42]
        for en in c['entities']:
            row,index=map(int,en['dyn']['kt:writingBoard/anchor'].split('|')[-2:]);x=c['rows'][row][index];down=row*(10 if sand else 12)+c['verticalOffset']-19
            point=mul([math.cos(yaw)*x,-down,math.sin(yaw)*x],scale)
            rotated=plus(plus(mul(point,math.cos(t)),mul(cross(axis,point),math.sin(t))),mul(axis,sum(a*b for a,b in zip(axis,point))*(1-math.cos(t))))
            loc=loads(en['dyn']['kt:writingBoard/signature'])['location'];poseerr=max(poseerr,error(plus(base,rotated),[loc[k] for k in ('x','y','z')]))
    require(count==524 and hosts==36 and pngs==36 and maxerr<1e-10 and poseerr<1e-12,'saved scene geometry check failed')
    require(not layouts['blank-boundary']['entities'],'blank emits helpers')
    fallback=[e['props']['char_0'] for e in layouts['large-fallback-blank-lines']['entities']]
    require(0x25a1 in fallback and 0xe000 in fallback and all(c not in (32,0x200c) for c in fallback),'fallback boundary differs')
    raw=(current/'art/fonts/unifont-15.0.06.hex.gz').read_bytes(); dz=zlib.decompressobj(16+zlib.MAX_WBITS); font=dz.decompress(raw,MAX_FILE+1)
    require(dz.eof and len(font)<=MAX_FILE and not dz.unused_data,'font archive exceeds bound')
    hexes=dict(line.split(':') for line in font.decode().splitlines());digits=re.search("FONT_ADVANCE_DIGITS='([^']+)'",(current/'runtime/BP/scripts/data/board-font.js').read_text()).group(1)
    cps=sorted({e['props']['char_0'] for c in layouts.values() for e in c['entities']});saved=read(h/'independent-saved-scene-checks.json')['selected_atlas_checks']
    for cp in cps:
        rows=png((current/f'runtime/RP/textures/board_font/glyph_{cp//256:02X}.png').read_bytes(),True);x=(cp%16)*16;y=((cp%256)//16)*16;cell=b''.join(row[x:x+16] for row in rows[y:y+16])
        if cp==0xe000:
            require(digits[cp]=='6' and sha(cell)==next(s['cell_sha256'] for s in saved if s['cp']==cp),'private fallback differs');continue
        hexstr=hexes[f'{cp:04X}'];width=len(hexstr)//4;bits=bytes.fromhex(hexstr);pixels=[[255 if bits[yy*(width//8)+xx//8] & (128>>(xx%8)) else 0 for xx in range(width)] for yy in range(16)]
        columns=[xx for xx in range(width) if any(row[xx] for row in pixels)];left=min(columns) if columns else 0;right=max(columns) if columns else -1
        expected=b''.join(bytes(row[left:right+1]+[0]*(16-(right-left+1))) for row in pixels)
        require(cell==expected and int(digits[cp])==(right-left+1)//2+1,'Unifont cell/advance differs')
    controllers=read(current/'runtime/RP/render_controllers/board_glyph_visual.render_controllers.json')['render_controllers'];entity=read(current/'runtime/RP/entity/board_glyph_visual.entity.json')['minecraft:client_entity']['description']
    for name,c in controllers.items():
        for i,p in enumerate(c['arrays']['textures']['Array.pages']):require(p=='Texture.page_'+str(i) and entity['textures'][p.split('.')[1]]==f'textures/board_font/glyph_{i:02X}','atlas route differs')
        for i,p in enumerate(c['arrays']['geometries']['Array.cells']):require(p=='Geometry.'+('outline_cell_' if name.endswith('outline') else 'cell_')+str(i) and entity['geometry'][p.split('.')[1]]=='geometry.kt_runtime.board_'+('outline_cell_' if name.endswith('outline') else 'glyph_cell_')+str(i),'geometry route differs')
    return dict(vertices=count,host_meshes=hosts,embedded_png_records=pngs,selected_atlas_cells=len(cps),maximum_vertex_error_pixels=maxerr,maximum_source_pose_pen_error_blocks=poseerr,layout_cases=len(layouts),historical_inputs=len(manifest['inputs']))


def validate(root, work, repository=None):
    inventory(root,read(root/'artifact-sha256.json'))
    prep=extract(root,work);result=replay(prep)
    gui=root/'gui';manifest=read(gui/'evidence-sha256.json')
    for name,entry in manifest.items():check_bytes(checked_file(gui,name),entry,name)
    require({p.relative_to(gui).as_posix() for p in gui.rglob('*') if p.is_file()}==set(manifest)|{'evidence-sha256.json'},'GUI inventory differs')
    images=[p for p in gui.rglob('*.jpg')];require(len(images)==28 and len(list((gui/'accepted').glob('*.jpg')))==12,'GUI image count differs')
    for p in images:require(jpeg_size(p.read_bytes())==(1188,848),'JPEG dimensions differ')
    receipt=read(root/'current-input-verification.json');require(receipt['exact_inputs'],'empty reuse boundary')
    historical = {}
    for origin in (read(work/'supplement/N05-manifest.json'), read(prep/'manifest.json')):
        for name, entry in origin['inputs'].items():
            if name.startswith(('inputs/current/','inputs/canonical/')):
                historical.setdefault(entry['original_path'],set()).add(entry['sha256'])
    for entry in receipt['exact_inputs']:
        require(entry['sha256'] in historical.get(entry['path'],set()), 'reuse hash lacks historical input provenance')
        if entry.get('historical_member'):
            require(sha(checked_file(work,entry['historical_member']))==entry['sha256'],'archived unchanged input differs')
    changed=receipt.get('changed_host_inputs',[])
    require(len(changed)==7 and len({e['path'] for e in changed})==7,'expected seven chalk host transitions')
    def trim_edges(value):
        if isinstance(value,dict):
            for name, content in value.items():
                if name=='cubes' and isinstance(content,list):
                    for cube in content:
                        uv=cube.get('uv')
                        if isinstance(uv,dict):
                            for face in ('east','west','down'):uv.pop(face,None)
                trim_edges(content)
        elif isinstance(value,list):
            for content in value:trim_edges(content)
    for entry in changed:
        before=checked_file(work,entry['before_member']);after=checked_file(work,entry['current_member'])
        require(sha(before)==entry['historical_sha256'] and sha(after)==entry['current_sha256'],'host transition hash differs')
        require(entry['historical_sha256'] in historical.get(entry['path'],set()),'host prior hash lacks provenance')
        require(before!=after,'host transition unchanged')
        a,b=loads(before),loads(after);trim_edges(a);trim_edges(b)
        require(json.dumps(a,sort_keys=True,allow_nan=False)==json.dumps(b,sort_keys=True,allow_nan=False),'host changed outside narrow east/west/down UVs')
    if repository:
        repository=no_links(repository)
        seen=set()
        for entry in receipt['exact_inputs']:
            require(entry['path'] not in seen,'duplicate current input');seen.add(entry['path'])
            require(sha(checked_file(repository,entry['path']))==entry['sha256'],'unchanged repository input differs: '+entry['path'])
        for entry in receipt.get('changed_host_inputs',[]):
            require(entry['historical_sha256']!=entry['current_sha256'],'changed input falsely unchanged')
            require(sha(checked_file(repository,entry['path']))==entry['current_sha256'],'current changed host differs')
    result.update(status='PASS bounded offline evidence; no native or Java Font acceptance',gui_images=28,accepted_gui_images=12,repository_inputs_checked=bool(repository),exact_input_receipts=len(receipt['exact_inputs']),narrow_edge_host_transitions=len(changed))
    return result


def main():
    require(sys.flags.optimize==0 and not os.environ.get('PYTHONOPTIMIZE'),'optimized Python is unsupported')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repository',type=Path);parser.add_argument('--work-dir',type=Path);parser.add_argument('--report',type=Path);args=parser.parse_args()
    root=no_links(Path(__file__).absolute().parent).resolve(strict=True)
    repository=no_links(args.repository).resolve(strict=True) if args.repository is not None else None
    require(repository is None or repository.is_dir(), 'repository is not a directory')
    report=new_output(args.report,root,repository) if args.report else None
    # gettempdir()/TemporaryDirectory() can probe-write before returning a path.
    # Choose and check the prospective child before any directory or file creation.
    temp_parent=next((os.environ[name] for name in ('TMPDIR','TEMP','TMP') if os.environ.get(name)), '/tmp')
    destination=args.work_dir if args.work_dir else Path(temp_parent)/('n06-portable-'+uuid.uuid4().hex)
    work=new_output(destination,root,repository)
    require(report is None or not overlaps(report,work),'outputs overlap')
    work.mkdir(mode=0o700 if args.work_dir is None else 0o777)
    try:result=validate(root,work,repository)
    finally:
        if args.work_dir is None:shutil.rmtree(work)
    payload=json.dumps(result,indent=2,allow_nan=False)+'\n'
    if report:
        with report.open('x') as f:f.write(payload)
    print(payload,end='')

if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,TypeError,OSError,zipfile.BadZipFile,struct.error,zlib.error) as exc:
        print('FAIL: '+str(exc),file=sys.stderr);sys.exit(1)
