"""One current owner for the Cookery station module and its exact public API hooks.

Only wiring/identity/receipt validation is public. The performance algorithm is
an owned private runtime helper; the clean author module is never replaced by a
stored whole-file override or reconstructed from a historical output.
"""
import copy
from datetime import date
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

KIND = 'cookery-station-performance'
IDENTITY = 'senluo:cookery-station-performance'
HOST = '439d9798-118a-43ad-8a91-aab3161d9cb5'
ARCHIVE = 'f994f8aa3b3aa4ab323c021f871f05291a827e7957aa265e17e91a085ba85b81'
TARGET = 'scripts/custom_components/blocks/directStation.js'
AUTHOR = 'd107c42f21b394e1273f0e8dcf3701fb97a97a7775d26da0010a447a9c085c57'
HELPER = 'scripts/host_api/cookery-station-performance.js'
INSTALLED_HELPER = 'scripts/api/senluo_station_performance.js'
SPEC = 'host-extensions/cookery-station-performance.json'
API_SPEC = 'projects/grilling/gameplay_core/behavior_pack/host-extensions/board-api.json'
LOGICAL_PRIVATE = 'local/senluo-amw-cuisine'
WIRE_OPS = 'bd5d08807eda2c86e9c78da5d75c02545aca8b20f45f52a6f4c9f1a74ad1e364'
HELPER_IMPORT = 'import {createCookeryStationPerformance} from "../../api/senluo_station_performance.js";\n'
INIT = {'path': TARGET, 'anchor': 'const STEAMER_DISPLAY="kaleidoscope_cookery:steamer_item_display";',
        'position': 'after', 'text': '\nconst stationPerformance=createCookeryStationPerformance(world,system,[DISPLAY,POT_DISPLAY,STOCKPOT_DISPLAY,STEAMER_DISPLAY]);'}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def declaration_digest(value):
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())


def require(condition, message):
    if not condition:
        raise ValueError('Cookery station owner: ' + message)


def safe(root, name):
    path = PurePosixPath(name)
    require(not path.is_absolute() and '..' not in path.parts and '\\' not in name, 'unsafe path')
    result = Path(root) / name
    require(not result.is_symlink() and result.resolve().is_relative_to(Path(root).resolve()), 'path leaves source')
    return result


def head(root):
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()


def current_station_profile(spec, owned_root, api, api_raw, grilling_root):
    """Validate the single current source contract, without version replay layers."""
    require(spec.get('schema') == 1 and spec.get('kind') == KIND and spec.get('id') == IDENTITY
            and spec.get('version') == [1, 0, 1], 'identity differs')
    require(spec.get('host_uuid') == HOST and spec.get('archive_sha256') == ARCHIVE
            and spec.get('original_files') == {TARGET: AUTHOR}, 'clean author input differs')
    require(set(spec.get('patched_files', {})) == {TARGET}
            and re.fullmatch('[0-9a-f]{64}', spec['patched_files'][TARGET]) is not None, 'output inventory differs')
    require(api.get('host_uuid') == HOST and api.get('archive_sha256') == ARCHIVE
            and api.get('original_files', {}).get(TARGET) == AUTHOR, 'public API author input differs')
    handoff = spec.get('owner_handoff', {})
    hooks = [op for op in api['insertions'] if op.get('path') == TARGET]
    require(handoff.get('from_repository') == 'burnt-tea-dev/kaleidoscope-grilling-unofficial'
            and handoff.get('from_commit') == head(grilling_root)
            and handoff.get('spec_path') == API_SPEC and handoff.get('spec_sha256') == digest(api_raw)
            and handoff.get('id') == api['id'] and handoff.get('version') == api['version']
            and handoff.get('target') == TARGET and handoff.get('author_sha256') == AUTHOR
            and handoff.get('prior_output_sha256') == api['patched_files'][TARGET]
            and handoff.get('retained_imports_sha256') == digest(api['imports'][TARGET].encode())
            and handoff.get('retained_insertions_sha256') == declaration_digest(hooks), 'public API source binding differs')
    require(spec.get('imports') == {TARGET: HELPER_IMPORT + api['imports'][TARGET]}
            and spec.get('insertions') == [*hooks, INIT], 'existing public API hooks were changed or layered')
    require(declaration_digest(spec.get('text_replacements')) == WIRE_OPS
            and spec.get('json_updates') == [] and not spec.get('removed_files')
            and spec.get('copies') == {HELPER: INSTALLED_HELPER}, 'wiring exceeds current display/persistence owner')
    modules = {}
    for source, target in api['copies'].items():
        if target.startswith('scripts/') and target.endswith('.js'):
            modules[target] = digest(safe(Path(grilling_root) / 'projects/grilling/gameplay_core/behavior_pack', source).read_bytes())
    require(handoff.get('retained_modules') == modules and len(modules) == len(api['copies'])
            and INSTALLED_HELPER not in modules, 'public API module retention differs')
    helper_sha = digest(safe(owned_root, HELPER).read_bytes())
    require(helper_sha == spec.get('helper_sha256'), 'owned helper differs')
    require(date.fromisoformat(spec['expires']) >= date.today(), 'declaration expired')
    for field in ('authorization', 'feedback', 'removal_condition'):
        require(isinstance(spec.get(field), str) and bool(spec[field]), 'missing review metadata: ' + field)
    return {key: spec[key] for key in ('id', 'version', 'host_uuid', 'archive_sha256', 'original_files', 'patched_files')} | {
        'spec_sha256': declaration_digest(spec), 'copies': {INSTALLED_HELPER: {'source': HELPER, 'sha256': helper_sha}},
        'source_owner': 'upstream_extended', 'required_extensions': [], 'admission': 'current-cookery-station-owner'}


def collect_station_handoffs(owned, sources):
    """Resolve both real source checkouts before any public API target is delegated."""
    plans = {}
    for own in owned:
        repo = Path(sources[own['key']]); config = json.loads((repo / 'baseline.json').read_text())
        root = repo / config['runtime']['BP']; path = root / SPEC
        if not path.exists():
            continue
        require(config['repository'] == LOGICAL_PRIVATE and own['repository'] == LOGICAL_PRIVATE, 'foreign private source')
        identity = json.loads((repo / '.repo-target.json').read_text())
        require(identity.get('repository') == 'burnt-tea-dev/senluo-family-integration-private'
                and identity.get('repository_id') == 1406868911 and identity.get('private') is True
                and identity.get('logical_runtime_repository') == LOGICAL_PRIVATE
                and identity.get('owner', {}).get('id') == 344456559, 'unverified private repository identity')
        require('grilling' in sources, 'public API source missing')
        grilling = Path(sources['grilling']); api_path = grilling / API_SPEC
        api_raw = api_path.read_bytes(); api = json.loads(api_raw)
        spec = json.loads(path.read_text()); profile = current_station_profile(spec, root, api, api_raw, grilling)
        manifest = json.loads((root / 'manifest.json').read_text())
        require(manifest['header']['version'] == config['version'], 'private runtime identity differs')
        require(HOST not in plans, 'two private station owners')
        binding = {'owner_id': IDENTITY, 'owner_repository': LOGICAL_PRIVATE,
                   'owner_commit': head(repo), 'owner_version': config['version'], 'spec_sha256': digest(path.read_bytes()),
                   'input_sha256': AUTHOR, 'output_sha256': spec['patched_files'][TARGET],
                   'helper_target': INSTALLED_HELPER, 'helper_sha256': spec['helper_sha256'],
                   'retained_api': spec['owner_handoff']}
        plans[HOST] = {'private_key': own['key'], 'api_key': 'grilling', 'api': api, 'api_raw_sha256': digest(api_raw),
                       'spec': spec, 'profile': profile, 'binding': binding, 'delegated': False, 'completed': False}
    return plans


def active_api_declaration(spec):
    active = copy.deepcopy(spec)
    for key in ('original_files', 'patched_files', 'imports'):
        active[key].pop(TARGET)
    for key in ('insertions', 'text_replacements', 'json_updates'):
        if key in active:
            active[key] = [op for op in active[key] if op.get('path') != TARGET]
    return active


def delegated_api_spec(spec, plan):
    require(spec == plan['api'] and declaration_digest(spec) == declaration_digest(plan['api']), 'public declaration changed')
    require(not plan['delegated'], 'public station file delegated twice')
    plan['delegated'] = True
    return active_api_declaration(spec)


def validate_public_delegation(actual, expected, binding=None):
    """Validate the unchanged API surface; final owner pairing is checked separately.

    This never reconstructs or claims the retired public station output. Its one
    file remains the clean author input until the current private owner runs.
    """
    delegated = actual.get('delegated_files')
    require(isinstance(delegated, dict) and set(delegated) == {TARGET}, 'unexpected delegated API targets')
    value = delegated[TARGET]
    require(isinstance(value, dict) and (binding is None or value == binding), 'private owner binding differs')
    require(value.get('owner_id') == IDENTITY and value.get('owner_repository') == LOGICAL_PRIVATE
            and value.get('input_sha256') == AUTHOR and value.get('helper_target') == INSTALLED_HELPER
            and all(re.fullmatch('[0-9a-f]{64}', value.get(key, '')) for key in ('spec_sha256', 'output_sha256', 'helper_sha256'))
            and re.fullmatch('[0-9a-f]{40}', value.get('owner_commit', '')) is not None, 'invalid private delegation binding')
    retained = value.get('retained_api', {})
    require(retained.get('id') == expected['id'] and retained.get('version') == expected['version']
            and retained.get('target') == TARGET and retained.get('author_sha256') == AUTHOR
            and retained.get('prior_output_sha256') == expected['patched_files'].get(TARGET), 'retired API ownership differs')
    for key in ('id', 'version', 'copies'):
        require(actual.get(key) == expected.get(key), 'unaffected public API contract differs: ' + key)
    for key in ('original_files', 'patched_files'):
        require(actual.get(key) == {name: value for name, value in expected[key].items() if name != TARGET}, 'unaffected public API files differ: ' + key)
    copies = expected.get('copies', {})
    require(retained.get('retained_modules') == {target: record['sha256'] for target, record in copies.items()
                if target.startswith('scripts/') and target.endswith('.js')}, 'retained public API modules differ')
    return value


def public_api_receipt(api, modules):
    return {key: api[key] for key in ('id', 'version', 'original_files', 'patched_files')} | {'copies': modules}


def retained_api_copies(api, retained):
    return {target: {'source': source, 'sha256': retained[target]} for source, target in api['copies'].items()}


def validate_station_receipt_pair(spec, profile, api, api_receipt, station_receipt, files,
                                  *, owner_commit, owner_version, spec_sha256):
    """Require the real current private output, not just a pending delegation claim."""
    expected = {'owner_id': IDENTITY, 'owner_repository': LOGICAL_PRIVATE,
                'owner_commit': owner_commit, 'owner_version': owner_version, 'spec_sha256': spec_sha256,
                'input_sha256': AUTHOR, 'output_sha256': spec['patched_files'][TARGET],
                'helper_target': INSTALLED_HELPER, 'helper_sha256': spec['helper_sha256'],
                'retained_api': spec['owner_handoff']}
    copies = retained_api_copies(api, spec['owner_handoff']['retained_modules'])
    validate_public_delegation(api_receipt, public_api_receipt(api, copies), expected)
    require(station_receipt.get('owner_handoff') == expected
            and station_receipt.get('repository') == LOGICAL_PRIVATE
            and station_receipt.get('commit') == owner_commit and station_receipt.get('working_candidate') is False
            and station_receipt.get('spec_sha256') == spec_sha256
            and station_receipt.get('owner_version') == owner_version, 'current private receipt binding differs')
    for field in ('id', 'version', 'original_files', 'patched_files', 'copies'):
        require(station_receipt.get(field) == profile[field], 'current station receipt differs: ' + field)
    require(files.get(TARGET) == spec['patched_files'][TARGET]
            and files.get(INSTALLED_HELPER) == spec['helper_sha256'], 'current station payload differs')
    require(all(files.get(name) == expected for name, expected in spec['owner_handoff']['retained_modules'].items()), 'current API modules changed after handoff')


def render_station(raw, spec):
    require(digest(raw) == AUTHOR == spec['original_files'][TARGET], 'station source is not clean author input')
    text = spec['imports'][TARGET] + raw.decode()
    for op in spec['insertions']:
        anchor = op['anchor']
        require(op['path'] == TARGET and bool(anchor) and text.count(anchor) == 1
                and op['position'] in ('before', 'after'), 'station insertion is not unique')
        text = text.replace(anchor, op['text'] + anchor if op['position'] == 'before' else anchor + op['text'])
    for op in spec['text_replacements']:
        require(op['path'] == TARGET and bool(op['before']) and text.count(op['before']) == 1, 'station wiring preimage differs')
        text = text.replace(op['before'], op['after'])
    raw = text.encode()
    require(digest(raw) == spec['patched_files'][TARGET], 'current station output differs')
    return raw


def apply_station_extension(spec, owned_root, host_root, source, plan):
    require(plan is not None and spec == plan['spec'] and plan['delegated'] and not plan['completed'], 'missing or repeated current owner handoff')
    require(source.get('owner') == 'upstream_extended' and source.get('archive_sha256') == ARCHIVE, 'preceding author/API source differs')
    prior = [row for row in source.get('reviewed_extensions', []) if row.get('id') == plan['api']['id']]
    require(len(prior) == 1, 'one preceding public API receipt is required')
    modules = retained_api_copies(plan['api'], spec['owner_handoff']['retained_modules'])
    validate_public_delegation(prior[0], public_api_receipt(plan['api'], modules), plan['binding'])
    for name, expected in spec['owner_handoff']['retained_modules'].items():
        require(digest(safe(host_root, name).read_bytes()) == expected, 'public API helper changed: ' + name)
    target = safe(host_root, TARGET); helper = safe(owned_root, HELPER); destination = safe(host_root, INSTALLED_HELPER)
    require(not destination.exists() and digest(helper.read_bytes()) == spec['helper_sha256'], 'helper collision or changed source')
    output = render_station(target.read_bytes(), spec)
    target.write_bytes(output); destination.parent.mkdir(parents=True, exist_ok=True); destination.write_bytes(helper.read_bytes())
    plan['completed'] = True
    return {key: spec[key] for key in ('id', 'version', 'expires', 'original_files', 'patched_files', 'authorization', 'feedback', 'removal_condition')} | {
        'copies': plan['profile']['copies'], 'owner_handoff': plan['binding']}


def verify_station_handoffs(plans, records, output):
    for host, plan in plans.items():
        require(plan['delegated'] and plan['completed'], 'unfulfilled public station delegation')
        row = next((row for row in records if row['uuid'] == host), None)
        require(row is not None and row['files'].get(TARGET) == plan['binding']['output_sha256']
                and row['files'].get(INSTALLED_HELPER) == plan['binding']['helper_sha256'], 'completed station payload differs')
        extensions = row['source'].get('reviewed_extensions', [])
        owner = [record for record in extensions if record.get('id') == IDENTITY]
        api = [record for record in extensions if record.get('id') == plan['api']['id']]
        require(len(owner) == len(api) == 1 and owner[0].get('owner_handoff') == plan['binding'], 'current station receipt omitted or repeated')
        validate_public_delegation(api[0], public_api_receipt(plan['api'], retained_api_copies(plan['api'], plan['spec']['owner_handoff']['retained_modules'])), plan['binding'])
        for name, expected in plan['spec']['owner_handoff']['retained_modules'].items():
            require(row['files'].get(name) == expected, 'retained public API output differs: ' + name)
