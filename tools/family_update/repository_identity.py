"""Reviewed 2026-10-19 owner transfer; historical logical keys stay immutable."""

OWNER = {'login': 'burnt-tea-dev', 'id': 344456559, 'type': 'Organization'}
TARGETS = {
    'kaleidoscope-tavern-unofficial': (1377171148, False),
    'kaleidoscope-grilling-unofficial': (1377218440, False),
    'kaleidoscope-world-liquor-unofficial': (1385218112, False),
    'senluo-family-integration-private': (1406868911, True),
}


def target(repository):
    assert isinstance(repository, str) and repository.count('/') == 1, 'Unknown canonical repository'
    owner, name = repository.split('/')
    assert owner in ('casama233', OWNER['login']) and name in TARGETS, 'Unreviewed canonical repository'
    identity, private = TARGETS[name]
    return {'repository': OWNER['login'] + '/' + name, 'repository_id': identity,
            'private': private, 'owner': dict(OWNER)}


def current_name(repository):
    return target(repository)['repository']


def verify_record(record, repository):
    """PR/run repository records must name the new target and the original ID."""
    expected = target(repository)
    assert record['full_name'] == expected['repository'], 'Canonical repository owner/name differs'
    assert type(record['id']) is int and record['id'] == expected['repository_id'], 'Canonical repository ID differs'
    return expected


def verify_remote(record, repository):
    expected = verify_record(record, repository)
    assert record['private'] is expected['private'], 'Canonical repository visibility differs'
    assert all(record['owner'].get(key) == value for key, value in OWNER.items()), 'Canonical repository organization differs'
    return expected


def verify_ci(repository, environ):
    """Verify the Actions event, including an explicit cross-repository child gate."""
    import json
    from pathlib import Path
    expected = target(repository)
    if environ.get('GITHUB_REPOSITORY'):
        assert environ['GITHUB_REPOSITORY'] == expected['repository'], 'Wrong CI repository'
    if environ.get('GITHUB_REPOSITORY_ID'):
        assert environ['GITHUB_REPOSITORY_ID'] == str(expected['repository_id']), 'Wrong CI repository ID'
    if environ.get('GITHUB_ACTIONS') == 'true':
        assert environ.get('GITHUB_REPOSITORY_OWNER') == OWNER['login'], 'Wrong CI organization'
        assert environ.get('GITHUB_REPOSITORY_OWNER_ID') == str(OWNER['id']), 'Wrong CI organization ID'
        event_path = Path(environ['GITHUB_EVENT_PATH'])
        assert event_path.stat().st_size <= 4 * 1024**2
        record = json.loads(event_path.read_text())['repository']
        # The parent event is preserved, never relabelled as a peer's event.
        parent = record['full_name'] if environ.get('SENLUO_SOURCE_GATE') == '1' else repository
        verify_remote(record, parent)
    return expected
