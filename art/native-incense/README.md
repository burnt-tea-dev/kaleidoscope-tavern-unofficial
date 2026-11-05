# Selected native incense actors

These are Mojang's selected native entity sources, kept under their original
[license](LICENSE.md). They are not covered by the port's code or asset license.

Source: [Mojang/bedrock-samples v1.26.60.5](https://github.com/Mojang/bedrock-samples/tree/v1.26.60.5/behavior_pack/entities), released 2026-10-28.
On 2026-11-06 both parsed documents were compared with BDS 1.26.60.6:

| Source | Official blob | Matching last installed definition |
| --- | --- | --- |
| zombie_villager.json | 346f37f38f8a17bec004564ed043cf4b14126d61 | vanilla_1.20.80/entities/zombie_villager.json |
| zombie_villager_v2.json | 126ec4ad8bce69c14796adf85b492dc5425321e8 | vanilla_1.26.20/entities/zombie_villager_v2.json |

Run `python tools/build_incense_native_entities.py` after changing the selected
sources or the owned addition. It generates both complete BP definitions and the
packaged notice. Bedrock selects a whole entity definition; another file cannot
append a component group to these identifiers. Tavern therefore owns these two
definitions and must review selected native changes when adopting a new engine.

The generator preserves every original field, including ordinary golden-apple
conversion. It only adds the `kaleidoscope_tavern:incense_to_villager` group and
`kaleidoscope_tavern:incense_cure` event. The group uses the native transformation
with a three-second countdown and the existing bed/iron-bar acceleration settings;
the event removes the old conversion group before adding the owned group so a
new incense request can reset the countdown. No actor is manually replaced.

Runtime/native evidence and remaining parity limits belong to
[the current incense section](../../docs/PARITY-MATRIX.md#香薰先傷害再判斷治療2026-11-05).
