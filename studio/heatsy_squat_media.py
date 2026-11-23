"""Encode and verify two diagnostic loops from the exported viewer's exact frames."""
import json
import re
import subprocess
from heatsy_squat import ROOT, OUT
from heatsy_validate import sha


def run(args):
    return subprocess.run(args,cwd=ROOT,capture_output=True,text=True,check=True)


def main():
    records=[]
    timing=json.loads((OUT/'retarget.json').read_text())
    fps=timing['fps']; count=timing['source_frames']-1; duration=timing['duration']
    for view in ('front','side'):
        frames=OUT/f'frames-{view}'/'%04d.png'
        video=OUT/f'{view}.mp4'
        run(['ffmpeg','-y','-v','error','-framerate',str(fps),'-i',str(frames),'-frames:v',str(count),
            '-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',
            '-metadata','title=Heatsy synthetic squat - deformation diagnostic',str(video)])
        probe=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)]).stdout)
        stream=probe['streams'][0]
        assert int(stream['nb_frames'])==count and abs(float(probe['format']['duration'])-duration)<1/fps
        assert stream['pix_fmt']=='yuv420p' and stream['width']==stream['height']==640
        psnr=run(['ffmpeg','-v','info','-i',str(video),'-framerate',str(fps),'-i',str(frames),
            '-lavfi','[0:v][1:v]psnr','-frames:v',str(count),'-f','null','-']).stderr
        match=re.search(r'average:([\d.]+|inf)',psnr)
        assert match and float(match.group(1))>35
        run(['ffmpeg','-y','-v','error','-i',str(video),'-vf',f'scale=160:160,tile=10x{(count+9)//10}',
            '-frames:v','1',str(OUT/f'{view}-decoded-all-frames.png')])
        records.append(dict(view=view,sha256=sha(video),frames=count,fps=fps,duration=duration,
            width=640,height=640,psnr_db=float(match.group(1)),decoded_contact_sheet=f'{view}-decoded-all-frames.png'))
    (OUT/'media.json').write_text(json.dumps(dict(status='PASS',glb_sha256=sha(OUT/'heatsy-squat.glb'),
        purpose='Diagnostic loops; upper-body deformation failed review',videos=records,poster_sha256=sha(OUT/'poster.png')),indent=2))
    print(json.dumps(records,indent=2))


if __name__=='__main__':main()
