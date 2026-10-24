# Call 9 bigger shorts fix (Me Fighter agent): build a hidden low-poly closed proxy under-body
# (pelvis + upper-thigh stubs), skin it to the mixamorig skeleton with heat weights, then transfer
# its weights to the Shorts (nearest face, interpolated) and smooth. The proxy (dark liner material)
# stays in the export so any gap at the crotch / inner hem shows the liner, not the inside of the garment.
# Usage: blender -b -P 09_proxy_underbody.py -- in.glb out.glb
import bpy,bmesh,sys,os,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
inp,outp=sys.argv[-2],sys.argv[-1]
INSET=float(os.environ.get('INSET','0.007')); WS=int(os.environ.get('WSMOOTH','6'))
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.context.scene.render.fps=30
bpy.ops.import_scene.gltf(filepath=inp)
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); arm.data.pose_position='REST'; bpy.context.view_layer.update()
s=bpy.data.objects['Shorts']; AW=arm.matrix_world
B=lambda n:(AW@arm.data.bones['mixamorig:'+n].head_local, AW@arm.data.bones['mixamorig:'+n].tail_local)
# shorts in world space
sbm=bmesh.new(); sbm.from_mesh(s.data); sbm.transform(s.matrix_world); sbm.normal_update()
sv=[v.co.copy() for v in sbm.verts]; bvh=BVHTree.FromBMesh(sbm)
zmin=min(v.z for v in sv); zmax=max(v.z for v in sv)
# build primitives
parts=[]
def add(o): parts.append(o)
for side in ('Left','Right'):
    a,b=B(side+'UpLeg'); d=(b-a).normalized()
    top=a+Vector((0,0,0.06)); bot=a+d*((a.z-(zmin-0.07))/max(1e-4,-d.z))
    # radius: median distance of shorts leg verts to the axis near mid thigh, minus inset
    sgn=1 if side=='Left' else -1
    rs=[]
    for v in sv:
        if zmin+0.01<v.z<zmin+0.08 and v.x*sgn>0.02:
            t=(v-a).dot(d); rs.append((v-(a+d*t)).length)
    rs.sort(); r=(rs[len(rs)//2] if rs else 0.085)*0.93
    L=(top-bot).length
    bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=r,depth=L,location=(top+bot)/2)
    o=bpy.context.object; o.rotation_mode='QUATERNION'; o.rotation_quaternion=Vector((0,0,1)).rotation_difference((top-bot).normalized()); add(o)
    print(side,'thigh r',round(r,3))
cx=[v for v in sv if v.z>zmin+0.14]
mn=Vector([min(v[i] for v in cx) for i in range(3)]); mx=Vector([max(v[i] for v in cx) for i in range(3)])
c=(mn+mx)/2; hs=(mx-mn)/2
bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=1,location=(c.x,c.y,c.z-0.02))
o=bpy.context.object; o.scale=(hs.x*0.95,hs.y*0.95,hs.z*1.05); add(o)
for o in parts: o.select_set(True)
bpy.context.view_layer.objects.active=parts[0]; bpy.ops.object.transform_apply(location=True,rotation=True,scale=True); bpy.ops.object.join()
p=bpy.context.object; p.name='ShortsLiner'
m=p.modifiers.new('r','REMESH'); m.mode='VOXEL'; m.voxel_size=0.012; bpy.ops.object.modifier_apply(modifier='r')
m=p.modifiers.new('d','DECIMATE'); m.ratio=min(1.0,3000/max(1,len(p.data.polygons))); bpy.ops.object.modifier_apply(modifier='d')
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.quads_convert_to_tris(); bpy.ops.object.mode_set(mode='OBJECT')
# keep the proxy inside the shorts by INSET
pushed=0
for v in p.data.vertices:
    loc,n,i,dist=bvh.find_nearest(v.co)
    if loc is None: continue
    if v.co.z>zmin-0.005:
        off=(v.co-loc).dot(n)
        if off>-INSET: v.co=v.co-n*(off+INSET); pushed+=1
# below / near the hem, tuck the liner inside the body's thigh skin so it never shows past the hem
body=bpy.data.objects['Body']; bbm=bmesh.new(); bbm.from_mesh(body.data); bbm.transform(body.matrix_world); bbm.normal_update(); bb=BVHTree.FromBMesh(bbm)
tuck=0
for v in p.data.vertices:
    if v.co.z<zmin+0.035:
        loc,n,i,dist=bb.find_nearest(v.co)
        if loc is None: continue
        off=(v.co-loc).dot(n)
        if off>-0.004: v.co=v.co-n*(off+0.004); tuck+=1
print('tucked',tuck)
p.data.update(); print('liner tris',len(p.data.polygons),'pushed',pushed)
for _ in range(0):
    sm=p.modifiers.new('s','SMOOTH'); sm.iterations=2; sm.factor=0.3; bpy.ops.object.modifier_apply(modifier='s')
mat=bpy.data.materials.new('ShortsLiner'); mat.use_nodes=True
bs=mat.node_tree.nodes['Principled BSDF']; bs.inputs['Base Color'].default_value=(0.025,0.025,0.03,1); bs.inputs['Roughness'].default_value=0.95
p.data.materials.append(mat)
# skin the proxy
bpy.ops.object.select_all(action='DESELECT'); p.select_set(True); arm.select_set(True); bpy.context.view_layer.objects.active=arm
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
allowed={'mixamorig:'+n for n in ('Hips','Spine','LeftUpLeg','RightUpLeg','LeftLeg','RightLeg')}
for g in list(p.vertex_groups):
    if g.name not in allowed: p.vertex_groups.remove(g)
print('liner groups',[g.name for g in p.vertex_groups],'nogroup',sum(1 for v in p.data.vertices if not v.groups))
# smooth + normalize proxy weights
def smoothw(ob,its,names):
    me=ob.data; nb=[[] for _ in me.vertices]
    for e in me.edges: a,b=e.vertices; nb[a].append(b); nb[b].append(a)
    gi={ob.vertex_groups[n].index:n for n in names if n in ob.vertex_groups}
    W=[{gi[g.group]:g.weight for g in v.groups if g.group in gi} for v in me.vertices]
    for _ in range(its):
        W=[w if not nb[i] else {k:w.get(k,0)*0.5+sum(W[j].get(k,0) for j in nb[i])*0.5/len(nb[i]) for k in gi.values()} for i,w in enumerate(W)]
    for g in list(ob.vertex_groups):
        if g.name in names: ob.vertex_groups.remove(g)
    G={n:ob.vertex_groups.new(name=n) for n in names}
    for i,w in enumerate(W):
        t=sum(w.values())
        if t<=0: G['mixamorig:Hips'].add([i],1.0,'REPLACE'); continue
        for k,val in w.items():
            if val/t>0.003: G[k].add([i],val/t,'REPLACE')
smoothw(p,4,sorted(allowed))
# transfer to Shorts
for g in list(s.vertex_groups): s.vertex_groups.remove(g)
for n in sorted(allowed): s.vertex_groups.new(name=n)
dt=s.modifiers.new('dt','DATA_TRANSFER'); dt.object=p; dt.use_vert_data=True; dt.data_types_verts={'VGROUP_WEIGHTS'}
dt.vert_mapping='POLYINTERP_NEAREST'; dt.layers_vgroup_select_src='ALL'; dt.layers_vgroup_select_dst='NAME'
bpy.context.view_layer.objects.active=s
# armature modifier must stay after; move dt to top
while s.modifiers[0].name!='dt': bpy.ops.object.modifier_move_up(modifier='dt')
bpy.ops.object.modifier_apply(modifier='dt')
smoothw(s,WS,sorted(allowed))
print('shorts nogroup',sum(1 for v in s.data.vertices if not v.groups))
arm.data.pose_position='POSE'
bpy.ops.export_scene.gltf(filepath=outp,export_format='GLB',export_animation_mode='ACTIONS',export_force_sampling=False,export_def_bones=False,export_image_format='AUTO')
