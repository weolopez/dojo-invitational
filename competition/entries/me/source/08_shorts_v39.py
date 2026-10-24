# Call 9 outfit pass (Me Fighter agent): rebuild Shorts skinning procedurally from the hip/thigh bones
# (the body has no hip skin under the clothes, so body-surface weights fail), slim the boxy legs
# toward the thigh axis with a slight hem flare, then Laplacian-smooth the weights.
# Usage: blender -b -P 08_shorts_v39.py -- in.glb out.glb
import bpy,bmesh,sys,os,math
from mathutils import Vector
inp,outp=sys.argv[-2],sys.argv[-1]
SLIM=float(os.environ.get('SLIM','0.85'))
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.context.scene.render.fps=30
bpy.ops.import_scene.gltf(filepath=inp)
for o in list(bpy.data.objects):
    if o.name.startswith('Icosphere'): bpy.data.objects.remove(o)
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); arm.data.pose_position='REST'; bpy.context.view_layer.update()
s=bpy.data.objects['Shorts']; body=bpy.data.objects['Body']; M=s.matrix_world; Mi=M.inverted()
B=lambda n:(arm.matrix_world@arm.data.bones['mixamorig:'+n].head_local, arm.matrix_world@arm.data.bones['mixamorig:'+n].tail_local)
hipz=B('LeftUpLeg')[0].z
def smooth(t): t=max(0.0,min(1.0,t)); return t*t*(3-2*t)
# thigh radius of the body below the shorts (for a floor on slimming)
def axis(side,z):
    a,b=B(side+'UpLeg'); t=(a.z-z)/(a.z-b.z); return a+(b-a)*t
bodyr={}
for v in body.data.vertices:
    w=body.matrix_world@v.co
    if 0.62<w.z<0.80 and abs(w.x)>0.03:
        side='Left' if w.x>0 else 'Right'; c=axis(side,w.z); r=math.hypot(w.x-c.x,w.y-c.y)
        k=(side,round(w.z,2)); bodyr[k]=max(bodyr.get(k,0),r)
print('body thigh r',sorted(bodyr.items())[:6])
rmin=max(bodyr.values()) if bodyr else 0.08
bm=bmesh.new(); bm.from_mesh(s.data); moved=0
for v in bm.verts:
    w=M@v.co
    if w.z<hipz-0.04 and abs(w.x)>0.02 and abs(w.x)>abs(axis('Left',w.z).x):  # outer side only
        side='Left' if w.x>0 else 'Right'; c=axis(side,w.z); d=Vector((w.x-c.x,w.y-c.y)); r=d.length
        k=smooth((hipz-0.04-w.z)/0.10)          # 0 at upper hip, 1 down the leg
        flare=1.0+0.04*smooth((0.78-w.z)/0.06)    # slight flare at the hem
        tgt=max(r*(1-(1-SLIM)*k)*flare, min(r, rmin+0.018))
        if r>1e-4: d*=tgt/r; w.x=c.x+d.x; w.y=c.y+d.y; v.co=Mi@w; moved+=1
bm.to_mesh(s.data); bm.free(); s.data.update(); print('slimmed',moved)
# procedural weights (blended in only on the outer hip/thigh; inner leg + crotch keep original weights)
OW=[{s.vertex_groups[g.group].name.replace('mixamorig:',''):g.weight for g in v.groups} for v in s.data.vertices]
for g in list(s.vertex_groups): s.vertex_groups.remove(g)
G={n:s.vertex_groups.new(name='mixamorig:'+n) for n in ('Hips','Spine','LeftUpLeg','RightUpLeg')}
me=s.data; W=[]
for v in me.vertices:
    w=M@v.co; d={}
    leg=smooth((hipz+0.05-w.z)/0.17)            # wide hip->thigh blend band (the hip-split fix)
    cr=smooth((abs(w.x)-0.015)/0.05)            # crotch seam stays on Hips (no body skin there to show through)
    sp=smooth((w.z-1.06)/0.04)*0.5              # waistband rides partly on Spine
    l=leg*cr; side='LeftUpLeg' if w.x>0 else 'RightUpLeg'
    d[side]=l; 
    rest=max(0.0,1-sum(d.values())); d['Spine']=rest*sp; d['Hips']=rest*(1-sp)
    m=smooth((abs(w.x)-0.08)/0.05)*float(os.environ.get('MIX','1')); o=OW[v.index]; t=sum(o.values()) or 1
    W.append({k:d.get(k,0)*m+o.get(k,0)/t*(1-m) for k in G})
nb=[[] for _ in me.vertices]
for e in me.edges: a,b=e.vertices; nb[a].append(b); nb[b].append(a)
for it in range(int(os.environ.get('WSMOOTH','8'))):
    W=[wd if not nb[i] else {k:wd.get(k,0)*0.5+sum(W[j].get(k,0) for j in nb[i])*0.5/len(nb[i]) for k in G} for i,wd in enumerate(W)]
for i,wd in enumerate(W):
    tot=sum(wd.values())
    for k,val in wd.items():
        if val/tot>0.002: G[k].add([i],val/tot,'REPLACE')
print('nogroup',sum(1 for v in me.vertices if not v.groups))
arm.data.pose_position='POSE'
bpy.ops.export_scene.gltf(filepath=outp,export_format='GLB',export_animation_mode='ACTIONS',export_force_sampling=False,export_def_bones=False,export_image_format='AUTO')
