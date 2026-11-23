"""One target-specific retarget of the unchanged normalized synthetic squat.

Append animation to the preserved metre-based GLB. No mesh/skin accessor is
decoded for rewriting; the existing normal restoration is an explicit prior step.
"""
import copy
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'pipeline'))
import motion
import qa_glb
from heatsy_gltf import load, save, accessor
from heatsy_validate import asset, matrices, sha

OUT = ROOT / 'outputs/heatsy-bodyweight'
BASE = ROOT / 'outputs/heatsy-probe/compatibility'
MOTION = ROOT / 'motions/synthetic/squat.json'


def timing(data):
    """The closed endpoint is a key, not an extra playback interval."""
    count, fps = len(data['frames']), float(data['fps'])
    assert count >= 2 and np.isfinite(fps) and fps > 0
    return dict(source_frames=count, fps=fps, duration=(count-1)/fps)


def unit(v):
    v = np.asarray(v, dtype=float)
    length = np.linalg.norm(v)
    if length < 1e-10:
        raise ValueError('Zero direction')
    return v / length


def from_matrix(m):
    """Quaternion xyzw, with SVD removing only floating-point scale noise."""
    u, _, v = np.linalg.svd(m[:3, :3])
    r = u @ v
    assert np.linalg.det(r) > 0
    # Symmetric eigenproblem is stable near 180 degrees.
    x, y, z = r[0], r[1], r[2]
    k = np.array([[x[0]-y[1]-z[2], x[1]+y[0], x[2]+z[0], z[1]-y[2]],
                  [x[1]+y[0], y[1]-x[0]-z[2], y[2]+z[1], x[2]-z[0]],
                  [x[2]+z[0], y[2]+z[1], z[2]-x[0]-y[1], y[0]-x[1]],
                  [z[1]-y[2], x[2]-z[0], y[0]-x[1], x[0]+y[1]+z[2]]]) / 3
    values, vectors = np.linalg.eigh(k)
    q = vectors[:, np.argmax(values)]
    return q if q[3] >= 0 else -q


def aim(a, b):
    a, b = unit(a), unit(b)
    dot = float(np.dot(a, b))
    if dot < -.999999:
        axis = unit(np.cross(a, [1,0,0] if abs(a[0]) < .8 else [0,1,0]))
        return np.r_[axis, 0.]
    return unit(np.r_[np.cross(a, b), 1 + dot])


def multiply(a, b):
    return np.asarray(qa_glb.q_mul(a, b))


def inverse(q):
    return np.array([-q[0], -q[1], -q[2], q[3]])


def retarget(g, data):
    assert data['format'] == motion.FORMAT and data['source']['kind'] == 'synthetic'
    assert not any(f.get('twists') for f in data['frames']), 'This fixture has no axial twist targets; reassess before accepting another motion'
    _, rest_world, parents = matrices(g)
    names = {n['name']: i for i, n in enumerate(g['nodes'])}
    restq = {i: from_matrix(m) for i, m in rest_world.items()}
    canonical = motion.rest_bones()
    mapping = {'spine_01':'spine', 'spine_02':'spine', 'spine_03':'chest',
               'neck':'neck', 'head':'head'}
    for side in ('L','R'):
        for name in ('thigh','shin','foot'):
            mapping[f'{name}.{side}'] = f'{name}.{side}'
    arm_children = {}
    for side in ('L','R'):
        arm_children.update({f'upperarm.{side}':(f'forearm.{side}',f'upper_arm.{side}'),
            f'forearm.{side}':(f'hand.{side}',f'forearm.{side}'),
            f'hand.{side}':(f'middle_01.{side}',f'hand.{side}')})
    targets = set(mapping) | set(arm_children) | {'pelvis'}
    targets |= {f'{b}.{side}' for b in ('clavicle','scapula') for side in ('L','R')}
    channels = {names[n]: [] for n in targets}
    translations = []
    pelvis = names['pelvis']
    leg_lengths = []
    for side in ('L','R'):
        positions = [rest_world[names[f'{b}.{side}']][:3,3] for b in ('thigh','shin','foot')]
        leg_lengths.append(sum(np.linalg.norm(b-a) for a,b in zip(positions,positions[1:])))
    source_length = sum(np.linalg.norm(np.array(canonical[b+'.L'][1])-canonical[b+'.L'][0]) for b in ('thigh','shin'))
    root_scale = float(np.mean(leg_lengths)/source_length)
    rest_basis = np.array(motion.REST_BASIS).T
    convert = np.array([[1,0,0],[0,0,1],[0,-1,0]])
    for frame in data['frames']:
        desired = {}
        for name, source in mapping.items():
            h, t = canonical[source]
            r = motion.blender_to_yup(motion._sub(t,h))
            if name.startswith(('thigh.','shin.')):
                child = ('shin.' if name.startswith('thigh.') else 'foot.')+name[-1]
                r = rest_world[names[child]][:3,3]-rest_world[names[name]][:3,3]
            d = motion.blender_to_yup(frame['dirs'][source])
            desired[names[name]] = multiply(aim(r,d),restq[names[name]])
        p = frame['pelvis']
        basis = np.array([p[k] for k in ('left','forward','up')]).T
        desired[pelvis] = multiply(from_matrix(convert @ basis @ rest_basis.T @ convert.T),restq[pelvis])
        torso_delta = aim([0,1,0], motion.blender_to_yup(frame['dirs']['chest']))
        for name, (child, source) in arm_children.items():
            i, j = names[name], names[child]
            rest_dir = rest_world[j][:3,3]-rest_world[i][:3,3]
            delta = aim(rest_dir,motion.blender_to_yup(frame['dirs'][source]))
            desired[i] = multiply(delta,restq[i])
            if name.startswith('upperarm.'):
                side = name[-1]
                elevation = np.degrees(2*np.arccos(np.clip(abs(delta[3]),0,1)))
                follow = np.clip((elevation-30)/120,0,1)
                # Same small girdle-follow policy as build_exercise, applied to
                # this rig's clavicle and leaf scapula. No new shoulder solver.
                for bone, share in [('clavicle',.22),('scapula',.40)]:
                    bi = names[f'{bone}.{side}']
                    partial = qa_glb.q_slerp([0,0,0,1],delta,float(share*follow))
                    desired[bi] = multiply(multiply(torso_delta,partial),restq[bi])
        posed_worldq = {}
        def resolve(i):
            if i in posed_worldq:
                return posed_worldq[i]
            parent = resolve(parents[i]) if i in parents else np.array([0,0,0,1.])
            local = np.array(g['nodes'][i].get('rotation',[0,0,0,1]))
            if i in desired:
                local = unit(multiply(inverse(parent), desired[i]))
                if channels[i] and np.dot(channels[i][-1],local) < 0:
                    local = -local
                channels[i].append(local)
            posed_worldq[i] = multiply(parent,local)
            return posed_worldq[i]
        for i in range(len(g['nodes'])):
            resolve(i)
        translations.append(np.array(g['nodes'][pelvis]['translation'])
            + np.array(motion.blender_to_yup(frame['root']))*root_scale)
    return channels, np.array(translations), dict(root_scale=root_scale,
        mapping=mapping, arms=arm_children, animated_nodes=sorted(targets),
        method='absolute leg and arm aims; target leg-length root-travel scale; canonical direction deltas preserve spine/foot rest calibration; existing small girdle follow',
        **timing(data), source_sha256=sha(MOTION),
        coordinate_conversion='OpenGym metres (+Z up, -Y forward) to glTF metres (+Y up, +Z forward): (x,z,-y)',
        hierarchy={n['name']:g['nodes'][parents[i]]['name'] if i in parents else None for i,n in enumerate(g['nodes'])},
        unmapped_bones=[g['nodes'][i]['name'] for i in g['skins'][0]['joints'] if g['nodes'][i]['name'] not in targets],
        fallback='Unmapped fingers, toes and forearm_twist retain local rest TRS and inherit their animated parent. No twist reference is invented. Hand world aim compensates for the intervening twist node.',
        spine_policy='spine_01 and spine_02 share the canonical spine world delta; spine_03 uses chest. Parent-relative quaternion conversion prevents accumulating that world delta twice.')


def append_animation(g, blob, data, offset=0.):
    g = copy.deepcopy(g)
    blob = bytearray(blob)
    rotations, translations, report = retarget(g,data)
    translations[:,1] += offset
    def add(values, kind):
        values = np.asarray(values,dtype='<f4')
        blob.extend(b'\0'*(-len(blob)%4))
        view = len(g['bufferViews'])
        g['bufferViews'].append({'buffer':0,'byteOffset':len(blob),'byteLength':values.nbytes})
        blob.extend(values.tobytes())
        idx = len(g['accessors'])
        a = {'bufferView':view,'componentType':5126,'count':len(values),'type':kind}
        if kind == 'SCALAR':
            a.update(min=[float(values.min())],max=[float(values.max())])
        g['accessors'].append(a)
        return idx
    time = add(np.arange(report['source_frames'])/report['fps'],'SCALAR')
    anim = {'name':'Heatsy synthetic bodyweight squat — unapproved','samplers':[],'channels':[]}
    def track(node,path,values,kind):
        output = add(values,kind)
        index = len(anim['samplers'])
        anim['samplers'].append({'input':time,'output':output,'interpolation':'LINEAR'})
        anim['channels'].append({'sampler':index,'target':{'node':node,'path':path}})
    for node, values in sorted(rotations.items()):
        track(node,'rotation',values,'VEC4')
    pelvis = next(i for i,n in enumerate(g['nodes']) if n['name']=='pelvis')
    track(pelvis,'translation',translations,'VEC3')
    g['animations'] = [anim]
    report['constant_floor_offset_m'] = offset
    report['mesh_parent_policy'] = 'body_rig and mesh remain static identity; all root travel belongs only to pelvis joint'
    return g,blob,report


def sample(g,b,t,indices=None,normals=False):
    """Independent exported GLB sampling via existing qa_glb.Clip FK + numpy LBS."""
    clip = qa_glb.Clip(g,b)
    evaluated = clip.world(t)
    world = np.array([evaluated[i] for i in range(len(g['nodes']))],dtype=float)
    p = g['meshes'][0]['primitives'][0]
    attrs = {k:accessor(g,b,i) for k,i in p['attributes'].items()}
    idx = np.arange(len(attrs['POSITION'])) if indices is None else np.array(indices)
    skin = g['skins'][0]
    ibm = accessor(g,b,skin['inverseBindMatrices']).reshape(-1,4,4).transpose(0,2,1)
    ops = world[skin['joints']] @ ibm
    js,ws = attrs['JOINTS_0'][idx].astype(int),attrs['WEIGHTS_0'][idx].astype(float)
    blend = sum(ws[:,k,None,None]*ops[js[:,k]] for k in range(4))
    positions = np.einsum('nij,nj->ni',blend,np.c_[attrs['POSITION'][idx],np.ones(len(idx))])[:,:3]
    if normals:
        n = np.einsum('nij,nj->ni',blend[:,:3,:3],attrs['NORMAL'][idx])
        n /= np.linalg.norm(n,axis=1)[:,None]
        return positions,n,world
    return positions,world


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    source = OUT/'roundtrip.glb'
    assert sha(source) == sha(BASE/'roundtrip.glb'), 'Restoration differs from verified baseline'
    data = motion.load(MOTION)
    g,b = load(source)
    interim,blob,_ = append_animation(g,b,data)
    posed,_ = sample(interim,bytes(blob),0)
    # One standing alignment, applied to pelvis in every frame. Never foot IK,
    # per-frame clamping, scale manipulation or a change to source motion.
    offset = -float(posed[:,1].min())
    out,blob,report = append_animation(g,b,data,offset)
    save(OUT/'heatsy-squat.glb',out,blob)
    report.update(baseline_sha256=sha(source),glb_sha256=sha(OUT/'heatsy-squat.glb'),
        movement_approved=False,anatomy_approved=False,public_ready=False)
    (OUT/'retarget.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
