"""Focused, non-mutating ablation of the upper-body deformation blocker."""
import copy
import json
import numpy as np
from heatsy_squat import OUT, BASE, ROOT, sample
from heatsy_gltf import load
from heatsy_validate import asset, sha


def main():
    reference=asset(BASE/'roundtrip.glb')
    g,b=load(OUT/'heatsy-squat.glb')
    validation=json.loads((OUT/'validation.json').read_text())
    duration=validation['duration']
    times=[duration*p for p in (0,.25,.5,.75,1)]
    bottom=min(validation['poses'],key=lambda p:abs(p['time']-duration/2))
    edge=bottom['worst_edge_vertices']
    names={n['name']:i for i,n in enumerate(g['nodes'])}
    variants={'full':set(),
        'without_girdle_follow':{names[f'{n}.{side}'] for n in ('clavicle','scapula') for side in ('L','R')},
        'upper_body_rest_control':{c['target']['node'] for c in g['animations'][0]['channels']
            if g['nodes'][c['target']['node']]['name'].split('.')[0] not in ('pelvis','thigh','shin','foot')}}
    report={}
    for variant,exclude in variants.items():
        h=copy.deepcopy(g)
        h['animations'][0]['channels']=[c for c in h['animations'][0]['channels'] if c['target']['node'] not in exclude]
        report[variant]=[]
        for time in times:
            positions,_=sample(h,b,time,indices=edge)
            report[variant].append(dict(time=time,edge_m=float(np.linalg.norm(positions[1]-positions[0]))))
    vocabulary=json.loads((BASE/'muscles.json').read_text())
    ids=reference['attrs']['_PART_ID'].ravel().astype(int)
    rest=reference['positions'][edge]
    rest_length=float(np.linalg.norm(rest[1]-rest[0]))
    ratios=[p['edge_m']/rest_length for p in report['full']]
    assert max(ratios)>4, 'Recorded deformation blocker no longer reproduced; reassess instead of reporting stale failure'
    assert max(abs(p['edge_m']/rest_length-1) for p in report['upper_body_rest_control'])<.001
    original_map=np.load(BASE/'roundtrip-to-source.npy')
    report.update(glb_sha256=sha(OUT/'heatsy-squat.glb'),vertices=edge,
        source_vertices_via_verified_correspondence=original_map[edge].tolist(),
        rest_edge_m=rest_length,rest_positions=rest.tolist(),edge_stretch_by_pose=ratios,
        part_ids=ids[edge].tolist(),part_names=[vocabulary['parts'][(ids[i]-1)//2]['id'] for i in edge],
        influences=[{reference['names'][j]:float(w) for j,w in enumerate(reference['weights'][i]) if w>0} for i in edge],
        assessment='UNACCEPTABLE_UPPER_BODY_STRETCH',review_ready=False,
        distinction='New pose-induced distortion of preserved skin weights; not explained by the pre-existing tiny/degenerate triangles. No topology or weight repair performed.',
        inference='Existing sharply varying weights under upper-arm elevation are the dominant cause. Removing girdle follow retains severe stretching; the upper-body-rest control removes it. This does not establish a general rig diagnosis.',
        failing_times_seconds=times)
    (OUT/'deformation-diagnosis.json').write_text(json.dumps(report,indent=2))
    # Add only the involved muscle to the existing review choices, by vocabulary.
    selections=json.loads((BASE/'selections.json').read_text())
    part_index=next(i for i,p in enumerate(vocabulary['parts']) if p['id']=='latissimus_dorsi')
    for side,offset in [('L',0),('R',1)]:
        code=1+2*part_index+offset
        selections.append(dict(part='latissimus_dorsi',muscle='latissimus_dorsi',group='upper_back',side=side,
            code=code,vertices=int(np.sum(ids==code)),available=bool(np.any(ids==code))))
    (OUT/'selections.json').write_text(json.dumps(selections,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
