"""Independent decoded GLB contact/kinematic checks, never an anatomy approval."""
import json
import hashlib
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'pipeline'))
sys.path.insert(0,str(ROOT/'studio'))
from qa_glb import Clip
from heatsy_gltf import load,accessor
from equipment_paths import OUT

def cylinder_distance(x,center,half,radius):
    q=np.column_stack([abs(x[:,0]-center)-half,np.linalg.norm(x[:,1:],axis=1)-radius])
    return np.linalg.norm(np.maximum(q,0),axis=1)+np.minimum(np.max(q,axis=1),0)


def validate_grip_preservation(candidate,blob):
    """Pose-only continuation: preserve hand proportions, skin and other motion."""
    baseline,base_blob=load(ROOT/'outputs/equipment-use/goblet.glb')
    def body(g):
        node=next(n for n in g['nodes'] if 'skin' in n)
        return g['meshes'][node['mesh']]['primitives'][0],g['skins'][node['skin']]
    old,old_skin=body(baseline);new,new_skin=body(candidate)
    for attr in ('POSITION','NORMAL','JOINTS_0','WEIGHTS_0'):
        np.testing.assert_array_equal(accessor(baseline,base_blob,old['attributes'][attr]),accessor(candidate,blob,new['attributes'][attr]))
    np.testing.assert_array_equal(accessor(baseline,base_blob,old['indices']),accessor(candidate,blob,new['indices']))
    assert [baseline['nodes'][i]['name'] for i in old_skin['joints']]==[candidate['nodes'][i]['name'] for i in new_skin['joints']]
    np.testing.assert_array_equal(accessor(baseline,base_blob,old_skin['inverseBindMatrices']),accessor(candidate,blob,new_skin['inverseBindMatrices']))
    def tracks(g,b):
        result={}
        for animation in g['animations']:
            for channel in animation['channels']:
                name=g['nodes'][channel['target']['node']]['name']
                if name.startswith('finger'):continue
                sampler=animation['samplers'][channel['sampler']]
                result[(name,channel['target']['path'])]=(accessor(g,b,sampler['input']),accessor(g,b,sampler['output']))
        return result
    previous,current=tracks(baseline,base_blob),tracks(candidate,blob)
    assert previous.keys()==current.keys()
    for key in previous:
        for before,after in zip(previous[key],current[key]):np.testing.assert_allclose(before,after,atol=1e-7,rtol=0)
    return dict(rest_geometry_skin_bind_identical=True,nonfinger_tracks_unchanged=len(previous),tolerance=1e-7)

def main():
    (OUT/'contact-validation.json').write_text(json.dumps(dict(status='BUILDING',technical_pass=False)))
    path=OUT/'goblet.glb';digest=hashlib.sha256(path.read_bytes()).hexdigest();g,b=load(path);clip=Clip(g,b)
    preservation=validate_grip_preservation(g,b)
    original,blob=load(ROOT/'outputs/bodyweight/squat-technical.glb');source=Clip(original,blob)
    node=next(n for n in g['nodes'] if 'skin' in n);prim=g['meshes'][node['mesh']]['primitives'][0]
    attr=prim['attributes'];x=accessor(g,b,attr['POSITION']);js=accessor(g,b,attr['JOINTS_0']).astype(int);ws=accessor(g,b,attr['WEIGHTS_0'])
    skin=g['skins'][node['skin']];names=[g['nodes'][j]['name'] for j in skin['joints']]
    ibm=accessor(g,b,skin['inverseBindMatrices']).reshape(-1,4,4).transpose(0,2,1)
    hands={s:np.sum(ws*np.array([n.endswith('.'+s) and n.startswith(('wrist','finger','metacarpal')) for n in names])[js],axis=1)>.5 for s in ('L','R')}
    tri=accessor(g,b,prim['indices']).reshape(-1,3).astype(int)
    allhand=hands['L']|hands['R'];hp=np.c_[x,np.ones(len(x))]
    records=[];start=None;relative0=None;max_joint=0.;crossings={}
    for index,t in enumerate(np.linspace(0,clip.duration,181)):
        world=clip.world(float(t));ops=np.array([world[j] for j in skin['joints']])@ibm
        posed=sum(ws[:,k,None]*np.einsum('nij,nj->ni',ops[js[:,k]],hp)[:,:3] for k in range(4))
        assert np.isfinite(posed).all()
        equipment=np.array(world[clip.by_name['Dumbbell']]);inv=np.linalg.inv(equipment)
        local=(np.c_[posed,np.ones(len(posed))]@inv.T)[:,:3]
        shaft=cylinder_distance(local,0,.075,.017)
        sdf=np.minimum.reduce([shaft,cylinder_distance(local,-.098,.0275,.055),cylinder_distance(local,.098,.0275,.055)])
        chest=np.array(world[clip.by_name['spine01']]);relative=np.linalg.inv(chest)@equipment
        if start is None:start=posed.copy();relative0=relative.copy()
        sourceworld=source.world(float(t)+1/30)
        for name in ('root','foot.L','foot.R','upperleg01.L','upperleg01.R','lowerleg01.L','lowerleg01.R'):
            max_joint=max(max_joint,float(np.max(abs(np.array(world[clip.by_name[name]])[:3,3]-np.array(sourceworld[source.by_name[name]])[:3,3]))))
        record=dict(time=float(t),equipment_chest_component_drift=float(np.max(abs(relative-relative0))),
                    nonhand_max_penetration_m=max(0.,float(-sdf[~allhand].min())),hands={})
        for side,mask in hands.items():
            # Shaft contact restricted to exposed handle between the two heads.
            eligible=mask&(abs(local[:,0])<.0705)
            distance=float(np.min(abs(shaft[eligible]))) if eligible.any() else float('inf')
            wrist=np.array(world[clip.by_name['wrist.'+side]])[:3,3]
            indexp=np.array(world[clip.by_name['finger2-1.'+side]])[:3,3]
            pinky=np.array(world[clip.by_name['finger5-1.'+side]])[:3,3]
            direction=(indexp+pinky)/2-wrist;direction/=np.linalg.norm(direction)
            axis=equipment[:3,0]/np.linalg.norm(equipment[:3,0])
            normal=np.cross(indexp-wrist,pinky-wrist);normal/=np.linalg.norm(normal)
            knuckle_center=(indexp+pinky)/2
            knuckle_inward=equipment[:3,3]-knuckle_center;knuckle_inward-=axis*np.dot(axis,knuckle_inward);knuckle_inward/=np.linalg.norm(knuckle_inward)
            palm_center=(wrist+knuckle_center)/2
            inward=equipment[:3,3]-palm_center;inward-=axis*np.dot(axis,inward);inward/=np.linalg.norm(inward)
            record['hands'][side]=dict(handle_surface_gap_m=distance,max_penetration_m=max(0.,float(-sdf[mask].min())),
                wrist_to_shaft_angle_deg=float(np.degrees(np.arccos(np.clip(abs(np.dot(direction,axis)),0,1)))),
                palm_plane_alignment_abs=float(abs(np.dot(normal,inward))),
                knuckle_radial_alignment_abs=float(abs(np.dot(normal,knuckle_inward))),
                near_handle_vertices=int(np.sum(eligible&(abs(shaft)<.005))))
        records.append(record)
        if index in (0,45,90):
            crossings[str(index)]=posed
    np.savez_compressed(OUT/'hand-crossings-input.npz',glb_sha256=np.array(digest),tri=tri,left=hands['L'],right=hands['R'],**crossings)
    max_gap=max(r['hands'][s]['handle_surface_gap_m'] for r in records for s in hands)
    hand_depth=max(r['hands'][s]['max_penetration_m'] for r in records for s in hands)
    body_depth=max(r['nonhand_max_penetration_m'] for r in records)
    drift=max(r['equipment_chest_component_drift'] for r in records)
    seam=float(np.max(abs(posed-start)))
    orientation_min=min(r['hands'][s]['wrist_to_shaft_angle_deg'] for r in records for s in hands)
    alignment_min=min(r['hands'][s]['palm_plane_alignment_abs'] for r in records for s in hands)
    checks=dict(contact=max_gap<.005,hand_penetration=hand_depth<.003,major_body_intersections=body_depth<.003,
        equipment_stability=drift<1e-4,loop=seam<1e-5,source_lower_body=max_joint<1e-5,
        grip_direction=orientation_min>60,palm_plane=alignment_min>.7)
    passed=all(checks.values())
    report=dict(status='PASS' if passed else 'PARTIAL',technical_pass=passed,checks=checks,samples=181,
        glb_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),max_handle_gap_m=max_gap,max_hand_penetration_m=hand_depth,
        max_nonhand_penetration_m=body_depth,max_equipment_chest_drift=drift,mesh_seam_m=seam,
        max_source_lower_body_component_error_m=max_joint,min_grip_angle_deg=orientation_min,min_palm_plane_alignment=alignment_min,
        visual='unapproved',movement='unapproved',human_approval='unapproved',records=records,preservation=preservation,
        collision_scope='All body vertices against analytic generator cylinders at181 poses; head cylinders conservatively enclose polygonal heads. Does not establish absence of triangle-only crossings or all self-collisions; hand/hand surface crossings tested separately.')
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,'Asset changed during validation'
    (OUT/'contact-validation.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='records'},indent=2))
    return 0 if passed else 2

def hand_crossings():
    from mathutils.bvhtree import BVHTree
    from heatsy_repair_intersections import crosses
    data=np.load(OUT/'hand-crossings-input.npz');tri=data['tri'];left=tri[np.all(data['left'][tri],axis=1)];right=tri[np.all(data['right'][tri],axis=1)]
    assert str(data['glb_sha256'])==hashlib.sha256((OUT/'goblet.glb').read_bytes()).hexdigest(),'Stale hand-crossing input'
    report={}
    for key in ('0','45','90'):
        y=data[key];a=BVHTree.FromPolygons(y.tolist(),left.tolist(),all_triangles=True);b=BVHTree.FromPolygons(y.tolist(),right.tolist(),all_triangles=True)
        pairs=np.array(a.overlap(b),int);count=deep=0
        if len(pairs):
            p=y[left[pairs[:,0]]];q=y[right[pairs[:,1]]];hit=np.zeros(len(pairs),bool);margin=hit.copy()
            for j in range(3):
                h,s=crosses(p[:,j],p[:,(j+1)%3],q[:,0],q[:,1],q[:,2]);hit|=h;margin|=s
                h,s=crosses(q[:,j],q[:,(j+1)%3],p[:,0],p[:,1],p[:,2]);hit|=h;margin|=s
            count=int(hit.sum());deep=int(margin.sum())
        report[key]=dict(crossing_pairs=count,with_0_1mm_margin=deep)
    (OUT/'hand-crossings.json').write_text(json.dumps(dict(glb_sha256=hashlib.sha256((OUT/'goblet.glb').read_bytes()).hexdigest(),poses=report),indent=2))
    print(report)

if __name__=='__main__':
    if '--hand-crossings' in sys.argv:hand_crossings()
    else:sys.exit(main())
