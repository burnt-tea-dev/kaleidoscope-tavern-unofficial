# Tavern 0.6.170: shaker editor arithmetic normalization

Status: local source candidate; publication is disabled. Native warning-removal, paired-family admission, saved-world and human client acceptance remain separate gates. This is not a gameplay-fix or complete Java-parity claim.

## Exact change

The signed-coefficient formatter in `tools/shaker_held_frames.py` now emits explicit subtraction for the negative coefficient. Its generated resource changes only `animation.kt_mixology.shake_first_left/bones/grip/position[0]`:

```text
4.50451374 + -1.53805532 * math.sin(q.life_time * 1718.87338539247)
4.50451374 - 1.53805532 * math.sin(q.life_time * 1718.87338539247)
```

For every real sine value, `a + (-b)*s` equals `a - b*s`. All other item/player expressions, source clocks, selectors, hand dispatch, camera/socket placement, geometry, UVs, textures, materials and gameplay remain unchanged. Required package versions and owned BP/RP dependency metadata advance together without changing UUIDs.

The predecessor is published source commit `4584618e94332068749046be73d766f883b49eb6`. The animation file SHA256 changes from `01e9ebc9e822f4d6c3826dd2a04e3abff963956f176f9dea5a35862e8a3844fa` to `2740cf7f4bc4a05c432e98e591d964169b992bf8cb1553ecb4425be91f54fb06`. One appended test-only review layer reverses exactly this line to the earlier bytes; all existing layers and immutable T168/T169 witnesses are retained.

## Regression scope

The nine held-frame tests retain all existing geometry/dispatch coverage and add generated/shipped spelling checks, rejection of the original adjacent-operator and wrong-sign mutations, and numeric comparisons. The six native-frame tests remain intact. The historical T168 test selects its exact release rather than assuming it is forever the last review layer, retaining its immutable source/hash/tampering checks.

Before versioning, the exact unchanged animation candidate was independently checked with official Blockbench 5.2.2 source commit `c9ace42ef1b770bdadfe656729c7833b8feb37d2`: 4,577 source/inverse parser comparisons had zero pairwise difference; four isolated fixtures had 264 channel-axis conversion checks and no validator warnings. The original adjacent-operator warning was preserved in its original fixture. These source/parser checks do not replace actual native UI observation or prove Bedrock runtime grammar acceptance.

The original source operator sequence is not established here as a Bedrock content error. Camera adaptations, native `this` coordinates, clock epoch alignment, and later Java arm-pose layers are outside this change. Intended oscillation frequency does not establish a runtime phase-reset contract.

## Admission boundaries

World Liquor 0.1.147 still declares exact Tavern 0.6.169 dependencies. Its preserved manifest/baseline equality checks do not admit Tavern 0.6.170 as that frozen pair. Existing family pins remain untouched and require a separately reviewed paired update. This is a static contract statement, not an observed engine-resolution result.

Publication remains disabled. No earlier runtime/client/deployment receipt is reassigned to this candidate. Use the canonical regression, clean freeze/identity and package gates; a generated archive alone does not establish native/client or full-family acceptance.
