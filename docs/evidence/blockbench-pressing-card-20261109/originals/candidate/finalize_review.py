"""Finish the review artifact hash inventory without altering any input or fixture."""
from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent
manifest=json.loads((H/'manifest.json').read_text())
audit=json.loads((H/'independent-audit.json').read_text())
assert audit['status']=='passed' and not audit['runtime_applied'] and not audit['gui_reviewed']
assert hashlib.sha256((H/manifest['candidate']['file']).read_bytes()).hexdigest()==manifest['candidate']['after_sha256']
files={str(p.relative_to(H)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(H.rglob('*')) if p.is_file() and p.name!='artifact-sha256.json' and '__pycache__' not in p.parts}
(H/'artifact-sha256.json').write_text(json.dumps(files,indent=2)+'\n')
print('Finalized',len(files),'files; single candidate geometry; GUI pending.')
