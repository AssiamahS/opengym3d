"""Independent catalog geometry/metadata/hash gate; no animation generation."""
import json
from pathlib import Path
import sys
import numpy as np
from equipment_catalog import ROOT, OUT, sha, validate_catalog
sys.path.insert(0,str(ROOT/'pipeline'))
from qa_glb import Clip
from heatsy_gltf import load, accessor


def contact_distance(kind, positions):
    """Nominal analytical surfaces of the unchanged procedural handles."""
    p=np.asarray(positions,float)
    if kind=='kettlebell':
        return abs(np.sqrt((np.linalg.norm(p[:,:2],axis=1)-.062)**2+p[:,2]**2)-.014)
    return abs(np.linalg.norm(p[:,1:],axis=1)-(.017 if kind=='dumbbell' else .014))


def main():
    report_path=OUT/'catalog-validation.json'
    report_path.write_text(json.dumps(dict(status='BUILDING')))
    try:
        catalog=json.loads((OUT/'catalog.json').read_text());validate_catalog(catalog)
        records=[]
        for item in catalog['items']:
            path=OUT/item['geometry'];g,b=load(path)
            assert not g.get('animations') and not g.get('skins'),'Standalone asset must have no animation or character'
            assert sha(path)==item['sha256']
            assert sha(OUT/item['thumbnail'])==item['thumbnailSha256']
            assert sha(ROOT/item['provenance']['sourcePath'])==item['provenance']['generatorSha256']
            assert (OUT/item['provenance']['licensePath']).read_bytes()==(ROOT/'LICENSE').read_bytes()
            validation=json.loads(Path(str(path)+'.gltf.json').read_text())
            assert validation['status']=='PASS' and validation['glb_sha256']==sha(path)
            assert validation['issues']['numErrors']==0 and not validation['issues'].get('truncated')
            world=Clip(g,b).world(0);points=[]
            for index,node in enumerate(g['nodes']):
                assert 'matrix' not in node,'Static matrix nodes require explicit decoder support'
                if 'mesh' not in node:continue
                for prim in g['meshes'][node['mesh']]['primitives']:
                    x=accessor(g,b,prim['attributes']['POSITION']);assert np.isfinite(x).all()
                    points.append((np.c_[x,np.ones(len(x))]@np.array(world[index]).T)[:,:3])
            points=np.concatenate(points);lo=points.min(axis=0);hi=points.max(axis=0)
            np.testing.assert_allclose(lo,item['bounds']['min'],atol=1e-6)
            np.testing.assert_allclose(hi,item['bounds']['max'],atol=1e-6)
            d=item['dimensions'];np.testing.assert_allclose(hi-lo,[d['length'],d['height'],d['width']],atol=1e-5)
            gaps=contact_distance(item['id'],[c['position'] for c in item['contactPoints']])
            assert max(gaps)<1e-6
            records.append(dict(id=item['id'],sha256=sha(path),bounds_error_m=float(np.max(abs(hi-lo-[d['length'],d['height'],d['width']]))),
                                nominal_contact_error_m=float(max(gaps)),bytes=path.stat().st_size,thumbnail_bytes=(OUT/item['thumbnail']).stat().st_size))
        report=dict(status='PASS',catalog_sha256=sha(OUT/'catalog.json'),items=records,
                    scope='Static geometry, dimensions, nominal analytic contact targets and provenance; no equipment technique approval')
        report_path.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    except Exception as exc:
        report_path.write_text(json.dumps(dict(status='FAIL',error=str(exc)),indent=2));raise


if __name__=='__main__':main()
