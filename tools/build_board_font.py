#!/usr/bin/env python3
"""Build Tavern Board Font from the retained GNU Unifont 15.0.06 source.

Requires Pillow. --metrics-only leaves PNG atlases and client bindings untouched.
Identical complete pages share a texture; logical pages and 16x16 UV cells stay.
"""
import argparse
import gzip
import hashlib
import json
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'art/fonts/unifont-15.0.06.hex.gz'
SOURCE_SHA256 = '9ad23271a7b2c904a33c1fc97c97a5909016533efac192957eb6b7900df54fb3'
ENTITY = 'runtime/RP/entity/board_glyph_visual.entity.json'
METRICS = 'runtime/BP/scripts/data/board-font.js'
ATLAS_DIRECTORY = 'runtime/RP/textures/board_font'


@lru_cache(maxsize=2)
def source_layout(compressed):
    """Pure source conversion shared by generation and the current contract."""
    assert hashlib.sha256(compressed).hexdigest() == SOURCE_SHA256, 'GNU Unifont source differs'
    glyphs, advances = {}, {}
    # Preserve full width for East Asian ranges used by the original layout.
    ranges = [(0x3001, 0x30ff, 15), (0x3200, 0x9fff, 15), (0xac00, 0xd7af, 14),
              (0xf900, 0xfaff, 15), (0xff01, 0xff5e, 15)]
    for line in gzip.decompress(compressed).decode().splitlines():
        code, data = line.split(':'); cp = int(code, 16)
        if cp > 65535 or 0xe000 <= cp <= 0xf8ff:
            continue
        width = len(data) // 4
        im = Image.frombytes('1', (width, 16), bytes.fromhex(data)).convert('L')
        box = im.getbbox(); left, right = (box[0], box[2] - 1) if box else (0, -1)
        for first, last, edge in ranges:
            if first <= cp <= last:
                left, right = 0, edge; break
        cell = Image.new('L', (16, 16)); w = right - left + 1
        if w > 0:
            cell.paste(im.crop((left, 0, right + 1, 16)), (0, 0))
        glyphs[cp] = cell; advances[cp] = w // 2 + 1
    for cp, advance in [(32, 4), (0x200c, 0)]:
        glyphs[cp] = Image.new('L', (16, 16)); advances[cp] = advance
    missing = Image.new('L', (16, 16))
    ImageDraw.Draw(missing).rectangle((0, 0, 9, 13), outline=255, width=2)
    pages, textures, atlases = {}, {}, {}
    for page in range(256):
        alpha = Image.new('L', (256, 256))
        for low in range(256):
            alpha.paste(glyphs.get(page * 256 + low, missing), ((low % 16) * 16, (low // 16) * 16))
        pixels = alpha.tobytes()
        canonical = pages.setdefault(pixels, page)
        if canonical == page:
            out = Image.new('RGBA', (256, 256), (255, 255, 255, 0)); out.putalpha(alpha)
            atlases[f'{ATLAS_DIRECTORY}/glyph_{page:02X}.png'] = out.tobytes()
        textures[f'page_{page}'] = f'textures/board_font/glyph_{canonical:02X}'
    values = [advances.get(cp, 6) for cp in range(65536)]
    assert len(values) == 65536 and all(0 <= value <= 9 for value in values), 'Invalid board advances'
    metrics = ('// Tavern Board Font: GNU Unifont 15.0.06 derived advances, in Java font-pixel units.\n'
               + "const FONT_ADVANCE_DIGITS='" + ''.join(str(value) for value in values) + "';\n"
               + 'export const fontAdvance=code=>FONT_ADVANCE_DIGITS.charCodeAt(code)-48;\n'
               + 'export const fontBoldOffset=()=>.5;\n')
    return textures, atlases, metrics


def layout(root=ROOT):
    return source_layout((Path(root) / SOURCE).read_bytes())


def generate(root=ROOT, *, metrics_only=False):
    root = Path(root)
    textures, atlases, metrics = layout(root)
    if not metrics_only:
        for page in range(256):
            path = root / ATLAS_DIRECTORY / f'glyph_{page:02X}.png'
            pixels = atlases.get(path.relative_to(root).as_posix())
            if pixels is None:
                path.unlink(missing_ok=True)
            else:
                Image.frombytes('RGBA', (256, 256), pixels).save(path, optimize=True)
        entity_path = root / ENTITY
        entity = json.loads(entity_path.read_text())
        entity['minecraft:client_entity']['description']['textures'] = textures
        entity_path.write_text(json.dumps(entity, ensure_ascii=False, indent=2) + '\n')
    (root / METRICS).write_text(metrics)
    return len(atlases)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metrics-only', action='store_true', help='regenerate only the JavaScript glyph metric tables')
    args = parser.parse_args()
    count = generate(metrics_only=args.metrics_only)
    print('Board font metrics generated; ' + ('PNG atlases unchanged.' if args.metrics_only else
          f'256 logical GNU Unifont pages share {count} distinct atlases.') + ' No Minecraft bitmap-provider glyphs.')
