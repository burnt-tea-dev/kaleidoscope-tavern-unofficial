"""Validate six additive freezer uppers without carrying private author assets."""
import copy
import json

NAMESPACE = 'kaleidoscope_chinesefood:'
LOWERS = ('freezer', 'freezer_green', 'freezer_light_blue', 'freezer_orange',
          'freezer_pink', 'freezer_yellow')
COPIES = {'host-assets/chinesefood/' + lower + '_upper.json':
          'blocks/kitchen/' + lower + '_upper.json' for lower in LOWERS}
LOWER_TITLE = 'senluo.freezer.lower'
UPPER_TITLE = 'senluo.freezer.upper'


def validate_upper_copies(spec, owned_root, changed, profile):
    """Only exact derived definitions may extend the reviewed original six ids.

    The profile has already bound the source archive, declaration and every
    copy digest. Compare complete definitions as well: a refreshed digest must
    never authorize unrelated geometry, recipe or creative-menu changes.
    """
    block_copies = {source: target for source, target in spec['copies'].items()
                    if target.startswith('blocks/')}
    if not block_copies:
        return set()
    if (not profile or spec.get('id') != 'senluo:chinesefood-native-freezer-storage'
            or block_copies != COPIES):
        raise ValueError('Native freezer copies require the exact six reviewed uppers')
    for lower in LOWERS:
        original = 'blocks/kitchen/' + lower + '.json'
        if original not in changed:
            raise ValueError('Native freezer upper lacks its reviewed lower definition')
        expected = copy.deepcopy(json.loads(changed[original]))
        block = expected['minecraft:block']
        if block['description']['identifier'] != NAMESPACE + lower:
            raise ValueError('Native freezer lower identity differs')
        block['description']['identifier'] += '_upper'
        block['description']['states'][NAMESPACE + 'top'] = [True, False]
        container = {'slot_count': 36}
        lower_container = block['components']['minecraft:block_entity']['container']
        if 'title' in lower_container:
            if lower_container['title'] != LOWER_TITLE:
                raise ValueError('Native freezer lower container title differs')
            container['title'] = UPPER_TITLE
        block['components']['minecraft:block_entity'] = {'container': container}
        block['components']['minecraft:loot'] = 'loot_tables/senluo_native/freezer_empty.json'
        for permutation in block.get('permutations', []):
            permutation.get('components', {}).pop('minecraft:block_entity', None)
        path = owned_root / ('host-assets/chinesefood/' + lower + '_upper.json')
        if (path.is_symlink() or not path.resolve().is_relative_to(owned_root.resolve())
                or not path.is_file() or json.loads(path.read_bytes()) != expected):
            raise ValueError('Native freezer upper differs from its original author definition: ' + lower)
    return set(block_copies.values())
