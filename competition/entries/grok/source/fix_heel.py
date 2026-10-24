# v5: plant the rear heel in fighting_idle (rotation keys only; key times untouched)
import json,struct,sys,numpy as np
from scipy.spatial.transform import Rotation as R, Slerp
inp,outp=sys.argv[1],sys.argv[2]; FIX=len(sys.argv)>3
b=open(inp,'rb').read()
L=struct.unpack('<I',b[12:16])[0]; g=json.loads(b[20:20+L])
BL=struct.unpack('<I',b[20+L:24+L])[0]; bin_=bytearray(b[28+L:28+L+BL])
N=g['nodes']; idx={n.get('name'):i for i,n in enumerate(N)}
CT={5126:'f'}; NC={'SCALAR':1,'VEC3':3,'VEC4':4}
def acc(i):
    a=g['accessors'][i]; bv=g['bufferViews'][a['bufferView']]
    o=bv.get('byteOffset',0)+a.get('byteOffset',0); n=a['count']*NC[a['type']]
    return np.frombuffer(bytes(bin_[o:o+4*n]),dtype='<f4').reshape(a['count'],NC[a['type']]).astype(float)
def add_acc(arr,typ):
    global bin_
    while len(bin_)%4: bin_.append(0)
    o=len(bin_); data=arr.astype('<f4').tobytes(); bin_+=data
    g['bufferViews'].append({'buffer':0,'byteOffset':o,'byteLength':len(data)})
    a={'bufferView':len(g['bufferViews'])-1,'componentType':5126,'count':len(arr),'type':typ}
    if typ=='VEC3': a['min']=arr.min(0).tolist(); a['max']=arr.max(0).tolist()
    g['accessors'].append(a); return len(g['accessors'])-1
chain=['Hips','{s}UpLeg','{s}Leg','{s}Foot','{s}ToeBase']
def rest_trs(n):
    return np.array(N[n].get('translation',[0,0,0])), np.array(N[n].get('rotation',[0,0,0,1]))
def fk(tr, s, ts):
    """world pos/rot along chain for side s at times ts; tr: dict node->(path->(times,vals,interp))"""
    Pw=np.zeros((len(ts),3)); Rw=R.identity(len(ts)); out={}
    for k in chain:
        n=idx['mixamorig:'+k.format(s=s)]
        t0,q0=rest_trs(n)
        T=np.tile(t0,(len(ts),1)); Q=R.from_quat(np.tile(q0,(len(ts),1)))
        if (n,'translation') in tr:
            tt,v,_=tr[(n,'translation')]; T=np.stack([np.interp(ts,tt,v[:,j]) for j in range(3)],1) if len(tt)>1 else np.tile(v[0],(len(ts),1))
        if (n,'rotation') in tr:
            tt,v,_=tr[(n,'rotation')]
            Q=Slerp(tt,R.from_quat(v))(np.clip(ts,tt[0],tt[-1])) if len(tt)>1 else R.from_quat(np.tile(v[0],(len(ts),1)))
        Pw=Pw+Rw.apply(T); Rw=Rw*Q; out[k.format(s=s)]=(Pw.copy(),Rw,Q)
    return out
def pitch(d): return np.arcsin(d[:,1]/np.linalg.norm(d,axis=1))
up=np.array([0,1,0.])

restfk={s:fk({},s,np.array([0.])) for s in ('Left','Right')}
rest={s:(pitch(restfk[s][s+'ToeBase'][0]-restfk[s][s+'Foot'][0])[0], restfk[s][s+'Foot'][0][0,1], restfk[s][s+'ToeBase'][0][0,1]) for s in restfk}
a=next(a for a in g['animations'] if a['name']=='fighting_idle')
tr={}
for c in a['channels']:
    sm=a['samplers'][c['sampler']]; tr[(c['target']['node'],c['target']['path'])]=(acc(sm['input'])[:,0],acc(sm['output']),c)
for s in ('Left','Right'):
    n=idx['mixamorig:%sFoot'%s]; tt,q,c=tr[(n,'rotation')]
    f=fk(tr,s,tt); d=f[s+'ToeBase'][0]-f[s+'Foot'][0]; tp=pitch(d)-rest[s][0]
    print(s,'pitch dev deg mean %.1f min %.1f max %.1f'%(np.degrees(tp).mean(),np.degrees(tp).min(),np.degrees(tp).max()),
      'ankle dy cm %.1f'%((f[s+'Foot'][0][:,1]-rest[s][1]).mean()*100),'toe dy cm %.1f'%((f[s+'ToeBase'][0][:,1]-rest[s][2]).mean()*100), 'z(fwd) %.2f'%f[s+'Foot'][0][:,2].mean())
    if FIX and s=='Right':   # rear foot (z<0 = behind in glTF +z-forward space): two-bone IK drop the ankle, flatten the foot
        nu,nl=idx['mixamorig:RightUpLeg'],idx['mixamorig:RightLeg']
        for nn in (nu,nl): assert np.allclose(tr[(nn,'rotation')][0],tt), 'key times differ'
        H=f['RightUpLeg'][0]; K=f['RightLeg'][0]; A=f['RightFoot'][0]
        Rpar=f['Hips'][1]; Rup=f['RightUpLeg'][1]; Rlg=f['RightLeg'][1]; Rft=f['RightFoot'][1]
        l1=np.linalg.norm(K-H,axis=1); l2=np.linalg.norm(A-K,axis=1)
        At=A.copy(); At[:,1]=np.minimum(A[:,1],rest[s][1]+0.006)
        def rot_between(u,v):
            u=u/np.linalg.norm(u,axis=1,keepdims=True); v=v/np.linalg.norm(v,axis=1,keepdims=True)
            ax=np.cross(u,v); sn=np.linalg.norm(ax,axis=1); cs=(u*v).sum(1)
            ang=np.arctan2(sn,cs); ax=ax/np.maximum(sn,1e-9)[:,None]; return R.from_rotvec(ax*ang[:,None])
        D=np.linalg.norm(At-H,axis=1); D=np.minimum(D,(l1+l2)*0.999); a_=(At-H)/np.linalg.norm(At-H,axis=1,keepdims=True)
        x=(l1**2-l2**2+D**2)/(2*D); h=np.sqrt(np.maximum(l1**2-x**2,0))
        p=(K-H)-a_*((K-H)*a_).sum(1)[:,None]; p/=np.linalg.norm(p,axis=1,keepdims=True)
        K2=H+a_*x[:,None]+p*h[:,None]; A2=H+a_*D[:,None]
        R1=rot_between(K-H,K2-H); Rup2=R1*Rup
        R2=rot_between(R1.apply(A-K),A2-K2); Rlg2=R2*R1*Rlg
        # foot: world pitch back to rest (flat) minus 3 deg toe-down
        d=f['RightToeBase'][0]-A; delta=-(tp+np.radians(3)); delta=np.minimum(delta,0)*0+delta*(delta>0)
        axf=np.cross(d,np.array([0,1,0.])); axf/=np.linalg.norm(axf,axis=1,keepdims=True)
        Rft2=R.from_rotvec(axf*delta[:,None])*Rft
        Q={nu:(Rpar.inv()*Rup2),nl:(Rup2.inv()*Rlg2),n:(Rlg2.inv()*Rft2)}
        for nn,qq in Q.items():
            qn=qq.as_quat()
            for k in range(1,len(qn)):
                if np.dot(qn[k],qn[k-1])<0: qn[k]*=-1
            cc=tr[(nn,'rotation')][2]; a['samplers'][cc['sampler']]['output']=add_acc(qn,'VEC4'); tr[(nn,'rotation')]=(tt,qn,cc)
        f=fk(tr,s,tt); d=f[s+'ToeBase'][0]-f[s+'Foot'][0]; tp=pitch(d)-rest[s][0]
        print('  fixed',s,'pitch dev %.1f'%np.degrees(tp).mean(),'ankle dy cm %.1f'%((f[s+'Foot'][0][:,1]-rest[s][1]).mean()*100),'toe dy cm %.1f'%((f[s+'ToeBase'][0][:,1]-rest[s][2]).mean()*100))
if FIX:
    while len(bin_)%4: bin_.append(0)
    g['buffers'][0]['byteLength']=len(bin_)
    js=json.dumps(g,separators=(',',':')).encode()
    while len(js)%4: js+=b' '
    tot=12+8+len(js)+8+len(bin_)
    open(outp,'wb').write(struct.pack('<III',0x46546C67,2,tot)+struct.pack('<II',len(js),0x4E4F534A)+js+struct.pack('<II',len(bin_),0x004E4942)+bin_)
