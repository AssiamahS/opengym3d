"""Bounded attachment diagnostics; never replace an accepted or source asset.

Power sharpening is a rejected-or-reviewable experiment, not anatomy approval.
All measurements use the decoded exported candidate, including FLOAT32 weights.
"""
import json
from pathlib import Path
import shutil
import sys
import numpy as np

from heatsy_repair import Rig, ROOT, export_weights
from heatsy_validate import asset, sha
from heatsy_squat import sample

OUT = ROOT / 'outputs/heatsy-attachment'
BASELINE = ROOT / 'outputs/heatsy-repair/heatsy-squat.glb'


def sharpen(weights, rest_y, exponent):
    """Concentrate existing influences, retaining the existing sole constraint."""
    if not np.isfinite(exponent) or exponent < 1:
        raise ValueError('Exponent must be finite and at least one')
    if not np.isfinite(weights).all() or np.any(weights < 0) or np.any(weights.sum(1) <= 0):
        raise ValueError('Invalid skin weights')
    values = weights ** exponent
    values /= values.sum(1)[:, None]
    alpha = np.clip((rest_y - .10) / .06, 0, 1)
    alpha = alpha * alpha * (3 - 2 * alpha)
    return weights * (1 - alpha[:, None]) + values * alpha[:, None]


def soften(weights, rest_y, strength):
    """Bounded-slope influence compression; exact zeros stay zero (no new bones)."""
    if not np.isfinite(strength) or strength < 0:
        raise ValueError('Strength must be finite and nonnegative')
    values = weights / (1 + strength * weights)
    values /= values.sum(1)[:, None]
    alpha = np.clip((rest_y - .10) / .06, 0, 1)
    alpha = alpha * alpha * (3 - 2 * alpha)
    return weights * (1 - alpha[:, None]) + values * alpha[:, None]


def edge_terms(x, weights, operators, edges):
    """Exact vector decomposition; magnitudes alone must never be added."""
    a, b = edges.T
    mean = (weights[a] + weights[b]) / 2
    delta = weights[b] - weights[a]
    average_operator = (mean @ operators[:, :3, :3].reshape(len(operators), 9)).reshape(-1, 3, 3)
    geometric = np.einsum('nik,nk->ni', average_operator, x[b] - x[a])
    gradient_operator = (delta @ operators[:, :3, :].reshape(len(operators), 12)).reshape(-1, 3, 4)
    gradient = np.einsum('nik,nk->ni', gradient_operator, np.c_[(x[a] + x[b]) / 2, np.ones(len(a))])
    return geometric, gradient, np.linalg.svd(average_operator, compute_uv=False)


def decomposition(rig, decoded, world, posed):
    actual = np.linalg.norm(posed[rig.edges[:, 1]] - posed[rig.edges[:, 0]], axis=1)
    ratios = actual / np.maximum(rig.length, 1e-12)
    report = {}
    ops = world[rig.joints] @ decoded['ibm']
    for region, mask in rig.regions.items():
        eligible = np.flatnonzero(mask & (rig.length >= .001))
        # Most compressed and largest absolute-change edges are both retained.
        selected = np.unique(np.r_[eligible[np.argsort(ratios[eligible])[:10]],
            eligible[np.argsort(abs(actual[eligible] - rig.length[eligible]))[-10:]]])
        edges = rig.edges[selected]
        geometric, gradient, singular = edge_terms(decoded['attrs']['POSITION'], decoded['weights'], ops, edges)
        exact = posed[edges[:, 1]] - posed[edges[:, 0]]
        np.testing.assert_allclose(geometric + gradient, exact, atol=1e-12, rtol=0)
        report[region] = [dict(vertices=edge.tolist(), parts=[rig.part.get(int(rig.ids[i]), 'unlabelled') for i in edge],
            rest_mm=float(rig.length[index]*1000), posed_mm=float(actual[index]*1000), ratio=float(ratios[index]),
            geometric_mm=(g*1000).tolist(), gradient_mm=(d*1000).tolist(),
            constant_weight_ratio=float(np.linalg.norm(g)/rig.length[index]),
            average_operator_singular_values=s.tolist(),
            endpoint_weights=[{n:float(w) for n,w in zip(rig.names, decoded['weights'][i]) if w>0} for i in edge])
            for index,edge,g,d,s in zip(selected,edges,geometric,gradient,singular)]
    return report


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    checkpoint = OUT / 'protected.json'
    if not checkpoint.exists():
        protected = {}
        for folder in ('outputs/bodyweight','outputs/heatsy-probe','outputs/heatsy-squat',
                       'outputs/heatsy-bodyweight','outputs/heatsy-repair','motions','work/heatsy/model'):
            for path in (ROOT/folder).rglob('*'):
                if path.is_file() and path.name not in ('server.log','server-error.log'):
                    protected[path.relative_to(ROOT).as_posix()] = sha(path)
        checkpoint.write_text(json.dumps(protected, indent=2))
    protected = json.loads(checkpoint.read_text())
    assert all(sha(ROOT/p) == digest for p,digest in protected.items())
    r = Rig(); base = asset(BASELINE)
    # Use the delivered GLB's coordinates/binds for both controlled and animated poses.
    r.x = base['attrs']['POSITION']; r.a['ibm'] = base['ibm']
    poses = r.controlled()
    report = dict(status='PARTIAL', baseline_sha256=sha(BASELINE), candidates={},
        source_sha256=sha(ROOT/'work/heatsy/model/body_superficial.app5m.glb'),
        motion_sha256=sha(ROOT/'motions/synthetic/squat.json'), protected_files=len(protected),
        anatomy_approved=False, method='Rest-space influence contrast experiments; no pose fitting')
    heat={name:{} for name in poses}
    for name in ('LICENSE','NOTICE.md','IMPORTER-NOTICE.md','MOTION-CODE-MIT.txt'):
        shutil.copy2(BASELINE.parent/name, OUT/name)
    trials = [('baseline', None, 0)] + [(f'power-{p:g}', sharpen, p) for p in (1.1,1.25,1.5)]
    trials += [(f'soften-{s:g}', soften, s) for s in (.5,1,2)]
    for name, transform, parameter in trials:
        path = BASELINE if transform is None else OUT/f'{name}.glb'
        if transform is not None:
            weights = transform(base['weights'], r.rest[:,1], parameter)
            export_weights(weights, path, dict(method=transform.__name__,parameter=parameter,
                parent_sha256=sha(BASELINE), no_pose_fitting=True, foot_preservation=True, accepted=False))
        decoded = asset(path)
        metrics = {}
        for pose,world in poses.items():
            y = r.deform(world, decoded['weights'])
            if pose in ('standing','descent','bottom'):
                y,world = sample(decoded['g'],decoded['b'],dict(standing=0,descent=.75,bottom=1.5)[pose])
            metrics[pose] = r.metrics(y)
            if name in ('baseline','soften-0.5'):
                heat[pose]['before' if name=='baseline' else 'after']=r.heat(y).tolist()
            if pose == 'bottom':
                (OUT/f'{name}-edge-terms.json').write_text(json.dumps(decomposition(r,decoded,world,y),indent=2))
        report['candidates'][name] = dict(glb_sha256=sha(path), parameter=parameter, poses=metrics)
        m=metrics['bottom']
        print(name, json.dumps({k:{f:m[k][f] for f in ('maximum','over2','below_half','max_absolute_change_mm')} for k in ('all','torso','hips','knees','arms')}), m['surface'], flush=True)
    assert all(sha(ROOT/p) == digest for p,digest in protected.items())
    (OUT/'experiments.json').write_text(json.dumps(report,indent=2))
    (OUT/'strain-heat.json').write_text(json.dumps(heat))
    pose_locals={name:[(np.linalg.inv(world[r.parent[i]])@world[i] if i in r.parent else world[i]).T.ravel().tolist()
        for i in r.joints] for name,world in poses.items()}
    (OUT/'diagnostic-poses.json').write_text(json.dumps(dict(names=r.names,poses=pose_locals)))
    print('PARTIAL: experiments only; no candidate automatically accepted')
    return 2


if __name__ == '__main__':
    sys.exit(main())
