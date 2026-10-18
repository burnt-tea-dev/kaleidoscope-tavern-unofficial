"""Admit maintenance only inside its configured whole-process memory cgroup."""
from pathlib import Path
import re
import subprocess
import sys
import time
from family_update import common as c

GIB = 1024 ** 3
MIB = 1024 ** 2
LIGHT_PHASES = frozenset({'prepare', 'record-ci', 'deploy', 'update', 'verify-live',
                          'cleanup-copies', 'cleanup-engine-inputs', 'capture_predeploy',
                          'build_candidate', 'record_static', 'recover-preinstall'})
NATIVE_PHASES = frozenset({'saved-world', 'rehearse_saved_world', 'saved_world_first', 'saved_world_restart'})
SHRINK_HEADROOM = 32 * MIB
RESIDENT_ACCOUNTING_PAD = 32 * MIB
RECLAIM_ATTEMPTS = 8
RECLAIM_SECONDS = 2.0


def phase_budget(config, phase):
    """An opt-in cap table; historical single-cap configurations are unchanged."""
    if not isinstance(config, dict) or 'phase_limits' not in config:
        return config, None
    if set(config) != {'unit', 'limit_bytes', 'swap_limit_bytes', 'reserve_bytes', 'phase_limits'}:
        raise ValueError('Unexpected phased memory budget fields')
    limits = config['phase_limits']
    if not isinstance(limits, dict) or set(limits) != {'light', 'native'} or any(type(x) is not int for x in limits.values()):
        raise ValueError('Two exact reviewed phase limits are required')
    if not 256 * MIB <= limits['light'] < limits['native'] == config['limit_bytes'] or config['swap_limit_bytes'] != 0:
        raise ValueError('Phased memory ceilings or zero-swap contract differ')
    if phase not in LIGHT_PHASES | NATIVE_PHASES:
        raise ValueError('Unknown memory budget phase: ' + str(phase))
    category = 'native' if phase in NATIVE_PHASES else 'light'
    return {**{k: v for k, v in config.items() if k != 'phase_limits'}, 'limit_bytes': limits[category]}, category


def assess_phase(config, phase, meminfo, membership, current, maximum, swap_maximum, resident_anon=0):
    selected, category = phase_budget(config, phase)
    if category is None:
        return assess(selected, meminfo, membership, current, maximum, swap_maximum)
    if maximum not in {str(x) for x in config['phase_limits'].values()} or type(current) is not int or current < 0:
        raise ValueError('Actual phase ceiling is not one of the reviewed limits')
    if type(resident_anon) is not int or resident_anon < 0:
        raise ValueError('Phased memory requires a valid resident anonymous observation')
    # Only our already-resident anon can reduce the remaining enforced budget.
    # File cache/shmem/kernel receive no credit; retain an accounting pad and
    # cap the observation by memory.current in case counters were sampled apart.
    credit = max(0, min(current, resident_anon) - RESIDENT_ACCOUNTING_PAD)
    result = assess(selected, meminfo, membership, credit, str(selected['limit_bytes']), swap_maximum)
    result.update(current_bytes=current, previous_limit_bytes=int(maximum), phase_category=category,
                  resident_anon_bytes=resident_anon, resident_accounting_pad_bytes=RESIDENT_ACCOUNTING_PAD,
                  current_headroom_credit_bytes=credit)
    return result


def _bounded_command(args, timeout):
    child = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        return child.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        child.kill()
        try:
            child.wait(timeout=0.2)
        except subprocess.TimeoutExpired:
            pass  # The still-enclosed helper cannot authorize a cap reduction.
        raise RuntimeError('Memory control helper timed out; retain the current cap')


def _reclaim(group, amount, timeout):
    # memory.reclaim can partially succeed with EAGAIN. Keep its potentially
    # blocking write in a bounded child while the original high cap still holds.
    worker = ("import errno,os,sys\n"
              "try:\n"
              " fd=os.open(sys.argv[1],os.O_WRONLY)\n"
              " try: os.write(fd,(sys.argv[2]+' swappiness=0').encode())\n"
              " finally: os.close(fd)\n"
              "except OSError as e:\n"
              " if e.errno==errno.EAGAIN: sys.exit(75)\n"
              " raise\n")
    code = _bounded_command([sys.executable, '-B', '-c', worker, str(group / 'memory.reclaim'), str(amount)], timeout)
    if code not in (0, 75):
        raise RuntimeError('Bounded file-cache reclaim failed; retain the current cap')


def _fit_before_shrink(group, target):
    fit = target - SHRINK_HEADROOM
    deadline = time.monotonic() + RECLAIM_SECONDS
    attempts = []
    for attempt in range(RECLAIM_ATTEMPTS + 1):
        current = int((group / 'memory.current').read_text())
        stats = dict((key, int(value)) for key, value in (line.split() for line in (group / 'memory.stat').read_text().splitlines()))
        if not {'anon', 'kernel', 'file', 'shmem', 'unevictable', 'slab_reclaimable'} <= set(stats) or any(x < 0 for x in stats.values()):
            raise ValueError('Missing or invalid memory.stat shrink observation')
        floor = stats['anon'] + stats['shmem'] + max(0, stats['kernel'] - stats['slab_reclaimable'])
        if current <= fit:
            return {'fit_bytes': fit, 'current_bytes': current, 'unreclaimable_estimate_bytes': floor, 'attempts': attempts}
        remaining = deadline - time.monotonic()
        if floor > fit or stats['file'] <= stats['shmem'] + stats['unevictable'] or attempt == RECLAIM_ATTEMPTS or remaining <= 0:
            raise RuntimeError('Current memory cannot safely fit the lower cap; retain the current cap')
        amount = min(256 * MIB, current - fit)
        _reclaim(group, amount, min(0.35, remaining))
        attempts.append({'requested_bytes': amount, 'current_before_bytes': current})
    raise RuntimeError('Bounded reclaim did not fit the lower cap')


def _set_limit(config, target):
    code = _bounded_command(['systemctl', 'set-property', '--runtime', '--', config['unit'],
                             'MemoryMax=' + str(target), 'MemorySwapMax=' + str(config['swap_limit_bytes'])], 3.0)
    if code:
        raise RuntimeError('Unable to enforce the reviewed phase ceiling')


def _group():
    memberships = [line[3:] for line in Path('/proc/self/cgroup').read_text().splitlines() if line.startswith('0::')]
    if len(memberships) != 1:
        raise ValueError('Require one cgroup-v2 maintenance membership')
    membership = memberships[0]
    relative = Path(membership.removeprefix('/'))
    if '..' in relative.parts:
        raise ValueError('Unsafe cgroup path')
    return membership, Path('/sys/fs/cgroup') / relative


def _assess_current(config, phase, membership, group):
    resident_anon = 0
    if phase_budget(config, phase)[1] is not None:
        try:
            rows = [line.split() for line in (group / 'memory.stat').read_text().splitlines()]
        except OSError as error:
            raise ValueError('Missing phased memory.stat anonymous observation') from error
        anon = [row for row in rows if row and row[0] == 'anon']
        if len(anon) != 1 or len(anon[0]) != 2 or not re.fullmatch('[0-9]+', anon[0][1]):
            raise ValueError('Missing or invalid phased memory.stat anonymous observation')
        resident_anon = int(anon[0][1])
    return assess_phase(config, phase, Path('/proc/meminfo').read_text(), membership,
                        int((group / 'memory.current').read_text()), (group / 'memory.max').read_text().strip(),
                        (group / 'memory.swap.max').read_text().strip(), resident_anon=resident_anon)


def _events(group):
    return dict(line.split() for line in (group / 'memory.events').read_text().splitlines())


def _native_guard():
    c.assert_lease()
    server = c.summary()
    if server.get('name') != c.SERVER or server.get('status') != 'STOPPED' or server.get('player_count') != 0:
        raise ValueError('Native ceiling requires this owned, stopped and empty server')


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
    selected, category = phase_budget(config, phase)
    if category == 'native':
        _native_guard()
    membership, group = _group()
    record = _assess_current(config, phase, membership, group)
    if category and any(int(_events(group).get(key, '0')) for key in ('oom', 'oom_kill', 'oom_group_kill')):
        raise RuntimeError('This maintenance cgroup already recorded an OOM; do not retry with a higher cap')
    if record['ok'] and category and record['previous_limit_bytes'] != selected['limit_bytes']:
        if selected['limit_bytes'] < record['previous_limit_bytes']:
            record['shrink'] = _fit_before_shrink(group, selected['limit_bytes'])
        # Memory may have changed during reclaim. Re-admit immediately before
        # changing the real systemd limit, and again after exact readback.
        before = _assess_current(config, phase, membership, group)
        if not before['ok']:
            record = before
        else:
            if selected['limit_bytes'] < before['previous_limit_bytes'] and before['current_bytes'] > selected['limit_bytes'] - SHRINK_HEADROOM:
                raise RuntimeError('Current memory regrew before the lower cap; retain the current cap')
            if category == 'native':
                _native_guard()
            _set_limit(config, selected['limit_bytes'])
            after_membership, after_group = _group()
            if (after_membership, after_group) != (membership, group):
                raise ValueError('Maintenance cgroup changed during phase transition')
            record.update(_assess_current(config, phase, membership, group))
            if int((group / 'memory.max').read_text()) != selected['limit_bytes']:
                raise ValueError('Actual phase ceiling readback differs')
            record['limit_transition_verified'] = True
            record['limit_transition'] = {'from_bytes': before['previous_limit_bytes'], 'to_bytes': selected['limit_bytes']}
    record.update(phase=phase, recorded_at=c.now(),
                  memory_events=_events(group))
    if category and any(int(record['memory_events'].get(key, '0')) for key in ('oom', 'oom_kill', 'oom_group_kill')):
        record['ok'] = False
        record['reason'] = 'Maintenance cgroup recorded an OOM during this phase'
    c.R.mkdir(parents=True, exist_ok=True)
    target = c.R / ('preinstall-recovery-memory-admissions.json' if phase == 'recover-preinstall' else 'memory-admissions.json')
    history = c.read(target) if target.exists() else {'schema': 1, 'observations': []}
    if len(history['observations']) >= 256:
        raise ValueError('Memory admission history exceeds this transaction budget')
    history['observations'].append(record)
    c.atomic(target, history)
    if not record['ok']:
        raise RuntimeError('Maintenance deferred: insufficient memory for its enforced ceiling plus operating margin')
    return record
