# Kaleidoscope Tavern (Unofficial)

A Bedrock port of Kaleidoscope Tavern, with brewing, cocktails, furniture, storage and the shared Tavern guide. [繁體中文](README.zh-TW.md).

## Install and current source

Download public packages from [Releases](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/releases). Enable both BP and RP and use the dependencies listed for that release. A Git main commit is development source; it does not establish which version is installed on a server.

[baseline.json](baseline.json) owns the current source version, pack identities and exact dependencies. [family/upstream.lock.json](family/upstream.lock.json) records reviewed family inputs. [CHANGELOG.md](CHANGELOG.md) describes changes; [the family status index](family/BASELINE-STATUS.md) separates published source and recorded acceptance. Do not infer a running deployment from an old README snapshot.

## Develop and verify

Read [AGENTS.md](AGENTS.md), [baseline maintenance](docs/BASELINE-MAINTENANCE.md) and the relevant [family update procedure](family/UPDATE-WORKFLOW.md). The builder packages committed runtime directly:

```sh
python3 tools/build_release.py
```

Use the existing targeted checks during development; canonical CI runs the required suite. [PARITY-MATRIX](docs/PARITY-MATRIX.md) and [BUGS](docs/BUGS.md) retain implemented behavior, known differences and player reports. Engine loading and source checks do not establish rendered gameplay, audio or client acceptance. Private integration remains a separate private addon.

## License and history

Original code is BSD-3-Clause; original and derived art is CC BY-NC-SA4.0. See [CREDITS](CREDITS.md), LICENSE-CODE and LICENSE-ASSETS. Earlier README release snapshots remain in [Git history](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/blob/bb9e7cfb32b642ccfa563a1d3aca2abc9e744453/README.md).
