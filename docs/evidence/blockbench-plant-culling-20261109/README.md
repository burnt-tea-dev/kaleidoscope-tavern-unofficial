# Crop and filled-vine cutout policy

The candidate changes exactly **36 material fields in four BP resources**:
eight each for ordinary/gold/ice crops and twelve for ordinary single-shape
filled-vine routes. `alpha_test_single_sided` matches the source cutout culling
policy while preserving every authored direction. Ordinary connected shapes
(24 permutations, 48 material fields) and gold/ice A3 vines are unchanged.

No geometry, ±0.08 displacement / 0.16 thickness adaptation, UV, PNG, AO,
dimming, item transform, collision, selection, loot, growth, waterlogging or
connection/state routing changes. PR613 wild-vine rescale and materials, the
accepted +6 tilted rack, and known Allium clipping limitation are retained.

## Review and source boundaries

**Eighteen original 1188×848 JPEGs form nine same-camera Front/Double pairs.**
All nine show visibly increased native leaf/fruit coverage in Double. Source
controls and the ordinary vine’s already-correct north_south control remain
unchanged, supported by decoded-pixel checks. The exact [GUI receipt](gui-review.json)
records cameras, observations and limits; [images.json](images.json) separates
18 accepted model views from 24 supporting UI/camera diagnostics and zero
excluded images. All scene changes were unsaved and discarded.

Preparation files in the archives retain their original review-only/pending
wording without rewriting history. The final GUI receipt supersedes that status.

The original full source audit covers 1,026 effective state combinations, 48
models and 660 directed faces. `current-reuse.json` separately verifies all 63
relevant runtime inputs unchanged from the original 0.6.213 proposal at accepted
0.6.214 main `682a9dd01cc8d5ad26b714c0b279d04cbafeb205`. Historical reports and
scripts requiring their old origin/main identity were not rewritten or rerun.

All model sources use cutout. Official Java 1.20.1 and 1.21.1 class data and
pinned maintained Forge/NeoForge sources establish default CULL. Class bytes
were read as data, not executed. The exact Forge 47.3.0 archive returned 403 in
the earlier investigation and was not retried. Exact loader-release archives
and 26.1.2 renderer behavior remain unchecked. Fresh read-only GitHub branch
checks at 2026-11-09 02:59:59 UTC still resolve Forge main to c4ec1880 and
NeoForge 1.21.1 to a1afba34. Fresh pinned gradle.properties reads match local
Git blobs; [the receipt](upstream-freshness.json) distinguishes this check from
local byte revalidation. No complete JAR, mapping file,
vendor bundle, binary executable or credentials are included.

The source lacks same-name crop/filled-vine item models. The native stage-zero
item_visual fallback stays consistent with the source-backed geometry policy;
this is not Java inventory-context, fruit/bare-trellis item or held-pose parity.

Free-format Front/Double texture controls demonstrate editor sidedness only,
not execution of native BP material_instances. No Minecraft client, BDS, native
renderer, saved-world, LIVE, full-family or deployment acceptance is claimed.

## Portable evidence

`archives.json` and `archive-entries.json` bind 401 exact members: original
review reports/scripts, 14 original/control scenes, 21 reused Front captures,
204 pinned source/runtime/review inputs, bounded semantic receipts and current
source-contract inputs. Every archive part is at most 180,000 bytes. Concatenate
parts in the recorded order to recover a split ZIP. The validator does this
in memory. All 42 raw final GUI/model/settings captures are preserved separately under
images/accepted and images/diagnostics, without re-encoding.

Run:

```
python docs/evidence/blockbench-plant-culling-20261109/validate_evidence.py --repository .
```

The replay checks artifact/member/image hashes, the exact 36-field delta,
resolved-face control isolation and 12 mutation negatives, and recomputes all
nine original-JPEG decoded-pixel comparisons without writing or re-encoding an image. It executes only the
preserved independent checker's pure comparison functions, never its historical
Git/path/output body. It also runs the current shared cultivation tests from the
portable source subset. Optimized Python is rejected. Nothing is downloaded,
no GUI or game starts, and repository files are not changed.

The current shared owner checks 108 base/permutation declarations and all 1,026
states. Its tests reject each of 204 possible double-sided material regressions
plus route, shading, texture, face-ownership and item-fallback mutations. The
actual board/farm adapters are a separate source regression suite, not gameplay.

`ownership-handoff.json` records the existing aggregate's 149 → 145 remaining
block scope, four original beforeProjected hashes, and unchanged 159-file
original aggregate. `validate_handoff.py --repository .` reconstructs both
aggregates and rejects a retained historical block mutation without disk edits.
Eight historical postimage entries are retired; no new inverse/version ledger
or unrelated generator is added. See [the current material contract](../../CULTIVATION-PLANT-MATERIALS.md).

## Local integration validation

The unmodified formal aggregate passed with pinned Java source and the original
cedfaedf integration baseline. The installed compiler module required an existing
helper on PATH for that command only. No new test bypass or exemption was added;
the existing conditional World Liquor timed-effects SKIP remains. The first
attempt stopped on that prerequisite and is not counted as a full pass. See
[local validation](local-validation.json) and [compiler environment](compiler-environment.json).

After the pass, main advanced only by the 44 new N02 evidence files. The
[base update receipt](docs-only-base-update.json) supplies exact Git commands
proving that the two base revisions differ only by those added documents, with
matching runtime, tool, test, data, art and SDK trees and metadata blobs. A complete
before/after candidate manifest was not retained, so no candidate-wide fingerprint
is claimed. The original aggregate result is reused for that docs-only base
advance; it was not rerun.

## Later family-lock base advance

The final base then advanced to fde4293e (#615), changing only
`family/upstream.lock.json` to select the reviewed BetterBiomes V.7 archive and
manifest compatibility release 1.0.10002. [The separate receipt](family-lock-base-update.json)
records the exact delta, unchanged Tavern runtime/test/source and identity objects,
and targeted family tests. The new lock is preserved byte-for-byte.

This lock is an input to full-family assembly and preparation receipts. Those
results cannot be reused under the new lock hash. The existing standalone Tavern
aggregate is retained; this task did not download the BetterBiomes archive, rerun
full-family admission or add a test exemption. The existing conditional World
Liquor SKIP remains. Canonical standalone packaging and strict identity checks
are repeated from the final clean commit without another freeze or version bump.
