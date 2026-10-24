# v6: delete Human_export (skin) triangles that lie fully under the rash guard (incl. the v5 collar band) or shorts,
# eroded RING vertex rings back from every visible edge (v6 ships RING=1). The body index buffer changes;
# optional SINK pushes hidden vertices inward (v6 ships SINK=0). Face/head vertices are never touched (never under a garment). Removes skin poke-through at the collar when the spring
# layer / head look-at pushes the neck, and frees triangle budget.
import sys,numpy as np;from scipy.spatial import cKDTree;from glbio import *
g,b=load(sys.argv[1]); RING=int(sys.argv[3]) if len(sys.argv)>3 else 3
SINK=float(sys.argv[4]) if len(sys.argv)>4 else 0.0
nodes={n['name']:n for n in g['nodes']}
def arr(i,dt=np.float32):
    a=g['accessors'][i];c={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
    d={5126:np.float32,5125:np.uint32,5123:np.uint16,5121:np.uint8}[a['componentType']]
    return np.frombuffer(raw(g,b,i),d).reshape(a['count'],c) if c>1 else np.frombuffer(raw(g,b,i),d)
def prim(name): return g['meshes'][nodes[name]['mesh']]['primitives'][0]
bp=prim('Human_export'); P=arr(bp['attributes']['POSITION']).astype(float); N=arr(bp['attributes']['NORMAL']).astype(float)
I=arr(bp['indices']).astype(np.int64).reshape(-1,3)
hidden=np.zeros(len(P),bool)
for gname in ('RashGuard','Shorts'):
    Q=arr(prim(gname)['attributes']['POSITION']).astype(float); kd=cKDTree(Q)
    nb=kd.query_ball_point(P,0.025)
    for v,l in enumerate(nb):
        if not l: continue
        d=Q[l]-P[v]; along=d@N[v]; lat=np.linalg.norm(d-np.outer(along,N[v]),axis=1)
        if np.any((along>0.0005)&(lat<0.006)): hidden[v]=True
# erode: unhide anything within RING edge-rings of a non-hidden vertex
adj=[[] for _ in range(len(P))]
for a,c in ((0,1),(1,2),(2,0)):
    for x,y in zip(I[:,a],I[:,c]): adj[x].append(y); adj[y].append(x)
h=hidden.copy(); depth=np.zeros(len(P))
for r in range(RING):
    vis=~h; nh=h.copy()
    for v in np.where(h)[0]:
        if any(vis[u] for u in adj[v]): nh[v]=False
    depth[h&~nh]=r+1
    h=nh
depth[h]=RING+1
# hidden-but-kept skin near the garment edges sinks 1.5 mm per ring (max 4.5 mm) so it can't poke through when the
# spring layer pushes the neck/shoulders; ring 0 (touching visible skin) stays put
off=np.minimum(np.maximum(depth-1,0)*SINK,3*SINK)*hidden
P2=(P-N*off[:,None]).astype('<f4'); pa=dict(g['accessors'][bp['attributes']['POSITION']]); pa['min']=P2.min(0).tolist(); pa['max']=P2.max(0).tolist()
bp['attributes']['POSITION']=add(g,b,P2.tobytes(),pa,34962); print('sunk verts',(off>0).sum())
keep=~h[I].all(1)
print('body tris',len(I),'-> kept',keep.sum(),'removed',(~keep).sum())
newI=I[keep].astype(np.uint32)
ia=dict(g['accessors'][bp['indices']]); ia['count']=newI.size; ia['componentType']=5125
bp['indices']=add(g,b,newI.tobytes(),ia,34963)
save(sys.argv[2],g,b)
