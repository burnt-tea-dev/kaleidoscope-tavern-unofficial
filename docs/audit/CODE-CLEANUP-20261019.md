# Evidence-led tooling cleanup, 2026-10-19

This review starts from canonical `6f30ad23cbf54433cd2cc0ad2425af8bbc03799b`. The [exact deletion manifest](CODE-CLEANUP-20261019.json) was written before removing any file; it records the original Git blob, SHA256, size, reason and retained coverage. Historical reports and artifacts retain their original scope.

## Retired one-shot code

`effects-apply.yml` only applies the already-merged September 28 patch when its own file changes on the old effects branch. `transfer.part1/2/3` have exactly that workflow as their executable consumer. `pick-block-snapshot.yml` only archives the September 25 foundation branch when its own workflow changes. Both branch tips are main ancestors. Current effect regressions, foundation/creative pick and `test_pick_block.py` remain in `validation.yml`; no gameplay test is removed. The original content remains at this review commit in Git.

## Consolidated retention coverage

reviewed integration/reviewed integration/reviewed integration/reviewed integration files duplicate the same finite-map and assembly fixture, changing the owner version and later adding paired-component assertions. One parameterized suite checks every explicit owner version 51 through 54, every retained component, declaration hash rejection, foreign owner/version/map rejection, recorded component owner/source version, paired BP/RP routing, local-candidate provenance and unsupported future/version-shape rejection. reviewed integration/reviewed integration's independent copy/symlink/mutation coverage remains in `test_retained_host_profiles.py`. The current CI and aggregate release CLI invoke the replacement; historical commands use the frozen Git source they originally tested.

## Unconsumed reference work and duplicate setup

The normal audit downloads and disassembles the same Minecraft 1.20.1 references, but none of its test commands reads `vanilla-reference`; only a provenance JSON is copied to the artifact. This is generation-only input work, not an assertion comparing the current addon. Remove those two workflow lines rather than caching an unused result. Keep `collect_reference.py`, the manual `--reference` generators, committed source hashes, all effect tests and their reports. Run the existing effect suites with no reference directory to verify the actual dependency boundary. The old 14–16 minute/day cache estimate is superseded by this stronger source finding; no new measured savings are claimed.

The second identical nbtlib install in the baseline job is redundant with the unconditional first install. Runtime jobs now need the existing baseline gate as well as impact, so an invalid baseline stops expensive tasks without hiding the failing check. Required job names and family admission rules remain intact.

## Validation and limits

Targeted local results and actual PR checks are recorded separately by the host audit. Full required validation belongs to CI. This change does not modify runtime, release identity, dependency lock or LIVE; it cannot certify rendered gameplay or human acceptance. No failing behavior test is deleted to obtain a green result.

## Current HUD coverage follow-up

The [assertion map and preimage hashes](HUD-COVERAGE-20261019.json) show that two production-labelled test files still imported the retired title/queue helper while the real sender uses the graphical Actionbar factory. Route valid packets and malformed/oversized rejection through `bedrock/shaker-hud-transport.js` directly. Replace retired server-timeout cases with actual disconnect/owned-stop isolation, retaining the existing UI lifetime, generator reconstruction and heartbeat assertions unchanged. The old exported helper and all runtime/release bytes remain unchanged; its retirement is a separate payload boundary.
