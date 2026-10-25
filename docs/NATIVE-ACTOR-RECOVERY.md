# Exact native actor recovery and conservation

`tools/native_actor_recovery.py` admits an explicit original stopped-world plan
and repairs only canonical `digp` pointers and a proved UTF-8 replacement
`StorageKey`. It retains complete original item NBT, active authority, original
UID/root/token, malformed aliases, world properties, block data and unrelated
records. It never opens LIVE or a caller-designated source world through its
world API. Recovery is one atomic batch; conflicting or partial states refuse.

The narrow `pending_removed_bowl: true` plan profile additionally requires
`cookery_bowl`, `pending_remove: true`, the observed original owner cell to be
exactly `minecraft:air` with its pinned typed states, and the actor's unchanged
root to describe that same dimension/cell as
`kaleidoscope_chinesefood:bowl_stack`. Its active binding must still name the exact
original UID. The full typed inventory hash must match and contain exactly three
original `minecraft:bowl`. Normal air, replaced/foreign blocks, missing or false
pending state, altered binding/root and a different inventory refuse. This
profile makes the original pending native break transaction loadable; it does
not clear properties, replace blocks or materialize items offline.

Each recovery receipt carries `original_inventory_nbt_hex`, bound by the plan's
complete typed inventory hash. A pending removed target also records original
loose Item UIDs so pre-existing nearby bowls cannot substitute for the returned
original inventory.

`tools/native_actor_recovery_validation.py` verifies the stopped snapshots after
the existing native first-load and restart runs:

```python
commands = validation.commands(plan)
# The orchestration owner executes those commands in the normal isolated QA run.
observed = validation.inspect_world(world, plan,
    stage_root=stage_root, source_world=source_world)
observed['native_run'] = copy.deepcopy(native_run_record)
verified = validation.verify(plan, recovery_receipt, observed, previous=None)
# After the same world has normally restarted:
verified_restart = validation.verify(plan, recovery_receipt,
    restart_observation, previous=observed)
```

The normal run receipt must prove successful zero-player startup/stop, a distinct
phase log, and acknowledgement/cleanup of every planned named ticking area.
Areas coalesce only targets in the same exact dimension/chunk; more than ten
required areas refuse. Missing load evidence remains an explicit observation
requirement and cannot pass because actor/index bytes happen to exist.

Active Tavern cabinets and Cookery bowls retain their original UID, native slots,
full typed item metadata/count, owner/token/root/binding and one correct aligned
`digp` reference. The comparison permits compound key ordering, empty-slot
serialization and unrelated native runtime fields to change. It preserves every
occupied item's typed payload. It never accepts identifier-only item equality.

For the pending removed profile, the old canonical actor must be absent and
unindexed, binding/pending properties absent, and retained malformed aliases
unchanged and unindexed. Exactly three original bowls must appear as ordinary
native Item entities in the original dimension/XZ cell, within one block below
to two blocks above the original Y. Their full typed Item metadata is compared
after removing the inventory-only Slot and aggregating Count; all other item
fields and NBT types remain significant. Each returned Item needs a unique native
UID, canonical eight-byte StorageKey and one correct index. The same returned
Item UID/key/metadata/count set must remain after restart; replacement Items or a
second return refuse. Items outside that small region leave conservation
unverified rather than triggering a broad search or an item waiver.

Both tools expose pure functions for synthetic tests. The validator's world API
reuses the same explicit idle-stage/nonlinked boundary and performs no gameplay
writes. Tests do not establish native or rendered acceptance; source, full-family
native, saved-world and human client gates remain separate.

```sh
python3 tools/test_native_actor_recovery.py
python3 tools/test_native_actor_recovery_validation.py
```
