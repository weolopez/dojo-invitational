import bpy, sys, os, struct

# Probe: can we import a Mixamo FBX, read its skeleton + clip, and what does the
# existing reference hermes.glb give us as a base? Headless sanity for the pipeline.

def log(*a): print("PROBE:", *a)

# 1. Texture dims (fixing the earlier quoting bug, done natively here)
for p in ["assets/textures/skin_pore_normal.png","assets/textures/dojo_mat_albedo.png","assets/textures/shirt_plaid_albedo.png"]:
    fp = os.path.join(os.getcwd(), p)
    if os.path.exists(fp):
        b=open(fp,'rb').read()
        if b[:2]==b'\x89P':
            w,h=struct.unpack_from('>II',b,16); log("tex",p,w,"x",h)

# 2. Import one Mixamo FBX and report skeleton + animation
bpy.ops.wm.read_factory_settings(use_empty=True)
fbx = os.path.join(os.getcwd(),"assets/mixamo/fighting_idle.fbx")
log("importing", fbx, "exists=", os.path.exists(fbx))
try:
    bpy.ops.import_scene.fbx(filepath=fbx)
    arms=[o for o in bpy.data.objects if o.type=='ARMATURE']
    log("armatures:", [a.name for a in arms])
    if arms:
        bones=[b.name for b in arms[0].data.bones]
        mix=[b for b in bones if b.startswith('mixamorig')]
        log("total bones", len(bones), "mixamorig bones", len(mix))
        log("sample bones", bones[:8])
    acts=[a.name for a in bpy.data.actions]
    log("actions:", acts)
    if bpy.data.actions:
        a=bpy.data.actions[0]
        log("action0 frame_range", tuple(a.frame_range))
    meshes=[o for o in bpy.data.objects if o.type=='MESH']
    log("meshes in fbx:", [(m.name, len(m.data.vertices)) for m in meshes])
except Exception as e:
    log("FBX import FAILED:", repr(e))

# 3. Can we import the existing reference GLB (to reuse its rig+clips+base mesh)?
bpy.ops.wm.read_factory_settings(use_empty=True)
glb=os.path.join(os.getcwd(),"dojo/public/fighters/hermes.glb")
try:
    bpy.ops.import_scene.gltf(filepath=glb)
    log("GLB imported OK")
    log("objects:", [(o.name,o.type) for o in bpy.data.objects][:12])
    log("actions in glb:", len(bpy.data.actions))
    meshes=[o for o in bpy.data.objects if o.type=='MESH']
    for m in meshes:
        log("mesh", m.name, "verts", len(m.data.vertices), "mats", [ms.name for ms in m.data.materials])
except Exception as e:
    log("GLB import FAILED:", repr(e))

log("ADDONS gltf exporter present:", hasattr(bpy.ops.export_scene,'gltf'))
