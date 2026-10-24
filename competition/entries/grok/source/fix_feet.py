import json,struct,sys,numpy as np
from scipy.spatial.transform import Rotation as R, Slerp
SRC=json.load(open('src.json'))
inp,outp=sys.argv[1],sys.argv[2]
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
# rest metrics
restfk={s:fk({},s,np.array([0.])) for s in ('Left','Right')}
rest={s:(pitch(restfk[s][s+'ToeBase'][0]-restfk[s][s+'Foot'][0])[0], restfk[s][s+'Foot'][0][0,1], restfk[s][s+'ToeBase'][0][0,1]) for s in restfk}
tgt_hip=restfk['Left']['Hips'][0][0,1]
report=[]
ONLY=set(sys.argv[3].split(',')) if len(sys.argv)>3 else None
for a in g['animations']:
    if ONLY and a['name'] not in ONLY: continue
    name=a['name']; src=SRC[name]; sr=src['rest']; scale=tgt_hip/sr['hip']
    tr={}
    for c in a['channels']:
        sm=a['samplers'][c['sampler']]; tr[(c['target']['node'],c['target']['path'])]=(acc(sm['input'])[:,0],acc(sm['output']),c)
    def srcval(ts,s,key):
        fr=src['frames']; i=np.clip(np.round(ts*src['fps']).astype(int),0,len(fr)-1)
        return np.array([key(fr[j],s) for j in i])
    newq={}
    for s in ('Left','Right'):
        n=idx['mixamorig:%sFoot'%s]; tt,q,c=tr[(n,'rotation')]
        f=fk(tr,s,tt); d=f[s+'ToeBase'][0]-f[s+'Foot'][0]
        tp=pitch(d)-rest[s][0]
        sp=srcval(tt,s,lambda fr,s:fr[s][0])-sr[s][0]
        delta=sp-tp
        ax=np.cross(d,up); ax/=np.linalg.norm(ax,axis=1,keepdims=True)
        Qw=R.from_rotvec(ax*delta[:,None])
        Pw=f[s+'Leg'][1]
        qn=(Pw.inv()*Qw*Pw*R.from_quat(q)).as_quat()
        # keep sign continuity
        for i in range(1,len(qn)):
            if np.dot(qn[i],qn[i-1])<0: qn[i]*=-1
        newq[s]=qn; tr[(n,'rotation')]=(tt,qn,c)
        report.append((name,s,float(np.degrees(np.abs(delta)).mean())))
    # grounding: hips Y
    hn=idx['mixamorig:Hips']; tt,ht,hc=tr[(hn,'translation')]
    clear=[]; sclear=[]
    for s in ('Left','Right'):
        f=fk(tr,s,tt)
        clear.append(np.minimum(f[s+'Foot'][0][:,1]-rest[s][1], f[s+'ToeBase'][0][:,1]-rest[s][2]))
        sclear.append(srcval(tt,s,lambda fr,s:min(fr[s][1]-sr[s][1],fr[s][2]-sr[s][2]))*scale)
    dy=np.minimum(*sclear)-np.minimum(*clear)
    ht=ht.copy(); ht[:,1]+=dy
    report.append((name,'hipdy_mean_cm',float(np.abs(dy).mean()*100)))
    for s in ('Left','Right'):
        n=idx['mixamorig:%sFoot'%s]; c=tr[(n,'rotation')][2]
        a['samplers'][c['sampler']]['output']=add_acc(newq[s].astype(float),'VEC4')
    a['samplers'][hc['sampler']]['output']=add_acc(ht,'VEC3')
g['buffers'][0]['byteLength']=len(bin_)
while len(bin_)%4: bin_.append(0)
g['buffers'][0]['byteLength']=len(bin_)
js=json.dumps(g,separators=(',',':')).encode()
while len(js)%4: js+=b' '
tot=12+8+len(js)+8+len(bin_)
open(outp,'wb').write(struct.pack('<III',0x46546C67,2,tot)+struct.pack('<II',len(js),0x4E4F534A)+js+struct.pack('<II',len(bin_),0x004E4942)+bin_)
for r in report: print(*r)
