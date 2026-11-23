"""Snapshot both baselines and rerun existing explicit normal restoration in isolation."""
import json
import shutil
from heatsy_squat import ROOT, OUT, BASE, MOTION
from heatsy_validate import sha


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    protected = [MOTION, ROOT/'pipeline/synthetic_squat.py', ROOT/'work/heatsy/model/body_superficial.app5m.glb']
    for directory in (ROOT/'outputs/bodyweight',BASE,ROOT/'outputs/heatsy-squat'):
        protected.extend(p for p in directory.rglob('*') if p.is_file())
    hashes = {str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in protected}
    (OUT/'baseline-before.json').write_text(json.dumps(hashes,indent=2))
    assert json.loads((BASE/'milestone.json').read_text())['status']=='PASS'
    assert sha(BASE/'roundtrip.glb')==json.loads((BASE/'validation.json').read_text())['roundtrip_sha256']
    shutil.copy2(BASE/'blender-raw.glb',OUT/'blender-raw.glb')
    # Override only output locations in this process; no baseline writes.
    import heatsy_validate
    import heatsy_normals
    heatsy_validate.OUT = OUT
    heatsy_normals.OUT = OUT
    heatsy_normals.main()
    assert sha(OUT/'roundtrip.glb') == sha(BASE/'roundtrip.glb')
    for name in ('LICENSE','NOTICE.md','muscles.json','za_map.json','IMPORTER-NOTICE.md','selections.json'):
        shutil.copy2(BASE/name,OUT/name)
    shutil.copy2(ROOT/'LICENSE',OUT/'MOTION-CODE-MIT.txt')
    (OUT/'DERIVATION.md').write_text('''# Heatsy synthetic squat review — CC BY-SA 4.0

Heatsy / DDDEV LTD; Z-Anatomy; BodyParts3D. Full attribution and asset license
accompany this file as NOTICE.md and LICENSE. Derived animation and review images
retain CC BY-SA 4.0. Synthetic source motion and pipeline code are MIT.

Changes: rerun the verified normal-restoration stage on a separate copy of the
raw static export, then append target-specific animation channels from the
unchanged synthetic bodyweight squat. No geometry, anatomical attributes,
weights or bind matrices are rewritten. Metre geometry is not rescaled.
One constant standing-floor alignment is applied to the pelvis track.
Movement, anatomical quality and public readiness remain unapproved.
''')


if __name__=='__main__':
    main()
