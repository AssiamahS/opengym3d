"""Isolated import/round-trip probe; never alters the source or bodyweight character."""
import bpy
import json
import sys
import traceback
from pathlib import Path
from mathutils import Vector

root = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'pipeline'))
import qa_glb
source = root/'work/heatsy/model/body_superficial.app5m.glb'
out = root/'outputs/heatsy-probe'
out.mkdir(parents=True,exist_ok=True)
report = {'blender':bpy.app.version_string,'importer': 'bundled io_scene_gltf2',
          'source_commit':'6cf6a0ae7c63bcffca1137ddcec14a31b7254a6d',
          'retargeting_tested':False,'status':'FAIL'}
try:
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(source))
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    arms=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']
    points=[o.matrix_world@v.co for o in meshes for v in o.data.vertices]
    report.update(height_m=max(p.z for p in points)-min(p.z for p in points),
        vertices=sum(len(o.data.vertices) for o in meshes),
        triangles=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes),
        bones=[len(o.data.bones) for o in arms],
        attributes={o.name:[(a.name,a.data_type,a.domain) for a in o.data.attributes] for o in meshes},
        armature_modifiers=sum(sum(m.type=='ARMATURE' for m in o.modifiers) for o in meshes))
    # Small temporary knee rotation verifies that actual skin vertices respond.
    mesh=meshes[0]; arm=arms[0]
    candidate=next((b for b in arm.pose.bones if 'leg' in b.name.lower()),list(arm.pose.bones)[-1])
    deps=bpy.context.evaluated_depsgraph_get()
    before=[v.co.copy() for v in mesh.evaluated_get(deps).data.vertices]
    candidate.rotation_mode='XYZ';candidate.rotation_euler.x=.25
    bpy.context.view_layer.update()
    after=[v.co.copy() for v in mesh.evaluated_get(deps).data.vertices]
    report['skinning_probe']={'bone':candidate.name,'rotation_radians':.25,
        'max_vertex_displacement_m':max((a-b).length for a,b in zip(after,before))}
    candidate.rotation_euler.x=0;bpy.context.view_layer.update()
    target=out/'roundtrip.glb'
    bpy.ops.export_scene.gltf(filepath=str(target),export_attributes=True,export_animations=False)
    original,_=qa_glb.load_glb(source);exported,_=qa_glb.load_glb(target)
    def attributes(g):
        return sorted({a for m in g['meshes'] for p in m['primitives'] for a in p['attributes'] if a.startswith('_')})
    report['source_attributes']=attributes(original);report['roundtrip_attributes']=attributes(exported)
    report['status']='PASS' if set(report['source_attributes'])<=set(report['roundtrip_attributes']) else 'FAIL'
except Exception as exc:
    report['error']=str(exc);report['traceback']=traceback.format_exc()
report['next_question']='Can the pinned importer preserve all custom scalar/vector attributes without loss before attempting any retarget?'
(out/'probe.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
