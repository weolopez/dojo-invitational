import json,struct,sys,numpy as np
inp,outp=sys.argv[1],sys.argv[2]; SKIP={'knockdown_front','getup_back','getup_front'}
b=open(inp,'rb').read();L=struct.unpack('<I',b[12:16])[0];g=json.loads(b[20:20+L])
BL=struct.unpack('<I',b[20+L:24+L])[0];bin_=bytearray(b[28+L:28+L+BL])
def acc(i):
    a=g['accessors'][i];bv=g['bufferViews'][a['bufferView']];o=bv.get('byteOffset',0)+a.get('byteOffset',0)
    return np.frombuffer(bytes(bin_[o:o+4*a['count']]),'<f4').astype(float)
new={}
for a in g['animations']:
    if a['name'] in SKIP: continue
    for s in a['samplers']:
        i=s['input']
        if i not in new:
            t=acc(i)*1.25
            while len(bin_)%4: bin_.append(0)
            o=len(bin_);d=t.astype('<f4').tobytes();bin_+=d
            g['bufferViews'].append({'buffer':0,'byteOffset':o,'byteLength':len(d)})
            g['accessors'].append({'bufferView':len(g['bufferViews'])-1,'componentType':5126,'count':len(t),'type':'SCALAR','min':[float(t.min())],'max':[float(t.max())]})
            new[i]=len(g['accessors'])-1
        s['input']=new[i]
while len(bin_)%4: bin_.append(0)
g['buffers'][0]['byteLength']=len(bin_)
js=json.dumps(g,separators=(',',':')).encode()
while len(js)%4: js+=b' '
open(outp,'wb').write(struct.pack('<III',0x46546C67,2,12+8+len(js)+8+len(bin_))+struct.pack('<II',len(js),0x4E4F534A)+js+struct.pack('<II',len(bin_),0x004E4942)+bin_)
for a in g['animations']: print(a['name'],round(max(g['accessors'][s['input']]['max'][0] for s in a['samplers']),2),end='; ')
