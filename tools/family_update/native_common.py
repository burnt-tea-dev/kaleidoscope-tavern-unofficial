"""Native zero-player loading helpers; no simulated player or live world writes."""
import io, re, shutil, struct
from family_update.common import *

def setup_engine(engine, world_name, port, expected_inputs=None):
    properties = dict(line.split('=', 1) for line in (B / 'server.properties').read_text().splitlines() if '=' in line and not line.lstrip().startswith('#'))
    # Unset spike/slow thresholds disable those warnings. Keep every explicit
    # live watchdog value so QA observes the same limits, without adding defaults.
    # https://github.com/MicrosoftDocs/minecraft-creator/blob/main/creator/Documents/BedrockServer/server-properties.md
    watchdog = ''.join(f'{key.strip()}={value}\n' for key, value in properties.items() if key.strip().startswith('script-watchdog-'))
    live_ports = {int(properties.get('server-port', 19132)), int(properties.get('server-portv6', 19133))}
    assert not {port, port + 1} & live_ports, 'Isolated BDS port overlaps live'
    data_present = (B / 'data').exists()
    if data_present:
        assert (B / 'data').is_dir(), 'BDS data input must be a directory'
    expected_data = hashes(B / 'data') if data_present else None
    if expected_inputs is not None:
        captured_data = expected_inputs['trees'].get('data')
        assert data_present == ('data' in expected_inputs['trees']) and expected_data == captured_data, 'BDS data input differs from captured engine inventory'
    engine.mkdir()
    for name in ['bedrock_server', 'definitions', 'behavior_packs', 'resource_packs']:
        (engine / name).symlink_to((B / name).resolve(), target_is_directory=(B / name).is_dir())
    for name in ['config', 'minecraftpe', 'treatments']:
        if name=='minecraftpe':
            cache=client_pack_cache()
            shutil.copytree(B/name,engine/name,ignore=lambda directory,names:[n for n in names if Path(directory)==B/name and n in cache])
        else:shutil.copytree(B / name, engine / name)
    if data_present:
        shutil.copytree(B / 'data', engine / 'data')
        assert hashes(engine / 'data') == expected_data, 'Isolated BDS data copy differs from captured input'
        assert hashes(B / 'data') == expected_data, 'BDS data input changed during isolated copy'
    (engine / 'allowlist.json').write_text('[]\n')
    (engine / 'server.properties').write_text(f'server-name=Parity isolated native QA\nlevel-name={world_name}\nserver-port={port}\nserver-portv6={port+1}\nonline-mode=true\nallow-list=true\nview-distance=5\ntick-distance=4\nmax-threads=2\nenable-lan-visibility=false\ncontent-log-file-enabled=true\ncontent-log-console-output-enabled=true\ntransport=nethernet\n'+watchdog)

def level_metadata(source):
    import nbtlib
    raw = (source if source.is_file() else source / 'level.dat').read_bytes()
    return nbtlib.File.parse(io.BytesIO(raw[8:]), byteorder='little')

def blank_level(target, name):
    import nbtlib
    captured = R / 'production-before/level-metadata.dat'
    assert sha(captured) == read(R / 'production-before/capture.json')['level_metadata']['sha256']
    data = level_metadata(captured)
    data['LevelName'] = nbtlib.String(name)
    data['SpawnX'], data['SpawnY'], data['SpawnZ'] = nbtlib.Int(0), nbtlib.Int(80), nbtlib.Int(64)
    data['GameType'] = nbtlib.Int(1)
    if not CONFIG.get('preserve_captured_experiments',False):
        data['experiments'] = nbtlib.Compound()
    output = io.BytesIO(); data.write(output, byteorder='little'); body = output.getvalue()
    (target / 'level.dat').write_bytes(struct.pack('<II', 10, len(body)) + body)

def native_run(engine, phase, minimum_seconds=30, commands=(), delayed_commands=()):
    assert not (engine.parent / 'retired-copies.json').exists(), 'Retired QA output cannot restart; prepare a new isolated world'
    assert not (engine / "packs-pruned.json").exists(), "Completed QA engines with removed redundant packs cannot restart; prepare a new isolated world"
    log = engine / (phase + '.log')
    markers = STARTUP_MARKERS
    commands = tuple(commands)
    areas = []; names = set()
    for command in commands:
        match = re.fullmatch(r'(?:execute in (overworld|nether|the_end) run )?tickingarea add circle (-?\d+) (-?\d+) (-?\d+) (\d+) ([A-Za-z0-9_]+)(?: (?:true|false))?', command)
        if not match:
            if 'tickingarea' in command.split():
                raise ValueError('QA ticking-area commands require a supported explicitly named add')
            areas.append(None);continue
        dimension, x, _, z, radius, name = match.groups()
        area = {'dimension': dimension or 'overworld', 'name': name,
                'x': int(x), 'z': int(z), 'radius': int(radius)}
        key = (area['dimension'], name)
        if key in names:raise ValueError('Duplicate QA ticking-area name')
        names.add(key);areas.append(area)
    # BDS reports the containing chunk's center, not the requested block X/Z.
    # For example 31,-22 is acknowledged as 24,-24 (including negative Z).
    # Serialize adds so a success can be bound to exactly one dispatched name.
    acknowledgement = re.compile(r'(?m)^\[[^\n\]]+ INFO\] Added ticking area centered at (-?\d+), -?\d+, (-?\d+) with a radius of (\d+) chunks?\.\r?$')
    created = []; pending = None; cursor = 0; dispatched = 0
    sent = delayed_sent = False; sent_tick = None; stop_reason = 'timeout'; cleanup = []
    with log.open('w') as output:
        process = subprocess.Popen(['./bedrock_server'], cwd=engine, env={**os.environ, 'LD_LIBRARY_PATH': str(engine)}, stdin=subprocess.PIPE, stdout=output, stderr=subprocess.STDOUT, text=True)
        try:
            for tick in range(90):
                time.sleep(1)
                text = log.read_text(errors='replace')
                if pending is not None:
                    area, offset = pending
                    if any((int(match[1]) // 16, int(match[2]) // 16, int(match[3])) == (area['x'] // 16, area['z'] // 16, area['radius'])
                           for match in acknowledgement.finditer(text[offset:])):
                        created.append(area);pending = None;cursor += 1
                if process.poll() is not None:
                    stop_reason = 'process_exit';break
                if ' ERROR]' in text or '[error]' in text.lower():
                    stop_reason = 'error';break
                if not sent and 'Server started.' in text:
                    if pending is None and cursor < len(commands):
                        area = areas[cursor]
                        process.stdin.write(commands[cursor]+'\n');process.stdin.flush();dispatched += 1
                        if area is None:cursor += 1
                        else:pending = (area, len(text))
                    if cursor == len(commands) and pending is None:
                        sent=True;sent_tick=tick
                if sent and not delayed_sent and tick-sent_tick>=5:
                    for command in delayed_commands:process.stdin.write(command+'\n')
                    process.stdin.flush();delayed_sent=True
                if sent and all(marker in text for marker in markers) and tick >= minimum_seconds and (not delayed_commands or delayed_sent):
                    stop_reason = 'ready';break
            if process.poll() is None:
                cleanup = [f'execute in {area["dimension"]} run tickingarea remove {area["name"]}' for area in reversed(created)]
                process.communicate('\n'.join([*cleanup, 'stop'])+'\n', timeout=30)
        finally:
            if process.poll() is None: process.kill(); process.wait()
    text = log.read_text(errors='replace')
    errors = [line for line in text.splitlines() if ' ERROR]' in line or '[error]' in line.lower()]
    connections = [line for line in text.splitlines() if 'Player connected:' in line]
    result = {'phase': phase, 'started': 'Server started.' in text, 'family_initialized': all(marker in text for marker in markers), 'exit_code': process.returncode, 'errors': errors, 'warning_count': sum(' WARN]' in line or '[warning]' in line.lower() for line in text.splitlines()), 'real_player_connections': len(connections), 'log_sha256': sha(log)}
    result.update(commands_sent=bool(dispatched), commands_completed=sent, delayed_commands_sent=delayed_sent,
                  missing_startup_markers=[marker for marker in markers if marker not in text], stop_reason=stop_reason,
                  ticking_areas_created=[{key: area[key] for key in ['dimension', 'name']} for area in created],
                  ticking_area_cleanup_commands=cleanup)
    result['ok'] = result['family_initialized'] and not errors and not connections and process.returncode == 0 and sent and (not delayed_commands or delayed_sent)
    return result

def player_hashes(world):
    from leveldb import LevelDB
    database = LevelDB(str(world / 'db'))
    try: return {key.hex(): hashlib.sha256(value).hexdigest() for key,value in database.items() if key.startswith((b'player', b'~local_player'))}
    finally: database.close()
