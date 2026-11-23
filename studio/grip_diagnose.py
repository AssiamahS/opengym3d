"""Exported-MPFB hand deformation diagnostics; read-only towards every baseline."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'pipeline'))
from qa_glb import Clip
from heatsy_gltf import load,accessor
from goblet_build import sha
from equipment_paths import output_path
from goblet_validate import cylinder_distance


def inspect(path):
    g,b=load(path);clip=Clip(g,b);world=clip.world(0)
    node=next(n for n in g['nodes'] if 'skin' in n)
    p=g['meshes'][node['mesh']]['primitives'][0];a=p['attributes']
    x=accessor(g,b,a['POSITION']);j=accessor(g,b,a['JOINTS_0']).astype(int);w=accessor(g,b,a['WEIGHTS_0'])
    skin=g['skins'][node['skin']];names=[g['nodes'][i]['name'] for i in skin['joints']]
    ibm=accessor(g,b,skin['inverseBindMatrices']).reshape(-1,4,4).transpose(0,2,1)
    ops=np.array([world[k] for k in skin['joints']])@ibm
    posed=sum(w[:,k,None]*np.einsum('nij,nj->ni',ops[j[:,k]],np.c_[x,np.ones(len(x))])[:,:3] for k in range(4))
    tri=accessor(g,b,p['indices']).reshape(-1,3).astype(int)
    edges=np.unique(np.sort(np.vstack([tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]]),axis=1),axis=0)
    rest=np.linalg.norm(x[edges[:,1]]-x[edges[:,0]],axis=1)
    actual=np.linalg.norm(posed[edges[:,1]]-posed[edges[:,0]],axis=1)
    ratio=actual/np.maximum(rest,1e-12)
    area0=np.linalg.norm(np.cross(x[tri[:,1]]-x[tri[:,0]],x[tri[:,2]]-x[tri[:,0]]),axis=1)/2
    area1=np.linalg.norm(np.cross(posed[tri[:,1]]-posed[tri[:,0]],posed[tri[:,2]]-posed[tri[:,0]]),axis=1)/2
    regions={}
    for region,prefixes in [('all_hands',('wrist','metacarpal','finger')),('thumbs',('finger1',)),('fingers',('finger2','finger3','finger4','finger5'))]:
        mask=np.sum(w*np.array([n.startswith(prefixes) for n in names])[j],axis=1)>.5
        eligible=np.all(mask[edges],axis=1)&(rest>=.0005)
        indices=np.flatnonzero(eligible);values=ratio[indices]
        surface=np.all(mask[tri],axis=1)&(area0>1e-12)
        worst=indices[np.argsort(abs(actual[indices]-rest[indices]))[-5:][::-1]]
        regions[region]=dict(vertices=int(mask.sum()),edges=len(indices),
            minimum=float(values.min()),p01=float(np.quantile(values,.01)),p50=float(np.median(values)),p95=float(np.quantile(values,.95)),
            p99=float(np.quantile(values,.99)),maximum=float(values.max()),below_half=int(np.sum(values<.5)),over2=int(np.sum(values>2)),
            max_absolute_change_mm=float(np.max(abs(actual[indices]-rest[indices]))*1000),
            triangles_below_tenth_area=int(np.sum(surface&(area1<.1*area0))),
            worst_absolute=[dict(vertices=edges[i].tolist(),rest_mm=float(rest[i]*1000),posed_mm=float(actual[i]*1000),ratio=float(ratio[i])) for i in worst])
    bones={}
    for name in names:
        if name.startswith(('wrist','metacarpal','finger')):
            bones[name]=np.array(world[clip.by_name[name]]).tolist()
    equipment=np.array(world[clip.by_name['Dumbbell']]);local=(np.c_[posed,np.ones(len(posed))]@np.linalg.inv(equipment).T)[:,:3]
    sdf=np.minimum.reduce([cylinder_distance(local,0,.075,.017),cylinder_distance(local,-.098,.0275,.055),cylinder_distance(local,.098,.0275,.055)])
    worst=np.argsort(sdf)[:10]
    penetration=[dict(vertex=int(i),depth_mm=float(-sdf[i]*1000),equipment_local=local[i].tolist(),influences={names[k]:float(v) for k,v in zip(j[i],w[i]) if v>.001}) for i in worst]
    influence_hash=hashlib.sha256(w.tobytes()+j.tobytes()+json.dumps(names).encode()).hexdigest()
    return dict(glb_sha256=sha(path),regions=regions,bones=bones,worst_penetration=penetration,skin_influences_sha256=influence_hash,
        method='Standing exported mesh; edges >=0.5mm rest length. Triangle areas exclude rest areas <=1e-12m2. Region membership requires >0.5 summed influence; not physiological strain.'),x,tri


def main():
    candidate=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'outputs/equipment-library/grip-experiments/transport/goblet.glb'
    out=output_path(candidate.resolve().parent)
    before,x0,t0=inspect(ROOT/'outputs/equipment-use/goblet.glb')
    after,x1,t1=inspect(candidate)
    np.testing.assert_array_equal(x0,x1);np.testing.assert_array_equal(t0,t1)
    if before['skin_influences_sha256']!=after['skin_influences_sha256']:
        raise AssertionError('Skin influences changed')
    thumb_world_delta=max(float(np.max(abs(np.array(before['bones'][name])-np.array(after['bones'][name])))) for name in before['bones'] if name.startswith('finger1'))
    record=dict(baseline=before,candidate=after,geometry_unchanged=True,skin_influences_unchanged=True,maximum_thumb_world_matrix_change=thumb_world_delta)
    (out/'grip-deformation.json').write_text(json.dumps(record,indent=2))
    print(json.dumps({name:v['regions'] for name,v in [('before',before),('after',after)]},indent=2))


if __name__=='__main__':main()
