"""One fixed Fishing observer on the existing stopped-world first/restart copy.

The QA overlay changes Fishing's main import, excludes one exact QA owner from
orphan processing and adds two named scripts. All changes are restored before
the closed-engine pack deletion boundary.
Actual canonical storage helpers run unchanged in Fishing's own DP scope.
Nothing here launches BDS, copies a world or alters a deployment receipt.
"""
from __future__ import annotations
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

from family_update import common as c

KIND = 'fishing_native_contents_observer'
PREFIX = 'SENLUO_FISHING_NATIVE_OBSERVER '
EVENT = 'senluo_qa:fishing_contents'
BP = '5e121bf2-1d2d-4da4-be15-cffc5f216d94'
RP = 'e1168f1a-83d6-4abc-8f4b-ecb86e0a91dd'
OWNER = 'companion-sources/fishing-current-local/runtimeowner'
RECIPE = 'companion-sources/fishing-current-local/recipe.json'
INPUT_RECIPE = 'companion-sources/fishing-current-local/input-recipe.json'
PROBE = 'tools/native/fishing-contents-probe.js'
HELPERS = [OWNER + '/BP/scripts/blocks/tank-contents.js', OWNER + '/BP/scripts/blocks/native-tank-storage.js']
MAIN_SOURCE = OWNER + '/BP/scripts/main.js'
TANKS_SOURCE = OWNER + '/BP/scripts/blocks/tanks.js'
MAIN = 'scripts/main.js'
TANKS = 'scripts/blocks/tanks.js'
PROBE_TARGET = 'scripts/fishing-contents-probe.js'
LISTENER_TARGET = 'scripts/fishing-native-observer.js'
APPEND = b'\nimport "./fishing-native-observer.js";\n'
QA_ORPHAN_BEFORE = b'    const key = entity.getDynamicProperty(NATIVE_STORAGE_OWNER);\n    const owner = ownedPosition(key);'
QA_ORPHAN_AFTER = b"    const key = entity.getDynamicProperty(NATIVE_STORAGE_OWNER);\n    if (key === 'kfv:qa:contents:minecraft:overworld:24,300,8') return;\n    const owner = ownedPosition(key);"
POSITION = {'x': 24, 'y': 300, 'z': 8}
SLOTS = [22, 23, 24]

LISTENER = r'''// Exact test-only Fishing observer; never a deployment input.
import {world,system} from '@minecraft/server';
import {runFishingContentsProbe} from './fishing-contents-probe.js';
const BINDING='__BINDING__',EVENT='senluo_qa:fishing_contents',SAFETY='qa:fishing_observer_safety';
const seen=new Set(),position={x:24,y:300,z:8};
const check=(ok,message)=>{if(!ok)throw Error(message);};
system.afterEvents.scriptEventReceive.subscribe(event=>{
 if(event.id!==EVENT||event.sourceType!=='Server')return;
 let request;try{request=JSON.parse(event.message);}catch{return;}
 if(request?.binding_id!==BINDING||!['first','restart'].includes(request.phase)||Object.keys(request).length!==2)return;
 const phase=request.phase;
 const emit=(type,value)=>console.warn('SENLUO_FISHING_NATIVE_OBSERVER '+JSON.stringify({schema:1,binding_id:BINDING,phase,type,...value}));
 system.run(()=>{
  try{
   check(!seen.has(phase),'duplicate Fishing observer command');seen.add(phase);
   check(world.getAllPlayers().length===0,'Fishing observer requires zero Players');
   const dimension=world.getDimension('minecraft:overworld'),block=dimension.getBlock(position);
   check(block?.typeId,'Fishing observer cell is not loaded');
   let safety;
   if(phase==='first'){
    check(world.getDynamicProperty(SAFETY)===undefined,'stale Fishing safety fixture');
    check(block.typeId==='minecraft:air','Fishing observer refuses to replace an existing block');
    const entities=dimension.getEntities({location:{x:24.5,y:300.5,z:8.5},maxDistance:1});
    check(entities.length===0,'Fishing observer refuses to overlap existing entities');
    safety={binding_id:BINDING,before_type:'minecraft:air',before_entities:0,position};
    block.setType('minecraft:chest');world.setDynamicProperty(SAFETY,JSON.stringify(safety));
   }else{
    const raw=world.getDynamicProperty(SAFETY);check(typeof raw==='string','Fishing safety proof did not persist');safety=JSON.parse(raw);
    check(safety.binding_id===BINDING&&safety.before_type==='minecraft:air'&&safety.before_entities===0&&
     ['x','y','z'].every(axis=>safety.position?.[axis]===position[axis]),'Fishing safety proof differs');
   }
   check(block.typeId==='minecraft:chest','Fishing receipt chest changed');
   const container=block.getComponent('minecraft:inventory')?.container;
   check(container?.size===27,'Fishing receipt chest inventory unavailable');
   for(let slot=0;slot<container.size;slot++)check(!container.getItem(slot),'Fishing receipt chest must start empty');
   let cases=0;
   runFishingContentsProbe({phase,dimension,container,position,receiptSlot:22,out:(type,value)=>{
    check(type==='case','unknown Fishing observer record');cases++;emit('case',{case:value});
   }});
   emit('done',{ok:true,cases,safe_scene:{...safety,block_type:block.typeId,receipt_slots:[22,23,24]},
    players:world.getAllPlayers().length,simulated_players:false,player_use:false,client:false});
  }catch(error){emit('fail',{error:String(error),client:false});}
 });
});
'''


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            assert key not in result, 'Duplicate observer evidence field'
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs)


def _regular(path):
    path = Path(path)
    assert path.is_absolute() and path.resolve() == path and not path.is_symlink(), 'Observer input must be an explicit regular path'
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, 'rb') as stream:
        before = os.fstat(stream.fileno()); raw = stream.read(); after = os.fstat(stream.fileno())
    final = path.lstat()
    assert stat.S_ISREG(before.st_mode) and stat.S_ISREG(final.st_mode), 'Observer input is not regular'
    assert (before.st_dev, before.st_ino) == (final.st_dev, final.st_ino), 'Observer input was replaced'
    assert all(getattr(before, key) == getattr(after, key) for key in ['st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns']), 'Observer input changed during read'
    return raw


def enabled():
    path = c.CONFIG.get('managed_drift_recovery')
    if not path:
        return False
    review = _json(_regular(Path(path)))
    return review.get('profile') == 'reviewed-same-uuid-local-input-repair-v1' and review.get('local_existing_input', {}).get('action') == 'repair_forward'


def _git_file(root, name, commit):
    entry = c.git(root, 'ls-tree', commit, '--', name)
    assert entry, 'Fishing observer source is not committed: ' + name
    header, actual_name = entry.split('\t', 1)
    mode, kind, blob = header.split()
    assert actual_name == name and mode in ('100644', '100755') and kind == 'blob', 'Fishing observer source is linked or irregular'
    raw = _regular(root / name)
    stored = subprocess.check_output(['git', '-C', str(root), 'cat-file', 'blob', blob])
    assert raw == stored, 'Fishing observer source differs from its committed blob: ' + name
    return {'path': name, 'git_blob': blob, 'sha256': _sha(raw)}, raw


def _sources():
    assert enabled() and c.EXTENSION is not None, 'This observer requires the reviewed current local Fishing repair'
    root = c.EXTENSION
    commit = c.git(root, 'rev-parse', 'HEAD')
    records, raw = {}, {}
    for name in [PROBE, *HELPERS, MAIN_SOURCE, TANKS_SOURCE, RECIPE, INPUT_RECIPE, '.repo-target.json']:
        records[name], raw[name] = _git_file(root, name, commit)
    target = _json(raw['.repo-target.json'])
    assert target['repository'] == 'burnt-tea-dev/senluo-family-integration-private' and target['repository_id'] == 1406868911 and target['private'] is True
    assert target['owner'] == {'login': 'burnt-tea-dev', 'id': 344456559, 'type': 'Organization'}, 'Fishing observer private repository identity differs'
    recipe = _json(raw[RECIPE])
    assert recipe['schema'] == 1 and recipe['kind'] == 'canonical_local_fishing_repair'
    assert recipe['historical_origin_status'] == 'unknown' and recipe['original_archive_verified'] is False and recipe['latest_stable_verified'] is False
    assert all(recipe[key] is False for key in ['native_loading', 'saved_world_migration', 'client', 'production_ready'])
    assert recipe['input_recipe'] == {'path': INPUT_RECIPE, 'sha256': records[INPUT_RECIPE]['sha256']}, 'Fishing source recipe input binding differs'
    source = {'repository': target['repository'], 'repository_id': target['repository_id'], 'private': True,
              'commit': commit, 'tree': c.git(root, 'rev-parse', commit + '^{tree}'), 'files': records}
    return source, raw, recipe


def input_refs():
    if not enabled():
        return {}
    source, _, _ = _sources()
    return {'fishing_native_observer_source': source,
            'fishing_native_observer_controller': _sha(_regular(Path(__file__).absolute()))}


def _world(world):
    expected = c.R / 'saved-world-engine/worlds/Saved World QA'
    assert Path(world) == expected and expected.resolve() == expected and expected.is_dir() and not expected.is_symlink(), 'Fishing observer is confined to this saved-world QA copy'
    return expected


def _metadata(path):
    info = Path(path).lstat()
    assert stat.S_ISREG(info.st_mode) and not Path(path).is_symlink()
    return {'device': info.st_dev, 'uid': info.st_uid, 'gid': info.st_gid,
            'mode': stat.S_IMODE(info.st_mode), 'mtime_ns': info.st_mtime_ns}


def _restore(path, raw, metadata):
    path.write_bytes(raw)
    os.chmod(path, metadata['mode'])
    os.utime(path, ns=(path.stat().st_atime_ns, metadata['mtime_ns']))
    assert _metadata(path) == metadata, 'Fishing original file metadata was not restored'


def _expected(receipt):
    receipt_path = c.C / 'family-receipt.json'
    receipt_raw = _regular(receipt_path)
    assert _json(receipt_raw) == receipt, 'Fishing observer receipt differs from the immutable candidate'
    packs = {row['uuid']: row for row in receipt['packs']}
    assert len(packs) == len(receipt['packs']) and BP in packs and RP in packs
    source, raw, recipe = _sources()
    for side, uid in [('BP', BP), ('RP', RP)]:
        assert packs[uid]['side'] == ('behavior' if side == 'BP' else 'resource')
        assert packs[uid]['version'] == recipe['version'] and packs[uid]['files'] == recipe['output_hashes'][side], 'Fishing observer source is not this exact candidate pair'
    original = {MAIN: raw[MAIN_SOURCE], TANKS: raw[TANKS_SOURCE]}
    assert original[TANKS].count(QA_ORPHAN_BEFORE) == 1, 'Fishing QA orphan preimage is not the exact reviewed function'
    changed = {MAIN: original[MAIN] + APPEND, TANKS: original[TANKS].replace(QA_ORPHAN_BEFORE, QA_ORPHAN_AFTER)}
    metadata = {}
    for name, before in original.items():
        assert _sha(before) == packs[BP]['files'][name], 'Fishing observer preimage differs'
        candidate_file = c.C / 'behavior_packs' / BP / name
        assert _regular(candidate_file) == before, 'Fishing candidate preimage differs from its canonical source'
        metadata[name] = _metadata(candidate_file)
    for name in HELPERS:
        assert source['files'][name]['sha256'] == packs[BP]['files'][name.split('/BP/', 1)[1]], 'Fishing observer helper differs from actual candidate'
    assert PROBE_TARGET not in packs[BP]['files'] and LISTENER_TARGET not in packs[BP]['files'], 'Fishing observer would overwrite candidate files'
    backup = c.R / 'production-before/backup-receipt.json'
    controller = _sha(_regular(Path(__file__).absolute()))
    identity = {'candidate_receipt_sha256': _sha(receipt_raw), 'source': source, 'controller_sha256': controller,
                'backup_receipt_sha256': _sha(_regular(backup))}
    binding = _sha(json.dumps(identity, sort_keys=True, separators=(',', ':')).encode())
    additions = {PROBE_TARGET: raw[PROBE], LISTENER_TARGET: LISTENER.replace('__BINDING__', binding).encode()}
    files = [{'path': 'behavior_packs/' + BP + '/' + name, 'before_sha256': _sha(original[name]), 'after_sha256': _sha(changed[name]),
              'operation': 'append_exact_listener_import' if name == MAIN else 'exclude_exact_qa_owner_from_orphan_processing',
              'original_metadata': metadata[name]} for name in [MAIN, TANKS]]
    files += [{'path': 'behavior_packs/' + BP + '/' + name, 'before_sha256': None, 'after_sha256': _sha(content), 'operation': 'add_exact_observer_script'} for name, content in sorted(additions.items())]
    record = {'schema': 1, 'kind': KIND, **identity, 'binding_id': binding, 'files': files,
              'fixture': {'dimension': 'minecraft:overworld', 'position': POSITION, 'receipt_slots': SLOTS, 'require_original_air_and_no_entities': True},
              'actual_fishing_owner_scope': True, 'helpers_unchanged': True, 'test_world_only': True,
              'client': False, 'simulated_players': False, 'player_use': False}
    return record, original, changed, additions


def _load(receipt, overlay):
    expected, original, changed, additions = _expected(receipt)
    assert set(overlay) == set(expected) | {'evidence'}, 'Unknown Fishing overlay fields'
    ref = overlay['evidence']; path = c.R / 'fishing-native-observer-overlay.json'
    assert ref == {'path': str(path), 'sha256': _sha(_regular(path))}, 'Fishing overlay evidence reference changed'
    assert _json(_regular(path)) == expected and {key: value for key, value in overlay.items() if key != 'evidence'} == expected, 'Fishing overlay source, scope or bytes differ'
    return expected, original, changed, additions


def install(world, receipt):
    c.assert_lease()
    world = _world(world)
    record, original, changed, additions = _expected(receipt)
    path = c.R / 'fishing-native-observer-overlay.json'
    assert not path.exists() and not path.is_symlink(), 'Never overwrite a Fishing overlay declaration'
    c.audit_candidate(world, receipt)
    pack = world / 'behavior_packs' / BP
    metadata = {row['path'].split('/' + BP + '/', 1)[1]: row['original_metadata'] for row in record['files'] if row['before_sha256'] is not None}
    for name, raw in original.items():
        assert _regular(pack / name) == raw and _metadata(pack / name) == metadata[name], 'Fishing observer source or metadata differs before installation'
    for name in additions:
        assert not (pack / name).exists() and not (pack / name).is_symlink(), 'Fishing observer destination already exists'
    written = []
    try:
        for name, content in additions.items():
            destination = pack / name
            assert destination.parent.resolve() == destination.parent and not destination.parent.is_symlink()
            with destination.open('xb') as output:
                output.write(content)
            written.append(destination)
        for name, raw in changed.items():
            (pack / name).write_bytes(raw)
        c.atomic(path, record)
        overlay = {**record, 'evidence': {'path': str(path), 'sha256': _sha(_regular(path))}}
        audit(world, receipt, overlay)
        return overlay
    except BaseException:
        for name, raw in original.items():
            _restore(pack / name, raw, metadata[name])
        for destination in reversed(written):
            destination.unlink()
        raise


def audit(world, receipt, overlay):
    world = _world(world)
    _, _, changed, additions = _load(receipt, overlay)
    pack = world / 'behavior_packs' / BP
    for name, raw in changed.items():
        assert _regular(pack / name) == raw, 'Fishing overlay is not the exact reviewed file projection'
    for name, content in additions.items():
        assert _regular(pack / name) == content, 'Fishing overlay added bytes changed'
    projection = copy.deepcopy(receipt)
    fish = next(row for row in projection['packs'] if row['uuid'] == BP)
    fish['files'] = {**fish['files'], **{name: _sha(content) for name, content in {**changed, **additions}.items()}}
    c.audit_candidate(world, projection)
    return {'candidate_projection_verified': True, 'exact_overlay_verified': True}


def commands(phase):
    assert phase in ('first', 'restart')
    receipt = _json(_regular(c.C / 'family-receipt.json'))
    record, _, _, _ = _expected(receipt)
    request = json.dumps({'phase': phase, 'binding_id': record['binding_id']}, separators=(',', ':'))
    return ['tickingarea add circle 24 300 8 1 fishing_native_observer', 'scriptevent ' + EVENT + ' ' + request]


def _parse(engine, phase, overlay):
    log = Path(engine) / (phase + '.log'); raw = _regular(log)
    text = raw.decode('utf-8', errors='replace')
    assert 'Server started.' in text and 'Player connected:' not in text and ' ERROR]' not in text and '[error]' not in text.lower(), 'Fishing native run did not start cleanly with zero Players'
    rows = []
    for line in text.splitlines():
        if PREFIX in line:
            row = _json(line.split(PREFIX, 1)[1])
            assert row['schema'] == 1 and row['binding_id'] == overlay['binding_id'] and row['phase'] == phase
            assert row['type'] in ('case', 'done'), 'Fishing native observer reported failure or an unknown record'
            rows.append(row)
    count = 3 if phase == 'first' else 2
    assert len(rows) == count + 1 and [row['type'] for row in rows] == ['case'] * count + ['done'], 'Fishing native named cases or completion are missing/duplicated'
    for row in rows[:-1]:
        assert set(row) == {'schema', 'binding_id', 'phase', 'type', 'case'}
    cases = [row['case'] for row in rows[:-1]]
    modes = ['native-fishing-DP-write-rollback', 'native-fishing-DP-write-rollback', 'native-fishing-persistence'] if phase == 'first' else ['native-fishing-persistence', 'native-fishing-recovery']
    assert [row['mode'] for row in cases] == modes
    for case in cases:
        assert case['phase'] == phase and case['playerUse'] is False and case['client'] is False
        fields = {
            'native-fishing-DP-write-rollback': {'mode', 'phase', 'fault', 'nativeContainers', 'injectedDPWrite', 'playerUse', 'client'},
            'native-fishing-persistence': {'mode', 'phase', 'fixture', 'key', 'carrier', 'nativeRecord', 'nativeStacks', 'nativeCarrierCount', 'playerUse', 'actualFishingOwnerScope', 'opaqueDynamicPropertiesConstructed', 'completeNbtByteComparison', 'client'},
            'native-fishing-recovery': {'mode', 'phase', 'fixture', 'receiptSlots', 'recoveredStacks', 'retiredTombstone', 'repeatedReturnRejected', 'playerUse', 'client'},
        }
        assert set(case) == fields[case['mode']], 'Fishing observer case has undeclared fields'
    if phase == 'first':
        assert [case['fault'] for case in cases[:2]] == ['before', 'after']
        assert all(case['nativeContainers'] is True and case['injectedDPWrite'] is True for case in cases[:2])
    persisted = cases[-1] if phase == 'first' else cases[0]
    assert persisted['actualFishingOwnerScope'] is True and persisted['opaqueDynamicPropertiesConstructed'] is False and persisted['completeNbtByteComparison'] is False
    assert persisted['nativeCarrierCount'] == 1 and isinstance(persisted['carrier'], str) and persisted['carrier']
    stacks = persisted['nativeStacks']
    assert len(stacks) == 4 and stacks[3] is None and [stack['id'] for stack in stacks[:3]] == ['kaleidoscope_fishing:carp', 'kaleidoscope_fishing:carp', 'kaleidoscope_fishing:grass_carp']
    assert all(stack['amount'] == 1 and stack['name'] and stack['lore'] and stack['canDestroy'] == ['minecraft:stone'] and stack['canPlaceOn'] == ['minecraft:glass'] and stack['keep'] is True for stack in stacks[:3])
    native = persisted['nativeRecord']
    assert set(native) == {'schema', 'key', 'dimension', 'position', 'ids', 'entity', 'token', 'retired'}
    assert native['schema'] == 1 and native['key'] == persisted['key'] == 'kfv:qa:contents:minecraft:overworld:24,300,8'
    assert native['position'] == POSITION and native['dimension'] == 'minecraft:overworld' and native['entity'] == persisted['carrier'] and native['retired'] is False
    assert native['ids'] == [stack['id'] if stack else None for stack in stacks] and isinstance(native['token'], str) and native['token']
    done = rows[-1]
    assert set(done) == {'schema', 'binding_id', 'phase', 'type', 'ok', 'cases', 'safe_scene', 'players', 'simulated_players', 'player_use', 'client'}
    assert done['ok'] is True and done['cases'] == count and done['players'] == 0 and done['simulated_players'] is False and done['player_use'] is False and done['client'] is False
    assert done['safe_scene'] == {'binding_id': overlay['binding_id'], 'before_type': 'minecraft:air', 'before_entities': 0, 'position': POSITION, 'block_type': 'minecraft:chest', 'receipt_slots': SLOTS}
    if phase == 'restart':
        recovered = cases[1]
        assert recovered['fixture'] == persisted['fixture'] and recovered['receiptSlots'] == SLOTS and recovered['recoveredStacks'] == stacks[:3] and recovered['repeatedReturnRejected'] is True
        tombstone = recovered['retiredTombstone']
        assert tombstone == {**native, 'ids': [None] * 4, 'entity': None, 'retired': True}, 'Fishing native retirement changed identity or payload'
    return {'schema': 1, 'kind': KIND, 'phase': phase, 'binding_id': overlay['binding_id'], 'log': {'path': str(log), 'sha256': _sha(raw)},
            'cases': cases, 'safe_scene': done['safe_scene'], 'ok': True, 'actual_fishing_owner_scope': True,
            'complete_nbt_byte_comparison': False, 'player_use': False, 'client': False, 'simulated_players': False}


def verify(engine, world, phase, overlay):
    assert Path(engine) == c.R / 'saved-world-engine' and phase in ('first', 'restart')
    receipt = _json(_regular(c.C / 'family-receipt.json'))
    audit(world, receipt, overlay)
    report = _parse(engine, phase, overlay)
    path = c.R / ('fishing-native-observer-' + phase + '.json')
    assert not path.exists() and not path.is_symlink(), 'Never overwrite a Fishing phase report'
    c.atomic(path, report)
    return {**report, 'evidence': {'path': str(path), 'sha256': _sha(_regular(path))}}


def _phase_reports(overlay):
    reports = []
    for phase in ['first', 'restart']:
        actual = _parse(c.R / 'saved-world-engine', phase, overlay)
        path = c.R / ('fishing-native-observer-' + phase + '.json')
        assert _json(_regular(path)) == actual, 'Fishing native phase report changed'
        reports.append(actual)
    before, after = reports[0]['cases'][2], reports[1]['cases'][0]
    assert all(before[key] == after[key] for key in ['fixture', 'key', 'carrier', 'nativeRecord', 'nativeStacks']), 'Fishing carrier or complete measured payload changed across normal restart'
    return reports


def _removal_record(overlay, reports):
    return {'schema': 1, 'kind': 'fishing_native_observer_removal', 'overlay': overlay['evidence'],
            'candidate_receipt_sha256': overlay['candidate_receipt_sha256'], 'binding_id': overlay['binding_id'],
            'world': str(c.R / 'saved-world-engine/worlds/Saved World QA'), 'engine_stopped': True,
            'restored_files': [{'path': row['path'], 'sha256': row['before_sha256'], 'metadata': row['original_metadata']}
                               for row in overlay['files'] if row['before_sha256'] is not None],
            'removed_added_files': [row['path'] for row in overlay['files'] if row['before_sha256'] is None],
            'phase_reports': [{'path': str(c.R / ('fishing-native-observer-' + phase + '.json')),
                               'sha256': _sha(_regular(c.R / ('fishing-native-observer-' + phase + '.json')))} for phase in ['first', 'restart']],
            'phase_logs': [report['log'] for report in reports], 'canonical_candidate_audited': True,
            'client': False, 'simulated_players': False}


def _lifecycle(evidence, overlay, reports):
    assert evidence['test_only_overlays'] == [overlay], 'Require exactly this declared Fishing observer overlay'
    assert evidence['candidate_receipt_sha256'] == overlay['candidate_receipt_sha256']
    assert [run['phase'] for run in evidence['runs']] == ['first', 'restart']
    for run, actual in zip(evidence['runs'], reports, strict=True):
        assert run['ok'] and run['started'] and run['family_initialized'] and run['exit_code'] == 0 and not run['errors'] and run['real_player_connections'] == 0
        assert actual['log']['sha256'] == run['log_sha256'], 'Fishing observer native log differs from the parent lifecycle evidence'


def remove(world, receipt, overlay, *, evidence):
    """Restore the exact candidate only after both phases and a stopped engine."""
    c.assert_lease()
    world = _world(world)
    from family_update.storage import assert_idle
    assert_idle(c.R / 'saved-world-engine')
    _, original, _, additions = _load(receipt, overlay)
    reports = _phase_reports(overlay)
    _lifecycle(evidence, overlay, reports)
    audit(world, receipt, overlay)
    path = c.R / 'fishing-native-observer-removal.json'
    assert not path.exists() and not path.is_symlink(), 'Never overwrite a Fishing overlay removal receipt'
    metadata = {row['path'].split('/' + BP + '/', 1)[1]: row['original_metadata'] for row in overlay['files'] if row['before_sha256'] is not None}
    pack = world / 'behavior_packs' / BP
    for name, raw in original.items():
        _restore(pack / name, raw, metadata[name])
    for name in additions:
        (pack / name).unlink()
    c.audit_candidate(world, receipt)
    c.atomic(path, _removal_record(overlay, reports))
    return {'path': str(path), 'sha256': _sha(_regular(path))}


def validate_native_evidence(evidence):
    overlays = evidence['test_only_overlays']
    if not enabled():
        assert overlays == [], 'An unrequested Fishing observer cannot authorize overlays'
        return None
    assert isinstance(overlays, list) and len(overlays) == 1, 'Require exactly the declared Fishing observer overlay'
    overlay = overlays[0]
    receipt = _json(_regular(c.C / 'family-receipt.json'))
    _load(receipt, overlay)
    reports = _phase_reports(overlay)
    _lifecycle(evidence, overlay, reports)
    path = c.R / 'fishing-native-observer-removal.json'
    expected_removal = _removal_record(overlay, reports)
    removal = evidence['test_only_overlay_removal']
    assert removal == {'path': str(path), 'sha256': _sha(_regular(path))}, 'Fishing overlay removal reference changed'
    assert _json(_regular(path)) == expected_removal, 'Fishing overlay removal did not restore the exact candidate'
    return {'ok': True, 'overlay': overlay['evidence'], 'reports': [{'path': str(c.R / ('fishing-native-observer-' + phase + '.json')), 'sha256': _sha(_regular(c.R / ('fishing-native-observer-' + phase + '.json')))} for phase in ['first', 'restart']],
            'removal': removal, 'actual_fishing_owner_scope': True, 'complete_nbt_byte_comparison': False, 'player_use': False, 'client': False}
