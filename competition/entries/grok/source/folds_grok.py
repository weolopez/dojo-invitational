# Grok v3.4 garments: keeps the original rash guard and shorts, subdivides the shorts once, and sculpts procedural
# folds and seam lines into both (radial displacement from the nearest bone axis). Exports a GLB whose garment
# meshes are spliced into the untouched original fighter.glb by splice_mesh.py.
import bpy,sys,math,os
from mathutils import Vector
from mathutils.geometry import intersect_point_line
inp,outp=sys.argv[-2],sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=inp)
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE'); rig.data.pose_position='REST'
def bone(n): return rig.matrix_world@rig.data.bones['mixamorig:'+n].head_local
def tail(n): return rig.matrix_world@rig.data.bones['mixamorig:'+n].tail_local
SEGS=[(bone('Hips'),bone('Spine')),(bone('Spine'),bone('Spine2')),(bone('Spine2'),bone('Neck'))]
for s in ('Left','Right'):
    SEGS+=[(bone(s+'Arm'),bone(s+'ForeArm')),(bone(s+'UpLeg'),bone(s+'Leg')),(bone(s+'Shoulder'),bone(s+'Arm'))]
def radial(p):
    best=None
    for a,b in SEGS:
        q,t=intersect_point_line(p,a,b); t=max(0,min(1,t)); q=a+(b-a)*t; d=(p-q).length
        if best is None or d<best[0]: best=(d,q)
    v=p-best[1]; return v.normalized() if v.length>1e-6 else Vector((0,0,1))
def g(x,s): return math.exp(-(x/s)**2)
fwd=Vector((0,-1,0))
def around(p,a,b):
    dr=(b-a).normalized(); q=p-a; t=q.dot(dr); r=q-dr*t
    ref=fwd-dr*fwd.dot(dr); ref.normalize(); oth=dr.cross(ref)
    return t,math.atan2(r.dot(oth),r.dot(ref)),r.length
LEGS={sg:(bone(s+'UpLeg'),bone(s+'Leg')) for s,sg in (('Left',1),('Right',-1))}
ARMS={sg:(bone(s+'Arm'),bone(s+'ForeArm')) for s,sg in (('Left',1),('Right',-1))}
sh=bpy.data.objects['Shorts']; rg=bpy.data.objects['RashGuard']
def zr(o):
    zs=[(o.matrix_world@v.co).z for v in o.data.vertices]; return min(zs),max(zs)
SZ0,SZ1=zr(sh); RZ0,RZ1=zr(rg); print('shorts z',SZ0,SZ1,'rash z',RZ0,RZ1)
def seam(dist,w=0.0035): return g(dist,w)
def shorts_d(p):
    sg=1 if p.x>0 else -1; a,b=LEGS[sg]; t,th,r=around(p,a,b)
    hang=max(0,min(1,(SZ1-0.06-p.z)/0.18))
    d=0.006*hang                                          # leg panels hang slightly away from the thigh
    cre=max(0,math.sin(th*5+t*9*sg+1.3*sg))**6            # vertical drape creases
    d+=0.008*hang*cre*(0.6+0.4*math.sin(th*2+0.7))
    # crotch drag folds (front, diagonal from crotch to hip)
    if p.y<0 and p.z<SZ1-0.08:
        u=(abs(p.x)*1.0+(SZ1-p.z)*0.8); d+=0.0035*max(0,math.sin(u*55))**4*g(abs(p.x)-0.06,0.07)*hang
    # waistband: gathers in the top 4 cm and a stitch groove below it
    wb=max(0,min(1,(p.z-(SZ1-0.045))/0.01)); ang=math.atan2(p.y,p.x)
    d+=wb*(0.0025+0.0015*(0.5+0.5*math.sin(ang*70)))
    d-=0.0018*seam(p.z-(SZ1-0.05),0.003)
    # side seams and inseam
    d-=0.0012*seam(abs(th)-math.pi/2 if sg>0 else abs(abs(th)-math.pi/2),0.06)*hang if False else 0
    side=abs(abs(math.atan2(p.y,abs(p.x)))-0.0)                        # outer side: y≈0, |x| large
    if abs(p.x)>0.12: d-=0.0012*g(p.y-0.0,0.004)*min(1,(abs(p.x)-0.12)/0.03)
    if abs(p.x)<0.1 and p.z<SZ1-0.12: d-=0.0010*g(p.y-0.0,0.004)
    # hem stitch line 1.8 cm above the leg hem
    hz=SZ0+0.018+ (0 if True else 0); d-=0.0012*seam(p.z-(SZ0+0.02),0.003)
    return d
def rash_d(p):
    d=0.0
    for sg,(a,b) in ARMS.items():
        if p.x*sg>0.16:
            t,th,r=around(p,a,b); under=0.5-0.5*math.cos(th)
            d+=0.0026*max(0,math.sin(t*95+th))**4*under          # underarm bunching
            d-=0.0011*seam(t-0.015,0.004)                        # set-in sleeve seam ring
    # side seams (y≈ mid-depth of torso at the flank) and shoulder seams (top of shoulder)
    if abs(p.x)<0.2 and p.z<RZ1-0.08:
        flank=min(1,max(0,(abs(p.x)-0.11)/0.04)); d-=0.0011*g(p.y-0.01,0.005)*flank
    if p.z>RZ1-0.12 and 0.07<abs(p.x)<0.19: d-=0.0010*g(p.y-0.0,0.005)
    # horizontal compression wrinkles above the waistband, strongest at the flanks and the low back
    z=p.z-SZ1
    if -0.02<z<0.16:
        flank=min(1,(abs(p.x)/0.15)**3)+ (0.6 if p.y>0.03 else 0)
        d+=0.003*g(z-0.05,0.06)*min(1,flank)*max(0,math.sin(z*85+abs(p.x)*30))**4
    # diagonal pull folds from the armpits toward the sternum
    if p.y<0 and 1.25<p.z<1.42 and abs(p.x)<0.17:
        u=abs(p.x)*0.8+(1.45-p.z); d+=0.0016*max(0,math.sin(u*60))**4*g(abs(p.x)-0.13,0.04)
    return d
def apply_disp(o,fn,subdiv,smooth=0):
    bpy.ops.object.select_all(action='DESELECT')
    if subdiv:
        bpy.context.view_layer.objects.active=o; o.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.subdivide(number_cuts=1,smoothness=1.0); bpy.ops.object.mode_set(mode='OBJECT')
    mw=o.matrix_world; inv=mw.inverted_safe().to_3x3()
    if smooth:
        import bmesh
        bm=bmesh.new(); bm.from_mesh(o.data); bm.normal_update()
        pin={v for v in bm.verts if v.is_boundary}
        c0=sum((v.co for v in bm.verts),Vector())/len(bm.verts)
        orig={v:v.co.copy() for v in bm.verts}
        for it in range(smooth):
            new={v:sum((e.other_vert(v).co for e in v.link_edges),Vector())/len(v.link_edges) for v in bm.verts if v not in pin and v.link_edges}
            for v,c in new.items(): v.co=v.co.lerp(c,0.6)
        bm.normal_update()
        # restore the original offset from the body: move each vertex back out along its normal by its own shrink
        for v in bm.verts:
            if v in pin: continue
            sh_=(orig[v]-v.co).dot(v.normal); v.co+=v.normal*sh_
        for it in range(3):
            new={v:sum((e.other_vert(v).co for e in v.link_edges),Vector())/len(v.link_edges) for v in bm.verts if v not in pin and v.link_edges}
            for v,c in new.items(): v.co=v.co.lerp(c,0.5)
        bm.to_mesh(o.data); bm.free()
    for v in o.data.vertices:
        p=mw@v.co; v.co=v.co+inv@(radial(p)*fn(p))
    o.data.update(); print(o.name,'verts',len(o.data.vertices),'tris',sum(len(f.vertices)-2 for f in o.data.polygons))
apply_disp(sh,shorts_d,1,int(os.environ.get('SMS','40')))
apply_disp(rg,rash_d,0)
for o in list(bpy.data.objects):
    if o.type=='MESH' and o not in (sh,rg): bpy.data.objects.remove(o)
for a in list(bpy.data.actions): bpy.data.actions.remove(a)
bpy.ops.export_scene.gltf(filepath=outp,export_format='GLB',export_animations=False,export_image_format='NONE' if False else 'AUTO')
