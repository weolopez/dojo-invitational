# v6 collar fix, spliced into the RashGuard primitive only.
# The v5 collar band was exported as 2176 loose quads (4 unshared verts each, flat normals, every quad UV 0..1), so it
# shaded faceted, tiled the knit per quad and opened hairline cracks when the neck is pushed. Here:
#  1. weld the collar quads (positions within 0.05 mm), smooth area-weighted normals, cylindrical UVs (one seam at the back)
#  2. Laplacian-smooth the collar skin weights along the band (top-4 kept, renormalised) so it bends as one piece
#  3. delete shirt triangles that lie fully under the collar (eroded 2 rings from any visible shirt vertex) - the old
#     shirt edge poking through was the faint yoke/overlap seam
import sys,numpy as np;from glbio import *;from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix;from scipy.sparse.csgraph import connected_components
g,b=load(sys.argv[1]);nodes={n['name']:n for n in g['nodes']}
p=g['meshes'][nodes['RashGuard']['mesh']]['primitives'][0];at=p['attributes']
def arr(i):
    a=g['accessors'][i];c={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']];d={5126:np.float32,5125:np.uint32,5123:np.uint16,5121:np.uint8}[a['componentType']]
    x=np.frombuffer(raw(g,b,i),d);return (x.reshape(a['count'],c) if c>1 else x).copy()
P=arr(at['POSITION']).astype(float);N=arr(at['NORMAL']).astype(float);UV=arr(at['TEXCOORD_0']).astype(float)
J=arr(at['JOINTS_0']).astype(int);Wt=arr(at['WEIGHTS_0']).astype(float);I=arr(p['indices']).reshape(-1,3).astype(int)
n=len(P);e=np.concatenate([I[:,[0,1]],I[:,[1,2]]]);A=coo_matrix((np.ones(len(e)),(e[:,0],e[:,1])),(n,n))
_,lab=connected_components(A,directed=False);main=np.argmax(np.bincount(lab));isC=lab!=main
shirtV=np.where(~isC)[0];colV=np.where(isC)[0]
shirtF=I[~isC[I[:,0]]];colF=I[isC[I[:,0]]]
# 1 weld
kd=cKDTree(P[colV]);pairs=kd.query_pairs(5e-5,output_type='ndarray')
parent=np.arange(len(colV))
def find(x):
    while parent[x]!=x: parent[x]=parent[parent[x]];x=parent[x]
    return x
for a_,c_ in pairs:
    ra,rc=find(a_),find(c_)
    if ra!=rc: parent[max(ra,rc)]=min(ra,rc)
root=np.array([find(i) for i in range(len(colV))]);u,inv=np.unique(root,return_inverse=True)
CP=P[colV][u];loc=np.full(n,-1);loc[colV]=inv;CF=loc[colF]
CF=CF[(CF[:,0]!=CF[:,1])&(CF[:,1]!=CF[:,2])&(CF[:,0]!=CF[:,2])]
print('collar verts',len(colV),'->',len(CP),'faces',len(CF))
# weights: dense per joint, average duplicates
nj=len(g['skins'][0]['joints']);D=np.zeros((len(colV),nj))
np.add.at(D,(np.repeat(np.arange(len(colV)),4),J[colV].ravel()),Wt[colV].ravel())
CW=np.zeros((len(CP),nj));np.add.at(CW,inv,D);CW/=np.bincount(inv)[:,None]
# 2 smooth weights along the band (vertex adjacency)
ce=np.concatenate([CF[:,[0,1]],CF[:,[1,2]],CF[:,[2,0]]]);m=len(CP)
Adj=coo_matrix((np.ones(len(ce)*2),(np.r_[ce[:,0],ce[:,1]],np.r_[ce[:,1],ce[:,0]])),(m,m)).tocsr();Adj.data[:]=1
deg=np.asarray(Adj.sum(1)).ravel()
for it in range(int(sys.argv[3]) if len(sys.argv)>3 else 4): CW=0.5*CW+0.5*(Adj@CW)/deg[:,None]
top=np.argsort(-CW,1)[:,:4];CJ=top;CWt=np.take_along_axis(CW,top,1);CWt/=CWt.sum(1,keepdims=True)
# 2b drop the collar's overlap skirt that lay over the shirt (its uneven lower edge and mismatched knit read as a
#    blotchy yoke seam); keep 9 mm of overlap below the band so no gap can open
kdS=cKDTree(P[shirtV]);dd,ii=kdS.query(CP,k=8);over=np.zeros(len(CP),bool)
for v in range(len(CP)):
    q=P[shirtV][ii[v]]-CP[v];nrm=N[shirtV][ii[v]];al=(q*nrm).sum(1);lat=np.linalg.norm(q-nrm*al[:,None],axis=1)
    over[v]=np.any((dd[v]<0.012)&(lat<0.006))
nov=np.where(~over)[0]
if len(nov):
    dnov,_=cKDTree(CP[nov]).query(CP);dropV=over&(dnov>(float(sys.argv[4]) if len(sys.argv)>4 else 0.009))
else: dropV=np.zeros(len(CP),bool)
CF=CF[~dropV[CF].all(1)];print('collar over-shirt verts',over.sum(),'dropped',dropV.sum(),'collar faces',len(CF))
used=np.unique(CF);rm=np.full(len(CP),-1);rm[used]=np.arange(len(used))
CP=CP[used];CJ=CJ[used];CWt=CWt[used];CF=rm[CF]
# normals
fn=np.cross(CP[CF[:,1]]-CP[CF[:,0]],CP[CF[:,2]]-CP[CF[:,0]]);CN=np.zeros_like(CP)
for k in range(3): np.add.at(CN,CF[:,k],fn)
CN/=np.linalg.norm(CN,axis=1,keepdims=True)+1e-12
# 3 cylindrical UVs around the neck axis (glTF: y up), seam at the back (-z)
cx,cz=CP[:,0].mean(),CP[:,2].mean();ang=np.arctan2(CP[:,0]-cx,-(CP[:,2]-cz))  # 0 at the back
uu=(ang%(2*np.pi))/(2*np.pi)*0.35;vv=CP[:,1]*0.6
# split seam: faces whose u span > half range get their low-u verts duplicated at +0.35
cu=uu[CF];bad=(cu.max(1)-cu.min(1))>0.175;extra=[]
CP=list(CP);CN=list(CN);UVc=list(np.c_[uu,vv]);CJ=list(CJ);CWt=list(CWt);dup={}
for fi in np.where(bad)[0]:
    for k in range(3):
        v=CF[fi,k]
        if uu[v]<0.175:
            if v not in dup:
                dup[v]=len(CP);CP.append(CP[v]);CN.append(CN[v]);UVc.append(np.array([uu[v]+0.35,vv[v]]));CJ.append(CJ[v]);CWt.append(CWt[v])
            CF[fi,k]=dup[v]
CP,CN,UVc,CJ,CWt=map(np.array,(CP,CN,UVc,CJ,CWt))
# 4 shirt faces hidden under the collar
kdC=cKDTree(CP);nb=kdC.query_ball_point(P[shirtV],0.02);hid=np.zeros(n,bool)
for i,l in enumerate(nb):
    if not l: continue
    v=shirtV[i];d=CP[l]-P[v];al=d@N[v];lat=np.linalg.norm(d-np.outer(al,N[v]),axis=1)
    if np.any((np.abs(al)<0.02)&(al>-0.0005)&(lat<0.004)): hid[v]=True
adj=[[] for _ in range(n)]
for x,y in np.concatenate([shirtF[:,[0,1]],shirtF[:,[1,2]],shirtF[:,[2,0]]]): adj[x].append(y);adj[y].append(x)
h=hid.copy()
for r in range(2):
    nh=h.copy()
    for v in np.where(h)[0]:
        if any(not h[u_] for u_ in adj[v]): nh[v]=False
    h=nh
keepF=shirtF[~h[shirtF].all(1)];print('shirt tris',len(shirtF),'->',len(keepF))
# rebuild: shirt verts (reindexed) + collar
sidx=np.full(n,-1);sidx[shirtV]=np.arange(len(shirtV))
NP=np.r_[P[shirtV],CP].astype('<f4');NN=np.r_[N[shirtV],CN].astype('<f4');NU=np.r_[UV[shirtV],UVc].astype('<f4')
NJ=np.r_[J[shirtV],CJ].astype('<u2');NW=np.r_[Wt[shirtV],CWt].astype('<f4')
NI=np.r_[sidx[keepF],CF+len(shirtV)].astype('<u4').ravel()
def acc(arr_,typ,ct):
    a={'componentType':ct,'count':len(arr_),'type':typ}
    if typ=='VEC3': a['min']=arr_.min(0).tolist();a['max']=arr_.max(0).tolist()
    return a
p['attributes']={'POSITION':add(g,b,NP.tobytes(),acc(NP,'VEC3',5126),34962),'NORMAL':add(g,b,NN.tobytes(),acc(NN,'VEC3',5126),34962),
 'TEXCOORD_0':add(g,b,NU.tobytes(),acc(NU,'VEC2',5126),34962),'JOINTS_0':add(g,b,NJ.tobytes(),acc(NJ,'VEC4',5123),34962),
 'WEIGHTS_0':add(g,b,NW.tobytes(),acc(NW,'VEC4',5126),34962)}
p['indices']=add(g,b,NI.tobytes(),{'componentType':5125,'count':len(NI),'type':'SCALAR'},34963)
print('rashguard verts',len(NP),'tris',len(NI)//3)
save(sys.argv[2],g,b)
