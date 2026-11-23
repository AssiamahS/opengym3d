"""Reproduce the isolated repair proof; exit 2 still means unresolved deformation."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import hashlib
import zipfile
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/heatsy-repair'
STAGES=[]


def run(args,log,env=None):
    start=time.perf_counter();print('Running:',' '.join(map(str,args)),flush=True)
    with (OUT/log).open('w',encoding='utf-8') as stream:
        result=subprocess.run(list(map(str,args)),cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,env=env)
    STAGES.append(dict(stage=log,seconds=time.perf_counter()-start,exit_code=result.returncode))
    if result.returncode:raise subprocess.CalledProcessError(result.returncode,args)


def main():
    OUT.mkdir(parents=True,exist_ok=True);start=time.perf_counter()
    checkpoint=OUT/'checkpoints';checkpoint.mkdir(exist_ok=True)
    if not (checkpoint/'baseline-hashes.json').exists():
        paths=[p for d in ('outputs/bodyweight','outputs/heatsy-probe','outputs/heatsy-squat','outputs/heatsy-bodyweight','motions/synthetic','work/heatsy/model')
               for p in (ROOT/d).rglob('*') if p.is_file() and p.name not in ('server.log','server-error.log')]
        (checkpoint/'baseline-hashes.json').write_text(json.dumps({p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2))
        with zipfile.ZipFile(checkpoint/'before-repair-source.zip','w',zipfile.ZIP_DEFLATED) as archive:
            for folder in ('studio','tests','docs'):
                for p in (ROOT/folder).rglob('*'):
                    if p.is_file() and '__pycache__' not in p.parts:archive.write(p,p.relative_to(ROOT))
    (OUT/'milestone.json').write_text(json.dumps(dict(status='BUILDING',technical_pass=False)))
    try:
        run([sys.executable,'studio/heatsy_repair.py','diagnose'],'diagnosis.log')
        run([sys.executable,'studio/heatsy_repair.py','transforms'],'transforms.log')
        run([sys.executable,'studio/heatsy_repair.py','build'],'build-derivative.log')
        run([sys.executable,'studio/heatsy_repair.py','transforms_after'],'transforms-after.log')
        run([sys.executable,'studio/heatsy_repair_validate.py'],'validation.log')
        run([sys.executable,'-m','unittest','discover','-s','tests','-v'],'tests.log')
        run(['node','studio/validate_gltf.mjs',str(OUT/'heatsy-squat.glb')],'gltf.log')
        blender=[ROOT/'work/toolchain/blender-4.5.11-windows-x64/blender.exe','-b','--factory-startup','--python-exit-code','1','-P']
        run(blender+['studio/heatsy_repair_blender.py'],'blender-parity.log')
        run(blender+['studio/heatsy_repair_intersections.py'],'intersections.log')
        env=dict(os.environ,FMS_HEATSY_OUTPUT='outputs/heatsy-repair',FMS_HEATSY_QUERY='repair=final',FMS_HEATSY_GPU='1')
        run(['node','studio/heatsy_squat_capture.mjs'],'capture.log',env)
        run(['node','studio/heatsy_repair_capture.mjs','--final'],'comparison-capture.log')
        # The existing media encoder is parameterized in-process, not duplicated.
        import heatsy_squat_media
        heatsy_squat_media.OUT=OUT
        media_start=time.perf_counter();heatsy_squat_media.main();STAGES.append(dict(stage='media',seconds=time.perf_counter()-media_start))
        from heatsy_repair_finish import main as finish
        result=finish()
        return result
    except Exception as exc:
        (OUT/'milestone.json').write_text(json.dumps(dict(status='FAIL',technical_pass=False,error=str(exc)),indent=2));raise
    finally:
        (OUT/'build-timing.json').write_text(json.dumps(dict(total_seconds=time.perf_counter()-start,stages=STAGES),indent=2))


if __name__=='__main__':sys.exit(main())
