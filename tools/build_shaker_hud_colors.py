#!/usr/bin/env python3
"""Complete literal Java color controls without changing progress or expiry keys.

The checked-in white slot sprite is the original Java rhombus mask. Generated
RGB texels multiply that source and retain its alpha, as ShakerOverlay does.
"""
import json
from pathlib import Path
from formatting_hud_ui import snapshot_panel
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
RP = ROOT / 'runtime/RP'
COLORS = [0xff55ff, 0x5555ff, 0xffaa00, 0x55ff55, 0xffff55, 0xff5555, 0xffffff,
          0x000000, 0x0000aa, 0x00aa00, 0x00aaaa, 0xaa0000, 0xaa00aa, 0xaaaaaa,
          0x555555, 0x55ffff]

def code(n):return ''.join('§'+c for c in f'{n:02x}')

def main():
    path = RP / 'ui/kt_tavern_hud.json'
    hud = json.loads(path.read_text())
    panel = hud['kt_mixology_packet']['controls'][0]['slots']
    slots = panel['controls']
    original = {next(iter(control)): next(iter(control.values())) for control in slots if '@kaleidoscope_tavern_hud.kt_mixology_slot' in next(iter(control))}
    mask = Image.open(RP / 'textures/ui/kt_mixology/slots/700.png').convert('RGBA').crop((0, 0, 16, 16))
    updated = []
    for slot in range(3):
        for color in range(17):
            key = f'kt_slot_{slot}_{color}@kaleidoscope_tavern_hud.kt_mixology_slot'
            control = original.get(key, {}).copy()
            texture = ['0', '0', '0']
            texture[slot] = str(color) if color < 8 else f'x{color:02d}'
            name = ''.join(texture)
            control.update(offset=[slot * 20, 0], uv=[slot * 20, 0],
                           texture=f'textures/ui/kt_mixology/slots/{name}',
                           visible=f"(not (($kt_text - '§r§1{code(slot)}{code(color)}§r') = $kt_text))")
            control.pop('bindings',None);control.pop('property_bag',None)
            updated.append({key: control})
            if color >= 8:
                rgb = tuple(COLORS[color - 1] >> shift & 255 for shift in (16, 8, 0))
                icon = ImageChops.multiply(mask, Image.new('RGBA', mask.size, (*rgb, 255)))
                image = Image.new('RGBA', (56, 16))
                image.paste(icon, (slot * 20, 0))
                image.save(RP / f'textures/ui/kt_mixology/slots/{name}.png')
    panel['controls'] = updated
    snapshot_panel(panel,'kt_slot','§r§0§r§2','§r§0§r§2§r§f§f§r','kt_text')
    path.write_text(json.dumps(hud, ensure_ascii=False, separators=(',', ':')) + '\n')
    print('Generated 51 literal controls: three slots, all 16 Java colors and empty')

if __name__ == '__main__':
    main()
