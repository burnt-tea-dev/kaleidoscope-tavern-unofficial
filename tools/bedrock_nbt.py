"""Lossless little-endian NBT for stopped-world migration.

Bedrock also stores opaque bytes in TAG_String (notably actor StorageKey).
nbtlib's default UTF-8 replacement decoder destroys those bytes. Keep its
typed values, but decode/encode string payloads and names with surrogateescape.
The caller supplies a strict stream; no global nbtlib codecs are changed.
"""
import io
import struct

import nbtlib


def _read_string(stream):
    length = struct.unpack('<H', stream.read(2))[0]
    return stream.read(length).decode('utf-8', 'surrogateescape')


def _write_string(value, stream):
    raw = value.encode('utf-8', 'surrogateescape')
    stream.write(struct.pack('<H', len(raw)))
    stream.write(raw)


def _read_payload(tag_id, stream):
    if tag_id == 8:
        return nbtlib.String(_read_string(stream))
    if tag_id == 9:
        subtype, length = struct.unpack('<Bi', stream.read(5))
        if length < 0 or (subtype == 0 and length):
            raise ValueError('invalid NBT list length/subtype')
        tag = nbtlib.Base.get_tag(subtype)
        return nbtlib.List[tag](_read_payload(subtype, stream) for _ in range(length))
    if tag_id == 10:
        result = nbtlib.Compound()
        while True:
            child_id = stream.read(1)[0]
            if child_id == 0:
                return result
            name = _read_string(stream)
            if name in result:
                raise ValueError('duplicate NBT compound name')
            result[name] = _read_payload(child_id, stream)
    if tag_id not in (1, 2, 3, 4, 5, 6, 7, 11, 12):
        raise ValueError('invalid NBT payload type')
    if tag_id in (7, 11, 12):
        start = stream.tell()
        if struct.unpack('<i', stream.read(4))[0] < 0:
            raise ValueError('negative NBT array length')
        stream.seek(start)
    return nbtlib.Base.get_tag(tag_id).parse(stream, byteorder='little')


def _write_payload(tag, stream):
    if isinstance(tag, nbtlib.String):
        _write_string(tag, stream)
    elif isinstance(tag, nbtlib.List):
        stream.write(struct.pack('<Bi', tag.subtype.tag_id, len(tag)))
        for child in tag:
            _write_payload(child, stream)
    elif isinstance(tag, nbtlib.Compound):
        for name, child in tag.items():
            stream.write(bytes([child.tag_id]))
            _write_string(name, stream)
            _write_payload(child, stream)
        stream.write(b'\0')
    else:
        tag.write(stream, byteorder='little')


def encode_root(tag):
    stream = io.BytesIO()
    stream.write(b'\x0a')
    _write_string(tag.root_name, stream)
    _write_payload(tag, stream)
    return stream.getvalue()


def parse_root(stream):
    """Read one root, rejecting any representation that cannot round-trip."""
    start = stream.tell()
    if stream.read(1) != b'\x0a':
        raise ValueError('expected NBT compound root')
    name = _read_string(stream)
    tag = nbtlib.File(_read_payload(10, stream), root_name=name)
    end = stream.tell()
    if encode_root(tag) != stream.getvalue()[start:end]:
        raise ValueError('NBT root cannot be preserved byte-for-byte')
    return tag
