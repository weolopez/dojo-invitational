# v3.7 fit pass (Me Fighter agent): pull loose garment fabric onto the body, push out any fabric inside the skin,
# Taubin-smooth the ripple bands, re-skin garments + lower head neck from the body's own weights, report foot heights.
# Usage: blender -b -P 07_fit_v37.py -- in.glb out.glb
import bpy,bmesh,sys,os
from mathutils import Vector
from mathutils.bvhtree import BVHTree
inp,outp=sys.argv[-2],sys.argv[-1]
MAXD={'RashGuard':float(os.environ.get('MAXS','0.011')),'Shorts':float(os.environ.get('MAXH','0.013'))}
MIND=float(os.environ.get('MIND','0.0045'))
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.context.scene.render.fps=30
bpy.ops.import_scene.gltf(filepath=inp)
for o in list(bpy.data.objects):
    if o.name.startswith('Icosphere'): bpy.data.objects.remove(o)
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
meshes={o.name:o for o in bpy.data.objects if o.type=='MESH'}; print('meshes',list(meshes))
body=meshes['Body']
arm.data.pose_position='REST'; bpy.context.view_layer.update()
dg=bpy.context.evaluated_depsgraph_get()
bb=bmesh.new(); bb.from_mesh(body.data); bb.transform(body.matrix_world); bb.normal_update(); bb.faces.ensure_lookup_table(); bb.verts.ensure_lookup_table(); BV=BVHTree.FromBMesh(bb)
def act(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
from mathutils.interpolate import poly_3d_calc
BW=[{body.vertex_groups[g.group].name:g.weight for g in v.groups} for v in body.data.vertices]
def reskin(o,src,mask=None):
    M=o.matrix_world; out=0
    for v in o.data.vertices:
        w=M@v.co; loc,n,fi,d=BV.find_nearest(w)
        if loc is None: continue
        k=max(0.0,min(1.0,(0.03-d)/0.015)) if mask is None else mask[v.index]
        if mask is None and (M.to_3x3()@v.normal).normalized().dot(bb.faces[fi].normal)<0.5: k=0
        if k<=0: continue
        f=bb.faces[fi]; ws=poly_3d_calc([x.co for x in f.verts],loc); acc={}
        for x,b in zip(f.verts,ws):
            for g,val in BW[x.index].items(): acc[g]=acc.get(g,0)+val*b*k
        if k<1:
            for g in v.groups: acc[o.vertex_groups[g.group].name]=acc.get(o.vertex_groups[g.group].name,0)+g.weight*(1-k)
        top=sorted(acc.items(),key=lambda t:-t[1])[:4]; tot=sum(t[1] for t in top)
        if tot<=0: continue
        for g in list(v.groups): o.vertex_groups[g.group].remove([v.index])
        for gname,val in top:
            if gname not in o.vertex_groups: o.vertex_groups.new(name=gname)
            o.vertex_groups[gname].add([v.index],val/tot,'REPLACE')
        out+=1
    print(o.name,'reskinned',out)
    # Laplacian smoothing of the weight field (removes weight steps that crumple fabric)
    me=o.data; nb=[[] for _ in me.vertices]
    for e in me.edges: a,b=e.vertices; nb[a].append(b); nb[b].append(a)
    names=[g.name for g in o.vertex_groups]
    W=[{names[g.group]:g.weight for g in v.groups} for v in me.vertices]
    for it in range(int(os.environ.get('WSMOOTH','6'))):
        N=[]
        for i,wd in enumerate(W):
            if not nb[i]: N.append(wd); continue
            acc={k:v*0.5 for k,v in wd.items()}
            for j in nb[i]:
                for k,v in W[j].items(): acc[k]=acc.get(k,0)+v*0.5/len(nb[i])
            N.append(acc)
        W=N
    for i,wd in enumerate(W):
        top=sorted(wd.items(),key=lambda t:-t[1])[:4]; tot=sum(t[1] for t in top)
        for g in list(me.vertices[i].groups): o.vertex_groups[g.group].remove([i])
        for k,v in top:
            if v/tot>0.002: o.vertex_groups[k].add([i],v/tot,'REPLACE')
for name in os.environ.get('GARMENTS','RashGuard,Shorts').split(','):
    o=meshes[name]; M=o.matrix_world; Mi=M.inverted()
    bm=bmesh.new(); bm.from_mesh(o.data); n0=len(bm.verts); (None if os.environ.get('NOMERGE') else bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=0.00005)); bm.normal_update(); print(name,'merged',n0-len(bm.verts))
    bnd={v for v in bm.verts if v.is_boundary}
    # hem region (rib band + turned edge) keeps its shape: protect 3 rings from the boundary
    ring=set(bnd)
    for k in range(3): ring|={e.other_vert(v) for v in list(ring) for e in v.link_edges}
    pulled=pushed=0; orig={v:v.co.copy() for v in bm.verts}
    for it in range(0 if os.environ.get('NOMOVE') else 3):
        for v in bm.verts:
            w=M@v.co; loc,n,i,d=BV.find_nearest(w)
            if loc is None or d>0.08: continue
            nn=bb.faces[i].normal; s=(w-loc).dot(nn)
            if (M.to_3x3()@v.normal).normalized().dot(nn)<0.5: continue
            if s<MIND and v not in ring: w=loc+nn*MIND; pushed+=1
            elif v in ring: continue
            elif s>MAXD[name]: w=loc+nn*(MAXD[name]+(s-MAXD[name])*0.25); pulled+=1
            v.co=Mi@w
        for lam in (() if os.environ.get('NOTAUBIN') else (0.5,-0.53)):  # Taubin: removes ripple bands without shrinking
            new={v:v.co+(sum((e.other_vert(v).co for e in v.link_edges),Vector())/len(v.link_edges)-v.co)*lam for v in bm.verts if v not in ring and v.link_edges}
            for v,c in new.items(): v.co=c
        bm.normal_update()
        # hem ring follows the displacement of its nearest free neighbour (no flaps, no collapsed hem)
        from mathutils.kdtree import KDTree
        free=[v for v in bm.verts if v not in ring]; KD=KDTree(len(free))
        for k,v in enumerate(free): KD.insert(orig[v],k)
        KD.balance()
        for v in ring:
            c,k,dd=KD.find(orig[v]); f=free[k]; v.co=orig[v]+(f.co-orig[f])
    bm.to_mesh(o.data); bm.free(); o.data.update()
    print(name,'pulled',pulled,'pushed',pushed)
    if name in os.environ.get('RESKIN','RashGuard,Shorts').split(','): reskin(o,body)
    vs=[v for v in o.data.vertices]; print(name,'groups',len(o.vertex_groups),'nogroup',sum(1 for v in vs if not v.groups),'badsum',sum(1 for v in vs if v.groups and abs(sum(g.weight for g in v.groups)-1)>0.01))
# head: lower neck verts take the body's weights (smooth ramp), so seam rides with the body under the spring layer
head=meshes['OwnerHead']
nz=(arm.matrix_world@arm.data.bones['mixamorig:Neck'].head_local).z; hz=(arm.matrix_world@arm.data.bones['mixamorig:Head'].head_local).z
mask=[]
for v in head.data.vertices:
    z=(head.matrix_world@v.co).z; t=(hz-z)/max(1e-4,(hz-nz)); mask.append(max(0.0,min(1.0,t*float(os.environ.get('HEADK','1.6')))))
print('head mask>0',sum(1 for m in mask if m>0),'of',len(mask),'nz',round(nz,3),'hz',round(hz,3))
reskin(head,body,mask)
arm.data.pose_position='POSE'
# feet report for stance clips
sc=bpy.context.scene
for cl in ('fighting_idle','block','block_high','crouch'):
    ac=bpy.data.actions.get(cl) or next((a for a in bpy.data.actions if a.name.startswith(cl)),None)
    if not ac: print('noaction',cl); continue
    arm.animation_data.action=ac; f0,f1=map(int,ac.frame_range); rows=[]
    for f in range(f0,f1+1,max(1,(f1-f0)//6)):
        sc.frame_set(f); r=[]
        for s in ('Left','Right'):
            ft=(arm.matrix_world@arm.pose.bones['mixamorig:'+s+'Foot'].head).z; to=(arm.matrix_world@arm.pose.bones['mixamorig:'+s+'ToeBase'].head).z
            r.append((round(ft,3),round(to,3)))
        rows.append(r)
    print('FEET',cl,rows)
bpy.ops.export_scene.gltf(filepath=outp,export_format='GLB',export_animation_mode='ACTIONS',export_force_sampling=False,export_def_bones=False,export_image_format='AUTO')
