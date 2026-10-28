"""Recorder contract regressions using synthetic transcripts, never a BDS claim."""
import copy
import json
import pathlib
import tempfile
import unittest

from record_shaker_migration import EVIDENCE_NAME, LOG_NAME, MAIN_OVERLAY_NOTE, PREFIX, BDS_VERSION, validate_phase, validate_potion_pair, validate_recorded_inputs, write_evidence

VERSION = '0.1.112'


def transcript(phase):
    addon = dict(source='kaleidoscope_world_liquor', version=VERSION, recipes=60, pages=50, shakerInputs=67)
    rows = []

    def case(mode, **values):
        rows.append(dict(kind='case', mode=mode, phase=phase, **values))

    case('addon_registration', **addon)
    for index, lock in enumerate(('inventory', 'slot')):
        if phase == 'first':
            rows.append(dict(kind='case', mode='native-cross-id', source='kaleidoscope_tavern:shaker_'+('active' if index == 0 else 'pouring'),
                             target='kaleidoscope_tavern:shaker', lock=lock, adventureLists=10, rawLore=True, hostScopeDynamicTypes=4))
        else:
            rows.append(dict(kind='case', mode='saved-metadata', slot=index, lock=lock))
    case('portable-stackable-ingredient-metadata', ingredients=3,
         rowTypes=['kaleidoscope_tavern:plum_wine_q4', 'kaleidoscope_tavern:whiskey_q4', 'kaleidoscope_tavern:honey_wine_q4'],
         nativeEquality=True, independentClone=True, fullArbitraryNBT=False)
    for kind, counts in (('pressing_tub', [11]), ('barrel', [3, 5, 1, 1])):
        case('native-machine-write' if phase == 'first' else 'native-machine-restart-recovery', machineKind=kind,
             slots=len(counts), counts=counts, schema=2, **({'hostScopeMetadata': True} if phase == 'first' else {'completeNativeSlots': True}))
    case('native-potion-registry', currentPotionEffectTypes=['minecraft:future_native', 'minecraft:healing', 'minecraft:poison'],
         mappedDisplayEffects=['minecraft:healing', 'minecraft:poison'], unmappedDisplayEffects=['minecraft:future_native'],
         deliveryTypes=['Consume', 'ThrownLingering', 'ThrownSplash'], playerUse=False, client=False)
    for index, (effect, rgb, x, facing, yaw) in enumerate((('healing', 0xf82423, 16, 'north', 0), ('poison', 0x87a363, 20, 'east', 90))):
        key = 'kt:vanillaBottleDisplays/minecraft:overworld/'+str(x)+'_300_4'
        position = dict(x=x, y=300, z=4)
        carrier, helper_id = 'saved-potion-carrier-'+str(index), phase+'-potion-helper-'+str(index)
        stack = dict(typeId='minecraft:potion', amount=1, nameTag='Native liquid minecraft:'+effect,
                     rawLore=[dict(text='Retain potion metadata '+str(index))], canDestroy=['minecraft:stone'], canPlaceOn=['minecraft:glass'],
                     keepOnDeath=True, lockMode='inventory' if index == 0 else 'slot', properties={'potion_probe:payload':'original stack '+str(index)},
                     potion=dict(effectId='minecraft:'+effect, deliveryId='Consume'))
        case('native-potion-liquid', fixtureId='native-potion-123', slot=index, position=position, facing=facing, ownerKey=key,
             displayPayload=dict(item='minecraft:potion', nativeItems=1, potion=dict(effectId='minecraft:'+('poison' if index == 0 else 'healing'), deliveryId='Consume')),
             nativeCarrier=carrier, nativeRecord=dict(schema=1, key=key, dimension='minecraft:overworld', position=copy.deepcopy(position),
                                                    ids=['minecraft:potion']+[None]*8, entity=carrier, token='saved-potion-token-'+str(index)),
             nativeStack=copy.deepcopy(stack), pickedStack=copy.deepcopy(stack), nativeCarrierCount=1, helperCount=1,
             helper=dict(id=helper_id, type='kaleidoscope_tavern:potion_liquid_visual', anchor=key, rgb=rgb, position=dict(x=x+.5, y=300, z=4.5),
                         rotation=dict(x=0, y=yaw), inventory=False), waitedTicks=20, playerUse=False, client=False)
        if phase == 'restart':
            case('native-potion-cleanup', fixtureId='native-potion-123', slot=index, ownerKey=key, nativeCarrier=carrier, helperId=helper_id,
                 recoveredSlot=18+index, recoveredStack=copy.deepcopy(stack), ledgerGone=True, nativeRequiredGone=True,
                 carrierGone=True, helperGone=True, nearbyHelpers=0, remainingNativeCarriers=0, blockType='minecraft:air', displayPayloadGone=True,
                 playerUse=False, client=False)
    case('native-aura-chunk-readiness', area='status_aura_qa', readableChunks=4, waitedTicks=5, preload=True)
    if phase == 'first':
        case('native-aura-acquisition', duration=597, ownLease=True, nativeParticleFlagsReadable=False)
    else:
        case('native-aura-saved-restore', duration=450, ownLease=True, reloadEventMode='replayed',storedLeaseMatchesNative=True,reloadWitnesses=1, reloadAcknowledgements=1,
             reloadAcknowledgement=dict(entity='saved-aura-wolf', id='speed', ticks=460, amplifier=0, tick=10))
        case('native-aura-foreign-handoff', duration=797, ownLease=False, nativeParticleFlagsReadable=False,
             foreignHandoffs=1, reloadAcknowledgementsUnchanged=True)
    case('native-one-tick-invisibility-expiry', nativeTicksObserved=2, scriptTicksWaited=3, playerConcealmentVerified=False)
    case('native-outline-registry', glowing=False, client=False)
    case('native-put-recovery', activations=2, idleCallbacksMeasured=False)
    case('native-splash-rolled-heal', health=6, effects=1, eventEnvelope='observer', physicalImpact=False)
    case('native-splash-persisted-hook', health=5, rawAmount=0, healAmount=3, declaredThisPhase=phase == 'first')
    case('native-splash-armor-stand-immunity', health=2, effects=0)
    for owned in (True, False):
        case('native-splash-hurt-source', owned=owned, health=14,
             event=dict(target='cow-owned' if owned else 'cow-unowned', damage=6, cause='magic', owner='owner-id' if owned else None),
             sourceMapping='magic_owner_only', directProjectileRepresented=False)
    case('native-splash-cancelled-hurt', health=20, apiAcknowledgements=1, status='APPLIED_NATIVE_INSTANT', actualHurtEvents=0, acknowledgementIsDeliveredDamage=False)

    def recipient(type_id, health, inanimate, mob):
        return dict(type=type_id, valid=True, componentIds=['minecraft:health'] if health else [], healthAvailable=health is not None,
                    health=None if health is None else dict(currentValue=health, effectiveMin=0, effectiveMax=health),
                    families=['inanimate'] if inanimate else [], inanimate=inanimate, mob=mob, errors={})

    xp = recipient('minecraft:xp_orb', None, True, False)
    case('native-vision-recipient-components', immediateXp=copy.deepcopy(xp), settledXp=copy.deepcopy(xp),
         testOnlyHealthHelper=recipient('living_effect_qa:health_helper', 100, True, False), cod=recipient('minecraft:cod', 3, False, False))
    case('native-vision-living-class', excluded='living_effect_qa:health_helper', excludedHasHealth=True, excludedHealth=100,
         excludedHasMobFamily=False, testOnlyHealthWitness=True, additionalExcluded='minecraft:xp_orb', xpHealthApiAvailable=False,
         admitted=['minecraft:cow', 'minecraft:armor_stand', 'minecraft:cod'], codHasMobFamily=False, targets=3, newTargetSounds=1,
         outline='unavailable', recipientFunctionOnly=True, playerEffectEntrance=False, client=False)
    case('native-upside-down-mob-class', renamed=['living_effect_qa:mob', 'minecraft:cow', 'minecraft:cod'],
         excluded=['minecraft:armor_stand', 'living_effect_qa:health_helper', 'minecraft:xp_orb'], codHasMobFamily=False,
         renames=3, recipientFunctionOnly=True, playerEffectEntrance=False, nameVisibilityParity=False, client=False)
    case('native-liquor-familyless-fall', target='minecraft:cod', nativeMobFamily=False,
         sourceEffect='kaleidoscope_world_liquor:multi_jump', controlHealth=[3, 2], controlHurtEvents=1,
         protectedHealth=[3, 3], protectedHurtEvents=0, snapshotObserved=True, snapshotWaitedTicks=5,
         nativeAcknowledgement=True, playerEffectEntrance=False, client=False)
    rows.append(dict(kind='done', phase=phase, players=0, playerSessions=0, client=False, crossPackPrivateData=False, addon_registration=addon))
    return dict(phase=phase, ok=True, normal_stop=True, errors=[], player_connections=0, observations=rows)


def raw_log(row):
    return ('Version: '+BDS_VERSION+'\n'+''.join(PREFIX+json.dumps(item)+'\n' for item in row['observations'])+'Quit correctly\n').encode()


def mode(row, name):
    return next(item for item in row['observations'] if item.get('mode') == name)


class RecorderTests(unittest.TestCase):
    def reject(self, row, raw=None):
        with self.assertRaises(AssertionError):
            validate_phase(row, raw if raw is not None else raw_log(row), VERSION)

    def test_complete_expanded_first_and_restart_contracts(self):
        for phase in ('first', 'restart'):
            row = transcript(phase)
            self.assertEqual(validate_phase(row, raw_log(row), VERSION)['version'], VERSION)
        # Both acknowledged and synchronously rejected native cancellation are honest observations.
        row = transcript('restart')
        mode(row, 'native-splash-cancelled-hurt').update(status='NATIVE_HURT_REJECTED', apiAcknowledgements=0)
        validate_phase(row, raw_log(row), VERSION)
        validate_potion_pair([transcript('first'), transcript('restart')])

    def recorded_inputs(self):
        current = {}
        for label, version in [('tavern', [0, 6, 139]), ('liquor', [0, 1, 116])]:
            trees = {kind: dict(sha256=('a' if label=='tavern' else 'b')*64, files=count) for kind, count in [('BP', 3), ('RP', 2)]}
            baseline = dict(repository='test/'+label, version=version, source_trees=copy.deepcopy(trees))
            current[label] = dict(baseline=baseline, source_trees=trees, commit='a'*40)
        overlays = {name: 'b'*64 for name in (
            'scripts/living-effects-probe.js', 'scripts/native-probe-inputs.js',
            'entities/living-probe.json', 'entities/health-helper-probe.json',
            'scripts/machine-ingredients-probe.js', 'scripts/status-aura-probe.js', 'scripts/potion-bottle-probe.js')}
        overlays['scripts/main.js'] = MAIN_OVERLAY_NOTE
        report = dict(sources={label: dict(commit=source['commit'], repository=source['baseline']['repository'],
                                          version=source['baseline']['version'], source_trees=source['source_trees'])
                              for label, source in current.items()}, test_only_overlays=overlays)
        return copy.deepcopy(report), current, overlays

    def test_recorded_sources_reject_matching_source_stage_drift_and_stale_identity(self):
        report, current, overlays = self.recorded_inputs()
        validate_recorded_inputs(report, current, overlays)
        # These trees are what the existing byte-for-byte source/stage check
        # accepts. Changing both copies must still fail the frozen/run binding.
        current['tavern']['source_trees']['BP']['sha256'] = 'c'*64
        with self.assertRaises(AssertionError):
            validate_recorded_inputs(report, current, overlays)
        current['tavern']['baseline']['source_trees'] = copy.deepcopy(current['tavern']['source_trees'])
        with self.assertRaises(AssertionError):
            validate_recorded_inputs(report, current, overlays)
        report, current, overlays = self.recorded_inputs()
        current['liquor']['commit'] = 'd'*40
        with self.assertRaises(AssertionError):
            validate_recorded_inputs(report, current, overlays)

    def test_recorded_overlays_reject_stale_observer_hash_and_changed_key_set(self):
        report, current, overlays = self.recorded_inputs()
        # Current source and staged observer agree; the original runner hash
        # remains authoritative for which helper actually produced the log.
        overlays['scripts/status-aura-probe.js'] = 'c'*64
        with self.assertRaises(AssertionError):
            validate_recorded_inputs(report, current, overlays)
        report, current, overlays = self.recorded_inputs()
        report['test_only_overlays']['scripts/main.js'] = 'undeclared append'
        with self.assertRaises(AssertionError):
            validate_recorded_inputs(report, current, overlays)
        report, current, overlays = self.recorded_inputs()
        del report['test_only_overlays']['scripts/native-probe-inputs.js']
        with self.assertRaises(AssertionError):
            validate_recorded_inputs(report, current, overlays)
        report, current, overlays = self.recorded_inputs()
        del report['test_only_overlays']['scripts/potion-bottle-probe.js']
        with self.assertRaises(AssertionError):
            validate_recorded_inputs(report, current, overlays)

    def test_missing_duplicate_and_unexpected_modes_are_rejected(self):
        for mutation in ('missing', 'duplicate', 'unexpected', 'legacy-only'):
            with self.subTest(mutation=mutation):
                row = transcript('first')
                if mutation == 'missing':
                    row['observations'].remove(mode(row, 'portable-stackable-ingredient-metadata'))
                elif mutation == 'duplicate':
                    row['observations'].insert(-1, copy.deepcopy(mode(row, 'native-put-recovery')))
                elif mutation == 'unexpected':
                    mode(row, 'native-put-recovery')['mode'] = 'unreviewed-mode'
                else:
                    row['observations'] = [item for item in row['observations'] if item.get('mode') in ('native-cross-id', 'native-put-recovery') or item['kind'] == 'done']
                self.reject(row)

        for phase in ('first', 'restart'):
            for missing in ('native-aura-chunk-readiness', 'native-upside-down-mob-class', 'native-liquor-familyless-fall', 'native-potion-registry', 'native-potion-liquid'):
                with self.subTest(phase=phase, missing=missing):
                    row = transcript(phase)
                    row['observations'].remove(mode(row, missing))
                    self.reject(row)
        row = transcript('restart')
        row['observations'].remove(mode(row, 'native-potion-cleanup'))
        self.reject(row)

    def test_potion_registry_requires_current_complete_partition_and_explicit_unmapped_ids(self):
        for key, value in [('currentPotionEffectTypes', []), ('mappedDisplayEffects', ['minecraft:healing']),
                           ('unmappedDisplayEffects', []), ('deliveryTypes', ['ThrownSplash']),
                           ('playerUse', True), ('client', True)]:
            with self.subTest(key=key):
                row = transcript('first'); mode(row, 'native-potion-registry')[key] = value; self.reject(row)
        row = transcript('first'); registry = mode(row, 'native-potion-registry')
        registry['mappedDisplayEffects'] = registry['currentPotionEffectTypes']; registry['unmappedDisplayEffects'] = []
        self.reject(row)

    def test_potion_liquid_requires_native_authority_complete_metadata_and_observed_properties(self):
        for target, key, value in [('row', 'ownerKey', 'wrong-owner'), ('row', 'nativeCarrierCount', 2),
                                  ('row', 'helperCount', 0), ('row', 'helperCount', 2), ('row', 'waitedTicks', 85),
                                  ('row', 'playerUse', True), ('row', 'client', True),
                                  ('helper', 'rgb', 0x87a363), ('helper', 'anchor', 'wrong-owner'), ('helper', 'inventory', True),
                                  ('helper', 'position', dict(x=16, y=300, z=4)), ('helper', 'rotation', dict(x=0, y=90)),
                                  ('nativeRecord', 'entity', 'replacement'), ('nativeRecord', 'token', ''),
                                  ('nativeStack', 'nameTag', 'blank'), ('nativeStack', 'properties', {}),
                                  ('nativeStack', 'rawLore', []), ('nativeStack', 'canDestroy', []),
                                  ('nativeStack', 'potion', dict(effectId='minecraft:poison', deliveryId='Consume'))]:
            with self.subTest(target=target, key=key):
                row = transcript('first'); liquid = mode(row, 'native-potion-liquid')
                (liquid if target == 'row' else liquid[target])[key] = value
                self.reject(row)
        row = transcript('first'); liquid = mode(row, 'native-potion-liquid')
        liquid['displayPayload']['potion'] = copy.deepcopy(liquid['nativeStack']['potion'])
        self.reject(row)
        row = transcript('first'); liquid = mode(row, 'native-potion-liquid')
        liquid['pickedStack']['properties'] = {}; self.reject(row)

    def test_potion_restart_cleanup_requires_original_receipt_and_no_remaining_owners(self):
        for key, value in [('fixtureId', 'native-potion-456'), ('nativeCarrier', 'replacement'), ('helperId', 'wrong-helper'),
                           ('recoveredSlot', 17), ('ledgerGone', False), ('nativeRequiredGone', False), ('carrierGone', False),
                           ('helperGone', False), ('nearbyHelpers', 1), ('remainingNativeCarriers', 1),
                           ('blockType', 'kaleidoscope_tavern:potion_bottle'), ('displayPayloadGone', False), ('client', True)]:
            with self.subTest(key=key):
                row = transcript('restart'); mode(row, 'native-potion-cleanup')[key] = value; self.reject(row)
        row = transcript('restart'); mode(row, 'native-potion-cleanup')['recoveredStack']['properties'] = {}; self.reject(row)

    def test_potion_restart_cannot_recreate_equivalent_fixtures_or_change_saved_metadata(self):
        for mutation in ('fixture', 'carrier', 'token', 'metadata', 'registry'):
            with self.subTest(mutation=mutation):
                first, restart = transcript('first'), transcript('restart')
                liquid, cleanup = mode(restart, 'native-potion-liquid'), mode(restart, 'native-potion-cleanup')
                if mutation == 'fixture':
                    for row in restart['observations']:
                        if row.get('fixtureId'): row['fixtureId'] = 'native-potion-999'
                elif mutation == 'carrier':
                    liquid['nativeCarrier'] = liquid['nativeRecord']['entity'] = cleanup['nativeCarrier'] = 'fresh-carrier'
                elif mutation == 'token':
                    liquid['nativeRecord']['token'] = 'fresh-token'
                elif mutation == 'metadata':
                    for stack in (liquid['nativeStack'], liquid['pickedStack'], cleanup['recoveredStack']):
                        stack['canDestroy'] = ['minecraft:dirt']
                else:
                    registry = mode(restart, 'native-potion-registry')
                    registry['currentPotionEffectTypes'].remove('minecraft:future_native'); registry['unmappedDisplayEffects'] = []
                # Each phase looks valid in isolation; only the paired world
                # binding rejects these fresh equivalents or altered metadata.
                for row in (first, restart): validate_phase(row, raw_log(row), VERSION)
                with self.assertRaises(AssertionError): validate_potion_pair([first, restart])

    def test_familyless_fall_requires_real_control_damage_and_public_snapshot(self):
        for key, value in [('target', 'minecraft:cow'), ('nativeMobFamily', True),
                           ('sourceEffect', 'kaleidoscope_world_liquor:reverse_gravity'),
                           ('controlHealth', [3, 3]), ('controlHurtEvents', 0),
                           ('protectedHealth', [3, 2]), ('protectedHurtEvents', 1),
                           ('snapshotObserved', False), ('snapshotWaitedTicks', 21),
                           ('nativeAcknowledgement', 1), ('playerEffectEntrance', True), ('client', True)]:
            with self.subTest(key=key):
                row = transcript('first')
                mode(row, 'native-liquor-familyless-fall')[key] = value
                self.reject(row)
        # An API return may acknowledge a subsequently cancelled native hurt.
        # Both return values are acceptable only with the same delivered outcome.
        row = transcript('restart')
        mode(row, 'native-liquor-familyless-fall')['nativeAcknowledgement'] = False
        validate_phase(row, raw_log(row), VERSION)

    def test_portable_ingredient_types_must_match_all_three_quality_four_rows(self):
        for mutation in ('missing', 'wrong-quality', 'duplicate', 'reordered'):
            with self.subTest(mutation=mutation):
                row = transcript('first')
                portable = mode(row, 'portable-stackable-ingredient-metadata')
                if mutation == 'missing':
                    del portable['rowTypes']
                elif mutation == 'wrong-quality':
                    portable['rowTypes'][0] = 'kaleidoscope_tavern:plum_wine_q3'
                elif mutation == 'duplicate':
                    portable['rowTypes'][1] = portable['rowTypes'][0]
                else:
                    portable['rowTypes'].reverse()
                self.reject(row)

    def test_chunk_readiness_requires_all_four_chunks_and_bounded_poll_ticks(self):
        for key, value in [('area', 'migration_qa'), ('readableChunks', 3), ('preload', False),
                           ('waitedTicks', 0), ('waitedTicks', 301), ('waitedTicks', 6), ('waitedTicks', True)]:
            with self.subTest(key=key, value=value):
                row = transcript('restart')
                mode(row, 'native-aura-chunk-readiness')[key] = value
                self.reject(row)
        for ticks in (5, 50, 300):
            row = transcript('first')
            mode(row, 'native-aura-chunk-readiness')['waitedTicks'] = ticks
            validate_phase(row, raw_log(row), VERSION)

    def test_upside_down_requires_all_three_renames_and_all_three_exclusions(self):
        for key, value in [('renamed', ['living_effect_qa:mob', 'minecraft:cow', 'minecraft:armor_stand']),
                           ('excluded', ['living_effect_qa:health_helper', 'minecraft:xp_orb']),
                           ('renames', 2), ('codHasMobFamily', True), ('nameVisibilityParity', True), ('client', True)]:
            with self.subTest(key=key):
                row = transcript('restart')
                mode(row, 'native-upside-down-mob-class')[key] = value
                self.reject(row)

    def test_restart_aura_saved_readback_requires_zero_replay_and_a_valid_lease(self):
        row=transcript('restart')
        restored=mode(row,'native-aura-saved-restore')
        restored.update(reloadEventMode='saved_readback',reloadWitnesses=0,reloadAcknowledgements=0,reloadAcknowledgement=None)
        validate_phase(row,raw_log(row),VERSION)
        for key,value in [('reloadWitnesses',1),('reloadAcknowledgements',1),('storedLeaseMatchesNative',False),('reloadEventMode','unknown')]:
            with self.subTest(key=key):
                changed=copy.deepcopy(row);mode(changed,'native-aura-saved-restore')[key]=value;self.reject(changed)

    def test_restart_aura_requires_complete_bounded_native_reload_acknowledgement(self):
        for target, key, value in [('row', 'reloadWitnesses', 0), ('row', 'reloadAcknowledgements', 0),
                                   ('row', 'reloadAcknowledgements', 2), ('row', 'reloadAcknowledgements', True),
                                   ('row', 'reloadAcknowledgement', None), ('ack', 'entity', ''), ('ack', 'id', 'jump_boost'),
                                   ('ack', 'ticks', 0), ('ack', 'ticks', 20000001), ('ack', 'amplifier', 1),
                                   ('ack', 'tick', -1), ('ack', 'tick', 1.5)]:
            with self.subTest(target=target, key=key, value=value):
                row = transcript('restart')
                restored = mode(row, 'native-aura-saved-restore')
                (restored if target == 'row' else restored['reloadAcknowledgement'])[key] = value
                self.reject(row)
        row = transcript('restart')
        del mode(row, 'native-aura-saved-restore')['reloadAcknowledgement']['tick']
        self.reject(row)
        row = transcript('restart')
        del mode(row, 'native-aura-saved-restore')['reloadWitnesses']
        self.reject(row)
        # Counters are process totals, not an assumption that exactly one reload occurred.
        row = transcript('restart')
        mode(row, 'native-aura-saved-restore').update(reloadWitnesses=3, reloadAcknowledgements=2)
        validate_phase(row, raw_log(row), VERSION)
        row = transcript('first')
        mode(row, 'native-aura-acquisition')['reloadAcknowledgements'] = 1
        self.reject(row)

    def test_foreign_refresh_must_handoff_once_without_consuming_reload_acknowledgement(self):
        for key, value in [('foreignHandoffs', 0), ('foreignHandoffs', 2), ('foreignHandoffs', True),
                           ('reloadAcknowledgementsUnchanged', False)]:
            with self.subTest(key=key, value=value):
                row = transcript('restart')
                mode(row, 'native-aura-foreign-handoff')[key] = value
                self.reject(row)
        row = transcript('restart')
        del mode(row, 'native-aura-foreign-handoff')['reloadAcknowledgementsUnchanged']
        self.reject(row)

    def test_machine_kind_overwrite_and_wrong_fields_counts_or_phase_are_rejected(self):
        for mutation in ('kind-overwrite', 'missing-field', 'counts', 'phase', 'duplicate-machine', 'duplicate-hurt-owner'):
            with self.subTest(mutation=mutation):
                row = transcript('restart')
                machine = mode(row, 'native-machine-restart-recovery')
                if mutation == 'kind-overwrite':
                    machine['kind'] = machine.pop('machineKind')
                elif mutation == 'missing-field':
                    del machine['completeNativeSlots']
                elif mutation == 'counts':
                    machine['counts'] = [10]
                elif mutation == 'phase':
                    machine['phase'] = 'first'
                elif mutation == 'duplicate-machine':
                    machines = [item for item in row['observations'] if item.get('mode') == machine['mode']]
                    machines[1].update(machine)
                else:
                    hurt = [item for item in row['observations'] if item.get('mode') == 'native-splash-hurt-source']
                    hurt[1].update(hurt[0])
                self.reject(row)

    def test_false_lifecycle_and_client_claims_are_rejected(self):
        mutations = [('row', 'ok', False), ('row', 'normal_stop', False), ('row', 'player_connections', 1),
                     ('row', 'errors', ['ERROR']), ('done', 'players', False), ('done', 'playerSessions', 1),
                     ('done', 'client', True), ('done', 'crossPackPrivateData', True), ('done', 'phase', 'first')]
        for target, key, value in mutations:
            with self.subTest(target=target, key=key):
                row = transcript('restart')
                (row if target == 'row' else row['observations'][-1])[key] = value
                self.reject(row)
        row = transcript('restart')
        mode(row, 'native-aura-foreign-handoff')['ownLease'] = True
        self.reject(row)
        row = transcript('first')
        row['observations'][-1]['addon_registration']['version'] = '0.1.111'
        self.reject(row)

    def test_report_cannot_override_raw_log_or_omit_failure(self):
        row = transcript('first'); raw = raw_log(row)
        mode(row, 'portable-stackable-ingredient-metadata')['nativeEquality'] = False
        self.reject(row, raw)
        row = transcript('first'); raw = raw_log(row)
        self.reject(row, raw.replace(b'Quit correctly', b''))
        self.reject(row, raw+PREFIX.encode()+b'{"kind":"failure","error":"late failure"}\n')
        self.reject(row, raw+b'Player connected: unexpected\n')
        self.reject(row, raw.replace(b'"nativeEquality": true', b'"nativeEquality": false'))

    def test_invisibility_expiry_requires_bounded_native_clock_evidence(self):
        for key in ('nativeTicksObserved', 'scriptTicksWaited'):
            row = transcript('first')
            del mode(row, 'native-one-tick-invisibility-expiry')[key]
            self.reject(row)
        for key, values in [('nativeTicksObserved', [0, 1, 19, True, 2.5]),
                            ('scriptTicksWaited', [0, 61, True, 3.5])]:
            for value in values:
                with self.subTest(key=key, value=value):
                    row = transcript('restart')
                    mode(row, 'native-one-tick-invisibility-expiry')[key] = value
                    self.reject(row)
        row = transcript('first')
        mode(row, 'native-one-tick-invisibility-expiry')['playerConcealmentVerified'] = True
        self.reject(row)

    def test_new_outputs_never_replace_either_existing_evidence_file(self):
        for existing in (EVIDENCE_NAME, LOG_NAME):
            with self.subTest(existing=existing), tempfile.TemporaryDirectory() as directory:
                work = pathlib.Path(directory); (work/existing).write_bytes(b'original proof')
                with self.assertRaises(AssertionError):
                    write_evidence(work, {}, ['new log'])
                self.assertEqual((work/existing).read_bytes(), b'original proof')
                self.assertEqual({path.name for path in work.iterdir()}, {existing})


if __name__ == '__main__':
    unittest.main()
