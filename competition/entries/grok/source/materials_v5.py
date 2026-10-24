# v5 material edits at the glTF JSON level (no re-export):
#  - garments: the Poly Haven Bi-Stretch normal/roughness and recoloured albedo (horizontal ribs = ripple bands, and
#    blotchy) are replaced by the procedural knit maps from weave_tex.py; colour comes from baseColorFactor
#  - skin: the reddish KHR_materials_sheen (0.55,0.36,0.28) produced the red rim line under the jaw at grazing angles;
#    it is replaced by a faint neutral-warm sheen. Skin textures/normal/roughness are untouched.
import sys; from glbio import *
g,b=load(sys.argv[1]); d=sys.argv[2]
def put_img(idx,path):
    data=open(path,'rb').read()
    while len(b)%4: b.append(0)
    o=len(b); b.extend(data); g['bufferViews'].append({'buffer':0,'byteOffset':o,'byteLength':len(data)})
    g['images'][idx]={'bufferView':len(g['bufferViews'])-1,'mimeType':'image/png','name':path.split('/')[-1][:-4]}
put_img(14,d+'/knit_nor.png'); put_img(16,d+'/knit_rough.png'); put_img(15,d+'/knit_diff.png')
M={m['name']:m for m in g['materials']}
M['RashGuard']['pbrMetallicRoughness']['baseColorFactor']=[0.026,0.027,0.030,1]
M['Shorts']['pbrMetallicRoughness']['baseColorFactor']=[0.013,0.013,0.016,1]
for n in ('RashGuard','Shorts'):
    M[n]['normalTexture']['scale']=0.6
    M[n]['extensions']['KHR_materials_sheen']={'sheenColorFactor':[0.05,0.05,0.055],'sheenRoughnessFactor':0.6}
M['Skin']['extensions']['KHR_materials_sheen']={'sheenColorFactor':[0.09,0.075,0.065],'sheenRoughnessFactor':0.5}
save(sys.argv[3],g,b); print('ok')
