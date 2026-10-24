import numpy as np;from glbio import *;from scipy.sparse import coo_matrix;from scipy.sparse.csgraph import connected_components
def arr(g,b,i):
    a=g['accessors'][i];c={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']];d={5126:np.float32,5125:np.uint32,5123:np.uint16,5121:np.uint8}[a['componentType']]
    x=np.frombuffer(raw(g,b,i),d);return (x.reshape(a['count'],c) if c>1 else x).copy()
def prim(g,b,name):
    nodes={n['name']:n for n in g['nodes']};p=g['meshes'][nodes[name]['mesh']]['primitives'][0];at=p['attributes']
    return p,{k:arr(g,b,v) for k,v in at.items()},arr(g,b,p['indices']).reshape(-1,3).astype(int)
def comps(I,n):
    e=np.concatenate([I[:,[0,1]],I[:,[1,2]]]);A=coo_matrix((np.ones(len(e)),(e[:,0],e[:,1])),(n,n))
    return connected_components(A,directed=False)[1]
def boundary_loops(F):
    from collections import defaultdict
    E=np.sort(np.concatenate([F[:,[0,1]],F[:,[1,2]],F[:,[2,0]]]),1);u,c=np.unique(E,axis=0,return_counts=True);be=u[c==1]
    adj=defaultdict(list)
    for a,b_ in be: adj[a].append(b_);adj[b_].append(a)
    seen=set();loops=[]
    for s in adj:
        if s in seen: continue
        st=[s];comp=[]
        while st:
            v=st.pop()
            if v in seen: continue
            seen.add(v);comp.append(v);st+=adj[v]
        loops.append(np.array(comp))
    return loops
def write_prim(g,b,p,A,I):
    def acc(x,typ,ct):
        a={'componentType':ct,'count':len(x),'type':typ}
        if typ=='VEC3': a['min']=x.min(0).tolist();a['max']=x.max(0).tolist()
        return a
    spec={'POSITION':('VEC3',5126,'<f4'),'NORMAL':('VEC3',5126,'<f4'),'TEXCOORD_0':('VEC2',5126,'<f4'),'JOINTS_0':('VEC4',5123,'<u2'),'WEIGHTS_0':('VEC4',5126,'<f4')}
    for k,(t,ct,dt) in spec.items():
        x=np.ascontiguousarray(A[k].astype(dt));p['attributes'][k]=add(g,b,x.tobytes(),acc(x,t,ct),34962)
    x=np.ascontiguousarray(I.astype('<u4').ravel());p['indices']=add(g,b,x.tobytes(),{'componentType':5125,'count':len(x),'type':'SCALAR'},34963)
