"""Run inside the pinned Blender: retain an unmodified-import failure."""
import hashlib
import json
from pathlib import Path
import traceback
import sys
import bpy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/heatsy-probe/compatibility'
OUT.mkdir(parents=True, exist_ok=True)
source = ROOT / 'work/heatsy/model/body_superficial.app5m.glb'
assert bpy.app.version == (4, 5, 11)
assert hashlib.sha256(source.read_bytes()).hexdigest() == 'ce9859de013c2ee9713dbe3158275208b57be1b4ff31957eca87195b991c0ab1'
baseline = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ROOT / 'outputs/bodyweight').rglob('*') if p.is_file()}
(OUT / 'bodyweight-before.json').write_text(json.dumps(baseline, indent=2))
bpy.ops.wm.read_factory_settings(use_empty=True)
try:
    bpy.ops.import_scene.gltf(filepath=str(source))
except Exception:
    trace = traceback.format_exc()
    attempt = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else '0'
    (OUT / f'original-traceback-attempt-{attempt}.txt').write_text(trace)
    mismatch = 'all the input array dimensions' in trace
    if mismatch:
        (OUT / 'original-traceback.txt').write_text(trace)
    (OUT / 'reproduce-latest.json').write_text(json.dumps({'attempt': attempt,
        'attribute_dimension_failure_reproduced': mismatch,
        'failure': 'array shape mismatch' if mismatch else 'normalized attribute type failure'}, indent=2))
    print('EXPECTED IMPORT FAILURE:', 'array shape mismatch' if mismatch else 'normalized attribute type failure')
else:
    raise AssertionError('Expected original importer to fail')
