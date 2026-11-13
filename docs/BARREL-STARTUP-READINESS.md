# Preserve loaded barrels until installed recipes register

An existing full, closed, unbatched barrel can tick before an installed extension
finishes registering. With water, four wheat and four wheat seeds, the old
transition selects sixteen vinegar bottles; once World Liquor registers, those
inputs correctly produce four Absolut Vodka bottles. The same failure reproduces
with the clean Orchard, Sculk and Dimensions Wine recipe payloads. These are
source counterexamples, not evidence that a player's live barrel was damaged.

At native startup, Tavern probes one native definition for each supported recipe
provider through one declarative table:

| Recipe source | Installed item marker |
| --- | --- |
| `kaleidoscope_world_liquor` | `kaleidoscope_world_liquor:absolut_vodka_q1` |
| `kaleidoscope_orchard` | `kaleidoscope_orchard:strawberry_wine_q1` |
| `kaleidoscope_sculk` | `kaleidoscope_sculk:honglan_wine_q1` |
| `kaleidoscope_dim_wine` | `kaleidoscope_dim_wine:abyssal_porter_q1` |

New fermentation without a matching Tavern builtin waits for every detected
provider's successful recipe-cache rebuild. This preserves the same state
object, ingredient projection and native inventory. World Liquor completing its
own registration cannot release a pending author's barrier. No timeout turns
valid inputs into vinegar. Existing batches continue with their saved recipe,
output and 97 loaded tick cadence; completed batches remain extractable. Once
registration succeeds, the next ordinary check starts fermentation. Removing a
source restores the wait for new batches. Absent markers preserve standalone
vinegar behavior.

This preserves the Java assumption that recipe matching sees the installed
recipe set before committing ingredients. It adds no world scan, transport
protocol change, hard dependency or offline fermentation. A broken installed
provider intentionally leaves these new barrels waiting;
`pendingBarrelRecipeSources` in the existing diagnostics identifies the source.
Tavern builtin matches keep working because they always precede extensions.

This is a supported-provider contract, not arbitrary provider discovery. Before
an extension sends its first packet, the host registry has no source declaration
to inspect. A native namespace alone does not promise a recipe sender, and
Dimensions Wine's Beeswax Honey Wine uses only vanilla water, honeycomb and honey
bottles. Inferring ownership from barrel inputs would miss that recipe; waiting
for every installed namespace would block unrelated packs. The four bounded
probes share the existing readiness mechanism without author-specific timers.

`tools/barrel-recipe-readiness.test.mjs` covers the actual recipe fields,
late and rejected registration, unrelated sources, host reload, removal and
re-registration, permanently pending providers, saved batch continuation and
extraction, absent optional packs and genuine vinegar fallback. Minimal author
recipe fields come from Orchard CF9227353, Sculk CF9317015 and Dimensions Wine
CF9317013; complete author scripts remain outside the public repository. Native
saved-world loading and real client interaction remain separate acceptance
evidence.
