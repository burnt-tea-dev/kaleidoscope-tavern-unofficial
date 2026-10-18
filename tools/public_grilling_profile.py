"""Select the public Grilling/Cookery profile; reuse the canonical family builder.

The complete author pack is supplied and generated locally. This module neither
uploads that output nor installs it into a world. It does not compile gameplay.
"""
import copy
import hashlib
import io
import json
from pathlib import Path
import zipfile

COOKERY_SHA = 'f994f8aa3b3aa4ab323c021f871f05291a827e7957aa265e17e91a085ba85b81'
COOKERY_BP = '439d9798-118a-43ad-8a91-aab3161d9cb5'
COOKERY_RP = '01ba9a7f-877e-46c7-8583-6c0441366b55'
IDENTITIES = {
    'grilling': {'repository': 'casama233/kaleidoscope-grilling-unofficial', 'repository_id': 1377218440},
    'tavern': {'repository': 'casama233/kaleidoscope-tavern-unofficial', 'repository_id': 1377171148},
}


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def select_public_grilling_lock(lock, sources):
    if set(sources) not in ({'grilling'}, {'grilling', 'tavern'}):
        raise ValueError('Public Grilling accepts only Grilling and optional Tavern sources')
    owned = [copy.deepcopy(row) for row in lock['owned'] if row['key'] in sources]
    if len(owned) != len(sources) or {row['key'] for row in owned} != set(sources):
        raise ValueError('Canonical lock lacks an exact public owned source')
    upstream = [copy.deepcopy(row) for row in lock['upstream'] if row['name'] == 'Cookery']
    if len(upstream) != 1:
        raise ValueError('Canonical lock must select exactly one Cookery archive')
    host = upstream[0]
    expected = {COOKERY_BP: [1, 6, 2], COOKERY_RP: [1, 6, 2]}
    if (host.get('project_id') != 1673664 or host.get('file_id') != 9227406
            or host.get('sha256') != COOKERY_SHA or len(host['packs']) != 2
            or {row['uuid']: row['version'] for row in host['packs']} != expected):
        raise ValueError('Public profile requires the reviewed clean Cookery 1.6.2 pair')
    manifests = []
    for row in owned:
        config = read(sources[row['key']] / 'baseline.json')
        if (row['repository'] != IDENTITIES[row['key']]['repository']
                or any(config.get(k) != v for k, v in IDENTITIES[row['key']].items())
                or row['version'] != config['version'] or row['source_trees'] != config['source_trees']):
            raise ValueError('Owned source identity or baseline differs from the canonical lock')
        for side in ['BP', 'RP']:
            manifest = read(sources[row['key']] / config['runtime'][side] / 'manifest.json')
            if (manifest['header']['uuid'] != config['packs'][side]['uuid']
                    or manifest['header']['version'] != config['version']
                    or manifest.get('dependencies', []) != config['packs'][side]['dependencies']):
                raise ValueError('Public source manifest differs from its canonical baseline')
            manifests.append((side, manifest))
    grilling = read(sources['grilling'] / 'baseline.json')
    spec = read(sources['grilling'] / grilling['runtime']['BP'] / 'host-extensions/board-api.json')
    if (tuple(grilling['version']) < (2, 8, 154) or spec.get('id') != 'kaleidoscope_grilling:family-api-0.2.13'
            or spec.get('archive_sha256') != COOKERY_SHA or spec.get('host_uuid') != COOKERY_BP):
        raise ValueError('Published G149/Cookery160 cannot be used as the new public162 adapter')
    versions = {**expected, **{m['header']['uuid']: m['header']['version'] for _, m in manifests}}
    if len(versions) != len(expected) + len(manifests):
        raise ValueError('Public profile has colliding pack identities')
    for _, manifest in manifests:
        for dep in manifest.get('dependencies', []):
            if 'uuid' in dep and versions.get(dep['uuid']) != dep['version']:
                raise ValueError('Public profile has an unresolved exact dependency')
    sides = {'behavior': {COOKERY_BP}, 'resource': {COOKERY_RP}}
    for side, manifest in manifests:
        sides['behavior' if side == 'BP' else 'resource'].add(manifest['header']['uuid'])
    order = {side: [uid for uid in lock['order'][side] if uid in selected] for side, selected in sides.items()}
    if any(len(order[side]) != len(selected) or set(order[side]) != selected for side, selected in sides.items()):
        raise ValueError('Canonical order does not close the public profile')
    return {'schema': lock.get('schema', 1), 'owned': owned, 'upstream': upstream, 'order': order}


def validate_public_archive(archives, host, read_author_packs):
    if len(archives) != 1 or not Path(archives[0]).is_file():
        raise ValueError('Supply exactly one clean Cookery archive file, with no extra packs')
    raw = Path(archives[0]).read_bytes()
    if digest(raw) != host['sha256']:
        raise ValueError('Cookery archive checksum differs')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        found = [{'uuid': m['header']['uuid'], 'version': m['header']['version']} for m, _ in read_author_packs(z)]
    if sorted(found, key=lambda r: r['uuid']) != sorted(host['packs'], key=lambda r: r['uuid']):
        raise ValueError('Cookery archive includes an extra, missing or changed pack')


def export_local_mcaddon(out, receipt, name):
    archive = out / name
    if archive.exists():
        raise ValueError('Never replace an existing local archive')
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for row in receipt['packs']:
            root = out / (row['side'] + '_packs') / row['uuid']
            actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
            if actual != set(row['files']):
                raise ValueError('Candidate file inventory changed before local export')
            for relative, expected in sorted(row['files'].items()):
                path = root / relative
                if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
                    raise ValueError('Candidate export path is outside its pack')
                raw = path.read_bytes()
                if digest(raw) != expected:
                    raise ValueError('Candidate bytes changed before local export')
                info = zipfile.ZipInfo(row['side'] + '_packs/' + row['uuid'] + '/' + relative, (2026, 10, 18, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                z.writestr(info, raw)
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError('Local archive CRC verification failed')
    return archive


def build_public_grilling(lock, sources, archives, out, *, assemble_family, read_author_packs):
    sources = {key: Path(path) for key, path in sources.items()}
    out = Path(out)
    selected = select_public_grilling_lock(lock, sources)
    validate_public_archive(archives, selected['upstream'][0], read_author_packs)
    # The existing canonical baseline/dirty/source/hash/extension gates execute
    # unchanged. Public setup never exposes working-candidate or private options.
    receipt = assemble_family(selected, sources, list(map(Path, archives)), out,
                              source_identities={key: IDENTITIES[key] for key in sources})
    version = next(row['version'] for row in selected['owned'] if row['key'] == 'grilling')
    archive = export_local_mcaddon(out, receipt, 'Grilling_Public_' + '.'.join(map(str, version)) + '_Cookery_1.6.2_API_0.2.13.mcaddon')
    report = {'schema': 1, 'profile': 'grilling-public-cookery162', 'packs': len(receipt['packs']),
              'archive': archive.name, 'archive_sha256': digest(archive.read_bytes()),
              'receipt': 'family-receipt.json', 'receipt_sha256': digest((out / 'family-receipt.json').read_bytes()),
              'contains_author_pack_local_only': True, 'official_author_release': False,
              'world_installed': False, 'saved_world_migration': False, 'client': False, 'production_ready': False}
    (out / 'public-profile.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
