# v7: smooth the shorts (remove lumpy displacement noise) and level the leg hems.
# Positions are welded by location, the leg-opening boundary loops are set to a constant height per leg (the loop's median y),
# a Taubin (lambda/mu) smooth runs on interior vertices with all boundaries pinned, vertices are kept >= MIN mm off the body,
# and normals are recomputed. UVs, joints, weights, topology unchanged.  usage: fix_shorts_v7.py in.glb out.glb ITERS MIN_MM
import sys,numpy as np;from collar_common import *;from glbio import *;from scipy.spatial import cKDTree;from scipy.sparse import coo_matrix
inp,outp=sys.argv[1:3];IT=int(sys.argv[3]);MIN=float(sys.argv[4])/1000
g,b=load(inp);p,A,I=prim(g,b,'Shorts');P=A['POSITION'].astype(float);N=A['NORMAL'].astype(float)
key=np.unique(np.round(P*1e5).astype(np.int64),axis=0,return_inverse=True)[1].ravel();m=key.max()+1
X=np.zeros((m,3));np.add.at(X,key,P);X/=np.bincount(key)[:,None];F=key[I]
F=F[(F[:,0]!=F[:,1])&(F[:,1]!=F[:,2])&(F[:,0]!=F[:,2])]
e=np.concatenate([F[:,[0,1]],F[:,[1,2]],F[:,[2,0]]]);es=np.sort(e,1);u,c=np.unique(es,axis=0,return_counts=True)
bnd=np.zeros(m,bool);bnd[u[c==1].ravel()]=True
Adj=coo_matrix((np.ones(len(e)*2),(np.r_[e[:,0],e[:,1]],np.r_[e[:,1],e[:,0]])),(m,m)).tocsr();Adj.data[:]=1;deg=np.maximum(np.asarray(Adj.sum(1)).ravel(),1)
# the leg openings are closed by the 2 cm turned hem (outer wall -> fold -> inner wall), so the hem line is the fold:
# per leg and per 3.75 deg sector around the leg axis take the lowest vertex (fold height), and shift that sector's
# vertices toward the median fold height with a falloff over 6 cm, giving a constant-height fold.
Y0=X[:,1].copy()
for side in (-1,1):
    leg=(np.sign(X[:,0])==side)&(Y0<0.80);low=leg&(Y0<0.73);c=X[low][:,[0,2]].mean(0)
    th=np.arctan2(X[:,2]-c[1],X[:,0]-c[0]);bins=((th+np.pi)/(2*np.pi)*96).astype(int)%96
    fm=np.array([Y0[low&(bins==k)].min() if (low&(bins==k)).any() else np.nan for k in range(96)])
    fm=np.where(np.isnan(fm),np.nanmedian(fm),fm);fs=np.array([np.mean(fm[[(k-1)%96,k,(k+1)%96]]) for k in range(96)])
    tgt=np.median(fm);print('leg',side,'fold height range mm',(np.ptp(fm))*1000,'-> constant',tgt)
    w=np.clip(1-(Y0-fs[bins])/0.06,0,1);w[~leg]=0;X[:,1]+=w*(tgt-fm[bins])
    pin=leg&(X[:,1]<tgt+0.003);bnd|=pin
_,Ab,_=prim(g,b,'Human_export');Pb=Ab['POSITION'].astype(float);Nb=Ab['NORMAL'].astype(float);T=cKDTree(Pb)
d0,i0=T.query(X);h0=((X-Pb[i0])*Nb[i0]).sum(1)
X0=X.copy();free=~bnd
for it in range(IT):
    for lam in (0.5,-0.53):
        L=(Adj@X)/deg[:,None]-X;X[free]+=lam*L[free]
d,i=T.query(X);h=((X-Pb[i])*Nb[i]).sum(1);lim=np.minimum(h0,MIN)
push=h<lim;X[push]+=Nb[i[push]]*(lim-h)[push][:,None]
print('moved mm max/mean',np.linalg.norm(X-X0,axis=1).max()*1000,np.linalg.norm(X-X0,axis=1).mean()*1000,'pushed',push.sum())
fn=np.cross(X[F[:,1]]-X[F[:,0]],X[F[:,2]]-X[F[:,0]]);Ng=np.zeros((m,3))
for k in range(3): np.add.at(Ng,F[:,k],fn)
Ng/=np.linalg.norm(Ng,axis=1,keepdims=True)+1e-12
A['POSITION']=X[key];A['NORMAL']=Ng[key];write_prim(g,b,p,A,I);save(outp,g,b)
