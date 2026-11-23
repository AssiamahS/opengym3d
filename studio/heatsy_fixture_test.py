"""Actual Blender regression seam: stock, ordering-only, full patch, then export."""
import difflib
import itertools
import json
from pathlib import Path
import sys
import traceback
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'studio'))
from heatsy_gltf import fixture, load, accessor
from heatsy_patch import apply
OUT = ROOT / 'outputs/heatsy-probe/compatibility'
OUT.mkdir(parents=True, exist_ok=True)
mode = sys.argv[sys.argv.index('--') + 1]
if mode != 'stock':
    source, modified = apply(normalized=mode == 'fixed')
    (OUT / f'{mode}-importer.patch').write_text(''.join(difflib.unified_diff(
        source.splitlines(True), modified.splitlines(True), 'bundled/mesh.py', 'process-local/mesh.py')))
results = []
cases = [(str(i), order, False) for i, order in enumerate(itertools.permutations(('_FIBER', '_TENDON', '_PART_ID')))]
# Exactly one triangle and two float attributes: isolate ordering from conversion.
cases += [('minimal-order', tuple(reversed(list({'_FIBER', '_PART_ID'}))), True),
          ('normalized-vector', ('_FIBER',), False), ('normalized-scalar', ('_TENDON',), False)]
for label, order, decoded_custom in cases:
    path = OUT / f'fixture-{label}.glb'
    fixture(path, order, decoded_custom)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    result = {'case': label, 'order': order, 'pass': False}
    try:
        bpy.ops.import_scene.gltf(filepath=str(path), merge_vertices=False)
        mesh = next(o.data for o in bpy.context.scene.objects if o.type == 'MESH')
        result['blender_attributes'] = {a.name: a.data_type for a in mesh.attributes if a.name.startswith('_')}
        g, b = load(path)
        attrs = g['meshes'][0]['primitives'][0]['attributes']
        for name in order:
            a = mesh.attributes.get(name)
            assert a is not None, f'{name} silently discarded'
            values = np.array([list(x.vector) if name == '_FIBER' else [x.value] for x in a.data])
            expected = accessor(g, b, attrs[name])
            error = float(np.max(np.abs(values - expected)))
            result[name + '_error'] = error
            assert error <= (0 if name == '_PART_ID' else 1e-7), f'{name} value error {error}'
        target = OUT / f'fixture-{label}-roundtrip.glb'
        bpy.ops.export_scene.gltf(filepath=str(target), export_attributes=True, export_animations=False)
        h, c = load(target)
        aa = h['meshes'][0]['primitives'][0]['attributes']
        # Match by position, never exported array index.
        sp = accessor(g, b, attrs['POSITION'])
        ep = accessor(h, c, aa['POSITION'])
        mapping = [next(j for j, p in enumerate(sp) if np.max(abs(p - q)) < 1e-7) for q in ep]
        for name in order:
            np.testing.assert_allclose(accessor(h, c, aa[name]), accessor(g, b, attrs[name])[mapping],
                                       atol=0 if name == '_PART_ID' else 1e-7, rtol=0)
        result['pass'] = True
    except Exception as exc:
        result['error'] = str(exc)
        result['traceback'] = traceback.format_exc()
    results.append(result)
(OUT / f'fixture-{mode}.json').write_text(json.dumps(results, indent=2))
print(mode, sum(r['pass'] for r in results), '/', len(results))
if mode == 'fixed':
    assert all(r['pass'] for r in results)
else:
    assert any(not r['pass'] for r in results)
