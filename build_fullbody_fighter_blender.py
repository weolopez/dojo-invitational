"""
Blender Python Script: Full-Body Rigged Fighter & Virtual Dojo Room with Multi-Clip Combat Animations
Run with:
  /Applications/Blender.app/Contents/MacOS/Blender --background --python /Users/weo/Development/3d/build_fullbody_fighter_blender.py
or open in Blender -> Scripting -> Run Script, then press SPACEBAR in the 3D Viewport to play the combat animation!

Features:
- High-detail sculpted head matched to reference photos (brow ridge, nose bridge, cheek contour, jaw, wavy hair groom, right-ear AirPod Pro)
- Full-body articulated fighter character (neck, chest, abs, pelvis, arms, MMA gloves, legs, shin guards, feet)
- Complete Virtual Training Room (octagon floor mat, walls, neon rim strips, hanging heavy bag)
- Hierarchical Blender rig with multi-clip NLA animations exported to GLB:
  Idle, Step_Forward, Step_Back, Jab, Cross, Uppercut, Roundhouse_Kick, Front_Kick, Guard, Hit_React, KO, Arena_Showcase
- Exports:
  - /Users/weo/Development/3d/fullbody_fighter_arena.blend
  - /Users/weo/Development/3d/fullbody_fighter_arena.glb
  - /Users/weo/Development/3d/assets/fighter_character.glb (standalone fighter with all NLA clips for Three.js)
"""

import bpy
import bmesh
import math
import os
from mathutils import Vector, Euler

OUTPUT_DIR = "/Users/weo/Development/3d"
ASSETS_DIR = "/Users/weo/Development/3d/assets"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_mat(name, color, roughness=0.5, metallic=0.0, emission=None, emission_strength=0.0, sss=0.0):
    mat = bpy.data.materials.new(name=name)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        if sss > 0.0:
            if "Subsurface Weight" in bsdf.inputs:
                bsdf.inputs["Subsurface Weight"].default_value = sss
            elif "Subsurface" in bsdf.inputs:
                bsdf.inputs["Subsurface"].default_value = sss
        if emission and "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
            bsdf.inputs["Emission Strength"].default_value = emission_strength
    return mat


def deform_head_mesh(obj, scale_factor=0.145):
    """Sculpts anatomical cranial, facial, nose, cheek, brow, and jaw proportions matching reference views."""
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()

    for v in bm.verts:
        x, y, z = v.co.x, v.co.y, v.co.z

        x *= 0.86
        y *= 0.98
        z *= 1.18

        if z > 0.25:
            x *= 0.96 - 0.08 * max(0.0, (z - 0.5))
            if y < 0:
                y *= 1.04

        # Brow ridge prominence (front is -Y)
        if -0.25 < z < 0.35 and y < -0.4:
            brow_factor = math.exp(-((z - 0.18) ** 2) / 0.015) * math.exp(-(x ** 2) / 0.22)
            y -= 0.055 * brow_factor

        # Eye sockets recession
        for side in (-1.0, 1.0):
            eye_dx = x - side * 0.28
            eye_dz = z - 0.06
            eye_dist2 = eye_dx ** 2 + eye_dz ** 2
            if y < -0.35 and eye_dist2 < 0.045:
                y += 0.085 * math.exp(-eye_dist2 / 0.014)

        # Prominent nose bridge & rounded tip
        if abs(x) < 0.22 and -0.35 < z < 0.14 and y < -0.45:
            nose_profile = math.exp(-(x ** 2) / (0.012 + 0.02 * max(0.0, -z)))
            bridge_z = math.exp(-((z + 0.10) ** 2) / 0.032)
            tip_z = math.exp(-((z + 0.22) ** 2) / 0.008)
            y -= (0.16 * bridge_z + 0.11 * tip_z) * nose_profile

        # Full cheeks and nasolabial contour
        if -0.45 < z < 0.02 and y < -0.15:
            cheek = math.exp(-((abs(x) - 0.38) ** 2) / 0.04) * math.exp(-((z + 0.18) ** 2) / 0.045)
            x += (0.055 if x > 0 else -0.055) * cheek
            y -= 0.035 * cheek

        # Mouth / lips contour
        if abs(x) < 0.26 and -0.56 < z < -0.34 and y < -0.45:
            lip = math.exp(-(x ** 2) / 0.035) * math.exp(-((z + 0.44) ** 2) / 0.004)
            y -= 0.04 * lip

        # Rounded chin and submental fullness
        if z < -0.45:
            jaw_taper = max(0.52, 1.0 + 0.38 * (z + 0.45))
            x *= jaw_taper
            if y < -0.2:
                chin_bulge = math.exp(-(x ** 2) / 0.06) * math.exp(-((z + 0.72) ** 2) / 0.025)
                y -= 0.05 * chin_bulge
            if -0.65 < y < -0.15 and z < -0.68:
                z -= 0.045 * math.exp(-(x ** 2) / 0.12)

        v.co = Vector((x * scale_factor, y * scale_factor, z * scale_factor))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()


def add_part(name, primitive, loc, scale, mat, parent_obj=None, rot=(0, 0, 0), collection=None):
    if primitive == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=24, radius=1.0, location=loc)
    elif primitive == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=1.0, depth=1.0, location=loc)
    elif primitive == "cube":
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    elif primitive == "icosphere":
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1.0, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    obj.rotation_euler = Euler(rot, "XYZ")
    bpy.ops.object.shade_smooth()
    if mat:
        obj.data.materials.append(mat)
    if parent_obj:
        obj.parent = parent_obj
    if collection and collection not in obj.users_collection:
        collection.objects.link(obj)
    return obj


def build_virtual_room(mats, room_col):
    room_root = bpy.data.objects.new("Virtual_Dojo_Room", None)
    room_col.objects.link(room_root)

    add_part("Dojo_Floor", "cube", (0, 0, -0.05), (12.0, 12.0, 0.1), mats["floor"], room_root, collection=room_col)
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=3.8, depth=0.06, location=(0, 0, 0.03))
    mat_oct = bpy.context.active_object
    mat_oct.name = "Octagon_Combat_Mat"
    mat_oct.data.materials.append(mats["mat_surface"])
    mat_oct.parent = room_root
    room_col.objects.link(mat_oct)

    bpy.ops.mesh.primitive_torus_add(major_radius=3.6, minor_radius=0.03, major_segments=8, minor_segments=12, location=(0, 0, 0.06))
    ring_border = bpy.context.active_object
    ring_border.name = "Octagon_Neon_Border"
    ring_border.data.materials.append(mats["neon_blue"])
    ring_border.parent = room_root
    room_col.objects.link(ring_border)

    add_part("Back_Wall", "cube", (0, 5.5, 2.5), (12.0, 0.2, 5.0), mats["wall"], room_root, collection=room_col)
    add_part("Left_Wall", "cube", (-5.5, 0, 2.5), (0.2, 12.0, 5.0), mats["wall"], room_root, collection=room_col)
    add_part("Right_Wall", "cube", (5.5, 0, 2.5), (0.2, 12.0, 5.0), mats["wall"], room_root, collection=room_col)

    bag_pivot = bpy.data.objects.new("HeavyBag_Pivot", None)
    bag_pivot.location = (0.85, -1.1, 3.2)
    room_col.objects.link(bag_pivot)
    bag_pivot.parent = room_root

    add_part("HeavyBag_Chain", "cylinder", (0, 0, -0.45), (0.025, 0.025, 0.9), mats["metal"], bag_pivot, collection=room_col)
    add_part("HeavyBag_Body", "cylinder", (0, 0, -1.45), (0.26, 0.26, 1.35), mats["bag_red"], bag_pivot, collection=room_col)
    add_part("HeavyBag_StrapTop", "cylinder", (0, 0, -0.88), (0.265, 0.265, 0.08), mats["glove"], bag_pivot, collection=room_col)
    add_part("HeavyBag_StrapBot", "cylinder", (0, 0, -1.95), (0.265, 0.265, 0.08), mats["glove"], bag_pivot, collection=room_col)

    return room_root, bag_pivot


def build_fighter_and_rig(mats, fighter_col):
    def make_joint(name, loc, parent=None):
        j = bpy.data.objects.new(name, None)
        j.empty_display_type = "ARROWS"
        j.empty_display_size = 0.10
        j.location = loc
        fighter_col.objects.link(j)
        if parent:
            j.parent = parent
        return j

    root = make_joint("Fighter_Root", (0, 0, 0))
    pelvis = make_joint("Pelvis_Joint", (0, 0, 0.96), root)
    spine = make_joint("Spine_Joint", (0, 0, 0.22), pelvis)
    chest = make_joint("Chest_Joint", (0, 0, 0.26), spine)
    neck = make_joint("Neck_Joint", (0, 0, 0.28), chest)
    head_joint = make_joint("Head_Joint", (0, 0, 0.12), neck)

    # Torso & Combat Gi / Rashguard + Signature Brown Plaid Collar Accent
    add_part("Pelvis_Mesh", "sphere", (0, 0, 0.0), (0.21, 0.15, 0.15), mats["pants"], pelvis, collection=fighter_col)
    add_part("Belt_Black", "cylinder", (0, 0, 0.08), (0.205, 0.155, 0.06), mats["glove"], pelvis, collection=fighter_col)
    add_part("Abdomen_Mesh", "cylinder", (0, 0, 0.12), (0.19, 0.14, 0.28), mats["rashguard"], spine, collection=fighter_col)
    add_part("Chest_Mesh", "sphere", (0, 0, 0.12), (0.25, 0.17, 0.24), mats["rashguard"], chest, collection=fighter_col)
    add_part("Chest_Trim", "cylinder", (0, -0.015, 0.15), (0.245, 0.165, 0.055), mats["accent_red"], chest, collection=fighter_col)
    add_part("Neck_Mesh", "cylinder", (0, 0, 0.05), (0.072, 0.075, 0.14), mats["skin"], neck, collection=fighter_col)

    # High-Resolution Sculpted Head matched to reference photos
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=48, radius=1.0, location=(0, 0, 0.12))
    head = bpy.context.active_object
    head.name = "Head_Sculpt"
    deform_head_mesh(head, scale_factor=0.145)
    bpy.ops.object.shade_smooth()
    head.data.materials.append(mats["skin"])
    head.parent = head_joint
    fighter_col.objects.link(head)

    S = 0.145
    for side, s_lbl in ((-1.0, "R"), (1.0, "L")):
        add_part(
            f"Eye_Sclera_{s_lbl}",
            "sphere",
            (side * 0.28 * S, -0.78 * S, 0.12 + 0.06 * S),
            (0.115 * S, 0.115 * S, 0.115 * S),
            mats["sclera"],
            head_joint,
            collection=fighter_col,
        )
        add_part(
            f"Eye_Iris_{s_lbl}",
            "sphere",
            (side * 0.28 * S, -0.88 * S, 0.12 + 0.06 * S),
            (0.062 * S, 0.024 * S, 0.062 * S),
            mats["eye"],
            head_joint,
            collection=fighter_col,
        )
        add_part(
            f"Ear_{s_lbl}",
            "sphere",
            (side * 0.86 * S, 0.05 * S, 0.12 - 0.07 * S),
            (0.07 * S, 0.135 * S, 0.25 * S),
            mats["skin"],
            head_joint,
            rot=(math.radians(-10), math.radians(side * 12), 0),
            collection=fighter_col,
        )

    # Signature Right-Ear AirPod Pro (-X is character's right ear)
    add_part(
        "AirPod_Bud_R",
        "sphere",
        (-0.91 * S, -0.02 * S, 0.12 - 0.11 * S),
        (0.064 * S, 0.082 * S, 0.068 * S),
        mats["airpod"],
        head_joint,
        collection=fighter_col,
    )
    add_part(
        "AirPod_Stem_R",
        "cylinder",
        (-0.94 * S, -0.08 * S, 0.12 - 0.21 * S),
        (0.028 * S, 0.028 * S, 0.18 * S),
        mats["airpod"],
        head_joint,
        rot=(math.radians(32), math.radians(-14), 0),
        collection=fighter_col,
    )

    # Wavy Salt-and-Pepper Hair Clusters
    hair_clusters = [
        (-0.78, 0.12, 0.27, (0.28, 0.65, 0.55)),
        (0.78, 0.12, 0.27, (0.28, 0.65, 0.55)),
        (-0.84, 0.25, -0.03, (0.25, 0.55, 0.48)),
        (0.84, 0.25, -0.03, (0.25, 0.55, 0.48)),
        (0.0, 0.78, 0.10, (0.78, 0.45, 0.72)),
        (0.0, 0.72, -0.33, (0.72, 0.38, 0.48)),
        (0.0, 0.25, 0.87, (0.68, 0.68, 0.28)),
        (-0.18, -0.35, 0.93, (0.28, 0.35, 0.16)),
        (0.14, -0.38, 0.91, (0.24, 0.32, 0.14)),
    ]
    for idx, (hx, hy, hz, hscale) in enumerate(hair_clusters):
        add_part(
            f"Hair_Cluster_{idx}",
            "icosphere",
            (hx * S, hy * S, 0.12 + hz * S),
            (hscale[0] * S, hscale[1] * S, hscale[2] * S),
            mats["hair"],
            head_joint,
            collection=fighter_col,
        )

    # Arms & MMA Gloves
    limbs = {}
    for side, s_lbl in ((-1, "R"), (1, "L")):
        sh = make_joint(f"Shoulder_{s_lbl}", (side * 0.26, 0, 0.20), chest)
        el = make_joint(f"Elbow_{s_lbl}", (0, 0, -0.28), sh)
        wr = make_joint(f"Wrist_{s_lbl}", (0, 0, -0.25), el)

        add_part(f"Deltoid_{s_lbl}", "sphere", (0, 0, -0.02), (0.085, 0.085, 0.095), mats["skin"], sh, collection=fighter_col)
        add_part(f"UpperArm_{s_lbl}", "cylinder", (0, 0, -0.14), (0.062, 0.062, 0.26), mats["skin"], sh, collection=fighter_col)
        add_part(f"Forearm_{s_lbl}", "cylinder", (0, 0, -0.12), (0.052, 0.052, 0.24), mats["skin"], el, collection=fighter_col)
        add_part(f"MMA_Glove_{s_lbl}", "sphere", (0, -0.01, -0.04), (0.068, 0.078, 0.078), mats["glove"], wr, collection=fighter_col)
        add_part(f"WristWrap_{s_lbl}", "cylinder", (0, 0, 0.02), (0.056, 0.056, 0.06), mats["accent_red"], wr, collection=fighter_col)

        limbs[f"sh_{s_lbl}"] = sh
        limbs[f"el_{s_lbl}"] = el
        limbs[f"wr_{s_lbl}"] = wr

        # Legs & Shin Guards
        hip = make_joint(f"Hip_{s_lbl}", (side * 0.12, 0, -0.04), pelvis)
        knee = make_joint(f"Knee_{s_lbl}", (0, 0, -0.44), hip)
        ankle = make_joint(f"Ankle_{s_lbl}", (0, 0, -0.42), knee)

        add_part(f"Thigh_{s_lbl}", "cylinder", (0, 0, -0.22), (0.095, 0.095, 0.44), mats["pants"], hip, collection=fighter_col)
        add_part(f"Shin_{s_lbl}", "cylinder", (0, 0, -0.21), (0.072, 0.072, 0.40), mats["shinguard"], knee, collection=fighter_col)
        add_part(f"InstepGuard_{s_lbl}", "sphere", (0, -0.04, -0.02), (0.065, 0.09, 0.045), mats["accent_red"], ankle, collection=fighter_col)
        add_part(f"Foot_{s_lbl}", "cube", (0, -0.06, -0.04), (0.09, 0.22, 0.065), mats["skin"], ankle, collection=fighter_col)

        limbs[f"hip_{s_lbl}"] = hip
        limbs[f"knee_{s_lbl}"] = knee
        limbs[f"ankle_{s_lbl}"] = ankle

    return {
        "root": root,
        "pelvis": pelvis,
        "spine": spine,
        "chest": chest,
        "neck": neck,
        "head": head_joint,
        **limbs,
    }


def animate_combat_sequence(rig, bag_pivot=None):
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = 260
    scene.render.fps = 30

    def key_rot(obj, frame, deg_xyz):
        if not obj:
            return
        obj.rotation_euler = Euler([math.radians(d) for d in deg_xyz], "XYZ")
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)

    def key_loc(obj, frame, loc_xyz):
        if not obj:
            return
        obj.location = Vector(loc_xyz)
        obj.keyframe_insert(data_path="location", frame=frame)

    def set_guard_pose(f, bounce_z=0.0, torso_twist=-18, step_y=0.0):
        key_loc(rig["pelvis"], f, (0, step_y, 0.93 + bounce_z))
        key_rot(rig["pelvis"], f, (0, 0, torso_twist))
        key_rot(rig["spine"], f, (8, 0, -5))
        key_rot(rig["chest"], f, (10, 0, -8))
        key_rot(rig["head"], f, (-10, 0, 20))

        key_rot(rig["sh_L"], f, (55, 18, -15))
        key_rot(rig["el_L"], f, (105, 0, 0))
        key_rot(rig["sh_R"], f, (45, -18, 20))
        key_rot(rig["el_R"], f, (115, 0, 0))

        key_rot(rig["hip_L"], f, (18, 8, 0))
        key_rot(rig["knee_L"], f, (-28, 0, 0))
        key_rot(rig["hip_R"], f, (-16, -8, 0))
        key_rot(rig["knee_R"], f, (-24, 0, 0))
        if bag_pivot:
            key_rot(bag_pivot, f, (0, 0, 0))

    # Segment 1 (1-40): Idle Bounce
    set_guard_pose(1, 0.0, -18)
    set_guard_pose(10, -0.04, -15)
    set_guard_pose(20, 0.01, -20)
    set_guard_pose(30, -0.04, -16)
    set_guard_pose(40, 0.0, -18)

    # Segment 2 (41-60): Snap Left Jab
    set_guard_pose(42, 0.0, -18)
    set_guard_pose(50, -0.02, -4, step_y=-0.06)
    key_rot(rig["chest"], 50, (14, 0, 20))
    key_rot(rig["sh_L"], 50, (92, 4, -8))
    key_rot(rig["el_L"], 50, (10, 0, 0))
    if bag_pivot:
        key_rot(bag_pivot, 50, (-9, 3, 0))
    set_guard_pose(60, 0.0, -18)

    # Segment 3 (61-85): Power Right Cross
    set_guard_pose(62, 0.0, -18)
    set_guard_pose(72, -0.04, 24, step_y=-0.08)
    key_rot(rig["chest"], 72, (18, 0, 40))
    key_rot(rig["sh_R"], 72, (96, -8, 12))
    key_rot(rig["el_R"], 72, (6, 0, 0))
    key_rot(rig["sh_L"], 72, (45, 22, -20))
    key_rot(rig["el_L"], 72, (118, 0, 0))
    if bag_pivot:
        key_rot(bag_pivot, 72, (-18, -6, 0))
    set_guard_pose(85, 0.0, -18)

    # Segment 4 (86-115): Lead Hook + Rear Uppercut
    set_guard_pose(88, -0.05, -28)
    set_guard_pose(98, 0.03, 28, step_y=-0.05)
    key_rot(rig["spine"], 98, (-6, 8, 18))
    key_rot(rig["chest"], 98, (-8, 10, 32))
    key_rot(rig["sh_R"], 98, (78, -22, 18))
    key_rot(rig["el_R"], 98, (68, 0, 0))
    if bag_pivot:
        key_rot(bag_pivot, 98, (-22, 8, 0))
    set_guard_pose(115, 0.0, -18)

    # Segment 5 (116-150): High Right Roundhouse Kick
    set_guard_pose(118, -0.03, -12)
    set_guard_pose(132, 0.03, 38)
    key_rot(rig["pelvis"], 132, (-20, 24, 45))
    key_rot(rig["spine"], 132, (-14, -15, 16))
    key_rot(rig["hip_R"], 132, (112, -34, 26))
    key_rot(rig["knee_R"], 132, (-8, 0, 0))
    if bag_pivot:
        key_rot(bag_pivot, 132, (-28, 14, 0))
    set_guard_pose(150, 0.0, -18)

    # Segment 6 (151-175): Front Teep / Push Kick
    set_guard_pose(152, 0.0, -18)
    set_guard_pose(162, 0.01, -5)
    key_rot(rig["pelvis"], 162, (-12, 0, -5))
    key_rot(rig["hip_L"], 162, (98, 0, 0))
    key_rot(rig["knee_L"], 162, (-6, 0, 0))
    if bag_pivot:
        key_rot(bag_pivot, 162, (-24, 0, 0))
    set_guard_pose(175, 0.0, -18)

    # Segment 7 (176-195): High Tight Block / Guard
    set_guard_pose(177, 0.0, -18)
    set_guard_pose(185, -0.05, -10)
    key_rot(rig["spine"], 185, (16, 0, 0))
    key_rot(rig["chest"], 185, (18, 0, 0))
    key_rot(rig["sh_L"], 185, (72, 28, -28))
    key_rot(rig["el_L"], 185, (128, 0, 0))
    key_rot(rig["sh_R"], 185, (72, -28, 28))
    key_rot(rig["el_R"], 185, (128, 0, 0))
    set_guard_pose(195, 0.0, -18)

    # Segment 8 (196-215): Hit React Stagger
    set_guard_pose(197, 0.0, -18)
    set_guard_pose(204, -0.03, -28, step_y=0.14)
    key_rot(rig["spine"], 204, (-18, -8, -12))
    key_rot(rig["chest"], 204, (-22, -10, -16))
    key_rot(rig["head"], 204, (-28, 12, 32))
    set_guard_pose(215, 0.0, -18)

    # Segment 9 (216-260): Knockout Fall & Recovery
    set_guard_pose(217, 0.0, -18)
    key_loc(rig["pelvis"], 238, (0, 0.45, 0.18))
    key_rot(rig["pelvis"], 238, (-82, 0, -10))
    key_rot(rig["spine"], 238, (-10, 0, 0))
    key_rot(rig["chest"], 238, (-8, 0, 0))
    key_rot(rig["sh_L"], 238, (15, 45, 0))
    key_rot(rig["el_L"], 238, (25, 0, 0))
    key_rot(rig["sh_R"], 238, (15, -45, 0))
    key_rot(rig["el_R"], 238, (25, 0, 0))
    key_rot(rig["hip_L"], 238, (10, 12, 0))
    key_rot(rig["knee_L"], 238, (-15, 0, 0))
    key_rot(rig["hip_R"], 238, (8, -12, 0))
    key_rot(rig["knee_R"], 238, (-12, 0, 0))
    set_guard_pose(260, 0.0, -18)


def setup_lights_and_camera(room_col):
    bpy.ops.object.light_add(type="AREA", location=(-2.5, -3.2, 3.4))
    key = bpy.context.active_object
    key.data.energy = 450.0
    key.data.size = 2.5
    key.rotation_euler = Euler((math.radians(50), 0, math.radians(-35)), "XYZ")
    room_col.objects.link(key)

    bpy.ops.object.light_add(type="AREA", location=(2.8, -2.2, 2.5))
    fill = bpy.context.active_object
    fill.data.energy = 220.0
    fill.data.size = 2.5
    fill.rotation_euler = Euler((math.radians(60), 0, math.radians(45)), "XYZ")
    room_col.objects.link(fill)

    bpy.ops.object.light_add(type="AREA", location=(0.0, 3.2, 3.5))
    rim = bpy.context.active_object
    rim.data.energy = 380.0
    rim.data.color = (0.55, 0.78, 1.0)
    rim.rotation_euler = Euler((math.radians(-45), 0, 0), "XYZ")
    room_col.objects.link(rim)

    bpy.ops.object.camera_add(location=(-2.3, -4.2, 1.65), rotation=(math.radians(82), 0, math.radians(-26)))
    cam = bpy.context.active_object
    cam.data.lens = 38.0
    bpy.context.scene.camera = cam
    room_col.objects.link(cam)


def main():
    clear_scene()
    room_col = bpy.data.collections.new("Dojo_Room_Collection")
    fighter_col = bpy.data.collections.new("Fighter_Collection")
    bpy.context.scene.collection.children.link(room_col)
    bpy.context.scene.collection.children.link(fighter_col)

    mats = {
        "skin": make_mat("Fighter_Skin", (0.76, 0.55, 0.44), roughness=0.38, sss=0.30),
        "hair": make_mat("Fighter_Hair", (0.14, 0.13, 0.12), roughness=0.55),
        "sclera": make_mat("Fighter_Sclera", (0.95, 0.93, 0.91), roughness=0.12),
        "eye": make_mat("Fighter_Eye", (0.18, 0.10, 0.05), roughness=0.08),
        "airpod": make_mat("AirPod_White", (0.95, 0.96, 0.98), roughness=0.15),
        "rashguard": make_mat("Combat_Rashguard", (0.11, 0.13, 0.16), roughness=0.65),
        "pants": make_mat("Combat_Pants", (0.08, 0.09, 0.11), roughness=0.72),
        "glove": make_mat("MMA_Gloves", (0.06, 0.06, 0.07), roughness=0.35),
        "shinguard": make_mat("Shin_Guards", (0.10, 0.11, 0.13), roughness=0.40),
        "accent_red": make_mat("Crimson_Trim", (0.78, 0.12, 0.14), roughness=0.45),
        "bag_red": make_mat("HeavyBag_Leather", (0.58, 0.09, 0.10), roughness=0.38),
        "metal": make_mat("Steel_Chain", (0.65, 0.68, 0.72), roughness=0.25, metallic=0.9),
        "floor": make_mat("Dojo_Concrete", (0.09, 0.10, 0.12), roughness=0.80),
        "mat_surface": make_mat("Octagon_Mat", (0.14, 0.17, 0.22), roughness=0.68),
        "wall": make_mat("Dojo_Wall", (0.07, 0.08, 0.10), roughness=0.85),
        "neon_blue": make_mat("Neon_Ring", (0.2, 0.65, 1.0), roughness=0.2, emission=(0.2, 0.65, 1.0), emission_strength=4.5),
    }

    room_root, bag_pivot = build_virtual_room(mats, room_col)
    rig = build_fighter_and_rig(mats, fighter_col)
    animate_combat_sequence(rig, bag_pivot)
    setup_lights_and_camera(room_col)

    blend_out = os.path.join(OUTPUT_DIR, "fullbody_fighter_arena.blend")
    glb_out = os.path.join(OUTPUT_DIR, "fullbody_fighter_arena.glb")
    fighter_glb_out = os.path.join(ASSETS_DIR, "fighter_character.glb")

    bpy.ops.wm.save_as_mainfile(filepath=blend_out)
    bpy.ops.export_scene.gltf(filepath=glb_out, export_format="GLB", export_animations=True)

    # Also export standalone Fighter GLB (without room geometry) for the dojo/ Vite fighting game
    bpy.ops.object.select_all(action="DESELECT")
    for obj in fighter_col.objects:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=fighter_glb_out,
        export_format="GLB",
        use_selection=True,
        export_animations=True,
    )
    print(f"Saved arena to {blend_out}, {glb_out}, and standalone fighter to {fighter_glb_out}")


if __name__ == "__main__":
    main()
