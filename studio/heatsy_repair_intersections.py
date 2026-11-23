"""Blender BVH broad phase + explicit segment/triangle surface intersections.

No coplanar-contact, containment or clinical collision claim. Ignore shared
vertices and endpoint/edge touches; count proper interior crossings only.
"""
import json
from pathlib import Path
import sys
import numpy as np
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'studio'))
from heatsy_squat import sample
from heatsy_gltf import load,accessor
from heatsy_validate import sha
OUT=ROOT/'outputs/heatsy-repair'


def crosses(origin,end,a,b,c):
    direction=end-origin;e1=b-a;e2=c-a
    h=np.cross(direction,e2);det=np.einsum('ij,ij->i',e1,h)
    valid=abs(det)>1e-12
    inv=np.zeros_like(det);inv[valid]=1/det[valid]
    s=origin-a;u=inv*np.einsum('ij,ij->i',s,h)
    q=np.cross(s,e1);v=inv*np.einsum('ij,ij->i',direction,q)
    t=inv*np.einsum('ij,ij->i',e2,q)
    crossing=valid&(u>1e-6)&(v>1e-6)&(u+v<1-1e-6)&(t>1e-6)&(t<1-1e-6)
    normal=np.cross(e1,e2);norm=np.maximum(np.linalg.norm(normal,axis=1),1e-30)
    d0=np.einsum('ij,ij->i',s,normal)/norm
    d1=np.einsum('ij,ij->i',end-a,normal)/norm
    # Additional robust metric: segment endpoints extend >0.1 mm to each side
    # of the triangle plane. Keep the raw metric, do not replace it silently.
    return crossing,crossing&(np.minimum(abs(d0),abs(d1))>.0001)


def inspect(y,tri,ids):
    tree=BVHTree.FromPolygons(y.tolist(),tri.tolist(),all_triangles=True)
    pairs=np.array(tree.overlap(tree),dtype=int)
    pairs=pairs[pairs[:,0]<pairs[:,1]]
    ta,tb=tri[pairs[:,0]],tri[pairs[:,1]]
    adjacent=np.any(ta[:,:,None]==tb[:,None,:],axis=(1,2))
    pairs=pairs[~adjacent];a=y[tri[pairs[:,0]]];b=y[tri[pairs[:,1]]]
    hit=np.zeros(len(pairs),bool);significant=hit.copy()
    for j in range(3):
        h,s=crosses(a[:,j],a[:,(j+1)%3],b[:,0],b[:,1],b[:,2]);hit|=h;significant|=s
        h,s=crosses(b[:,j],b[:,(j+1)%3],a[:,0],a[:,1],a[:,2]);hit|=h;significant|=s
    pairs=pairs[hit]
    codes=ids[tri[pairs,0]]
    return dict(proper_crossing_triangle_pairs=len(pairs),
        crossings_with_0_1mm_plane_margin=int(significant.sum()),
        same_part_pairs=int(np.sum(codes[:,0]==codes[:,1])),
        cross_part_pairs=int(np.sum(codes[:,0]!=codes[:,1])),
        most_frequent_part_pairs=[dict(part_ids=c.tolist(),pairs=int(n)) for c,n in sorted(zip(*np.unique(np.sort(codes,axis=1),axis=0,return_counts=True)),key=lambda x:-x[1])[:12]])


def main():
    report={}
    paths={'before':ROOT/'outputs/heatsy-bodyweight/heatsy-squat.glb'}
    for label,filename in [('spatial20','candidate-spatial-20.glb'),('spatial30','candidate-spatial-30.glb')]:
        if (OUT/filename).exists():paths[label]=OUT/filename
    if (OUT/'heatsy-squat.glb').exists():paths['accepted']=OUT/'heatsy-squat.glb'
    for name,path in paths.items():
        g,b=load(path);p=g['meshes'][0]['primitives'][0];tri=accessor(g,b,p['indices']).astype(int).reshape(-1,3)
        ids=accessor(g,b,p['attributes']['_PART_ID']).ravel().astype(int)
        report[name]=dict(glb_sha256=sha(path),poses={})
        for pose,t in [('neutral',None),('standing',0),('descent',.75),('bottom',1.5)]:
            if t is None:
                static=dict(g);static.pop('animations');y,_=sample(static,b,0)
            else:y,_=sample(g,b,t)
            report[name]['poses'][pose]=inspect(y,tri,ids)
            print(name,pose,report[name]['poses'][pose]['proper_crossing_triangle_pairs'],flush=True)
    (OUT/'surface-intersections.json').write_text(json.dumps(dict(method=__doc__,results=report),indent=2))


if __name__=='__main__':main()
