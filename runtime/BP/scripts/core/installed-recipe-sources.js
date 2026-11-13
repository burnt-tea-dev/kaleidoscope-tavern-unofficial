// Supported providers declare no presence event before their recipe transfer.
// Native namespaces alone do not promise a provider, and some recipes contain
// only vanilla inputs. Probe one reviewed item definition per provider instead
// of scanning every item or guessing ownership from a saved barrel's contents.
const SOURCES=[
 ['kaleidoscope_world_liquor','kaleidoscope_world_liquor:absolut_vodka_q1'],
 ['kaleidoscope_orchard','kaleidoscope_orchard:strawberry_wine_q1'],
 ['kaleidoscope_sculk','kaleidoscope_sculk:honglan_wine_q1'],
 ['kaleidoscope_dim_wine','kaleidoscope_dim_wine:abyssal_porter_q1']
];
/** Bounded native lookups after world startup; no optional hard dependency. */
export function installedBarrelRecipeSources(itemExists){
 return SOURCES.filter(([,marker])=>itemExists(marker)).map(([source])=>source);
}
