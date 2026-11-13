# Current API v1 extension compatibility

The host accepts current Sculk and Dimensions Wine registrations through the existing Script Event protocol. Packet limits are 1900 UTF-8 bytes, 1,500,000 payload bytes and 2048 parts; incomplete transfers expire after 2400 loaded ticks. Readiness advertises these same limits. ACK identities, atomic replacement and the existing sender scheduling remain the protocol contract. The public SDK sender retains its conservative 262144-byte/512-part bound; independently maintained senders must honor the advertised host limits.

`shakerInputs` describes at most 256 distinct registered input items. A physical shaker still has three ingredient slots; a barrel still has four. Namespaced `itemGroups` expand alternative ingredients for barrel and pressing recipes. `recipes[].when` checks `itemsAll`, `itemsAny` and `fluidsAll` before validating a conditionally available recipe.

Quality-block bottle descriptors may omit `displayStates`: their count uses `kaleidoscope_tavern:count`, and facing uses `minecraft:cardinal_direction`. Explicit mappings remain supported. The unqualified Creative item keeps its original item ID through display, storage and pickup while using the maximum-quality preview effects.

Fluid titles are optional. The shared guide resolves a missing title from the registered filled-container page, preserving its localized name rather than inventing another bucket suffix. Declared guide-category trees are validated within their source, then projected into the family's existing seven roots and child groups. This keeps both entrances within Cookery's 32-category limit without replacing either guide interface.

The shared `kaleidoscope_tavern:toggle_light` component accepts the boolean `kaleidoscope_tavern:lit` state used by current addon lights. It uses the existing decoration interaction route, retains held items and facing, preserves waterlogging, and suppresses duplicate before/after callbacks. Turning on requests `random.orb` at volume 0.45/pitch 1.45; turning off requests `random.pop` at volume 0.40/pitch 1.0.

## Applying a custom effect from an existing consumption component

Server scripts can send `kaleidoscope_tavern:effect_apply` with JSON fields
`entity` (entity ID), `effect` (effect ID), `duration` (seconds) and `amplifier`
(zero-based level). The existing receiver accepts `ScriptEventSource.Server`,
messages of at most 1024 characters, finite durations from 0 to 1000000 and
integer amplifiers from 0 to 255. Effects must be implemented by Tavern or
registered through the existing extension foundation. Unknown effects are
ignored. Timed effects need positive duration; their existing owner performs
the seconds-to-ticks conversion, stacking, expiry and persistence.

This route now accepts Tavern's own implemented effects, including
`kaleidoscope_tavern:slightly_tipsy`, without an external definition or addon
registration. It calls the same `applyCustomEffect` used by ordinary Tavern
drinks. There is no second countdown, saved property, or replacement buff.
It sends no ACK; sending a packet does not prove application or client visuals.
The component must dispatch only on actual consumption, leaving native item
settlement with its existing owner. Ordinary bottle drinks continue through
`completeDrink`; their extension/guide registration is a separate operation.

The Dimensions Wine source adapter uses this route from its actual pop-can
`onConsume`. Its existing quality-2 Fanta/Pepsi/Sprite `slightly_tipsy` data agrees
with [the maintained NeoForge Java table](https://github.com/WitherRedstone/Kaleidoscope-DimensionsWine/blob/6702d5f678b98c67b37d50408b8446641d492c6a/src/main/resources/data/kaleidoscope_dim_wine/datamap/drink_effect/fanta.json):
45 seconds, amplifier 0, probability 1. Java also declares `happy` at qualities
3–6. The clean Bedrock author omits those rows and has no implementation;
this connection does not claim to restore `happy` or Java's camera roll.

## Barrel quality boosters

`barrelQualityBoosters` supplies `item`, `boost`, `firstBoost`, `maxQuality`, `cooldownTicks`, `damage` and `consume`. The host advertises `barrel_quality_boosters`. The existing machine state and inventory transaction own the result: quality changes preserve the current fermentation countdown, and a failed save restores the original item and state without starting the cooldown.

Dimensions Wine's Mead Essence advances an already produced batch by one quality level, up to the host's six levels. Survival spends one of its ten durability uses; an exhausted essence remains the same original item and cannot be used again in either mode. Creative spends no durability when using an essence that still has durability. A successful use starts the 600-tick player/item cooldown. Custom names, lore and properties remain intact.

These decisions follow the maintained Java source: [Forge MeadEssence](https://github.com/WitherRedstone/Kaleidoscope-DimensionsWine/blob/cd5e040051cdb03b33834d7670807909c5e8d7cb/src/main/java/com/chinaex123/kaleidoscope_dim_wine/item/MeadEssence.java), [NeoForge MeadEssence](https://github.com/WitherRedstone/Kaleidoscope-DimensionsWine/blob/6702d5f678b98c67b37d50408b8446641d492c6a/src/main/java/com/chinaex123/kaleidoscope_dim_wine/item/MeadEssence.java). Java's `firstBoost` applies only at raw level zero; this host's produced batches start at level one. Java's host accessors and persistence clamp to six levels. The clean Bedrock author host instead applies the first boost at level one and deletes an item at maximum damage; this implementation follows Java for those observable behaviors.

## Yielding the optional effect bar to a one-shot message

Server scripts can ask Tavern's existing effect bar to pause for one player:

```js
import {system} from '@minecraft/server';

// Send at the actual message producer, immediately before its ActionBar write.
try {
 system.sendScriptEvent('kaleidoscope_tavern:actionbar_hold',
  JSON.stringify({player:player.id,ticks:60}));
} catch { /* A signalling failure must not suppress the original message. */ }
player.onScreenDisplay.setActionBar(message);
```

The JSON object requires `player`, an existing player entity ID, not a name or selector. `ticks` is optional (default 60); supplied values must be positive safe integers. Values above 100 are capped at 100. Zero, negative, fractional, string and null values are ignored, as are malformed/oversized packets and unknown, invalid or non-player IDs. Extra fields are ignored.

This event uses the existing extension-host boundary: only `ScriptEventSource.Server`, at most 1900 UTF-8 message bytes, and the existing shared limit of 256 accepted-source requests per server tick. Pack namespaces are cooperative identifiers, not authenticated pack identities. Do not send via a player's `runCommand`; use `system.sendScriptEvent`. No extension registration is needed and no ACK is sent, including for rejected requests. Sending is not confirmation of receipt or installation; the public API does not promise synchronous cross-pack dispatch before the following display write.

On receipt at server tick `t`, the existing hold becomes `max(previousHold, t + min(ticks, 100))`. Tavern skips effect-bar writes while the current tick is below that deadline, then resumes through its existing 20-tick update. A shorter hold cannot shorten a longer one. The event never clears or writes the ActionBar, changes tags, effects or saved data, or pauses other players. Existing block/item interaction holds remain 60 ticks. Leave/spawn and the existing absent-player cleanup discard the same in-memory hold.

This is a quiet window for cooperating one-shot producers, not ownership of every HUD writer. It does not pause Tavern's foreground shaker HUD or another addon's writers. For delayed messages, send from the actual display branch rather than when enqueueing. See [effect-bar behavior](EFFECT-BAR.md).

## Verification boundary

Focused tests call the real transport, registry, bottle display, decoration, machine, native inventory transaction and shared guide implementations through the repository's API fixture. Private replay uses the two clean author senders, exact custom item/block definitions, this host and the original Cookery 1.6.4 guide receiver. No complete third-party scripts are published here. API-fixture results do not establish native BDS behavior, client rendering, audible output or TPS; those remain separate family gates and human acceptance.

Dimensions Wine's Ranger's Satchel declares Java `minecraft:glowing` at qualities 3–6. The [official Bedrock stable effect list](https://learn.microsoft.com/en-gb/minecraft/creator/commands/commands/effect?view=minecraft-bedrock-stable) contains 37 effects and does not provide Glowing. The [stable EffectTypes API](https://learn.microsoft.com/en-us/minecraft/creator/scriptapi/minecraft/server/effecttypes?view=minecraft-bedrock-stable) documents that an absent ID returns `undefined`. This is the documented stable boundary; this round has no separate native-registry or rendering receipt.

The current consumer skips only that unsupported effect row. Actual clean payload replay through `completeDrink` at every affected quality verifies that Survival consumes exactly one bottle and returns exactly one empty Tavern bottle, including stacked drinks; supported effects still execute, and the remaining stack retains its metadata. Creative retains the drink and receives one empty bottle. The shared guide states the missing outline in all three supported languages. No effect is substituted, and the drink is not rejected as a whole.
