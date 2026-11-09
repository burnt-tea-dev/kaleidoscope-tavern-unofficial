"""Complete bounded resource consumer proof, against saved canonical Git blob names."""
import hashlib
from pathlib import Path
from path_guard import safe_path, reject_symlinks

def verify_census(package, payload=None):
    reject_symlinks(package/'census')
    expected = {}
    tree = package/'originals/candidate/provenance/canonical-runtime-tree.txt'
    for line in tree.read_text().splitlines():
        meta, name = line.split('\t')
        if name.startswith(('runtime/RP/entity/', 'runtime/RP/attachables/')) and name.endswith('.json'):
            safe_path(package/'census',name)
            assert name not in expected
            expected[name] = meta.split()[2]
    assert len(expected) == 129, 'Pinned census must include every entity and attachable JSON'
    if payload is None:
        payload = {str(p.relative_to(package/'census')):safe_path(package/'census',str(p.relative_to(package/'census'))).read_bytes() for p in (package/'census').rglob('*') if p.is_file()}
    assert set(payload) == set(expected), 'Missing or extra canonical resource definitions'
    consumers = []
    for name, data in payload.items():
        blob = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        assert blob == expected[name], ('Canonical blob mismatch', name)
        if 'geometry.kt_runtime.pressing_card' in data.decode():
            consumers.append(name)
    targets = [f'runtime/RP/entity/runtime_pressing_tub_ingredients{("_"+str(i)) if i else ""}.entity.json' for i in range(8)]
    assert sorted(consumers) == sorted(targets)
    for name in targets:
        assert payload[name] == safe_path(package/'originals/candidate/inputs/current',name).read_bytes()
    return consumers
