"""Validate the tracked skin derivative without relaxing prior technical gates."""
import json
import numpy as np
from heatsy_repair import Rig, ROOT, OUT, BROKEN, dump
from heatsy_gltf import load,accessor
from heatsy_squat import sample
from heatsy_validate import sha
from heatsy_squat_validate import channels_gate


def main():
    r=Rig();g,b=load(OUT/'heatsy-squat.glb');old,blob=load(BROKEN)
    assert b[:len(blob)]==blob, 'Original geometry/animation binary prefix modified'
    for key in ('nodes','skins','animations','materials','scenes','scene'):
        assert g[key]==old[key],f'{key} changed'
    before=old['meshes'][0]['primitives'][0];after=g['meshes'][0]['primitives'][0]
    assert before['indices']==after['indices']
    for key,index in before['attributes'].items():
        if key not in ('JOINTS_0','WEIGHTS_0'):
            assert after['attributes'][key]==index
            np.testing.assert_array_equal(accessor(g,b,index),accessor(old,blob,index))
    assert g['accessors'][:len(old['accessors'])]==old['accessors']
    joints=accessor(g,b,after['attributes']['JOINTS_0']).astype(int)
    ws=accessor(g,b,after['attributes']['WEIGHTS_0'])
    assert ws.min()>=0 and np.isfinite(ws).all() and np.max(abs(ws.sum(1)-1))<2e-7
    weights=np.zeros_like(r.w)
    for k in range(4):np.add.at(weights,(np.arange(len(weights)),joints[:,k]),ws[:,k])
    names,channels=channels_gate(g,b)
    records=[];min_y=1.;normal_step=0.;start=None;prev=None;ankles=[];soles={};history={s:[] for s in ('L','R')}
    for frame,t in enumerate(np.linspace(0,r.clip.duration,181)):
        y,n,world=sample(g,b,float(t),normals=True)
        assert np.isfinite(y).all() and np.isfinite(n).all()
        if start is None:
            start=y.copy()
            for side,sign in [('L',1),('R',-1)]:
                ii=np.flatnonzero((y[:,0]*sign>0)&(y[:,1]<.1))
                soles[side]=ii[y[ii,1]<=y[ii,1].min()+.002]
        if prev is not None:normal_step=max(normal_step,float(np.degrees(np.arccos(np.clip(np.sum(n*prev,axis=1),-1,1))).max()))
        prev=n;min_y=min(min_y,float(y[:,1].min()))
        ankles.append([world[names['foot.'+s]][:3,3] for s in ('L','R')])
        for s in soles:history[s].append(y[soles[s]])
        if frame in (0,45,90,135,180):
            baseline,_=sample(old,blob,float(t))
            records.append(dict(time=float(t),before=r.metrics(baseline),after=r.metrics(y)))
        # All joint world transforms are unmodified, not merely comparable aims.
        np.testing.assert_allclose(world,r.pose(float(t)),atol=1e-12)
    ankles=np.array(ankles);drift=np.linalg.norm(ankles-ankles[0],axis=2).max(0)
    closure=float(np.max(abs(y-start)))
    assert min_y>-.005 and drift.max()<.02 and closure<1e-5 and normal_step<20
    rest,_=sample({k:v for k,v in g.items() if k!='animations'},b,0)
    rest_error=float(np.max(abs(rest-r.rest)));assert rest_error<1e-5
    selected=json.loads((ROOT/'outputs/heatsy-bodyweight/sample-indices.json').read_text())
    (OUT/'sample-indices.json').write_text(json.dumps(selected))
    protected=json.loads((OUT/'checkpoints/baseline-hashes.json').read_text())
    assert all(sha(ROOT/p)==h for p,h in protected.items())
    bottom=records[2];assert all(bottom['after'][reg]['p99']<bottom['before'][reg]['p99'] for reg in ('all','torso','hips','knees'))
    report=dict(status='PASS',technical_pass=True,glb_sha256=sha(OUT/'heatsy-squat.glb'),
        protected_files_unchanged=len(protected),duration=r.clip.duration,samples=181,**channels,
        unchanged=['geometry accessors','triangles','anatomy attributes','inverse binds','node hierarchy','all animation keys and channels','materials'],
        changed_weight_vertices=int(np.sum(np.max(abs(weights-r.w),axis=1)>2e-7)),
        max_weight_sum_error=float(np.max(abs(ws.sum(1)-1))),rest_position_error_m=rest_error,
        minimum_skin_y_m=min_y,foot_joint_drift_m=drift.tolist(),mesh_loop_error_m=closure,
        max_normal_step_degrees_at_60hz=normal_step,
        sole_contact={s:dict(vertices=len(soles[s]),max_horizontal_drift_m=float(np.linalg.norm((np.array(h)-h[0])[:,:,[0,2]],axis=2).max()),
            max_penetration_m=max(0.,-float(np.array(h)[:,:,1].min())),
            max_lift_from_standing_m=float((np.array(h)[:,:,1]-h[0][:,1]).max())) for s,h in history.items()},
        poses=records,deformation_resolved=False,movement_approved=False,anatomy_approved=False,public_ready=False)
    dump('validation.json',report)
    dump('weight-change.json',dict(changed_vertices=report['changed_weight_vertices'],
        max_component_change=float(np.max(abs(weights-r.w))),mean_l1_change=float(np.mean(np.sum(abs(weights-r.w),axis=1))),
        original_skin_sha256=sha(BROKEN),derivative_sha256=report['glb_sha256'],
        per_part=[dict(code=int(c),vertices=int(np.sum(r.ids==c)),changed=int(np.sum(np.max(abs(weights[r.ids==c]-r.w[r.ids==c]),axis=1)>2e-7))) for c in np.unique(r.ids)]))
    print('PASS preservation/contact/loop/normal gates; deformation remains unapproved')


if __name__=='__main__':main()
