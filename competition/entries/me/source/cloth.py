import bpy,bmesh,sys,math
from mathutils import Vector
inp,outp=sys.argv[-2],sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=inp)
for o in list(bpy.data.objects):
    if o.name.startswith('Icosphere'): bpy.data.objects.remove(o)
fab=bpy.data.materials['TrainingFabric']
def set_map(m,scale,rot=0):
    for n in m.node_tree.nodes:
        if n.type=='MAPPING':
            n.inputs['Scale'].default_value=(scale,scale,1); n.inputs['Location'].default_value=(0,0,0); n.inputs['Rotation'].default_value=(0,0,rot)
def tint(m,c,rough=None):
    b=m.node_tree.nodes['Principled Bsdf'] if 'Principled Bsdf' in m.node_tree.nodes else [n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'][0]
    # baseColor texture feeds Base Color; insert multiply via exporter-understood factor: use a Mix(MULTIPLY) node
    tex=b.inputs['Base Color'].links[0].from_node if b.inputs['Base Color'].links else None
    if tex:
        mix=m.node_tree.nodes.new('ShaderNodeMix'); mix.data_type='RGBA'; mix.blend_type='MULTIPLY'; mix.inputs[0].default_value=1
        m.node_tree.links.new(tex.outputs['Color'],mix.inputs[6]); mix.inputs[7].default_value=(*c,1)
        m.node_tree.links.new(mix.outputs[2],b.inputs['Base Color'])
set_map(fab,30)
shorts_m=fab.copy(); shorts_m.name='ShortsFabric'; tint(shorts_m,(0.45,0.47,0.55))
rib=fab.copy(); rib.name='RibTrim'; set_map(rib,70,math.pi/2); tint(rib,(0.6,0.6,0.6))
def loops(bm):
    bnd={e for e in bm.edges if e.is_boundary}; seen=set(); out=[]
    for e in bnd:
        if e in seen: continue
        stack=[e]; comp=set()
        while stack:
            x=stack.pop()
            if x in comp: continue
            comp.add(x)
            for v in x.verts:
                for y in v.link_edges:
                    if y in bnd and y not in comp: stack.append(y)
        seen|=comp; out.append(comp)
    return out
def process(name, mat, trims, collar=False, SMOOTH=4, INFL=0.003):
    o=bpy.data.objects[name]; me=o.data
    o.data.materials.append(rib); ri=len(o.data.materials)-1
    if mat is not None: o.data.materials[0]=mat
    bm=bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    dl=bm.verts.layers.deform.verify()
    MW=o.matrix_world.copy(); bmesh.ops.transform(bm,matrix=MW,verts=bm.verts)
    print(name,'MW',[list(r) for r in MW])
    L=loops(bm)
    info=[(len(l), sum((v.co for e in l for v in e.verts),Vector())/ (2*len(l))) for l in L]
    print(name,'loops',[(n,round(c.z,3)) for n,c in info])
    # smooth jagged boundaries
    for it in range(6):
        for l in L:
            vs={v for e in l for v in e.verts}; new={}
            for v in vs:
                nb=[e.other_vert(v) for e in v.link_edges if e in l]
                if len(nb)==2: new[v]=v.co*0.5+(nb[0].co+nb[1].co)*0.25
            for v,c in new.items(): v.co=c
    if collar:
        from mathutils.bvhtree import BVHTree
        from mathutils.kdtree import KDTree
        body=bpy.data.objects['Body']; bbm=bmesh.new(); bbm.from_mesh(body.data); bbm.verts.ensure_lookup_table()
        bvh=BVHTree.FromBMesh(bbm)
        hbm=bmesh.new(); hbm.from_mesh(bpy.data.objects['OwnerHead'].data); hbm.transform(bpy.data.objects['OwnerHead'].matrix_world); hvh=BVHTree.FromBMesh(hbm)
        hverts=[v.co.copy() for v in hbm.verts if v.co.z<1.6]
        slab=[v.co.copy() for v in bbm.verts if 1.512<v.co.z<1.535]
        nc=sum(slab,Vector())/len(slab)
        def rb(dx,dy):
            ang=math.atan2(dy,dx); best=[ (q.xy-nc.xy).length for q in slab if abs(((math.atan2(q.y-nc.y,q.x-nc.x)-ang+math.pi)%(2*math.pi))-math.pi)<0.35]
            return (sum(best)/len(best)) if best else 0.07
        bkd=KDTree(len(bbm.verts))
        for v in bbm.verts: bkd.insert(v.co,v.index)
        bkd.balance()
        bdl=bbm.verts.layers.deform.active
        gmap={g.index:g.name for g in body.vertex_groups}; omap={g.name:g.index for g in o.vertex_groups}
        neck=[e for e in bm.edges if e.is_boundary and all(v.co.z>1.29 and abs(v.co.x)<0.27 for v in e.verts)]
        orig={}
        for v in {v for e in neck for v in e.verts}:
            d=v.co.xy-nc.xy; d=d/max(d.length,1e-6); r=rb(d.x,d.y)+0.007
            orig[v]=(v.co.copy(), Vector((nc.x+d.x*r, nc.y+d.y*r, max(v.co.z+0.01, 1.524))))
        edges=neck; prev={v:v for v in orig}
        newverts=[]
        N=6
        for ring in range(1,N+1):
            r=bmesh.ops.extrude_edge_only(bm,edges=edges)
            nv=[g for g in r['geom'] if isinstance(g,bmesh.types.BMVert)]
            # map new verts to their source: nearest prev boundary vert
            for v in nv:
                src=min(prev.values(),key=lambda p:(p.co-v.co).length) if False else None
            edges=[g for g in r['geom'] if isinstance(g,bmesh.types.BMEdge) and all(x in nv for x in g.verts)]
            # each new vert sits exactly on its parent; find parent by position
            pos={tuple(round(c,6) for c in p.co):k for k,p in prev.items()}
            newprev={}
            for v in nv:
                k=pos.get(tuple(round(c,6) for c in v.co))
                if k is None: continue
                p0,p1=orig[k]; t=ring/N; t=1-(1-t)**1.6
                q=p0.lerp(p1,t)
                loc,nrm,idx,dist=bvh.find_nearest(q)
                if loc is not None and ((q-loc).dot(nrm)<0.006): q=loc+nrm*0.006
                dq=q.xy-nc.xy; ang=math.atan2(dq.y,dq.x)
                hr=[ (hv.xy-nc.xy).length for hv in hverts if abs(hv.z-q.z)<0.012 and abs(((math.atan2(hv.y-nc.y,hv.x-nc.x)-ang+math.pi)%(2*math.pi))-math.pi)<0.2]
                if hr and dq.length<max(hr)+0.005: q.xy=nc.xy+dq.normalized()*(max(hr)+0.005)
                v.co=q; newprev[k]=v; newverts.append(v)
            prev=newprev
            for f in [g for g in r['geom'] if isinstance(g,bmesh.types.BMFace)]: f.material_index=ri; f.smooth=True
        for v in newverts:
            _,bi,_=bkd.find(v.co); src=bbm.verts[bi][bdl]; dst=v[dl]; dst.clear()
            for gi,w in src.items():
                n=gmap[gi]
                if n in omap: dst[omap[n]]=w
        print('collar verts',len(newverts),'neck center',nc)
    bm.normal_update()
    inner=[v for v in bm.verts if not v.is_boundary]
    for it in range(SMOOTH):
        bmesh.ops.smooth_vert(bm,verts=inner,factor=0.5,use_axis_x=True,use_axis_y=True,use_axis_z=True)
    bm.normal_update()
    for v in inner: v.co+=v.normal*INFL
    bm.normal_update()
    # trims: faces within dist of boundary (geodesic approx by BFS over verts with euclid)
    bnd=[v for v in bm.verts if v.is_boundary]
    from mathutils.kdtree import KDTree
    kd=KDTree(len(bnd))
    for i,v in enumerate(bnd): kd.insert(v.co,i)
    kd.balance()
    for f in bm.faces:
        c=f.calc_center_median(); _,_,d=kd.find(c)
        w=trims(c,d)
        if w: f.material_index=ri
    bmesh.ops.transform(bm,matrix=MW.inverted(),verts=bm.verts); bm.normal_update()
    bm.to_mesh(me); bm.free(); me.update()
process('RashGuard',None,lambda c,d:d<0.022,collar=False)
process('Shorts',shorts_m,lambda c,d:d<0.02)
bpy.ops.export_scene.gltf(filepath=outp,export_format='GLB',export_animation_mode='ACTIONS',export_force_sampling=False,export_def_bones=False)
