#!/usr/bin/env python3
"""Project owner-reviewed Java tab sequences into native creative groups.

Each addon supplies its own ordered source plan. This converter owns no family
taxonomy and never infers membership from an item name, tag or component.
"""
import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
CATALOG = Path('runtime/BP/item_catalog/crafting_item_catalog.json')
PLAN = Path('data/java-creative-tabs.json')
BEGIN = '## BEGIN shared creative decoration groups'
END = '## END shared creative decoration groups'
LOCALES = ('en_US', 'zh_CN', 'zh_TW')
JAVA_TABS = Path('src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/init/ModCreativeTabs.java')


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def entries(catalog):
    found = {}
    for category in catalog['minecraft:crafting_items_catalog']['categories']:
        for group in category['groups']:
            name = group.get('group_identifier', {}).get('name')
            for item in group['items']:
                if not isinstance(item, str) or item in found:
                    raise ValueError(f'Duplicate/invalid catalog entry: {item}')
                found[item] = (category['category_name'], name)
    return found


def definitions(root):
    found = {}
    for folder, kind in (('items', 'minecraft:item'), ('blocks', 'minecraft:block')):
        for path in sorted((root / 'runtime/BP' / folder).rglob('*.json')):
            value = load(path)
            desc = value[kind]['description']
            found.setdefault(desc['identifier'], []).append((path, value, kind))
    return found


def localize(original, labels):
    if BEGIN in original or END in original:
        if original.count(BEGIN) != 1 or original.count(END) != 1:
            raise ValueError('Invalid generated language markers')
        before, rest = original.split(BEGIN, 1)
        _, after = rest.split(END, 1)
        original = before + after.lstrip('\r\n')
    existing = {line.split('=', 1)[0] for line in original.splitlines()
                if '=' in line and not line.startswith('##')}
    if existing.intersection(labels):
        raise ValueError('Duplicate shared creative group translation')
    section = BEGIN + '\n' + ''.join(f'{key}={value}\n' for key, value in labels.items()) + END + '\n'
    # Put this before other generated sections. build_effect_names.py owns its tail.
    return section + original


def planned(root):
    """Generate catalog/menu metadata from this owner's ordered Java rows."""
    root = Path(root).resolve()
    plan = load(root / PLAN)
    defs = definitions(root)
    visible_categories = {'construction', 'equipment', 'items', 'nature'}
    reviewed = set()
    for tab in plan['tabs']:
        if tab['category'] not in visible_categories:
            raise ValueError('Invalid creative category: ' + tab['category'])
        for entry in tab['entries']:
            item = entry.get('bedrock')
            if entry.get('unavailable'):
                continue
            if not item:
                raise ValueError('No Bedrock representative for Java entry: ' + entry['java'])
            if item in reviewed:
                raise ValueError('Duplicate plan entry: ' + item)
            reviewed.add(item)
    for entry in plan.get('bedrock_additions', []):
        if entry['category'] not in visible_categories:
            raise ValueError('Invalid creative category: ' + entry['category'])
        item = entry['bedrock']
        if item in reviewed:
            raise ValueError('Duplicate plan entry: ' + item)
        reviewed.add(item)
    catalog_members = entries(load(root / CATALOG))
    visible = {item for item, rows in defs.items() if any(
        value[kind]['description'].get('menu_category', {}).get('category') in visible_categories
        for _, value, kind in rows)}
    unknown = (set(catalog_members) | visible) - reviewed
    if unknown:
        raise ValueError('Visible items missing from the reviewed plan: ' + ', '.join(sorted(unknown)))
    missing = reviewed - visible
    if missing:
        raise ValueError('No visible definition for planned items: ' + ', '.join(sorted(missing)))
    output, displayed, groups = {}, set(), []
    for tab in plan['tabs']:
        members = []
        for entry in tab['entries']:
            item = entry.get('bedrock')
            if not item or entry.get('unavailable'):
                continue
            rows = [row for row in defs.get(item, [])
                    if row[1][row[2]]['description'].get('menu_category', {}).get('category')
                    in ('construction', 'equipment', 'items', 'nature')]
            displayed.add(item)
            members.append(item)
            for path, value, kind in rows:
                menu = value[kind]['description']['menu_category']
                desired = {**menu, 'category': tab['category']}
                if tuple(map(int, value['format_version'].split('.'))) >= (1, 21, 60):
                    desired['group'] = tab['group']
                else:
                    desired.pop('group', None)
                value[kind]['description']['menu_category'] = desired
                output[path] = encoded(value)
        if members:
            groups.append({'category_name': tab['category'], 'groups': [{
                'group_identifier': {'name': tab['group'], 'icon': tab['icon']},
                'items': members}]})
    # The explicit additions list is owner data, not an inferred semantic tail.
    loose = {}
    for entry in plan.get('bedrock_additions', []):
        item = entry['bedrock']
        for path, value, kind in defs.get(item, []):
            menu = value[kind]['description'].get('menu_category', {})
            if menu.get('category') not in ('construction', 'equipment', 'items', 'nature'):
                continue
            value[kind]['description']['menu_category'] = {
                **{key: val for key, val in menu.items() if key != 'group'},
                'category': entry['category']}
            output[path] = encoded(value)
            if item not in displayed:
                loose.setdefault(entry['category'], []).append(item)
                displayed.add(item)
    for category, members in loose.items():
        groups.append({'category_name': category, 'groups': [{'items': members}]})
    # Categories are the engine's four pages; order within a Java tab is never sorted.
    categories = []
    for row in groups:
        category = next((c for c in categories if c['category_name'] == row['category_name']), None)
        if category is None:
            category = {'category_name': row['category_name'], 'groups': []}
            categories.append(category)
        category['groups'].extend(row['groups'])
    output[root / CATALOG] = encoded({'format_version': '1.21.60',
        'minecraft:crafting_items_catalog': {'categories': categories}})
    for locale in LOCALES:
        path = root / 'runtime/RP/texts' / (locale + '.lang')
        labels = {tab['group']: tab['labels'][locale] for tab in plan['tabs']}
        output[path] = localize(path.read_text(encoding='utf-8'), labels).encode()
    return output


def apply(root, write=False):
    root = Path(root).resolve()
    updates = planned(root)
    stale = [p for p, content in updates.items() if p.read_bytes() != content]
    if not write and stale:
        raise ValueError('Stale creative catalog/definitions/labels: ' + ', '.join(str(p.relative_to(root)) for p in stale[:12]))
    for path in stale:
        path.write_bytes(updates[path])
    return {'namespace': load(root / PLAN)['namespace'], 'visible_items': len(entries(load(root / CATALOG))),
            'planned_items': sum(len(tab['entries']) for tab in load(root / PLAN)['tabs']), 'changed_files': len(stale)}


def runtime_sources(root=HERE.parents[1]):
    """Current catalog and definition metadata; gameplay has its own checks."""
    root = Path(root).resolve()
    return frozenset(path.relative_to(root).as_posix() for path in planned(root)
                     if path == root / CATALOG or path.is_relative_to(root / 'runtime/BP/items')
                     or path.is_relative_to(root / 'runtime/BP/blocks'))


def check_java_wine_order(root, java_source):
    """Compare existing wine representatives with Java's accepted-item order."""
    plan = load(Path(root) / PLAN)
    if plan['namespace'] != 'kaleidoscope_tavern':
        raise ValueError('Java Tavern wine order requires the Tavern creative plan')
    expected = [entry['bedrock'].split(':', 1)[1] for tab in plan['tabs']
                for entry in tab['entries'] if entry.get('state') == 'maximum bottle level']
    representatives = {re.sub(r'_q[1-6]$', '', name).upper(): name for name in expected}
    if not expected or len(representatives) != len(expected):
        raise ValueError('Ambiguous Java wine representatives')
    source = Path(java_source)
    if source.is_dir():
        source /= JAVA_TABS
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', source.read_text(encoding='utf-8'), flags=re.S)
    accepted = re.findall(
        r'\boutput\s*\.\s*accept\s*\(\s*(?:BottleBlockItem\s*\.\s*getMaxLevelDrink\s*\(\s*)?'
        r'ModItems\s*\.\s*([A-Z][A-Z0-9_]*)', text)
    actual = [representatives[name] for name in accepted if name in representatives]
    if actual != expected:
        raise ValueError('Creative wine order differs from Java accepted items')
    catalog_order = [item.split(':', 1)[1] for item in entries(load(Path(root) / CATALOG))
                     if item.split(':', 1)[1] in representatives.values()]
    if catalog_order != expected:
        raise ValueError('Visible wine catalog differs from the reviewed Java order')
    return {'source': str(source), 'items': len(actual), 'order': 'passed'}


def check_current(root, java_source=None):
    """Validate current output and ownership; this is not client acceptance."""
    root = Path(root).resolve()
    sources = runtime_sources(root)
    # Definitions retain their independent gameplay/source history. Only the
    # generated catalog itself must have one exclusive current owner.
    catalog_sources = {CATALOG.as_posix()}
    ledger = load(root / 'data/baseline-reconciliation.json')
    for section in ('files', 'reviewedFunctionalDeltas'):
        if catalog_sources & set(ledger.get(section, {})):
            raise ValueError('Creative catalog returned to a historical postimage')
    for section in ('reviewedFunctionalDeltaLayers', 'reviewedAssetDeltaLayers'):
        if any(catalog_sources & set(layer['files']) for layer in ledger.get(section, [])):
            raise ValueError('Creative catalog returned to a reverse delta')
    reference = load(root / 'data/launch-repair-reference.json')
    for section in ('reviewedChanges', 'newRuntimeFiles'):
        if catalog_sources & set(reference.get(section, {})):
            raise ValueError('Creative catalog returned to the launch hash aggregate')
    report = apply(root)
    report.update(sources=sorted(sources), bds=False, client=False,
                  java_wine_order=check_java_wine_order(root, java_source) if java_source else 'not run')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=HERE.parents[1])
    parser.add_argument('--write', action='store_true', help='Regenerate reviewed catalog, visible menus and group labels')
    parser.add_argument('--java-source', type=Path, help='Check Tavern wine order against a Java checkout or ModCreativeTabs.java')
    args = parser.parse_args()
    report = apply(args.root, args.write)
    if args.java_source:
        report['java_wine_order'] = check_java_wine_order(args.root, args.java_source)
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
