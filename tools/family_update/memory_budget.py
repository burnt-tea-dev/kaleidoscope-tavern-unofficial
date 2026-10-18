"""Admit maintenance only inside its configured whole-process memory cgroup."""
from pathlib import Path
import re
from family_update import common as c

GIB = 1024 ** 3


def assess(config, meminfo, membership, current, maximum, swap_maximum):
    if not isinstance(config, dict) or set(config) != {'unit', 'limit_bytes', 'swap_limit_bytes', 'reserve_bytes'}:
        raise ValueError('Explicit maintenance memory budget is required')
    unit = config['unit']
    if not isinstance(unit, str) or not re.fullmatch(r'[A-Za-z0-9_.@-]+\.(service|scope)', unit):
        raise ValueError('Memory budget requires one explicit systemd unit')
    for key in ['limit_bytes', 'swap_limit_bytes', 'reserve_bytes']:
        if type(config[key]) is not int or config[key] < 0:
            raise ValueError('Memory budget values must be byte integers')
    if config['limit_bytes'] < 256 * 1024 ** 2 or config['reserve_bytes'] < 2 * GIB:
        raise ValueError('Memory budget lacks a usable process limit or 2 GiB operating margin')
    if not membership.startswith('/') or membership.split('/')[-1] != unit:
        raise ValueError('Maintenance is outside its reviewed memory cgroup')
    if maximum == 'max' or swap_maximum == 'max':
        raise ValueError('Maintenance cgroup memory and swap must be bounded')
    if int(maximum) != config['limit_bytes'] or int(swap_maximum) != config['swap_limit_bytes']:
        raise ValueError('Actual whole-process limits differ from the reviewed budget')
    values = {}
    for line in meminfo.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[0] == 'MemAvailable:' and parts[2] == 'kB':
            values['available'] = int(parts[1]) * 1024
    if 'available' not in values or values['available'] < 0 or current < 0:
        raise ValueError('Host or cgroup memory observation is missing')
    # MemAvailable already excludes current resident usage. Reserve enough
    # additional headroom for this entire cgroup to reach its enforced ceiling.
    needed = config['reserve_bytes'] + max(0, config['limit_bytes'] - current)
    return {'ok': values['available'] >= needed, 'unit': unit,
            'available_bytes': values['available'], 'current_bytes': current,
            'limit_bytes': int(maximum), 'swap_limit_bytes': int(swap_maximum),
            'reserve_bytes': config['reserve_bytes'], 'required_available_bytes': needed}


def require(phase):
    config = c.CONFIG.get('memory_budget')
    memberships = [line[3:] for line in Path('/proc/self/cgroup').read_text().splitlines() if line.startswith('0::')]
    if len(memberships) != 1:
        raise ValueError('Require one cgroup-v2 maintenance membership')
    membership = memberships[0]
    relative = Path(membership.removeprefix('/'))
    if '..' in relative.parts:
        raise ValueError('Unsafe cgroup path')
    group = Path('/sys/fs/cgroup') / relative
    record = assess(config, Path('/proc/meminfo').read_text(), membership,
                    int((group / 'memory.current').read_text()),
                    (group / 'memory.max').read_text().strip(),
                    (group / 'memory.swap.max').read_text().strip())
    record.update(phase=phase, recorded_at=c.now(),
                  memory_events=dict(line.split() for line in (group / 'memory.events').read_text().splitlines()))
    c.R.mkdir(parents=True, exist_ok=True)
    target = c.R / 'memory-admissions.json'
    history = c.read(target) if target.exists() else {'schema': 1, 'observations': []}
    if len(history['observations']) >= 256:
        raise ValueError('Memory admission history exceeds this transaction budget')
    history['observations'].append(record)
    c.atomic(target, history)
    if not record['ok']:
        raise RuntimeError('Maintenance deferred: insufficient memory for its enforced ceiling plus operating margin')
    return record
