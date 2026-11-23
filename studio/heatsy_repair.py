"""Isolated, deterministic Heatsy deformation experiments. Never writes baselines."""
import copy
import json
from pathlib import Path
import sys
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import splu
from scipy.spatial import cKDTree

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'studio'))
from heatsy_squat import BASE, sample, qa_glb, from_matrix, aim, multiply, inverse
from heatsy_gltf import load, accessor, save
from heatsy_validate import asset, matrices, sha

OUT=ROOT/'outputs/heatsy-repair'
BROKEN=ROOT/'outputs/heatsy-bodyweight/heatsy-squat.glb'


def dump(name,value):
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/name).write_text(json.dumps(value,indent=2),encoding='utf-8')


class Rig:
    def __init__(self):
        a=asset(BASE/'roundtrip.glb')
        self.a=a;self.g=a['g'];self.b=a['b'];self.x=a['attrs']['POSITION']
        self.rest=a['positions'];self.w=a['weights'];self.names=a['names']
        self.node={n['name']:i for i,n in enumerate(self.g['nodes'])}
        self.joints=self.g['skins'][0]['joints'];self.parent=a['parents'];self.local=a['local']
        self.tri=a['triangles'];self.ids=a['attrs']['_PART_ID'].ravel().astype(int)
        self.edges=np.unique(np.sort(np.vstack([self.tri[:,[0,1]],self.tri[:,[1,2]],self.tri[:,[2,0]]]),axis=1),axis=0)
        self.length=np.linalg.norm(self.rest[self.edges[:,1]]-self.rest[self.edges[:,0]],axis=1)
        self.source_length=np.linalg.norm(self.x[self.edges[:,1]]-self.x[self.edges[:,0]],axis=1)
        v=json.loads((BASE/'muscles.json').read_text());mg={m['id']:m['group'] for m in v['muscles']}
        self.part={1+2*i+s:p['id'] for i,p in enumerate(v['parts']) for s in (0,1)}
        cg={1+2*i+s:mg[p['muscle']] for i,p in enumerate(v['parts']) for s in (0,1)}
        self.groups=np.array([cg.get(int(i),'unlabelled') for i in self.ids])
        self.regions={'all':np.ones(len(self.edges),bool)}
        for region,groups in {'hips':['glutes','hip_flexors','adductors'],
            'knees':['quads','hamstrings','calves'],'torso':['upper_back','lower_back','abs','chest','shoulders','neck'],
            'arms':['arms_front','arms_back','forearms']}.items():
            self.regions[region]=np.all(np.isin(self.groups[self.edges],groups),axis=1)
        self.bg,self.bb=load(BROKEN);self.clip=qa_glb.Clip(self.bg,self.bb)
        rt=self.rest[self.tri];self.area=np.linalg.norm(np.cross(rt[:,1]-rt[:,0],rt[:,2]-rt[:,0]),axis=1)/2

    def world(self,local):
        result={}
        def go(i):
            if i not in result:result[i]=(go(self.parent[i]) if i in self.parent else np.eye(4))@local[i]
            return result[i]
        return np.array([go(i) for i in range(len(local))])

    def pose(self,time=None,only=None):
        if time is None:return self.world(self.local)
        if only is None:
            world=self.clip.world(time)
            return np.array([world[i] for i in range(len(self.local))])
        local=self.local.copy()
        for n in only:local[self.node[n]]=qa_glb.trs(*self.clip.local(self.node[n],time))
        return self.world(local)

    def deform(self,world,weights=None):
        w=self.w if weights is None else weights
        ops=world[self.joints]@self.a['ibm']
        # Dense weights permit controlled experiments; export remains four influences.
        y=np.zeros_like(self.x)
        for j in range(len(self.names)):
            ii=np.flatnonzero(w[:,j]>0)
            y[ii]+=w[ii,j,None]*(self.x[ii]@ops[j,:3,:3].T+ops[j,:3,3])
        return y

    def metrics(self,y):
        actual=np.linalg.norm(y[self.edges[:,1]]-y[self.edges[:,0]],axis=1)
        ratio=actual/np.maximum(self.length,1e-12)
        report={}
        def describe(i):
            return dict(vertices=self.edges[i].tolist(),part_ids=self.ids[self.edges[i]].tolist(),
                parts=[self.part.get(int(k),'unlabelled') for k in self.ids[self.edges[i]]],
                rest_mm=float(self.length[i]*1000),posed_mm=float(actual[i]*1000),
                change_mm=float((actual[i]-self.length[i])*1000),ratio=float(ratio[i]))
        for region,mask in self.regions.items():
            ii=np.flatnonzero(mask&(self.length>=.001));r=ratio[ii]
            top=ii[np.argsort(r)[-5:][::-1]]
            report[region]=dict(edges=len(ii),p50=float(np.median(r)),p95=float(np.quantile(r,.95)),
                p99=float(np.quantile(r,.99)),maximum=float(r.max()),over2=int(np.sum(r>2)),
                below_half=int(np.sum(r<.5)),max_absolute_change_mm=float(np.max(abs(actual[ii]-self.length[ii]))*1000),
                worst=[describe(i) for i in top],
                worst_absolute_change=[describe(i) for i in ii[np.argsort(abs(actual[ii]-self.length[ii]))[-5:][::-1]]])
        report['edge_length_bands']={name:dict(count=int(mask.sum()),maximum=float(ratio[mask].max()) if mask.any() else None)
            for name,mask in [('below_0.1mm',self.length<.0001),('0.1_to_1mm',(self.length>=.0001)&(self.length<.001)),('at_least_1mm',self.length>=.001)]}
        degenerate=self.source_length<1e-12
        report['source_degenerate_edges']=dict(count=int(degenerate.sum()),
            max_posed_separation_mm=float(actual[degenerate].max()*1000) if degenerate.any() else 0,
            ratio=None,reason='Zero-length source edges have no meaningful stretch ratio')
        nearzero=(self.source_length>=1e-12)&(self.source_length<.0001)
        report['source_nonzero_below_0_1mm']=dict(count=int(nearzero.sum()),
            max_absolute_change_mm=float(np.max(abs(actual[nearzero]-self.length[nearzero]))*1000) if nearzero.any() else 0)
        tri=y[self.tri];area=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)/2
        report['surface']=dict(newly_tiny=int(np.sum((self.area>1e-10)&(area<1e-12))),
            below_tenth_rest_area=int(np.sum((self.area>1e-10)&(area<self.area*.1))))
        return report

    def heat(self,y):
        lengths=np.linalg.norm(y[self.edges[:,1]]-y[self.edges[:,0]],axis=1)
        strain=np.abs(np.log(np.maximum(lengths,1e-12)/np.maximum(self.length,1e-12)))
        strain[self.length<.001]=0
        values=np.zeros(len(self.x))
        np.maximum.at(values,self.edges[:,0],strain);np.maximum.at(values,self.edges[:,1],strain)
        return values

    def controlled(self):
        both=lambda name:[name+'.L',name+'.R']
        return {'neutral':self.pose(), 'standing':self.pose(0),
            'hip_flexion':self.pose(1.5,both('thigh')),
            'knee_flexion':self.pose(1.5,both('shin')),
            'shoulder_only':self.pose(0,both('upperarm')),
            'shoulder_girdle':self.pose(0,both('upperarm')+both('clavicle')+both('scapula')),
            'torso_only':self.pose(1.5,['spine_01','spine_02','spine_03','neck','head']),
            'descent':self.pose(.75),'bottom':self.pose(1.5)}


def diagnose():
    r=Rig();report={};ops=r.pose()[r.joints]@r.a['ibm']
    audit=dict(rest_skin_operator_identity_error=float(np.max(abs(ops-np.eye(4)))),
        weight_sum_error=float(np.max(abs(r.w.sum(1)-1))),
        inverse_bind_determinant_range=[float(np.linalg.det(r.a['ibm'][:,:3,:3]).min()),float(np.linalg.det(r.a['ibm'][:,:3,:3]).max())],
        original_source_sha256=sha(ROOT/'work/heatsy/model/body_superficial.app5m.glb'))
    axes={}
    for name,world in r.controlled().items():
        y=r.deform(world);report[name]=r.metrics(y)
        rotations=world[r.joints,:3,:3]
        report[name]['rigidity']=dict(determinant_min=float(np.linalg.det(rotations).min()),
            determinant_max=float(np.linalg.det(rotations).max()),
            max_scale_error=float(np.max(abs(np.linalg.svd(rotations,compute_uv=False)-1))))
        axes[name]={n:dict(position=world[i,:3,3].tolist(),axes=world[i,:3,:3].tolist(),
            rest_position=r.a['world'][i][:3,3].tolist(),rest_axes=r.a['world'][i][:3,:3].tolist(),
            local_delta=from_matrix(np.linalg.inv(r.local[i])@(np.linalg.inv(world[r.parent[i]])@world[i] if i in r.parent else world[i])).tolist())
            for n,i in r.node.items() if n in ['pelvis','spine_01','spine_02','spine_03','clavicle.L','scapula.L','upperarm.L','forearm.L','thigh.L','shin.L']}
    # Exact edge-vector decomposition: smooth rigid action vs differing weights.
    decomposition=[];world=r.pose(1.5);ops=world[r.joints]@r.a['ibm']
    for region in ('torso','hips','knees'):
        a,b=report['bottom'][region]['worst'][0]['vertices']
        dx=r.x[b]-r.x[a];mid=(r.x[a]+r.x[b])/2
        mean=(r.w[a]+r.w[b])/2;dw=r.w[b]-r.w[a]
        rigid=np.einsum('j,jik,k->i',mean,ops[:,:3,:3],dx)
        gradient=np.einsum('j,ji->i',dw,np.einsum('jik,k->ji',ops[:,:3,:3],mid)+ops[:,:3,3])
        decomposition.append(dict(region=region,vertices=[int(a),int(b)],
            geometric_component_mm=float(np.linalg.norm(rigid)*1000),weight_gradient_component_mm=float(np.linalg.norm(gradient)*1000),
            total_mm=float(np.linalg.norm(rigid+gradient)*1000),
            endpoints=[{n:float(w) for n,w in zip(r.names,r.w[i]) if w>0} for i in (a,b)]))
    dump('controlled-baseline.json',report);dump('joint-axes.json',axes);dump('rig-audit.json',audit);dump('edge-decomposition.json',decomposition)
    print(json.dumps({'audit':audit,'edge_decomposition':decomposition,'poses':{n:{k:round(v[k]['maximum'],3) for k in ('all','torso','hips','knees')} for n,v in report.items()}},indent=2))


def rotation_variation(r,time,arm_roll=0.,girdle=None,spine=False):
    world=r.pose(time);local=np.array([qa_glb.trs(*r.clip.local(i,time)) for i in range(len(r.local))])
    desired={}
    if arm_roll:
        for side,sign in [('L',1),('R',-1)]:
            for name,child in [('upperarm','forearm'),('forearm','hand')]:
                i,j=r.node[name+'.'+side],r.node[child+'.'+side]
                axis=world[j,:3,3]-world[i,:3,3];axis/=np.linalg.norm(axis)
                angle=np.radians(arm_roll*sign)/2
                q=np.r_[axis*np.sin(angle),np.cos(angle)]
                desired[i]=np.array(qa_glb.trs([0,0,0],q,[1,1,1]))[:3,:3]@world[i,:3,:3]
    if girdle is not None:
        for side in ('L','R'):
            for name in ('clavicle','scapula'):
                i=r.node[name+'.'+side];rest=r.a['world'][i][:3,:3]
                delta=from_matrix(world[i,:3,:3]@rest.T)
                q=qa_glb.q_slerp([0,0,0,1],delta,girdle)
                desired[i]=np.array(qa_glb.trs([0,0,0],q,[1,1,1]))[:3,:3]@rest
            # Keep source limb world orientations (rather than hiding elevation).
            for name in ('upperarm','forearm','hand'):desired[r.node[name+'.'+side]]=world[r.node[name+'.'+side],:3,:3]
    if spine:
        i=r.node['spine_03'];delta=from_matrix(world[i,:3,:3]@r.a['world'][i][:3,:3].T)
        for name,share in [('spine_01',1/3),('spine_02',2/3),('spine_03',1)]:
            j=r.node[name];q=qa_glb.q_slerp([0,0,0,1],delta,share)
            desired[j]=np.array(qa_glb.trs([0,0,0],q,[1,1,1]))[:3,:3]@r.a['world'][j][:3,:3]
        for side in ('L','R'):
            for name in ('clavicle','scapula','upperarm','forearm','hand'):desired[r.node[name+'.'+side]]=world[r.node[name+'.'+side],:3,:3]
    done={}
    def resolve(i):
        parent=resolve(r.parent[i]) if i in r.parent else np.eye(4)
        if i not in done:
            if i in desired:local[i,:3,:3]=parent[:3,:3].T@desired[i]
            done[i]=parent@local[i]
        return done[i]
    return np.array([resolve(i) for i in range(len(local))])


def transform_experiments(after=False):
    r=Rig();report={}
    weights=np.load(OUT/'accepted-weights.npy') if after else None
    variants={'baseline':{},'girdle_off':{'girdle':0},'girdle_double':{'girdle':2},'distributed_spine':{'spine':True}}
    variants.update({f'arm_roll_{angle}':{'arm_roll':angle} for angle in (-90,-45,45,90)})
    for name,kwargs in variants.items():
        report[name]={str(t):r.metrics(r.deform(rotation_variation(r,t,**kwargs),weights)) for t in (0,.75,1.5)}
    dump('transform-experiments-after.json' if after else 'transform-experiments.json',report)
    print(json.dumps({n:{region:round(v['1.5'][region]['maximum'],3) for region in ('torso','hips','knees')} for n,v in report.items()},indent=2))


def smooth_weights(r,radius_mm,anchors=True,palette=False):
    """Screened rest-surface diffusion, blocked at anatomical IDs; four influences.

    Distance weights are positive; the M-matrix solve is a convex averaging
    operation. Original pure-bone vertices are hard anchors. No posed geometry
    or source-motion frames participate in the correction.
    """
    edges=r.edges[(r.ids[r.edges[:,0]]==r.ids[r.edges[:,1]])&(r.ids[r.edges[:,0]]>0)]
    distance=np.linalg.norm(r.rest[edges[:,1]]-r.rest[edges[:,0]],axis=1)
    conductance=1/np.maximum(distance,.0005)**2
    a,b=edges.T
    adjacency=sparse.coo_matrix((np.r_[conductance,conductance],(np.r_[a,b],np.r_[b,a])),shape=(len(r.x),len(r.x))).tocsr()
    degree=np.array(adjacency.sum(1)).ravel()
    # Average neighbor squared-gradient energy (physical radius in metres).
    count=np.maximum(np.diff(adjacency.indptr),1)
    conductance/=np.maximum(count[a],count[b])
    adjacency=sparse.coo_matrix((np.r_[conductance,conductance],(np.r_[a,b],np.r_[b,a])),shape=(len(r.x),len(r.x))).tocsr()
    lap=sparse.diags(np.array(adjacency.sum(1)).ravel())-adjacency
    matrix=(sparse.eye(len(r.x))+(radius_mm/1000)**2*lap).tocsr()
    fixed=(r.ids==0)|(r.w.max(1)>.999 if anchors else False)
    free=np.flatnonzero(~fixed);fi=np.flatnonzero(fixed)
    rhs=r.w[free]-matrix[free][:,fi]@r.w[fi]
    solver=splu(matrix[free][:,free].tocsc())
    result=r.w.copy()
    # Individual RHS avoids pathological BLAS multi-thread overhead on this host.
    for j in range(len(r.names)):result[free,j]=solver.solve(rhs[:,j])
    result=np.maximum(result,0)
    if palette:
        # A fixed palette per anatomical part avoids top-four rank-switch seams.
        # This is an explicit experimental alternative, not a silent pruning.
        for code in np.unique(r.ids):
            if code==0:continue
            ii=np.flatnonzero(r.ids==code)
            keep=np.argsort(-r.w[ii].sum(0),kind='stable')[:4]
            excluded=np.ones(len(r.names),bool);excluded[keep]=False
            result[np.ix_(ii,np.flatnonzero(excluded))]=0
    top=np.argsort(-result,axis=1,kind='stable')[:,:4]
    compact=np.take_along_axis(result,top,axis=1)
    compact/=compact.sum(1)[:,None]
    output=np.zeros_like(result);np.put_along_axis(output,top,compact,axis=1)
    return output


def weight_experiments():
    r=Rig();report={};world=r.pose(1.5)
    for radius in (5,10,20,40):
        weights=smooth_weights(r,radius)
        report[str(radius)]=r.metrics(r.deform(world,weights))
        report[str(radius)]['changed_vertices']=int(np.sum(np.max(abs(weights-r.w),axis=1)>1e-7))
        np.save(OUT/f'weights-{radius}mm.npy',weights)
        print(radius,{k:round(report[str(radius)][k]['maximum'],3) for k in ('torso','hips','knees')},flush=True)
    dump('weight-experiments.json',report)


def spatial_weights(r,sigma_mm,include_unlabelled=False):
    """Rest-space Gaussian averaging, per part, area weighted against density bias.

    Does not use any posed sample. Nearby opposite sides of a thin muscle share
    the same field. Unlabelled disconnected surfaces are separate components.
    """
    sigma=sigma_mm/1000
    mass=np.zeros(len(r.x))
    for k in range(3):np.add.at(mass,r.tri[:,k],r.area/3)
    mass=np.maximum(mass,1e-12)
    result=r.w.copy()
    # No averaging across labels or across disconnected unlabelled bone pieces.
    groups=[]
    for code in np.unique(r.ids):
        ii=np.flatnonzero(r.ids==code)
        if code==0:
            if not include_unlabelled:continue
            edges=r.edges[np.all(r.ids[r.edges]==0,axis=1)]
            graph=sparse.coo_matrix((np.ones(len(edges)),(edges[:,0],edges[:,1])),shape=(len(r.x),len(r.x))).tocsr()[ii][:,ii]
            count,labels=sparse.csgraph.connected_components(graph,directed=False)
            groups.extend(ii[labels==j] for j in range(count))
        else:groups.append(ii)
    for ii in groups:
        tree=cKDTree(r.rest[ii]);dist=tree.sparse_distance_matrix(tree,3*sigma,output_type='coo_matrix')
        kernel=sparse.coo_matrix((np.exp(-.5*(dist.data/sigma)**2)*mass[ii[dist.col]],(dist.row,dist.col)),shape=dist.shape).tocsr()
        result[ii]=(kernel@r.w[ii])/np.asarray(kernel.sum(1))
    top=np.argsort(-result,axis=1,kind='stable')[:,:4]
    compact=np.take_along_axis(result,top,axis=1);compact/=compact.sum(1)[:,None]
    output=np.zeros_like(result);np.put_along_axis(output,top,compact,axis=1)
    return output


def spatial_experiments():
    r=Rig();world=r.pose(1.5);report={}
    for radius in (5,10,20,30):
        weights=spatial_weights(r,radius,include_unlabelled=True)
        np.save(OUT/f'weights-spatial-{radius}mm.npy',weights)
        report[str(radius)]=r.metrics(r.deform(world,weights))
        print(radius,{k:[round(report[str(radius)][k]['maximum'],3),round(report[str(radius)][k]['p99'],3),report[str(radius)][k]['over2']] for k in ('all','torso','hips','knees')},report[str(radius)]['surface'],flush=True)
    dump('spatial-experiments.json',report)


def export_weights(weights,path,recipe):
    """Append new skin accessors; retain geometry/anatomy/binds/animation bytes."""
    g,b=load(BROKEN);g=copy.deepcopy(g);blob=bytearray(b)
    top=np.argsort(-weights,axis=1,kind='stable')[:,:4]
    values=np.take_along_axis(weights,top,axis=1).astype('<f4')
    values/=values.sum(1)[:,None]
    top[values==0]=0  # Unused influences have no semantic effect; avoid glTF warnings.
    def add(array,component):
        blob.extend(b'\0'*(-len(blob)%4));view=len(g['bufferViews'])
        g['bufferViews'].append(dict(buffer=0,byteOffset=len(blob),byteLength=array.nbytes))
        blob.extend(array.tobytes());idx=len(g['accessors'])
        g['accessors'].append(dict(bufferView=view,componentType=component,count=len(array),type='VEC4'))
        return idx
    attrs=g['meshes'][0]['primitives'][0]['attributes']
    attrs['JOINTS_0']=add(top.astype('uint8'),5121);attrs['WEIGHTS_0']=add(values,5126)
    g['asset'].setdefault('extras',{})['forged_motion_derivative']=dict(recipe=recipe,
        source_animation_sha256=sha(BROKEN),license='CC-BY-SA-4.0',anatomy_approved=False)
    save(path,g,blob)


def candidates():
    import shutil
    r=Rig()
    for name in ('LICENSE','NOTICE.md','IMPORTER-NOTICE.md','selections.json','muscles.json','za_map.json','MOTION-CODE-MIT.txt'):
        source=ROOT/'outputs/heatsy-bodyweight'/name
        shutil.copy2(source,OUT/name)
    for radius in (10,20,30):
        weights=np.load(OUT/f'weights-spatial-{radius}mm.npy')
        export_weights(weights,OUT/f'candidate-spatial-{radius}.glb',dict(method='same-part area-weighted rest-space Gaussian',sigma_mm=radius,unlabelled='separate connected components'))
    poses={};heat={}
    for name,world in r.controlled().items():
        poses[name]=[(np.linalg.inv(world[r.parent[i]])@world[i] if i in r.parent else world[i]).T.ravel().tolist() for i in r.joints]
        heat[name]=dict(before=r.heat(r.deform(world)).tolist(),after=r.heat(r.deform(world,np.load(OUT/'weights-spatial-20mm.npy'))).tolist())
    dump('diagnostic-poses.json',dict(names=r.names,poses=poses));dump('strain-heat.json',heat)


def compact_weights(values,continuous=False):
    """Four influences, with optional continuous fade at fourth/fifth rank swaps."""
    result=values.copy()
    if continuous and result.shape[1]>4:
        threshold=np.partition(result,-5,axis=1)[:,-5]
        result=np.maximum(result-threshold[:,None],0)
        if np.any(result.sum(1)<1e-12):raise ValueError('Ambiguous equal-weight support requires explicit review')
    top=np.argsort(-result,axis=1,kind='stable')[:,:4]
    compact=np.take_along_axis(result,top,axis=1);compact/=compact.sum(1)[:,None]
    output=np.zeros_like(result);np.put_along_axis(output,top,compact,axis=1)
    return output


def coherent_weights(r,sigma_mm,support_guard=False,continuous=False):
    """A continuous area-weighted rest-space skin field across nearby surfaces.

    Anatomy IDs are never changed. Opposite-side limb influences are excluded;
    the source foot region retains original weights with a smooth ankle blend.
    """
    sigma=sigma_mm/1000;mass=np.zeros(len(r.x))
    for k in range(3):np.add.at(mass,r.tri[:,k],r.area/3)
    mass=np.maximum(mass,1e-12);tree=cKDTree(r.rest)
    result=np.zeros_like(r.w);sparse_weights=sparse.csr_matrix(r.w)
    # Bound memory while including every neighbor within three sigma.
    for start in range(0,len(r.x),2000):
        end=min(start+2000,len(r.x));query=cKDTree(r.rest[start:end])
        dist=query.sparse_distance_matrix(tree,3*sigma,output_type='coo_matrix')
        kernel=sparse.coo_matrix((np.exp(-.5*(dist.data/sigma)**2)*mass[dist.col],(dist.row,dist.col)),shape=dist.shape).tocsr()
        result[start:end]=(kernel@sparse_weights).toarray()/np.asarray(kernel.sum(1))
    if support_guard:
        # Nearby arms and thighs in the rest pose are not a shared skin domain.
        # A part/component can retain only bones already present in that domain.
        domains=[]
        for code in np.unique(r.ids):
            ii=np.flatnonzero(r.ids==code)
            if code:
                domains.append(ii)
            else:
                e=r.edges[np.all(r.ids[r.edges]==0,axis=1)]
                graph=sparse.coo_matrix((np.ones(len(e)),(e[:,0],e[:,1])),shape=(len(r.x),len(r.x))).tocsr()[ii][:,ii]
                count,labels=sparse.csgraph.connected_components(graph,directed=False)
                domains.extend(ii[labels==j] for j in range(count))
        for ii in domains:
            excluded=np.flatnonzero(r.w[ii].max(0)==0)
            result[np.ix_(ii,excluded)]=0
    else:
        for j,name in enumerate(r.names):
            if name.endswith('.L'):result[(r.rest[:,0]<-.005)&(r.w[:,j]==0),j]=0
            if name.endswith('.R'):result[(r.rest[:,0]>.005)&(r.w[:,j]==0),j]=0
    result/=result.sum(1)[:,None]
    # Original sole/foot influence field is a preservation constraint, independent
    # of the exercise pose. C1 transition from 0.10 to 0.16 metres above rest floor.
    alpha=np.clip((r.rest[:,1]-.10)/.06,0,1);alpha=alpha*alpha*(3-2*alpha)
    result=result*alpha[:,None]+r.w*(1-alpha[:,None])
    return compact_weights(result,continuous)


def coherent_experiments():
    r=Rig();report={}
    for sigma in (15,25,35):
        weights=coherent_weights(r,sigma);np.save(OUT/f'weights-coherent-{sigma}mm.npy',weights)
        export_weights(weights,OUT/f'candidate-coherent-{sigma}.glb',dict(method='area-weighted coherent rest-space field',sigma_mm=sigma,foot_preservation=True))
        report[str(sigma)]=r.metrics(r.deform(r.pose(1.5),weights))
        print(sigma,{k:[round(report[str(sigma)][k]['maximum'],3),round(report[str(sigma)][k]['p99'],3),report[str(sigma)][k]['over2']] for k in ('all','torso','hips','knees')},report[str(sigma)]['surface'],flush=True)
    dump('coherent-experiments.json',report)


def guarded_experiments():
    r=Rig();report={}
    for sigma in (25,35):
        weights=coherent_weights(r,sigma,support_guard=True);np.save(OUT/f'weights-guarded-{sigma}mm.npy',weights)
        export_weights(weights,OUT/f'candidate-guarded-{sigma}.glb',dict(method='coherent rest-space field with original part/component bone-support guard',sigma_mm=sigma,foot_preservation=True))
        report[str(sigma)]=r.metrics(r.deform(r.pose(1.5),weights))
        print(sigma,{k:[round(report[str(sigma)][k]['maximum'],3),round(report[str(sigma)][k]['p99'],3),report[str(sigma)][k]['over2']] for k in ('all','torso','hips','knees')},report[str(sigma)]['surface'],flush=True)
    dump('guarded-experiments.json',report)


def continuous_experiment():
    r=Rig();weights=coherent_weights(r,35,support_guard=True,continuous=True)
    np.save(OUT/'weights-continuous-35mm.npy',weights)
    export_weights(weights,OUT/'candidate-continuous-35.glb',dict(method='guarded coherent field, continuous top-four sparsification',sigma_mm=35,foot_preservation=True))
    report={name:r.metrics(r.deform(world,weights)) for name,world in r.controlled().items()}
    dump('continuous-experiment.json',report)
    print(json.dumps({name:{k:[round(v[k]['maximum'],3),round(v[k]['p99'],3),v[k]['over2']] for k in ('all','torso','hips','knees')} for name,v in report.items()},indent=2))


def build_derivative():
    import shutil
    r=Rig();weights=coherent_weights(r,35,support_guard=True,continuous=True)
    recipe=dict(version=1,method='area-weighted coherent rest-space field',sigma_mm=35,
        support='original per-part / unlabelled connected-component bone support only',
        sparsification='subtract fifth-largest weight, clamp positive, normalize; at most four influences',
        foot_preservation='original field below rest Y=0.10m; smoothstep transition to 0.16m',
        no_pose_fitting=True,no_geometry_change=True,license='CC-BY-SA-4.0')
    export_weights(weights,OUT/'heatsy-squat.glb',recipe)
    np.save(OUT/'accepted-weights.npy',weights)
    for name in ('LICENSE','NOTICE.md','IMPORTER-NOTICE.md','selections.json','muscles.json','za_map.json','MOTION-CODE-MIT.txt'):
        shutil.copy2(ROOT/'outputs/heatsy-bodyweight'/name,OUT/name)
    retarget=json.loads((ROOT/'outputs/heatsy-bodyweight/retarget.json').read_text())
    retarget.update(glb_sha256=sha(OUT/'heatsy-squat.glb'),weight_derivative=recipe)
    dump('retarget.json',retarget);dump('recipe.json',recipe)
    (OUT/'DERIVATION.md').write_text('''# Explicit skin-weight derivative — CC BY-SA 4.0

Heatsy / DDDEV LTD; Z-Anatomy; BodyParts3D. See NOTICE.md and LICENSE.
Source mesh, topology, anatomical IDs, decoded fiber/tendon values, normals,
inverse binds, rig and all squat animation channels remain unchanged.
Only JOINTS_0/WEIGHTS_0 references are replaced with appended, audited data.
The original binary prefix remains present. The deterministic rest-space weight
correction and four-influence reduction are specified in recipe.json.
No anatomical region is removed or renamed. No pose-specific frame edits.
Movement, anatomy and public readiness remain unapproved. This is a derivative,
not a claim that the source author supplied these corrected weights.
''',encoding='utf-8')
    poses={};heat={};metrics={}
    for name,world in r.controlled().items():
        poses[name]=[(np.linalg.inv(world[r.parent[i]])@world[i] if i in r.parent else world[i]).T.ravel().tolist() for i in r.joints]
        y=r.deform(world,weights)
        heat[name]=dict(before=r.heat(r.deform(world)).tolist(),after=r.heat(y).tolist())
        metrics[name]=r.metrics(y)
    dump('diagnostic-poses.json',dict(names=r.names,poses=poses));dump('accepted-strain-heat.json',heat);dump('controlled-after.json',metrics)
    print('Exported tracked derivative:',sha(OUT/'heatsy-squat.glb'))


if __name__=='__main__':
    {'diagnose':diagnose,'transforms':transform_experiments,'transforms_after':lambda:transform_experiments(True),'weights':weight_experiments,'spatial':spatial_experiments,'candidates':candidates,'coherent':coherent_experiments,'guarded':guarded_experiments,'continuous':continuous_experiment,'build':build_derivative}[sys.argv[1] if len(sys.argv)>1 else 'diagnose']()
