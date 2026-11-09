# Incense source surfaces

The two canonical models, `runtime/RP/models/entity/incense_closed.geo.json` and
`incense_open.geo.json`, own the pot geometry for all eight incense types. Each
block uses the closed model by default, the open model when its open state is 1,
and the closed model for native item visuals. No separate incense pot entity or
attachable owns another copy of these meshes. The incense emitter and native
conversion-entity generators do not generate these pot models.

## Source contract

The checked-in `data/incense-surfaces/java-{closed,open}.json` models retain the
Forge author elements at `c4ec1880bd44cf3139d3ba744ab30bb379cf1416`; their
source paths and hashes are in `data/incense-surfaces/source.json`. All sixteen
colour/state model element lists match those two fixtures. The corresponding
NeoForge `a1afba34981a00e89d57130d3dc8f1e64f1820a2` resources and pinned release
JAR also retain the same fill bottom. There is no model `cullface` instruction
or custom incense renderer that removes it. Author block registration uses
`noOcclusion`, without a support-survival condition that requires a solid floor.

The fill element has a downward face at model Y=1. The base texture's central
4×4 pixels are transparent, while the fill face's 4×4 pixels are opaque. Removing
the fill bottom changes the first opaque underside from the fill at Y=1 to the
lid at Y=4. This is not an invisible duplicate face. Restore only its source UV:
`uv: [20, 16]`, `uv_size: [-4, -4]`; the open model also keeps the source fill's
existing `unshaded` material. No texture, top face, model placement, material
sidedness, held transform, particle, behavior, API, or pack UUID changes are
needed.

`tools/check_incense_surfaces.py` checks the current source faces, UVs, shade,
cutout rescale and opposing planes, every block/item material and geometry route,
effective closed/open lifecycle components, and transparent-contact masks.
Matching permutations replace whole components; both inherited and overridden
values are checked. Geometry routes must retain the visible shared root in both
placed states and their item visuals, without visibility overrides.
It casts 256 point-sampled upward rays across all
sixteen type/state combinations, comparing source/native first-hit depth and
RGBA. The two geometrical contacts have opposing normals; single-sided material
culling must remain enabled. Existing lid/frame alpha checks remain active.
`tools/test_incense_surfaces.py` rejects missing faces, wrong UVs/depth, changed
top faces, hidden/transparent fill, double-sided foliage, disconnected item/open
routes, and reintroduced historical projection layers.
It also rejects open-state lifecycle changes and hidden geometry roots, including
through the actual launch-check entry point with and without source inputs.
Identical explicit overrides remain valid; partial component replacements do not
inherit omitted nested fields.

The active T158/T159 inverse geometry/block projections and original launch hash
entries are retired for this exact domain. Current resources use the contract
above, not a new inverse delta or a runtime-hash exemption. The motion aggregate
keeps its original total and archived per-file source digests while separately
checking the remaining historical blocks. Historical release notes and Git
commits are unchanged. Frozen release identity, UUID/dependency checks and
append-only release history remain separate.

These tests establish static resource and alpha-surface agreement, not native
Minecraft lighting, filtering, client rendering, gameplay or saved-world
acceptance. A source candidate must receive its paired version and normal
freeze/CI/package checks before it can be released; an unfrozen edit must fail
strict identity/build checks under the previously frozen version.
