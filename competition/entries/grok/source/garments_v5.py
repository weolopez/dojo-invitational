# Grok v5 garments (call #5). Input: the v2 GLB (garments carry the old MARBLE displacement). Output: a garment-only
# GLB, spliced into the shipped fighter.glb by splice_mesh.py, so face/skin/eyes/hair stay byte-identical.
#  - Taubin smoothing (no shrink) removes the MARBLE blotches and banding from both garment shells
#  - shorts: one subdivide; leg hems snapped to clean planar edge loops; a 2 cm turned hem band (slight roll + stitch
#    groove); gentle vertical drape on the leg panels only
#  - rash guard: no horizontal wrinkle bands; flank seams kept; a new snug mock/crew collar band covers the shoulders
#    from the old flat 1.50 m cut up to the base of the neck, with a rolled top edge. It follows the body surface at
#    +4.5 mm and its vertices take skin weights from the nearest body (or shirt) vertex
import bpy,bmesh,sys,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
inp,outp=sys.argv[-2],sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=inp)
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE'); rig.data.pose_position='REST'
def bone(n): return rig.matrix_world@rig.data.bones['mixamorig:'+n].head_local
body=bpy.data.objects['Human_export']; sh=bpy.data.objects['Shorts']; rg=bpy.data.objects['RashGuard']
def W(o): return o.matrix_world
def world_bm(o):
    bm=bmesh.new(); bm.from_mesh(o.data); bm.transform(W(o)); bm.verts.ensure_lookup_table(); return bm
def kd_of(bm):
    kd=KDTree(len(bm.verts)); [kd.insert(v.co,i) for i,v in enumerate(bm.verts)]; kd.balance(); return kd
def taubin(o,it,lam=0.55,mu=-0.58):
    bm=bmesh.new(); bm.from_mesh(o.data)
    pin={v for v in bm.verts if v.is_boundary}
    for i in range(it):
        for f in (lam,mu):
            new={v:sum((e.other_vert(v).co for e in v.link_edges),Vector())/len(v.link_edges) for v in bm.verts if v not in pin and v.link_edges}
            for v,c in new.items(): v.co=v.co+(c-v.co)*f
    bm.to_mesh(o.data); bm.free(); o.data.update()
def subdiv(o):
    bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active=o; o.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=1e-5)
    bpy.ops.mesh.subdivide(number_cuts=1,smoothness=1.0); bpy.ops.object.mode_set(mode='OBJECT')

# ---------------- SHORTS ----------------
subdiv(sh); taubin(sh,int(sys.argv[-3]) if sys.argv[-3].isdigit() else 80)
# offset-field smoothing: the MARBLE blobs are low-frequency bulges Taubin keeps; smooth the garment's distance-to-body
# field over the mesh and move every vertex along the body normal to the smoothed distance (silhouette kept, blobs gone)
def offset_smooth(o,it):
    bb=world_bm(body); bvh=BVHTree.FromBMesh(bb)
    bm=bmesh.new(); bm.from_mesh(o.data); bm.transform(W(o)); bm.verts.ensure_lookup_table()
    D={};N={}
    for v in bm.verts:
        loc,n,i,dist=bvh.find_nearest(v.co)
        if loc is None: continue
        d=(v.co-loc).dot(n)
        if abs(d)<0.05: D[v]=d; N[v]=n
    S=dict(D)
    for k in range(it):
        S={v:0.5*S[v]+0.5*sum(S.get(e.other_vert(v),S[v]) for e in v.link_edges)/max(1,len(v.link_edges)) for v in S}
    NS_=dict(N)
    for k in range(40):
        NS_={v:(NS_[v]+sum((NS_.get(e.other_vert(v),NS_[v]) for e in v.link_edges),Vector())).normalized() for v in NS_}
    for v in S: v.co=v.co+NS_[v]*(S[v]-D[v])
    bm.transform(W(o).inverted()); bm.to_mesh(o.data); bm.free(); o.data.update()
offset_smooth(sh,120); taubin(sh,30)
bm=world_bm(sh)
SZ1=max(v.co.z for v in bm.verts)
for s,sg in (('Left',1),('Right',-1)):
    a,b=bone(s+'UpLeg'),bone(s+'Leg'); ax=(b-a).normalized()
    vs=[v for v in bm.verts if v.co.x*sg>0.02 and v.co.z<0.80]
    tmax=max((v.co-a).dot(ax) for v in vs); th=tmax-0.010     # hem plane 1 cm above the lowest ragged point
    c=a+ax*th
    for v in vs:
        t=(v.co-a).dot(ax); r=v.co-a-ax*t
        if t>th: v.co=a+ax*th+r                                # snap everything below to the hem plane
        u=th-min(t,th)                                         # distance above hem
        # turned hem band: 2 cm band rolled out 0.8 mm, stitch groove at 2 cm
        if r.length>1e-6:
            n=r.normalized()
            d=0.0008*(1 if u<0.02 else 0)+(-0.0010*math.exp(-((u-0.02)/0.002)**2))+0.0006*math.exp(-(u/0.002)**2)
            if u>0.001 or t<th: v.co=v.co+n*d
    # gentle vertical drape creases on the leg panel (no horizontal waves)
    for v in vs: pass
for v in bm.verts:
    p=v.co; sg=1 if p.x>0 else -1; s='Left' if sg>0 else 'Right'
    a,b=bone(s+'UpLeg'),bone(s+'Leg'); ax=(b-a).normalized(); t=(p-a).dot(ax); r=p-a-ax*t
    if r.length<1e-6 or p.z>SZ1-0.10: continue
    q=p-a-ax*t; th_=math.atan2(q.y,q.x); hang=max(0,min(1,(SZ1-0.10-p.z)/0.15))*max(0,min(1,(p.z-0.73)/0.03))
    v.co=p+r.normalized()*hang*0.0035*max(0,math.sin(th_*4+0.8*sg))**4
bm.transform(W(sh).inverted()); bm.to_mesh(sh.data); bm.free(); sh.data.update()

# ---------------- RASH GUARD ----------------
taubin(rg,40)
bbm=world_bm(body); rbm=world_bm(rg)
bvh_b=BVHTree.FromBMesh(bbm); bvh_r=BVHTree.FromBMesh(rbm); kd_b=kd_of(bbm); kd_r=kd_of(rbm)
dl_b=bbm.verts.layers.deform.active; dl_r=rbm.verts.layers.deform.active
nk=bone('Neck'); C=Vector((nk.x,nk.y,0)); ZC=nk.z+0.017; ZTOP=ZC+0.025   # collar top 2.5 cm above the neck root
NA=128; NS=16
def down(xy,z0):
    o=Vector((xy.x,xy.y,z0)); hb=bvh_b.ray_cast(o,Vector((0,0,-1)),0.4); hr=bvh_r.ray_cast(o,Vector((0,0,-1)),0.4)
    if hr[0] is not None and (hb[0] is None or hr[3]<hb[3]+0.004): return hr[0],hr[1],'r'
    return hb[0],hb[1],'b'
grid=[]
for i in range(NA):
    th=2*math.pi*i/NA; d=Vector((math.cos(th),math.sin(th),0))
    ZTOP=ZC-0.007+0.028*math.sin(th)      # crew line: low at the front (+y is back), higher at the nape
    h=bvh_b.ray_cast(Vector((C.x,C.y,ZTOP)),d,0.2); rn=((h[0]-Vector((C.x,C.y,ZTOP))).length if h[0] else 0.06)
    # march outward until the down-ray lands on the shirt, then 1.5 cm more (overlap onto the shirt)
    r=rn+0.004; rend=None; ov=0
    while r<rn+0.25:
        p,n,src=down(C+d*r,ZTOP+0.003)
        if p is None: break
        if src=='r':
            ov+=0.003
            if ov>=0.035: rend=r; break
        r+=0.003
    if rend is None: rend=r
    col=[]
    # ring 0: on the neck at ZTOP; ring 1 at ZC; rings 2..: down-rays at radii rn..rend
    for k in range(NS):
        if k==0: p=Vector((C.x,C.y,ZTOP))+d*(rn+0.0045); n=d; src='b'
        else:
            t=(k-1)/(NS-2); rr=rn+0.004+(rend-rn-0.004)*(t**1.3)
            p,n,src=down(C+d*rr,ZTOP+0.003)
            if p is None: p=col[-1][0]; n=d
            elif k>1 and p.z>col[-1][0].z-0.001: p=Vector((p.x,p.y,col[-1][0].z-0.001-0.0045))
            off=0.0045 if src=='b' else 0.0012
            if n.z<0: n=-n
            p=p+n*off
        col.append((p.copy(),src))
    grid.append(col)
# smooth every ring across angles in cylindrical coords (kills spikes where rays hit chin / missed the shirt edge)
for k in range(NS):
    R=[];Z=[]
    for i in range(NA):
        p=grid[i][k][0]; R.append(math.hypot(p.x-C.x,p.y-C.y)); Z.append(p.z)
    for it in range(6):
        R=[sorted(R[(i+o)%NA] for o in range(-3,4))[3] for i in range(NA)]   # median
        Z=[sorted(Z[(i+o)%NA] for o in range(-3,4))[3] for i in range(NA)]
    for it in range(4):
        R=[(R[i-1]+2*R[i]+R[(i+1)%NA])/4 for i in range(NA)]; Z=[(Z[i-1]+2*Z[i]+Z[(i+1)%NA])/4 for i in range(NA)]
    for i in range(NA):
        th=2*math.pi*i/NA; grid[i][k]=(Vector((C.x+R[i]*math.cos(th),C.y+R[i]*math.sin(th),Z[i])),grid[i][k][1])
# keep rings monotonic downward
for i in range(NA):
    for k in range(2,NS):
        p,s_=grid[i][k]
        if p.z>grid[i][k-1][0].z-0.0008: grid[i][k]=(Vector((p.x,p.y,grid[i][k-1][0].z-0.0008)),s_)
# rolled top edge: over the top (+3 mm) and 1 cm down on the inside
cbm=bmesh.new(); dl=cbm.verts.layers.deform.verify()
def setw(v,src):
    if src=='b': co,idx,dd=kd_b.find(v.co); w=bbm.verts[idx][dl_b]
    else: co,idx,dd=kd_r.find(v.co); w=rbm.verts[idx][dl_r]
    for k_,x in w.items(): v[dl][k_]=x
V=[]
for i,col in enumerate(grid):
    th=2*math.pi*i/NA; d=Vector((math.cos(th),math.sin(th),0))
    top=col[0][0]; extra=[(top+Vector((0,0,-0.010))-d*0.0035,'b'),(top+Vector((0,0,0.0025))-d*0.0018,'b')]
    pts=list(reversed(extra))+col          # inner fold -> roll top -> outside ... -> overlap on shirt
    pts=[extra[0],extra[1]]+col
    row=[]
    for p,src in pts:
        v=cbm.verts.new(p); setw(v,'b' if src=='b' else 'r'); row.append(v)
    V.append(row)
cbm.verts.ensure_lookup_table()
M=len(V[0])
for i in range(NA):
    j=(i+1)%NA
    for k in range(M-1):
        try: cbm.faces.new((V[i][k],V[i][k+1],V[j][k+1],V[j][k]))
        except ValueError: pass
# smooth the band (keep the rolled edge and the last overlap ring)
for it in range(3):
    new={}
    for row in V:
        for k in range(3,M-1):
            v=row[k]; new[v]=sum((e.other_vert(v).co for e in v.link_edges),Vector())/len(v.link_edges)
    for v,c in new.items(): v.co=v.co.lerp(c,0.35)
cbm.normal_update()
# orient outward
out=sum(((f.calc_center_median()-Vector((C.x,C.y,f.calc_center_median().z))).normalized().dot(f.normal) for f in cbm.faces))
if out<0: bmesh.ops.reverse_faces(cbm,faces=cbm.faces)
# UVs: continue the fabric (tiling is done in the material) - simple cylindrical mapping
uvl=cbm.loops.layers.uv.verify()
for f in cbm.faces:
    for l in f.loops:
        p=l.vert.co; l[uvl].uv=((math.atan2(p.y-C.y,p.x-C.x)/(2*math.pi))*0.35, p.z*0.6)
print('collar verts',len(cbm.verts),'faces',len(cbm.faces))
me=bpy.data.meshes.new('Collar'); cbm.to_mesh(me)
col_o=bpy.data.objects.new('Collar',me); bpy.context.collection.objects.link(col_o)
for g in rg.vertex_groups: col_o.vertex_groups.new(name=g.name)
# deform layer keys map to vertex group indices; rg and body share the same group order (checked below)
assert [g.name for g in rg.vertex_groups]==[g.name for g in body.vertex_groups]
col_o.data.materials.append(rg.data.materials[0])
# join collar into the rash guard (rash guard is in world space after import? apply transforms to be safe)
col_o.matrix_world=W(rg).inverted()@col_o.matrix_world if False else col_o.matrix_world
bm2=bmesh.new(); bm2.from_mesh(me); bm2.transform(W(rg).inverted()); bm2.to_mesh(me); bm2.free(); col_o.matrix_world=W(rg)
bpy.ops.object.select_all(action='DESELECT'); col_o.select_set(True); rg.select_set(True); bpy.context.view_layer.objects.active=rg
bpy.ops.object.join()
mod=rg.modifiers.new('arm','ARMATURE') if not any(m.type=='ARMATURE' for m in rg.modifiers) else None
for o in (sh,rg):
    print(o.name,'verts',len(o.data.vertices),'tris',sum(len(f.vertices)-2 for f in o.data.polygons))
for o in list(bpy.data.objects):
    if o.type=='MESH' and o not in (sh,rg): bpy.data.objects.remove(o)
for a in list(bpy.data.actions): bpy.data.actions.remove(a)
bpy.ops.export_scene.gltf(filepath=outp,export_format='GLB',export_animations=False)
