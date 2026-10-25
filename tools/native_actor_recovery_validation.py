"""Read-only logical native conservation gates for the exact recovery plan.

The caller runs and normally stops its isolated QA world. It attaches that
native_run receipt to the returned observation before verify(). Saved actors or
index bytes alone cannot establish that the planned chunks were actually loaded.
"""
from __future__ import annotations

import copy
import json
import math

import nbtlib

import native_actor_recovery as recovery
from bedrock_nbt import encode_root

NUMBERS = (nbtlib.Byte, nbtlib.Short, nbtlib.Int, nbtlib.Long, nbtlib.Float, nbtlib.Double)
AREA_PREFIX = 'native_actor_recovery_'
require = recovery.require


def _areas(plan):
    targets = recovery._validate_plan(plan)
    result = []
    for row in sorted(targets, key=lambda r: (r['dimension_id'], r['owner_block']['position'], r['unique_id'])):
        x, y, z = row['owner_block']['position'];chunk = (x // 16, z // 16)
        covered = next((area for area in result if area['dimension_id'] == row['dimension_id'] and area['chunk'] == chunk), None)
        if covered is None:
            covered = {'name': AREA_PREFIX + str(len(result)), 'dimension_id': row['dimension_id'],
                       'dimension': recovery.DIMENSIONS[row['dimension_id']].split(':')[1],
                       'position': [x, y, z], 'chunk': chunk, 'radius': 1, 'unique_ids': []}
            result.append(covered)
        covered['unique_ids'].append(row['unique_id'])
    require(len(result) <= 10, 'Planned native targets need more than ten named QA ticking areas')
    return result


def commands(plan):
    """Named normal QA areas, coalescing targets in the same exact chunk."""
    return [f"execute in {a['dimension']} run tickingarea add circle {' '.join(map(str, a['position']))} 1 {a['name']} true"
            for a in _areas(plan)]


def observation_requirements(plan):
    return {'native_run_receipt_required': True, 'normal_stop_required': True, 'zero_players_required': True,
            'named_ticking_area_commands': commands(plan),
            'named_ticking_areas': [{'dimension': a['dimension'], 'name': a['name']} for a in _areas(plan)],
            'limits': 'Unloaded/unobserved targets cannot pass; the probe owner must create and acknowledge these areas in each normal QA run.'}


def _position(tag):
    position = tag.get('Pos')
    require(isinstance(position, nbtlib.List) and len(position) == 3 and
            all(isinstance(value, NUMBERS) and math.isfinite(float(value)) for value in position), 'Native actor position is not three finite typed numbers')
    dimension = tag.get('DimensionId', nbtlib.Int(0))
    require(isinstance(dimension, nbtlib.Int) and int(dimension) in recovery.DIMENSIONS, 'Native actor dimension is not an admitted TAG_Int')
    return [float(value) for value in position], int(dimension)


def _drop_region(row, position, dimension):
    x, y, z = row['owner_block']['position']
    return dimension == row['dimension_id'] and math.floor(position[0]) == x and math.floor(position[2]) == z and y - 1 <= position[1] <= y + 2


def _canonical(value):
    """Compound order is serialization detail; NBT types/list order are not."""
    if isinstance(value, nbtlib.Compound):
        return nbtlib.Compound({key: _canonical(value[key]) for key in sorted(value)})
    if isinstance(value, nbtlib.List):
        return type(value)([_canonical(child) for child in value])
    return copy.deepcopy(value)


def _item(item, *, slot=False):
    require(isinstance(item, nbtlib.Compound), 'Native item payload is not a compound')
    count, name = item.get('Count'), item.get('Name')
    require(isinstance(count, nbtlib.Byte) and isinstance(name, nbtlib.String), 'Native item Count/Name NBT types differ')
    count = int(count);name = str(name)
    require(0 <= count <= 127 and bool(name) == bool(count), 'Native item count/name is invalid')
    index = None
    if slot:
        require(isinstance(item.get('Slot'), nbtlib.Byte), 'Native inventory Slot is not TAG_Byte')
        index = int(item['Slot'])
    else:
        require('Slot' not in item, 'Ordinary dropped Item unexpectedly contains an inventory Slot')
    metadata = nbtlib.Compound({key: copy.deepcopy(value) for key, value in item.items() if key not in ('Slot', 'Count')})
    digest = recovery.sha(encode_root(nbtlib.File({'Item': _canonical(metadata)})))
    return {'slot': index, 'name': name, 'count': count, 'metadata_sha256': digest}


def _inventory(raw_hex, capacity):
    raw = recovery._hex(raw_hex, 'complete original inventory evidence')
    wrapper = recovery.decode(raw)
    require(set(wrapper) == {'Items'} and isinstance(wrapper['Items'], nbtlib.List)
            and wrapper['Items'].subtype is nbtlib.Compound, 'Complete typed inventory wrapper differs')
    occupied, seen = {}, set()
    for tag in wrapper['Items']:
        item = _item(tag, slot=True);slot = item['slot']
        require(0 <= slot < capacity and slot not in seen, 'Native inventory has duplicate/out-of-range slots')
        seen.add(slot)
        if item['count']:
            occupied[slot] = item
    require(occupied, 'Original recovery inventory is empty')
    return occupied


def _typed_properties(world, row):
    authority = row['authority'];owner = world.get(authority['scope'])
    require(isinstance(owner, nbtlib.Compound), 'Active world owner scope disappeared')
    keys = [authority['key']]
    if row['family'] == 'tavern_native':
        keys.append(authority['required_key'])
    else:
        keys.append(authority['key'] + ':remove')
    return encode_root(nbtlib.File({key: owner[key] for key in keys if key in owner})).hex()


def inspect(db, plan):
    """Capture only relevant native NBT/index/owner evidence; perform no writes."""
    targets = recovery._validate_plan(plan)
    pending = [row for row in targets if row.get('pending_removed_bowl', False)]
    wanted_keys = {bytes.fromhex(row['actor_key_hex']) for row in targets}
    wanted_keys.update(bytes.fromhex(alias['actor_key_hex']) for row in targets for alias in row.get('retained_aliases', []))
    target_owners = {(row['authority']['scope'], row['authority']['actor_properties'].get(
        'kaleidoscope_tavern:storage_owner', row['authority']['actor_properties'].get('senluo:kcf_owner'))): row['unique_id'] for row in targets}
    world = recovery.decode(recovery._get(db, recovery.WORLD_DP))
    actors, uid_keys, owner_keys, indexes, drops = {}, {}, {}, {}, {row['unique_id']: [] for row in pending}
    for key, raw in db.items():
        require(isinstance(key, bytes) and isinstance(raw, bytes), 'Unknown DB record encoding')
        if key.startswith(recovery.ACTOR_PREFIX):
            tag = recovery.decode(raw);uid = recovery._uid(tag)
            if uid is not None:
                uid_keys.setdefault(uid, []).append(key.hex())
            claims = []
            for scope, props in tag.get('DynamicProperties', {}).items():
                if not isinstance(props, nbtlib.Compound):
                    continue
                for name in ('kaleidoscope_tavern:storage_owner', 'senluo:kcf_owner'):
                    owner = (scope, str(props.get(name, '')))
                    if owner in target_owners:
                        claims.append(owner);owner_keys.setdefault(owner, []).append(key.hex())
            if key in wanted_keys or claims:
                actors[key.hex()] = raw.hex()
            if str(tag.get('identifier', '')) == 'minecraft:item' and pending:
                position, dimension = _position(tag)
                for row in pending:
                    if _drop_region(row, position, dimension):
                        drops[row['unique_id']].append({'actor_key_hex': key.hex(), 'actor_nbt_hex': raw.hex(),
                            'uid_record_keys': None})
        elif key.startswith(b'digp'):
            require(len(key) in (12, 16) and len(raw) % 8 == 0, 'Unaligned/unknown native digp record')
            indexes[key] = raw
    tracked = {key[len(recovery.ACTOR_PREFIX):] for key in wanted_keys}
    for values in drops.values():
        for record in values:
            key = bytes.fromhex(record['actor_key_hex']);tracked.add(key[len(recovery.ACTOR_PREFIX):])
            uid = recovery._uid(recovery.decode(bytes.fromhex(record['actor_nbt_hex'])))
            record['uid_record_keys'] = sorted(uid_keys.get(uid, []))
    pointer_indexes = {pointer: [] for pointer in tracked}
    for key, raw in indexes.items():
        for offset in range(0, len(raw), 8):
            pointer = raw[offset:offset + 8]
            if pointer in pointer_indexes:
                pointer_indexes[pointer].append(key.hex())
    rows = []
    for row in targets:
        key = bytes.fromhex(row['actor_key_hex']);owner = (row['authority']['scope'], row['authority']['actor_properties'].get(
            'kaleidoscope_tavern:storage_owner', row['authority']['actor_properties'].get('senluo:kcf_owner')))
        block, _ = recovery.block_at(db, row['owner_block']['position'], row['dimension_id'])
        aliases = []
        for alias in row.get('retained_aliases', []):
            alias_key = bytes.fromhex(alias['actor_key_hex'])
            aliases.append({'actor_key_hex': alias_key.hex(), 'actor_nbt_hex': actors.get(alias_key.hex()),
                            'digp_references': pointer_indexes[alias_key[len(recovery.ACTOR_PREFIX):]]})
        local_drops = drops.get(row['unique_id'], [])
        for record in local_drops:
            pointer = bytes.fromhex(record['actor_key_hex'])[len(recovery.ACTOR_PREFIX):]
            record['digp_references'] = pointer_indexes[pointer]
        rows.append({'unique_id': row['unique_id'], 'actor_key_hex': key.hex(),
            'canonical_actor_nbt_hex': actors.get(key.hex()), 'uid_record_keys': sorted(uid_keys.get(row['unique_id'], [])),
            'owner_record_keys': sorted(owner_keys.get(owner, [])),
            'digp_references': pointer_indexes[key[len(recovery.ACTOR_PREFIX):]], 'retained_aliases': aliases,
            'owner_block_nbt_hex': encode_root(nbtlib.File(block)).hex(), 'world_properties_nbt_hex': _typed_properties(world, row),
            'ordinary_items_at_former_cell': sorted(local_drops, key=lambda value: value['actor_key_hex'])})
    return {'schema': 1, 'kind': 'native_actor_conservation_observation', 'plan_sha256': recovery.digest_plan(plan),
            'targets': rows, 'observation_requirements': observation_requirements(plan),
            'native_run': None, 'writes': False, 'client': False}


def inspect_world(world, plan, *, stage_root, source_world):
    """Use the recovery tool's explicit idle-stage, nonlinked DB boundary."""
    return recovery._world_call(inspect, world, plan, stage_root=stage_root, source_world=source_world)


def _native_run(plan, observation, phase):
    run = observation.get('native_run')
    require(isinstance(run, dict), 'Native run receipt missing; planned chunks are unobserved')
    require(run.get('ok') is True and run.get('started') is True and run.get('family_initialized') is True
            and run.get('exit_code') == 0 and run.get('errors') == [] and run.get('real_player_connections') == 0
            and run.get('commands_completed') is True and run.get('stop_reason') == 'ready'
            and run.get('phase') == ('first' if phase == 'first_load' else 'restart')
            and recovery._hash(run.get('log_sha256')), 'Native run did not provide complete zero-player normal-stop evidence')
    created = run.get('ticking_areas_created');cleanup = run.get('ticking_area_cleanup_commands')
    require(isinstance(created, list) and isinstance(cleanup, list), 'Named QA area acknowledgement/cleanup evidence missing')
    actual = [(value.get('dimension'), value.get('name')) for value in created if isinstance(value, dict)]
    require(len(actual) == len(set(actual)), 'Duplicate acknowledged QA area names')
    for area in _areas(plan):
        key = (area['dimension'], area['name'])
        require(key in actual and f"execute in {area['dimension']} run tickingarea remove {area['name']}" in cleanup,
                'A planned owner chunk lacks acknowledged loading and normal area cleanup')


def _owner(tag, row):
    props = recovery._properties(tag, row['authority']['scope'])
    for name, value in row['authority']['actor_properties'].items():
        require(isinstance(props.get(name), nbtlib.String) and str(props[name]) == value, 'Original native owner/token/root changed')
    for scope, other in tag['DynamicProperties'].items():
        require(isinstance(other, nbtlib.Compound), 'Native actor has an unknown DP scope type')
        if scope != row['authority']['scope']:
            require(not (set(other) & set(row['authority']['actor_properties'])), 'Native actor has mixed owner scopes')


def _aliases(row, observation):
    expected = {alias['actor_key_hex']: alias for alias in row.get('retained_aliases', [])}
    actual = {alias['actor_key_hex']: alias for alias in observation['retained_aliases']}
    require(len(observation['retained_aliases']) == len(actual) and set(actual) == set(expected), 'Retained alias evidence is missing or duplicated')
    for key, alias in expected.items():
        observed = actual[key]
        require(observed.get('actor_nbt_hex') is not None and observed.get('digp_references') == [], 'Malformed alias disappeared or was revived/indexed')
        raw = bytes.fromhex(observed['actor_nbt_hex'])
        require(recovery.sha(raw) == alias['actor_sha256'], 'Retained malformed alias body changed')
    return set(expected)


def _target(row, original, observed):
    require(observed.get('unique_id') == row['unique_id'] and observed.get('actor_key_hex') == row['actor_key_hex'], 'Observed native target order/identity differs')
    capacity = 9 if row['family'] == 'tavern_native' else 128
    raw = recovery._hex(original.get('original_inventory_nbt_hex'), 'original typed inventory receipt')
    require(recovery.sha(raw) == row['items_sha256'] == original.get('items_sha256'), 'Original complete inventory receipt does not bind the plan')
    expected = _inventory(raw.hex(), capacity)
    block = recovery.decode(bytes.fromhex(observed['owner_block_nbt_hex']))
    require(isinstance(block.get('name'), nbtlib.String) and str(block['name']) == row['owner_block']['name']
            and recovery.block_states_digest(block) == row['owner_block']['states_sha256'], 'Original owner block/typed states changed during native loading')
    aliases = _aliases(row, observed)
    properties = recovery.decode(bytes.fromhex(observed['world_properties_nbt_hex']))
    authority = row['authority'];key = authority['key']
    pending_removed = row.get('pending_removed_bowl', False)
    if pending_removed:
        require(sum(item['count'] for item in expected.values()) == 3 and all(item['name'] == 'minecraft:bowl' for item in expected.values()), 'Pending removed source is not the original three bowls')
        require(observed.get('canonical_actor_nbt_hex') is None and observed.get('digp_references') == [], 'Original pending actor remains present or indexed')
        require(observed['uid_record_keys'] == sorted(aliases) and observed['owner_record_keys'] == sorted(aliases), 'Pending owner/UID was rebound or revived')
        require(key not in properties and key + ':remove' not in properties, 'Completed pending release did not clear the old binding/pending marker')
        before_uids = original.get('original_loose_item_uids')
        require(isinstance(before_uids, list) and all(isinstance(uid, str) for uid in before_uids), 'Original loose-item identity baseline is missing')
        metadata_counts, identities = {}, []
        for value in observed['ordinary_items_at_former_cell']:
            item_key = bytes.fromhex(value['actor_key_hex']);tag = recovery.decode(bytes.fromhex(value['actor_nbt_hex']));uid = recovery._uid(tag)
            require(uid is not None, 'Ordinary returned item lacks a native UID')
            if uid in before_uids:
                continue
            require(str(tag.get('identifier', '')) == 'minecraft:item' and uid != row['unique_id']
                    and item_key.startswith(recovery.ACTOR_PREFIX) and len(item_key) == len(recovery.ACTOR_PREFIX) + 8,
                    'Returned bowl is not a new ordinary canonical native Item')
            position, dimension = _position(tag)
            require(_drop_region(row, position, dimension), 'Returned native Item is outside the exact former owner cell')
            require(value['uid_record_keys'] == [item_key.hex()], 'Returned native Item UID is duplicated')
            pointer = item_key[len(recovery.ACTOR_PREFIX):]
            require(recovery._storage_paths(tag) == [recovery.STORAGE_PATH] and recovery._path(tag, recovery.STORAGE_PATH) == pointer,
                    'Returned native Item StorageKey is not its canonical eight-byte key')
            require(value['digp_references'] == [recovery.digp_key(position, dimension).hex()], 'Returned native Item is not indexed exactly once in its own chunk')
            item = _item(tag.get('Item'))
            require(item['count'] > 0, 'Returned native Item is empty')
            digest = item['metadata_sha256'];metadata_counts[digest] = metadata_counts.get(digest, 0) + item['count']
            identities.append({'unique_id': uid, 'actor_key_hex': item_key.hex(), 'metadata_sha256': digest, 'count': item['count']})
        expected_counts = {}
        for item in expected.values():
            digest = item['metadata_sha256'];expected_counts[digest] = expected_counts.get(digest, 0) + item['count']
        require(metadata_counts == expected_counts, 'Original three bowls did not return with complete typed native Item metadata/count')
        require(len({value['unique_id'] for value in identities}) == len(identities), 'Returned ordinary Item is counted more than once')
        return {'unique_id': row['unique_id'], 'profile': 'pending_removed_bowl', 'item_count': 3,
                'original_complete_items_preserved': True, 'old_binding_and_pending_cleared': True,
                'old_canonical_actor_absent_unindexed': True, 'retained_aliases_unindexed': True,
                'ordinary_item_identities': sorted(identities, key=lambda value: value['actor_key_hex'])}
    require(not row.get('pending_remove', False), 'A different pending native transaction needs its own reviewed conservation profile')
    require(isinstance(properties.get(key), nbtlib.String), 'Original active native binding/ledger disappeared')
    if row['family'] == 'tavern_native':
        require(json.loads(str(properties[key])) == json.loads(authority['raw']), 'Original native ledger identity/slots/token changed')
        required = properties.get(authority['required_key'])
        require(isinstance(required, NUMBERS) and float(required) == 1, 'Original native-required marker disappeared')
    else:
        require(str(properties[key]) == row['unique_id'], 'Original Cookery binding UID changed')
        pending = properties.get(key + ':remove', nbtlib.Double(0))
        require(isinstance(pending, NUMBERS) and float(pending) == 0, 'Active Cookery bowl unexpectedly entered pending removal')
    require(observed['uid_record_keys'] == sorted(aliases | {row['actor_key_hex']})
            and observed['owner_record_keys'] == sorted(aliases | {row['actor_key_hex']}), 'Original native UID/owner was duplicated or rebound')
    require(observed.get('canonical_actor_nbt_hex') is not None, 'Original native container actor is absent')
    tag = recovery.decode(bytes.fromhex(observed['canonical_actor_nbt_hex']))
    require(recovery._uid(tag) == row['unique_id'] and str(tag.get('identifier', '')) == row['identifier'], 'Original container UID/family changed')
    _owner(tag, row);position, dimension = _position(tag)
    require(dimension == row['dimension_id'] and all(abs(position[i] - row['owner_block']['position'][i] - .5) < .1 for i in (0, 2))
            and abs(position[1] - row['owner_block']['position'][1]) <= 2, 'Native actor moved outside its exact original owner cell')
    pointer = bytes.fromhex(row['storage_key']['after_hex'])
    require(recovery._storage_paths(tag) == [recovery.STORAGE_PATH] and recovery._path(tag, recovery.STORAGE_PATH) == pointer,
            'Original native container lost its canonical StorageKey')
    require(observed['digp_references'] == [row['digp']['key_hex']], 'Original native container is not indexed exactly once in its owner chunk')
    current = encode_root(nbtlib.File({'Items': tag.get(row['inventory_field'])})).hex()
    require(_inventory(current, capacity) == expected, 'Native slot/count/full typed item metadata changed')
    return {'unique_id': row['unique_id'], 'profile': row['family'], 'original_uid_and_owner_preserved': True,
            'original_complete_items_preserved': True, 'native_slots': sorted(expected),
            'item_count': sum(value['count'] for value in expected.values()), 'indexed_once': True,
            'retained_aliases_unindexed': True}


def _phase(plan, receipt, observation, phase):
    require(isinstance(observation, dict) and observation.get('schema') == 1
            and observation.get('kind') == 'native_actor_conservation_observation'
            and observation.get('plan_sha256') == recovery.digest_plan(plan) and observation.get('writes') is False,
            'Observation does not bind this exact stopped-stage plan')
    _native_run(plan, observation, phase)
    rows = plan['targets'];proof = receipt.get('targets');observed = observation.get('targets')
    require(isinstance(proof, list) and isinstance(observed, list) and len(proof) == len(observed) == len(rows), 'Native target evidence is incomplete')
    results = []
    for row, before, after in zip(rows, proof, observed):
        require(before.get('unique_id') == row['unique_id'] and before.get('actor_key_hex') == row['actor_key_hex'], 'Original recovery receipt target identity differs')
        results.append(_target(row, before, after))
    return results


def verify(plan, recovery_receipt, observed, previous=None):
    """Report refusal with the missing observation requirement; never waive items."""
    recovery._validate_plan(plan)
    phase = 'first_load' if previous is None else 'restart'
    report = {'schema': 1, 'kind': 'native_actor_conservation_verification', 'phase': phase,
              'plan_sha256': recovery.digest_plan(plan), 'ok': False, 'issues': [], 'targets': [],
              'observation_requirements': observation_requirements(plan), 'client': False, 'writes': False}
    try:
        require(isinstance(recovery_receipt, dict) and recovery_receipt.get('schema') == 1
                and recovery_receipt.get('kind') == 'native_actor_index_recovery'
                and recovery_receipt.get('plan_sha256') == recovery.digest_plan(plan), 'Recovery receipt does not bind this plan')
        results = _phase(plan, recovery_receipt, observed, phase)
        if previous is not None:
            prior = _phase(plan, recovery_receipt, previous, 'first_load')
            require(previous['native_run']['log_sha256'] != observed['native_run']['log_sha256'], 'Restart reused the first-load native run evidence')
            for before, after in zip(prior, results):
                require(before == after, 'Native restart changed full inventory/ordinary Item identity or re-dropped bowls')
            report['previous_observation_sha256'] = recovery.sha(json.dumps(previous, sort_keys=True, separators=(',', ':')).encode())
        report.update(ok=True, targets=results, original_complete_items_preserved=True,
                      named_target_chunks_observed=True, restart_no_redrop=previous is not None,
                      observation_sha256=recovery.sha(json.dumps(observed, sort_keys=True, separators=(',', ':')).encode()))
    except (ValueError, KeyError, TypeError, IndexError) as error:
        report['issues'].append(str(error))
    return report
