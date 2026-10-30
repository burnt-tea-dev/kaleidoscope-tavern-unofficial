"""Current extension owners and their shared runtime connections.

Behavior is exercised by the existing extension, bottle, furniture and guide
suites. Java resource checks remain in the package suite. This static boundary
neither reverses current source nor certifies native or rendered gameplay.
"""
import json
from pathlib import Path

from foundation.source_contract import imported, read_module
from check_localization import check as check_localization, parse_lang, tokens
from build_locale_aliases import PARTIAL_LOCALES

ROOT = Path(__file__).resolve().parents[1]
SOURCE_GROUPS = {
    'registrationAndTransport': ('bedrock/extension-host.js', 'core/registry.js', 'core/transport.js', 'core/extension-foundation.js'),
    'bottleIdentity': ('core/extension-content.js', 'core/bottle-display-schema.js'),
    'furnitureLifecycle': ('core/furniture.js',),
    'optionalEffectProtocol': ('data/effect-icons.js',),
    'machinesAndDecorations': ('bedrock/machines.js', 'core/machines.js', 'bedrock/decorations.js'),
    'sharedGuide': ('core/cookery-guide-publisher.js', 'data/cookery-guide-payload.js', 'data/guide-navigation.js', 'data/guide-copy.js'),
}
COMPLETE_LOCALE_SOURCES = frozenset('runtime/RP/texts/' + locale + '.lang' for locale in ('en_US', 'zh_CN', 'zh_TW'))
PARTIAL_LOCALE_SOURCES = frozenset('runtime/RP/texts/' + locale + '.lang' for locale in PARTIAL_LOCALES)
LOCALE_SOURCES = COMPLETE_LOCALE_SOURCES | PARTIAL_LOCALE_SOURCES
QUALITY_UP_KEY = 'kaleidoscope_tavern.message.barrel_quality_up'
LAMP_RECIPE = 'runtime/BP/recipes/blue_pendant_lamp_from_dye.json'


def runtime_sources():
    return frozenset('runtime/BP/scripts/' + name for group in SOURCE_GROUPS.values() for name in group) | LOCALE_SOURCES | {LAMP_RECIPE}


def check(root=ROOT, *, syntax=True, localization=True):
    root = Path(root)
    modules = {name: read_module(root, 'runtime/BP/scripts/' + name, syntax)
               for group in SOURCE_GROUPS.values() for name in group}
    entrypoint = read_module(root, 'runtime/BP/scripts/main.js', False)
    for module, names in (
        ('./core/registry.js', {'ExtensionRegistry'}),
        ('./bedrock/extension-host.js', {'installExtensionHost'}),
        ('./bedrock/machines.js', {'setRegistry', 'registerMachineComponents', 'installMachineEvents'}),
        ('./bedrock/decorations.js', {'registerDecorationComponents', 'installDecorationEvents'}),
        ('./data/cookery-guide-payload.js', {'buildCookeryGuidePayload', 'prepareCookeryGuidePayload'}),
        ('./core/cookery-guide-publisher.js', {'installCookeryGuidePublisher'}),
    ):
        imported(entrypoint, module, names)
    assert entrypoint.count('installExtensionHost(registry)') == 1, 'Current extension host is disconnected'
    assert entrypoint.count('setRegistry(registry)') == 1, 'Current machine registry is disconnected'
    assert '()=>prepareCookeryGuidePayload(registry)' in entrypoint, 'Shared guide publisher is disconnected'
    assert 'installCookeryGuidePublisher(system,()=>prepareCookeryGuidePayload(registry))' in entrypoint, 'Cookery guide publisher is disconnected'

    imported(modules['bedrock/extension-host.js'], '../core/transport.js', {'ExtensionTransport', 'EVENTS', 'TRANSPORT_LIMITS'})
    imported(modules['bedrock/extension-host.js'], '../core/registry.js', {'CAPABILITIES'})
    imported(modules['core/registry.js'], './extension-content.js', {'installContent'})
    imported(modules['core/furniture.js'], './extension-content.js', {'externalFurnitureDefinition'})
    recipe=json.loads((root/LAMP_RECIPE).read_text())['minecraft:recipe_shaped']
    assert recipe['pattern']==[' L ','LGL',' L ']
    assert recipe['key']=={'L':{'item':'kaleidoscope_tavern:yellow_pendant_lamp'},'G':{'item':'minecraft:blue_dye'}}
    assert recipe['result']=={'item':'kaleidoscope_tavern:blue_pendant_lamp','count':4}
    imported(modules['core/bottle-display-schema.js'], './extension-content.js', {'bottleBase', 'bottleBlock'})
    imported(modules['bedrock/machines.js'], '../core/machines.js', {'interact', 'advanceBarrel'})
    imported(modules['bedrock/machines.js'], '../core/bottle-display-schema.js', {'bottlePermutationBlock', 'bottlePermutationStates'})
    imported(modules['bedrock/decorations.js'], './java-placement-router.js', {'registerJavaBlockUseHandler', 'settleJavaBlockUse'})
    imported(modules['bedrock/decorations.js'], './waterlogging.js', {'setWithWater'})
    imported(modules['data/cookery-guide-payload.js'], './guide-navigation.js', {'extensionGuideCategory'})
    imported(modules['data/cookery-guide-payload.js'], './guide-catalog.js', {'prepareConsolidateGuide'})
    imported(read_module(root, 'runtime/BP/scripts/data/guide-catalog.js', False), './guide-copy.js', {'applyReviewedAddonGuideCopy'})
    imported(read_module(root, 'runtime/BP/scripts/core/bottles.js', False), './extension-content.js', {'externalDrink'})
    imported(read_module(root, 'runtime/BP/scripts/bedrock/bottles.js', False), '../core/bottle-display-schema.js',
             {'bottlePermutationBlock', 'bottlePermutationStates', 'legacyBottleDisplay'})

    languages = {name: parse_lang((root / name).read_text(), name) for name in LOCALE_SOURCES}
    for name in COMPLETE_LOCALE_SOURCES:
        assert QUALITY_UP_KEY in languages[name], ('Missing current quality feedback key', name)
    # Partial Java translations retain the existing English fallback. When an
    # override is present, it must preserve the same placeholder contract.
    for name, labels in languages.items():
        if QUALITY_UP_KEY in labels:
            assert tokens(labels[QUALITY_UP_KEY]) == tokens(languages['runtime/RP/texts/en_US.lang'][QUALITY_UP_KEY]), ('Quality feedback placeholders differ', name)
    localization_result = check_localization(root) if localization else 'not run'

    sources = runtime_sources()
    ledger = json.loads((root / 'data/baseline-reconciliation.json').read_text())
    for section in ('files', 'reviewedFunctionalDeltas'):
        assert not sources & set(ledger.get(section, {})), 'Current extension owner returned to a historical postimage'
    for section in ('reviewedFunctionalDeltaLayers', 'reviewedAssetDeltaLayers'):
        for layer in ledger.get(section, []):
            assert not sources & set(layer['files']), 'Current extension owner returned to a reverse delta'
    reference = json.loads((root / 'data/launch-repair-reference.json').read_text())
    for section in ('reviewedChanges', 'newRuntimeFiles'):
        assert not sources & set(reference[section]), 'Current extension owner returned to the launch hash aggregate'
    return {
        'sources': sorted(sources), 'ownershipAndWiring': 'passed',
        'syntax': 'passed' if syntax else 'not run',
        'localization': localization_result,
        'behavior': 'existing current-extension-contract, transport-integrity, extension-bottle, furniture-interaction and standalone-guide suites; not run by this static check',
        'javaResources': 'existing incense surfaces/sampling, barrel materials/collision and guide checks in the package suite; not run by this static check',
        'bds': False, 'client': False,
    }


if __name__ == '__main__':
    print(json.dumps(check()))
