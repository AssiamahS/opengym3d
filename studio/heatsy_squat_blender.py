"""Evaluate the delivered GLB in pinned Blender; never export or alter it."""
import json
import math
from pathlib import Path
import sys
import bpy
import numpy as np
from mathutils.kdtree import KDTree

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'studio'))
from heatsy_squat import OUT, sample
from heatsy_gltf import load, accessor
from heatsy_validate import sha
from heatsy_patch import apply


def main():
    apply()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene
    scene.render.fps=30
    path=OUT/'heatsy-squat.glb'
    g,b=load(path)
    attrs=g['meshes'][0]['primitives'][0]['attributes']
    source=accessor(g,b,attrs['POSITION'])
    ids=accessor(g,b,attrs['_PART_ID']).ravel()
    chosen=json.loads((OUT/'sample-indices.json').read_text())
    bpy.ops.import_scene.gltf(filepath=str(path),merge_vertices=False,
        bone_heuristic='BLENDER',guess_original_bind_pose=False,disable_bone_shape=True)
    obj=next(o for o in scene.objects if o.type=='MESH')
    assert len(obj.data.vertices)==len(source)
    # Blender can reorder coincident corners. Match rest geometry, all anatomy
    # values and named influences; never assume array-index correspondence.
    local=np.array([v.co[:] for v in obj.data.vertices])[:,[0,2,1]]
    local[:,2]*=-1
    imported={}; expected_attrs={}
    for key,width in [('_PART_ID',1),('_FIBER',3),('_TENDON',1)]:
        attr=obj.data.attributes[key]
        values=np.empty(len(source)*width,dtype=np.float32)
        attr.data.foreach_get('vector' if width==3 else 'value',values)
        imported[key]=values.reshape(-1,width)
        expected_attrs[key]=accessor(g,b,attrs[key])
    joints=accessor(g,b,attrs['JOINTS_0']).astype(int)
    weights=accessor(g,b,attrs['WEIGHTS_0'])
    names=[g['nodes'][j]['name'] for j in g['skins'][0]['joints']]
    actual_weights=[{obj.vertex_groups[a.group].name:a.weight for a in v.groups if a.weight>0} for v in obj.data.vertices]
    tree=KDTree(len(local))
    for i,co in enumerate(local):tree.insert(co,i)
    tree.balance()
    mapping=[]
    max_rest_error=0.
    for i,co in enumerate(source):
        expected={names[j]:float(w) for j,w in zip(joints[i],weights[i]) if w>0}
        candidates=[]
        for _,j,dist in tree.find_range(co,1e-5):
            actual=actual_weights[j]
            if (expected.keys()==actual.keys() and all(abs(w-actual[n])<2e-7 for n,w in expected.items())
                and all(np.max(abs(imported[key][j]-expected_attrs[key][i]))<1e-7 for key in imported)):
                candidates.append((dist,j))
        assert candidates, f'No Blender correspondence for GLB vertex {i}'
        dist,j=min(candidates);mapping.append(j);max_rest_error=max(max_rest_error,dist)
    duration=json.loads((OUT/'retarget.json').read_text())['duration']
    records=[]
    for phase in (0,.25,.5,.75,1,.123,.337,.611):
        # glTF import places t=0 at Blender frame 0; use subframes off key.
        frame=phase*duration*scene.render.fps
        scene.frame_set(math.floor(frame),subframe=frame-math.floor(frame))
        evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh=evaluated.to_mesh()
        try:
            positions=np.array([(evaluated.matrix_world@mesh.vertices[mapping[i]].co)[:] for i in chosen])[:,[0,2,1]]
            positions[:,2]*=-1
        finally:
            evaluated.to_mesh_clear()
        expected,_=sample(g,b,phase*duration,indices=chosen)
        error=float(np.max(abs(positions-expected)))
        records.append(dict(phase=phase,max_position_component_error_m=error,positions=positions.tolist()))
    maximum=max(r['max_position_component_error_m'] for r in records)
    report=dict(status='PASS' if maximum<1e-5 else 'FAIL',glb_sha256=sha(path),
        blender=bpy.app.version_string,vertices_per_pose=len(chosen),poses=records,
        max_position_component_error_m=maximum,tolerance_m=1e-5,
        max_rest_correspondence_distance_m=max_rest_error,
        correspondence='All GLB vertices matched to Blender rest positions, decoded anatomy and named weights; coincident equivalent records may share a match. Posed samples use this mapping.',
        normal_scope='Blender custom-normal re-encoding is a known static limitation; final GLB source-restored normals are checked in browser separately. No Blender normal parity claim.')
    (OUT/'blender-parity.json').write_text(json.dumps(report,indent=2))
    print('Blender vs GLB FK/LBS:',maximum,'m')
    assert report['status']=='PASS'


if __name__=='__main__':main()
