"""Final gates preserve exit 2 while visible deformation limitations remain."""
import json
import sys
import platform
import zipfile
import numpy as np
import scipy
from heatsy_repair import Rig, ROOT, OUT, BROKEN, dump
from heatsy_gltf import load
from heatsy_validate import sha
from heatsy_squat import sample


def main():
    path=OUT/'heatsy-squat.glb';digest=sha(path);g,b=load(path)
    records={n:json.loads((OUT/f'{n}.json').read_text()) for n in ('validation','viewer','media','blender-parity')}
    gltf=json.loads((OUT/'heatsy-squat.glb.gltf.json').read_text())
    for name,r in records.items():
        assert r['glb_sha256']==digest
        assert r['status']=='PASS' or (name=='blender-parity' and r['status']=='FAIL')
    assert gltf['status']=='PASS' and gltf['glb_sha256']==digest
    assert gltf['issues']['numErrors']==0 and not gltf['issues'].get('truncated',False)
    warnings=[m['code'] for m in gltf['issues']['messages'] if m['severity']==1]
    assert warnings==['NODE_SKINNED_MESH_NON_ROOT']
    indices=json.loads((OUT/'sample-indices.json').read_text());max_position=max_normal=max_joint=max_blender=0.
    for p in records['viewer']['samples']:
        y,n,world=sample(g,b,p['phase']*records['validation']['duration'],indices=indices,normals=True)
        bp=next(q for q in records['blender-parity']['poses'] if q['phase']==p['phase'])
        max_blender=max(max_blender,float(np.max(abs(np.array(bp['positions'])-p['positions']))))
        max_position=max(max_position,float(np.max(abs(y-p['positions']))))
        max_normal=max(max_normal,float(np.max(abs(n-p['normals']))))
        for i,node in enumerate(g['nodes']):
            name=node['name'].replace('.','')
            if name in p['bones']:max_joint=max(max_joint,float(np.max(abs(np.array(p['bones'][name]).reshape(4,4).T-world[i]))))
    assert max_position<1e-5 and max_normal<1e-5 and max_joint<1e-5
    blender_pass=records['blender-parity']['status']=='PASS' and max_blender<1e-5
    assert len(records['viewer']['samples'])==8 and len(records['viewer']['selection_checks'])==57
    assert '\nOK\n' in (OUT/'tests.log').read_text() and 'skipped=' not in (OUT/'tests.log').read_text()
    for item in records['media']['videos']:assert sha(OUT/(item['view']+'.mp4'))==item['sha256']
    assert sha(OUT/'poster.png')==records['media']['poster_sha256']
    protected=json.loads((OUT/'checkpoints/baseline-hashes.json').read_text())
    assert all(sha(ROOT/p)==h for p,h in protected.items())
    surface=json.loads((OUT/'surface-intersections.json').read_text())
    assert surface['results']['accepted']['glb_sha256']==digest
    profile_path=OUT/'performance-profile.json'
    if profile_path.exists():
        profile=json.loads(profile_path.read_text())
        assert profile['status']=='PASS' and profile['glb_sha256']==digest
    rig=Rig();volume=np.load(OUT/'volume-controls.npz')
    dump('volume-experiment.json',dict(glb_sha256=digest,
        diagnostic_only=True,exported_glb_uses='linear blend skinning',
        poses={name:rig.metrics(volume[name]) for name in volume.files}))
    parity=dict(status='PASS' if blender_pass else 'FAIL',glb_sha256=digest,vertices_per_pose=len(indices),poses=8,
        tolerance_m=1e-5,blender_gate_pass=blender_pass,
        max_three_vs_python_position_error_m=max_position,max_blender_vs_three_position_error_m=max_blender,
        max_normal_component_error=max_normal,max_joint_matrix_error=max_joint,
        hierarchy_warning='Static identity mesh/body_rig; unchanged pelvis translation; no dropped/doubled parent motion in tested engines')
    dump('animated-parity.json',parity)
    files=['studio/heatsy_repair.py','studio/heatsy_repair_validate.py','studio/heatsy_repair_build.py',
        'studio/heatsy_repair_finish.py','studio/heatsy_repair_blender.py','studio/heatsy_repair_intersections.py',
        'studio/heatsy_repair_capture.mjs','studio/heatsy_repair_profile.mjs','studio/heatsy_squat_capture.mjs',
        'studio/heatsy-squat/viewer.js','tests/test_heatsy_repair.py','studio/requirements-repair.txt']
    dump('provenance.json',dict(glb_sha256=digest,broken_baseline_sha256=sha(BROKEN),
        original_source_sha256=sha(ROOT/'work/heatsy/model/body_superficial.app5m.glb'),
        motion_sha256=sha(ROOT/'motions/synthetic/squat.json'),code_sha256={p:sha(ROOT/p) for p in files},
        python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,
        attribution='Heatsy / DDDEV LTD; Z-Anatomy; BodyParts3D',license='CC-BY-SA-4.0',
        recipe=json.loads((OUT/'recipe.json').read_text()),geometry_and_anatomy_unchanged=True,
        skin_weights_are_explicit_derivative=True,manual_frame_edits=False))
    report=dict(status='PARTIAL',technical_pass=blender_pass,deformation_resolved=False,exit_code=2,
        glb_sha256=digest,protected_files_unchanged=len(protected),parity=parity,
        motion_approved=False,anatomy_approved=False,public_ready=False,
        remaining=([] if blender_pass else ['Blender posed-position parity exceeds unchanged 10 micrometre gate'])+['Residual shoulder/hip/knee compression and surface intersections',
            'Skin-weight derivative is not anatomically validated',
            'Synthetic source has no independent axial-twist targets or pelvic tilt',
            'Hardware headless profiling is not a mobile or displayed-frame benchmark'])
    dump('milestone.json',report)
    with zipfile.ZipFile(OUT/'checkpoints/before-repair-source.zip') as archive:
        import hashlib
        changed=[]
        for name in archive.namelist():
            source=ROOT/name
            assert source.exists(),f'Archived source removed: {name}'
            if hashlib.sha256(archive.read(name)).hexdigest()!=sha(source):changed.append(name)
        dump('source-change-audit.json',dict(changed_preexisting_files=changed,removed_files=[],
            source_checkpoint='checkpoints/before-repair-source.zip'))
    doc=ROOT/'docs/HEATSY_DEFORMATION_REPAIR.md'
    if doc.exists():(OUT/'REVIEW.md').write_text(doc.read_text(encoding='utf-8').replace('../outputs/heatsy-repair/','./'),encoding='utf-8')
    with zipfile.ZipFile(OUT/'checkpoints/accepted-source.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for folder in ('studio','tests','docs'):
            for source in (ROOT/folder).rglob('*'):
                if source.is_file() and '__pycache__' not in source.parts:archive.write(source,source.relative_to(ROOT))
    print(json.dumps(report,indent=2))
    return 2


if __name__=='__main__':sys.exit(main())
