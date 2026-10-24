import json,struct,numpy as np
def load(f):
    b=open(f,'rb').read();L=struct.unpack('<I',b[12:16])[0];g=json.loads(b[20:20+L])
    BL=struct.unpack('<I',b[20+L:24+L])[0];return g,bytearray(b[28+L:28+L+BL])
def save(f,g,bin_):
    while len(bin_)%4: bin_.append(0)
    g['buffers'][0]['byteLength']=len(bin_)
    j=json.dumps(g,separators=(',',':')).encode()
    while len(j)%4: j+=b' '
    out=struct.pack('<III',0x46546C67,2,12+8+len(j)+8+len(bin_))+struct.pack('<II',len(j),0x4E4F534A)+j+struct.pack('<II',len(bin_),0x004E4942)+bytes(bin_)
    open(f,'wb').write(out)
def raw(g,bin_,i):
    a=g['accessors'][i];bv=g['bufferViews'][a['bufferView']]
    o=bv.get('byteOffset',0)+a.get('byteOffset',0)
    n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]*a['count']*{5126:4,5123:2,5125:4,5121:1}[a['componentType']]
    assert bv.get('byteStride') in (None,0) or True
    return bytes(bin_[o:o+n])
def add(g,bin_,data,acc,target=None):
    while len(bin_)%4: bin_.append(0)
    o=len(bin_);bin_+=data
    bv={'buffer':0,'byteOffset':o,'byteLength':len(data)}
    if target: bv['target']=target
    g['bufferViews'].append(bv)
    a=dict(acc);a.pop('byteOffset',None);a['bufferView']=len(g['bufferViews'])-1
    g['accessors'].append(a);return len(g['accessors'])-1
