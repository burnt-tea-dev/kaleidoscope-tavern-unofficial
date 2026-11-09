# T218: identical board textures and bounded seat maintenance

Base: [`e47978d1fc4d27048e20792f0c4368ce2f263a82`](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/commit/e47978d1fc4d27048e20792f0c4368ce2f263a82), checked against fresh main and open PRs #577/#621 on 2026-11-09. Those PRs do not own the font or seat implementation changed here.

## Concrete costs and repairs

| Source | Before | T218 |
| --- | --- | --- |
| `RP/entity/board_glyph_visual.entity.json` and `textures/board_font` | 256 distinct texture paths; 33 PNGs contain exactly the same fallback page | All 256 logical page keys remain; the 33 identical pages share `glyph_D8`, so 224 PNGs remain |
| Font atlas RGBA8 pixel accounting | 64 MiB | 56 MiB; 8 MiB less nominal pixel storage and 32,160 fewer PNG file bytes |
| `BP/scripts/bedrock/furniture.js::tickFurniture` | Copies all known seat handles every five ticks, then processes at most 128 | Uses the existing bounded storage iterator; enumerates/processes at most 128 handles, progressing after removals |
| Actual seat adapter with 8,192 retained handles | 8,192 registry yields per maintenance pass | 128 yields; the following pass visits the next 128, retiring invalid handles |

The pixel figures are width × height × four bytes per physical PNG. They are **not measured Minecraft RAM/VRAM savings**: native residency, compression, mipmaps, atlas padding and decoder peaks have not been measured. No FPS, TPS or watchdog improvement is claimed from Node counters.

`tools/build_board_font.py` owns the deduplication and binding updates. It compares full alpha-page bytes; RGB is uniformly white in every generated page. It keeps the first identical page and removes only that generator's superseded PNG path. It does not resize a texture or change a glyph. The complete 256-page routing was compared with the immutable base: each new resolved PNG is byte-identical to its old resolved PNG, including all RGBA pixels. The 65,536 advance metrics, page-array ordering, geometries, UVs, animations, tint, glowing outline and camera gates are unchanged. Running the generator again reproduced the same output bytes.

The seat change reuses `bedrock/storage-visual-maintenance.js`. Seat ownership, riders, eject conditions, yaw and five-tick cadence remain in their existing adapters. Its existing tests cover bounded iteration, deletion and newly spawned work; two added tests exercise the real seat entrypoint, its enumeration budget and maintenance of a live stool after invalid handles retire.

## Current contracts replace historical source projections

- `tools/current_extension_source_contract.py` now owns the actual furniture adapter as well as its existing core model. Startup, event and five-tick maintenance wiring stay checked; the actual adapter tests cover seating, transfer rollback, recovery, yaw and the 128-handle budget.
- `tools/board_font_contract.py` derives all RGBA pixels, 256 logical bindings and 65,536 metrics from the pinned GNU Unifont input. It rejects missing or extra atlases, returned duplicate files, wrong page/cell arrays and selectors, missing geometry bindings and material changes. The existing rendering generator still checks every UV, outline, tint and range gate.
- Only the furniture preimage, its T131/T156 reverse deltas and launch postimage, and the board entity's T134 reverse asset entry are retired. No new inverse delta or version-specific exception is added.
- The storage and motion texture aggregates hand exactly 256 font paths to the current contract. The remaining **1,754 historical texture files** keep aggregate `33c0ef8ef55b96e29efcba73fe3c4a951f087d6824a147dd7834070cd31cc9ae`. Adding the 256 original font hashes from the base commit reproduces the former 2,010-file aggregate `a85b798ece7151ec00f6a4d8af2569a4f2cbaf348b2d839fe3a4558d6358c144` exactly; unrelated textures were not reaccepted from changed bytes.
- Launch inventory separately requires all 224 physical atlases plus their entity and subtracts only the 32 source-derived retired aliases. Unrelated-file preservation, geometry budgets, manifests/dependencies, identity and append-only release history remain enabled.

## Verification

- `node --experimental-loader ./tools/foundation/mock-loader.mjs --test tools/furniture-interaction.test.mjs`: 17 passed.
- `node --experimental-loader ./tools/efficiency/mock-loader.mjs --test tools/efficiency/efficiency.test.mjs tools/efficiency/board-rendering.test.mjs`: 66 passed.
- Negative control: loading only the base `furniture.js` into the same 17-case test run gives 15 passes and both new regression failures, including `8192 !== 128`. The working source was not overwritten.
- `python3 tools/test_board_font_contract.py`: 9 passed, including negative mutations to mapping, each RGBA channel, glyph ink, missing/returned atlases, page/cell order, selectors, UVs, tint, outline offsets, metrics and source input; repeated generation is byte-identical.
- `python3 tools/build_board_rendering.py --check`: passed, including original material/UV/outline contracts.
- `node tools/check_board_layout.mjs`: passed the independent full-BMP advance/bold oracle and existing layout checks.
- `python3 tools/check_launch.py --baseline <cedfaedf6140bae61b24afb658869b1d0e6ea1a9 checkout>`: passed exact runtime inventory, with 2,986 unchanged existing runtime files checked. Storage, motion and client-asset checks also passed; no new Java checkout or native observation is claimed.
- Full logical-page byte comparison and repeat generation: passed. The short reproduction below needs the base Git object and Pillow for generation.
- Release identity, append-only history and archive checks are separate from these behavior/resource checks; T218 is a new paired identity with the same UUIDs and API dependencies.

```python
import json, subprocess
from pathlib import Path
base = 'e47978d1fc4d27048e20792f0c4368ce2f263a82'
def old(path):
    return subprocess.check_output(['git', 'show', base + ':' + path])
path = 'runtime/RP/entity/board_glyph_visual.entity.json'
before = json.loads(old(path))
after = json.loads(Path(path).read_bytes())
a = before['minecraft:client_entity']['description']['textures']
b = after['minecraft:client_entity']['description']['textures']
assert a.keys() == b.keys() and len(b) == 256
for key in a:
    assert old('runtime/RP/' + a[key] + '.png') == Path('runtime/RP/' + b[key] + '.png').read_bytes()
before['minecraft:client_entity']['description']['textures'] = b
assert before == after
assert len(set(b.values())) == 224
assert len(list(Path('runtime/RP/textures/board_font').glob('*.png'))) == 224
metrics = 'runtime/BP/scripts/data/board-font.js'
assert old(metrics) == Path(metrics).read_bytes()
```

## Remaining limits

Dense text still uses one native helper per visible glyph (`bedrock/board-text.js`); 300 displayed nonblank glyphs still mean 300 helpers. Full cellar cabinets still require up to nine bottle helpers. This patch reduces duplicate texture resources and script iteration; it does not solve native actor or draw-call density.

No Minecraft client, BDS, user's computer, saved-world deployment or LIVE instance was used. Low-memory-device peak RSS, native texture residency, frame time, rendering, save/reload and multiplayer acceptance remain unmeasured. World Liquor's manifest currently pins Tavern T205; this standalone candidate does not silently rebind that family dependency or publish a release.
