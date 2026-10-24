# Replace the RashGuard/Shorts mesh geometry of the original GLB with the geometry from a garment-only GLB.
import sys,numpy as np;from glbio import *
g,b=load(sys.argv[1]);n,nb=load(sys.argv[2])
gi={x['name']:i for i,x in enumerate(g['nodes'])}
skin_g=g['skins'][0]['joints']; skin_n=n['skins'][0]['joints']
jmap=np.array([skin_g.index(gi[n['nodes'][j]['name']]) for j in skin_n])
for nd in n['nodes']:
    if nd['name'] not in ('RashGuard','Shorts'): continue
    src=n['meshes'][nd['mesh']]['primitives']; dst=g['meshes'][g['nodes'][gi[nd['name']]]['mesh']]
    mat=dst['primitives'][0].get('material'); prims=[]
    for p in src:
        A={}
        for k,ai in p['attributes'].items():
            if k not in ('POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0'): continue
            acc=n['accessors'][ai]; data=raw(n,nb,ai)
            if k=='JOINTS_0':
                dt={5121:np.uint8,5123:np.uint16}[acc['componentType']]
                j=np.frombuffer(data,dt).reshape(-1,4); data=jmap[j].astype(np.uint16).tobytes(); acc=dict(acc,componentType=5123)
            A[k]=add(g,b,data,acc,34962)
        ia=n['accessors'][p['indices']]; I=add(g,b,raw(n,nb,p['indices']),ia,34963)
        prims.append({'attributes':A,'indices':I,'material':mat,'mode':4})
    dst['primitives']=prims; print('spliced',nd['name'],[g['accessors'][x['attributes']['POSITION']]['count'] for x in prims])
save(sys.argv[3],g,b)
