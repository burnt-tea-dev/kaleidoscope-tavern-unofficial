"""Bounded pre-execution capacity projection; never a native admission receipt.

The CLI has already admitted its actual light cgroup and canonical runner.
Waiting only reads local source, controls and host memory. Actual native admission, fresh
capture, the maintenance lease and the full-family gates remain downstream.
"""
import copy
from pathlib import Path
import time

from family_update import common as c, memory_budget as m

STATE = 'native-capacity-wait-state.json'
INTERVAL = 60
OOM_EVENTS = ('oom', 'oom_kill', 'oom_group_kill')


class _WaitTimeout(RuntimeError):
    pass


def configured_seconds():
    if 'native_capacity_wait_seconds' not in c.CONFIG:
        return None
    value = c.CONFIG['native_capacity_wait_seconds']
    if type(value) is not int or not 1 <= value <= 7200:
        raise ValueError('native_capacity_wait_seconds must be an integer within 1..7200')
    return value


def _started():
    return any(path.exists() for path in [c.C, c.R / 'production-before', c.R / 'build-evidence.json',
                                         c.R / 'reviewed-family-receipt.json', c.R / 'deployment-result.json'])


def _lease_reference():
    if c.LEASE.is_symlink():
        raise ValueError('Maintenance lease changed into a symlink')
    return c.sha(c.LEASE) if c.LEASE.exists() else None


def _snapshot():
    if c.read(c.CONFIG_PATH) != c.CONFIG:
        raise RuntimeError('Loaded configuration differs from its current file bytes')
    return {'config_sha256': c.sha(c.CONFIG_PATH), 'sources': c.source_state(),
            'orchestration_sha256': c.orchestration_hashes(), 'lease_sha256': _lease_reference()}


def _unchanged(before, config):
    if c.CONFIG != config or _snapshot() != before or _started():
        raise RuntimeError('Configuration, source, runner or transaction identity changed while waiting')


def _observe(budget, expected_group=None):
    light, category = m.phase_budget(budget, 'update')
    native, native_category = m.phase_budget(budget, 'saved-world')
    if category != 'light' or native_category != 'native' or light['swap_limit_bytes'] != 0:
        raise ValueError('Capacity wait requires the reviewed phased, zero-swap budget')
    membership, group = m._group()
    info = group.stat()
    identity = (membership, info.st_dev, info.st_ino)
    if expected_group is not None and identity != expected_group:
        raise RuntimeError('Maintenance cgroup identity changed while waiting')
    maximum = (group / 'memory.max').read_text().strip()
    swap = (group / 'memory.swap.max').read_text().strip()
    if maximum != str(light['limit_bytes']) or swap != '0':
        raise RuntimeError('Actual light memory ceiling or zero-swap control changed while waiting')
    events = m._events(group)
    if any(key not in events or not events[key].isdecimal() for key in OOM_EVENTS):
        raise ValueError('Missing or invalid maintenance OOM controls')
    if any(int(events[key]) for key in OOM_EVENTS):
        raise RuntimeError('Maintenance cgroup recorded an OOM; do not retry this wait')
    # The existing assessor validates actual membership/current/controls. Zero
    # resident-anon credit keeps even the light recheck conservative.
    record = m.assess_phase(budget, 'update', Path('/proc/meminfo').read_text(), membership,
                            int((group / 'memory.current').read_text()), maximum, swap,
                            resident_anon=0)
    if not record['ok']:
        raise RuntimeError('Actual light memory budget no longer has its operating margin')
    required = native['limit_bytes'] + native['reserve_bytes'] + m.RESIDENT_ACCOUNTING_PAD
    return identity, {'available_bytes': record['available_bytes'], 'required_available_bytes': required,
                      'native_limit_bytes': native['limit_bytes'], 'reserve_bytes': native['reserve_bytes'],
                      'cushion_bytes': m.RESIDENT_ACCOUNTING_PAD, 'self_resident_credit_bytes': 0,
                      'light_limit_bytes': light['limit_bytes'], 'swap_limit_bytes': 0,
                      'memory_events': events, 'projection_fits': record['available_bytes'] >= required}


def wait_if_configured():
    seconds = configured_seconds()
    if seconds is None or _started():
        return None  # Existing transactions retain their original fresh gates.
    target = c.R / STATE
    if target.exists() or target.is_symlink():
        raise RuntimeError('This capacity wait already ran; do not automatically retry its output')
    c.lease_available()  # Read-only: never wait with an active maintenance lease.
    config = copy.deepcopy(c.CONFIG)
    before = _snapshot()
    start = time.monotonic()
    deadline = start + seconds
    group = None
    state = {'schema': 1, 'kind': 'native_capacity_wait_state', 'receipt': False,
             'scope': 'pre-execution-capacity-projection-only', 'native_admission': False,
             'live_mutated': False, 'limit_changed': False, 'wait_seconds': seconds,
             'poll_interval_seconds': INTERVAL, 'observations': 0,
             'config_sha256': before['config_sha256']}

    def write(status):
        state.update(state=status, recorded_at=c.now(), elapsed_seconds=max(0, time.monotonic() - start))
        c.R.mkdir(parents=True, exist_ok=True)
        c.atomic(target, state)

    try:
        while True:
            _unchanged(before, config)
            group, observation = _observe(config['memory_budget'], group)
            state.update(observation)
            state['observations'] += 1
            if time.monotonic() > deadline or (time.monotonic() >= deadline and not observation['projection_fits']):
                write('timed_out')
                raise _WaitTimeout('Native capacity wait timed out before any candidate or lease; no automatic retry')
            if observation['projection_fits']:
                break
            write('waiting')
            time.sleep(min(INTERVAL, max(0, deadline - time.monotonic())))
        # These normal remote/source/server-binding reads occur after the loop,
        # never during waiting. A projection cannot replace real native gates.
        c.verify_canonical_runner()
        _unchanged(before, config)
        _, final = _observe(config['memory_budget'], group)
        if not final['projection_fits']:
            raise RuntimeError('Capacity regressed during final canonical recheck; do not retry this wait')
        state.update(final)
        write('projection_available')
        return state
    except _WaitTimeout as error:
        raise RuntimeError(str(error)) from None
    except (AssertionError, OSError, RuntimeError, ValueError) as error:
        state['reason'] = str(error)[:500]
        write('rejected')
        raise
