# Grape support-loss drops

Reviewed against main `8d4a9c6a8d8e030fd07800b99de025572995fe7d` on 2026-11-13.
This is an unfrozen source candidate. Paired release identity is reserved for the
family integration owner; it is not an installable release or a LIVE change.

## Player-visible failure and repair

Pruning or breaking a grapevine trellis removed its hanging fruit inside the
parent transaction. That transaction intentionally suppresses the later natural
break callback, so a mature bunch disappeared without its own drops. Independently,
the natural-break fallback emitted one fruit for every crop age, instead of the
crop's maturity-dependent Java loot.

- Commit the parent trellis transaction first, then invoke the existing crop
  support maintenance. Its ordinary natural-break owner handles the fruit.
- Use the existing `fruitHarvest(kind, age, false)` source contract for all three
  crops: immature crops drop nothing; mature crops drop 1–2 of their own fruit,
  plus a 30% chance of one green grape.
- Keep a secondary crop break separate from the player's direct Creative break.
  This preserves support-loss drops without restoring the parent's Creative drops.
- The shared shearing transaction now respects `doTileDrops=false` after its block
  changes. Pruning and harvesting still change the block and wear the tool, but do
  not spawn resources. Only these two cultivation paths call this transaction.
- Preserve existing rollback: a failed parent transaction retains fruit; a failed
  child drop withdraws partial items and restores the crop for a later retry.

No item IDs, saved properties, resource assets, models, helper entities, timers,
recipes, manifests or release history are changed. The new work is event-driven;
there is no added scan or visual-helper cost.

## Java authority

Forge 1.20.1 source `c4ec1880bd44cf3139d3ba744ab30bb379cf1416`:

- [GrapeCropBlock](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/c4ec1880bd44cf3139d3ba744ab30bb379cf1416/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/block/plant/GrapeCropBlock.java):
  `updateShape` returns air after losing its mature trellis support; `getDrops`
  is empty below age 5. Shearing removes the fruit, emits resources through
  `Block.popResource`, and damages the shears.
- [GrapevineTrellisBlock](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/c4ec1880bd44cf3139d3ba744ab30bb379cf1416/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/block/plant/GrapevineTrellisBlock.java):
  shearing replaces the vine with a bare trellis using a neighbor update, emits
  one grapevine through `Block.popResource`, and damages the shears.
- Generated loot for [grape](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/c4ec1880bd44cf3139d3ba744ab30bb379cf1416/src/generated/resources/data/kaleidoscope_tavern/loot_tables/blocks/grape_crop.json),
  [ice grape](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/c4ec1880bd44cf3139d3ba744ab30bb379cf1416/src/generated/resources/data/kaleidoscope_tavern/loot_tables/blocks/ice_grape_crop.json),
  and [gold grape](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/c4ec1880bd44cf3139d3ba744ab30bb379cf1416/src/generated/resources/data/kaleidoscope_tavern/loot_tables/blocks/gold_grape_crop.json):
  1–2 own fruit and a 30% green-grape pool.

The same crop, trellis and loot semantics were independently checked in NeoForge
1.21.1 source `a1afba34981a00e89d57130d3dc8f1e64f1820a2` and the separate,
unpublished [26.1.2 source](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/tree/9b8f165a4641e738e694641dd81240a0206573e1/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/block/plant)
`9b8f165a4641e738e694641dd81240a0206573e1`. This is a scoped comparison, not
complete gameplay acceptance for any of those branches.

### Vanilla neighbor updates and drop rule

The existing official Minecraft 1.21.1 [client JAR](https://piston-data.mojang.com/v1/objects/30c73b1c5da787909b2f73340419fdf13b9def88/client.jar)
and [client mappings](https://piston-data.mojang.com/v1/objects/2244b6f072256667bcd9a73df124d6c58de77992/client.txt)
were independently verified against their metadata SHA-1 object IDs. Read-only
inspection used the installed JDK's `jdk.jdeps/com.sun.tools.javap.Main` module;
no Minecraft class was executed and no full bytecode dump is committed.

Mapped bytecode follows `Level.setBlockAndUpdate` (line 326, flags 3), neighbor
shape dispatch (lines 257–261), `BlockStateBase.updateNeighbourShapes`
(lines 1121–1126), `CollectingNeighborUpdater.ShapeUpdate.runNext`
(lines 143–144), and `NeighborUpdater.executeShapeUpdate` (lines 35–38).
The latter invokes the crop's `updateShape`, then `Block.updateOrDestroy`.
That function (lines 174–183) calls `destroyBlock` with drops enabled when bit 32
is absent and with a **null destroying entity**. `Level.destroyBlock`
(lines 308–313) calls `Block.dropResources`; `Block.getDrops` reaches the crop's
maturity override. This is why breaking the support in Creative does not discard
the secondary crop's loot. `Block.popResource` (lines 395–402) independently gates
item spawning on `RULE_DOBLOCKDROPS`, including shearing. Vanilla bytecode scope is
1.21.1 only; the separate 26.1.2 vanilla engine was not inspected.

## Targeted verification

The existing `tools/board-farm-interaction.test.mjs` now exercises the registered
interaction, protected-break, crop-tick and natural-break callbacks. Its local
fixture explicitly models the queued script-removal callback already documented
by `scripted-block-change.js`; this does not constitute a new BDS execution.

- Initial support/maturity matrix: 14 failures and 2 passes before the runtime
  repair, then all 16 passed. It covers three varieties, age 4/5, Survival/Creative
  pruning, and parent break with either value of `doTileDrops`.
- Shearing gamerule matrix: all 6 failed before the shared guard, then all passed.
  It covers pruning and direct harvesting for each variety and asserts tool wear
  and committed block changes as well as the absence of drops.
- Three added safety cases cover parent spawn failure, partial child spawn failure
  with restore/retry/no duplicate, and unknown support plus the two-fruit outcome.
- Final existing owner suite: **60 passed** (35 previous cases and 25 new cases).
- Adjacent existing machine, potion-bottle and shaker-retention suites: **72 passed**.
- `cultivation_source_contract.py`, `current_extension_source_contract.py`, and
  `git diff --check`: passed. Static resource checks are not new visual acceptance.
- Development baseline structure check passed with identity explicitly unchecked.
- Independent review confirmed the source semantics and injected additional
  first/second child drop and parent drop failures; no blocking finding remained.

Reproduce from the repository root:

```sh
node --experimental-loader ./tools/foundation/mock-loader.mjs --test tools/board-farm-interaction.test.mjs
node --experimental-loader ./tools/foundation/mock-loader.mjs --test tools/machine-native-ingredients.test.mjs tools/potion-bottle-visual.test.mjs tools/shaker-item-retention.test.mjs
python tools/cultivation_source_contract.py
python tools/current_extension_source_contract.py
python tools/baseline_gate.py check
git diff --check
```

## Limits

- The final candidate has no new native BDS/client run. In particular, actual
  engine callback delivery/timing, chunk boundaries and concurrent players remain
  native validation work. Deterministic API doubles do not establish those results.
- Java loot also carries `survives_explosion`; the existing scripted drop path does
  not reproduce explosion-radius survival probabilities. This repair is not a
  claim of complete explosion parity.
- Full CI, fresh paired identity, clean-release packaging and saved-world
  deployment are separate gates. No version guard was weakened to make an
  unfrozen candidate installable.
- No model or animation changed, so Blockbench is not a relevant validation step
  for this script-only repair. Earlier visual reviews are not counted again.
