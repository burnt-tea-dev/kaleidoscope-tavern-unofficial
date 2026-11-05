# Tavern 0.6.203

Incense uses its own native zombie-villager conversion with a three-second
countdown. The selected vanilla actor definitions and normal golden-apple cure
remain intact. Later incense damage is no longer skipped by a curing tag,
including tags already present on saved actors.

Native BDS 1.26.60.6 observed exactly 60 ticks for v2 conversion and exactly
60 ticks after restarting its countdown. The tested setup routes all resolved to
v2; the legacy type is not verified. The same-world saved final-state readback also passes after waiting for
chunk/actor loading and resolving the original saved entity ID. The initial
read-too-early failure remains in the evidence; no first-phase case was replayed.
Trade/equipment preservation and client audiovisual behavior are not established.
See the [current incense evidence](PARITY-MATRIX.md#香薰專用原生轉換2026-11-06).
