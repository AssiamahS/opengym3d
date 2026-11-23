"""Small independent GLB decoder for the compatibility checks (numpy only)."""
import json
import struct
from pathlib import Path
import numpy as np

DTYPES = {5120: 'i1', 5121: 'u1', 5122: '<i2', 5123: '<u2', 5125: '<u4', 5126: '<f4'}
WIDTHS = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def load(path):
    data = Path(path).read_bytes()
    magic, version, length = struct.unpack_from('<4sII', data)
    assert magic == b'glTF' and version == 2 and length == len(data)
    size, typ = struct.unpack_from('<I4s', data, 12)
    assert typ == b'JSON'
    g = json.loads(data[20:20 + size])
    offset = 20 + size
    size, typ = struct.unpack_from('<I4s', data, offset)
    assert typ == b'BIN\0'
    return g, data[offset + 8:offset + 8 + size]


def accessor(g, blob, index, decoded=True):
    a = g['accessors'][index]
    assert 'sparse' not in a, 'Sparse accessor requires explicit support'
    v = g['bufferViews'][a['bufferView']]
    assert v.get('buffer', 0) == 0
    dtype = np.dtype(DTYPES[a['componentType']])
    width = WIDTHS[a['type']]
    array = np.ndarray((a['count'], width), dtype=dtype, buffer=blob,
        offset=v.get('byteOffset', 0) + a.get('byteOffset', 0),
        strides=(v.get('byteStride', width * dtype.itemsize), dtype.itemsize)).copy()
    if decoded and a.get('normalized', False):
        maximum = np.iinfo(dtype).max
        array = np.maximum(array.astype(np.float64) / maximum, -1)
    return array


def save(path, g, blob):
    blob = bytes(blob)
    g['buffers'] = [{'byteLength': len(blob)}]
    meta = json.dumps(g, separators=(',', ':')).encode()
    meta += b' ' * (-len(meta) % 4)
    blob += b'\0' * (-len(blob) % 4)
    Path(path).write_bytes(struct.pack('<4sII', b'glTF', 2, 28 + len(meta) + len(blob))
        + struct.pack('<I4s', len(meta), b'JSON') + meta
        + struct.pack('<I4s', len(blob), b'BIN\0') + blob)


def fixture(path, order, decoded_custom=False):
    g = {'asset': {'version': '2.0'}, 'scene': 0, 'scenes': [{'nodes': [0]}],
         'nodes': [{'mesh': 0}], 'accessors': [], 'bufferViews': []}
    blob = bytearray()
    def add(values, component, kind, normalized=False):
        blob.extend(b'\0' * (-len(blob) % 4))
        data = np.array(values, dtype=DTYPES[component]).tobytes()
        index = len(g['accessors'])
        g['bufferViews'].append({'buffer': 0, 'byteOffset': len(blob), 'byteLength': len(data)})
        g['accessors'].append({'bufferView': index, 'componentType': component,
            'type': kind, 'count': 3, 'normalized': normalized})
        blob.extend(data)
        return index
    position = add([[0, 0, 0], [1, 0, 0], [0, 1, 0]], 5126, 'VEC3')
    g['accessors'][position].update(min=[0, 0, 0], max=[1, 1, 0])
    values = {'_FIBER': ([[-128, 64, 127], [32, -64, 0], [127, 1, -127]], 5120, 'VEC3', True),
              '_TENDON': ([0, 128, 255], 5121, 'SCALAR', True),
              '_PART_ID': ([1, 2, 238], 5121, 'SCALAR', False)}
    ids = {}
    for name in order:
        data, component, kind, normalized = values[name]
        if decoded_custom:
            data = np.array(data, dtype=np.float64)
            if normalized:
                data = np.maximum(-1, data / np.iinfo(DTYPES[component]).max)
            component, normalized = 5126, False
        ids[name] = add(data, component, kind, normalized)
    attrs = {'POSITION': position, **{k: ids[k] for k in order}}
    g['meshes'] = [{'primitives': [{'attributes': attrs}]}]
    save(path, g, blob)
