"""Encode the actual exported-model browser frames; never touches older proofs."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/equipment-use'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def run(args):
    return subprocess.run(args,cwd=ROOT,check=True,capture_output=True,text=True)

def main():
    timing=json.loads((OUT/'preview.json').read_text())
    assert timing['status']=='PASS'
    count,fps=timing['frame_count'],timing['fps']
    records=[]
    for view in ('front','side'):
        frames=str(OUT/f'frames-{view}'/'%04d.png');video=OUT/f'{view}.mp4'
        run(['ffmpeg','-y','-v','error','-framerate',str(fps),'-i',frames,'-frames:v',str(count),
             '-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(video)])
        info=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)]).stdout)
        stream=info['streams'][0]
        assert int(stream['nb_frames'])==count
        assert abs(float(info['format']['duration'])-count/fps)<1/fps
        log=run(['ffmpeg','-i',str(video),'-framerate',str(fps),'-i',frames,'-lavfi','[0:v][1:v]psnr',
                 '-frames:v',str(count),'-f','null','-']).stderr
        psnr=float(re.search(r'average:([\d.]+|inf)',log)[1]);assert psnr>35
        run(['ffmpeg','-y','-v','error','-i',str(video),'-vf',f'scale=160:160,tile=10x{(count+9)//10}',
             '-frames:v','1',str(OUT/f'{view}-contact-sheet.png')])
        records.append(dict(view=view,sha256=sha(video),frames=count,psnr_db=psnr,width=stream['width'],height=stream['height']))
        run(['ffmpeg','-y','-v','error','-i',str(video),'-vf','scale=320:320','-an','-c:v','libx264',
             '-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/f'quick-{view}.mp4')])
    run(['ffmpeg','-y','-v','error','-i',str(OUT/'side.mp4'),'-vf','scale=320:320','-an',
         '-c:v','libx264','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/'quick-peek.mp4')])
    quick=json.loads(run(['ffprobe','-v','error','-show_streams','-of','json',str(OUT/'quick-peek.mp4')]).stdout)['streams'][0]
    assert quick['width']==quick['height']==320 and int(quick['nb_frames'])==count
    report=dict(status='PASS',glb_sha256=sha(OUT/'goblet.glb'),fps=fps,frames=count,videos=records,
                quick_peek_sha256=sha(OUT/'quick-peek.mp4'),movement_approved=False,human_approved=False)
    (OUT/'media.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
