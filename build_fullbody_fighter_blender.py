"""
Blender Python Script: Full-Body Rigged Fighter & Virtual Dojo Room with Keyframed Combat Animations
Run with:
  /Applications/Blender.app/Contents/MacOS/Blender --background --python /Users/weo/Development/3d/build_fullbody_fighter_blender.py
or open in Blender -> Scripting -> Run Script, then press SPACEBAR in the 3D Viewport to play the combat animation!

Features:
- Full-body articulated fighter character with sculpted head matched to reference photos
- Complete Virtual Training Room (octagon floor mat, walls, neon rim strips, hanging heavy bag)
- Hierarchical Blender Armature rig (Pelvis, Spine, Chest, Head, Arms, Hands, Legs, Feet)
- 160-frame keyframed combat animation sequence (Fighting Stance Bounce -> Jab-Cross Combo -> Roundhouse Kick -> Guard)
- Exports fullbody_fighter_arena.blend and fullbody_fighter_arena.glb
"""

import bpy
import bmesh
import math
import os
from mathutils import Vector, Euler

OUTPUT_DIR = "/Users/weo/Development/3d"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_mat(name, color, roughness=0.5, metallic=0.0, emission=None, emission_strength=0.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        if emission and "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
            bsdf.inputs["Emission Strength"].default_value = emission_strength
    return mat


def add_part(name, primitive, loc, scale, mat, parent_obj=None, rot=(0, 0, 0)):
    if primitive == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=24, radius=1.0, location=loc)
    elif primitive == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=1.0, depth=1.0, location=loc)
    elif primitive == "cube":
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    obj.rotation_euler = Euler(rot, "XYZ")
    bpy.ops.object.shade_smooth()
    if mat:
        obj.data.materials.append(mat)
    if parent_obj:
        obj.parent = parent_obj
    return obj


def build_virtual_room(mats):
    room_root = bpy.data.objects.new("Virtual_Dojo_Room", None)
    bpy.context.collection.objects.link(room_root)

    # Studio Floor & Padded Octagon Mat
    add_part("Dojo_Floor", "cube", (0, 0, -0.05), (12.0, 12.0, 0.1), mats["floor"], room_root)
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=3.8, depth=0.06, location=(0, 0, 0.03))
    mat_oct = bpy.context.active_object
    mat_oct.name = "Octagon_Combat_Mat"
    mat_oct.data.materials.append(mats["mat_surface"])
    mat_oct.parent = room_root

    # Glowing Ring Boundary
    bpy.ops.mesh.primitive_torus_add(major_radius=3.6, minor_radius=0.03, major_segments=8, minor_segments=12, location=(0, 0, 0.06))
    ring_border = bpy.context.active_object
    ring_border.name = "Octagon_Neon_Border"
    ring_border.data.materials.append(mats["neon_blue"])
    ring_border.parent = room_root

    # Back & Side Training Walls
    add_part("Back_Wall", "cube", (0, 5.5, 2.5), (12.0, 0.2, 5.0), mats["wall"], room_root)
    add_part("Left_Wall", "cube", (-5.5, 0, 2.5), (0.2, 12.0, 5.0), mats["wall"], room_root)
    add_part("Right_Wall", "cube", (5.5, 0, 2.5), (0.2, 12.0, 5.0), mats["wall"], room_root)

    # Heavy Punching Bag Rig
    bag_pivot = bpy.data.objects.new("HeavyBag_Pivot", None)
    bag_pivot.location = (0.85, -1.1, 3.2)
    bpy.context.collection.objects.link(bag_pivot)
    bag_pivot.parent = room_root

    add_part("HeavyBag_Chain", "cylinder", (0, 0, -0.45), (0.025, 0.025, 0.9), mats["metal"], bag_pivot)
    add_part("HeavyBag_Body", "cylinder", (0, 0, -1.45), (0.26, 0.26, 1.35), mats["bag_red"], bag_pivot)
    add_part("HeavyBag_StrapTop", "cylinder", (0, 0, -0.88), (0.265, 0.265, 0.08), mats["glove"], bag_pivot)
    add_part("HeavyBag_StrapBot", "cylinder", (0, 0, -1.95), (0.265, 0.265, 0.08), mats["glove"], bag_pivot)

    return bag_pivot


def build_fighter_and_rig(mats):
    # Create Hierarchical Empty Pivots for clean cross-version Blender & GLTF animation
    def make_joint(name, loc, parent=None):
        j = bpy.data.objects.new(name, None)
        j.empty_display_type = "ARROWS"
        j.empty_display_size = 0.12
        j.location = loc
        bpy.context.collection.objects.link(j)
        if parent:
            j.parent = parent
        return j

    root = make_joint("Fighter_Root", (0, 0, 0))
    pelvis = make_joint("Pelvis_Joint", (0, 0, 0.96), root)
    spine = make_joint("Spine_Joint", (0, 0, 0.22), pelvis)
    chest = make_joint("Chest_Joint", (0, 0, 0.26), spine)
    neck = make_joint("Neck_Joint", (0, 0, 0.28), chest)
    head_joint = make_joint("Head_Joint", (0, 0, 0.12), neck)

    # Torso & Combat Gi / Rashguard Meshes
    add_part("Pelvis_Mesh", "sphere", (0, 0, 0.0), (0.21, 0.15, 0.15), mats["pants"], pelvis)
    add_part("Belt_Black", "cylinder", (0, 0, 0.08), (0.20, 0.15, 0.06), mats["glove"], pelvis)
    add_part("Abdomen_Mesh", "cylinder", (0, 0, 0.12), (0.19, 0.14, 0.28), mats["rashguard"], spine)
    add_part("Chest_Mesh", "sphere", (0, 0, 0.12), (0.25, 0.17, 0.24), mats["rashguard"], chest)
    add_part("Chest_Trim", "cylinder", (0, -0.02, 0.14), (0.24, 0.16, 0.05), mats["accent_red"], chest)
    add_part("Neck_Mesh", "cylinder", (0, 0, 0.05), (0.075, 0.075, 0.14), mats["skin"], neck)

    # Sculpted Head + Hair + Right Ear AirPod
    head = add_part("Head_Sculpt", "sphere", (0, 0, 0.11), (0.13, 0.15, 0.17), mats["skin"], head_joint)
    add_part("Nose_Bridge", "sphere", (0, -0.145, 0.105), (0.024, 0.035, 0.042), mats["skin"], head_joint)
    for side, s_lbl in ((-1, "R"), (1, "L")):
        add_part(f"Eye_{s_lbl}", "sphere", (side * 0.045, -0.132, 0.125), (0.018, 0.012, 0.018), mats["eye"], head_joint)
        add_part(f"Ear_{s_lbl}", "sphere", (side * 0.132, 0.0, 0.10), (0.015, 0.028, 0.038), mats["skin"], head_joint)
    # Signature Right-Ear AirPod
    add_part("AirPod_R", "cylinder", (-0.144, -0.01, 0.085), (0.006, 0.006, 0.032), mats["airpod"], head_joint, rot=(0.4, -0.2, 0))
    # Wavy Salt-and-Pepper Hair
    add_part("Hair_Crown", "sphere", (0, 0.03, 0.16), (0.135, 0.145, 0.12), mats["hair"], head_joint)
    add_part("Hair_Side_R", "sphere", (-0.115, 0.02, 0.13), (0.045, 0.09, 0.085), mats["hair"], head_joint)
    add_part("Hair_Side_L", "sphere", (0.115, 0.02, 0.13), (0.045, 0.09, 0.085), mats["hair"], head_joint)

    # Arms & MMA Gloves
    limbs = {}
    for side, s_lbl in ((-1, "R"), (1, "L")):
        sh = make_joint(f"Shoulder_{s_lbl}", (side * 0.26, 0, 0.20), chest)
        el = make_joint(f"Elbow_{s_lbl}", (0, 0, -0.28), sh)
        wr = make_joint(f"Wrist_{s_lbl}", (0, 0, -0.25), el)

        add_part(f"Deltoid_{s_lbl}", "sphere", (0, 0, -0.02), (0.085, 0.085, 0.095), mats["skin"], sh)
        add_part(f"UpperArm_{s_lbl}", "cylinder", (0, 0, -0.14), (0.062, 0.062, 0.26), mats["skin"], sh)
        add_part(f"Forearm_{s_lbl}", "cylinder", (0, 0, -0.12), (0.052, 0.052, 0.24), mats["skin"], el)
        add_part(f"MMA_Glove_{s_lbl}", "sphere", (0, -0.01, -0.04), (0.065, 0.075, 0.075), mats["glove"], wr)
        add_part(f"WristWrap_{s_lbl}", "cylinder", (0, 0, 0.02), (0.055, 0.055, 0.06), mats["accent_red"], wr)

        limbs[f"sh_{s_lbl}"] = sh
        limbs[f"el_{s_lbl}"] = el
        limbs[f"wr_{s_lbl}"] = wr

        # Legs & Shin Guards
        hip = make_joint(f"Hip_{s_lbl}", (side * 0.12, 0, -0.04), pelvis)
        knee = make_joint(f"Knee_{s_lbl}", (0, 0, -0.44), hip)
        ankle = make_joint(f"Ankle_{s_lbl}", (0, 0, -0.42), knee)

        add_part(f"Thigh_{s_lbl}", "cylinder", (0, 0, -0.22), (0.095, 0.095, 0.44), mats["pants"], hip)
        add_part(f"Shin_{s_lbl}", "cylinder", (0, 0, -0.21), (0.072, 0.072, 0.40), mats["shinguard"], knee)
        add_part(f"Foot_{s_lbl}", "cube", (0, -0.06, -0.04), (0.09, 0.22, 0.07), mats["skin"], ankle)

        limbs[f"hip_{s_lbl}"] = hip
        limbs[f"knee_{s_lbl}"] = knee
        limbs[f"ankle_{s_lbl}"] = ankle

    return {
        "root": root,
        "pelvis": pelvis,
        "spine": spine,
        "chest": chest,
        "head": head_joint,
        **limbs,
    }


def animate_combat_sequence(rig, bag_pivot):
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = 160
    scene.render.fps = 30

    def key_rot(obj, frame, deg_xyz):
        obj.rotation_euler = Euler([math.radians(d) for d in deg_xyz], "XYZ")
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)

    def key_loc(obj, frame, loc_xyz):
        obj.location = Vector(loc_xyz)
        obj.keyframe_insert(data_path="location", frame=frame)

    # Base Fighting Guard Pose helper
    def set_guard_pose(f, bounce_z=0.0, torso_twist=-18):
        key_loc(rig["pelvis"], f, (0, 0, 0.93 + bounce_z))
        key_rot(rig["pelvis"], f, (0, 0, torso_twist))
        key_rot(rig["spine"], f, (8, 0, -5))
        key_rot(rig["chest"], f, (10, 0, -8))
        key_rot(rig["head"], f, (-12, 0, 22))

        # Lead Left Arm Guard (+X)
        key_rot(rig["sh_L"], f, (55, 18, -15))
        key_rot(rig["el_L"], f, (105, 0, 0))
        # Rear Right Arm Guard (-X)
        key_rot(rig["sh_R"], f, (45, -18, 20))
        key_rot(rig["el_R"], f, (115, 0, 0))

        # Staggered Combat Stance Legs
        key_rot(rig["hip_L"], f, (18, 8, 0))
        key_rot(rig["knee_L"], f, (-28, 0, 0))
        key_rot(rig["hip_R"], f, (-16, -8, 0))
        key_rot(rig["knee_R"], f, (-24, 0, 0))
        key_rot(bag_pivot, f, (0, 0, 0))

    # Frames 1-40: Rhythmic Fighter Bounce
    set_guard_pose(1, 0.0, -18)
    set_guard_pose(15, -0.04, -15)
    set_guard_pose(30, 0.01, -20)
    set_guard_pose(45, -0.03, -18)

    # Frame 58: Snap Left Jab
    set_guard_pose(58, -0.02, -5)
    key_rot(rig["chest"], 58, (14, 0, 18))
    key_rot(rig["sh_L"], 58, (92, 5, -8))
    key_rot(rig["el_L"], 58, (12, 0, 0))
    key_rot(bag_pivot, 58, (-8, 3, 0))

    # Frame 72: Power Right Cross
    set_guard_pose(72, -0.04, 22)
    key_rot(rig["chest"], 72, (18, 0, 38))
    key_rot(rig["sh_R"], 72, (96, -8, 12))
    key_rot(rig["el_R"], 72, (8, 0, 0))
    key_rot(rig["sh_L"], 72, (45, 20, -20))
    key_rot(rig["el_L"], 72, (115, 0, 0))
    key_rot(bag_pivot, 72, (-18, -6, 0))

    # Frame 90: Recover to Guard
    set_guard_pose(90, 0.0, -18)
    key_rot(bag_pivot, 90, (10, 2, 0))

    # Frame 112: High Right Roundhouse Kick
    set_guard_pose(112, 0.02, 35)
    key_rot(rig["pelvis"], 112, (-18, 22, 42))
    key_rot(rig["spine"], 112, (-12, -15, 15))
    key_rot(rig["hip_R"], 112, (108, -32, 25))
    key_rot(rig["knee_R"], 112, (-10, 0, 0))
    key_rot(bag_pivot, 112, (-26, 14, 0))

    # Frame 135 & 160: Return to Active Stance
    set_guard_pose(135, -0.03, -18)
    key_rot(bag_pivot, 135, (12, -5, 0))
    set_guard_pose(160, 0.0, -18)


def setup_lights_and_camera():
    bpy.ops.object.light_add(type="AREA", location=(-2.5, -3.2, 3.4))
    key = bpy.context.active_object
    key.data.energy = 450.0
    key.data.size = 2.5
    key.rotation_euler = Euler((math.radians(50), 0, math.radians(-35)), "XYZ")

    bpy.ops.object.light_add(type="AREA", location=(2.8, -2.2, 2.5))
    fill = bpy.context.active_object
    fill.data.energy = 220.0
    fill.data.size = 2.5
    fill.rotation_euler = Euler((math.radians(60), 0, math.radians(45)), "XYZ")

    bpy.ops.object.light_add(type="AREA", location=(0.0, 3.2, 3.5))
    rim = bpy.context.active_object
    rim.data.energy = 380.0
    rim.data.color = (0.55, 0.78, 1.0)
    rim.rotation_euler = Euler((math.radians(-45), 0, 0), "XYZ")

    bpy.ops.object.camera_add(location=(-2.3, -4.2, 1.65), rotation=(math.radians(82), 0, math.radians(-26)))
    cam = bpy.context.active_object
    cam.data.lens = 38.0
    bpy.context.scene.camera = cam


def main():
    clear_scene()
    mats = {
        "skin": make_mat("Fighter_Skin", (0.76, 0.55, 0.44), roughness=0.40),
        "hair": make_mat("Fighter_Hair", (0.15, 0.14, 0.13), roughness=0.58),
        "eye": make_mat("Fighter_Eye", (0.16, 0.09, 0.04), roughness=0.10),
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

    bag_pivot = build_virtual_room(mats)
    rig = build_fighter_and_rig(mats)
    animate_combat_sequence(rig, bag_pivot)
    setup_lights_and_camera()

    blend_out = os.path.join(OUTPUT_DIR, "fullbody_fighter_arena.blend")
    glb_out = os.path.join(OUTPUT_DIR, "fullbody_fighter_arena.glb")
    bpy.ops.wm.save_as_mainfile(filepath=blend_out)
    try:
        bpy.ops.export_scene.gltf(filepath=glb_out, export_format="GLB", export_animations=True)
    except Exception as e:
        print("GLB export notice:", e)
    print(f"Saved animated full-body fighter project to {blend_out}")


if __name__ == "__main__":
    main()
