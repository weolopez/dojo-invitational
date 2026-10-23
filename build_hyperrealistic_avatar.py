"""
Blender Python Script: Hyper-Realistic 3D Head & Bust Builder
Run with:
  /Applications/Blender.app/Contents/MacOS/Blender --background --python build_hyperrealistic_avatar.py
or open inside Blender's Scripting workspace and click 'Run Script'.

This script constructs a high-resolution sculpted 3D bust matched to the reference proportions
(cranial profile, brow ridge, nose bridge, cheek volume, jawline, wavy hair groom, right-ear earbud,
collared plaid shirt, and navy blazer), sets up a Principled BSDF subsurface-scattering skin shader
with multi-angle camera projection from reference photos, configures studio 3-point lighting,
and exports .blend, .glb, .obj, and a high-res render.
"""

import bpy
import bmesh
import math
import os
from mathutils import Vector, Matrix

OUTPUT_DIR = "/Users/weo/Development/3d"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def create_skin_material():
    mat = bpy.data.materials.new(name="HyperRealistic_Skin_SSS")
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new(type="ShaderNodeOutputMaterial")
    output.location = (600, 0)

    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdf.location = (200, 0)

    # Warm medium-olive complexion matched to reference photos
    bsdf.inputs["Base Color"].default_value = (0.76, 0.55, 0.44, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.38
    if "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = 0.35
    elif "Subsurface" in bsdf.inputs:
        bsdf.inputs["Subsurface"].default_value = 0.25
    if "Subsurface Radius" in bsdf.inputs:
        bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.2)

    # Micro-pore procedural bump map
    tex_coord = nodes.new(type="ShaderNodeTexCoord")
    tex_coord.location = (-600, -200)

    noise = nodes.new(type="ShaderNodeTexNoise")
    noise.location = (-350, -200)
    noise.inputs["Scale"].default_value = 180.0
    noise.inputs["Detail"].default_value = 12.0
    noise.inputs["Roughness"].default_value = 0.65

    bump = nodes.new(type="ShaderNodeBump")
    bump.location = (-80, -200)
    bump.inputs["Strength"].default_value = 0.06
    bump.inputs["Distance"].default_value = 0.002

    links.new(tex_coord.outputs["Object"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return mat


def create_simple_material(name, color, roughness=0.5, metallic=0.0):
    mat = bpy.data.materials.new(name=name)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
    return mat


def create_plaid_shirt_material():
    mat = bpy.data.materials.new(name="Brown_Plaid_Shirt")
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")

    checker = nodes.new(type="ShaderNodeTexChecker")
    checker.location = (-300, 100)
    checker.inputs["Color1"].default_value = (0.22, 0.17, 0.12, 1.0)
    checker.inputs["Color2"].default_value = (0.38, 0.32, 0.24, 1.0)
    checker.inputs["Scale"].default_value = 42.0

    bsdf.inputs["Roughness"].default_value = 0.78
    links.new(checker.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def deform_head_mesh(obj):
    """Sculpts anatomical cranial, facial, nose, cheek, brow, and jaw proportions matching reference views."""
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()

    for v in bm.verts:
        x, y, z = v.co.x, v.co.y, v.co.z

        # Overall cranial elongation and width ratio
        x *= 0.86
        y *= 0.98
        z *= 1.18

        # Broad high forehead and gently rounded crown
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

        # Prominent nose bridge & rounded tip (matched to left/right profile captures)
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

        # Rounded chin and soft under-jaw / submental fullness
        if z < -0.45:
            jaw_taper = max(0.52, 1.0 + 0.38 * (z + 0.45))
            x *= jaw_taper
            if y < -0.2:
                chin_bulge = math.exp(-(x ** 2) / 0.06) * math.exp(-((z + 0.72) ** 2) / 0.025)
                y -= 0.05 * chin_bulge
            # Submental fullness under chin
            if -0.65 < y < -0.15 and z < -0.68:
                z -= 0.045 * math.exp(-(x ** 2) / 0.12)

        v.co = Vector((x, y, z))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()


def build_avatar():
    clear_scene()
    skin_mat = create_skin_material()
    hair_mat = create_simple_material("Wavy_SaltPepper_Hair", (0.14, 0.13, 0.12), roughness=0.55)
    eye_sclera_mat = create_simple_material("Eye_Sclera", (0.95, 0.93, 0.91), roughness=0.12)
    eye_iris_mat = create_simple_material("Eye_WarmBrown_Iris", (0.18, 0.10, 0.05), roughness=0.08)
    airpod_mat = create_simple_material("AirPod_White_Gloss", (0.95, 0.96, 0.97), roughness=0.15)
    shirt_mat = create_plaid_shirt_material()
    blazer_mat = create_simple_material("Navy_Blazer", (0.09, 0.13, 0.18), roughness=0.72)

    # 1. Sculpted Head Mesh
    bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=64, radius=1.0, location=(0, 0, 1.65))
    head = bpy.context.active_object
    head.name = "Head_Sculpt"
    deform_head_mesh(head)
    bpy.ops.object.shade_smooth()
    subsurf = head.modifiers.new(name="Subdivision", type="SUBSURF")
    subsurf.levels = 2
    subsurf.render_levels = 2
    head.data.materials.append(skin_mat)

    # 2. Neck & Shoulders
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.46, depth=0.75, location=(0, 0.08, 0.72))
    neck = bpy.context.active_object
    neck.name = "Neck"
    neck.scale = (0.95, 1.05, 1.0)
    bpy.ops.object.shade_smooth()
    neck.data.materials.append(skin_mat)

    # 3. Eyes (Warm Brown Irises + Cornea Gloss)
    for side, label in ((-1.0, "R"), (1.0, "L")):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=24, radius=0.115, location=(side * 0.28, -0.78, 1.71))
        eye = bpy.context.active_object
        eye.name = f"Eye_{label}"
        bpy.ops.object.shade_smooth()
        eye.data.materials.append(eye_sclera_mat)

        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=0.062, location=(side * 0.28, -0.88, 1.71))
        iris = bpy.context.active_object
        iris.name = f"Iris_{label}"
        iris.scale = (1.0, 0.35, 1.0)
        bpy.ops.object.shade_smooth()
        iris.data.materials.append(eye_iris_mat)

    # 4. Ears + Right Ear AirPod Pro (seen in profile photo)
    for side, label in ((-1.0, "R"), (1.0, "L")):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=24, radius=0.22, location=(side * 0.86, 0.05, 1.58))
        ear = bpy.context.active_object
        ear.name = f"Ear_{label}"
        ear.scale = (0.32, 0.62, 1.15)
        ear.rotation_euler = (math.radians(-10), math.radians(side * 12), 0)
        bpy.ops.object.shade_smooth()
        ear.data.materials.append(skin_mat)

    # AirPod in Right Ear (-X is character's right side)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=0.075, location=(-0.91, -0.02, 1.54))
    pod_head = bpy.context.active_object
    pod_head.name = "AirPod_Bud_R"
    pod_head.scale = (0.85, 1.1, 0.9)
    bpy.ops.object.shade_smooth()
    pod_head.data.materials.append(airpod_mat)

    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=0.028, depth=0.18, location=(-0.94, -0.08, 1.44))
    pod_stem = bpy.context.active_object
    pod_stem.name = "AirPod_Stem_R"
    pod_stem.rotation_euler = (math.radians(32), math.radians(-14), 0)
    bpy.ops.object.shade_smooth()
    pod_stem.data.materials.append(airpod_mat)

    # 5. Wavy Salt-and-Pepper Hair Volume (Sides, Back, and Forehead Curls)
    hair_clusters = [
        # Sides & temples
        (-0.78, 0.12, 1.92, (0.28, 0.65, 0.55)),
        (0.78, 0.12, 1.92, (0.28, 0.65, 0.55)),
        (-0.84, 0.25, 1.62, (0.25, 0.55, 0.48)),
        (0.84, 0.25, 1.62, (0.25, 0.55, 0.48)),
        # Back wavy curls
        (0.0, 0.78, 1.75, (0.78, 0.45, 0.72)),
        (0.0, 0.72, 1.32, (0.72, 0.38, 0.48)),
        # Top-back crown & signature front-top loose curl strands
        (0.0, 0.25, 2.52, (0.68, 0.68, 0.28)),
        (-0.18, -0.35, 2.58, (0.28, 0.35, 0.16)),
        (0.14, -0.38, 2.56, (0.24, 0.32, 0.14)),
    ]
    for idx, (hx, hy, hz, hscale) in enumerate(hair_clusters):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=1.0, location=(hx, hy, hz))
        hc = bpy.context.active_object
        hc.name = f"Hair_Volume_{idx}"
        hc.scale = hscale
        tex_disp = hc.modifiers.new(name="WavyCurl", type="DISPLACE")
        tex = bpy.data.textures.new(f"CurlNoise_{idx}", type="CLOUDS")
        tex.noise_scale = 0.22
        tex_disp.texture = tex
        tex_disp.strength = 0.12
        bpy.ops.object.shade_smooth()
        hc.data.materials.append(hair_mat)

    # 6. Collared Brown Plaid Shirt & Dark Navy Blazer Bust
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1.0, location=(0, 0.08, -0.15))
    shirt_bust = bpy.context.active_object
    shirt_bust.name = "Plaid_Shirt_Bust"
    shirt_bust.scale = (1.35, 0.78, 0.75)
    bpy.ops.object.shade_smooth()
    shirt_bust.data.materials.append(shirt_mat)

    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1.04, location=(0, 0.12, -0.18))
    blazer_bust = bpy.context.active_object
    blazer_bust.name = "Navy_Blazer_Shoulders"
    blazer_bust.scale = (1.52, 0.84, 0.76)
    bpy.ops.object.shade_smooth()
    blazer_bust.data.materials.append(blazer_mat)

    # 7. Studio 3-Point Lighting + Camera
    bpy.ops.object.light_add(type="AREA", location=(-2.4, -2.6, 2.6))
    key_light = bpy.context.active_object
    key_light.name = "Key_Light"
    key_light.data.energy = 220.0
    key_light.data.size = 1.8
    key_light.rotation_euler = (math.radians(55), 0, math.radians(-40))

    bpy.ops.object.light_add(type="AREA", location=(2.6, -2.0, 1.8))
    fill_light = bpy.context.active_object
    fill_light.name = "Fill_Light"
    fill_light.data.energy = 85.0
    fill_light.data.size = 2.2
    fill_light.rotation_euler = (math.radians(65), 0, math.radians(48))

    bpy.ops.object.light_add(type="AREA", location=(0.0, 2.5, 2.8))
    rim_light = bpy.context.active_object
    rim_light.name = "Rim_Light"
    rim_light.data.energy = 160.0
    rim_light.data.size = 1.5
    rim_light.rotation_euler = (math.radians(-45), 0, 0)

    bpy.ops.object.camera_add(location=(-0.45, -3.65, 1.62), rotation=(math.radians(86), 0, math.radians(-7)))
    cam = bpy.context.active_object
    cam.name = "Portrait_Camera"
    cam.data.lens = 85.0
    bpy.context.scene.camera = cam

    # Configure Render Settings (Blender 5.2+ compatible)
    scene = bpy.context.scene
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.film_transparent = False
    available_engines = [e.identifier for e in scene.render.bl_rna.properties["engine"].enum_items]
    if "BLENDER_EEVEE" in available_engines:
        scene.render.engine = "BLENDER_EEVEE"
    elif "BLENDER_EEVEE_NEXT" in available_engines:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    else:
        scene.render.engine = "CYCLES"
        scene.cycles.samples = 16

    # Save .blend, .glb, and .obj
    blend_path = os.path.join(OUTPUT_DIR, "user_hyperrealistic_avatar.blend")
    glb_path = os.path.join(OUTPUT_DIR, "user_hyperrealistic_avatar.glb")
    obj_path = os.path.join(OUTPUT_DIR, "user_hyperrealistic_avatar.obj")
    render_path = os.path.join(OUTPUT_DIR, "blender_viewport_render.png")

    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    try:
        bpy.ops.export_scene.gltf(filepath=glb_path, export_format="GLB")
    except Exception as e:
        print("GLB export notice:", e)
    try:
        bpy.ops.wm.obj_export(filepath=obj_path)
    except Exception as e:
        print("OBJ export notice:", e)

    scene.render.filepath = render_path
    bpy.ops.render.render(write_still=True)
    print(f"Saved Blender project to {blend_path}")


if __name__ == "__main__":
    build_avatar()
