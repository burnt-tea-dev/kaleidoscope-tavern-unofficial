# Placed Molotov projectile candidate

Source candidate based on main `8d4a9c6a8d8e030fd07800b99de025572995fe7d`,
reviewed 2026-11-13. Native arrow delivery is **unverified**. This is not a
completed in-game repair, installable release or deployment.

## Confirmed source gaps

1. The Bedrock placed Molotov declared `collision_box: false` and a 10×14×10
   selection box. Java's Molotov inherits a collidable 6×14×6 bottle shape.
2. The current display-projectile callback did not recognize Molotov blocks.
   Delivering an arrow-hit event to that real callback left the bottle unchanged
   and did not spawn its incendiary projectile.

The second finding is a callback result, not proof that the current non-colliding
block can receive a real native arrow event. The attempted native comparison did
not reach its cases. No event is synthesized in the runtime repair.

## Candidate

- Restore both boxes to Java `box(5,0,5,11,14,11)`: Bedrock origin `[-3,0,-3]`,
  size `[6,14,6]`. Geometry, texture, item appearance and animation are unchanged.
- Let the existing display-projectile owner recognize a placed Molotov.
- Use the existing `spawnThrownDrink` Molotov branch to create one ownerless
  projectile at the block center, with zero initial velocity. Its existing native
  projectile/impact lifecycle owns falling and ignition; do not invoke ignition
  directly from the arrow callback or invent a substitute hit event.
- Preserve Java's order: Molotov creation precedes the base-bottle permission
  decision. A disallowed base removal leaves the bottle and still creates the
  ownerless projectile, as the source does. The existing Bedrock owner policy is
  retained; it is not a complete equivalent of Java's per-block `mayInteract`.
- On allowed removal, preserve water and suppress the queued natural-break item
  refund. On spawn/shoot/block-write failure, remove the uncommitted child and
  restore the bottle/water. Do not touch the incoming arrow's owner, metadata,
  position, velocity or persistence.

No polling, helper entities, new gameplay IDs, stored schema, recipe, version or
render resource is added. The transient thrown Molotov is the existing gameplay
projectile. There is no new model/animation work for Blockbench to validate.

## Java evidence

Current upstream branch heads were checked before this work:

- Forge 1.20.1: `c4ec1880bd44cf3139d3ba744ab30bb379cf1416`
- NeoForge 1.21.1: `a1afba34981a00e89d57130d3dc8f1e64f1820a2`
- Separate unpublished 26.1.2: `9b8f165a4641e738e694641dd81240a0206573e1`

All three implementations agree on the relevant behavior:

- [MolotovBlock](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/a1afba34981a00e89d57130d3dc8f1e64f1820a2/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/block/brew/MolotovBlock.java)
  uses `noOcclusion`, not `noCollission`, and creates a projectile at position
  +(.5,.5,.5) before calling its superclass.
- [BottleBlock](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/a1afba34981a00e89d57130d3dc8f1e64f1820a2/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/block/brew/BottleBlock.java)
  supplies the shape and uses `mayInteract` only for removal/glass fragments.
- [ThrownMolotovEntity](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/c4ec1880bd44cf3139d3ba744ab30bb379cf1416/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/entity/ThrownMolotovEntity.java)
  owns ignition on its subsequent impact, rather than immediate arrow ignition.

Read-only inspection of the official Minecraft 1.21.1 client bytecode and mappings
also confirms that `BlockBehaviour.Properties` defaults `hasCollision` to true,
`noOcclusion` changes a different flag, and `getCollisionShape` (mapped line 355)
uses the block's shape while collision is enabled. The reviewed client and mapping
SHA-1 values are respectively `30c73b1c5da787909b2f73340419fdf13b9def88` and
`2244b6f072256667bcd9a73df124d6c58de77992`. No Minecraft class was executed by
this inspection and no complete Mojang dump is committed.

## Tests and source ownership

- Existing Molotov suite before repair: **11 failing, 8 passing**. Those failures
  distinguish the shape, spawning/order and failure-handling gaps.
- Final Molotov suite: **20 passing**, including a queued natural-break no-refund
  check. Together with existing potion and extension-bottle adapter tests:
  **34 passing**.
- Independent review: all 20 Molotov cases plus **8 additional passing** cases
  for wet spawn/shoot failures, block failure before/after mutation, and exact
  arrow metadata preservation across four player modes.
- Existing current-extension contract, development baseline structure and diff
  checks pass. The launch check passes after its existing immutable historical
  Git inputs are materialized. Its no-argument run does not reverify Java inputs.
- Historical identity regression: **35 passing**; existing motion preservation
  check passes. No new motion or rendered-client acceptance is claimed.

The two changed runtime files move from old source-byte reversal to the existing
current-extension owner. Their former ledger rows are preserved unchanged as
history, and the obsolete display-projectile reverse edge is retired. Current
shape/wiring and the real callback regressions now own the change. No hash update
or inverse patch makes an untested runtime body pass.

```sh
node --experimental-loader ./tools/foundation/mock-loader.mjs --test tools/molotov-fire-adapter.test.mjs tools/potion-bottle-visual.test.mjs tools/extension-bottle-adapter.test.mjs
python tools/current_extension_source_contract.py
python tools/check_launch.py
python tools/baseline_gate.py check
git diff --check
```

## Native attempt and remaining gates

An isolated official BDS 1.26.52.3/build 51798919 attempt identified the QA pack but
stopped during Minecraft service startup, before script initialization or any
arrow trajectory. Its `@minecraft/server` 2.7.0 declaration is not evidence of a
successful API initialization. It produced **no** hit/miss or ignition result.

The attempted server contacted the official `client.discovery.minecraft-services.net`
service; exact request path/method/payload were not observable in its log. TCP was
observed at 127.0.0.1:29754, while a separate UDP socket at `*:7551` had an unknown
purpose. Full loopback-only binding was therefore not established. The test was
not retried or worked around by disabling authentication. No test process remains,
and no existing service or world was altered.

A source-pinned offline pack is prepared for later authorized native validation.
It installs the actual display/Molotov listeners and observes native arrows and
child projectiles; it does not call handlers or ignition to simulate success.
Required native gates remain: physical arrow collision versus solid/miss controls,
zero-velocity projectile activation, water/permission behavior, and the complete
fall/impact/fire chain. Current release-engine and client/multiplayer acceptance
are also outstanding.

Paired version freezing belongs to the coordinated integration. Until that and
native acceptance are complete, retain this as a draft. No release guard is
weakened and no LIVE deployment is requested or performed.
