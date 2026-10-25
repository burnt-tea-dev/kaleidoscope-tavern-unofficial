"""Exact approved stable-author host declarations, without private implementation.

Existing profiles are unchanged. New author identities and public API versions
are admitted only with reviewed declaration digests, original/output hashes,
helper hashes and their explicitly compatible preceding source receipts.
"""
import hashlib
import json
from pathlib import Path

CATALOG = json.loads(Path(__file__).with_suffix('.json').read_text())
PROFILES = CATALOG['profiles']


def declaration_sha(spec):
    return hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def receipt(profile):
    result = {key: profile[key] for key in ['id', 'version', 'original_files', 'patched_files', 'copies']}
    if profile.get('removed_files'):
        result['removed_files'] = profile['removed_files']
    return result


def public_profiles():
    return {'public-api': CATALOG['public_api_profile'], **CATALOG.get('public_api_profiles', {})}


def public_predecessors(profile):
    # The original receipt remains the default. Only the named, unchanged
    # private declarations may use another reviewed public API predecessor.
    for name, accepted in CATALOG.get('public_api_predecessors', {}).items():
        if PROFILES.get(name) == profile:
            profiles = public_profiles()
            return [receipt(profiles[key]) for key in accepted]
    return [CATALOG['public_api']]


def validate_stable_source(profile, source):
    if source.get('owner') != profile['source_owner'] or source.get('archive_sha256') != profile['archive_sha256']:
        raise ValueError('stable host requires its exact preceding author source')
    prior = source.get('reviewed_extensions', [])
    if not isinstance(prior, list):
        raise ValueError('stable host preceding receipts must be a list')
    for name in profile['required_extensions']:
        expected = public_predecessors(profile) if name == 'public-api' else [receipt(PROFILES[name])]
        preceding = prior
        if name == 'public-api':
            public_ids = {p['id'] for p in public_profiles().values()} | {p['id'] for p in expected}
            preceding = [row for row in prior if isinstance(row, dict) and row.get('id') in public_ids]
            # A host has one public API source, not two sequential installations
            # or a mixture of a new identity and old helper hashes.
            if len(preceding) != 1:
                raise ValueError('stable host lacks exact preceding receipt: ' + name)
        def matches(row, option):
            if not isinstance(row, dict):
                return False
            if all(row.get(key) == value for key, value in option.items()):
                return True
            if name == 'public-api' and row.get('delegated_files'):
                from cookery_station_extension import validate_public_delegation
                try:
                    validate_public_delegation(row, option)
                    return True
                except (ValueError, KeyError, TypeError):
                    return False
            return False
        if not any(matches(row, option) for row in preceding for option in expected):
            raise ValueError('stable host lacks exact preceding receipt: ' + name)


def match_stable_profile(spec, owned_root=None, source=None):
    candidates = {**PROFILES, **public_profiles()}
    new_hosts = {p['host_uuid'] for p in candidates.values()}
    new_archives = {p.get('archive_sha256') for p in candidates.values()} - {None}
    if spec.get('host_uuid') not in new_hosts and spec.get('archive_sha256') not in new_archives:
        return None
    found = [(name, p) for name, p in candidates.items()
             if p['id'] == spec.get('id') and p['host_uuid'] == spec.get('host_uuid')]
    if not found:
        raise ValueError('unregistered stable host declaration')
    # Distinct owner releases may share the author UUID and extension ID.
    # Match the full reviewed declaration; never choose the newest by name.
    exact = [(name, profile) for name, profile in found if declaration_sha(spec) == profile['spec_sha256']]
    if len(exact) != 1:
        raise ValueError('stable host declaration differs from the exact reviewed profile: ' + spec['id'])
    name, profile = exact[0]
    if source is not None:
        validate_stable_source(profile, source)
    if owned_root is not None:
        for record in profile['copies'].values():
            path = owned_root / record['source']
            if path.is_symlink() or not path.resolve().is_relative_to(owned_root.resolve()) or not path.is_file():
                raise ValueError('stable host helper missing or outside owned source')
            if hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
                raise ValueError('stable host helper differs from the exact reviewed source')
    return profile


def current_author_profile(spec, owned_root=None, source=None):
    """A fresh owner uses one exact declaration, never an owner-version range."""
    profile = match_stable_profile(spec, owned_root, source)
    return profile if profile and profile.get('admission') in ('current-author-p55', 'current-author-p56', 'current-author-p57','current-author-p58') else None
