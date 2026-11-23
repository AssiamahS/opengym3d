"""Verify the bounded candidate through existing gates, always unapproved.

Run after heatsy_attachment.py. Outputs are isolated from every prior baseline.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'studio'))
OUT=ROOT/'outputs/heatsy-attachment'
BASE=ROOT/'outputs/heatsy-repair'


def native():
    import numpy as np
    import heatsy_squat_blender as parity
    from io_scene_gltf2.blender.imp.node import BlenderNode
    from io_scene_gltf2.blender.imp.vnode import VNode
    original=BlenderNode.create_bones
    records=[]

    def observed(gltf, armature_id):
        original(gltf,armature_id)
        armature=gltf.vnodes[armature_id].blender_object
        for vnode in gltf.vnodes.values():
            if vnode.type != VNode.Bone or not vnode.blender_bone_name:
                continue
            if vnode.blender_bone_name not in armature.data.bones:
                continue
            expected=np.array(vnode.editbone_arma_mat)
            actual=np.array(armature.data.bones[vnode.blender_bone_name].matrix_local)
            records.append(dict(name=vnode.blender_bone_name,
                max_component_error=float(np.max(abs(expected-actual))),
                intended=expected.tolist(), actual=actual.tolist(),
                intended_singular_values=np.linalg.svd(expected[:3,:3],compute_uv=False).tolist(),
                actual_singular_values=np.linalg.svd(actual[:3,:3],compute_uv=False).tolist()))

    BlenderNode.create_bones=staticmethod(observed)
    parity.OUT=OUT
    (OUT/'blender-parity.json').unlink(missing_ok=True)
    try:
        parity.main()
    except AssertionError:
        if not (OUT/'blender-parity.json').exists():raise
        if json.loads((OUT/'blender-parity.json').read_text())['status']!='FAIL':raise
    finally:
        BlenderNode.create_bones=staticmethod(original)
    (OUT/'native-rest-reconstruction.json').write_text(json.dumps(records,indent=2))
    from heatsy_repair_intersections import inspect
    from heatsy_gltf import load,accessor
    from heatsy_squat import sample
    from heatsy_validate import sha
    report={}
    for label,path in [('baseline',BASE/'heatsy-squat.glb'),('soften-0.5',OUT/'heatsy-squat.glb')]:
        g,b=load(path);p=g['meshes'][0]['primitives'][0]
        tri=accessor(g,b,p['indices']).astype(int).reshape(-1,3)
        ids=accessor(g,b,p['attributes']['_PART_ID']).ravel().astype(int)
        record=dict(sha256=sha(path),poses={})
        for name,t in [('neutral',None),('standing',0),('descent',.75),('bottom',1.5)]:
            source={k:v for k,v in g.items() if k!='animations'} if t is None else g
            y,_=sample(source,b,t or 0)
            record['poses'][name]=inspect(y,tri,ids)
        report[label]=record
    (OUT/'intersections.json').write_text(json.dumps(report,indent=2))


def main():
    from heatsy_validate import sha
    (OUT/'milestone.json').write_text(json.dumps(dict(status='BUILDING',technical_pass=False)))
    protected=json.loads((OUT/'protected.json').read_text())
    assert all(sha(ROOT/p)==digest for p,digest in protected.items())
    shutil.copy2(OUT/'soften-0.5.glb',OUT/'heatsy-squat.glb')
    for name in ('retarget.json','sample-indices.json','selections.json','muscles.json','za_map.json'):
        shutil.copy2(BASE/name,OUT/name)
    timing=json.loads((OUT/'retarget.json').read_text())
    timing.update(glb_sha256=sha(OUT/'heatsy-squat.glb'),
        weight_derivative=dict(parent_sha256=sha(BASE/'heatsy-squat.glb'),method='w/(1+0.5*w), normalize; foot blend retained',accepted=False))
    (OUT/'retarget.json').write_text(json.dumps(timing,indent=2))
    (OUT/'DERIVATION.md').write_text('''# Experimental skin derivative - CC BY-SA 4.0

Heatsy / DDDEV LTD; Z-Anatomy; BodyParts3D. See NOTICE.md and LICENSE.
Parent is the previous 35 mm repair; its SHA-256 and the exact candidate hash
are in retarget.json and milestone.json. Apply w/(1+0.5*w), normalize, and
retain the smooth rest-height foot preservation band (0.10-0.16 m).
No new bone support, geometry, anatomy labels, inverse binds or motion changes.
Only appended JOINTS_0/WEIGHTS_0 references differ from the original animation.

NOT ACCEPTED: some compression/intersection improvements accompany worse
maximum stretch and isolated knee compression. Movement, anatomy and public
use remain unapproved. Other candidate GLBs are rejected diagnostic experiments.
See their asset extras, experiments.json and REVIEW.md for exact recipes.
''',encoding='utf-8')
    (OUT/'checkpoints').mkdir(exist_ok=True)
    shutil.copy2(OUT/'protected.json',OUT/'checkpoints/baseline-hashes.json')
    import heatsy_repair_validate as validation
    validation.OUT=OUT
    validation.dump=lambda name,value:(OUT/name).write_text(json.dumps(value,indent=2))
    validation.main()

    def run(args,log,env=None):
        with (OUT/log).open('w',encoding='utf-8') as stream:
            subprocess.run([str(a) for a in args],cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)

    run([sys.executable,'-m','unittest','discover','-s','tests','-v'],'tests.log')
    run(['node','studio/validate_gltf.mjs',OUT/'heatsy-squat.glb'],'gltf.log')
    run([ROOT/'work/toolchain/blender-4.5.11-windows-x64/blender.exe','-b','--factory-startup',
         '--python-exit-code','1','-P',Path(__file__),'--','--blender'],'native.log')
    env=dict(os.environ,FMS_HEATSY_OUTPUT='outputs/heatsy-attachment',
             FMS_HEATSY_QUERY='repair=attachment-05&compare=before',FMS_HEATSY_GPU='1')
    run(['node','studio/heatsy_squat_capture.mjs'],'capture.log',env)
    run(['node','studio/heatsy_attachment_capture.mjs'],'details.log',env)
    import heatsy_squat_media as media
    media.OUT=OUT;media.main()
    import numpy as np
    from heatsy_gltf import load
    from heatsy_squat import sample
    g,b=load(OUT/'heatsy-squat.glb')
    viewer=json.loads((OUT/'viewer.json').read_text())
    native_report=json.loads((OUT/'blender-parity.json').read_text())
    indices=json.loads((OUT/'sample-indices.json').read_text())
    maximum=direct=normal=joint=0.
    for pose in viewer['samples']:
        y,n,world=sample(g,b,pose['phase']*timing['duration'],indices=indices,normals=True)
        maximum=max(maximum,float(np.max(abs(y-pose['positions']))))
        normal=max(normal,float(np.max(abs(n-pose['normals']))))
        for i,node in enumerate(g['nodes']):
            name=node['name'].replace('.','')
            if name in pose['bones']:
                joint=max(joint,float(np.max(abs(np.array(pose['bones'][name]).reshape(4,4).T-world[i]))))
        bp=next(p for p in native_report['poses'] if p['phase']==pose['phase'])
        direct=max(direct,float(np.max(abs(np.array(bp['positions'])-pose['positions']))))
    assert maximum<1e-5 and normal<1e-5 and joint<1e-5
    assert len(viewer['samples'])==8 and len(viewer['selection_checks'])==57 and viewer['status']=='PASS'
    assert all(sha(ROOT/p)==digest for p,digest in protected.items())
    result=dict(status='PARTIAL',exit_code=2,deformation_resolved=False,anatomy_approved=False,
        candidate_accepted=False,glb_sha256=sha(OUT/'heatsy-squat.glb'),protected_files_unchanged=len(protected),
        max_three_python_m=maximum,max_blender_three_m=direct,max_normal_component=normal,max_joint_component=joint,
        technical_pass=native_report['status']=='PASS' and direct<1e-5,
        decision='Do not replace previous repair: reduced compression and intersections but increased worst stretch; attachments remain unacceptable')
    files=['studio/heatsy_attachment.py','studio/heatsy_attachment_verify.py','studio/heatsy_attachment_capture.mjs',
        'studio/heatsy-squat/viewer.js','studio/heatsy_repair_profile.mjs','tests/test_heatsy_attachment.py']
    result['code_sha256']={p:sha(ROOT/p) for p in files}
    (OUT/'milestone.json').write_text(json.dumps(result,indent=2))
    review=(ROOT/'docs/HEATSY_ATTACHMENT_REVIEW.md').read_text(encoding='utf-8')
    review=review.replace('(../outputs/heatsy-attachment/','(').replace('(HEATSY_DEFORMATION_REPAIR.md)',
        '(../../docs/HEATSY_DEFORMATION_REPAIR.md)')
    (OUT/'REVIEW.md').write_text(review,encoding='utf-8')
    print(json.dumps(result,indent=2))
    return 2


if __name__=='__main__':
    if '--blender' in sys.argv:native()
    else:
        try:exit_code=main()
        except Exception as exc:
            (OUT/'milestone.json').write_text(json.dumps(dict(status='FAIL',technical_pass=False,error=str(exc)),indent=2))
            raise
        sys.exit(exit_code)
