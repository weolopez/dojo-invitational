# v7: remove the stepped lip where the v5/v6 collar yoke rides over the old shirt cut edge on the shoulders.
# The yoke sat at +4.5 mm over skin up to the shirt edge and +1.2 mm over the shirt after it, so it climbed the shirt
# edge in one step. Here the yoke height above the skin is re-solved as a smooth envelope over the shirt edge:
# inside a band of BAND cm around the edge the height field is relaxed (harmonic, 400 passes) with the band rim pinned
# and a floor of shirt height + FLOOR mm wherever the shirt lies underneath, so the yoke ramps over the edge instead
# of stepping. Normals are recomputed smooth. Only RashGuard positions/normals change (UVs, weights, topology kept).
# usage: fix_collar_v7.py in.glb ref_v5.glb out.glb BAND_CM FLOOR_MM
import sys,numpy as np;from collar_common import *;from glbio import *;from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
inp,ref,outp=sys.argv[1:4];BAND=float(sys.argv[4])/100;FLOOR=float(sys.argv[5])/1000;BLEND=float(sys.argv[6]) if len(sys.argv)>6 else 0.0
g,b=load(inp);p,A,I=prim(g,b,'RashGuard');P=A['POSITION'].astype(float);N=A['NORMAL'].astype(float)
lab=comps(I,len(P));isC=lab!=np.argmax(np.bincount(lab));C=np.where(isC)[0]
_,Ab,Ib=prim(g,b,'Human_export');Pb_=Ab['POSITION'].astype(float);Nb_=Ab['NORMAL'].astype(float)
g5,b5=load(ref);_,A5,I5=prim(g5,b5,'RashGuard');P5=A5['POSITION'].astype(float);N5=A5['NORMAL'].astype(float)
l5=comps(I5,len(P5));S=np.where(l5==np.argmax(np.bincount(l5)))[0]
def plane(Pr,Nr,X,k=6):
    d,i=cKDTree(Pr).query(X,k=k);w=1/(d+1e-4);w/=w.sum(1,keepdims=True)
    Pp=(Pr[i]*w[:,:,None]).sum(1);Np=(Nr[i]*w[:,:,None]).sum(1);return Pp,Np/np.linalg.norm(Np,axis=1,keepdims=True),d[:,0]
X=P[C];Pb,Nb,_=plane(Pb_,Nb_,X)
h0=((X-Pb)*Nb).sum(1)
Ps,Ns,_=plane(P5[S],N5[S],X)
# shirt height along the skin normal, where the skin-normal ray from the collar vertex passes through the shirt
t=((Ps-Pb)*Ns).sum(1)/np.clip((Nb*Ns).sum(1),0.3,None);hit=Pb+Nb*t[:,None]
lat=np.linalg.norm((hit-Ps)-((hit-Ps)*Ns).sum(1)[:,None]*Ns,axis=1)
_,_,dS=plane(P5[S],N5[S],hit,2);over=(dS<0.008)&(t>-0.002)&(t<0.03)
key=np.unique(np.round(X*1e5).astype(np.int64),axis=0,return_inverse=True)[1].ravel();m=key.max()+1
CF=I[isC[I[:,0]]];loc=np.full(len(P),-1);loc[C]=np.arange(len(C));LF=key[loc[CF]]
e=np.concatenate([LF[:,[0,1]],LF[:,[1,2]],LF[:,[2,0]]]);Adj=coo_matrix((np.ones(len(e)*2),(np.r_[e[:,0],e[:,1]],np.r_[e[:,1],e[:,0]])),(m,m)).tocsr();Adj.data[:]=1
deg=np.maximum(np.asarray(Adj.sum(1)).ravel(),1)
def K(x): o=np.zeros(m);c=np.zeros(m);np.add.at(o,key,x);np.add.at(c,key,1);return o/np.maximum(c,1)
H0=K(h0);OV=K(over.astype(float))>0.5;T=K(np.where(over,t,0));XK=np.zeros((m,3));np.add.at(XK,key,X);XK/=np.bincount(key,minlength=m)[:,None]
# edge = over vertices next to non-over vertices
nbr_non=(Adj@(~OV).astype(float))>0;edge=OV&nbr_non
dE,_=cKDTree(XK[edge]).query(XK);zone=dE<BAND
floor=np.where(OV,T+FLOOR,0.003)
H=H0.copy()
for it in range(400):
    Hs=(Adj@H)/deg;H[zone]=np.maximum(Hs[zone],floor[zone])
print('collar verts',len(C),'over shirt',over.sum(),'zone',zone.sum(),'max change mm',np.abs(H-H0).max()*1000)
X2=X+Nb*(H[key]-h0)[:,None];P[C]=X2
fn=np.cross(P[CF[:,1]]-P[CF[:,0]],P[CF[:,2]]-P[CF[:,0]]);Ng=np.zeros((m,3))
for k in range(3): np.add.at(Ng,LF[:,k],fn)
Ng/=np.linalg.norm(Ng,axis=1,keepdims=True)+1e-12
# blend toward the v5 shirt normal over the shirt so the yoke shades like the shirt it lies on (sternum patch)
NsK=np.zeros((m,3));np.add.at(NsK,key,np.where(over[:,None],Ns,0));NsK/=np.linalg.norm(NsK,axis=1,keepdims=True)+1e-12
wb=OV.astype(float)
for it in range(20): wb=0.5*wb+0.5*(Adj@wb)/deg
wb=np.clip(wb*1.0,0,1)[:,None]*BLEND
Nf=Ng*(1-wb)+NsK*wb;Nf/=np.linalg.norm(Nf,axis=1,keepdims=True)+1e-12
N[C]=Nf[key]
A['POSITION']=P;A['NORMAL']=N;write_prim(g,b,p,A,I);save(outp,g,b)
