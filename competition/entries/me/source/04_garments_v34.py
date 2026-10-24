# v3.3 garment rebuild: outer layer of old shell -> voxel remesh (one clean sheet, no stripe relief)
# -> Taubin smooth -> planar hems -> folds/waistband -> turned hem -> weights transferred, world-box UVs.
import bpy,bmesh,sys,math
from mathutils import Vector, noise
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_point_line
inp,outp=sys.argv[-2],sys.argv[-1]
SUBL=int(__import__('os').environ.get('SUBL','2'))
VOX=float(__import__('os').environ.get('VOX','0.005'))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps=30
bpy.ops.import_scene.gltf(filepath=inp)
for o in list(bpy.data.objects):
    if o.name.startswith('Icosphere'): bpy.data.objects.remove(o)
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
def bone(n): return arm.matrix_world@arm.data.bones['mixamorig:'+n].head_local
fwd=(bone('LeftToeBase')-bone('LeftFoot')); fwd.z=0; fwd.normalize(); up=Vector((0,0,1))
segs=[(arm.matrix_world@b.head_local,arm.matrix_world@b.tail_local) for b in arm.data.bones]
def axis_pt(c):
    best=None
    for a,b in segs:
        p,t=intersect_point_line(c,a,b); t=max(0,min(1,t)); p=a+(b-a)*t; d=(c-p).length
        if best is None or d<best[0]: best=(d,p)
    return best[1]
def outward(f): c=f.calc_center_median(); return (c-axis_pt(c)).dot(f.normal)>0
HEMS=[]
body=bpy.data.objects['Body']; _b=bmesh.new(); _b.from_mesh(body.data); BODYB=[body.matrix_world@v.co for v in _b.verts if v.is_boundary]
mats={n:bpy.data.materials[n] for n in ('TrainingFabric','ShortsFabric','RibTrim')}
SIDE=('Left','Right')
def act(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
def apply(o,m): act(o); bpy.ops.object.modifier_apply(modifier=m.name)

def rebuild(name, nrim, mat, foldamp, waistband=None, outside_of=None, solid=0.010, smooth=60, lap=0):
    old=bpy.data.objects[name]; old.name=name+'_old'
    src=old.copy(); src.data=old.data.copy(); bpy.context.scene.collection.objects.link(src)
    src.modifiers.clear(); src.parent=None; src.matrix_world=old.matrix_world
    bm=bmesh.new(); bm.from_mesh(src.data); bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=0.0002); bm.normal_update()
    oldb=[v.co.copy() for v in bm.verts if v.is_boundary]
    obvh=BVHTree.FromBMesh(bm)
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if not outward(f)],context='FACES')
    bm.to_mesh(src.data); bm.free()
    bodyb=[p for p in BODYB if obvh.find_nearest(p)[3] is not None and obvh.find_nearest(p)[3]<0.03]
    act(src); bpy.ops.object.vertex_group_remove(all=True)
    m=src.modifiers.new('s','SOLIDIFY'); m.thickness=solid; m.offset=-1; apply(src,m)
    m=src.modifiers.new('r','REMESH'); m.mode='VOXEL'; m.voxel_size=VOX; m.adaptivity=0; apply(src,m)
    bm=bmesh.new(); bm.from_mesh(src.data); bm.normal_update()
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if not outward(f)],context='FACES')
    # keep largest piece
    seen=set(); comps=[]
    for f in bm.faces:
        if f in seen: continue
        st=[f]; c=[]
        while st:
            x=st.pop()
            if x in seen: continue
            seen.add(x); c.append(x); st+=[y for e in x.edges for y in e.link_faces if y not in seen]
        comps.append(c)
    comps.sort(key=len)
    for c in comps[:-1]: bmesh.ops.delete(bm,geom=c,context='FACES')
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
    # Taubin smoothing
    bnd={v for v in bm.verts if v.is_boundary}
    for it in range(smooth):
        for lam in (0.5,-0.53):
            new={}
            for v in bm.verts:
                if v in bnd: continue
                nb=[e.other_vert(v).co for e in v.link_edges]; new[v]=v.co+(sum(nb,Vector())/len(nb)-v.co)*lam
            for v,c in new.items(): v.co=c
    if lap:
        bm.normal_update(); orig={v:(v.co.copy(),v.normal.copy()) for v in bm.verts}
        for it in range(lap):
            new={}
            for v in bm.verts:
                if v in bnd or not v.link_edges: continue
                nb=[e.other_vert(v).co for e in v.link_edges]; new[v]=v.co*0.3+sum(nb,Vector())/len(nb)*0.7
            for v,c in new.items(): v.co=c
        sh=[(orig[v][0]-v.co).dot(orig[v][1]) for v in bm.verts if v not in bnd]
        mean=sum(sh)/len(sh); print(name,'lap shrink mean',round(mean,4))
        bm.normal_update()
        for v in bm.verts:
            if v not in bnd: v.co+=v.normal*mean
    bm.to_mesh(src.data); bm.free()
    m=src.modifiers.new('ss','SUBSURF'); m.levels=SUBL; apply(src,m)
    bm=bmesh.new(); bm.from_mesh(src.data); bm.normal_update()
    # boundary loops: the NRIM largest are hems (cleaned), the rest are gaps (filled)
    def bloops():
        left={e for e in bm.edges if e.is_boundary}; out=[]
        while left:
            st=[left.pop()]; c={st[0]}
            while st:
                x=st.pop()
                for v in x.verts:
                    for y in v.link_edges:
                        if y in left: left.remove(y); c.add(y); st.append(y)
            out.append(c)
        return sorted(out,key=len,reverse=True)
    L=bloops(); print(name,'loops',[len(l) for l in L][:10])
    def cen(l): return sum((v.co for e in l for v in e.verts),Vector())/(2*len(l))
    big=[l for l in L if len(l)>40]
    rims=[max(big,key=lambda l:cen(l).z)]
    if nrim==4: rims.append(min(big,key=lambda l:cen(l).z))
    rims.append(max(big,key=lambda l:cen(l).x)); rims.append(min(big,key=lambda l:cen(l).x))
    if nrim==3:
        rims=[rims[0]]+[max([l for l in big if cen(l).x*sg>0.02],key=lambda l:-cen(l).z) for sg in (1,-1)]
    print(name,'rims',[(len(l),[round(x,2) for x in cen(l)]) for l in rims])
    holes=[e for l in L if not any(l is r for r in rims) for e in l]
    if holes:
        r=bmesh.ops.holes_fill(bm,edges=holes,sides=5000); bmesh.ops.triangulate(bm,faces=r['faces'])
        print(name,'filled',len(r['faces']))
    L=[l for l in bloops() if len(l)>40]
    for l in L:
        vs={v for e in l for v in e.verts}
        nbr={v:[e.other_vert(v) for e in v.link_edges if e in l] for v in vs}
        for it in range(250):
            new={v:(v.co*0.5+(nb[0].co+nb[1].co)*0.25) for v,nb in nbr.items() if len(nb)==2}
            for v,c in new.items(): v.co=c
        # relax the two rows behind the rim so the stretched faces even out
        ring=set(vs)
        for k in range(3):
            nxt={e.other_vert(v) for v in ring for e in v.link_edges}-ring
            for it in range(4):
                for v in nxt:
                    nb=[e.other_vert(v).co for e in v.link_edges]; v.co=v.co*0.5+sum(nb,Vector())/len(nb)*0.5
            ring|=nxt
    if nrim==4:
        bm.normal_update()
        hem=min([l for l in bloops() if len(l)>40],key=lambda l:sum(v.co.z for e in l for v in e.verts)/(2*len(l)))
        le=list(hem)
        for zt in (None,TUCK):
            r=bmesh.ops.extrude_edge_only(bm,edges=le)
            nv=[x for x in r['geom'] if isinstance(x,bmesh.types.BMVert)]
            zmin=min(v.co.z for v in nv)
            for v in nv: v.co.z = (zmin-0.004) if zt is None else zt
            le=[x for x in r['geom'] if isinstance(x,bmesh.types.BMEdge) and x.is_boundary]
    # clean hem loop: dissolve tiny bisect slivers
    bmesh.ops.dissolve_degenerate(bm,edges=bm.edges,dist=VOX*0.2)
    from mathutils.kdtree import KDTree
    bv=[v.co.copy() for v in bm.verts if v.is_boundary]; KD=KDTree(len(bv))
    for k,c in enumerate(bv): KD.insert(c,k)
    KD.balance()
    bm.normal_update()
    for v in bm.verts:
        p=v.co; v.co+=v.normal*foldamp(p)*min(1,KD.find(p)[2]/0.025)
        if waistband: v.co+=v.normal*waistband(p)
    if outside_of:
        sbm=bmesh.new(); sbm.from_mesh(outside_of.data); sb=BVHTree.FromBMesh(sbm); bm.normal_update()
        for v in bm.verts:
            loc,n,i,d=sb.find_nearest(v.co)
            if loc is not None and d<0.03 and (v.co-loc).dot(v.normal)<0.006: v.co=loc+v.normal*0.006
    for it in range(2):  # relax after pushes
        new={}
        for v in bm.verts:
            if v.is_boundary or not v.link_edges: continue
            nb=[e.other_vert(v).co for e in v.link_edges]; new[v]=v.co*0.6+sum(nb,Vector())/len(nb)*0.4
        for v,c in new.items(): v.co=c
    bm.normal_update()
    # rib band near hems + turned-under edge
    bnd=[e for e in bm.edges if e.is_boundary]
    ring={v for e in bnd for v in e.verts}
    for k in range(2): ring|={e.other_vert(v) for v in list(ring) for e in v.link_edges}
    for f in bm.faces: f.material_index=1 if all(v in ring for v in f.verts) else 0
    ret=bmesh.ops.extrude_edge_only(bm,edges=bnd)
    nv=set(x for x in ret['geom'] if isinstance(x,bmesh.types.BMVert))
    for v in nv:
        s=[e.other_vert(v) for e in v.link_edges if e.other_vert(v) not in nv][0]; v.co=s.co-s.normal*0.0035
    for f in ret['geom']:
        if isinstance(f,bmesh.types.BMFace): f.material_index=1
    # world box UVs (tiling fabric)
    uv=bm.loops.layers.uv.verify()
    for f in bm.faces:
        n=f.normal; ax=max(range(3),key=lambda i:abs(n[i]))
        for l in f.loops:
            c=l.vert.co; a,b=[c[i] for i in range(3) if i!=ax]
            l[uv].uv=(a/1.6,b/1.6)
    bm.to_mesh(src.data); bm.free()
    src.data.materials.clear(); src.data.materials.append(mat); src.data.materials.append(mats['RibTrim'])
    for p in src.data.polygons: p.use_smooth=True
    # weights from the old garment
    for vg in old.vertex_groups: src.vertex_groups.new(name=vg.name)
    dt=src.modifiers.new('dt','DATA_TRANSFER'); dt.object=old; dt.use_vert_data=True; dt.data_types_verts={'VGROUP_WEIGHTS'}
    dt.vert_mapping='POLYINTERP_NEAREST'; dt.layers_vgroup_select_src='ALL'; dt.layers_vgroup_select_dst='NAME'
    apply(src,dt)
    act(src); bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL',limit=4); bpy.ops.object.vertex_group_normalize_all(lock_active=False)
    src.parent=arm; src.matrix_parent_inverse=arm.matrix_world.inverted()
    am=src.modifiers.new('Armature','ARMATURE'); am.object=arm
    for mt in src.data.materials: mt.use_backface_culling=False
    bpy.data.objects.remove(old); src.name=name; src.data.name=name
    print(name,'verts',len(src.data.vertices),'tris',sum(len(p.vertices)-2 for p in src.data.polygons))
    return src

neck=bone('Neck'); zb=neck.z-0.005; zf=neck.z-0.05; d=0.08
neck_no=(up*2*d+fwd*(zb-zf)).normalized(); neck_co=neck+up*((zb+zf)/2-neck.z)
SHORTS_TOP=1.08; TUCK=0.975
SL=float(__import__('os').environ.get('SL','0.20')); LG=float(__import__('os').environ.get('LG','0.30'))
shirt_cuts=[(lambda c:c.z>1.42 and abs(c.x)<0.24,neck_co,neck_no),(lambda c:c.z<1.15,Vector((0,0,1.0)),-up)]
for s,sg in (('Left',1),('Right',-1)):
    a,b=bone(s+'Arm'),bone(s+'ForeArm'); dr=(b-a).normalized()
    shirt_cuts.append(((lambda sg,a,dr:(lambda c:c.x*sg>0.2 and (c-a).dot(dr)>0.07))(sg,a,dr),a+dr*SL,dr))
shorts_cuts=[(lambda c:c.z>1.0,Vector((0,0,SHORTS_TOP)),up)]
for s,sg in (('Left',1),('Right',-1)):
    a,b=bone(s+'UpLeg'),bone(s+'Leg'); dr=(b-a).normalized()
    shorts_cuts.append(((lambda sg:(lambda c:c.x*sg>0.0 and c.z<0.92))(sg),a+dr*LG,dr))
def g(x,s): return math.exp(-(x/s)**2)
def around(p,a,b):
    dr=(b-a).normalized(); q=p-a; t=q.dot(dr); r=q-dr*t
    ref=fwd-dr*fwd.dot(dr); ref.normalize(); oth=dr.cross(ref)
    return t,math.atan2(r.dot(oth),r.dot(ref))
LEGS={sg:(bone(s+'UpLeg'),bone(s+'Leg')) for s,sg in (('Left',1),('Right',-1))}
ARMS={sg:(bone(s+'Arm'),bone(s+'ForeArm')) for s,sg in (('Left',1),('Right',-1))}
def shortsfold(p):
    sg=1 if p.x>0 else -1; a,b=LEGS[sg]; t,th=around(p,a,b)
    w=max(0,min(1,(0.93-p.z)/0.08))          # hangs free below the hip, pinned by the waistband
    ph=th*5+t*9*sg+1.3*sg
    cre=max(0,math.sin(ph))**6
    return 0.0055*w*cre*(0.6+0.4*math.sin(th*2+0.7))
def shirtfold(p):
    d=0.0
    for sg,(a,b) in ARMS.items():                 # sleeve: soft rings bunching under the armpit
        if p.x*sg>0.17:
            t,th=around(p,a,b); under=0.5-0.5*math.cos(th)   # strongest on the underside
            d+=0.0028*max(0,math.sin(t*95+th))**4*under
    side=abs(p.x)/0.17                           # torso flanks: shallow diagonal drag folds toward the waist
    if p.z>SHORTS_TOP and abs(p.x)<0.2:
        z=p.z-SHORTS_TOP
        d+=0.0022*g(z-0.06,0.07)*min(1,side**3)*max(0,math.sin(z*70+abs(p.x)*40))**4
    return d
shirt=rebuild('RashGuard',4,mats['TrainingFabric'],shirtfold,smooth=10,lap=int(__import__('os').environ.get('LAPT','40')))
def wb(p):
    t=max(0,min(1,(p.z-(SHORTS_TOP-0.045))/0.04)); ang=math.atan2(p.y,p.x)
    return t*(0.002+0.0015*(0.5+0.5*math.sin(ang*70)))
shorts=rebuild('Shorts',3,mats['ShortsFabric'],shortsfold,waistband=wb,smooth=10,lap=int(__import__('os').environ.get('LAPS','60')))
# tuck: shirt stays under the shorts where they overlap
sbm=bmesh.new(); sbm.from_mesh(shorts.data); sb=BVHTree.FromBMesh(sbm)
tm=shirt.data; moved=0; TUCKP=int(__import__('os').environ.get('TUCKP','0'))
for v in tm.vertices:
    if TUCKP and v.co.z<SHORTS_TOP+0.02:
        loc,n,i,d=sb.find_nearest(v.co)
        if loc is not None and d<0.05 and (v.co-loc).dot(n)>-0.006:
            v.co=loc-n*0.007; moved+=1
print('tucked',moved)
bpy.ops.export_scene.gltf(filepath=outp,export_format='GLB',export_animation_mode='ACTIONS',export_force_sampling=False,export_def_bones=False,export_image_format='AUTO')
