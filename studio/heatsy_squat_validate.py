"""Separate preservation, animation, deformation measurements and browser parity."""
import copy
import json
import sys
import numpy as np
from heatsy_squat import ROOT, OUT, BASE, MOTION, sample, motion, timing
from heatsy_gltf import load, accessor
from heatsy_validate import asset, compare, sha


def hierarchy_gate(g):
    names = {n['name']:i for i,n in enumerate(g['nodes'])}
    animations = g.get('animations',[])
    assert len(animations)==1
    targets = [c['target'] for c in animations[0]['channels']]
    assert len({(c['node'],c['path']) for c in targets})==len(targets)
    assert all(c['path']=='rotation' or (c['path']=='translation' and c['node']==names['pelvis']) for c in targets)
    assert names['body_rig'] not in [c['node'] for c in targets]
    assert names['body_superficial'] not in [c['node'] for c in targets]
    for name in ('body_rig','body_superficial'):
        n=g['nodes'][names[name]]
        assert n.get('translation',[0,0,0])==[0,0,0]
        assert n.get('rotation',[0,0,0,1])==[0,0,0,1]
        assert n.get('scale',[1,1,1])==[1,1,1]
        assert 'matrix' not in n
    assert g['nodes'][names['body_rig']]['children']==[names['body_superficial'],names['pelvis']]
    return names


def channels_gate(g,b,source=None):
    names=hierarchy_gate(g)
    clock=timing(source or motion.load(MOTION))
    worst_closure=0.
    worst_step=0.
    for channel in g['animations'][0]['channels']:
        sampler=g['animations'][0]['samplers'][channel['sampler']]
        assert sampler['interpolation']=='LINEAR'
        times=accessor(g,b,sampler['input']).ravel()
        assert len(times)==clock['source_frames'] and times[0]==0 and abs(times[-1]-clock['duration'])<1e-6 and np.all(np.diff(times)>0)
        np.testing.assert_allclose(times,np.arange(clock['source_frames'])/clock['fps'],atol=2e-7)
        values=accessor(g,b,sampler['output']).astype(float)
        assert len(values)==clock['source_frames'] and np.isfinite(values).all()
        worst_closure=max(worst_closure,float(np.max(abs(values[0]-values[-1]))))
        if channel['target']['path']=='rotation':
            assert np.max(abs(np.linalg.norm(values,axis=1)-1))<1e-6
            dots=np.sum(values[1:]*values[:-1],axis=1)
            worst_step=max(worst_step,float(np.max(np.degrees(2*np.arccos(np.clip(abs(dots),0,1))))))
    assert worst_closure<1e-6
    assert worst_step<15, f'Quaternion discontinuity {worst_step}'
    return names,dict(max_channel_closure=worst_closure,max_rotation_step_degrees=worst_step)


def main():
    report={'status':'FAIL','technical_pass':False,'movement_approved':False,
            'anatomy_approved':False,'public_ready':False}
    try:
        before=json.loads((OUT/'baseline-before.json').read_text())
        assert all(sha(ROOT/p)==h for p,h in before.items()), 'Protected baseline or input changed'
        assert sha(OUT/'roundtrip.glb')==sha(BASE/'roundtrip.glb')
        g,b=load(OUT/'heatsy-squat.glb')
        static,static_blob=load(BASE/'roundtrip.glb')
        # Animation append must retain every original byte and rest definition.
        assert b[:len(static_blob)]==static_blob
        for key in ('meshes','skins','nodes','materials','scenes','scene'):
            assert g[key]==static[key], f'{key} changed'
        assert g['accessors'][:len(static['accessors'])]==static['accessors']
        p=g['meshes'][0]['primitives'][0]
        for name in ('_PART_ID','_FIBER','_TENDON'):
            a=g['accessors'][p['attributes'][name]]
            assert a['componentType']==5126 and not a.get('normalized',False)
        assert g['accessors'][p['attributes']['POSITION']]['count']==79674
        target=asset(OUT/'heatsy-squat.glb');target['g']=copy.deepcopy(target['g']);target['g'].pop('animations')
        # Reuse topology/correspondence verification; no index-based identity claim.
        preservation=compare(asset(BASE/'roundtrip.glb'),target)
        (OUT/'preservation.json').write_text(json.dumps(preservation,indent=2))
        names,channel_report=channels_gate(g,b)
        indices=accessor(g,b,p['indices']).astype(int).reshape(-1,3)
        ids=accessor(g,b,p['attributes']['_PART_ID']).ravel().astype(int)
        rest=asset(BASE/'roundtrip.glb')['positions']
        rest_tri=rest[indices]
        rest_areas=np.linalg.norm(np.cross(rest_tri[:,1]-rest_tri[:,0],rest_tri[:,2]-rest_tri[:,0]),axis=1)/2
        valid=rest_areas>1e-10
        edges=np.unique(np.sort(np.vstack([indices[:,[0,1]],indices[:,[1,2]],indices[:,[2,0]]]),axis=1),axis=0)
        lengths=np.linalg.norm(rest[edges[:,0]]-rest[edges[:,1]],axis=1)
        measurable=lengths>.001
        edges, lengths=edges[measurable],lengths[measurable]
        vocabulary=json.loads((BASE/'muscles.json').read_text())
        muscle_group={m['id']:m['group'] for m in vocabulary['muscles']}
        code_group={1+2*i+side:muscle_group[p['muscle']] for i,p in enumerate(vocabulary['parts']) for side in (0,1)}
        groups=np.array([code_group.get(int(code),'unlabelled') for code in ids])
        regions={'hips_glutes':['glutes','hip_flexors','adductors'],
                 'knee_crossing_muscles':['quads','hamstrings','calves'],
                 'shoulders_torso':['shoulders','chest','upper_back','lower_back','abs','neck']}
        region_edges={name:np.all(np.isin(groups[edges],selected),axis=1) for name,selected in regions.items()}
        starting=None;previous_normals=None;ankles=[];foot_heights=[];pose_reports=[];worst_normal_step=0.;worst_aim=0.
        source_motion=motion.load(MOTION)
        clock=timing(source_motion)
        intervals=2*(clock['source_frames']-1)
        soles={}; sole_history={side:[] for side in ('L','R')}
        for frame,t in enumerate(np.linspace(0,clock['duration'],intervals+1)):
            positions,normals,world=sample(g,b,float(t),normals=True)
            assert np.isfinite(positions).all() and np.isfinite(normals).all()
            if starting is None:
                starting=positions.copy()
                # Fixed material points: each foot's lowest 2 mm of standing skin.
                # Do not reselect vertices at each frame (that could hide slipping).
                for side,sign in [('L',1),('R',-1)]:
                    candidates=np.flatnonzero((positions[:,0]*sign>0)&(positions[:,1]<.1))
                    floor=positions[candidates,1].min()
                    soles[side]=candidates[positions[candidates,1]<=floor+.002]
                    assert len(soles[side])>10
            for side in soles:
                sole_history[side].append(positions[soles[side]].copy())
            if previous_normals is not None:
                angle=np.degrees(np.arccos(np.clip(np.sum(normals*previous_normals,axis=1),-1,1)))
                worst_normal_step=max(worst_normal_step,float(angle.max()))
            previous_normals=normals
            ankles.append([world[names['foot.'+side]][:3,3] for side in ('L','R')])
            foot_heights.append(float(positions[:,1].min()))
            if frame%2==0:
                source_frame=source_motion['frames'][frame//2]
                for side in ('L','R'):
                    for parent,child,canonical in [('thigh','shin','thigh'),('shin','foot','shin'),
                        ('upperarm','forearm','upper_arm'),('forearm','hand','forearm'),('hand','middle_01','hand')]:
                        actual=world[names[child+'.'+side]][:3,3]-world[names[parent+'.'+side]][:3,3]
                        expected=np.array(motion.blender_to_yup(source_frame['dirs'][canonical+'.'+side]))
                        cosine=np.dot(actual,expected)/np.linalg.norm(actual)/np.linalg.norm(expected)
                        worst_aim=max(worst_aim,float(np.degrees(np.arccos(np.clip(cosine,-1,1)))))
            if frame in {round(intervals*p) for p in (0,.25,.5,.75,1)}:
                tri=positions[indices]
                areas=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)/2
                stretch=np.linalg.norm(positions[edges[:,0]]-positions[edges[:,1]],axis=1)/lengths
                worst=int(np.argmax(stretch));knee={}
                for side in ('L','R'):
                    hip,kne,ank=[world[names[n+'.'+side]][:3,3] for n in ('thigh','shin','foot')]
                    x,y=hip-kne,ank-kne
                    knee[side]=float(np.degrees(np.arccos(np.clip(np.dot(x,y)/np.linalg.norm(x)/np.linalg.norm(y),-1,1))))
                pose_reports.append(dict(time=float(t),minimum_height_m=foot_heights[-1],knees_interior_degrees=knee,
                    regional_edge_stretch={name:dict(edges=int(mask.sum()),maximum=float(stretch[mask].max()),
                        p99=float(np.quantile(stretch[mask],.99)),over_2x=int(np.sum(stretch[mask]>2))) for name,mask in region_edges.items()},
                    max_edge_stretch=float(stretch[worst]),edge_over_2x=int(np.sum(stretch>2)),
                    worst_edge_vertices=edges[worst].tolist(),worst_edge_part_ids=ids[edges[worst]].tolist(),
                    worst_edge_positions=positions[edges[worst]].tolist(),
                    newly_tiny_triangles=int(np.sum(valid&(areas<1e-12))),
                    triangles_under_tenth_area=int(np.sum(valid&(areas<rest_areas*.1))),
                    bounds=[positions.min(0).tolist(),positions.max(0).tolist()]))
        ankles=np.array(ankles)
        drift=np.max(np.linalg.norm(ankles-ankles[0],axis=2),axis=0)
        closure=float(np.max(abs(positions-starting)))
        assert min(foot_heights)>-.005, f'Floor penetration {min(foot_heights)}'
        assert float(drift.max())<.02, f'Foot joint drift {drift}'
        assert closure<1e-5
        assert worst_normal_step<20, f'Abrupt skinned normal change {worst_normal_step}'
        assert worst_aim<.01, f'Target limb misses unchanged source direction: {worst_aim}'
        report.update(status='PASS',technical_pass=True,glb_sha256=sha(OUT/'heatsy-squat.glb'),
            motion_sha256=sha(MOTION),baseline_hashes_verified=len(before),**channel_report,
            duration=clock['duration'],samples=intervals+1,sample_hz=clock['fps']*2,minimum_skin_y_m=min(foot_heights),foot_joint_drift_m=drift.tolist(),
            sole_contact={side:dict(vertices=len(soles[side]),
                max_horizontal_drift_m=float(np.linalg.norm((np.array(history)-history[0])[:,:,[0,2]],axis=2).max()),
                max_penetration_m=max(0.,-float(np.array(history)[:,:,1].min())),
                max_lift_from_standing_m=float((np.array(history)[:,:,1]-history[0][:,1]).max()),
                max_sole_point_height_m=float(np.array(history)[:,:,1].max()),
                max_lowest_point_height_m=float(np.array(history)[:,:,1].min(axis=1).max())) for side,history in sole_history.items()},
            contact_policy='Fixed standing sole vertices within 2 mm of each side minimum; measured through full clip. Constant root offset only; no contact solver, collision response or toe articulation.',
            mesh_loop_error_m=closure,max_normal_step_degrees_at_60hz=worst_normal_step,
            max_limb_aim_error_degrees=worst_aim,
            source_tiny_triangles=int(np.sum(rest_areas<1e-12)),poses=pose_reports,
            hierarchy={'warning':'NODE_SKINNED_MESH_NON_ROOT',
                'disposition':'Retained hierarchy: static identity body_rig and mesh; animated pelvis only. All skin joints descend from pelvis. Verify browser deformed positions and joint matrices before completion.'})
        # Deliberately distribute samples across all anatomical IDs and vertex range.
        chosen=set(np.linspace(0,len(ids)-1,240,dtype=int).tolist())
        for code in np.unique(ids):
            ii=np.flatnonzero(ids==code)
            chosen.update(ii[np.linspace(0,len(ii)-1,min(8,len(ii)),dtype=int)].tolist())
        (OUT/'sample-indices.json').write_text(json.dumps(sorted(chosen)))
    except Exception as exc:
        report.update(error=str(exc),status='FAIL',technical_pass=False)
        raise
    finally:
        (OUT/'validation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='poses'},indent=2))


if __name__=='__main__':
    main()
