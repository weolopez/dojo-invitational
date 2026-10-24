# v6: material tweak + drop unreferenced bufferViews/accessors left behind by the splices (keeps the file small).
import sys,json;from glbio import *
g,b=load(sys.argv[1]); NS=float(sys.argv[3]) if len(sys.argv)>3 else None
if NS is not None:
    m=next(m for m in g['materials'] if m['name']=='RashGuard'); m['normalTexture']['scale']=NS
# collect referenced accessors
used=set()
def walk(x):
    if isinstance(x,dict):
        for k,v in x.items():
            if k in('indices','POSITION','NORMAL','TEXCOORD_0','TEXCOORD_1','JOINTS_0','WEIGHTS_0','TANGENT','COLOR_0','input','output','inverseBindMatrices') and isinstance(v,int): used.add(v)
            elif k=='attributes': [used.add(a) for a in v.values()]
            else: walk(v)
    elif isinstance(x,list): [walk(y) for y in x]
walk(g['meshes']);walk(g['animations']);walk(g['skins'])
amap={};acc=[]
for i,a in enumerate(g['accessors']):
    if i in used: amap[i]=len(acc);acc.append(a)
bvu={a['bufferView'] for a in acc}|{im['bufferView'] for im in g.get('images',[]) if 'bufferView' in im}
bmap={};bvs=[];nb=bytearray()
for i,bv in enumerate(g['bufferViews']):
    if i not in bvu: continue
    o=bv.get('byteOffset',0);d=b[o:o+bv['byteLength']]
    while len(nb)%4: nb.append(0)
    nbv=dict(bv);nbv['byteOffset']=len(nb);nb+=d;bmap[i]=len(bvs);bvs.append(nbv)
for a in acc: a['bufferView']=bmap[a['bufferView']]
for im in g.get('images',[]):
    if 'bufferView' in im: im['bufferView']=bmap[im['bufferView']]
def remap(x):
    if isinstance(x,dict):
        for k,v in list(x.items()):
            if k in('indices','POSITION','NORMAL','TEXCOORD_0','TEXCOORD_1','JOINTS_0','WEIGHTS_0','TANGENT','COLOR_0','input','output','inverseBindMatrices') and isinstance(v,int): x[k]=amap[v]
            elif k=='attributes': x[k]={kk:amap[vv] for kk,vv in v.items()}
            else: remap(v)
    elif isinstance(x,list): [remap(y) for y in x]
remap(g['meshes']);remap(g['animations']);remap(g['skins'])
g['accessors']=acc;g['bufferViews']=bvs
print('bin',len(b),'->',len(nb))
save(sys.argv[2],g,nb)
