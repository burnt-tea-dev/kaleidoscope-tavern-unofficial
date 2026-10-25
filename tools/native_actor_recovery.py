"""Restore exact native actor pointers only in a caller-designated stopped stage.

No item creation, ledger rewrite, alias deletion, position change or LIVE opener.
The pure functions accept a controlled DB handle; *_world requires an explicit
stage/source boundary and verifies that no process holds the stage open.
"""
from pathlib import Path
import copy
import hashlib
import io
import json
import math
import re
import struct
from uuid import UUID

import nbtlib
from author_state_migration import StrictNBTStream, transform_subchunk
from bedrock_nbt import encode_root, parse_root
from container_recovery import chunk_key

ACTOR_PREFIX = b'actorprefix'
WORLD_DP = b'DynamicProperties'
FAMILIES = {'tavern_native': 'kaleidoscope_tavern:stored_items',
            'cookery_bowl': 'senluo:bowl_inventory'}
DIMENSIONS = {0: 'minecraft:overworld', 1: 'minecraft:nether', 2: 'minecraft:the_end'}
TAVERN_SCOPE = json.loads((Path(__file__).resolve().parents[1] / 'runtime/BP/manifest.json').read_text())['header']['uuid']
INVENTORIES = ('ChestItems', 'Inventory', 'Items', 'Armor', 'ArmorItems', 'Mainhand', 'HandItems', 'Offhand')
STORAGE_PATH = ('internalComponents', 'EntityStorageKeyComponent', 'StorageKey')
BOWL_ROOT_TYPE = 'kaleidoscope_chinesefood:bowl_stack'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest_plan(plan):
    return sha(json.dumps(plan, ensure_ascii=True, sort_keys=True, separators=(',', ':')).encode())


def _hex(value, label, *, length=None):
    require(isinstance(value, str) and re.fullmatch(r'(?:[0-9a-f]{2})*', value) is not None, label + ' must be lowercase bytes hex')
    raw = bytes.fromhex(value)
    require(length is None or len(raw) == length, label + ' length differs')
    return raw


def _hash(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _get(db, key):
    try:
        return db.get(key)
    except KeyError:
        return None


def decode(raw):
    require(isinstance(raw, bytes) and raw, 'missing NBT record')
    stream = StrictNBTStream(raw)
    tag = parse_root(stream)
    require(stream.tell() == len(raw), 'NBT record has an unparsed suffix')
    return tag


def items_digest(tag, field):
    """The same typed, complete inventory wrapper used by the stopped census."""
    require(field in ('ChestItems', 'Inventory', 'Items') and isinstance(tag.get(field), nbtlib.List), 'unknown inventory field')
    return sha(encode_root(nbtlib.File({'Items': tag[field]})))


def block_states_digest(block):
    require(isinstance(block.get('states'), nbtlib.Compound), 'owner block lacks typed states')
    return sha(encode_root(nbtlib.File({'states': block['states']})))


def block_at(db, position, dimension):
    """Read layer zero through the existing lossless persistent-palette parser."""
    x, y, z = position
    key = chunk_key(position, 0x2f, dimension) + struct.pack('<b', y // 16)
    raw = _get(db, key)
    require(isinstance(raw, bytes) and len(raw) >= 2, 'owner subchunk is absent')
    if raw[0] == 9:
        require(struct.unpack('<b', raw[2:3])[0] == y // 16, 'owner subchunk coordinate differs')
    selected = []
    index = (x % 16) * 256 + (z % 16) * 16 + y % 16

    def observe(tag, layer, palette_index, bits, packed):
        if layer:
            return
        target = 0
        if bits:
            per = 32 // bits
            word = struct.unpack_from('<I', packed, (index // per) * 4)[0]
            target = (word >> ((index % per) * bits)) & ((1 << bits) - 1)
        if target == palette_index:
            selected.append(tag)

    unchanged, changes = transform_subchunk(raw, {}, observe)
    require(unchanged == raw and changes == 0 and len(selected) == 1, 'owner palette is ambiguous')
    return selected[0], key


def digp_key(position, dimension):
    x, _, z = position
    return b'digp' + struct.pack('<ii', math.floor(x / 16), math.floor(z / 16)) + (struct.pack('<i', dimension) if dimension else b'')


def _uid(tag):
    value = tag.get('UniqueID')
    return str(int(value)) if isinstance(value, nbtlib.Long) else None


def _properties(tag, scope):
    root = tag.get('DynamicProperties')
    require(isinstance(root, nbtlib.Compound) and isinstance(root.get(scope), nbtlib.Compound), 'actor owner scope is absent')
    return root[scope]


def _path(tag, path):
    node = tag
    for name in path:
        require(isinstance(node, nbtlib.Compound) and name in node, 'StorageKey path is absent')
        node = node[name]
    require(isinstance(node, nbtlib.String), 'StorageKey must remain TAG_String')
    return str(node).encode('utf-8', 'surrogateescape')


def _replace_path(tag, path, value):
    node = tag
    for name in path[:-1]:
        node = node[name]
    node[path[-1]] = nbtlib.String(value.decode('utf-8', 'surrogateescape'))


def _storage_paths(tag, prefix=()):
    result = []
    if isinstance(tag, nbtlib.Compound):
        for name, value in tag.items():
            path = (*prefix, name)
            if name == 'StorageKey':
                result.append(path)
            result.extend(_storage_paths(value, path))
    elif isinstance(tag, nbtlib.List):
        for index, value in enumerate(tag):
            result.extend(_storage_paths(value, (*prefix, index)))
    return result


def _inventory(tag, row):
    field = row['inventory_field']
    require(items_digest(tag, field) == row['items_sha256'], 'original complete inventory digest differs')
    inventory = tag[field]
    require(inventory.subtype is nbtlib.Compound and len(inventory) <= 256, 'unknown typed inventory list')
    slots = {}
    for item in inventory:
        slot, name, count = item.get('Slot'), item.get('Name'), item.get('Count')
        require(isinstance(slot, nbtlib.Byte) and isinstance(name, nbtlib.String) and isinstance(count, nbtlib.Byte), 'unknown inventory slot encoding')
        slot, name, count = int(slot), str(name), int(count)
        require(0 <= slot < (9 if row['family'] == 'tavern_native' else 128) and slot not in slots, 'duplicate/out-of-range inventory slot')
        require(0 <= count <= 127 and bool(name) == (count > 0), 'invalid source stack')
        slots[slot] = (name, count)
    require(any(count for _, count in slots.values()), 'only exact nonempty recovery targets are admitted')
    for other in INVENTORIES:
        if other == field or other not in tag:
            continue
        value = tag[other]
        require(isinstance(value, nbtlib.List), 'unknown additional inventory encoding')
        require(all(isinstance(item, nbtlib.Compound) and not str(item.get('Name', '')) and int(item.get('Count', 0)) == 0 for item in value), 'another inventory contains unreviewed items')
    return slots


def _validate_plan(plan):
    require(isinstance(plan, dict) and type(plan.get('schema')) is int and plan['schema'] == 1, 'unsupported native actor recovery plan')
    require(isinstance(plan.get('source'), str) and 0 < len(plan['source']) <= 1024, 'missing exact recovery provenance')
    require(_hash(plan.get('world_dp_sha256')), 'missing original world DP digest')
    targets = plan.get('targets')
    require(isinstance(targets, list) and 1 <= len(targets) <= 16, 'recovery requires one to sixteen exact targets')
    scopes = plan.get('active_scopes')
    require(isinstance(scopes, dict) and set(scopes) <= set(FAMILIES) and scopes.get('tavern_native') == TAVERN_SCOPE, 'active Tavern owner differs')
    require(all(isinstance(v, str) and str(UUID(v)) == v for v in scopes.values()), 'invalid active owner scope')
    keys, uids, positions = set(), set(), set()
    for row in targets:
        require(row.get('family') in FAMILIES and row.get('identifier') == FAMILIES[row['family']], 'foreign actor family')
        key = _hex(row.get('actor_key_hex'), 'actor key')
        require(key.startswith(ACTOR_PREFIX) and len(key) == len(ACTOR_PREFIX) + 8 and key not in keys, 'actor key must be one unique canonical eight-byte key')
        keys.add(key)
        uid = row.get('unique_id')
        require(isinstance(uid, str) and re.fullmatch(r'-?(?:0|[1-9][0-9]*)', uid) and -(1 << 63) <= int(uid) < (1 << 63) and uid not in uids, 'duplicate/invalid target UID')
        uids.add(uid)
        require(_hash(row.get('actor_sha256')) and _hash(row.get('items_sha256')), 'missing exact actor/inventory digest')
        require(row.get('dimension_id') in DIMENSIONS and type(row['dimension_id']) is int, 'unsupported actor dimension')
        require(isinstance(row.get('position'), list) and len(row['position']) == 3 and all(type(v) in (int, float) and math.isfinite(v) for v in row['position']), 'invalid original actor position')
        block = row.get('owner_block', {})
        require(type(block.get('dimension_id')) is int and block['dimension_id'] == row['dimension_id'] and isinstance(block.get('position'), list) and len(block['position']) == 3 and all(type(v) is int for v in block['position']), 'invalid owner block position/dimension')
        require(isinstance(block.get('name'), str) and _hash(block.get('states_sha256')), 'missing typed owner block proof')
        removed_bowl = row.get('pending_removed_bowl', False)
        require(type(removed_bowl) is bool, 'pending_removed_bowl must be an explicit boolean')
        allowed = ('kaleidoscope_tavern:', 'kaleidoscope_world_liquor:') if row['family'] == 'tavern_native' else ('kaleidoscope_chinesefood:',)
        if removed_bowl:
            require(row['family'] == 'cookery_bowl' and row.get('pending_remove') is True
                    and block['name'] == 'minecraft:air', 'pending_removed_bowl requires the exact pending bowl/air profile')
        else:
            require(block['name'].startswith(allowed), 'foreign owner block')
        owner = (row['dimension_id'], *block['position'])
        require(owner not in positions, 'duplicate recovery owner cell')
        positions.add(owner)
        storage = row.get('storage_key', {})
        path = storage.get('path')
        require(isinstance(path, list) and tuple(path) == STORAGE_PATH, 'unknown StorageKey path')
        before = _hex(storage.get('before_hex'), 'StorageKey preimage')
        after = _hex(storage.get('after_hex'), 'StorageKey postimage', length=8)
        require(after == key[len(ACTOR_PREFIX):], 'StorageKey is not the canonical DB pointer')
        if before != after:
            replacement = after.decode('utf-8', 'replace').encode('utf-8')
            require(row['family'] == 'cookery_bowl' and before == replacement and b'\xef\xbf\xbd' in before and len(before) > 8, 'only proved UTF-8 replacement StorageKey repair is admitted')
        index = row.get('digp', {})
        require('before_hex' in index, 'digp absence/preimage must be explicit')
        require(_hex(index.get('key_hex'), 'digp key') == digp_key(row['position'], row['dimension_id']), 'planned digp chunk/dimension differs')
        if index.get('before_hex') is not None:
            require(len(_hex(index['before_hex'], 'digp preimage')) % 8 == 0, 'unaligned planned digp preimage')
        authority = row.get('authority', {})
        require(authority.get('scope') == scopes.get(row['family']) and isinstance(authority.get('key'), str) and isinstance(authority.get('raw'), str), 'active authority scope/key/raw differs')
        require(authority.get('kind') == ('ledger' if row['family'] == 'tavern_native' else 'binding'), 'wrong authority kind')
        props = authority.get('actor_properties')
        required = {'kaleidoscope_tavern:storage_owner', 'kaleidoscope_tavern:storage_token'} if row['family'] == 'tavern_native' else {'senluo:kcf_owner', 'senluo:kcf_root'}
        require(isinstance(props, dict) and set(props) == required and all(isinstance(v, str) and v for v in props.values()), 'missing exact actor owner/token/root')
        aliases = row.get('retained_aliases', [])
        require(isinstance(aliases, list) and len(aliases) <= (1 if row['family'] == 'cookery_bowl' else 0), 'unreviewed actor aliases')
        for alias in aliases:
            alias_key = _hex(alias.get('actor_key_hex'), 'alias key')
            require(before != after and alias_key == ACTOR_PREFIX + before and alias_key not in keys, 'alias is not the proved malformed pointer key')
            require(_hash(alias.get('actor_sha256')) and alias.get('items_sha256') == row['items_sha256'], 'alias inventory differs from the original canonical inventory')
            keys.add(alias_key)
    return targets


def _summarize(records, exclude=()):
    digest = hashlib.sha256()
    count = 0
    for key in sorted(set(records) - set(exclude)):
        size, value_sha = records[key]
        digest.update(struct.pack('<Q', len(key))); digest.update(key)
        digest.update(struct.pack('<Q', size)); digest.update(value_sha)
        count += 1
    return {'records': count, 'sha256': digest.hexdigest()}


def _authority(world, tag, row, slots):
    authority = row['authority']; scope = authority['scope']
    props = _properties(tag, scope)
    expected = authority['actor_properties']
    for name, value in expected.items():
        require(isinstance(props.get(name), nbtlib.String) and str(props[name]) == value, 'actor owner/token/root differs')
    for other_scope, other in tag['DynamicProperties'].items():
        require(isinstance(other, nbtlib.Compound), 'unknown actor DP scope')
        if other_scope != scope:
            require(not (set(expected) & set(other)), 'mixed actor owner scopes')
    owner = world.get(scope)
    require(isinstance(owner, nbtlib.Compound) and isinstance(owner.get(authority['key']), nbtlib.String) and str(owner[authority['key']]) == authority['raw'], 'original active ledger/binding differs')
    block = row['owner_block']; dimension = DIMENSIONS[row['dimension_id']]
    if row['family'] == 'tavern_native':
        key = authority['key']
        require(key.startswith('kt:native_items/'), 'wrong native ledger key')
        storage = key[len('kt:native_items/'):]
        record = json.loads(authority['raw'])
        require(record.get('schema') == 1 and record.get('key') == storage and record.get('entity') == row['unique_id'] and record.get('dimension') == dimension and record.get('position') == dict(zip(('x', 'y', 'z'), block['position'])), 'native ledger identity/root differs')
        require(expected['kaleidoscope_tavern:storage_owner'] == storage and expected['kaleidoscope_tavern:storage_token'] == record.get('token'), 'native ledger owner/token differs')
        required = owner.get(authority.get('required_key'))
        numbers = (nbtlib.Byte, nbtlib.Short, nbtlib.Int, nbtlib.Long, nbtlib.Float, nbtlib.Double)
        require(authority.get('required_key') == 'kt:native_required/' + storage and type(authority.get('required_value')) is int and authority['required_value'] == 1 and isinstance(required, numbers) and float(required) == 1, 'native required marker differs')
        ids = record.get('ids')
        require(isinstance(ids, list) and len(ids) == 9 and all(v is None or isinstance(v, str) and v for v in ids), 'unknown native ledger slots')
        # This reviewed recovery profile covers the shared World Liquor cabinet
        # anchors in this repair. Other stored-items layouts need their own
        # owner/slot proof instead of accepting any block in an owned namespace.
        anchor = re.fullmatch(r'kt:extension_storage/kaleidoscope_world_liquor/(oak|birch|spruce|dark_oak|cherry)_(bar_cabinet|cellar_cabinet)/(overworld|nether|the_end)/(-?\d+)_(-?\d+)_(-?\d+)', storage)
        require(anchor is not None and block['name'] == 'kaleidoscope_world_liquor:' + anchor[1] + '_' + anchor[2] and dimension == 'minecraft:' + anchor[3] and block['position'] == [int(anchor[i]) for i in (4, 5, 6)], 'native anchor does not describe the original owner block')
        capacity = 2 if anchor[2] == 'bar_cabinet' else 9
        require(all(value is None for value in ids[capacity:]), 'native slots exceed the original cabinet layout')
        for i, item_id in enumerate(ids):
            name, count = slots.get(i, ('', 0))
            require((name == item_id and count == 1) if item_id else (not name and count == 0), 'full native slots differ from ledger')
        require(all(abs(float(tag['Pos'][i]) - block['position'][i] - .5) < .1 for i in range(3)), 'native actor is not at its owner cell')
    else:
        key = 'senluo:kcf_inventory:' + dimension + ':' + ','.join(map(str, block['position']))
        require(authority['key'] == key and authority['raw'] == row['unique_id'] and expected['senluo:kcf_owner'] == key, 'bowl active binding/owner differs')
        root = json.loads(expected['senluo:kcf_root'])
        root_type = BOWL_ROOT_TYPE if row.get('pending_removed_bowl', False) else block['name']
        require(root == {'dimension': dimension, **dict(zip(('x', 'y', 'z'), block['position'])), 'type': root_type}, 'bowl root does not describe the exact original owner block')
        pending = owner.get(key + ':remove', nbtlib.Double(0))
        require(isinstance(pending, (nbtlib.Byte, nbtlib.Short, nbtlib.Int, nbtlib.Long, nbtlib.Float, nbtlib.Double)) and float(pending) in (0, 1) and type(row.get('pending_remove', False)) is bool and bool(pending) == row.get('pending_remove', False), 'pending bowl removal must be explicit; no inventory waiver')
        if row.get('pending_removed_bowl', False):
            # The sole admitted removed-block profile completes the existing
            # pending break transaction. Air is never a normal storage owner;
            # all original item metadata remains bound by items_sha256 above.
            require(sum(count for _, count in slots.values()) == 3
                    and all(not count or name == 'minecraft:bowl' for name, count in slots.values()),
                    'pending_removed_bowl requires the original three complete native bowls')
        require(all(abs(float(tag['Pos'][i]) - block['position'][i] - .5) < .1 for i in (0, 2)) and abs(float(tag['Pos'][1]) - block['position'][1]) <= 2, 'bowl actor is outside its original owner cell')


def _scan(db, targets):
    records, uid_records, pointers = {}, {}, {bytes.fromhex(r['actor_key_hex'])[len(ACTOR_PREFIX):]: [] for r in targets}
    loose_item_uids = set()
    target_uids = {r['unique_id'] for r in targets}
    owners = {(r['authority']['scope'], r['authority']['actor_properties'].get('kaleidoscope_tavern:storage_owner', r['authority']['actor_properties'].get('senluo:kcf_owner'))): r for r in targets}
    for key, raw in db.items():
        require(isinstance(key, bytes) and isinstance(raw, bytes) and key not in records, 'unknown/duplicate DB record')
        records[key] = (len(raw), hashlib.sha256(raw).digest())
        if key.startswith(ACTOR_PREFIX):
            tag = decode(raw); uid = _uid(tag)
            if str(tag.get('identifier', '')) == 'minecraft:item':
                require(uid is not None, 'native loose item lacks its original UID')
                loose_item_uids.add(uid)
            if uid in target_uids:
                uid_records.setdefault(uid, []).append(key)
            for scope, props in tag.get('DynamicProperties', {}).items():
                if not isinstance(props, nbtlib.Compound):
                    continue
                for prop in ('kaleidoscope_tavern:storage_owner', 'senluo:kcf_owner'):
                    owner = (scope, str(props.get(prop, '')))
                    if owner in owners:
                        require(uid == owners[owner]['unique_id'], 'another UID claims the planned owner')
        elif key.startswith(b'digp'):
            require(len(key) in (12, 16) and len(raw) % 8 == 0, 'unaligned/unknown digp record')
            for offset in range(0, len(raw), 8):
                pointer = raw[offset:offset + 8]
                if pointer in pointers:
                    pointers[pointer].append(key)
    return records, uid_records, pointers, sorted(loose_item_uids)


def _prepare(db, plan):
    targets = _validate_plan(plan)
    original, uid_records, pointers, loose_item_uids = _scan(db, targets)
    dp_raw = _get(db, WORLD_DP)
    require(sha(dp_raw or b'') == plan['world_dp_sha256'], 'world dynamic properties changed')
    world = decode(dp_raw)
    expected_indexes, additions, before_actors, after_actors, protected, proof = {}, {}, {}, {}, {WORLD_DP}, []
    references = {r['unique_id']: [] for r in targets}
    for family, scope in plan['active_scopes'].items():
        owner = world.get(scope, {})
        require(isinstance(owner, nbtlib.Compound), 'active world owner scope is absent')
        for key, value in owner.items():
            uid = None
            if family == 'tavern_native' and key.startswith('kt:native_items/'):
                require(isinstance(value, nbtlib.String), 'unknown native ledger type')
                record = json.loads(str(value));uid = record.get('entity')
            elif family == 'cookery_bowl' and re.fullmatch(r'senluo:kcf_inventory:minecraft:(overworld|nether|the_end):-?\d+,-?\d+,-?\d+', key):
                require(isinstance(value, nbtlib.String), 'unknown bowl binding type');uid = str(value)
            if uid in references:
                references[uid].append((scope, key))
    for row in targets:
        key = bytes.fromhex(row['actor_key_hex']); pointer = key[len(ACTOR_PREFIX):]
        raw = _get(db, key);tag = decode(raw)
        require(_uid(tag) == row['unique_id'] and isinstance(tag.get('identifier'), nbtlib.String) and str(tag['identifier']) == row['identifier'], 'canonical actor UID/family differs')
        dimension = tag.get('DimensionId', nbtlib.Int(0))
        require(isinstance(dimension, nbtlib.Int) and int(dimension) == row['dimension_id'] and isinstance(tag.get('Pos'), nbtlib.List) and len(tag['Pos']) == 3 and [float(v) for v in tag['Pos']] == row['position'], 'original actor position/dimension differs')
        path = row['storage_key']['path'];before_key = bytes.fromhex(row['storage_key']['before_hex']);after_key = pointer
        require(_storage_paths(tag) == [tuple(path)], 'unknown or duplicate StorageKey fields')
        current_key = _path(tag, path)
        require(current_key in (before_key, after_key), 'StorageKey differs from both exact plan states')
        before_tag = copy.deepcopy(tag);_replace_path(before_tag, path, before_key)
        before_raw = encode_root(before_tag)
        require(sha(before_raw) == row['actor_sha256'], 'original actor body digest differs')
        after_tag = copy.deepcopy(before_tag);_replace_path(after_tag, path, after_key)
        after_raw = encode_root(after_tag)
        require(raw in (before_raw, after_raw), 'actor contains an unplanned change')
        slots = _inventory(tag, row);_authority(world, tag, row, slots)
        block, block_key = block_at(db, row['owner_block']['position'], row['dimension_id'])
        require(isinstance(block.get('name'), nbtlib.String) and str(block['name']) == row['owner_block']['name'] and block_states_digest(block) == row['owner_block']['states_sha256'], 'foreign owner block or typed states')
        protected.update((key, block_key))
        aliases = row.get('retained_aliases', []);approved = {key}
        for alias in aliases:
            alias_key = bytes.fromhex(alias['actor_key_hex']);alias_raw = _get(db, alias_key);alias_tag = decode(alias_raw)
            require(sha(alias_raw) == alias['actor_sha256'] and _uid(alias_tag) == row['unique_id'] and str(alias_tag.get('identifier', '')) == row['identifier'], 'retained alias identity/body differs')
            require(items_digest(alias_tag, row['inventory_field']) == row['items_sha256'] and _path(alias_tag, path) == before_key, 'retained alias inventory/StorageKey differs')
            require(int(alias_tag.get('DimensionId', 0)) == row['dimension_id'] and [float(v) for v in alias_tag.get('Pos', [])] == row['position'], 'retained alias position/dimension differs')
            _authority(world, alias_tag, row, _inventory(alias_tag, row))
            approved.add(alias_key);protected.add(alias_key)
        require(set(uid_records.get(row['unique_id'], [])) == approved, 'unreviewed duplicate UID or missing canonical actor/alias')
        require(references[row['unique_id']] == [(row['authority']['scope'], row['authority']['key'])], 'another active ledger/binding claims the target UID')
        index = bytes.fromhex(row['digp']['key_hex'])
        before_index = None if row['digp']['before_hex'] is None else bytes.fromhex(row['digp']['before_hex'])
        if index in expected_indexes:
            require(expected_indexes[index] == before_index, 'shared digp preimages differ')
        else:
            expected_indexes[index] = before_index
        additions.setdefault(index, []).append(pointer)
        before_actors[key], after_actors[key] = before_raw, after_raw
        proof.append({'actor_key_hex': key.hex(), 'unique_id': row['unique_id'], 'identifier': row['identifier'], 'items_sha256': row['items_sha256'],
                      'original_inventory_nbt_hex': encode_root(nbtlib.File({'Items': tag[row['inventory_field']]})).hex(),
                      'occupied_slots': sum(count > 0 for _, count in slots.values()), 'item_count': sum(count for _, count in slots.values()),
                      'actor_before_sha256': sha(before_raw), 'actor_after_sha256': sha(after_raw), 'storage_key_changed': before_raw != after_raw,
                      'digp_key_hex': index.hex(), 'retained_alias_keys': sorted(k.hex() for k in approved - {key}),
                      'pending_remove': row.get('pending_remove', False), 'first_load': 'NOT_VERIFIED', 'restart': 'NOT_VERIFIED'})
        if row.get('pending_removed_bowl', False):
            proof[-1]['pending_removed_bowl'] = True
            proof[-1]['original_loose_item_uids'] = loose_item_uids
    after_indexes = {}
    for key, before in expected_indexes.items():
        existing = [before[i:i + 8] for i in range(0, len(before or b''), 8)]
        require(len(existing) == len(set(existing)) and not (set(existing) & set(pointers)), 'planned digp preimage already contains a target/duplicate pointer')
        after_indexes[key] = (before or b'') + b''.join(sorted(additions[key]))
    pre = all(_get(db, k) == v for k, v in expected_indexes.items()) and all(_get(db, k) == v for k, v in before_actors.items())
    post = all(_get(db, k) == v for k, v in after_indexes.items()) and all(_get(db, k) == v for k, v in after_actors.items())
    require(pre or post, 'partial/conflicting recovery state; keep stage stopped')
    for row in targets:
        pointer = bytes.fromhex(row['actor_key_hex'])[len(ACTOR_PREFIX):]
        require(pointers[pointer] == ([] if pre else [bytes.fromhex(row['digp']['key_hex'])]), 'target pointer exists in another/duplicate index')
    updates = {key: value for key, value in after_actors.items() if value != before_actors[key]}
    updates.update(after_indexes)
    protected.update(expected_indexes)
    return {'state': 'before' if pre else 'after', 'updates': updates, 'original': original, 'protected': protected,
            'proof': proof, 'before': _summarize(original), 'unrelated': _summarize(original, updates), 'plan_sha256': digest_plan(plan)}


def inspect(db, plan):
    prepared = _prepare(db, plan)
    return {'schema': 1, 'kind': 'native_actor_recovery_inspection', 'state': prepared['state'], 'plan_sha256': prepared['plan_sha256'],
            'database': prepared['before'], 'unrelated_records': prepared['unrelated'], 'targets': prepared['proof'],
            'planned_mutation_keys': sorted(key.hex() for key in prepared['updates']), 'writes': False}


def _verify_records(db, original, updates):
    seen = set();after = {}
    for key, raw in db.items():
        require(key not in seen, 'duplicate DB key after recovery');seen.add(key)
        expected = updates.get(key)
        if expected is not None:
            require(raw == expected, 'planned recovery postimage differs')
        else:
            require(key in original and (len(raw), hashlib.sha256(raw).digest()) == original[key], 'unrelated DB content changed; keep stage stopped')
        after[key] = (len(raw), hashlib.sha256(raw).digest())
    require(seen == set(original) | set(updates), 'unexpected DB key creation/removal; keep stage stopped')
    return after


def recover(db, plan):
    """Preflight every target/index, then one atomic putBatch; never delete."""
    prepared = _prepare(db, plan);updates = prepared['updates'];original = prepared['original']
    for key in prepared['protected']:
        raw = _get(db, key)
        current = None if raw is None else (len(raw), hashlib.sha256(raw).digest())
        require(current == original.get(key), 'recovery preimage changed before batch')
    idempotent = prepared['state'] == 'after'
    if not idempotent:
        try:
            db.putBatch(updates)
        except Exception as error:
            # The adapter promises atomic batches. A broken adapter or external
            # writer must never yield a success receipt or trigger auto-repair.
            try:
                _verify_records(db, original, {})
            except Exception as changed:
                raise ValueError('failed batch changed the stage; keep stopped for review') from changed
            raise ValueError('atomic batch failed without logical writes') from error
    after = _verify_records(db, original, updates if not idempotent else {})
    require(_summarize(after, updates) == prepared['unrelated'], 'unrelated summary changed')
    return {'schema': 1, 'kind': 'native_actor_index_recovery', 'source': plan['source'], 'plan_sha256': prepared['plan_sha256'],
            'idempotent': idempotent, 'before': prepared['before'], 'after': _summarize(after),
            'unrelated_before': prepared['unrelated'], 'unrelated_after': _summarize(after, updates),
            'targets': prepared['proof'], 'changed_keys': [] if idempotent else sorted(k.hex() for k in updates),
            'planned_mutation_keys': sorted(k.hex() for k in updates), 'world_dp_sha256': plan['world_dp_sha256'],
            'only_planned_keys_changed': True, 'items_materialized': False, 'aliases_deleted': False,
            'native_loading': False, 'first_load': False, 'restart': False, 'client': False}


def verify(db, plan, receipt):
    """Exact post-batch verification before BDS; engine runs need the template."""
    require(receipt.get('schema') == 1 and receipt.get('kind') == 'native_actor_index_recovery' and receipt.get('plan_sha256') == digest_plan(plan), 'recovery receipt does not bind this plan')
    prepared = _prepare(db, plan)
    require(prepared['state'] == 'after' and prepared['unrelated'] == receipt.get('unrelated_after'), 'post-recovery bytes/unrelated summary differ')
    require(prepared['proof'] == receipt.get('targets'), 'post-recovery target invariants differ')
    return {'schema': 1, 'ok': True, 'phase': 'before_native_load', 'plan_sha256': digest_plan(plan),
            'unrelated_records_preserved': True, 'complete_items_preserved': True, 'first_load': False, 'restart': False, 'client': False}


def native_verification_template(plan, receipt):
    require(receipt.get('plan_sha256') == digest_plan(plan), 'receipt/plan differs')
    targets = []
    for row, proof in zip(plan['targets'], receipt['targets']):
        target = copy.deepcopy(proof)
        target.update(family=row['family'], dimension_id=row['dimension_id'], position=copy.deepcopy(row['position']),
                      owner_block=copy.deepcopy(row['owner_block']), authority=copy.deepcopy(row['authority']),
                      inventory_field=row['inventory_field'], expected_storage_key_hex=row['storage_key']['after_hex'])
        if row.get('pending_remove', False):
            target['required_runtime_transition'] = {'original_uid': row['unique_id'], 'original_items_sha256': row['items_sha256'],
                'original_item_count': proof['item_count'], 'exact_once_returned_items_proof': None,
                'old_binding_retired': None, 'new_binding_uid': None, 'new_inventory_initially_empty': None, 'ok': False}
            if row.get('pending_removed_bowl', False):
                target['required_runtime_transition'].update(profile='pending_removed_bowl',
                    original_root_type=BOWL_ROOT_TYPE, observed_owner_block='minecraft:air',
                    complete_returned_item_metadata_proof=None, first_load_returned_item_count=None,
                    pending_marker_cleared=None, old_actor_removed=None,
                    restart_total_returned_item_count=None, restart_did_not_redrop=None)
        targets.append(target)
    return {'schema': 1, 'plan_sha256': digest_plan(plan), 'phases': {phase: {'ok': False, 'observed': None,
        'requirements': ['original UID/owner/token or active binding/root', 'canonical eight-byte StorageKey and exactly one correct digp pointer',
                         'complete native inventory metadata/count conservation; no fallback from a JSON index',
                         'pending_remove requires exact-once runtime transfer of every original item before any replacement binding'],
        'targets': copy.deepcopy(targets)} for phase in ('first_load', 'restart')},
        'native_loading': False, 'client': False, 'limits': 'Template only; no pending-removal target may skip original inventory conservation.'}


def _stage(world, plan, stage_root, source_world):
    world, stage_root, source_world = (Path(p) for p in (world, stage_root, source_world))
    require(all(p.is_absolute() and p.exists() and p.resolve() == p for p in (world, stage_root, source_world)), 'use exact existing nonsymlink stage/source paths')
    require(world != stage_root and stage_root in world.parents and world != source_world and source_world not in world.parents and world not in source_world.parents and source_world not in stage_root.parents and stage_root not in source_world.parents, 'refusing a LIVE/source or overlapping world path')
    for path in (world, world / 'db'):
        require(path.is_dir() and not path.is_symlink(), 'invalid staged world/database')
    for path in (world / 'db').rglob('*'):
        require(not path.is_symlink() and (not path.is_file() or path.stat().st_nlink == 1), 'staged DB contains a symlink/shared file')
    active = json.loads((world / 'world_behavior_packs.json').read_text())
    require(isinstance(active, list), 'missing stage pack ownership list')
    ids = {row.get('pack_id') for row in active if isinstance(row, dict)}
    require(set(plan['active_scopes'].values()) <= ids, 'plan owner scope is not active in the isolated stage')
    from family_update.storage import assert_idle
    assert_idle(world)
    return world


def _world_call(fn, world, plan, *, stage_root, source_world, receipt=None):
    _validate_plan(plan)
    world = _stage(world, plan, stage_root, source_world)
    from leveldb import LevelDB
    db = LevelDB(str(world / 'db'))
    try:
        return fn(db, plan, receipt) if receipt is not None else fn(db, plan)
    finally:
        db.close()


def inspect_world(world, plan, *, stage_root, source_world):
    return _world_call(inspect, world, plan, stage_root=stage_root, source_world=source_world)


def recover_world(world, plan, *, stage_root, source_world):
    return _world_call(recover, world, plan, stage_root=stage_root, source_world=source_world)


def verify_world(world, plan, receipt, *, stage_root, source_world):
    return _world_call(verify, world, plan, stage_root=stage_root, source_world=source_world, receipt=receipt)
