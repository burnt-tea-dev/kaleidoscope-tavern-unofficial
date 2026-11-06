# Tavern 0.6.204

High Heels no longer treats every non-air front cell as a reason to lift the
player. It first asks a native block raycast to exclude passable blocks and
liquids, then retains the existing destination collision check and velocity.

The source regression uses the actual White Lady effect data and production
step callback. A slowly approached dandelion previously requested a one-block
teleport; flower/water now request none, with solid steps and rejected native
clearance retained. These tests use Script API interface doubles.

This source-first change has no BDS/real-Player movement or LIVE deployment
claim. Native step-height attributes, partial-block/diagonal movement and full
Java parity remain outside the established result. Existing saved status format,
API module versions and other effects are unchanged. See the
[current High Heels row](PARITY-MATRIX.md#other-tracked-mechanics).
