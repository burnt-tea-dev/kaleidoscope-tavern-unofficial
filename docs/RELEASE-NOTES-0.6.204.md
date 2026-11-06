# Tavern 0.6.204

High Heels no longer treats every non-air front cell as a reason to lift the
player. It first asks a native block raycast to exclude passable blocks and
liquids, then retains the existing destination collision check and velocity.

The source regression uses the actual White Lady effect data and production
step callback. A slowly approached dandelion previously requested a one-block
teleport; flower/water now request none, with solid steps and rejected native
clearance retained. These tests use Script API interface doubles.

Native Player validation has now found that the exact current
`tryTeleport` options reject `keepVelocity` on BDS1.26.60.6/server2.7.0.
The three walking fixtures physically moved, but the simulated Player's native
movement-input getter stayed zero, so they never reached the production step
predicate. They are inconclusive, not passed walking cases. See the
[sanitized native result](../data/native-high-heels-player-204.json).

This remains a draft with a known unavailable Player path. No LIVE deployment
or full Java parity is claimed. A separate QA-only native component proposal
must establish Player capability before gameplay or shared composition changes.
Existing saved status format, API module versions and other effects are unchanged.
See the [current High Heels row](PARITY-MATRIX.md#other-tracked-mechanics).
