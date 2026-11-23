"""Independent, topology-aware static roundtrip proof. Never compares vertex indices."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from heatsy_gltf import load, accessor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/heatsy-probe/compatibility'
SOURCE = ROOT / 'work/heatsy/model/body_superficial.app5m.glb'
SOURCE_HASH = 'ce9859de013c2ee9713dbe3158275208b57be1b4ff31957eca87195b991c0ab1'
# Geometry threshold is 1/10 of the source's 0.1 mm position quantization.
# Attribute threshold is ~one float32 ULP over [-1, 1], far below an 8-bit step.
POS_TOL = 1e-5
ATTR_TOL = 1e-7
WEIGHT_TOL = 2e-7


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def matrices(g):
    local = []
    for n in g['nodes']:
        if 'matrix' in n:
            m = np.array(n['matrix']).reshape(4, 4).T
        else:
            x, y, z, w = n.get('rotation', [0, 0, 0, 1])
            m = np.eye(4)
            m[:3, :3] = [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                         [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                         [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]
            m[:3, :3] *= n.get('scale', [1, 1, 1])
            m[:3, 3] = n.get('translation', [0, 0, 0])
        local.append(m)
    world = {}
    parents = {}
    for i, n in enumerate(g['nodes']):
        for c in n.get('children', []):
            assert c not in parents
            parents[c] = i
    def visit(i):
        if i not in world:
            world[i] = (visit(parents[i]) if i in parents else np.eye(4)) @ local[i]
        return world[i]
    for i in range(len(local)):
        visit(i)
    return np.array(local), world, parents


def asset(path):
    g, b = load(path)
    assert len(g['meshes']) == len(g['skins']) == 1
    assert len(g['meshes'][0]['primitives']) == 1
    p = g['meshes'][0]['primitives'][0]
    assert p.get('mode', 4) == 4 and not p.get('targets')
    attrs = {k: accessor(g, b, i).astype(np.float64) for k, i in p['attributes'].items()}
    loc, world, parents = matrices(g)
    skin = g['skins'][0]
    names = [g['nodes'][i]['name'] for i in skin['joints']]
    assert len(set(names)) == len(names)
    ibm = accessor(g, b, skin['inverseBindMatrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
    joint_world = np.array([world[i] for i in skin['joints']])
    operators = joint_world @ ibm
    count = len(attrs['POSITION'])
    hp = np.column_stack([attrs['POSITION'], np.ones(count)])
    weights = np.zeros((count, len(names)))
    world_pos = np.zeros((count, 3))
    for key in attrs:
        if not key.startswith('JOINTS_'):
            continue
        j = attrs[key].astype(int)
        w = attrs[key.replace('JOINTS_', 'WEIGHTS_')]
        for col in range(4):
            np.add.at(weights, (np.arange(count), j[:, col]), w[:, col])
            transformed = np.einsum('nij,nj->ni', operators[j[:, col]], hp)[:, :3]
            world_pos += w[:, col, None] * transformed
    return dict(g=g, b=b, attrs=attrs, positions=world_pos, weights=weights,
        names=names, joints=joint_world, ibm=ibm, operators=operators, hp=hp,
        local=loc, world=world, parents=parents,
        triangles=accessor(g, b, p['indices']).astype(int).reshape(-1, 3))


def cyclic(triangle):
    a, b, c = map(int, triangle)
    return min((a, b, c), (b, c, a), (c, a, b))


def compare(s, t, require_normals=True, write_artifacts=False):
    assert set(s['attrs']) == set(t['attrs']), 'Attribute names changed'
    assert set(s['names']) == set(t['names']), 'Skin joint names changed'
    assert not s['g'].get('animations') and not t['g'].get('animations')
    assert not s['g'].get('textures') and not t['g'].get('textures')
    assert len(s['g']['materials']) == len(t['g']['materials']) == 1
    sm, tm = s['g']['materials'][0], t['g']['materials'][0]
    assert sm.get('doubleSided', False) == tm.get('doubleSided', False)
    assert sm.get('alphaMode', 'OPAQUE') == tm.get('alphaMode', 'OPAQUE')
    for key, default in [('baseColorFactor', [1,1,1,1]), ('metallicFactor', 1), ('roughnessFactor', 1)]:
        np.testing.assert_allclose(sm.get('pbrMetallicRoughness', {}).get(key, default),
            tm.get('pbrMetallicRoughness', {}).get(key, default), atol=1e-7, rtol=0)
    order = [t['names'].index(n) for n in s['names']]
    tw = t['weights'][:, order]
    # Source positions lie on a 0.1 mm grid, apart from sub-micrometre bind noise.
    # Bucket both assets on that grid; all candidates are then checked numerically.
    skeys = np.rint(s['positions'] / 1e-4).astype(np.int64)
    tkeys = np.rint(t['positions'] / 1e-4).astype(np.int64)
    buckets = defaultdict(list)
    for i, k in enumerate(skeys):
        buckets[tuple(k)].append(i)
    mapping = []
    ambiguous = 0
    errors = dict(position_m=0., fiber=0., tendon=0., part_id=0., weights=0.)
    # Matching within a location considers all data. Topology is subsequently
    # compared as an oriented triangle multiset, including coincident identities.
    for i, key in enumerate(tkeys):
        candidates = buckets.get(tuple(key), [])
        valid = []
        for j in candidates:
            e = [np.max(abs(t['positions'][i]-s['positions'][j])),
                 np.max(abs(t['attrs']['_FIBER'][i]-s['attrs']['_FIBER'][j])),
                 np.max(abs(t['attrs']['_TENDON'][i]-s['attrs']['_TENDON'][j])),
                 np.max(abs(t['attrs']['_PART_ID'][i]-s['attrs']['_PART_ID'][j])),
                 np.max(abs(tw[i]-s['weights'][j]))]
            if all(x <= limit for x, limit in zip(e, [POS_TOL, ATTR_TOL, ATTR_TOL, 0, WEIGHT_TOL])):
                valid.append((j, e))
        assert valid, f'No preserved source vertex for exported vertex {i}, position {t["positions"][i]}'
        ambiguous += len(valid) > 1
        def normal_distance(item):
            ns = s['attrs']['NORMAL'][item[0]]
            nt = t['attrs']['NORMAL'][i]
            return np.linalg.norm(ns / np.linalg.norm(ns) - nt / np.linalg.norm(nt))
        j, e = min(valid, key=normal_distance)
        mapping.append(j)
        for key, value in zip(errors, e):
            errors[key] = max(errors[key], float(value))
    mapping = np.array(mapping)
    # Equivalent source vertices may share coordinates, data and weights. Give
    # them one identity for topology without erasing triangle multiplicity.
    signatures = {}
    canonical = []
    for i in range(len(skeys)):
        sig = (tuple(skeys[i]), tuple(s['attrs']['_PART_ID'][i]),
               tuple(s['attrs']['_FIBER'][i]), tuple(s['attrs']['_TENDON'][i]),
               tuple(s['weights'][i]))
        if require_normals:
            sig += (tuple(s['attrs']['NORMAL'][i]),)
        canonical.append(signatures.setdefault(sig, len(signatures)))
    canonical = np.array(canonical)
    source_tris = Counter(cyclic(x) for x in canonical[s['triangles']])
    target_tris = Counter(cyclic(x) for x in canonical[mapping[t['triangles']]])
    assert source_tris == target_tris, 'Oriented triangle/corner identity changed'
    assert set(canonical) == set(canonical[mapping]), 'Source vertex data lost'
    # The inverse bind matrices change representation when quantized positions
    # become metres. Compare the action of every contributing joint separately,
    # not merely the weighted sum (which could hide compensating errors).
    bind_error = 0.
    for j, name in enumerate(s['names']):
        used = np.flatnonzero(s['weights'][mapping, j] > 0)
        a = (s['operators'][j] @ s['hp'][mapping[used]].T).T[:, :3]
        b = (t['operators'][order[j]] @ t['hp'][used].T).T[:, :3]
        bind_error = max(bind_error, float(np.max(abs(a-b))) if len(used) else 0)
    assert bind_error <= POS_TOL, f'Per-joint bind contribution changed: {bind_error}'
    joint_error = float(np.max(abs(s['joints']-t['joints'][order])))
    assert joint_error <= POS_TOL, f'Joint world transforms changed: {joint_error}'
    snodes = {n['name']: i for i, n in enumerate(s['g']['nodes'])}
    tnodes = {n['name']: i for i, n in enumerate(t['g']['nodes'])}
    assert set(snodes) == set(tnodes), 'Scene nodes changed'
    node_changes = []
    for name, i in snodes.items():
        j = tnodes[name]
        def parent_name(a, index):
            return a['g']['nodes'][a['parents'][index]]['name'] if index in a['parents'] else None
        assert parent_name(s, i) == parent_name(t, j), f'Hierarchy changed: {name}'
        error = float(np.max(abs(s['world'][i]-t['world'][j])))
        assert error <= POS_TOL, f'Node transform changed: {name}'
        node_changes.append({'node': name, 'max_local_matrix_error': float(np.max(abs(s['local'][i]-t['local'][j]))),
                             'max_world_matrix_error': error})
    # Normals may be split/renormalized by Blender. Compare at triangle corners
    # through the data-preserving vertex match; report angle, never raw lengths.
    ns = s['attrs']['NORMAL'][mapping]
    nt = t['attrs']['NORMAL']
    ns = ns / np.linalg.norm(ns, axis=1)[:, None]
    nt = nt / np.linalg.norm(nt, axis=1)[:, None]
    angles = np.degrees(np.arccos(np.clip(np.sum(ns*nt, axis=1), -1, 1)))
    normal_max = float(angles.max())
    if write_artifacts:
        np.save(OUT / 'roundtrip-to-source.npy', mapping)
        (OUT / ('normal-diagnostic-final.json' if require_normals else 'normal-diagnostic-raw.json')).write_text(json.dumps({'maximum': normal_max,
            'over_point_one_degree': int(np.sum(angles > .1)),
            'worst': [{'target': int(i), 'source': int(mapping[i]), 'angle': float(angles[i]),
                       'source_normal': ns[i].tolist(), 'target_normal': nt[i].tolist(),
                       'position': t['positions'][i].tolist()} for i in np.argsort(angles)[-20:]]}, indent=2))
    if require_normals:
        assert normal_max < .1, f'Unexpected shading-normal change: {normal_max} degrees'
    representations = {}
    for name in s['attrs']:
        def rep(a):
            index = a['g']['meshes'][0]['primitives'][0]['attributes'][name]
            v = a['g']['accessors'][index]
            return {'componentType': v['componentType'], 'type': v['type'],
                    'normalized': v.get('normalized', False), 'count': v['count']}
        representations[name] = {'source': rep(s), 'roundtrip': rep(t)}
    return dict(status='PASS' if require_normals else 'NORMALS_NOT_VALIDATED', max_errors=errors, source_vertices=len(skeys),
        roundtrip_vertices=len(tkeys), triangles=len(s['triangles']),
        additional_split_vertices=len(tkeys)-len(skeys), ambiguous_equivalent_matches=ambiguous,
        oriented_triangle_multiset_equal=True, all_source_vertex_data_retained=True,
        joint_count=len(s['names']), joint_names=s['names'],
        max_joint_world_matrix_error=joint_error, per_joint_bind_contribution_error_m=bind_error,
        normal_max_angle_degrees=normal_max, node_transforms=node_changes,
        materials_preserved=True, source_material=sm, roundtrip_material=tm,
        unused_nonzero_joint_slots={'source': int(np.sum((s['attrs']['JOINTS_0'] != 0) & (s['attrs']['WEIGHTS_0'] == 0))),
                                   'roundtrip': int(np.sum((t['attrs']['JOINTS_0'] != 0) & (t['attrs']['WEIGHTS_0'] == 0)))},
        source_asset_extras=s['g'].get('extras'), roundtrip_asset_extras=t['g'].get('extras'),
        source_bounds_m=[s['positions'].min(0).tolist(), s['positions'].max(0).tolist()],
        roundtrip_bounds_m=[t['positions'].min(0).tolist(), t['positions'].max(0).tolist()],
        representations=representations)


def selections(s):
    vocabulary = json.loads((ROOT / 'work/heatsy/data/muscles.json').read_text())
    muscles = {m['id']: m for m in vocabulary['muscles']}
    codes = s['attrs']['_PART_ID'][:, 0]
    assert np.all(codes == np.rint(codes))
    result = []
    for index, part in enumerate(vocabulary['parts']):
        muscle = muscles[part['muscle']]
        if muscle['group'] not in ('quads', 'glutes', 'quadriceps'):
            continue
        for side, offset in [('L', 0), ('R', 1)]:
            code = 1 + 2*index + offset
            selected = np.flatnonzero(codes == code)
            result.append(dict(part=part['id'], muscle=part['muscle'], group=muscle['group'], side=side,
                code=code, vertices=len(selected), available=bool(len(selected)),
                bounds_m=[s['positions'][selected].min(0).tolist(), s['positions'][selected].max(0).tolist()] if len(selected) else None))
    assert result, 'No requested vocabulary groups found'
    return result


def main():
    report = {'status': 'FAIL', 'animated_deformation_tested': False,
              'tolerances': {'position_m': POS_TOL, 'anatomical_decoded': ATTR_TOL, 'part_ids': 0, 'weights': WEIGHT_TOL}}
    try:
        assert sha(SOURCE) == SOURCE_HASH
        s, t = asset(SOURCE), asset(OUT / 'roundtrip.glb')
        report.update(compare(s, t, write_artifacts=True))
        report['source_sha256'] = sha(SOURCE)
        report['roundtrip_sha256'] = sha(OUT / 'roundtrip.glb')
        report['selections'] = selections(s)
        (OUT / 'selections.json').write_text(json.dumps(report['selections'], indent=2))
        before = json.loads((OUT / 'bodyweight-before.json').read_text())
        assert all(sha(ROOT / p) == h for p, h in before.items()), 'Canonical bodyweight files changed'
        report['bodyweight_files_unchanged'] = len(before)
    except Exception as exc:
        report.update(status='FAIL', error=str(exc))
        raise
    finally:
        (OUT / 'validation.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k not in ('selections', 'node_transforms', 'representations', 'joint_names')}, indent=2))


if __name__ == '__main__':
    main()
