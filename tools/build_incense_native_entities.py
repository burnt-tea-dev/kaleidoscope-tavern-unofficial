#!/usr/bin/env python3
"""Preserve the selected native actors and add the Java incense cure countdown."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from family_bundle import read_definition

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'art/native-incense'
GROUP = 'kaleidoscope_tavern:incense_to_villager'
EVENT = 'kaleidoscope_tavern:incense_cure'
NAMES = ('zombie_villager', 'zombie_villager_v2')


def configure(original):
    result = deepcopy(original)
    entity = result['minecraft:entity']
    group = deepcopy(entity['component_groups']['to_villager'])
    delay = group['minecraft:transformation']['delay']
    delay['value'] = 3
    delay.pop('range_min', None)
    delay.pop('range_max', None)
    entity['component_groups'][GROUP] = group
    # Removing before adding restarts an existing native conversion, matching
    # Java startConverting(null, 60). Normal golden-apple events stay intact.
    entity['events'][EVENT] = {'sequence': [
        {'remove': {'component_groups': ['to_villager', GROUP]}},
        {'add': {'component_groups': [GROUP]}},
    ]}
    return result


def outputs(root=ROOT):
    source = root / 'art/native-incense'
    result = {}
    for name in NAMES:
        original = read_definition(source / (name + '.json'), jsonc=True)
        result[root / 'runtime/BP/entities' / (name + '.json')] = (
            json.dumps(configure(original), ensure_ascii=False, indent=2) + '\n')
    result[root / 'runtime/BP/NOTICE-Mojang-native-incense.txt'] = (
        'entities/zombie_villager.json and entities/zombie_villager_v2.json preserve\n'
        'Mojang/bedrock-samples v1.26.60.5 native definitions with the owned\n'
        'kaleidoscope_tavern:incense_to_villager group and incense_cure event added.\n'
        'Source and additions: art/native-incense/README.md and\n'
        'tools/build_incense_native_entities.py in the matching source repository.\n\n'
        + (source / 'LICENSE.md').read_text())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for path, text in outputs().items():
        if args.check:
            if not path.exists() or path.read_text() != text:
                raise SystemExit('Native incense output differs: ' + str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
    print('Native incense definitions ' + ('match reviewed sources' if args.check else 'generated'))


if __name__ == '__main__':
    main()
