"""Bounded fixture audit, not a Minecraft rendering or runtime acceptance test."""
from pathlib import Path
import base64
import hashlib
import json
import math
import zipfile

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'blockbench-20261108' / 'scenes'
source = json.loads((HERE / 'java-signature-cocktail.json').read_text())
hashes = json.loads((HERE / 'scene-entry-sha256.json').read_text())
offset = [-15, 0, -8]  # Java block centring plus the review-only left translation.


def near(a, b):
    assert len(a) == len(b)
    assert all(math.isclose(x, y, abs_tol=1e-10) for x, y in zip(a, b)), (a, b)


def without_id(element):
    return {k: v for k, v in element.items() if k != 'uuid'}


report = []
with zipfile.ZipFile(HERE / 'scenes.zip') as archive:
    for frame in range(6):
        name = f'signature-rescale-frame-{frame}.bbmodel'
        raw = archive.read('scenes/' + name)
        assert hashlib.sha256(raw).hexdigest() == hashes[name]
        new = json.loads(raw)
        old = json.loads((OLD / f'signature-frame-{frame}.bbmodel').read_text())
        assert len(new['elements']) == len(old['elements'])
        scaled = []
        for i, authored in enumerate(source['elements']):
            cube = new['elements'][i]
            assert cube['name'] == f'Java element {i}'
            rotation = authored.get('rotation', {})
            pivot = rotation.get('origin', [8, 0, 8])
            # These are the only two source rescale elements, both Y/-45.
            # Use sqrt(2), independently of the builder's cosine expression.
            if rotation.get('rescale'):
                assert i in (13, 14)
                assert rotation['axis'] == 'y' and rotation['angle'] == -45
                scale = [math.sqrt(2), 1, math.sqrt(2)]
                scaled.append(i)
            else:
                scale = [1, 1, 1]
            for endpoint in ('from', 'to'):
                near(cube[endpoint], [pivot[k] + (authored[endpoint][k] - pivot[k]) * scale[k] + offset[k] for k in range(3)])
            near(cube['origin'], [pivot[k] + offset[k] for k in range(3)])
            assert cube['rotation'] == old['elements'][i]['rotation']
            assert cube['faces'] == old['elements'][i]['faces']
            assert cube['shade'] == authored.get('shade', True)
            assert not cube.get('rescale'), 'Baked bounds must not be scaled a second time.'
        assert scaled == [13, 14]
        near([new['elements'][13]['to'][0] - new['elements'][13]['from'][0]], [5 * math.sqrt(2)])
        near([new['elements'][14]['to'][2] - new['elements'][14]['from'][2]], [5 * math.sqrt(2)])
        count = len(source['elements'])
        assert [without_id(e) for e in new['elements'][count:]] == [without_id(e) for e in old['elements'][count:]]
        assert [without_id(g) for g in new['groups']] == [without_id(g) for g in old['groups']]
        assert len(new['textures']) == len(old['textures'])
        for a, b in zip(new['textures'], old['textures']):
            assert without_id(a) == without_id(b)
            base64.b64decode(a['source'].split(',', 1)[1], validate=True)
        report.append({'frame': frame, 'java_elements': count, 'rescale_elements': scaled, 'baked_width': 5 * math.sqrt(2), 'runtime_elements_unchanged': len(new['elements']) - count, 'texture_bytes_unchanged': True})
print(json.dumps({'passed': True, 'scope': 'review fixture bounds, pivots, rotations, face UV, shade, texture bytes and unchanged native-side data; not client rendering', 'frames': report}, indent=2))
