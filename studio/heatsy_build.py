"""Reproduce the bounded Heatsy milestone. All writes stay in the probe subtree."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/heatsy-probe/compatibility'
BLENDER = ROOT / 'work/toolchain/blender-4.5.11-windows-x64/blender.exe'
COMMIT = '6cf6a0ae7c63bcffca1137ddcec14a31b7254a6d'


def run(args, log, env=None):
    print('Running:', ' '.join(map(str, args)), flush=True)
    with (OUT / log).open('w', encoding='utf-8') as stream:
        subprocess.run(list(map(str, args)), cwd=ROOT, env=env, stdout=stream,
                       stderr=subprocess.STDOUT, check=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'milestone.json').write_text(json.dumps({'status': 'BUILDING', 'public_ready': False}))
    try:
        assert subprocess.check_output(['git', '-C', str(ROOT/'work/heatsy'), 'rev-parse', 'HEAD'], text=True).strip() == COMMIT
        env = dict(os.environ, PYTHONHASHSEED='0')
        blender = [BLENDER, '-b', '--factory-startup', '--python-exit-code', '1', '-P']
        # Embedded Python's hash order can vary across Blender processes. Keep
        # every attempt; require the original concatenation failure specifically.
        for attempt in range(8):
            run(blender + ['studio/heatsy_repro.py', '--', str(attempt)], f'reproduce-{attempt}.log', env)
            if json.loads((OUT/'reproduce-latest.json').read_text())['attribute_dimension_failure_reproduced']:
                break
        else:
            raise RuntimeError('Original dimension failure not reproduced in eight fresh Blender processes')
        for mode in ('stock', 'order', 'fixed'):
            run(blender + ['studio/heatsy_fixture_test.py', '--', mode], f'fixture-{mode}.log', env)
        run(blender + ['studio/heatsy_roundtrip.py'], 'export.log', env)
        run([sys.executable, 'studio/heatsy_normals.py'], 'normal-preservation.log')
        run([sys.executable, 'studio/heatsy_validate.py'], 'validation.log')
        run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], 'tests.log')
        mpfb_env = dict(os.environ, FITX_ECORCHE='0', FMS_EXPORT_ONLY='1',
            FMS_ADDONS=str(ROOT/'work/toolchain/addons'), BLENDER_USER_RESOURCES=str(ROOT/'work/blender-user'))
        run(blender + ['pipeline/build_exercise.py', '--', 'studio/squat.json', str(OUT/'mpfb-regression')],
            'mpfb-export.log', mpfb_env)
        run(['node', 'studio/heatsy_check_gltf.mjs'], 'gltf.log')
        run(['node', 'studio/heatsy_capture.mjs'], 'viewer.log')
        run([sys.executable, 'studio/heatsy_finish.py'], 'finish.log')
    except Exception as exc:
        (OUT / 'milestone.json').write_text(json.dumps({'status': 'FAIL', 'error': str(exc), 'public_ready': False}, indent=2))
        raise
    print(f'PASS. Review {OUT / "milestone.json"} and /studio/heatsy/ on a local HTTP server.')


if __name__ == '__main__':
    main()
