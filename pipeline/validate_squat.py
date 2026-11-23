"""Fail-closed gate scoped to the local synthetic bodyweight preview.

Passing technical checks never grants human approval or public readiness.
"""
import hashlib
import json
import math
import sys
from pathlib import Path
import qa_glb
import anatomy_qa


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def required_qa():
    keys = {("skeleton", "rig"), ("animation", "clip"), ("loop", "clip"),
            ("prop_present", "none")}
    for chain in qa_glb.CHAINS.values():
        keys.update(("bone_length", f"{a}->{b}") for a, b in zip(chain, chain[1:]))
    keys.update(("hinge", j) for j in qa_glb.HINGES)
    keys.update(("spike", j) for j in qa_glb.WATCH)
    keys.update(("twist", j) for j in qa_glb.WATCH if j != "root")
    keys.update(("foot_slide", j) for j in ("foot.L", "foot.R"))
    keys.update(("anatomy", "squat:" + j) for j in anatomy_qa.PATTERNS["squat"])
    return keys


def audit_qa(report):
    rows = report.get("results", [])
    present = {(r.get("check"), r.get("joint")) for r in rows if r.get("status") == "PASS"}
    missing = sorted(required_qa() - present)
    return not missing and report.get("summary", {}).get("pass") is True, missing


def strict_motion(glb):
    gltf, names, times, frames, rotations = qa_glb.sample_clip(glb, 30)
    required = set(qa_glb.WATCH)
    if not required <= set(names):
        return {"status": "FAIL", "reason": "missing required bones"}
    joints = {gltf['nodes'][i]['name'] for skin in gltf.get('skins', []) for i in skin['joints']}
    if not joints:
        return {"status": "FAIL", "reason": "missing skin joints"}
    checks = []
    def add(name, value, limit):
        checks.append({"check": name, "value": value, "limit": limit,
                       "status": "PASS" if math.isfinite(value) and value <= limit else "FAIL"})
    for foot in ("foot.L", "foot.R"):
        # Whole interval is declared planted; not the upstream per-sample shortcut.
        add("planted_drift_" + foot, max(qa_glb.dist(f[foot], frames[0][foot]) for f in frames), .020)
    add("root_closure_m", qa_glb.dist(frames[0]['root'], frames[-1]['root']), .005)
    add("max_joint_loop_degrees", max(qa_glb.q_angle(rotations[0][j], rotations[-1][j]) for j in joints), 2)
    return {"status": "PASS" if all(c['status'] == 'PASS' for c in checks) else "FAIL",
            "glb_sha256": sha(glb), "samples": len(times), "checks": checks,
            "limitations": ["Joint positions do not measure skin-floor penetration", "Not movement/anatomy signoff"]}


def aggregate(out):
    out = Path(out)
    glb = out / 'squat-technical.glb'
    errors = []
    if not glb.is_file():
        return {"technical_pass": False, "public_ready": False, "errors": ["missing GLB"]}
    digest = sha(glb)
    required = {'qa': 'squat-technical.glb.qa.json', 'gltf': 'squat-technical.glb.gltf.json',
                'strict': 'strict-motion.json', 'preview': 'preview.json', 'media': 'media.json',
                'parity': 'viewer-parity.json'}
    for kind, filename in required.items():
        try:
            report = json.loads((out / filename).read_text())
            if report.get('glb_sha256') != digest:
                errors.append(f'{kind}: missing or stale GLB hash')
            if kind == 'qa':
                ok, missing = audit_qa(report)
                if not ok: errors.append(f'qa: failed/skipped/absent required checks: {missing}')
            elif report.get('status') != 'PASS':
                errors.append(f'{kind}: required check did not pass')
            if kind == 'gltf' and report.get('issues', {}).get('numErrors') != 0:
                errors.append('gltf: validator errors or missing result')
            if kind == 'strict' and (len(report.get('checks', [])) != 4 or
                    any(c.get('status') != 'PASS' for c in report.get('checks', []))):
                errors.append('strict: failed/skipped/absent checks')
            if kind == 'preview':
                if not {'front', 'side', 'three'} <= set(report.get('views', [])) or report.get('errors'):
                    errors.append('preview: incomplete views or browser errors')
                floor = report.get('mesh_floor_by_frame', [])
                if len(floor) != report.get('frame_count') or not floor or min(floor) < -.005:
                    errors.append('preview: absent floor samples or skin penetrates floor more than 5 mm')
            if kind == 'media':
                for artifact, field in [('squat-technical.mp4','mp4_sha256'), ('squat-technical.png','poster_sha256')]:
                    if not (out/artifact).exists() or report.get(field) != sha(out/artifact):
                        errors.append(f'media: missing/stale {artifact}')
        except (OSError, ValueError, TypeError):
            errors.append(f'{kind}: missing or invalid report')
    for filename in ('squat-technical.mp4', 'squat-technical.png', 'squat-technical.sheet.png', 'provenance.json'):
        if not (out / filename).is_file() or not (out / filename).stat().st_size:
            errors.append(f'missing required artifact: {filename}')
    try:
        provenance = json.loads((out/'provenance.json').read_text())
        if (provenance.get('glb_sha256') != digest or
                provenance.get('motion', {}).get('source', {}).get('kind') != 'synthetic' or
                provenance.get('motion', {}).get('license') != 'MIT'):
            errors.append('provenance: source identity/license/hash is missing or incompatible with fixture')
    except (OSError, ValueError, TypeError):
        errors.append('provenance: missing or invalid')
    return {"technical_pass": not errors, "public_ready": False,
            "movement_approved": False, "appearance_approved": False,
            "input_kind": "synthetic fixture", "glb_sha256": digest, "errors": errors}


def viewer_parity(out):
    """Compare independent Python FK against the actual browser bone samples."""
    preview = json.loads((out/'preview.json').read_text())
    gltf, blob = qa_glb.load_glb(out/'squat-technical.glb')
    clip = qa_glb.Clip(gltf, blob)
    worst, count = 0.0, 0
    for frame, browser in preview['sampled_bones'].items():
        matrices = clip.world(int(frame)/preview['fps'])
        for name in qa_glb.WATCH:
            # Three PropertyBinding sanitizes periods in glTF node names.
            browser_name = name.replace('.', '')
            if browser_name not in browser:
                raise ValueError(f'Browser sample is missing {name}')
            worst = max(worst, qa_glb.dist(browser[browser_name],qa_glb.m_pos(matrices[clip.by_name[name]])))
            count += 1
    return {'status':'PASS' if count and worst < 1e-5 else 'FAIL',
            'glb_sha256':sha(out/'squat-technical.glb'), 'comparisons':count,'max_joint_error_m':worst}


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else 'outputs/bodyweight')
    out.mkdir(parents=True, exist_ok=True)
    # A failed revalidation must never leave an earlier passing verdict in place.
    (out/'validation.json').write_text(json.dumps({'technical_pass':False,
        'public_ready':False,'status':'VALIDATING'}))
    glb = out / 'squat-technical.glb'
    spec = json.loads((Path(__file__).resolve().parent.parent / 'studio/squat.json').read_text())
    results, times = qa_glb.run_qa(glb, spec)
    (out / 'squat-technical.glb.qa.json').write_text(json.dumps({"glb_sha256": sha(glb),
        "summary": qa_glb.summarise(results), "results": results, "duration": times[-1],
        "thresholds": qa_glb.THRESH}, indent=2))
    (out / 'strict-motion.json').write_text(json.dumps(strict_motion(glb), indent=2))
    parity = viewer_parity(out)
    (out/'viewer-parity.json').write_text(json.dumps(parity,indent=2))
    report = aggregate(out)
    (out / 'validation.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0 if report['technical_pass'] else 1


if __name__ == '__main__':
    sys.exit(main())
