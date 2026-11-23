"""Gate the deliverables without converting technical success into deformation approval."""
import json
import sys
import shutil
import numpy as np
from heatsy_squat import ROOT,OUT,BASE,MOTION,sample
from heatsy_gltf import load
from heatsy_validate import sha


def main():
    report={'status':'FAIL','technical_pass':False,'review_ready':False,
            'movement_approved':False,'anatomy_approved':False,'public_ready':False}
    try:
        g,b=load(OUT/'heatsy-squat.glb');digest=sha(OUT/'heatsy-squat.glb')
        validation=json.loads((OUT/'validation.json').read_text())
        viewer=json.loads((OUT/'viewer.json').read_text())
        diagnosis=json.loads((OUT/'deformation-diagnosis.json').read_text())
        media=json.loads((OUT/'media.json').read_text())
        blender=json.loads((OUT/'blender-parity.json').read_text())
        gltf=json.loads((OUT/'heatsy-squat.glb.gltf.json').read_text())
        for r in (validation,viewer,media,gltf,blender):
            assert r['status']=='PASS' and r['glb_sha256']==digest
        assert diagnosis['glb_sha256']==digest
        assert diagnosis['assessment']=='UNACCEPTABLE_UPPER_BODY_STRETCH' and max(diagnosis['edge_stretch_by_pose'])>4
        warnings=[m for m in gltf['issues']['messages'] if m['severity']==1]
        assert gltf['issues']['numErrors']==0 and not gltf['issues'].get('truncated',False)
        assert len(warnings)==1 and warnings[0]['code']=='NODE_SKINNED_MESH_NON_ROOT'
        chosen=json.loads((OUT/'sample-indices.json').read_text())
        max_position=max_normal=max_joint=max_blender=0.
        for pose in viewer['samples']:
            positions,normals,world=sample(g,b,pose['phase']*validation['duration'],indices=chosen,normals=True)
            blender_pose=next(p for p in blender['poses'] if p['phase']==pose['phase'])
            max_blender=max(max_blender,float(np.max(abs(np.array(blender_pose['positions'])-np.array(pose['positions'])))))
            max_position=max(max_position,float(np.max(abs(positions-np.array(pose['positions'])))))
            max_normal=max(max_normal,float(np.max(abs(normals-np.array(pose['normals'])))))
            assert np.max(abs(np.array(pose['meshWorld']).reshape(4,4).T-np.eye(4)))<1e-8
            for i,n in enumerate(g['nodes']):
                name=n['name'].replace('.','')
                if name in pose['bones']:
                    actual=np.array(pose['bones'][name]).reshape(4,4).T
                    max_joint=max(max_joint,float(np.max(abs(actual-world[i]))))
        assert max_position<1e-5 and max_normal<1e-5 and max_joint<1e-5 and max_blender<1e-5
        assert len(viewer['samples'])==8 and len(viewer['selection_checks'])==57
        before=json.loads((OUT/'baseline-before.json').read_text())
        assert all(sha(ROOT/p)==value for p,value in before.items())
        assert validation['motion_sha256']==sha(MOTION)
        tests=(OUT/'tests.log').read_text()
        assert '\nOK\n' in tests and 'skipped=' not in tests
        for name in ('LICENSE','NOTICE.md'):
            assert sha(OUT/name)==sha(BASE/name)
        for item in media['videos']:
            assert sha(OUT/(item['view']+'.mp4'))==item['sha256']
        assert sha(OUT/'poster.png')==media['poster_sha256']
        for path in viewer['screenshots']:
            assert (ROOT/path).is_file()
        parity=dict(status='PASS',sampled_vertices_per_pose=len(chosen),poses=len(viewer['samples']),
            glb_sha256=digest,max_blender_vs_three_position_component_error_m=max_blender,
            max_deformed_position_error_m=max_position,max_deformed_normal_component_error=max_normal,
            max_joint_matrix_error=max_joint,
            hierarchy_disposition='Verified at standing, descent, bottom, ascent and return: mesh and body_rig are identity; pelvis owns translation; all 56 joint matrices and representative skin-deformed positions match independent FK/LBS. No dropped or doubled parent/root motion in this viewer.')
        (OUT/'animated-parity.json').write_text(json.dumps(parity,indent=2))
        sources=['studio/heatsy_squat.py','studio/heatsy_squat_prepare.py','studio/heatsy_squat_validate.py',
            'studio/heatsy_squat_diagnose.py','studio/heatsy_squat_finish.py','studio/heatsy_squat_build.py',
            'studio/heatsy_squat_capture.mjs','studio/heatsy_squat_media.py','studio/heatsy_squat_blender.py',
            'studio/heatsy-squat/viewer.js','studio/heatsy-squat/index.html','package-lock.json']
        provenance=dict(source_motion={'path':str(MOTION.relative_to(ROOT)),'sha256':sha(MOTION),'license':'MIT','unchanged':True},
            source_asset={'commit':'6cf6a0ae7c63bcffca1137ddcec14a31b7254a6d','license':'CC-BY-SA-4.0',
                'preserved_static_sha256':sha(BASE/'roundtrip.glb')},
            code_sha256={p:sha(ROOT/p) for p in sources},glb_sha256=digest,
            normal_restoration=json.loads((OUT/'normal-preservation.json').read_text()),
            units='metres; original 0.0001 quantization scale not reapplied',
            anatomical_attributes='unchanged FLOAT32, normalized=false; integer-valued PART_ID and decoded FIBER/TENDON',
            motion_approval=False,anatomy_approval=False,public_ready=False)
        (OUT/'provenance.json').write_text(json.dumps(provenance,indent=2))
        if (ROOT/'docs/HEATSY_BODYWEIGHT_REVIEW.md').exists():
            shutil.copy2(ROOT/'docs/HEATSY_BODYWEIGHT_REVIEW.md',OUT/'REVIEW.md')
        report.update(status='PARTIAL',technical_pass=True,review_ready=False,
            blocker='BLOCKED_DEFORMATION',human_review_artifacts_ready=True,
            deformation_check='FAIL',glb_sha256=digest,motion_sha256=sha(MOTION),
            protected_files_unchanged=len(before),vertex_records=79674,triangles=149030,joints=56,
            browser_parity=parity,diagnosis=diagnosis,
            performance=viewer['performance'],sole_contact=validation['sole_contact'],duration=validation['duration'],
            deliverables=['heatsy-squat.glb','front.mp4','side.mp4','poster.png','poses/'],
            note='Diagnostic animation delivered; stop here. No skin-weight edits, general mesh repair, retargeting expansion or publication.')
    except Exception as exc:
        report['error']=str(exc)
        raise
    finally:
        (OUT/'milestone.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='diagnosis'},indent=2))
    return 2  # Explicitly distinguishes a diagnosed deformation block from success.


if __name__=='__main__':sys.exit(main())
