"""Exact-hash supersession of old preservation guards; unrelated mutations fail.
Before hashes are verified against a pinned source checkout in check_launch.py.
Creative metadata projection is composed with (not replaced by) this ledger.
"""
import hashlib,json
from functools import lru_cache
from pathlib import Path
from baseline_reference import previous_bytes,additions as baseline_additions
from creative.historical import LegacyMenuProjection
from efficiency.reference import apply_efficiency_reference
ROOT=Path(__file__).resolve().parents[1]
@lru_cache(maxsize=1)
def reference():
    # Use the same validated supersession chain as check_launch.py. Preserve the
    # original before/beforeProjected hashes; do not bypass historical guards.
    original=json.loads((ROOT/'data/launch-repair-reference.json').read_text())
    return apply_efficiency_reference(original,ROOT)
@lru_cache(maxsize=1)
def changes():
    return reference()['reviewedChanges']
@lru_cache(maxsize=1)
def projection():return LegacyMenuProjection(ROOT)
def historical_digest(path,projected=False):
    path=Path(path);name=path.relative_to(ROOT).as_posix()
    removed=reviewed_removals().get(name)
    if removed:
        assert removed['before'] is not None,('Retired addition has no historical file',name)
        return removed['beforeProjected'] if projected else removed['before']
    actual=hashlib.sha256(previous_bytes(ROOT,path)).hexdigest();row=changes().get(name)
    if row:
        assert actual==row['after'],('Reviewed source changed after audit',name)
        return row['beforeProjected'] if projected else row['before']
    return hashlib.sha256(projection().read_bytes(path)).hexdigest() if projected else actual

@lru_cache(maxsize=1)
def reviewed_additions():
    rows=reference()['newRuntimeFiles']
    for name,digest in rows.items():assert hashlib.sha256(previous_bytes(ROOT,ROOT/name)).hexdigest()==digest,('Reviewed addition changed',name)
    removed=reviewed_removals()
    assert not (set(rows)&set(removed)), 'A file cannot be both a current addition and a removal'
    return {**rows,**{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in baseline_additions(ROOT) if name not in removed}}

@lru_cache(maxsize=1)
def reviewed_removals():
    rows=reference().get('removedRuntimeFiles',{})
    for name,row in rows.items():
        assert not (ROOT/name).exists(),('Reviewed removed file returned',name)
        assert row['reason']
        if row['before'] is None and row['beforeProjected'] is None:
            assert name in baseline_additions(ROOT),('Removed addition lacks historical review',name)
        else:
            assert isinstance(row['before'],str) and isinstance(row['beforeProjected'],str)
            assert len(row['before'])==64 and len(row['beforeProjected'])==64
    return rows

@lru_cache(maxsize=1)
def current_contract_sources():
    # Validate this current domain before retiring its exact paths from old
    # aggregate preservation checks. Other paths keep the historical guards.
    from check_potion_bottle_visual import check as check_potion_visual, runtime_sources as potion_runtime_sources
    from foundation.source_contract import check as check_foundation, runtime_sources as foundation_runtime_sources
    from current_extension_source_contract import check as check_extensions, runtime_sources as extension_runtime_sources
    from creative.catalog import check_current as check_creative, runtime_sources as creative_runtime_sources
    check_potion_visual()
    check_foundation(ROOT)
    check_extensions(ROOT)
    check_creative(ROOT)
    return potion_runtime_sources()|foundation_runtime_sources()|extension_runtime_sources()|creative_runtime_sources()

def historical_files(prefix):
    current=current_contract_sources()
    paths={p for p in (ROOT/prefix).rglob('*') if p.is_file() and p.relative_to(ROOT).as_posix() not in reviewed_additions() and p.relative_to(ROOT).as_posix() not in current}
    paths.update(ROOT/name for name,row in reviewed_removals().items() if row['before'] is not None and name.startswith(prefix+'/'))
    return sorted(paths)
