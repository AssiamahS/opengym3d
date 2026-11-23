"""Independent exported-node/browser parity, media identity and preservation."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'pipeline'))
from qa_glb import load_glb,Clip
from equipment_paths import OUT

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
    checkpoint=json.loads((OUT/'checkpoint-files.json').read_text())
    assert checkpoint and all(sha(ROOT/p)==h for p,h in checkpoint.items())
    catalog=json.loads((OUT/'catalog-validation.json').read_text())
    assert catalog['status']=='PASS' and catalog['catalog_sha256']==sha(OUT/'catalog.json')
    for item in catalog['items']:
        assert item['sha256']==sha(OUT/(item['id']+'.glb'))
    browser=json.loads((OUT/'catalog-check.json').read_text())
    validate_catalog_browser(browser)
    visual=json.loads((OUT/'visual-regression.json').read_text())
    assert visual['status']=='PASS' and visual['glb_sha256']==digest
    expected_images=tuple((OUT/f'grip-{label}{suffix}.png').relative_to(ROOT).as_posix()
                          for suffix in ('','-320') for label in ('before','after'))
    assert visual['file_sha256']=={p:sha(ROOT/p) for p in expected_images}
    for record in reports['media']['videos']:assert sha(OUT/(record['view']+'.mp4'))==record['sha256']
    assert sha(OUT/'quick-peek.mp4')==reports['media']['quick_peek_sha256']
    quick=reports['quick-peek-check']
    assert quick['file_sha256']=={p:sha(ROOT/p) for p in ('studio/equipment/preview.html',(OUT/'quick-front.mp4').relative_to(ROOT).as_posix(),(OUT/'quick-side.mp4').relative_to(ROOT).as_posix())}
    result=dict(status='PASS',scope='Exported joint/equipment node browser parity, media and baseline preservation; contact and visual acceptance are separate',
                glb_sha256=digest,node_comparisons=count,max_component_error_m=maximum,protected_files_unchanged=len(protected),
                checkpoint_files_unchanged=len(checkpoint),catalog='PASS',
                movement_approved=False,human_approved=False)
    (OUT/'integration.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))


def validate_catalog_browser(report):
    assert report['status']=='PASS'
    assert report['catalog_sha256']==sha(OUT/'catalog.json') and report['glb_sha256']==sha(OUT/'goblet.glb')
    expected_assets=('catalog.json','dumbbell.glb','kettlebell.glb','barbell.glb','goblet.glb')
    assert report['asset_sha256']=={name:sha(OUT/name) for name in expected_assets}
    expected_files=tuple('studio/equipment/'+name for name in ('index.html','style.css','viewer.js','preview.html'))+('studio/equipment_capture.mjs','studio/equipment_catalog_check.mjs')
    assert report['file_sha256']=={name:sha(ROOT/name) for name in expected_files}

if __name__=='__main__':
    try:main()
    except Exception as exc:
        (OUT/'integration.json').write_text(json.dumps(dict(status='FAIL',error=str(exc)),indent=2));raise
