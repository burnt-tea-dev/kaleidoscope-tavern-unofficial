"""Shared opaque source-texel geometry and RGB material wiring.

Keeps the source UV footprint, including transparent holes and face winding.
The generated surfaces are resource inputs, not native-client render evidence.
"""
import copy
import math
from collections import defaultdict


def face_point(cube, face, s, t):
    x, y, z = cube['origin']
    dx, dy, dz = cube['size']
    return {'north': [x + s * dx, y + (1-t) * dy, z],
            'south': [x + (1-s) * dx, y + (1-t) * dy, z + dz],
            'east': [x, y + (1-t) * dy, z + (1-s) * dz],
            'west': [x + dx, y + (1-t) * dy, z + s * dz],
            'up': [x + s * dx, y + dy, z + (1-t) * dz],
            'down': [x + s * dx, y, z + t * dz]}[face]


def boundaries(start, extent):
    assert extent != 0
    low, high = sorted((start, start + extent))
    return sorted({0.0, 1.0, *((pixel-start)/extent
                            for pixel in range(math.floor(low)+1, math.ceil(high))
                            if 0 < (pixel-start)/extent < 1)})


def rectangles(grid):
    """Merge only adjacent equal-color source texels on one original face."""
    seen = set()
    for y, row in enumerate(grid):
        for x, color in enumerate(row):
            if color is None or (x, y) in seen:
                continue
            right = x + 1
            while right < len(row) and grid[y][right] == color and (right, y) not in seen:
                right += 1
            bottom = y + 1
            while bottom < len(grid) and all(grid[bottom][xx] == color and (xx, bottom) not in seen for xx in range(x, right)):
                bottom += 1
            seen.update((xx, yy) for yy in range(y, bottom) for xx in range(x, right))
            yield color, x, y, right, bottom


def partition_texels(cubes, source, frame_height, frame_count):
    assert source.height == frame_height * frame_count
    groups = defaultdict(lambda: [[] for _ in range(frame_count)])
    for frame in range(frame_count):
        image = source.crop((0, frame * frame_height, source.width, (frame + 1) * frame_height))
        for cube in cubes:
            assert not cube.get('mirror') and not cube.get('inflate')
            for face, mapping in cube['uv'].items():
                assert not mapping.get('uv_rotation')
                u, v = mapping['uv']
                du, dv = mapping['uv_size']
                ss, ts = boundaries(u, du), boundaries(v, dv)
                grid = []
                for t0, t1 in zip(ts, ts[1:]):
                    row = []
                    for s0, s1 in zip(ss, ss[1:]):
                        pixel = image.getpixel((min(image.width-1, max(0, math.floor(u+du*(s0+s1)/2))),
                                                min(image.height-1, max(0, math.floor(v+dv*(t0+t1)/2)))))
                        assert pixel[3] in (0, 255), 'Partial-alpha source needs a separately reviewed renderer'
                        row.append(tuple(pixel[:3]) if pixel[3] else None)
                    grid.append(row)
                for color, x0, y0, x1, y1 in rectangles(grid):
                    points = [face_point(cube, face, s, t) for s in (ss[x0], ss[x1]) for t in (ts[y0], ts[y1])]
                    low = [round(min(p[a] for p in points), 9) for a in range(3)]
                    high = [round(max(p[a] for p in points), 9) for a in range(3)]
                    box = {key: copy.deepcopy(cube[key]) for key in ('pivot', 'rotation') if key in cube}
                    box.update(origin=low, size=[round(b-a, 9) for a, b in zip(low, high)],
                               uv={face: {'uv': [.5, .5], 'uv_size': [1, 1]}})
                    groups[color][frame].append(box)
    assert len(groups) <= 16, 'Unexpected source colour expansion exceeds the reviewed draw budget'
    return dict(sorted(groups.items()))


def tint_controller(geometry_names, color, clock=None):
    """One material route for both animated cups and static potion liquid."""
    if clock is None:
        assert len(geometry_names) == 1
        result = {'geometry': geometry_names[0]}
    else:
        result = {'arrays': {'geometries': {'Array.frames': geometry_names}},
                  'geometry': f'Array.frames[{clock}]'}
    result.update(materials=[{'*': 'Material.liquid_rgb'}], textures=['Texture.rgb_opaque'],
                  overlay_color={**{key: f"math.floor(query.property('kt_art:{prop}') * {source} / 255) / 255"
                                    for key, prop, source in zip(('r', 'g', 'b'), ('red', 'green', 'blue'), color)}, 'a': 1})
    return result
