"""Stage 4: export fighter.glb from .work/claude_rigged.blend, then render the required views FROM THAT GLB
in a clean scene (judge HDRI + one key light, EEVEE). Writes fighter.glb, renders/*.png, .work/previews/action_*.png.
"""
import math
import os

import bpy
from mathutils import Vector

ENTRY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ENTRY, ".work")
GLB = os.path.join(ENTRY, "fighter.glb")
HDRI = "/Users/weo/Development/3d/assets/polyhaven/hdri/basement_boxing_ring_2k.hdr"


def fit_clothes_weights(body_name="Human", cloth_name="Human.female_sportsuit01"):
    """Call #5: give the skin-tight sportsuit the skin's own bone weights. MPFB weights the suit with 17 coarse
    groups, so in big poses (the roundhouse) the top rode up into a crop top and the skin poked through the
    leggings at the hip and the top at the chest. Each suit vertex now takes the weights of the nearest point on the
    body surface (barycentric blend of that triangle's corners), so cloth and skin move together."""
    from mathutils.bvhtree import BVHTree
    from mathutils.geometry import barycentric_transform
    body, cloth = bpy.data.objects[body_name], bpy.data.objects[cloth_name]
    me = body.data
    me.calc_loop_triangles()
    gi = body.vertex_groups["body"].index
    on_body = {v.index for v in me.vertices if any(g.group == gi and g.weight > 0 for g in v.groups)}
    tris = [t.vertices[:] for t in me.loop_triangles if all(i in on_body for i in t.vertices)]
    co = [v.co.copy() for v in me.vertices]
    bvh = BVHTree.FromPolygons(co, tris)
    bones = {g.index: g.name for g in body.vertex_groups if g.name.startswith("mixamorig:")}
    vw = [{bones[g.group]: g.weight for g in v.groups if g.group in bones and g.weight > 0} for v in me.vertices]
    to_body = body.matrix_world.inverted() @ cloth.matrix_world
    new = []
    for v in cloth.data.vertices:
        p, _n, ti, _d = bvh.find_nearest(to_body @ v.co)
        a, b, c = (co[i] for i in tris[ti])
        w = barycentric_transform(p, a, b, c, Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
        acc = {}
        for k, idx in enumerate(tris[ti]):
            for name, x in vw[idx].items():
                acc[name] = acc.get(name, 0.0) + max(w[k], 0.0) * x
        total = sum(acc.values()) or 1.0
        new.append({n: x / total for n, x in acc.items() if x / total > 1e-3})
    for g in list(cloth.vertex_groups):
        cloth.vertex_groups.remove(g)
    groups = {}
    for i, ws in enumerate(new):
        for name, x in ws.items():
            g = groups.get(name) or groups.setdefault(name, cloth.vertex_groups.new(name=name))
            g.add([i], x, "REPLACE")
    print(f"[export] {cloth.name}: weights from the skin, {len(groups)} bone groups")


def lift_cloth(body_name="Human", cloth_name="Human.female_sportsuit01", gap=0.004):
    """Call #9: in places the CC0 suit lay on the skin at under a millimetre (a light patch of skin showed through
    the top behind the left shoulder). Each suit vertex closer than `gap` to the skin is moved out along the skin's
    normal to `gap`, about the thickness of the fabric."""
    from mathutils.bvhtree import BVHTree
    body, cloth = bpy.data.objects[body_name], bpy.data.objects[cloth_name]
    gi = body.vertex_groups["body"].index
    me = body.data
    on_body = {v.index for v in me.vertices if any(g.group == gi and g.weight > 0 for g in v.groups)}
    co = [body.matrix_world @ v.co for v in me.vertices]
    bvh = BVHTree.FromPolygons(co, [p.vertices[:] for p in me.polygons if all(i in on_body for i in p.vertices)])
    inv = cloth.matrix_world.inverted()
    moved = 0
    for v in cloth.data.vertices:
        p = cloth.matrix_world @ v.co
        hit, n, _i, d = bvh.find_nearest(p)
        if hit is None:
            continue
        side = (p - hit).dot(n)
        if side < gap:
            v.co = inv @ (hit + n.normalized() * gap)
            moved += 1
    print(f"[export] {cloth.name}: {moved} vertices lifted to {gap * 1000:.0f} mm off the skin")


def hide_covered_skin(body_name="Human", cloth_name="Human.female_sportsuit01", margin=0.012, reach=0.03):
    """Call #9: remove the skin that is always under the sportsuit. The suit has the skin's own weights (above), but
    in the arena's spring-driven poses the skin still poked through at the shoulders and collar by a few millimetres.
    A body vertex goes if the suit lies within `reach` of it and that point of the suit is more than `margin` from
    any edge of the garment (neckline, sleeves, hem, waistband, leg ends), so every visible edge keeps skin under it."""
    import bmesh
    from mathutils.bvhtree import BVHTree
    from mathutils.kdtree import KDTree
    body, cloth = bpy.data.objects[body_name], bpy.data.objects[cloth_name]
    cm = cloth.data
    cco = [cloth.matrix_world @ v.co for v in cm.vertices]
    bvh = BVHTree.FromPolygons(cco, [p.vertices[:] for p in cm.polygons])
    count = {}
    for p in cm.polygons:
        for e in p.edge_keys:
            count[e] = count.get(e, 0) + 1
    edges = [e for e, c in count.items() if c == 1]
    samples = []
    for a, b in edges:
        for k in range(5):
            samples.append(cco[a].lerp(cco[b], k / 4))
    kd = KDTree(len(samples))
    for i, p in enumerate(samples):
        kd.insert(p, i)
    kd.balance()
    gi = body.vertex_groups["body"].index
    bm = bmesh.new()
    bm.from_mesh(body.data)
    dl = bm.verts.layers.deform.active
    covered = set()
    for v in bm.verts:
        if dl is None or gi not in v[dl]:
            continue
        p = body.matrix_world @ v.co
        hit, _n, _i, d = bvh.find_nearest(p)
        if hit is None or d > reach:
            continue
        if kd.find(hit)[2] > margin:
            covered.add(v.index)
    faces = [f for f in bm.faces if all(v.index in covered for v in f.verts)]
    bmesh.ops.delete(bm, geom=faces, context="FACES_ONLY")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(body.data)
    bm.free()
    print(f"[export] {body.name}: removed {len(faces)} skin faces under the suit ({len(edges)} garment edges kept "
          f"{margin * 100:.0f} cm of skin under them)")


def clear_hair(hair_name="Human.ponytail01", others=("Human", "Human.female_sportsuit01"), gap=0.015, below=0.0):
    """Call #9: the ponytail hung so close to the back that its tail sank into the top when the head turned or the
    spine twisted. Hair vertices below the nape (`below` metres under the Neck joint) that lie within `gap` of the
    skin or suit are pushed out from that surface: distances from 0 to `gap` + 2 cm are remapped to `gap` to
    `gap` + 2 cm, so nothing sits closer than `gap` and the hair's layers keep their order."""
    from mathutils.bvhtree import BVHTree
    hair = bpy.data.objects[hair_name]
    arm = next(m.object for m in hair.modifiers if m.type == "ARMATURE")
    neck = (arm.matrix_world @ arm.data.bones["mixamorig:Neck"].head_local).z - below
    trees = []
    for name in others:
        o = bpy.data.objects[name]
        co = [o.matrix_world @ v.co for v in o.data.vertices]
        trees.append(BVHTree.FromPolygons(co, [p.vertices[:] for p in o.data.polygons]))
    inv = hair.matrix_world.inverted()
    moved = 0
    for v in hair.data.vertices:
        p = hair.matrix_world @ v.co
        if p.z > neck:
            continue
        best = None
        for t in trees:
            hit, n, _i, d = t.find_nearest(p)
            if hit is not None and (best is None or d < best[2]):
                best = (hit, n, d)
        if best is None or best[2] >= gap + 0.02:
            continue
        hit, n, d = best
        out = (p - hit).normalized() if (p - hit).length > 1e-6 and (p - hit).dot(n) > 0 else n.normalized()
        # Distances 0 .. gap + 2 cm are remapped to gap .. gap + 2 cm (continuous, and the hair keeps its layering).
        new = gap + d * 0.02 / (gap + 0.02)
        v.co = inv @ (hit + out * new)
        moved += 1
    print(f"[export] {hair.name}: {moved} ponytail vertices moved clear of the back")


def bake_modifiers():
    """Apply every modifier except the armature on each mesh (MPFB's helper masks and subdivision), so hidden
    helper geometry is really removed before export. The armature modifier is moved last first, because MPFB puts it
    first and the glTF exporter would otherwise skip the masks."""
    for obj in [o for o in bpy.data.objects if o.type == "MESH"]:
        arm = next((m for m in obj.modifiers if m.type == "ARMATURE"), None)
        if arm:
            with bpy.context.temp_override(object=obj, active_object=obj):
                bpy.ops.object.modifier_move_to_index(modifier=arm.name, index=len(obj.modifiers) - 1)
        for mod in [m for m in obj.modifiers if m.type != "ARMATURE"]:
            if not (mod.show_viewport and mod.show_render):
                obj.modifiers.remove(mod)  # switched off in MPFB's setup, so it isn't part of the look
                continue
            if mod.type == "SUBSURF":
                mod.levels = max(mod.levels, mod.render_levels)  # MPFB leaves the viewport level at 0
            try:
                with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj]):
                    bpy.ops.object.modifier_apply(modifier=mod.name)
            except RuntimeError:
                print(f"[export] {obj.name}: removed {mod.type} '{mod.name}' (Blender reports it as disabled)")
                obj.modifiers.remove(mod)
        print(f"[export] {obj.name}: {len(obj.data.vertices)} verts after baking modifiers")


def export():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(WORK, "claude_rigged.blend"))
    fit_clothes_weights()
    lift_cloth()
    hide_covered_skin()
    clear_hair()
    bake_modifiers()
    for o in bpy.data.objects:
        o.hide_set(False)
        o.select_set(o.type in {"MESH", "ARMATURE"})
    bpy.ops.export_scene.gltf(filepath=GLB, export_format="GLB", use_selection=True, export_apply=False,
                              export_animations=True, export_animation_mode="NLA_TRACKS", export_force_sampling=True,
                              export_image_format="AUTO", export_yup=True)
    patch_ior(GLB, {"Human.body": 1.4})
    print(f"[export] fighter.glb {os.path.getsize(GLB) / 1e6:.1f} MB")


def patch_ior(path, iors):
    """Call #9: Blender's glTF exporter leaves out KHR_materials_ior for an opaque material, so the skin's index of
    refraction (1.4; glTF's default is 1.5) is written into the GLB's JSON chunk here. The binary chunk is untouched."""
    import json
    import struct
    data = open(path, "rb").read()
    jlen = struct.unpack("<I", data[12:16])[0]
    doc = json.loads(data[20:20 + jlen])
    for m in doc["materials"]:
        if m["name"] in iors:
            m.setdefault("extensions", {})["KHR_materials_ior"] = {"ior": iors[m["name"]]}
    used = doc.setdefault("extensionsUsed", [])
    if "KHR_materials_ior" not in used:
        used.append("KHR_materials_ior")
    js = json.dumps(doc, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    rest = data[20 + jlen:]
    out = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + len(rest)) + struct.pack("<II", len(js), 0x4E4F534A) + js + rest
    open(path, "wb").write(out)
    print(f"[export] KHR_materials_ior set on {', '.join(iors)}")


def setup_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=GLB)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in scene.render.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.view_settings.view_transform = "AgX" if "AgX" in [v.identifier for v in scene.view_settings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
    world = bpy.data.worlds.new("judge")
    world.use_nodes = True
    env = world.node_tree.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(HDRI)
    world.node_tree.links.new(env.outputs["Color"], world.node_tree.nodes["Background"].inputs["Color"])
    scene.world = world
    key = bpy.data.objects.new("key", bpy.data.lights.new("key", "AREA"))
    key.data.energy, key.data.size = 350, 1.6
    key.location = (-1.8, -2.4, 2.5)
    key.rotation_euler = (Vector((0, 0, 1.3)) - key.location).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(key)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    arm = next(o for o in scene.objects if o.type == "ARMATURE")
    return scene, arm, cam


def pose(scene, arm, clip, frac):
    act = bpy.data.actions.get(clip)
    for t in list(arm.animation_data.nla_tracks):
        t.mute = True
    arm.animation_data.action = act
    if hasattr(arm.animation_data, "action_slot") and act.slots:
        arm.animation_data.action_slot = act.slots[0]
    f0, f1 = act.frame_range
    scene.frame_set(int(f0 + (f1 - f0) * frac))
    head = next(b for b in arm.pose.bones if b.name.endswith("Head"))
    return arm.matrix_world @ head.head


def shoot(scene, cam, name, angle_deg, dist, height, target, lens, folder):
    a = math.radians(angle_deg)
    cam.location = Vector((target.x + math.sin(a) * dist, target.y - math.cos(a) * dist, height))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens
    scene.render.filepath = os.path.join(folder, f"{name}.png")
    bpy.ops.render.render(write_still=True)


def main():
    export()
    scene, arm, cam = setup_scene()
    renders = os.path.join(ENTRY, "renders")
    os.makedirs(renders, exist_ok=True)
    head = pose(scene, arm, "fighting_idle", 0.3)
    body = Vector((head.x, head.y, head.z * 0.55))
    # glTF +Z forward becomes Blender -Y, so the fighter faces the -Y camera.
    shoot(scene, cam, "front", 0, 4.6, head.z * 0.6, body, 50, renders)
    shoot(scene, cam, "three_quarter", 35, 4.6, head.z * 0.62, body, 50, renders)
    shoot(scene, cam, "profile", 90, 4.6, head.z * 0.6, body, 50, renders)
    shoot(scene, cam, "closeup", 20, 0.95, head.z + 0.05, head + Vector((0, 0, 0.06)), 85, renders)
    previews = os.path.join(WORK, "previews")
    for clip, frac, ang in (("roundhouse_kick", 0.45, 70), ("jab_cross", 0.4, 60), ("knocked_out", 0.6, 80)):
        head = pose(scene, arm, clip, frac)
        shoot(scene, cam, f"action_{clip}", ang, 5.0, 1.1, Vector((head.x, head.y, 0.95)), 45, previews)
    print("[render] done")


main()
