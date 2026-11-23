"""Fail-closed aggregate with browser parity and preserved baseline hashes."""
import json
from pathlib import Path
import numpy as np
from heatsy_validate import ROOT, OUT, SOURCE, SOURCE_HASH, sha, asset
from heatsy_patch import MESH_SHA256


def finish():
    validation = json.loads((OUT / 'validation.json').read_text())
    viewer = json.loads((OUT / 'viewer.json').read_text())
    assert validation['status'] == viewer['status'] == 'PASS'
    assert validation['roundtrip_sha256'] == viewer['hashes']['roundtrip.glb'] == sha(OUT / 'roundtrip.glb')
    assert viewer['hashes']['validation.json'] == sha(OUT / 'validation.json')
    before = json.loads((OUT / 'bodyweight-before.json').read_text())
    assert all(sha(ROOT / p) == h for p, h in before.items())
    assert sha(SOURCE) == SOURCE_HASH
    importer = ROOT / 'work/toolchain/blender-4.5.11-windows-x64/4.5/scripts/addons_core/io_scene_gltf2/blender/imp/mesh.py'
    assert sha(importer) == MESH_SHA256
    assert sha(OUT / 'mpfb-regression/squat-technical.glb') == sha(ROOT / 'outputs/bodyweight/squat-technical.glb')
    raw_export = json.loads((OUT / 'export.json').read_text())
    preservation = json.loads((OUT / 'normal-preservation.json').read_text())
    assert raw_export['raw_export_sha256'] == preservation['raw_sha256'] == sha(OUT / 'blender-raw.glb')
    assert preservation['final_sha256'] == sha(OUT / 'roundtrip.glb')
    checks = {}
    assert json.loads((OUT/'reproduce-latest.json').read_text())['attribute_dimension_failure_reproduced']
    for mode in ('stock', 'order', 'fixed'):
        cases = json.loads((OUT / f'fixture-{mode}.json').read_text())
        checks[mode] = {c['case']: c['pass'] for c in cases}
    assert not checks['stock']['minimal-order'] and checks['order']['minimal-order']
    assert not checks['order']['normalized-vector'] and not checks['order']['normalized-scalar']
    assert len(checks['fixed']) == 9 and all(checks['fixed'].values())
    gltf = {}
    for name, path in [('source', SOURCE), ('roundtrip', OUT/'roundtrip.glb'), ('mpfb', OUT/'mpfb-regression/squat-technical.glb')]:
        result = json.loads((OUT / f'{name}-gltf.json').read_text())
        assert result['status'] == 'PASS' and result['sha256'] == sha(path)
        gltf[name] = {'errors': result['issues']['numErrors'], 'warnings': result['issues']['numWarnings']}
    positions = json.loads((OUT / 'browser-positions.json').read_text())
    parity = []
    for i, path in enumerate([SOURCE, OUT / 'roundtrip.glb']):
        expected = asset(path)['positions']
        actual = np.array(positions[i][0])
        assert actual.shape == expected.shape
        error = float(np.max(abs(actual-expected)))
        assert error < 1e-6
        parity.append({'asset': 'source' if i == 0 else 'roundtrip', 'vertices': len(actual), 'max_error_m': error})
    (OUT / 'browser-parity.json').write_text(json.dumps({'status': 'PASS', 'comparisons': parity}, indent=2))
    for name in ('LICENSE', 'NOTICE.md'):
        assert sha(OUT / name) == sha(ROOT / 'work/heatsy' / name)
    for name in ('muscles.json', 'za_map.json'):
        assert sha(OUT / name) == sha(ROOT / 'work/heatsy/data' / name)
    tests = (OUT / 'tests.log').read_text()
    assert '\nOK\n' in tests and 'skipped=' not in tests
    assert len(viewer['selection_checks']) == 16
    for screenshot in viewer['screenshots']:
        assert (ROOT / screenshot).is_file()
    result = dict(status='PASS', scope='static compatibility and appearance proof only',
        animated_deformation_tested=False, retargeting_tested=False, movement_approved=False,
        public_ready=False, source_sha256=SOURCE_HASH, roundtrip_sha256=sha(OUT/'roundtrip.glb'),
        importer_installation_unchanged=True, canonical_bodyweight_files_unchanged=len(before),
        fresh_mpfb_export_byte_identical=True, fixture_results=checks, gltf=gltf,
        browser_parity=parity, selection_checks=16, screenshots=viewer['screenshots'])
    (OUT / 'milestone.json').write_text(json.dumps(result, indent=2))
    print('PASS: Heatsy static compatibility milestone; source, importer and bodyweight baseline unchanged.')


if __name__ == '__main__':
    finish()
