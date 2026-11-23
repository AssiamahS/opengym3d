"""One bounded animated milestone; exit 2 means diagnostic outputs, deformation blocked."""
import json
import subprocess
import sys
import time
from heatsy_squat import ROOT,OUT

STAGES=[]


def run(args,log):
    print('Running:',' '.join(map(str,args)),flush=True)
    start=time.perf_counter()
    with (OUT/log).open('w',encoding='utf-8') as stream:
        subprocess.run(list(map(str,args)),cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True)
    STAGES.append(dict(stage=log,seconds=time.perf_counter()-start))


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    start=time.perf_counter()
    (OUT/'milestone.json').write_text(json.dumps({'status':'BUILDING','technical_pass':False,'review_ready':False}))
    try:
        for script,log in [('heatsy_squat_prepare.py','prepare.log'),('heatsy_squat.py','retarget.log'),
                           ('heatsy_squat_validate.py','validation.log'),('heatsy_squat_diagnose.py','diagnose.log')]:
            run([sys.executable,'studio/'+script],log)
        run([sys.executable,'-m','unittest','discover','-s','tests','-v'],'tests.log')
        run(['node','studio/validate_gltf.mjs',str(OUT/'heatsy-squat.glb')],'gltf.log')
        run([ROOT/'work/toolchain/blender-4.5.11-windows-x64/blender.exe','-b','--factory-startup',
             '--python-exit-code','1','-P','studio/heatsy_squat_blender.py'],'blender-parity.log')
        run(['node','studio/heatsy_squat_capture.mjs'],'capture.log')
        run([sys.executable,'studio/heatsy_squat_media.py'],'media.log')
        # The last stage deliberately returns 2 when technical checks pass but
        # deformation is unacceptable. Preserve its detailed PARTIAL report.
        from heatsy_squat_finish import main as finish
        result=finish()
        (OUT/'build-timing.json').write_text(json.dumps(dict(total_seconds=time.perf_counter()-start,stages=STAGES),indent=2))
        return result
    except Exception as exc:
        (OUT/'milestone.json').write_text(json.dumps({'status':'FAIL','technical_pass':False,'error':str(exc)},indent=2))
        raise


if __name__=='__main__':sys.exit(main())
