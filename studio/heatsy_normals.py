"""Restore source corner-normal directions lost by Blender's custom-normal encoding.

This is an explicit, verified export fidelity step, not an import workaround.
Keep Blender's raw export for audit. No positions, topology, skin or anatomical
attribute values are edited. Preserve the multiset of normal-bearing corners,
including coincident or degenerate corners, and verify the resulting topology.
"""
from collections import defaultdict
import json
import numpy as np
from heatsy_gltf import load, accessor, save
from heatsy_validate import asset, compare, SOURCE, OUT, sha, cyclic


def main():
    final = OUT / 'roundtrip.glb'
    raw = OUT / 'blender-raw.glb'
    s, t = asset(SOURCE), asset(raw)
    precheck = compare(s, t, require_normals=False, write_artifacts=True)
    mapping = np.load(OUT / 'roundtrip-to-source.npy')
    # Geometrically coincident corners need not have the same normal. Associate
    # triangles using full anatomy and skin identity, then recover each corner.
    def signature(i):
        return (tuple(np.rint(s['positions'][i] / 1e-4).astype(int)),
                tuple(s['attrs']['_PART_ID'][i]), tuple(s['attrs']['_FIBER'][i]),
                tuple(s['attrs']['_TENDON'][i]), tuple(s['weights'][i]))
    identities = {}
    ids = np.array([identities.setdefault(signature(i), len(identities)) for i in range(len(s['positions']))])
    buckets = defaultdict(list)
    for tri in s['triangles']:
        buckets[cyclic(ids[tri])].append(tri)
    desired = np.full((len(t['positions']), 3), np.nan)
    new_triangles = []
    copies = []
    split_normals = []
    corner_vertices = {}
    sn = s['attrs']['NORMAL']
    sn = sn / np.linalg.norm(sn, axis=1)[:, None]
    for tri in t['triangles']:
        keys = ids[mapping[tri]]
        candidates = buckets[cyclic(keys)]
        assert candidates
        possibilities = []
        for ci, candidate in enumerate(candidates):
            for shift in range(3):
                rotated = np.roll(candidate, -shift)
                if np.array_equal(ids[rotated], keys):
                    normals = sn[rotated]
                    possibilities.append((ci, normals))
        assert possibilities
        # Degenerate/coincident corners can be indistinguishable by position.
        # Choose the closest shading correspondence, retain every source corner,
        # and split if one exported vertex needs multiple source directions.
        ci, normals = min(possibilities, key=lambda x: float(np.sum((x[1]-t['attrs']['NORMAL'][tri])**2)))
        corners = []
        for vertex, normal in zip(tri, normals):
            key = (int(vertex), tuple(normal))
            if key not in corner_vertices:
                if np.isnan(desired[vertex]).any():
                    desired[vertex] = normal
                    corner_vertices[key] = int(vertex)
                else:
                    corner_vertices[key] = len(desired) + len(copies)
                    copies.append(int(vertex))
                    split_normals.append(normal)
            corners.append(corner_vertices[key])
        new_triangles.append(corners)
        candidates.pop(ci)
    assert np.isfinite(desired).all()
    assert not any(buckets.values())
    g, blob = load(raw)
    blob = bytearray(blob)
    blob.extend(b'\0' * (-len(blob) % 4))
    primitive = g['meshes'][0]['primitives'][0]
    if copies:
        desired = np.vstack([desired, split_normals])
    from heatsy_gltf import DTYPES
    def replace(idx, values, component, kind, target):
        blob.extend(b'\0' * (-len(blob) % 4))
        data = values.astype(DTYPES[component]).tobytes()
        view = len(g['bufferViews'])
        g['bufferViews'].append({'buffer': 0, 'byteOffset': len(blob), 'byteLength': len(data), 'target': target})
        blob.extend(data)
        old = g['accessors'][idx]
        g['accessors'][idx] = {**old, 'bufferView': view, 'byteOffset': 0,
            'componentType': component, 'count': len(values), 'type': kind}
    for name, idx in primitive['attributes'].items():
        values = desired if name == 'NORMAL' else np.vstack([t['attrs'][name], t['attrs'][name][copies]])
        a = g['accessors'][idx]
        if name == 'NORMAL' or copies:
            replace(idx, values, a['componentType'], a['type'], 34962)
    replace(primitive['indices'], np.array(new_triangles).reshape(-1,1), 5125, 'SCALAR', 34963)
    save(final, g, blob)
    f = asset(final)
    for name in t['attrs']:
        if name != 'NORMAL':
            assert np.array_equal(t['attrs'][name][t['triangles']], f['attrs'][name][f['triangles']]), f'Unexpected {name} corner change'
    assert np.array_equal(t['ibm'], f['ibm'])
    compare(s, f)
    report = dict(status='PASS', raw_sha256=sha(raw), final_sha256=sha(final),
        changed='Source corner-normal directions normalized to unit float32; only lossless vertex splits if needed',
        additional_corner_splits=len(copies),
        before_max_angle_degrees=precheck['normal_max_angle_degrees'],
        triangles_matched_by='oriented geometry, anatomical identity and skin weights; every source normal-bearing corner is retained and verified in final topology',
        source_near_zero_area_triangles=int(np.sum(np.linalg.norm(np.cross(
            s['positions'][s['triangles'][:,1]]-s['positions'][s['triangles'][:,0]],
            s['positions'][s['triangles'][:,2]]-s['positions'][s['triangles'][:,0]]),axis=1)/2 < 1e-12)))
    (OUT / 'normal-preservation.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
