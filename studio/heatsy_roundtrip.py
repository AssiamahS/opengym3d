"""Pinned, static Heatsy import/export; run only inside project-local Blender."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import traceback
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'studio'))
from heatsy_patch import apply, MESH_SHA256

OUT = ROOT / 'outputs/heatsy-probe/compatibility'
OUT.mkdir(parents=True, exist_ok=True)
source = ROOT / 'work/heatsy/model/body_superficial.app5m.glb'
expected = 'ce9859de013c2ee9713dbe3158275208b57be1b4ff31957eca87195b991c0ab1'
assert hashlib.sha256(source.read_bytes()).hexdigest() == expected
report = {'status': 'BUILDING', 'source_sha256': expected, 'blender': bpy.app.version_string,
          'importer_version': '4.5.51',
          'importer_mesh_sha256': MESH_SHA256, 'animated_deformation_tested': False}
try:
    apply()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source), merge_vertices=False,
        bone_heuristic='BLENDER', guess_original_bind_pose=False, disable_bone_shape=True)
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    report['meshes'] = [{
        'name': o.name, 'vertices': len(o.data.vertices), 'polygons': len(o.data.polygons),
        'attributes': {a.name: {'type': a.data_type, 'domain': a.domain}
                       for a in o.data.attributes if a.name.startswith('_')},
        'world_bounds': [[min((o.matrix_world @ v.co)[i] for v in o.data.vertices),
                          max((o.matrix_world @ v.co)[i] for v in o.data.vertices)] for i in range(3)]
    } for o in meshes]
    for o in meshes:
        assert {'_PART_ID', '_FIBER', '_TENDON'} <= set(o.data.attributes.keys())
    target = OUT / 'blender-raw.glb'
    bpy.ops.export_scene.gltf(filepath=str(target), export_format='GLB',
        export_attributes=True, export_animations=False, export_extras=True,
        export_all_influences=True, export_force_sampling=False,
        export_copyright='Heatsy / DDDEV LTD; Z-Anatomy; BodyParts3D. CC BY-SA 4.0. See NOTICE.md.')
    report['raw_export_sha256'] = hashlib.sha256(target.read_bytes()).hexdigest()
    report['status'] = 'EXPORTED_NOT_YET_VALIDATED'
    for name in ('LICENSE', 'NOTICE.md'):
        shutil.copy2(ROOT / 'work/heatsy' / name, OUT / name)
    for name in ('muscles.json', 'za_map.json'):
        shutil.copy2(ROOT / 'work/heatsy/data' / name, OUT / name)
    (OUT / 'DERIVATION.md').write_text('''# Local derived asset — CC BY-SA 4.0

Source: Heatsy Body Model, commit 6cf6a0ae7c63bcffca1137ddcec14a31b7254a6d.
Attribution and full asset license accompany this file as NOTICE.md and LICENSE.
Roundtrip and comparison images are adaptations under CC BY-SA 4.0.

Changes: imported/exported with Blender 4.5.11 and the project-local importer
compatibility patch. Normalized anatomical attributes are represented as decoded
float32 values; the exporter represents integer part IDs exactly as float32.
The final preservation step restores source normal directions after Blender's
normal encoding/export, with explicit lossless corner matching. Raw Blender
export is retained as blender-raw.glb. No rig rebuild, mesh simplification, muscle removal, retargeting,
or authored pose changes. Geometry/skin representation differences are measured
in validation.json; this file alone is not a preservation verdict.
Viewer highlights are selections by the original part vocabulary, not activation
measurements. Screenshots use uniform lighting and preserve the source rest pose.
''')
    (OUT / 'IMPORTER-NOTICE.md').write_text('''# Importer patch attribution

The process-local patch targets io_scene_gltf2 4.5.51 bundled with Blender 4.5.11.
Upstream mesh.py: Copyright 2018-2021 The glTF-Blender-IO authors, Apache-2.0.
Source: https://github.com/KhronosGroup/glTF-Blender-IO
Changes: ordered custom-attribute names and float storage for decoded normalized
attributes. No bundled source file is modified. See fixed-importer.patch.
The original Blender distribution retains its upstream source and license notices.
This importer code notice is separate from the Heatsy asset's CC BY-SA 4.0 license.
''')
except Exception:
    report.update(status='FAIL', traceback=traceback.format_exc())
    raise
finally:
    assert hashlib.sha256(source.read_bytes()).hexdigest() == expected
    (OUT / 'export.json').write_text(json.dumps(report, indent=2))
