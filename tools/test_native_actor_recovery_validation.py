"""Synthetic stopped native snapshots; these tests never execute BDS or LIVE."""
import copy
import json
from pathlib import Path
import struct
import tempfile
import types
import unittest
from unittest.mock import patch

import nbtlib
from bedrock_nbt import encode_root
import native_actor_recovery as recovery
import native_actor_recovery_validation as validation
from test_native_actor_recovery import CF_SCOPE, Database, actor, removed_bowl_fixture, string


def palette(blocks, positions):
    words = [0] * 256
    for selected, (x, y, z) in enumerate(positions):
        index = (x % 16) * 256 + (z % 16) * 16 + y % 16
        words[index // 16] |= selected << ((index % 16) * 2)
    return bytes([9, 1, 4, 4]) + struct.pack('<' + 'I' * 256, *words) + struct.pack('<I', len(blocks)) + b''.join(encode_root(block) for block in blocks)


def ordinary_item(uid, pointer, item, position=(49.5, 64.5, 32.5)):
    return nbtlib.File({'UniqueID': nbtlib.Long(uid), 'identifier': nbtlib.String('minecraft:item'), 'DimensionId': nbtlib.Int(0),
        'Pos': nbtlib.List[nbtlib.Float](position), 'Item': copy.deepcopy(item), 'Age': nbtlib.Short(30),
        'internalComponents': nbtlib.Compound({'EntityStorageKeyComponent': nbtlib.Compound({'StorageKey': string(pointer)})})})


def fixture(*, preexisting=False):
    db, plan = removed_bowl_fixture();native, pending = plan['targets']
    pointer = b'ACTIVE03';key = recovery.ACTOR_PREFIX + pointer
    binding = 'senluo:kcf_inventory:minecraft:overworld:50,64,32'
    props = {'senluo:kcf_owner': binding, 'senluo:kcf_root': json.dumps(
        {'dimension': 'minecraft:overworld', 'x': 50, 'y': 64, 'z': 32, 'type': recovery.BOWL_ROOT_TYPE})}
    tag = actor(303, recovery.FAMILIES['cookery_bowl'], pointer, (50.5, 64.25, 32.5), CF_SCOPE, props, 'minecraft:bowl', 3)
    db[key] = encode_root(tag)
    row = {'family': 'cookery_bowl', 'actor_key_hex': key.hex(), 'actor_sha256': recovery.sha(db[key]), 'unique_id': '303',
           'identifier': recovery.FAMILIES['cookery_bowl'], 'dimension_id': 0, 'position': [50.5, 64.25, 32.5],
           'inventory_field': 'ChestItems', 'items_sha256': recovery.items_digest(tag, 'ChestItems'),
           'owner_block': {'position': [50, 64, 32], 'dimension_id': 0, 'name': recovery.BOWL_ROOT_TYPE, 'states_sha256': '0' * 64},
           'storage_key': {'path': list(recovery.STORAGE_PATH), 'before_hex': pointer.hex(), 'after_hex': pointer.hex()},
           'digp': copy.deepcopy(pending['digp']), 'authority': {'scope': CF_SCOPE, 'kind': 'binding', 'key': binding, 'raw': '303', 'actor_properties': props}}
    blocks = [nbtlib.File({'name': nbtlib.String(name), 'states': nbtlib.Compound({'synthetic:facing': nbtlib.Int(0)}) if index == 0 else nbtlib.Compound(), 'version': nbtlib.Int(1)})
              for index, name in enumerate([native['owner_block']['name'], 'minecraft:air', recovery.BOWL_ROOT_TYPE])]
    row['owner_block']['states_sha256'] = recovery.block_states_digest(blocks[2])
    db[recovery.chunk_key((48, 64, 32), 0x2f) + b'\x04'] = palette(blocks, [(48, 64, 32), (49, 64, 32), (50, 64, 32)])
    plan['targets'].append(row)
    world = recovery.decode(db[recovery.WORLD_DP]);world[CF_SCOPE][binding] = nbtlib.String('303')
    db[recovery.WORLD_DP] = encode_root(world);plan['world_dp_sha256'] = recovery.sha(db[recovery.WORLD_DP])
    original = recovery.decode(db[bytes.fromhex(pending['actor_key_hex'])])['ChestItems'][0]
    item = nbtlib.Compound({name: copy.deepcopy(value) for name, value in original.items() if name != 'Slot'})
    if preexisting:
        old_pointer = b'OLDITEM1';db[recovery.ACTOR_PREFIX + old_pointer] = encode_root(ordinary_item(500, old_pointer, item))
        index = bytes.fromhex(pending['digp']['key_hex']);db[index] += old_pointer
        for target in plan['targets']:target['digp']['before_hex'] = db[index].hex()
    receipt = recovery.recover(db, plan)
    # Model a completed ordinary native break transaction, preserving the exact
    # original Item compound and retaining the unindexed malformed source alias.
    pending_key = bytes.fromhex(pending['actor_key_hex']);del db[pending_key]
    index = bytes.fromhex(pending['digp']['key_hex']);old_pointer = pending_key[len(recovery.ACTOR_PREFIX):]
    db[index] = b''.join(db[index][i:i + 8] for i in range(0, len(db[index]), 8) if db[index][i:i + 8] != old_pointer)
    world = recovery.decode(db[recovery.WORLD_DP]);del world[CF_SCOPE][pending['authority']['key']];del world[CF_SCOPE][pending['authority']['key'] + ':remove']
    db[recovery.WORLD_DP] = encode_root(world)
    pointer = b'ITEMPTR1';db[recovery.ACTOR_PREFIX + pointer] = encode_root(ordinary_item(404, pointer, item));db[index] += pointer
    return db, plan, receipt


def native_run(plan, phase='first'):
    areas = validation.observation_requirements(plan)['named_ticking_areas']
    return {'phase': phase, 'ok': True, 'started': True, 'family_initialized': True, 'exit_code': 0, 'errors': [],
            'real_player_connections': 0, 'commands_completed': True, 'stop_reason': 'ready',
            'log_sha256': ('a' if phase == 'first' else 'b') * 64, 'ticking_areas_created': areas,
            'ticking_area_cleanup_commands': [f"execute in {area['dimension']} run tickingarea remove {area['name']}" for area in reversed(areas)]}


def observe(db, plan, phase='first'):
    result = validation.inspect(db, plan);result['native_run'] = native_run(plan, phase);return result


def mutate_actor(db, key, mutate):
    tag = recovery.decode(db[key]);mutate(tag);db[key] = encode_root(tag)


class ValidationTests(unittest.TestCase):
    def test_first_and_restart_preserve_native_and_active_cookery_and_exact_three_returned_bowls(self):
        db, plan, receipt = fixture();before = dict(db);batches = db.batches
        first = observe(db, plan);result = validation.verify(plan, receipt, first)
        self.assertTrue(result['ok'], result['issues']);self.assertEqual([row['item_count'] for row in result['targets']], [1, 3, 3])
        self.assertTrue(result['targets'][1]['old_binding_and_pending_cleared'])
        restart = observe(db, plan, 'restart');again = validation.verify(plan, receipt, restart, previous=first)
        self.assertTrue(again['ok'], again['issues']);self.assertTrue(again['restart_no_redrop'])
        self.assertEqual(dict(db), before);self.assertEqual(db.batches, batches)

    def test_native_runtime_body_changes_compound_order_and_ledger_json_order_are_logical_not_byte_gates(self):
        db, plan, receipt = fixture();native = plan['targets'][0];key = bytes.fromhex(native['actor_key_hex'])
        def resave(tag):
            tag['unknown_component']['runtime_counter'] = nbtlib.Int(99)
            source = tag['ChestItems'][0]
            tag['ChestItems'][0] = nbtlib.Compound({name: source[name] for name in reversed(list(source))})
        mutate_actor(db, key, resave)
        world = recovery.decode(db[recovery.WORLD_DP]);scope = world[native['authority']['scope']];name = native['authority']['key']
        scope[name] = nbtlib.String(json.dumps(json.loads(str(scope[name])), sort_keys=True, indent=2));scope['foreign_runtime_value'] = nbtlib.Int(7)
        db[recovery.WORLD_DP] = encode_root(world)
        result = validation.verify(plan, receipt, observe(db, plan));self.assertTrue(result['ok'], result['issues'])

    def test_native_empty_slot_serialization_and_dropped_item_count_splitting_preserve_logical_items(self):
        db, plan, receipt = fixture();native = plan['targets'][0];key = bytes.fromhex(native['actor_key_hex'])
        mutate_actor(db, key, lambda tag: tag['ChestItems'].append(nbtlib.Compound({'Slot': nbtlib.Byte(8), 'Name': nbtlib.String(''), 'Count': nbtlib.Byte(0)})))
        pointer = b'ITEMPTR1';item_key = recovery.ACTOR_PREFIX + pointer
        mutate_actor(db, item_key, lambda tag: tag['Item'].__setitem__('Count', nbtlib.Byte(1)))
        second = b'ITEMPTR2';source = recovery.decode(db[item_key]);source['Item']['Count'] = nbtlib.Byte(2)
        db[recovery.ACTOR_PREFIX + second] = encode_root(ordinary_item(405, second, source['Item']))
        db[bytes.fromhex(plan['targets'][1]['digp']['key_hex'])] += second
        result = validation.verify(plan, receipt, observe(db, plan));self.assertTrue(result['ok'], result['issues'])

    def test_unobserved_chunks_missing_area_cleanup_or_failed_native_run_never_pass(self):
        for kind in ('missing', 'unloaded', 'cleanup', 'players', 'error', 'exit', 'wrong_phase', 'no_log', 'duplicate_area'):
            db, plan, receipt = fixture();observed = observe(db, plan)
            if kind == 'missing':observed['native_run'] = None
            elif kind == 'unloaded':observed['native_run']['ticking_areas_created'] = []
            elif kind == 'cleanup':observed['native_run']['ticking_area_cleanup_commands'] = []
            elif kind == 'players':observed['native_run']['real_player_connections'] = 1
            elif kind == 'error':observed['native_run']['errors'] = ['script error']
            elif kind == 'exit':observed['native_run']['exit_code'] = 1
            elif kind == 'wrong_phase':observed['native_run']['phase'] = 'restart'
            elif kind == 'no_log':del observed['native_run']['log_sha256']
            else:observed['native_run']['ticking_areas_created'] *= 2
            result = validation.verify(plan, receipt, observed)
            with self.subTest(kind=kind):self.assertFalse(result['ok']);self.assertTrue(result['issues']);self.assertTrue(result['observation_requirements']['named_ticking_area_commands'])

    def test_native_slot_metadata_types_count_uid_token_binding_and_index_failures_are_detected(self):
        for kind in ('name', 'count', 'metadata', 'metadata_type', 'slot', 'uid', 'token', 'storage', 'binding', 'ledger', 'index_duplicate', 'index_foreign'):
            db, plan, receipt = fixture();native = plan['targets'][0];key = bytes.fromhex(native['actor_key_hex'])
            if kind in ('binding', 'ledger'):
                target = plan['targets'][2] if kind == 'binding' else native
                world = recovery.decode(db[recovery.WORLD_DP]);world[target['authority']['scope']][target['authority']['key']] = nbtlib.String('wrong' if kind == 'binding' else '{}')
                db[recovery.WORLD_DP] = encode_root(world)
            elif kind.startswith('index'):
                pointer = key[len(recovery.ACTOR_PREFIX):]
                if kind == 'index_duplicate':db[bytes.fromhex(native['digp']['key_hex'])] += pointer
                else:db[b'digp' + struct.pack('<ii', 70, 80)] = pointer
            else:
                def change(tag):
                    if kind == 'name':tag['ChestItems'][0]['Name'] = nbtlib.String('minecraft:dirt')
                    elif kind == 'count':tag['ChestItems'][0]['Count'] = nbtlib.Byte(2)
                    elif kind == 'metadata':tag['ChestItems'][0]['tag']['display']['Name'] = nbtlib.String('lost original name')
                    elif kind == 'metadata_type':tag['ChestItems'][0]['tag']['ench'][0]['lvl'] = nbtlib.Int(3)
                    elif kind == 'slot':tag['ChestItems'][0]['Slot'] = nbtlib.Byte(1)
                    elif kind == 'uid':tag['UniqueID'] = nbtlib.Long(808)
                    elif kind == 'token':tag['DynamicProperties'][recovery.TAVERN_SCOPE]['kaleidoscope_tavern:storage_token'] = nbtlib.String('changed')
                    else:tag['internalComponents']['EntityStorageKeyComponent']['StorageKey'] = string(b'WRONGKEY')
                mutate_actor(db, key, change)
            result = validation.verify(plan, receipt, observe(db, plan))
            with self.subTest(kind=kind):self.assertFalse(result['ok']);self.assertTrue(result['issues'])

    def test_pending_release_never_waives_old_items_or_accepts_alias_revival_missing_drops_or_wrong_metadata(self):
        for kind in ('binding', 'pending_zero', 'canonical_revived', 'alias_revived', 'alias_changed', 'no_drop', 'wrong_location', 'wrong_dimension', 'count_two', 'count_six', 'metadata', 'metadata_type', 'drop_index_missing', 'drop_uid_duplicate'):
            db, plan, receipt = fixture();pending = plan['targets'][1];drop_key = recovery.ACTOR_PREFIX + b'ITEMPTR1'
            if kind in ('binding', 'pending_zero'):
                world = recovery.decode(db[recovery.WORLD_DP]);name = pending['authority']['key'] + (':remove' if kind == 'pending_zero' else '')
                world[CF_SCOPE][name] = nbtlib.Double(0) if kind == 'pending_zero' else nbtlib.String(pending['unique_id'])
                db[recovery.WORLD_DP] = encode_root(world)
            elif kind in ('canonical_revived', 'alias_revived', 'alias_changed'):
                alias_key = bytes.fromhex(pending['retained_aliases'][0]['actor_key_hex'])
                if kind == 'alias_changed':mutate_actor(db, alias_key, lambda tag: tag.__setitem__('changed_alias', nbtlib.Int(1)))
                else:
                    revived = bytes.fromhex(pending['actor_key_hex']) if kind == 'canonical_revived' else recovery.ACTOR_PREFIX + b'REVIVED!'
                    db[revived] = db[alias_key]
            elif kind == 'no_drop':del db[drop_key]
            elif kind == 'drop_index_missing':
                index = bytes.fromhex(pending['digp']['key_hex']);db[index] = db[index].replace(b'ITEMPTR1', b'')
            elif kind == 'drop_uid_duplicate':db[recovery.ACTOR_PREFIX + b'COPIED!!'] = db[drop_key]
            else:
                def change(tag):
                    if kind == 'wrong_location':tag['Pos'][0] = nbtlib.Float(51.5)
                    elif kind == 'wrong_dimension':tag['DimensionId'] = nbtlib.Int(1)
                    elif kind == 'count_two':tag['Item']['Count'] = nbtlib.Byte(2)
                    elif kind == 'count_six':tag['Item']['Count'] = nbtlib.Byte(6)
                    elif kind == 'metadata':tag['Item']['tag']['display']['Lore'][0] = nbtlib.String('changed')
                    else:tag['Item']['tag']['ench'][0]['lvl'] = nbtlib.Int(3)
                mutate_actor(db, drop_key, change)
            result = validation.verify(plan, receipt, observe(db, plan))
            with self.subTest(kind=kind):self.assertFalse(result['ok']);self.assertTrue(result['issues'])

    def test_restart_rejects_new_item_uid_even_when_replacement_metadata_and_total_match(self):
        db, plan, receipt = fixture();first = observe(db, plan)
        self.assertTrue(validation.verify(plan, receipt, first)['ok'])
        mutate_actor(db, recovery.ACTOR_PREFIX + b'ITEMPTR1', lambda tag: tag.__setitem__('UniqueID', nbtlib.Long(9999)))
        result = validation.verify(plan, receipt, observe(db, plan, 'restart'), previous=first)
        self.assertFalse(result['ok']);self.assertIn('re-dropped', result['issues'][0])

    def test_preexisting_loose_items_cannot_substitute_for_the_original_pending_three(self):
        db, plan, receipt = fixture(preexisting=True)
        self.assertIn('500', receipt['targets'][1]['original_loose_item_uids'])
        observed = observe(db, plan);self.assertTrue(validation.verify(plan, receipt, observed)['ok'])
        key = recovery.ACTOR_PREFIX + b'ITEMPTR1';del db[key]
        result = validation.verify(plan, receipt, observe(db, plan))
        self.assertFalse(result['ok']);self.assertIn('complete typed native Item', result['issues'][0])

    def test_original_receipt_requires_the_complete_typed_inventory_preimage(self):
        db, plan, receipt = fixture()
        for kind in ('missing', 'tampered'):
            changed = copy.deepcopy(receipt)
            if kind == 'missing':del changed['targets'][1]['original_inventory_nbt_hex']
            else:changed['targets'][1]['original_inventory_nbt_hex'] = changed['targets'][0]['original_inventory_nbt_hex']
            with self.subTest(kind=kind):self.assertFalse(validation.verify(plan, changed, observe(db, plan))['ok'])

    def test_commands_group_shared_chunks_separate_dimensions_and_reject_more_than_ten_areas(self):
        _, plan, _ = fixture();self.assertEqual(len(validation.commands(plan)), 1)
        rows = []
        for index in range(11):
            row = copy.deepcopy(plan['targets'][0]);row['unique_id'] = str(index + 1000)
            pointer = struct.pack('<Q', index + 1000);row['actor_key_hex'] = (recovery.ACTOR_PREFIX + pointer).hex()
            row['storage_key']['before_hex'] = row['storage_key']['after_hex'] = pointer.hex()
            row['owner_block']['position'][0] = index * 160;row['position'][0] = index * 160 + .5
            row['digp']['key_hex'] = recovery.digp_key(row['position'], 0).hex();rows.append(row)
        changed = copy.deepcopy(plan);changed['targets'] = rows
        with self.assertRaisesRegex(ValueError, 'ten'):validation.commands(changed)
        changed['targets'] = rows[:2];changed['targets'][1]['dimension_id'] = 1;changed['targets'][1]['owner_block']['dimension_id'] = 1
        changed['targets'][1]['digp']['key_hex'] = recovery.digp_key(changed['targets'][1]['position'], 1).hex()
        commands = validation.commands(changed);self.assertEqual(len(commands), 2);self.assertIn(' in nether ', commands[1])

    def test_inspect_world_uses_only_the_explicit_idle_stage_and_no_write_api(self):
        db, plan, _ = fixture();stage_db = Database(dict(db))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);stage_root = root/'stage';stage_root.mkdir();world = stage_root/'world';world.mkdir();(world/'db').mkdir()
            source = root/'source';source.mkdir();(source/'db').mkdir()
            (world/'world_behavior_packs.json').write_text(json.dumps([{'pack_id': scope} for scope in plan['active_scopes'].values()]))
            opened = []
            def open_db(path):opened.append(path);return stage_db
            with patch.dict('sys.modules', {'leveldb': types.SimpleNamespace(LevelDB=open_db)}), patch('family_update.storage.assert_idle') as idle:
                observed = validation.inspect_world(world, plan, stage_root=stage_root, source_world=source)
                with self.assertRaises(ValueError):validation.inspect_world(source, plan, stage_root=stage_root, source_world=source)
            self.assertEqual(opened, [str(world/'db')]);self.assertTrue(stage_db.closed);self.assertEqual(stage_db.batches, 0)
            self.assertFalse(observed['writes']);self.assertIsNone(observed['native_run']);idle.assert_called_once_with(world)


if __name__ == '__main__':
    unittest.main()
