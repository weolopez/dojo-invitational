import sys;from glbio import *
g,b=load(sys.argv[1]);n,nb=load(sys.argv[2])
idx={x['name']:i for i,x in enumerate(g['nodes'])}
have={a['name'] for a in g['animations']}
for a in n['animations']:
    if a['name'] in have: continue
    m={};S=[]
    for s in a['samplers']:
        for k in ('input','output'):
            if s[k] not in m: m[s[k]]=add(g,b,raw(n,nb,s[k]),n['accessors'][s[k]])
        S.append({'input':m[s['input']],'output':m[s['output']],'interpolation':s.get('interpolation','LINEAR')})
    C=[{'sampler':c['sampler'],'target':{'node':idx[n['nodes'][c['target']['node']]['name']],'path':c['target']['path']}} for c in a['channels']]
    g['animations'].append({'name':a['name'],'samplers':S,'channels':C});print('added',a['name'])
save(sys.argv[3],g,b)
