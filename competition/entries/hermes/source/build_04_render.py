"""
Hermes fighter — stage 4: beauty renders FROM the submitted fighter.glb.

Loads competition/entries/hermes/fighter.glb (the exact submitted file), lights it
with the judge's HDRI (basement_boxing_ring_2k.hdr) plus one key light, poses it in
fighting_idle, and renders the 4 required angles at >=1920px. Rendered FROM the GLB,
no paint-overs, no compositing, no AI image gen (RULES.md section 3 / penalties).

Run: Blender --background --python build_04_render.py
"""
import bpy, os, math
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
GLB = os.path.abspath(os.path.join(HERE, "..", "fighter.glb"))
HDRI = os.path.join(PROJECT, "assets", "polyhaven", "hdri", "basement_boxing_ring_2k.hdr")
RENDERS = os.path.abspath(os.path.join(HERE, "..", "renders"))
os.makedirs(RENDERS, exist_ok=True)

def log(*a): print("RENDER:", *a)

def setup_world():
    w = bpy.data.worlds.new("W"); bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    bg = nt.nodes.new("ShaderNodeBackground")
    out = nt.nodes.new("ShaderNodeOutputWorld")
    if os.path.exists(HDRI):
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(HDRI)
        nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=GLB)
    log("imported", GLB)

    # Pose into fighting_idle mid-clip.
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    if arm.animation_data and arm.animation_data.nla_tracks:
        for t in arm.animation_data.nla_tracks:
            if t.name == 'fighting_idle':
                for s in t.strips: s.mute = False
            else:
                for s in t.strips: s.mute = True
    bpy.context.scene.frame_set(30)

    # Compute character bounds for framing.
    deps = bpy.context.evaluated_depsgraph_get()
    mn = Vector((1e9,1e9,1e9)); mx = Vector((-1e9,-1e9,-1e9))
    for o in bpy.data.objects:
        if o.type == 'MESH':
            ev = o.evaluated_get(deps)
            for v in ev.bound_box:
                wv = o.matrix_world @ Vector(v)
                mn = Vector(map(min, mn, wv)); mx = Vector(map(max, mx, wv))
    center = (mn + mx) * 0.5
    height = mx.z - mn.z if (mx.z-mn.z) > (mx.y-mn.y) else mx.y - mn.y
    log("bounds", [round(v,2) for v in mn], [round(v,2) for v in mx])

    setup_world()
    # Key light
    key = bpy.data.lights.new("Key", 'AREA'); key.energy = 600; key.size = 2.0
    ko = bpy.data.objects.new("Key", key); bpy.context.collection.objects.link(ko)
    ko.location = center + Vector((2.0, -2.5, 2.2))
    ko.rotation_euler = (math.radians(55), 0, math.radians(40))

    # Camera
    cam = bpy.data.cameras.new("Cam"); cam.lens = 70
    co = bpy.data.objects.new("Cam", cam); bpy.context.collection.objects.link(co)
    bpy.context.scene.camera = co

    scene = bpy.context.scene
    # EEVEE Next: fast real-time PBR, and it matches the judge's Three.js arena
    # (real-time raster), so these renders honestly represent what ships.
    try:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
    except Exception:
        scene.render.engine = 'BLENDER_EEVEE'
    try:
        scene.eevee.taa_render_samples = 64
        scene.eevee.use_raytracing = True
    except Exception as e:
        log("eevee opts", e)
    try: scene.view_settings.view_transform = 'Standard'
    except Exception: pass
    scene.render.image_settings.file_format = 'PNG'
    scene.render.resolution_x = 2048
    scene.render.resolution_y = 2048
    scene.render.film_transparent = False

    def point_cam(pos):
        co.location = pos
        d = (center - Vector(pos)); 
        co.rotation_euler = d.to_track_quat('-Z','Y').to_euler()

    H = max(height, 1.7)
    # Full-body shots at ~mid height, head close-up higher.
    head_z = mx.z if (mx.z-mn.z) > (mx.y-mn.y) else mx.y
    head = Vector((center.x, center.y, head_z - 0.12)) if (mx.z-mn.z) > (mx.y-mn.y) else Vector((center.x, head_z-0.12, center.z))

    shots = {
        'front':         center + Vector((0, -3.2, 0.0)),
        'three_quarter': center + Vector((2.4, -2.6, 0.2)),
        'profile':       center + Vector((3.2, 0.0, 0.1)),
    }
    for name, pos in shots.items():
        point_cam(pos)
        scene.render.resolution_x = 2048; scene.render.resolution_y = 2732
        scene.render.filepath = os.path.join(RENDERS, f"{name}.png")
        bpy.ops.render.render(write_still=True)
        log("wrote", name)

    # Close-up on the head/face.
    co.data.lens = 120
    point_cam(head + Vector((0.15, -0.9, 0.0)))
    scene.render.resolution_x = 2048; scene.render.resolution_y = 2048
    scene.render.filepath = os.path.join(RENDERS, "closeup.png")
    bpy.ops.render.render(write_still=True)
    log("wrote closeup")

main()
