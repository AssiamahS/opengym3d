"""Independent exported-node/browser parity, media identity and preservation."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'pipeline'))
from qa_glb import load_glb,Clip
OUT=ROOT/'outputs/equipment-use'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def validate_samples(records):
    phases=[r['phase'] for r in records]
    assert all(any(abs(p-required)<1e-8 for p in phases) for required in (0,.25,.5,.75,1,.123,.337))
    for record in records:
        assert np.isfinite(record['phase']) and 0<=record['phase']<=1
        available={n.replace('.','') for n in record['positions']}
        assert {'Dumbbell','wristL','wristR','footL','footR','finger2-1L','finger2-1R'}<=available
        for point in record['positions'].values():
            point=np.asarray(point,dtype=float)
            assert point.shape==(3,) and np.isfinite(point).all()

def main():
    (OUT/'integration.json').write_text(json.dumps(dict(status='BUILDING')))
    digest=sha(OUT/'goblet.glb')
    reports={name:json.loads((OUT/f'{name}.json').read_text()) for name in ('preview','media','quick-peek-check')}
    assert all(r['status']=='PASS' for r in reports.values())
    assert all(reports[n]['glb_sha256']==digest for n in ('preview','media'))
    for path in ('goblet.glb','dumbbell.glb'):
        r=json.loads((OUT/f'{path}.gltf.json').read_text())
        assert r['status']=='PASS' and r['issues']['numErrors']==0 and r['glb_sha256']==sha(OUT/path)
        assert not r['issues'].get('truncated',False)
    g,b=load_glb(OUT/'goblet.glb');clip=Clip(g,b)
    names={n.get('name','').replace('.',''):i for i,n in enumerate(g['nodes'])}
    maximum=0.;count=0
    validate_samples(reports['preview']['samples'])
    for record in reports['preview']['samples']:
        assert np.isfinite(record['phase']) and 0<=record['phase']<=1
        available={n.replace('.','') for n in record['positions']}
        assert {'Dumbbell','wristL','wristR','footL','footR','finger2-1L','finger2-1R'}<=available
        world=clip.world(record['phase']*clip.duration)
        for name,point in record['positions'].items():
            point=np.asarray(point,dtype=float)
            assert point.shape==(3,) and np.isfinite(point).all()
            if name.replace('.','') not in names:continue
            expected=np.asarray(world[names[name.replace('.','')]])[:3,3]
            maximum=max(maximum,float(np.max(abs(expected-point))));count+=1
    assert count>100 and maximum<1e-5,(count,maximum)
    protected=json.loads((OUT/'protected.json').read_text())
    assert all(sha(ROOT/p)==h for p,h in protected.items())
    for record in reports['media']['videos']:assert sha(OUT/(record['view']+'.mp4'))==record['sha256']
    assert sha(OUT/'quick-peek.mp4')==reports['media']['quick_peek_sha256']
    quick=reports['quick-peek-check']
    assert quick['file_sha256']=={p:sha(ROOT/p) for p in ('studio/equipment/preview.html','outputs/equipment-use/quick-front.mp4','outputs/equipment-use/quick-side.mp4')}
    result=dict(status='PASS',scope='Exported joint/equipment node browser parity, media and baseline preservation; contact and visual acceptance are separate',
                glb_sha256=digest,node_comparisons=count,max_component_error_m=maximum,protected_files_unchanged=len(protected),
                movement_approved=False,human_approved=False)
    (OUT/'integration.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':
    try:main()
    except Exception as exc:
        (OUT/'integration.json').write_text(json.dumps(dict(status='FAIL',error=str(exc)),indent=2));raise
