#!/usr/bin/env python3
"""Actual host/addon in a disposable zero-player BDS, including saved mob restart.

The observer is an explicit test-only overlay in the copied host pack scope.
It never edits the source packs, live server, or existing worlds.
"""
import argparse, hashlib, json, os, pathlib, re, shutil, socket, subprocess, sys, time, zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
from baseline_gate import fingerprint
from pickup.run_native_smoke import BDS_VERSION


def render_world_liquor_probe_inputs(baseline, headers):
    """Bind the observer to the exact frozen packs copied by this invocation."""
    assert baseline['repository'] == 'casama233/kaleidoscope-world-liquor-unofficial'
    version = baseline['version']
    assert isinstance(version, list) and len(version) == 3 and all(type(value) is int and value >= 0 for value in version)
    for kind in ('BP', 'RP'):
        assert headers[kind]['version'] == version, f'{kind} probe version differs from canonical baseline'
        assert headers[kind]['uuid'] == baseline['packs'][kind]['uuid'], f'{kind} probe UUID differs from canonical baseline'
    row = {'source': 'kaleidoscope_world_liquor', 'version': '.'.join(map(str, version)),
           'behavior_uuid': headers['BP']['uuid'], 'resource_uuid': headers['RP']['uuid']}
    return 'export const WORLD_LIQUOR_PROBE_INPUTS=Object.freeze(' + json.dumps(row, separators=(',', ':')) + ');\n'


def run_phase(engine, work, phase, timeout_seconds, log_name=None):
    # Keep the same extracted engine executable for each launch. Its bytes
    # remain bound to engine_identity; no source pack or world is rewritten.
    (engine/'bedrock_server').chmod(0o755)
    log = work/(log_name or f'{phase}.log')
    with log.open('w') as output:
        process = subprocess.Popen(['./bedrock_server'], cwd=work, env={**os.environ, 'LD_LIBRARY_PATH': os.pathsep.join((str(work), str(engine)))}, stdin=subprocess.PIPE, stdout=output, stderr=subprocess.STDOUT, text=True)
        normal_stop = False
        try:
            for _ in range(timeout_seconds):
                time.sleep(1)
                text = log.read_text(errors='replace')
                if process.poll() is not None or '[LIVING_EFFECT_QA] {"kind":"failure"' in text or ' ERROR]' in text or '[error]' in text.lower():
                    break
                if any(f'"kind":"{kind}","phase":"{phase}"' in text for kind in ('done','partial')):
                    break
            if process.poll() is None:
                process.communicate('stop\n', timeout=30)
                normal_stop = process.returncode == 0
        finally:
            if process.poll() is None:
                process.kill(); process.wait()
    text = log.read_text(errors='replace')
    rows = [json.loads(line.split('[LIVING_EFFECT_QA] ', 1)[1]) for line in text.splitlines() if '[LIVING_EFFECT_QA] {' in line]
    normal_stop = normal_stop and bool(re.search(r'^Quit correctly\s*$', text, re.MULTILINE))
    errors = [line for line in text.splitlines() if re.search(r'\bERROR\]|\[error\]', line, re.IGNORECASE)]
    connections = len(re.findall(r'\bplayer[ _]?(?:connected|joined|spawned)\b', text, re.IGNORECASE))
    ok = normal_stop and not errors and not connections and any(row.get('kind') == 'done' and row.get('phase') == phase and row.get('players') == 0 for row in rows) and not any(row.get('kind') == 'failure' for row in rows)
    completed=any(row.get('kind') in ('done','partial') and row.get('phase')==phase and row.get('players')==0 for row in rows)
    return {'phase': phase, 'log': log.name, 'completed': completed, 'ok': ok, 'normal_stop': normal_stop,
            'player_connections': connections, 'errors': errors, 'observations': rows}


def resume_restart(args, engine, work, liquor, engine_identity):
    """Reobserve the stopped saved world; never rebuild its first-phase fixture."""
    assert args.phases == ['restart'], '--resume only permits --phases restart'
    original = json.loads((work/'native-living-report.json').read_text())
    assert original['engine']['executable_sha256'] == engine_identity['executable_sha256'], 'Resume engine changed'
    assert all(row['normal_stop'] and not row['player_connections'] and not row['errors'] for row in original['reports']), 'QA did not stop cleanly'
    report_path = work/'native-living-resume-report.json'
    assert not report_path.exists() and not (work/'restart-resume.log').exists(), 'Retain and inspect existing resume evidence'
    world = work/'worlds/living-effect-qa'
    roots = {'tavern': ROOT, **({'liquor': liquor} if liquor is not None else {})}
    assert set(roots) == set(original['sources']), 'Resume pack selection changed'
    overlays = dict(original['test_only_overlays'])
    observer_import = b"\n// Disposable native observer; not release content.\nimport './living-effects-probe.js';\n"
    # The observation is a new input; every canonical runtime byte must still
    # match the original frozen packs before replacing only that declared probe.
    for label, source in roots.items():
        baseline = json.loads((source/'baseline.json').read_text())
        previous = original['sources'][label]
        assert (previous['repository'], previous['version'], previous['source_trees']) == (baseline['repository'], baseline['version'], baseline['source_trees']), 'Resume runtime identity changed'
        for kind, folder in [('BP', 'behavior_packs'), ('RP', 'resource_packs')]:
            assert fingerprint(source/'runtime'/kind)[0] == baseline['source_trees'][kind], 'Resume source is not the frozen runtime'
            target = world/folder/label
            expected_names = set()
            for path in (source/'runtime'/kind).rglob('*'):
                if not path.is_file():
                    continue
                name = path.relative_to(source/'runtime'/kind).as_posix()
                expected_names.add(name)
                expected = path.read_bytes()
                if label == 'tavern' and kind == 'BP' and name == 'scripts/main.js':
                    expected += observer_import
                assert (target/name).read_bytes() == expected, 'Resume runtime differs: '+label+'/'+name
            if label == 'tavern' and kind == 'BP':
                for name, digest in overlays.items():
                    if name == 'scripts/main.js':
                        continue
                    assert hashlib.sha256((target/name).read_bytes()).hexdigest() == digest, 'Previous observer overlay differs: '+name
                expected_names.update(overlays)
            assert {p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()} == expected_names, 'Resume payload gained or lost files'
    host = world/'behavior_packs/tavern'
    shutil.copy2(args.probe, host/'scripts/living-effects-probe.js')
    overlays['scripts/living-effects-probe.js'] = hashlib.sha256(args.probe.read_bytes()).hexdigest()
    result = run_phase(engine, work, 'restart', args.timeout_seconds, 'restart-resume.log')
    report = {**original, 'scope': 'restart-only continuation; original first/restart report and logs are unchanged',
              'original_report': 'native-living-report.json', 'native_script_behavior': result['ok'],
              'test_only_overlays': overlays, 'reports': [result]}
    report_path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(result), flush=True)
    assert result['ok'], 'Saved-world readback incomplete; see restart-resume.log'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', type=pathlib.Path, required=True)
    parser.add_argument('--engine-provenance', type=pathlib.Path, help='Successful pickup-native engine receipt to bind when reusing that isolated installation')
    parser.add_argument('--liquor', type=pathlib.Path, help='Optional paired World Liquor source; omit for Tavern-only observers')
    parser.add_argument('--work', type=pathlib.Path, required=True)
    parser.add_argument('--port', type=int, default=27200)
    parser.add_argument('--probe', type=pathlib.Path, default=ROOT/'tools/native/living-effects-probe.js')
    parser.add_argument('--world-metadata', type=pathlib.Path, help='Read only level.dat from an existing isolated world; no DB is copied')
    parser.add_argument('--offline', action='store_true', help='Only inside an isolated loopback network namespace')
    parser.add_argument('--resume', action='store_true', help='Continue only restart in an existing stopped QA; keep original evidence and world unchanged')
    parser.add_argument('--phases', nargs='+', choices=['first', 'restart'], default=['first', 'restart'])
    parser.add_argument('--timeout-seconds', type=int, default=180, help='Normal-stop deadline per phase; use 420 for full native incense conversion')
    args = parser.parse_args()
    if args.timeout_seconds <= 0:
        parser.error('--timeout-seconds must be positive')
    if args.liquor is None and args.probe.resolve() == (ROOT/'tools/native/living-effects-probe.js').resolve():
        parser.error('--liquor is required for the default probe; choose --probe for a Tavern-only observer')
    if args.offline:
        assert os.readlink('/proc/self/ns/net') != os.readlink('/proc/1/ns/net') and {name for _,name in socket.if_nameindex()} == {'lo'}, 'Offline QA requires a loopback-only network namespace'
    engine, work = args.engine.resolve(), args.work.resolve()
    liquor = args.liquor.resolve() if args.liquor is not None else None
    engine_identity = {'executable_sha256': hashlib.sha256((engine/'bedrock_server').read_bytes()).hexdigest()}
    if args.resume:
        resume_restart(args, engine, work, liquor, engine_identity)
        return
    assert not work.exists(), 'Use a new isolated directory; retain failed evidence'
    if args.engine_provenance is not None:
        receipt_path = args.engine_provenance.resolve()
        assert receipt_path.parent == engine and receipt_path.name == 'native-storage-evidence.json'
        receipt_bytes = receipt_path.read_bytes(); receipt = json.loads(receipt_bytes)
        assert receipt['nativeServerSaveRestart'] is True and receipt['playerSessions'] == 0
        assert set(receipt['stages']) == {'1', '2'}
        archive = engine/'bds.zip'
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == receipt['bdsSHA256']
        with zipfile.ZipFile(archive) as source_archive:
            assert hashlib.sha256(source_archive.read('bedrock_server')).hexdigest() == engine_identity['executable_sha256']
        for phase in (1, 2):
            validation = json.loads((engine/f'stage-{phase}-runner-validation.json').read_text())
            assert validation['accepted'] and validation['returncode'] == 0 and validation['stopRequested'] and validation['completeOutputCaptured']
        engine_identity.update({'download': receipt['bdsDownload'], 'archive_sha256': receipt['bdsSHA256'],
                                'reused_successful_save_restart_receipt_sha256': hashlib.sha256(receipt_bytes).hexdigest()})
    properties = dict(line.split('=', 1) for line in (engine/'server.properties').read_text().splitlines() if '=' in line and not line.startswith('#'))
    assert not {args.port, args.port+1} & {int(properties.get('server-port', 19132)), int(properties.get('server-portv6', 19133))}
    work.mkdir(parents=True)
    for name in ['bedrock_server', 'definitions', 'behavior_packs', 'resource_packs']:
        (work/name).symlink_to(engine/name, target_is_directory=(engine/name).is_dir())
    for name in ['config', 'minecraftpe', 'treatments']:
        # This is engine configuration, never the live world or its pack cache.
        shutil.copytree(engine/name, work/name, ignore=shutil.ignore_patterns('packcache'))
    if (engine/'data').is_dir():
        shutil.copytree(engine/'data', work/'data')
    (work/'allowlist.json').write_text('[]\n')
    authentication = 'false' if args.offline else 'true'
    (work/'server.properties').write_text(f'server-name=Living effect native QA\nlevel-name=living-effect-qa\nserver-port={args.port}\nserver-portv6={args.port+1}\nallow-cheats=true\nonline-mode={authentication}\nallow-list={authentication}\nenable-lan-visibility=false\ntransport=nethernet\nview-distance=5\ntick-distance=4\nmax-threads=2\ncontent-log-file-enabled=true\ncontent-log-console-output-enabled=true\n')
    world = work/'worlds/living-effect-qa'
    world.mkdir(parents=True)
    # Reuse only level metadata from a stopped isolated QA world.
    # No DB, old test entities or player data enter this new isolated world.
    from family_update.world_experiments import transition, write_metadata, observe
    flags=json.loads(((liquor or ROOT)/'config.json').read_text())['experimentalGameplay']
    metadata=args.world_metadata if args.world_metadata is not None else engine/'worlds/pickup-smoke/level.dat'
    raw,experiment_transition=transition(metadata.read_bytes(),flags)
    write_metadata(world/'level.dat',raw)
    assert observe(raw,flags) is not None if flags else True
    (work/'world-experiment-transition.json').write_text(json.dumps(experiment_transition,indent=2)+'\n')
    manifests = {'BP': [], 'RP': []}
    sources = {}
    probe_inputs = None
    for label, source in [('tavern', ROOT)] + ([('liquor', liquor)] if liquor is not None else []):
        baseline = json.loads((source/'baseline.json').read_text())
        headers = {}
        source_record = {'commit': subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip(),
                         'repository': baseline['repository'], 'version': baseline['version'], 'source_trees': {}}
        for kind, folder in [('BP', 'behavior_packs'), ('RP', 'resource_packs')]:
            target = world/folder/label
            shutil.copytree(source/'runtime'/kind, target)
            tree, _ = fingerprint(target)
            assert tree == baseline['source_trees'][kind], f'{label} {kind} copied runtime differs from frozen source'
            source_record['source_trees'][kind] = tree
            header = json.loads((target/'manifest.json').read_text())['header']
            headers[kind] = header
            manifests[kind].append({'pack_id': header['uuid'], 'version': header['version']})
        sources[label] = source_record
        if label == 'liquor':
            probe_inputs = render_world_liquor_probe_inputs(baseline, headers)
    host = world/'behavior_packs/tavern'
    if probe_inputs is not None:
        (host/'scripts/native-probe-inputs.js').write_text(probe_inputs)
    shutil.copy2(args.probe, host/'scripts/living-effects-probe.js')
    shutil.copy2(ROOT/'tools/native/living-probe-entity.json', host/'entities/living-probe.json')
    shutil.copy2(ROOT/'tools/native/health-helper-entity.json', host/'entities/health-helper-probe.json')
    with (host/'scripts/main.js').open('a') as output:
        output.write("\n// Disposable native observer; not release content.\nimport './living-effects-probe.js';\n")
    overlays = {'scripts/living-effects-probe.js': hashlib.sha256(args.probe.read_bytes()).hexdigest(),
                'entities/living-probe.json': hashlib.sha256((ROOT/'tools/native/living-probe-entity.json').read_bytes()).hexdigest(),
                'entities/health-helper-probe.json': hashlib.sha256((ROOT/'tools/native/health-helper-entity.json').read_bytes()).hexdigest(),
                'scripts/main.js': 'Append only the declared disposable observer import after verifying the complete copied runtime.'}
    if probe_inputs is not None:
        overlays['scripts/native-probe-inputs.js'] = hashlib.sha256(probe_inputs.encode()).hexdigest()
    if args.probe.resolve() == (ROOT/'tools/native/shaker-migration-probe.js').resolve():
        for support_name in ('machine-ingredients-probe.js', 'status-aura-probe.js', 'potion-bottle-probe.js'):
            support = ROOT/'tools/native'/support_name
            shutil.copy2(support, host/'scripts'/support_name)
            overlays['scripts/'+support_name] = hashlib.sha256(support.read_bytes()).hexdigest()
    for kind, filename in [('BP', 'world_behavior_packs.json'), ('RP', 'world_resource_packs.json')]:
        (world/filename).write_text(json.dumps(manifests[kind], indent=2)+'\n')
    reports = []
    for phase in args.phases:
        result = run_phase(engine, work, phase, args.timeout_seconds)
        reports.append(result)
        (work/'native-living-report.json').write_text(json.dumps({'native_script_behavior': len(reports)==len(args.phases) and all(row['ok'] for row in reports),
            'client': False, 'full_family': False, 'live': False, 'test_only_host_overlay': True,
            'engine': engine_identity, 'sources': sources, 'copied_runtime_matches_frozen_source': True, 'test_only_overlays': overlays,
            'reports': reports}, indent=2)+'\n')
        print(json.dumps(reports[-1]), flush=True)
        assert result['normal_stop'] and not result['errors'] and not result['player_connections'] and result['completed'], f'{phase} did not complete: see {result["log"]}'
    assert all(row['ok'] for row in reports), 'One or more native capabilities remain unavailable; see native-living-report.json'


if __name__ == '__main__':
    main()
