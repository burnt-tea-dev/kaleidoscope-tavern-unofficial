"""Synthetic atomic/index/metadata regressions; no private world data or BDS."""
import copy
import json
import os
from pathlib import Path
import struct
import tempfile
import types
import unittest
from unittest.mock import patch

import nbtlib
from bedrock_nbt import encode_root
import native_actor_recovery as recovery

CF_SCOPE = '11111111-2222-4333-8444-555555555555'
STORAGE_PATH = ['internalComponents', 'EntityStorageKeyComponent', 'StorageKey']


class Database(dict):
    def __init__(self, values):
        super().__init__(values);self.batches = 0;self.closed = False;self.failure = None
    def get(self, key):
        return self[key]
    def putBatch(self, updates):
        self.batches += 1
        if self.failure == 'atomic':
            raise OSError('injected atomic failure')
        if self.failure == 'partial':
            key = next(iter(updates));self[key] = updates[key]
            raise OSError('injected broken adapter')
        self.update(updates)
        if self.failure == 'unrelated':
            self[b'player_synthetic'] = b'changed unexpectedly'
    def close(self):
        self.closed = True


def string(raw):
    return nbtlib.String(raw.decode('utf-8', 'surrogateescape'))


def stack(slot, item):
    return nbtlib.Compound({'Slot': nbtlib.Byte(slot), 'Name': nbtlib.String(item), 'Count': nbtlib.Byte(1),
        'tag': nbtlib.Compound({'display': nbtlib.Compound({'Name': nbtlib.String('original synthetic metadata'), 'Lore': nbtlib.List[nbtlib.String](['one original item'])}),
            'ench': nbtlib.List[nbtlib.Compound]([nbtlib.Compound({'id': nbtlib.Short(16), 'lvl': nbtlib.Short(3)})]),
            'opaque': string(b'\xff\x00\x80keep')})})


def actor(uid, identifier, pointer, position, scope, props, item, count=1):
    return nbtlib.File({'UniqueID': nbtlib.Long(uid), 'identifier': nbtlib.String(identifier), 'DimensionId': nbtlib.Int(0),
        'Pos': nbtlib.List[nbtlib.Float](position), 'ChestItems': nbtlib.List[nbtlib.Compound]([stack(i, item) for i in range(count)]),
        'DynamicProperties': nbtlib.Compound({scope: nbtlib.Compound({name: nbtlib.String(value) for name, value in props.items()})}),
        'internalComponents': nbtlib.Compound({'EntityStorageKeyComponent': nbtlib.Compound({'StorageKey': string(pointer)})}),
        'unknown_component': nbtlib.Compound({'binary_string': string(b'\x81\xff\x00opaque'), 'number': nbtlib.Int(27)})})


def palette(blocks, positions):
    words = [0] * 128
    for selected, position in enumerate(positions):
        x, y, z = position;i = (x % 16) * 256 + (z % 16) * 16 + y % 16
        words[i // 32] |= selected << (i % 32)
    return b'\x09\x01\x04\x02' + struct.pack('<' + 'I' * 128, *words) + struct.pack('<I', len(blocks)) + b''.join(encode_root(block) for block in blocks)


def fixture():
    positions = [(48, 64, 32), (49, 64, 32)]
    native_pointer = b'\x01\x00\x00\x00\x02\x00\x00\x00'
    bowl_pointer = b'\x00\x00\x00\x80\x00\x00\x00\xff'
    malformed = bowl_pointer.decode('utf-8', 'replace').encode()
    block_names = ['kaleidoscope_world_liquor:oak_bar_cabinet', 'kaleidoscope_chinesefood:bowl_stack']
    blocks = [nbtlib.File({'name': nbtlib.String(name), 'states': nbtlib.Compound({'synthetic:facing': nbtlib.Int(0)}), 'version': nbtlib.Int(1)}) for name in block_names]
    native_key = 'kt:extension_storage/kaleidoscope_world_liquor/oak_bar_cabinet/overworld/48_64_32'
    native_item = 'kaleidoscope_world_liquor:gin_q1'
    native_props = {'kaleidoscope_tavern:storage_owner': native_key, 'kaleidoscope_tavern:storage_token': 'original-token'}
    bowl_key = 'senluo:kcf_inventory:minecraft:overworld:49,64,32'
    bowl_props = {'senluo:kcf_owner': bowl_key, 'senluo:kcf_root': json.dumps({'dimension': 'minecraft:overworld', 'x': 49, 'y': 64, 'z': 32, 'type': block_names[1]})}
    tags = [actor(101, recovery.FAMILIES['tavern_native'], native_pointer, (48.5, 64.5, 32.5), recovery.TAVERN_SCOPE, native_props, native_item),
            actor(202, recovery.FAMILIES['cookery_bowl'], malformed, (49.5, 64.75, 32.5), CF_SCOPE, bowl_props, 'kaleidoscope_chinesefood:bowl', 3)]
    raw = [encode_root(tag) for tag in tags]
    alias_tag = copy.deepcopy(tags[1]);alias_tag['unrelated_alias_state'] = nbtlib.Int(91)
    alias_raw = encode_root(alias_tag)
    ledger = {'schema': 1, 'key': native_key, 'entity': '101', 'dimension': 'minecraft:overworld', 'position': dict(zip(('x', 'y', 'z'), positions[0])), 'ids': [native_item] + [None] * 8, 'token': 'original-token'}
    ledger_raw = json.dumps(ledger)
    world = nbtlib.File({recovery.TAVERN_SCOPE: nbtlib.Compound({'kt:native_items/' + native_key: nbtlib.String(ledger_raw), 'kt:native_required/' + native_key: nbtlib.Double(1), native_key: nbtlib.String('{"revision":1}') }),
                        CF_SCOPE: nbtlib.Compound({bowl_key: nbtlib.String('202'), bowl_key + ':remove': nbtlib.Double(1)}),
                        'foreign_scope': nbtlib.Compound({'opaque': string(b'\xff\x80world')})})
    world_raw = encode_root(world)
    index = recovery.digp_key((48.5, 64.5, 32.5), 0)
    owner_chunk = recovery.chunk_key(positions[0], 0x2f) + b'\x04'
    unrelated_pointer = b'unrelPtr'
    unrelated_actor = nbtlib.File({'UniqueID': nbtlib.Long(999), 'identifier': nbtlib.String('minecraft:cow'), 'opaque': string(b'\xffkeep')})
    db = Database({recovery.WORLD_DP: world_raw, recovery.ACTOR_PREFIX + native_pointer: raw[0], recovery.ACTOR_PREFIX + bowl_pointer: raw[1],
                   recovery.ACTOR_PREFIX + malformed: alias_raw, recovery.ACTOR_PREFIX + unrelated_pointer: encode_root(unrelated_actor),
                   index: unrelated_pointer, owner_chunk: palette(blocks, positions), b'player_synthetic': b'full original player bytes\x00\xff'})
    targets = []
    for i, (family, pointer, tag) in enumerate(zip(recovery.FAMILIES, [native_pointer, bowl_pointer], tags)):
        authority = {'scope': recovery.TAVERN_SCOPE if i == 0 else CF_SCOPE, 'kind': 'ledger' if i == 0 else 'binding',
                     'key': 'kt:native_items/' + native_key if i == 0 else bowl_key, 'raw': ledger_raw if i == 0 else '202',
                     'actor_properties': native_props if i == 0 else bowl_props}
        if i == 0:
            authority.update(required_key='kt:native_required/' + native_key, required_value=1)
        row = {'family': family, 'actor_key_hex': (recovery.ACTOR_PREFIX + pointer).hex(), 'actor_sha256': recovery.sha(raw[i]), 'unique_id': str(101 if i == 0 else 202),
               'identifier': recovery.FAMILIES[family], 'dimension_id': 0, 'position': [float(v) for v in tag['Pos']], 'inventory_field': 'ChestItems',
               'items_sha256': recovery.items_digest(tag, 'ChestItems'), 'owner_block': {'position': list(positions[i]), 'dimension_id': 0, 'name': block_names[i], 'states_sha256': recovery.block_states_digest(blocks[i])},
               'storage_key': {'path': STORAGE_PATH, 'before_hex': (pointer if i == 0 else malformed).hex(), 'after_hex': pointer.hex()},
               'digp': {'key_hex': index.hex(), 'before_hex': unrelated_pointer.hex()}, 'authority': authority}
        if i == 1:
            row.update(pending_remove=True, retained_aliases=[{'actor_key_hex': (recovery.ACTOR_PREFIX + malformed).hex(), 'actor_sha256': recovery.sha(alias_raw), 'items_sha256': row['items_sha256']}])
        targets.append(row)
    return db, {'schema': 1, 'source': 'synthetic exact stopped-stage evidence', 'world_dp_sha256': recovery.sha(world_raw),
                'active_scopes': {'tavern_native': recovery.TAVERN_SCOPE, 'cookery_bowl': CF_SCOPE}, 'targets': targets}


def rewrite_bowl_source(db, row, mutate):
    """Rebase a synthetic source fact, including its retained malformed alias."""
    for record in [row, *row.get('retained_aliases', [])]:
        key = bytes.fromhex(record['actor_key_hex']);tag = recovery.decode(db[key])
        mutate(tag)
        db[key] = encode_root(tag);record['actor_sha256'] = recovery.sha(db[key])
        record['items_sha256'] = recovery.items_digest(tag, row['inventory_field'])


def removed_bowl_fixture():
    db, plan = fixture();native, bowl = plan['targets']
    bowl['pending_removed_bowl'] = True
    bowl['owner_block']['name'] = 'minecraft:air'
    blocks = [nbtlib.File({'name': nbtlib.String(native['owner_block']['name']),
                          'states': nbtlib.Compound({'synthetic:facing': nbtlib.Int(0)}), 'version': nbtlib.Int(1)}),
              nbtlib.File({'name': nbtlib.String('minecraft:air'), 'states': nbtlib.Compound(), 'version': nbtlib.Int(1)})]
    bowl['owner_block']['states_sha256'] = recovery.block_states_digest(blocks[1])
    key = recovery.chunk_key((48, 64, 32), 0x2f) + b'\x04'
    db[key] = palette(blocks, [(48, 64, 32), (49, 64, 32)])
    def original_three(tag):
        original = stack(0, 'minecraft:bowl');original['Count'] = nbtlib.Byte(3)
        tag['ChestItems'] = nbtlib.List[nbtlib.Compound]([original,
            nbtlib.Compound({'Slot': nbtlib.Byte(1), 'Name': nbtlib.String(''), 'Count': nbtlib.Byte(0)}),
            nbtlib.Compound({'Slot': nbtlib.Byte(2), 'Name': nbtlib.String(''), 'Count': nbtlib.Byte(0)})])
    rewrite_bowl_source(db, bowl, original_three)
    return db, plan


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.db, self.plan = fixture()

    def test_one_atomic_batch_preserves_items_all_opaque_strings_aliases_and_unrelated_bytes(self):
        original = dict(self.db);before = recovery.inspect(self.db, self.plan)
        result = recovery.recover(self.db, self.plan)
        self.assertEqual(self.db.batches, 1);self.assertEqual(before['state'], 'before')
        self.assertTrue(recovery.verify(self.db, self.plan, result)['ok'])
        self.assertEqual(result['unrelated_before'], result['unrelated_after'])
        native, bowl = self.plan['targets'];native_key = bytes.fromhex(native['actor_key_hex']);bowl_key = bytes.fromhex(bowl['actor_key_hex'])
        self.assertEqual(self.db[native_key], original[native_key])
        repaired = recovery.decode(self.db[bowl_key]);self.assertEqual(recovery.items_digest(repaired, 'ChestItems'), bowl['items_sha256'])
        self.assertIn(b'\x81\xff\x00opaque', self.db[bowl_key])
        index_key = bytes.fromhex(native['digp']['key_hex']);self.assertEqual(self.db[index_key], original[index_key] + b''.join(sorted([native_key[len(recovery.ACTOR_PREFIX):], bowl_key[len(recovery.ACTOR_PREFIX):]])))
        alias_key = bytes.fromhex(bowl['retained_aliases'][0]['actor_key_hex']);self.assertEqual(self.db[alias_key], original[alias_key])
        self.assertEqual(set(original), set(self.db))
        changed = {k for k in self.db if self.db[k] != original[k]};self.assertEqual(changed, {bowl_key, index_key})
        self.assertFalse(result['items_materialized']);self.assertFalse(result['aliases_deleted'])

    def test_replay_is_noop_and_receipt_detects_later_unrelated_mutation(self):
        first = recovery.recover(self.db, self.plan);before = dict(self.db)
        second = recovery.recover(self.db, self.plan)
        self.assertTrue(second['idempotent']);self.assertEqual(second['changed_keys'], []);self.assertEqual(self.db.batches, 1);self.assertEqual(dict(self.db), before)
        self.assertTrue(recovery.verify(self.db, self.plan, first)['ok'])
        self.db[b'player_synthetic'] = b'later conflict'
        with self.assertRaisesRegex(ValueError, 'unrelated summary'):recovery.verify(self.db, self.plan, first)

    def test_partial_conflict_duplicate_pointer_foreign_index_and_shared_preimage_abort_without_write(self):
        for kind in ('partial', 'duplicate', 'foreign', 'preimage'):
            db, plan = fixture();pointer = bytes.fromhex(plan['targets'][0]['actor_key_hex'])[len(recovery.ACTOR_PREFIX):];index = bytes.fromhex(plan['targets'][0]['digp']['key_hex'])
            if kind == 'partial':db[index] += pointer
            elif kind == 'duplicate':db[index] += pointer * 2
            elif kind == 'foreign':db[b'digp' + struct.pack('<ii', 8, 9)] = pointer
            else:plan['targets'][1]['digp']['before_hex'] = ''
            before = dict(db)
            with self.subTest(kind=kind), self.assertRaises(ValueError):recovery.recover(db, plan)
            self.assertEqual(dict(db), before);self.assertEqual(db.batches, 0)

    def test_absent_index_is_added_once_without_rewriting_other_records(self):
        index = bytes.fromhex(self.plan['targets'][0]['digp']['key_hex']);del self.db[index]
        for row in self.plan['targets']:row['digp']['before_hex'] = None
        result = recovery.recover(self.db, self.plan)
        self.assertEqual(len(self.db[index]), 16);self.assertTrue(recovery.verify(self.db, self.plan, result)['ok'])

    def test_uid_alias_owner_and_active_binding_conflicts_never_materialize_items(self):
        for kind in ('uid', 'owner', 'alias', 'binding', 'inactive_scope'):
            db, plan = fixture();native, bowl = plan['targets']
            if kind == 'uid':db[recovery.ACTOR_PREFIX + b'copyPtr!'] = db[bytes.fromhex(native['actor_key_hex'])]
            elif kind == 'owner':
                tag = recovery.decode(db[bytes.fromhex(native['actor_key_hex'])]);tag['UniqueID'] = nbtlib.Long(909);db[recovery.ACTOR_PREFIX + b'otherPtr'] = encode_root(tag)
            elif kind == 'alias':bowl['retained_aliases'] = []
            else:
                world = recovery.decode(db[recovery.WORLD_DP])
                if kind == 'binding':world[CF_SCOPE][bowl['authority']['key']] = nbtlib.String('303')
                else:plan['active_scopes']['cookery_bowl'] = '66666666-7777-4888-8999-aaaaaaaaaaaa'
                db[recovery.WORLD_DP] = encode_root(world);plan['world_dp_sha256'] = recovery.sha(db[recovery.WORLD_DP])
            before = dict(db)
            with self.subTest(kind=kind), self.assertRaises(ValueError):recovery.recover(db, plan)
            self.assertEqual(dict(db), before);self.assertEqual(db.batches, 0)

    def test_foreign_owner_block_and_typed_state_change_abort_before_batch(self):
        for kind in ('name', 'owned_name', 'type'):
            db, plan = fixture()
            if kind == 'name':plan['targets'][0]['owner_block']['name'] = 'minecraft:chest'
            elif kind == 'owned_name':plan['targets'][0]['owner_block']['name'] = 'kaleidoscope_world_liquor:other_bar_cabinet'
            else:
                blocks = [nbtlib.File({'name': nbtlib.String(r['owner_block']['name']), 'states': nbtlib.Compound({'synthetic:facing': nbtlib.Byte(0)}), 'version': nbtlib.Int(1)}) for r in plan['targets']]
                key = recovery.chunk_key((48, 64, 32), 0x2f) + b'\x04';db[key] = palette(blocks, [(48, 64, 32), (49, 64, 32)])
            before = dict(db)
            with self.subTest(kind=kind), self.assertRaises(ValueError):recovery.recover(db, plan)
            self.assertEqual(dict(db), before);self.assertEqual(db.batches, 0)

    def test_only_utf8_replacement_storage_key_repair_and_exact_items_are_allowed(self):
        for kind in ('arbitrary_pointer', 'item_metadata', 'noncanonical_key', 'too_many', 'pending_waiver'):
            db, plan = fixture();bowl = plan['targets'][1]
            if kind == 'arbitrary_pointer':bowl['storage_key']['before_hex'] = b'arbitrary bytes'.hex()
            elif kind == 'item_metadata':
                key = bytes.fromhex(bowl['actor_key_hex']);tag = recovery.decode(db[key]);tag['ChestItems'][0]['tag']['display']['Name'] = nbtlib.String('changed');db[key] = encode_root(tag);bowl['actor_sha256'] = recovery.sha(db[key])
            elif kind == 'noncanonical_key':bowl['actor_key_hex'] += '00'
            elif kind == 'too_many':plan['targets'] *= 9
            else:bowl['pending_remove'] = False
            before = dict(db)
            with self.subTest(kind=kind), self.assertRaises(ValueError):recovery.recover(db, plan)
            self.assertEqual(dict(db), before);self.assertEqual(db.batches, 0)

    def test_atomic_failure_and_broken_adapter_fail_closed_without_success_receipt(self):
        for kind in ('atomic', 'partial', 'unrelated'):
            db, plan = fixture();before = dict(db);db.failure = kind
            with self.subTest(kind=kind), self.assertRaises(ValueError):recovery.recover(db, plan)
            self.assertEqual(db.batches, 1)
            if kind == 'atomic':self.assertEqual(dict(db), before)
            elif kind == 'partial':
                db.failure = None
                with self.assertRaisesRegex(ValueError, 'partial/conflicting'):recovery.inspect(db, plan)

    def test_last_target_failure_and_changed_preimage_never_write_an_earlier_target(self):
        self.plan['targets'][-1]['owner_block']['states_sha256'] = '0' * 64
        before = dict(self.db)
        with self.assertRaisesRegex(ValueError, 'typed states'):recovery.recover(self.db, self.plan)
        self.assertEqual(dict(self.db), before);self.assertEqual(self.db.batches, 0)
        db, plan = fixture();prepare = recovery._prepare
        def changed(database, specification):
            result = prepare(database, specification);database[recovery.WORLD_DP] += b'changed';return result
        with patch.object(recovery, '_prepare', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'preimage changed'):recovery.recover(db, plan)
        self.assertEqual(db.batches, 0)

    def test_wrong_dp_types_and_additional_storage_key_are_not_normalized(self):
        for kind in ('required_string', 'pending_string', 'second_storage_key'):
            db, plan = fixture();native, bowl = plan['targets']
            if kind == 'second_storage_key':
                key = bytes.fromhex(bowl['actor_key_hex']);tag = recovery.decode(db[key]);tag['unknown_component']['StorageKey'] = string(b'other key')
                db[key] = encode_root(tag);bowl['actor_sha256'] = recovery.sha(db[key])
            else:
                world = recovery.decode(db[recovery.WORLD_DP])
                scope, name = (recovery.TAVERN_SCOPE, native['authority']['required_key']) if kind == 'required_string' else (CF_SCOPE, bowl['authority']['key'] + ':remove')
                world[scope][name] = nbtlib.String('1');db[recovery.WORLD_DP] = encode_root(world);plan['world_dp_sha256'] = recovery.sha(db[recovery.WORLD_DP])
            before = dict(db)
            with self.subTest(kind=kind), self.assertRaises(ValueError):recovery.recover(db, plan)
            self.assertEqual(dict(db), before);self.assertEqual(db.batches, 0)

    def test_native_gate_template_cannot_accept_pending_removal_or_claim_restart(self):
        receipt = recovery.recover(self.db, self.plan);template = recovery.native_verification_template(self.plan, receipt)
        for phase in ('first_load', 'restart'):
            self.assertFalse(template['phases'][phase]['ok']);self.assertIsNone(template['phases'][phase]['observed'])
            self.assertTrue(template['phases'][phase]['targets'][1]['pending_remove'])
            self.assertTrue(any('exact-once' in value for value in template['phases'][phase]['requirements']))
        self.assertFalse(template['native_loading'])

    def test_pending_removed_bowl_only_repairs_pointer_and_storage_key_preserving_original_three(self):
        db, plan = removed_bowl_fixture();original = dict(db);bowl = plan['targets'][1]
        before_actor = recovery.decode(db[bytes.fromhex(bowl['actor_key_hex'])])
        before_items = encode_root(nbtlib.File({'Items': before_actor['ChestItems']}))
        inspected = recovery.inspect(db, plan);receipt = recovery.recover(db, plan)
        self.assertEqual(inspected['state'], 'before');self.assertTrue(recovery.verify(db, plan, receipt)['ok'])
        self.assertEqual(db.batches, 1);self.assertTrue(receipt['targets'][1]['pending_removed_bowl'])
        self.assertEqual(receipt['targets'][1]['item_count'], 3)
        key = bytes.fromhex(bowl['actor_key_hex']);index = bytes.fromhex(bowl['digp']['key_hex'])
        self.assertEqual({k for k in db if db[k] != original[k]}, {key, index})
        self.assertEqual(db[recovery.WORLD_DP], original[recovery.WORLD_DP])
        after_actor = recovery.decode(db[key])
        self.assertEqual(encode_root(nbtlib.File({'Items': after_actor['ChestItems']})), before_items)
        self.assertEqual(recovery.items_digest(after_actor, 'ChestItems'), bowl['items_sha256'])
        self.assertEqual(str(after_actor['ChestItems'][0]['Name']), 'minecraft:bowl')
        self.assertEqual(int(after_actor['ChestItems'][0]['Count']), 3)
        again = recovery.recover(db, plan)
        self.assertTrue(again['idempotent']);self.assertEqual(db.batches, 1)
        self.assertFalse(receipt['items_materialized']);self.assertFalse(receipt['aliases_deleted'])

    def test_pending_removed_bowl_requires_air_pending_exact_binding_root_and_three_original_bowls(self):
        for kind in ('implicit_air', 'false_flag', 'numeric_flag', 'pending_false', 'world_pending_false',
                     'world_pending_missing', 'foreign_root', 'air_root', 'wrong_root_cell', 'wrong_root_dimension',
                     'missing_root', 'binding_uid', 'missing_binding', 'replaced_actual_block',
                     'replaced_planned_block', 'typed_states', 'two_bowls', 'four_bowls', 'foreign_item', 'foreign_family'):
            db, plan = removed_bowl_fixture();native, bowl = plan['targets']
            if kind == 'implicit_air':del bowl['pending_removed_bowl']
            elif kind == 'false_flag':bowl['pending_removed_bowl'] = False
            elif kind == 'numeric_flag':bowl['pending_removed_bowl'] = 1
            elif kind == 'pending_false':bowl['pending_remove'] = False
            elif kind.startswith('world_pending') or kind in ('binding_uid', 'missing_binding'):
                world = recovery.decode(db[recovery.WORLD_DP]);owner = world[CF_SCOPE];key = bowl['authority']['key']
                if kind == 'world_pending_false':owner[key + ':remove'] = nbtlib.Double(0)
                elif kind == 'world_pending_missing':del owner[key + ':remove']
                elif kind == 'binding_uid':owner[key] = nbtlib.String('303');bowl['authority']['raw'] = '303'
                else:del owner[key]
                db[recovery.WORLD_DP] = encode_root(world);plan['world_dp_sha256'] = recovery.sha(db[recovery.WORLD_DP])
            elif kind in ('foreign_root', 'air_root', 'wrong_root_cell', 'wrong_root_dimension'):
                root = json.loads(bowl['authority']['actor_properties']['senluo:kcf_root'])
                if kind == 'foreign_root':root['type'] = 'kaleidoscope_chinesefood:pickle_jar'
                elif kind == 'air_root':root['type'] = 'minecraft:air'
                elif kind == 'wrong_root_cell':root['x'] += 1
                else:root['dimension'] = 'minecraft:nether'
                raw = json.dumps(root);bowl['authority']['actor_properties']['senluo:kcf_root'] = raw
                rewrite_bowl_source(db, bowl, lambda tag: tag['DynamicProperties'][CF_SCOPE].__setitem__('senluo:kcf_root', nbtlib.String(raw)))
            elif kind == 'missing_root':
                del bowl['authority']['actor_properties']['senluo:kcf_root']
            elif kind in ('replaced_actual_block', 'replaced_planned_block', 'typed_states'):
                replacement = 'minecraft:stone' if kind.startswith('replaced') else 'minecraft:air'
                states = nbtlib.Compound({'synthetic:foreign': nbtlib.Byte(0)}) if kind == 'typed_states' else nbtlib.Compound()
                blocks = [nbtlib.File({'name': nbtlib.String(native['owner_block']['name']), 'states': nbtlib.Compound({'synthetic:facing': nbtlib.Int(0)}), 'version': nbtlib.Int(1)}),
                          nbtlib.File({'name': nbtlib.String(replacement), 'states': states, 'version': nbtlib.Int(1)})]
                db[recovery.chunk_key((48, 64, 32), 0x2f) + b'\x04'] = palette(blocks, [(48, 64, 32), (49, 64, 32)])
                if kind == 'replaced_planned_block':
                    bowl['owner_block']['name'] = replacement;bowl['owner_block']['states_sha256'] = recovery.block_states_digest(blocks[1])
            elif kind in ('two_bowls', 'four_bowls', 'foreign_item'):
                def changed_inventory(tag):
                    if kind == 'foreign_item':tag['ChestItems'][0]['Name'] = nbtlib.String('minecraft:dirt')
                    else:tag['ChestItems'][0]['Count'] = nbtlib.Byte(2 if kind == 'two_bowls' else 4)
                rewrite_bowl_source(db, bowl, changed_inventory)
            else:
                native['pending_removed_bowl'] = True;native['pending_remove'] = True;native['owner_block']['name'] = 'minecraft:air'
            before = dict(db)
            with self.subTest(kind=kind), self.assertRaises(ValueError):recovery.recover(db, plan)
            self.assertEqual(dict(db), before);self.assertEqual(db.batches, 0)

    def test_pending_removed_bowl_template_requires_metadata_conservation_and_no_restart_redrop(self):
        db, plan = removed_bowl_fixture();receipt = recovery.recover(db, plan)
        template = recovery.native_verification_template(plan, receipt)
        for phase in ('first_load', 'restart'):
            self.assertFalse(template['phases'][phase]['ok'])
            transition = template['phases'][phase]['targets'][1]['required_runtime_transition']
            self.assertEqual(transition['profile'], 'pending_removed_bowl')
            self.assertEqual(transition['original_root_type'], 'kaleidoscope_chinesefood:bowl_stack')
            self.assertEqual(transition['observed_owner_block'], 'minecraft:air')
            self.assertEqual(transition['original_item_count'], 3)
            for field in ('complete_returned_item_metadata_proof', 'first_load_returned_item_count',
                          'pending_marker_cleared', 'old_actor_removed', 'restart_total_returned_item_count', 'restart_did_not_redrop'):
                self.assertIsNone(transition[field])
            self.assertFalse(transition['ok'])

    def test_world_opener_rejects_source_symlink_and_inactive_scope_before_leveldb(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);stage_root = root/'stage';stage_root.mkdir();world = stage_root/'world';world.mkdir();(world/'db').mkdir();source = root/'source';source.mkdir();(source/'db').mkdir()
            (world/'world_behavior_packs.json').write_text(json.dumps([{'pack_id': scope} for scope in self.plan['active_scopes'].values()]))
            with patch.dict('sys.modules', {'leveldb': types.SimpleNamespace(LevelDB=lambda _: self.fail('must not open a source database'))}):
                with self.assertRaises(ValueError):recovery.recover_world(source, self.plan, stage_root=stage_root, source_world=source)
                alias = stage_root/'alias';alias.symlink_to(world, target_is_directory=True)
                with self.assertRaises(ValueError):recovery.recover_world(alias, self.plan, stage_root=stage_root, source_world=source)
                (world/'world_behavior_packs.json').write_text('[]')
                with self.assertRaises(ValueError):recovery.recover_world(world, self.plan, stage_root=stage_root, source_world=source)
                (world/'world_behavior_packs.json').write_text(json.dumps([{'pack_id': scope} for scope in self.plan['active_scopes'].values()]))
                table = source/'db/table.ldb';table.write_bytes(b'synthetic source bytes');os.link(table, world/'db/shared.ldb')
                with self.assertRaisesRegex(ValueError, 'shared file'):recovery.recover_world(world, self.plan, stage_root=stage_root, source_world=source)

    def test_world_inspection_only_opens_the_explicit_idle_stage_and_always_closes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);stage_root = root/'stage';stage_root.mkdir();world = stage_root/'world';world.mkdir();(world/'db').mkdir();source = root/'source';source.mkdir();(source/'db').mkdir()
            (world/'world_behavior_packs.json').write_text(json.dumps([{'pack_id': scope} for scope in self.plan['active_scopes'].values()]))
            opened = []
            def database(path):
                opened.append(path);return self.db
            with patch.dict('sys.modules', {'leveldb': types.SimpleNamespace(LevelDB=database)}), patch('family_update.storage.assert_idle') as idle:
                result = recovery.inspect_world(world, self.plan, stage_root=stage_root, source_world=source)
            self.assertEqual(result['state'], 'before');self.assertEqual(opened, [str(world/'db')]);self.assertTrue(self.db.closed);self.assertEqual(self.db.batches, 0);idle.assert_called_once_with(world)


if __name__ == '__main__':
    unittest.main()
