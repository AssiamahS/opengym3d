"""Reproduce the isolated equipment proof, including failed contact evidence."""
import json
import os
from pathlib import Path
import subprocess
import sys
from equipment_media import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/equipment-use'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'milestone.json').write_text(json.dumps(dict(status='BUILDING',technical_pass=False)))
    if not (OUT/'protected.json').exists():
        protected={p.relative_to(ROOT).as_posix():sha(p) for folder in ('outputs/bodyweight','outputs/heatsy-probe','outputs/heatsy-bodyweight','outputs/heatsy-repair','outputs/heatsy-attachment','motions/synthetic')
            for p in (ROOT/folder).rglob('*') if p.is_file() and p.name not in ('server.log','server-error.log')}
        (OUT/'protected.json').write_text(json.dumps(protected,indent=2))
    def run(args,log,allowed=(0,)):
        with (OUT/log).open('w',encoding='utf-8') as stream:
            result=subprocess.run([str(a) for a in args],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        if result.returncode not in allowed:raise RuntimeError(f'{log}: exit {result.returncode}')
    blender=[ROOT/'work/toolchain/blender-4.5.11-windows-x64/blender.exe','-b','--factory-startup','--python-exit-code','1','-P']
    run(blender+['studio/goblet_build.py'],'build.log')
    run([sys.executable,'studio/goblet_validate.py'],'contact-validation.log',(0,2))
    run(blender+['studio/goblet_validate.py','--','--hand-crossings'],'hand-crossings.log')
    for file in ('goblet.glb','dumbbell.glb'):run(['node','studio/validate_gltf.mjs',OUT/file],file+'.validation.log')
    run([sys.executable,'pipeline/qa_glb.py',OUT/'goblet.glb'],'joint-qa.log')
    run([sys.executable,'-m','unittest','discover','-s','tests','-v'],'tests.log')
    run(['node','studio/equipment_capture.mjs'],'capture.log')
    run([sys.executable,'studio/equipment_media.py'],'media.log')
    run(['node','studio/equipment_capture.mjs','--preview-only'],'preview-check.log')
    run([sys.executable,'studio/equipment_verify.py'],'integration.log')
    finish()

def finish():
    digest=sha(OUT/'goblet.glb')
    contact=json.loads((OUT/'contact-validation.json').read_text());cross=json.loads((OUT/'hand-crossings.json').read_text())
    integration=json.loads((OUT/'integration.json').read_text())
    assert all(r['glb_sha256']==digest for r in (contact,cross,integration))
    technical=contact['technical_pass'] and all(p['with_0_1mm_margin']==0 for p in cross['poses'].values()) and integration['status']=='PASS'
    result=dict(status='TECHNICAL_PASS' if technical else 'PARTIAL',technical_pass=technical,
        visual='PARTIAL: coarse procedural finger contours; human review required',movement='unapproved synthetic fixture',human_approval='unapproved',public_ready=False,
        glb_sha256=digest,equipment_sha256=sha(OUT/'dumbbell.glb'),contact_checks=contact['checks'],hand_crossings=cross['poses'],
        protected_files_unchanged=integration['protected_files_unchanged'])
    (OUT/'milestone.json').write_text(json.dumps(result,indent=2))
    variation=json.loads((OUT/'variation.json').read_text())
    variation.update(technical='PASS' if technical else 'PARTIAL',visual='PARTIAL - finger contours need review',movement='unapproved',humanApproval='unapproved')
    (OUT/'variation.json').write_text(json.dumps(variation,indent=2))
    print(json.dumps(result,indent=2))
    return 0 if technical else 2

if __name__=='__main__':
    try:
        if '--finish-only' in sys.argv:code=finish()
        else:main();code=0 if json.loads((OUT/'milestone.json').read_text())['technical_pass'] else 2
    except Exception as exc:
        (OUT/'milestone.json').write_text(json.dumps(dict(status='FAIL',technical_pass=False,error=str(exc)),indent=2));raise
    sys.exit(code)
