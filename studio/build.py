"""One local bodyweight build. Required failures return nonzero; never publishes."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'pipeline'))
from validate_squat import sha


def run(args, log=None, check=True, **kwargs):
    print(' '.join(str(a) for a in args), flush=True)
    if log:
        with Path(log).open('w', encoding='utf-8') as stream:
            return subprocess.run(args, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                  check=check, **kwargs)
    return subprocess.run(args, cwd=ROOT, check=check, **kwargs)


def finish_media():
    out = ROOT / 'outputs/bodyweight'
    preview = json.loads((out / 'preview.json').read_text())
    n, fps = preview['frame_count'], preview['fps']
    for view in ('front', 'side', 'three'):
        dest = out / ('squat-technical.mp4' if view == 'three' else f'{view}.mp4')
        run(['ffmpeg', '-y', '-v', 'error', '-framerate', str(fps), '-i',
             f'work/frames-{view}/%04d.png', '-frames:v', str(n), '-c:v', 'libx264',
             '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(dest)])
        # Decode actual MP4 for review (not merely the pre-encode source frames).
        run(['ffmpeg', '-y', '-v', 'error', '-i', str(dest), '-vf',
             rf'select=not(mod(n\,{max(1, n//6)})),scale=256:256,tile=6x1',
             '-frames:v', '1', str(out / f'{view}-mp4-strip.png')])
        if view in ('front', 'side'):
            run(['ffmpeg','-y','-v','error','-i',str(dest),'-vf',
                 f'scale=160:160,tile=10x{(n+9)//10}', '-frames:v','1',str(out/f'{view}-all-frames.png')])
    metadata = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
                        '-show_format', '-of', 'json', str(out / 'squat-technical.mp4')]))
    stream = metadata['streams'][0]
    mp4_duration = float(metadata['format']['duration'])
    # PSNR checks the encoded video against the exact viewer frames, every frame.
    stats = subprocess.run(['ffmpeg', '-v', 'info', '-i', str(out / 'squat-technical.mp4'),
        '-framerate', str(fps), '-i', 'work/frames-three/%04d.png', '-lavfi',
        '[0:v][1:v]psnr', '-frames:v', str(n), '-f', 'null', '-'], cwd=ROOT,
        capture_output=True, text=True, check=True).stderr
    import re
    match = re.search(r'average:([\d.]+|inf)', stats)
    psnr = float(match.group(1)) if match else 0
    ok = (abs(mp4_duration - preview['duration']) <= 1/fps and int(stream['nb_frames']) == n
          and psnr > 35 and stream['pix_fmt'] == 'yuv420p')
    report = dict(status='PASS' if ok else 'FAIL', glb_sha256=sha(out/'squat-technical.glb'),
                  mp4_sha256=sha(out/'squat-technical.mp4'), poster_sha256=sha(out/'squat-technical.png'),
                  duration=mp4_duration, frames=int(stream['nb_frames']), fps=stream['r_frame_rate'],
                  psnr_db=psnr, format=metadata, source='same final GLB rendered by studio/viewer.js')
    (out/'media.json').write_text(json.dumps(report, indent=2))


def provenance():
    out = ROOT/'outputs/bodyweight'
    motion = json.loads((ROOT/'motions/synthetic/squat.json').read_text())
    sources = ['pipeline/synthetic_squat.py', 'pipeline/build_exercise.py', 'studio/squat.json',
               'studio/viewer.js', 'studio/capture.mjs', 'package-lock.json', 'motions/synthetic/squat.json']
    files = {p: sha(ROOT/p) for p in sources}
    character = ROOT/'work/toolchain/addons/mpfb/data'
    for p in [character/'3dobjs/base.obj', character/'rigs/standard/rig.default.json',
              character/'rigs/standard/weights.default.json']:
        files[str(p.relative_to(ROOT)).replace('\\', '/')] = sha(p)
    report = dict(upstream={'url':'https://github.com/AssiamahS/opengym3d',
        'commit':'ea3a60130fdcfb3c4771e44d09f84ebab4ee9bae','license':'MIT'},
        motion={k:motion[k] for k in ('source','license','technical_preview','limitations')},
        character={'name':'MPFB 2.0.16 core MakeHuman mesh, targets, default rig and weights',
        'asset_license':'CC0-1.0','addon_license':'GPL-3.0-or-later',
        'license_files':['licenses/MPFB-LICENSE.md','licenses/MPFB-ASSETS-CC0.md'],
        'third_party_assets':[]}, equipment=None, textures=None,
        input_sha256=files, glb_sha256=sha(out/'squat-technical.glb'),
        toolchain={'blender':'4.5.11','mpfb':'2.0.16','three':'0.170.0','python':sys.version,
                   'ffmpeg':subprocess.check_output(['ffmpeg','-version'],text=True).splitlines()[0]},
        public_ready=False, note='Synthetic engineering fixture; no capture accuracy or human approval claimed')
    (out/'provenance.json').write_text(json.dumps(report,indent=2))
    shutil.copytree(ROOT/'studio/licenses',out/'licenses',dirs_exist_ok=True)
    shutil.copy2(ROOT/'LICENSE',out/'licenses/OPENGYM-MIT.txt')
    shutil.copy2(ROOT/'studio/ATTRIBUTION.md',out/'ATTRIBUTION.md')


def main():
    os.chdir(ROOT)
    out=ROOT/'outputs/bodyweight'
    out.mkdir(parents=True,exist_ok=True)
    (ROOT/'work').mkdir(exist_ok=True)
    # Invalidate any previous successful verdict before starting another build.
    (out/'validation.json').write_text(json.dumps({'technical_pass':False,'public_ready':False,'status':'BUILDING'}))
    run([sys.executable,'-m','unittest','discover','-s','tests','-v'],out/'tests.log')
    run([sys.executable,'pipeline/synthetic_squat.py'])
    env=dict(os.environ,FITX_ECORCHE='0',FMS_EXPORT_ONLY='1',
             FMS_ADDONS=str(ROOT/'work/toolchain/addons'),BLENDER_USER_RESOURCES=str(ROOT/'work/blender-user'))
    run([str(ROOT/'work/toolchain/blender-4.5.11-windows-x64/blender.exe'),'-b','--factory-startup',
         '--python-exit-code','1','-P','pipeline/build_exercise.py','--','studio/squat.json',str(out)],
         out/'export.log',env=env)
    run(['node','studio/validate_gltf.mjs'])
    run([sys.executable,'pipeline/sheet_glb.py',str(out/'squat-technical.glb')])
    run(['node','studio/capture.mjs'],out/'capture.log')
    finish_media()
    provenance()
    run([sys.executable,'pipeline/validate_squat.py',str(out)])
    files = {str(p.relative_to(out)).replace('\\','/'):{'bytes':p.stat().st_size,'sha256':sha(p)}
             for p in out.rglob('*') if p.is_file() and p.name != 'bundle.json'}
    (out/'bundle.json').write_text(json.dumps({'local_only':True,'files':files},indent=2))
    print('Local technical preview complete; movement/appearance approval remains pending.')


if __name__ == '__main__':
    main()
