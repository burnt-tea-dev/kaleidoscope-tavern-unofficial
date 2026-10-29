# Kaleidoscope Tavern — Unofficial Bedrock Port

Brewing, cocktails and a place to enjoy them. This addon brings [Kaleidoscope Tavern](https://github.com/KaleidoscopeMods/KaleidoscopeTavern) to Minecraft Bedrock Edition.

[繁體中文](README.zh-TW.md) · [Download](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/releases) · [Changelog](CHANGELOG.md)

## Features

- Grow brewing ingredients, ferment drinks and mix cocktails.
- Furnish a tavern with bottles, cabinets, seating and customizable boards.
- Discover recipes and equipment through the in-game Tavern guide.
- Extend the collection with World Liquor; optionally integrate the guide with Cookery.

This is an independent, unfinished port, not an official release. Some effects and interactions differ from Java, and client visuals/audio are not fully verified. See the [parity matrix](docs/PARITY-MATRIX.md) for specific limitations.

## Installation

1. Back up your world and download the `.mcaddon` from **Releases**, not GitHub's source-code ZIP.
2. Import it into Minecraft Bedrock and activate both its behavior pack (BP) and resource pack (RP).
3. Use the Minecraft version and any experiment settings required by that release. If adding World Liquor, install its exact matching Tavern version.

Tavern has its own guide and does **not** require Cookery. Optional companion packs are installed separately; this download does not include them or the private server integration. Use the in-game guide for recipes and machine instructions.

## Languages

Item names and other resource text follow the Minecraft client language. Guide language selection is handled by the guide itself; these are separate settings. Translation coverage and remaining untranslated text are being reviewed.

## Development

Requirements: Python 3 and Node.js. The maintained packs are in [`runtime/BP`](runtime/BP/) and [`runtime/RP`](runtime/RP/).

From a clean, committed checkout:

```sh
python3 tools/check_release.py
python3 tools/build_release.py
```

Packages are written to `dist/`. Source versions and exact dependencies live in [`baseline.json`](baseline.json); development source can be newer than the downloadable release. For changes, start with [AGENTS.md](AGENTS.md) and [baseline maintenance](docs/BASELINE-MAINTENANCE.md). Use the existing checks for the affected feature.

## Reporting issues

Include the addon and Minecraft versions, companion packs, enabled experiments, reproduction steps and expected result. Screenshots or a short recording help with visual and audio issues. Check [known issues](docs/BUGS.md) first; do not post private worlds, credentials or third-party archives.

## Credits and license

Original project: **Kaleidoscope Official Production Team / YSBB**. Bedrock adaptation: **casama233 and contributors**. No affiliation or endorsement is implied.

Code: [BSD-3-Clause](LICENSE-CODE). Original and derived artwork: [CC BY-NC-SA 4.0](LICENSE-ASSETS). Other assets retain their own terms; see [credits](CREDITS.md).
