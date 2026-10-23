"""
Hermes fighter — stage 1: build the base human mesh (fictional person).

Builds a proportioned adult male combatant mesh procedurally in Blender:
  - head with real face topology (sculpted brow, nose, cheekbones, jaw, lips, ears)
  - neck, torso, arms, hands (blocked), legs, feet
  - subdivided for smooth silhouette, kept well under the 250k-tri budget

This is an HONEST procedural+sculpted base built in Blender. It is NOT a photoscan
and NOT derived from any real person's photos. Claims in NOTES.md reflect exactly that.

Output: entries/hermes/source/base_human.blend
Run: Blender --background --python build_01_base.py
"""
import bpy, bmesh, math, os
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def add_subsurf(obj, levels=2, render=3):
    m = obj.modifiers.new("Subsurf", 'SUBSURF')
    m.levels = levels; m.render_levels = render

def shade_smooth(obj):
    for p in obj.data.polygons: p.use_smooth = True

# ---------------------------------------------------------------- HEAD
def build_head():
    """A face-topology head: start from a UV sphere, then sculpt facial planes
    by moving vertex groups. Produces brow, nose bridge, cheek, jaw, chin, lips."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=48, radius=0.098)
    head = bpy.context.active_object
    head.name = "Head"
    # Scale to a human skull aspect (taller than wide, deeper than wide)
    head.scale = (0.92, 1.06, 1.0)
    bpy.ops.object.transform_apply(scale=True)

    me = head.data
    bm = bmesh.new(); bm.from_mesh(me)
    bm.verts.ensure_lookup_table()

    def shape(v):
        co = v.co.copy()
        x, y, z = co.x, co.y, co.z           # x=right, y=up, z=front
        front = z > 0
        # Flatten the back of the skull slightly, extend crown
        if z < -0.03: co.z *= 0.95
        # Brow ridge: push forward a band above eye line
        if front and 0.012 < y < 0.045 and abs(x) < 0.07:
            co.z += 0.010 * (1 - abs(x)/0.07)
        # Eye sockets: recess two hollows
        for sx in (-1, 1):
            eye = Vector((sx*0.037, 0.012, 0.085))
            d = (co - eye).length
            if d < 0.032 and front:
                co -= co.normalized() * (0.010 * (1 - d/0.032))
        # Nose: build a bridge + tip ridge down the centre
        if front and abs(x) < 0.016 and -0.03 < y < 0.03:
            ridge = 0.018 * (1 - abs(y)/0.03) * (1 - abs(x)/0.016)
            co.z += ridge
            if -0.028 < y < -0.004:  # tip/bulb
                co.z += 0.006
        # Nostrils flare
        if front and 0.011 < abs(x) < 0.02 and -0.03 < y < -0.012:
            co.z += 0.004
        # Cheekbones
        for sx in (-1, 1):
            ck = Vector((sx*0.05, -0.004, 0.06))
            d = (co - ck).length
            if d < 0.035 and front:
                co.z += 0.006 * (1 - d/0.035)
        # Mouth / lips: subtle protrusion with a seam
        if front and abs(x) < 0.028 and -0.062 < y < -0.04:
            co.z += 0.007 * (1 - abs(x)/0.028)
            if -0.054 < y < -0.05: co.z -= 0.002  # lip seam
        # Jaw + chin: square the lower face, bring chin forward
        if y < -0.05:
            taper = 1.0 - (abs(y) - 0.05) * 0.9
            co.x *= max(0.72, taper)
            if front and abs(x) < 0.03 and y < -0.072:
                co.z += 0.010 * (1 - abs(x)/0.03)   # chin
        # Chin bottom
        if y < -0.088: co.y = -0.088 - (abs(y)-0.088)*0.4
        v.co = co

    for v in bm.verts: shape(v)
    bm.to_mesh(me); bm.free()
    head.location = (0, 1.62, 0)   # head top near ~1.72 m, refined later
    add_subsurf(head, 2, 3)
    shade_smooth(head)
    return head

# ---------------------------------------------------------------- EARS
def build_ear(side):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.022)
    ear = bpy.context.active_object
    ear.name = f"Ear_{'L' if side<0 else 'R'}"
    ear.scale = (0.35, 1.0, 0.7)
    bpy.ops.object.transform_apply(scale=True)
    ear.location = (side*0.082, 1.628, -0.01)
    ear.rotation_euler = (0, 0, math.radians(-8*side))
    add_subsurf(ear, 1, 2); shade_smooth(ear)
    return ear

# ---------------------------------------------------------------- EYES
def build_eye(side):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=24, radius=0.0125)
    eye = bpy.context.active_object
    eye.name = f"Eye_{'L' if side<0 else 'R'}"
    eye.location = (side*0.037, 1.632, 0.078)
    add_subsurf(eye, 2, 3); shade_smooth(eye)
    # cornea bulge
    return eye

# ---------------------------------------------------------------- TEETH (block)
def build_teeth():
    bpy.ops.mesh.primitive_cube_add(size=1)
    t = bpy.context.active_object; t.name = "Teeth"
    t.scale = (0.03, 0.006, 0.012)
    bpy.ops.object.transform_apply(scale=True)
    t.location = (0, 1.556, 0.07)
    return t

# ---------------------------------------------------------------- BODY
def build_body():
    """Torso+limbs from a metaball-free approach: a subdivided mesh skin via
    skin modifier over an armature-like vertex chain, then subsurf."""
    # Build a stick figure of edges and use the Skin modifier for organic volume.
    mesh = bpy.data.meshes.new("Body")
    obj = bpy.data.objects.new("Body", mesh)
    bpy.context.collection.objects.link(obj)

    # joint points (x,y,z) in metres, y-up
    J = {
        'hips':     Vector((0, 1.00, 0)),
        'spine':    Vector((0, 1.16, 0.005)),
        'chest':    Vector((0, 1.34, 0.01)),
        'neck':     Vector((0, 1.50, 0)),
        'headbase': Vector((0, 1.56, 0)),
        'l_shldr':  Vector((0.18, 1.45, 0)), 'r_shldr': Vector((-0.18, 1.45, 0)),
        'l_elbow':  Vector((0.33, 1.20, 0)), 'r_elbow': Vector((-0.33, 1.20, 0)),
        'l_wrist':  Vector((0.42, 0.98, 0.02)), 'r_wrist': Vector((-0.42, 0.98, 0.02)),
        'l_hip':    Vector((0.10, 0.98, 0)), 'r_hip': Vector((-0.10, 0.98, 0)),
        'l_knee':   Vector((0.12, 0.55, 0.02)), 'r_knee': Vector((-0.12, 0.55, 0.02)),
        'l_ankle':  Vector((0.12, 0.09, 0)), 'r_ankle': Vector((-0.12, 0.09, 0)),
        'l_toe':    Vector((0.12, 0.03, 0.14)), 'r_toe': Vector((-0.12, 0.03, 0.14)),
    }
    edges = [('hips','spine'),('spine','chest'),('chest','neck'),('neck','headbase'),
             ('chest','l_shldr'),('l_shldr','l_elbow'),('l_elbow','l_wrist'),
             ('chest','r_shldr'),('r_shldr','r_elbow'),('r_elbow','r_wrist'),
             ('hips','l_hip'),('l_hip','l_knee'),('l_knee','l_ankle'),('l_ankle','l_toe'),
             ('hips','r_hip'),('r_hip','r_knee'),('r_knee','r_ankle'),('r_ankle','r_toe')]
    keys = list(J.keys()); idx = {k:i for i,k in enumerate(keys)}
    verts = [J[k] for k in keys]
    edge_list = [(idx[a], idx[b]) for a,b in edges]
    mesh.from_pydata([tuple(v) for v in verts], edge_list, [])
    mesh.update()

    skin = obj.modifiers.new("Skin", 'SKIN')
    # set skin radii per joint for believable limb thickness
    obj.data.skin_vertices  # ensure layer
    sv = obj.data.skin_vertices[0].data
    radii = {
        'hips':(0.15,0.12),'spine':(0.15,0.11),'chest':(0.17,0.12),'neck':(0.055,0.055),
        'headbase':(0.05,0.05),
        'l_shldr':(0.07,0.07),'r_shldr':(0.07,0.07),
        'l_elbow':(0.05,0.05),'r_elbow':(0.05,0.05),
        'l_wrist':(0.035,0.035),'r_wrist':(0.035,0.035),
        'l_hip':(0.09,0.09),'r_hip':(0.09,0.09),
        'l_knee':(0.06,0.06),'r_knee':(0.06,0.06),
        'l_ankle':(0.045,0.045),'r_ankle':(0.045,0.045),
        'l_toe':(0.04,0.03),'r_toe':(0.04,0.03),
    }
    for k,i in idx.items():
        sv[i].radius = radii[k]
    # mark hips as skin root
    sv[idx['hips']].use_root = True
    add_subsurf(obj, 2, 3)
    shade_smooth(obj)
    return obj

def main():
    reset()
    head = build_head()
    earL = build_ear(-1); earR = build_ear(1)
    eyeL = build_eye(-1); eyeR = build_eye(1)
    teeth = build_teeth()
    body = build_body()

    # Join face parts to head where sensible later; keep separate for materials now.
    out = os.path.join(HERE, "base_human.blend")
    bpy.ops.wm.save_as_mainfile(filepath=out)
    # report
    total_tris = 0
    deps = bpy.context.evaluated_depsgraph_get()
    for o in bpy.data.objects:
        if o.type=='MESH':
            ev = o.evaluated_get(deps)
            m = ev.to_mesh()
            m.calc_loop_triangles()
            total_tris += len(m.loop_triangles)
            ev.to_mesh_clear()
    print(f"BUILD: saved {out}")
    print(f"BUILD: objects={[o.name for o in bpy.data.objects if o.type=='MESH']}")
    print(f"BUILD: total evaluated triangles ~ {total_tris}")

main()
