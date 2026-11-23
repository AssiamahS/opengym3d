"""Reuse the pinned Blender verifier against the isolated repair output."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'studio'))
import heatsy_squat_blender
heatsy_squat_blender.OUT=ROOT/'outputs/heatsy-repair'
(heatsy_squat_blender.OUT/'blender-parity.json').unlink(missing_ok=True)
parity_failed=False
try:
    heatsy_squat_blender.main()
except AssertionError:
    import json
    record=json.loads((heatsy_squat_blender.OUT/'blender-parity.json').read_text())
    if record['status']!='FAIL':raise
    # Preserve the existing failure and tolerance. Continue independent volume
    # diagnostics so a precision limitation does not hide deformation evidence.
    parity_failed=True

# Independent volume-preservation ablation. Standard glTF LBS cannot carry this
# modifier setting; these positions are diagnostic data, not an exported fix.
import bpy
import numpy as np
from heatsy_gltf import load,accessor
out=ROOT/'outputs/heatsy-repair'
g,b=load(out/'heatsy-squat.glb')
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
attrs=g['meshes'][0]['primitives'][0]['attributes']
local=np.array([v.co[:] for v in obj.data.vertices])[:,[0,2,1]];local[:,2]*=-1
assert np.max(abs(local-accessor(g,b,attrs['POSITION'])))<1e-5
for name,field,width in [('_PART_ID','value',1),('_TENDON','value',1),('_FIBER','vector',3)]:
    data=np.empty(len(local)*width,dtype=np.float32);obj.data.attributes[name].data.foreach_get(field,data)
    np.testing.assert_allclose(data.reshape(-1,width),accessor(g,b,attrs[name]),atol=1e-7,rtol=0)
modifier=next(m for m in obj.modifiers if m.type=='ARMATURE')
arrays={}
for mode in ('linear','dual_quaternion'):
    modifier.use_deform_preserve_volume=mode=='dual_quaternion'
    for name,t in [('standing',0),('descent',.75),('bottom',1.5)]:
        frame=t*30;bpy.context.scene.frame_set(int(frame),subframe=frame-int(frame))
        evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
        y=np.array([(evaluated.matrix_world@v.co)[:] for v in mesh.vertices])[:,[0,2,1]];y[:,2]*=-1
        arrays[mode+'_'+name]=y;evaluated.to_mesh_clear()
modifier.use_deform_preserve_volume=False
np.savez_compressed(out/'volume-controls.npz',**arrays)
# Locate native-import precision differences without modifying bones or weights.
import json
from heatsy_squat import sample
from heatsy_validate import sha
armature=modifier.object
bpy.context.scene.frame_set(45)
_,world=sample(g,b,1.5)
ibm=accessor(g,b,g['skins'][0]['inverseBindMatrices']).reshape(-1,4,4).transpose(0,2,1)
conversion=np.array([[1,0,0,0],[0,0,-1,0],[0,1,0,0],[0,0,0,1]],float)
arm_world=np.array(armature.matrix_world);mesh_world=np.array(obj.matrix_world)
operators=[];bone_records=[]
for k,node in enumerate(g['skins'][0]['joints']):
    name=g['nodes'][node]['name'];bone=armature.pose.bones[name]
    actual=np.linalg.inv(conversion)@arm_world@np.array(bone.matrix)@np.linalg.inv(np.array(bone.bone.matrix_local))@np.linalg.inv(arm_world)@mesh_world@conversion
    expected=world[node]@ibm[k];operators.append(actual)
    bone_records.append(dict(name=name,max_operator_component_error=float(np.max(abs(actual-expected)))))
weights=accessor(g,b,attrs['WEIGHTS_0']);joints=accessor(g,b,attrs['JOINTS_0']).astype(int)
x=np.column_stack([local,np.ones(len(local))]);predicted=np.zeros((len(x),3))
for k in range(4):predicted+=np.einsum('nij,nj->ni',np.array(operators)[joints[:,k]],x)[:,:3]*weights[:,k,None]
expected,_=sample(g,b,1.5)
record=dict(glb_sha256=sha(out/'heatsy-squat.glb'),bones=bone_records,
    max_imported_rest_coordinate_component_error_m=float(np.max(abs(local-accessor(g,b,attrs['POSITION'])))),
    max_native_operator_vs_glb_position_component_error_m=float(np.max(abs(predicted-expected))),
    max_native_operator_vs_blender_evaluated_component_error_m=float(np.max(abs(predicted-arrays['linear_bottom']))),
    interpretation='Native Blender rest/pose bone reconstruction differs slightly from original glTF inverse-bind operators. The unchanged parity tolerance remains enforced; this diagnostic does not adjust either engine.')
(out/'blender-operator-diagnostic.json').write_text(json.dumps(record,indent=2))
if parity_failed:
    print('FAIL: unchanged native Blender parity gate; independent diagnostics saved. Final build must remain PARTIAL with technical_pass=false.')
