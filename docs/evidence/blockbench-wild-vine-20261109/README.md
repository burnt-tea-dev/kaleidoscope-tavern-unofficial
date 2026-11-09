# Wild grapevine: source width and directed cutout faces

The completed editor review supports restoring the Java cross rescale for both
growing head and body. The active a2 center-plane X/Z span returns from the old
11.3844191771-unit slabs to the source's 14.4 units. The shared geometry keeps
all four authored directed UV faces. The final coupled repair also changes only
the four head/body world/item wildcard material methods to
`alpha_test_single_sided`, aligning culling with the documented source policy.
AO, dimming, textures, identities, poses and gameplay remain unchanged.

**Thickness is an adaptation:** the candidate's centered 0.16-unit slabs put
surfaces ±0.08 from the source planes and span about 14.513137157 overall. The
source is zero-thickness. Geometry SHA-256 is
`e7e8c23f421aba7d8082c6952d6599bc5fb99231c9a656ff1566b4303cbd0d0b`.

## What was actually reviewed

[Twenty accepted original views](images.md) comprise eight Front-sided Free
source/current/candidate comparisons, eight native before/candidate North/South
controls, and four one-variable South sidedness controls. The exact captures,
scene/input hashes, camera directions, observations and limitations are retained
in [the GUI receipt](gui-review.json). Three excluded and three diagnostic images
are preserved separately and never counted as artwork acceptance.

The earlier Free BEFORE South loss **is not a proven missing-back runtime bug**.
Its texture was explicitly Front-sided, while native imports use the editor's
Auto/DoubleSide path. Switching only the Free texture sidedness reproduced the
native mirrored BEFORE sprite and the candidate's extra fills. Zero-thickness
SOURCE Double controls exhibit coplanar stripes; no pixel-exact Double parity is
claimed. Front-sided source/candidate views support the intended width and sprite
orientation. Native geometry imports omit BP materials, so they do not directly
certify the final single-sided runtime route or lighting.

Microsoft's [material reference](https://learn.microsoft.com/en-us/minecraft/creator/reference/content/blockreference/examples/blockcomponents/minecraftblock_material_instances?view=minecraft-bedrock-stable)
distinguishes disabled culling in alpha_test from enabled culling in
alpha_test_single_sided. Official Java 1.20.1 and 1.21.1 class data confirms that
vanilla cutout retains default CULL. Pinned maintained Forge 1.20.x and NeoForge
1.21.1 source maps named cutout to that world type and to culled layered items.
The [bounded material proposal](material-route-proposal.json), now applied,
records exact references and limitations. It preserves both directed faces of
each plane rather than deleting the back-facing authored surface.

## Portable evidence and replay

`archives/review-inputs.zip` preserves exact original scenes, bounded source
models/blockstates/textures, direct controls, sidedness controls, source receipts,
independent geometry checks, current final input subset and licenses.
`archive-entries.json` binds every member. No complete official archive, uploaded
mod JAR or whole mapping file is included. Original preparation reports inside
`review/` retain their historical pending status; the final GUI receipt and this
README supersede that status without rewriting original evidence.

Run `python docs/evidence/blockbench-wild-vine-20261109/validate_evidence.py`.
It checks all artifact/member/image hashes, replays the independent source
geometry/UV negative controls in a temporary directory, checks the current
surface contract, and verifies the exact four-field material delta. It does not
run historical builders, download anything, launch an editor/game or modify the
repository. Add `--repository /path/to/checkout` to check the final active
inputs against a checkout. Optimized Python is rejected.

`source-verification.json` checks the original 12 affected inputs against
canonical main cb2b37dfa2181ee042a090d8dbd434758a762afb and the unchanged Java
branch heads. Both official cross parents were independently rechecked as ZIP
data. The 26.1.2 vanilla parent/renderer remains unchecked; the full uploaded
mod JAR was not newly rehashed. The Forge47.3.0 source archive request returned
403 and was not retried; item-source support uses pinned maintained branches,
not a claim that exact loader archives were verified.

No Minecraft client, BDS, native renderer, held/item context, growth/gameplay,
saved-world, full-family or LIVE acceptance is claimed. Canonical PR/CI review
and any subsequent deployment are separate. See the current
[surface contract](../../WILD-VINE-SURFACE-CONTRACT.md) for ownership and tests.

## Frozen local candidate

The paired 0.6.214 candidate passed strict frozen identity/history checks and the
real canonical packager from a clean commit. Its 5,913,355-byte archive has
SHA-256 `db21cc94b0ec907863e9fd39ac6e8c1cb3e36d8dedd1fa079a523649df8bf551`.
See [frozen validation](frozen-validation.json) and [targeted local checks](local-validation.json).
No remote publication or full PR CI is claimed by this local receipt.
