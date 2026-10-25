# Placed native potion liquid

The original potion bottle model marks only element 1's six liquid faces with
`tintindex: 0`. Both reviewed Forge `c4ec1880` and NeoForge `a1afba34` authors
register `PotionBottleColor`; it reads the bottle's saved potion stack. The
previous Bedrock block always used the untinted original PNG, so Healing and
Poison retained different native items but rendered through identical assets.

The current adapter keeps the original seven untinted glass cubes in the block
and supplies the liquid through one cosmetic entity type. `core/potions.js`
owns default-potion colour semantics, using the common `core/effect-colors.js`
constants also consumed by the existing aura adapter. The recipe whitelist is
unchanged. The source-texel geometry utility is shared with signature cups;
signature outputs remain byte-identical. Original liquid alpha holes, three
source shades and PBR roughness 200 are retained. Every potion uses the same
three geometries and opaque white texture, with three synced RGB properties.

The combined geometry check validates this current resource contract before
accounting for its four shared meshes. Glass uses seven cubes; each liquid
shade uses at most 21 single-face rectangles (504 allocated vertices). The
existing base-model budget remains below 1,024. This is a project budget,
not a claimed engine-wide geometry-ID limit or rendered-client evidence.

The saved native ItemStack remains the only adopted item authority. Colour
reads and Creative picks use the same strict read-only native source as removal.
Missing adopted carriers remove the cosmetic liquid at the block tick and never
reconstruct a replacement item. Creative
pick remains read-only; take, natural break and projectile break use existing
transaction completion for cosmetic cleanup. The helper has no inventory.
Block ticks validate colour and restore missing helpers. Entity-load and bounded
maintenance check owner liveness and pose, invoking full repair only for drift;
healthy helpers avoid another native inventory read. Full repair collapses
duplicates and unloaded owner cells defer cleanup. Cosmetic spawn failure
does not undo a committed item placement.

Vanilla bottle placement uses the existing Java direction adapter to face opposite
the player. Forge `VanillaBottlePlaceEvent.getPlacement` maps WATER/EMPTY to the
ordinary water block without storing the input stack; NeoForge does the same for
water or missing potion contents. Their water loot creates canonical water. That
stateless water behavior, accepted inputs, quantities and models remain unchanged.

`tools/potion-bottle-visual.test.mjs` exercises the production callbacks with the
existing API double. Its expected colours come from original Minecraft 1.21.1
JVM execution, not a second copy of the adapter formula. It covers all 46 Java
registry defaults and the 47 native IDs recorded in the historical T0.6.48
probe, including exact stack metadata, stale JSON, unavailable storage,
future unmapped IDs, cleanup and cosmetic failures. `potionCapabilities()`
reports current mapped and unmapped display IDs when a native probe runs;
the old 47-ID fixture is not proof of today's engine registry.

`tools/check_potion_bottle_visual.py --java-source PATH` verifies the original
Java model, tint faces, texture bytes, coordinate/UV conversion, generated
resources and glass/PBR separation. `check_launch.py` invokes this current
contract. The affected potion scripts/block and entrypoint have retired from
the old inverse baseline/pickup checks; their behavior is checked by the
current potion, aura, pickup and entrypoint suites. Unrelated domains and
release identity, history and saved-world protections retain their guards.

Scope: default native potion colours follow the NeoForge 1.21.1 integer
`PotionContents` policy. Forge 1.20.1 uses float accumulation and can differ in
low channel values; this does not claim bit-identical colour across both
branches. Existing aura float behavior is unchanged. `long_mundane` aliases
Java's no-effect `mundane`. Bedrock Wither uses the original Java Wither effect
colour, an explicit Bedrock-only adaptation because Java has no Wither potion.
Unknown native IDs preserve placement/pickup and show untinted white liquid.
Arbitrary foreign custom colours/effect visibility are not exposed by the
Bedrock potion identity API and are not claimed restored.

The [original native-persistence job](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/actions/runs/40012443439/job/120616254143)
passed on BDS 1.26.52.3 with zero players: 24 first-load and 27 same-world restart
cases. The actual registry returned 47 mapped potion IDs and no unmapped IDs.
Healing and Poison used native ItemStacks with metadata, deliberately conflicting
JSON, independent cosmetic RGB helpers, read-only pick and exact removal/cleanup.
The original logs and source identities remain unchanged when later CI verifies
identical execution inputs. This is script/property and synthetic-world evidence;
rendered colours, real Player interaction, the full family and an existing
private saved-world migration remain pending.

## Reproduce the independent numeric oracle

`tools/fixtures/PotionColorOracle.java` is our own harness. It extracts 26
original methods from the official Minecraft 1.21.1 client JAR; its type-remap
round-trip checks preserve the original instruction traces. Registry/Holder,
the MobEffect colour getter and unused feature/blend types are narrow fixtures.
The full Potions initializer supplies the 46 registrations; the MobEffects
initializer supplies 39 constants. No game JAR is included in this repository.

Use the original JAR SHA256 and class hashes in
`data/java-parity/potion-colors.json`, Gson 2.10.1 and Guava 32.1.2-jre
(with failureaccess 1.0.1). Put those dependency JARs in `POTION_LIBS`; use a
separate output directory. The command emits numeric rows and original-method
trace checks, not BDS/client evidence:

```bash
POTION_ORACLE_OUT=/tmp/potion-color-oracle
POTION_LIBS=/path/to/dependency-jars
POTION_CLIENT_JAR=/path/to/minecraft-1.21.1-client.jar
POTION_EXPORTS=(
  --add-exports java.base/jdk.internal.org.objectweb.asm=ALL-UNNAMED
  --add-exports java.base/jdk.internal.org.objectweb.asm.tree=ALL-UNNAMED
  --add-exports java.base/jdk.internal.org.objectweb.asm.commons=ALL-UNNAMED
  --add-exports java.base/jdk.internal.org.objectweb.asm.util=ALL-UNNAMED
)
javac "${POTION_EXPORTS[@]}" -cp "$POTION_LIBS/gson-2.10.1.jar" \
  -d "$POTION_ORACLE_OUT" tools/fixtures/PotionColorOracle.java
java -Xmx128m "${POTION_EXPORTS[@]}" -cp "$POTION_ORACLE_OUT:$POTION_LIBS/*" \
  org.senluo.oracle.PotionColorOracle "$POTION_CLIENT_JAR" "$POTION_ORACLE_OUT"
```
