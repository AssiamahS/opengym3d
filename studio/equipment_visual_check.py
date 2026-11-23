"""Matched-camera raster regression checks, never a visual-approval verdict.

The fixed grip preset frames the hands inside the stated image region. Comparing
the preserved checkpoint against the continuation catches unintended body,
equipment, camera or presentation changes outside that region.
"""
import json
import numpy as np
from PIL import Image
from equipment_paths import ROOT,OUT
from equipment_catalog import sha


def compare(before,after):
    assert before.shape==after.shape and before.ndim==3 and before.shape[2]==3
    h,w=before.shape[:2]
    changed=np.max(abs(before.astype(float)-after.astype(float)),axis=2)>8
    # Includes both hands, thumb webs and their anti-aliased outline, but not
    # the head, torso, upper dumbbell head or the majority of either arm.
    hand_region=np.zeros((h,w),bool)
    hand_region[int(h*.34):int(h*.64),int(w*.25):int(w*.58)]=True
    outside=int(np.sum(changed&~hand_region));total=int(changed.sum())
    assert total>20,'No visible grip change was rendered'
    assert outside/(h*w)<.001,'Unexpected raster change outside the grip region'
    assert total/(h*w)<.12,'Unbounded visual change'
    return dict(width=w,height=h,changed_pixels=total,outside_grip_pixels=outside,
                changed_fraction=total/(h*w),outside_grip_fraction=outside/(h*w))


def main():
    report_path=OUT/'visual-regression.json'
    report_path.write_text(json.dumps(dict(status='BUILDING')))
    try:
        records=[];hashes={}
        for suffix in ('','-320'):
            paths=[OUT/f'grip-{label}{suffix}.png' for label in ('before','after')]
            arrays=[np.array(Image.open(p).convert('RGB')) for p in paths]
            # The CSS wrapper includes its one-pixel border; video checks enforce
            # exact 320x320 media separately.
            if suffix:assert arrays[0].shape[1]==320 and 320<=arrays[0].shape[0]<=322
            records.append(compare(*arrays))
            hashes.update({p.relative_to(ROOT).as_posix():sha(p) for p in paths})
        result=dict(status='PASS',glb_sha256=sha(OUT/'goblet.glb'),file_sha256=hashes,views=records,
                    visual_approval='UNAPPROVED',scope='Matched-camera change localization at detail and 320px; anatomy, thumb contour and technique require human review')
        report_path.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
    except Exception as exc:
        report_path.write_text(json.dumps(dict(status='FAIL',error=str(exc)),indent=2));raise


if __name__=='__main__':main()
