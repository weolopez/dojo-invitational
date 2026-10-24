"""Give the owner fighter a skin PBR material and fitted training clothes.

Run with:
  /Applications/Blender.app/Contents/MacOS/Blender --background --python source/upgrade_body.py

The first run snapshots the current fighter into .work/input_fighter.glb. Subsequent
runs rebuild from that snapshot so garment layers do not accumulate.
"""

import math
import os
import shutil

import bpy
import bmesh
import numpy as np
from mathutils import Vector


ENTRY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ENTRY, ".work")
INPUT = os.path.join(WORK, "input_fighter.glb")
OUTPUT = os.path.join(ENTRY, "fighter.glb")
TEXTURE_SIZE = 1024
FABRIC_BASE = (0.105, 0.125, 0.14)
SKIN_BASE = (0.69, 0.53, 0.45)


def periodic_blur(values, sigma):
    fy = np.fft.fftfreq(values.shape[0])[:, None]
    fx = np.fft.fftfreq(values.shape[1])[None, :]
    kernel = np.exp(-2 * (np.pi * sigma) ** 2 * (fx * fx + fy * fy))
    return np.real(np.fft.ifft2(np.fft.fft2(values) * kernel))


def save_texture(name, pixels, alpha=False):
    image = bpy.data.images.new(
        name, width=pixels.shape[1], height=pixels.shape[0], alpha=alpha
    )
    if pixels.ndim == 2:
        rgba = np.ones((*pixels.shape, 4), dtype=np.float32)
        rgba[..., :3] = pixels[..., None]
    elif pixels.shape[2] == 3:
        rgba = np.ones((*pixels.shape[:2], 4), dtype=np.float32)
        rgba[..., :3] = pixels
    else:
        rgba = pixels
    image.pixels.foreach_set(rgba[::-1].astype(np.float32).ravel())
    image.filepath_raw = os.path.join(WORK, name + ".png")
    image.file_format = "PNG"
    image.save()
    image.pack()
    return image


def normal_from_height(height, strength):
    dx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * strength
    dy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * strength
    normals = np.dstack((-dx, dy, np.ones_like(height)))
    normals /= np.linalg.norm(normals, axis=2, keepdims=True)
    return normals * 0.5 + 0.5


def make_skin_images():
    rng = np.random.default_rng(23)
    n = TEXTURE_SIZE
    pores = np.zeros((n, n), dtype=np.float32)
    points = rng.integers(0, n, size=(int(n * n * 0.012), 2))
    pores[points[:, 0], points[:, 1]] = 1
    broad = periodic_blur(rng.standard_normal((n, n)), 18)
    fine = periodic_blur(rng.standard_normal((n, n)), 1.1)
    height = -periodic_blur(pores, 1.15) * 0.9 + fine * 0.11 + broad * 0.15
    height /= max(float(height.std()), 1e-6)
    normal = normal_from_height(height, 0.08)

    variation = periodic_blur(rng.standard_normal((n, n)), 10)
    variation /= max(float(variation.std()), 1e-6)
    albedo = np.empty((n, n, 3), dtype=np.float32)
    for channel, base in enumerate(SKIN_BASE):
        albedo[..., channel] = np.clip(base * (1 + variation * 0.018), 0, 1)

    roughness = np.clip(0.68 + periodic_blur(rng.standard_normal((n, n)), 2) * 0.018, 0.58, 0.78)
    return (
        save_texture("owner_body_skin", albedo),
        save_texture("owner_body_skin_normal", normal),
        save_texture("owner_body_skin_roughness", roughness),
    )


def make_fabric_images():
    n = TEXTURE_SIZE
    y, x = np.mgrid[0:n, 0:n].astype(np.float32) / n
    warp = np.cos(2 * np.pi * x * 64 + 0.18 * np.sin(2 * np.pi * y * 4))
    weft = np.cos(2 * np.pi * y * 64 + 0.18 * np.sin(2 * np.pi * x * 4))
    rng = np.random.default_rng(42)
    height = 0.55 * warp + 0.45 * weft
    height += periodic_blur(rng.standard_normal((n, n)), 1.0) * 0.12
    color_var = 0.045 * warp + 0.035 * weft + periodic_blur(rng.standard_normal((n, n)), 5) * 0.01
    albedo = np.empty((n, n, 3), dtype=np.float32)
    for channel, base in enumerate(FABRIC_BASE):
        albedo[..., channel] = np.clip(base * (1 + color_var), 0, 1)
    normal = normal_from_height(height, 0.11)
    roughness = np.clip(0.79 + color_var * 0.3, 0.72, 0.86)
    return (
        save_texture("owner_training_fabric", albedo),
        save_texture("owner_training_fabric_normal", normal),
        save_texture("owner_training_fabric_roughness", roughness),
    )


def pbr_material(name, base_color, roughness):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*base_color, 1)
    shader.inputs["Metallic"].default_value = 0
    shader.inputs["Roughness"].default_value = roughness
    return material, shader


def image_material(name, images, roughness, uv_scale=1):
    material, shader = pbr_material(name, (1, 1, 1), roughness)
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    uv = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (uv_scale, uv_scale, 1)
    links.new(uv.outputs["UV"], mapping.inputs["Vector"])

    def add_image(image, colorspace, output):
        texture = nodes.new("ShaderNodeTexImage")
        texture.image = image
        texture.image.colorspace_settings.name = colorspace
        links.new(mapping.outputs["Vector"], texture.inputs["Vector"])
        if output == "normal":
            normal_map = nodes.new("ShaderNodeNormalMap")
            normal_map.inputs["Strength"].default_value = 0.28
            links.new(texture.outputs["Color"], normal_map.inputs["Color"])
            links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])
        else:
            links.new(texture.outputs["Color"], shader.inputs[output])

    add_image(images[0], "sRGB", "Base Color")
    add_image(images[1], "Non-Color", "normal")
    add_image(images[2], "Non-Color", "Roughness")
    return material


def vertex_weights(obj, vertex, names):
    group_names = obj.vertex_groups
    weights = 0.0
    for assignment in vertex.groups:
        if group_names[assignment.group].name in names:
            weights += assignment.weight
    return weights


def shape_masculine_proportions(body):
    world_to_local = body.matrix_world.inverted()
    center_x = body.matrix_world.translation.x
    center_y = body.matrix_world.translation.y
    for vertex in body.data.vertices:
        point = body.matrix_world @ vertex.co
        torso = vertex_weights(
            body, vertex, {"mixamorig:Spine", "mixamorig:Spine1", "mixamorig:Spine2"}
        )
        hips = vertex_weights(
            body, vertex, {"mixamorig:Hips", "mixamorig:LeftUpLeg", "mixamorig:RightUpLeg"}
        )
        arms = vertex_weights(
            body, vertex, {"mixamorig:LeftArm", "mixamorig:RightArm",
                           "mixamorig:LeftForeArm", "mixamorig:RightForeArm"}
        )
        legs = vertex_weights(
            body, vertex, {"mixamorig:LeftUpLeg", "mixamorig:RightUpLeg",
                           "mixamorig:LeftLeg", "mixamorig:RightLeg"}
        )

        chest = math.exp(-((point.z - 1.38) / 0.22) ** 2) * torso
        waist = math.exp(-((point.z - 1.08) / 0.16) ** 2) * max(torso, hips)
        hip = math.exp(-((point.z - 0.91) / 0.19) ** 2) * hips
        thigh = math.exp(-((point.z - 0.66) / 0.22) ** 2) * legs

        point.x = center_x + (point.x - center_x) * (1 + 0.30 * chest - 0.16 * waist - 0.12 * hip + 0.14 * thigh)
        point.y = center_y + (point.y - center_y) * (1 + 0.18 * chest - 0.12 * waist - 0.08 * hip + 0.14 * thigh + 0.18 * arms)
        point.z = 1.40 + (point.z - 1.40) * (1 + 0.14 * arms)
        vertex.co = world_to_local @ point
    body.data.update()


def create_garment(body, name, predicate, fabric, offset, thickness):
    mesh = body.data.copy()
    garment = body.copy()
    garment.data = mesh
    garment.name = name
    garment.parent = body.parent
    garment.matrix_world = body.matrix_world.copy()
    body.users_collection[0].objects.link(garment)

    selected_faces = []
    for polygon in mesh.polygons:
        vertices = [mesh.vertices[index] for index in polygon.vertices]
        center = body.matrix_world @ (
            sum((vertex.co for vertex in vertices), Vector()) / len(vertices)
        )
        weights = {
            "torso": sum(
                vertex_weights(body, vertex, {"mixamorig:Spine", "mixamorig:Spine1", "mixamorig:Spine2"})
                for vertex in vertices
            ) / len(vertices),
            "hips": sum(
                vertex_weights(body, vertex, {"mixamorig:Hips", "mixamorig:LeftUpLeg", "mixamorig:RightUpLeg"})
                for vertex in vertices
            ) / len(vertices),
            "arms": sum(
                vertex_weights(body, vertex, {"mixamorig:LeftArm", "mixamorig:RightArm",
                                                "mixamorig:LeftForeArm", "mixamorig:RightForeArm"})
                for vertex in vertices
            ) / len(vertices),
        }
        if predicate(center, weights):
            selected_faces.append(polygon.index)

    if len(selected_faces) < 100:
        raise RuntimeError(f"{name} selection unexpectedly small: {len(selected_faces)} faces")

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    keep = set(selected_faces)
    bmesh.ops.delete(bm, geom=[face for face in bm.faces if face.index not in keep], context="FACES")
    bmesh.ops.delete(bm, geom=[edge for edge in bm.edges if not edge.link_faces], context="EDGES")
    bmesh.ops.delete(bm, geom=[vertex for vertex in bm.verts if not vertex.link_faces], context="VERTS")
    bm.normal_update()
    object_scale = body.matrix_world.to_scale().x
    for vertex in bm.verts:
        vertex.co += vertex.normal * (offset / object_scale)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.clear()
    mesh.materials.append(fabric)

    solidify = garment.modifiers.new("Fabric thickness", "SOLIDIFY")
    solidify.thickness = thickness
    solidify.offset = 1
    bpy.context.view_layer.objects.active = garment
    garment.select_set(True)
    for other in bpy.context.selected_objects:
        if other != garment:
            other.select_set(False)
    bpy.ops.object.modifier_move_to_index(modifier=solidify.name, index=0)
    bpy.ops.object.modifier_apply(modifier=solidify.name)
    garment.select_set(False)
    print(f"[owner-body] {name}: {len(selected_faces)} garment faces")
    return garment


def replace_material(obj, material):
    obj.data.materials.clear()
    obj.data.materials.append(material)


def main():
    os.makedirs(WORK, exist_ok=True)
    if not os.path.exists(INPUT):
        shutil.copy2(OUTPUT, INPUT)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=INPUT)
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    body = bpy.data.objects["Beta_Surface"]
    joints = bpy.data.objects["Beta_Joints"]
    shape_masculine_proportions(body)

    for obj in list(bpy.data.objects):
        if obj.type == "MESH" and obj.name == "Icosphere":
            bpy.data.objects.remove(obj, do_unlink=True)

    skin_images = make_skin_images()
    cloth_images = make_fabric_images()
    skin = image_material("Owner natural skin", skin_images, 0.68, uv_scale=3)
    fabric = image_material("Charcoal training knit", cloth_images, 0.8, uv_scale=8)
    replace_material(body, skin)
    replace_material(joints, skin)

    create_garment(
        body,
        "Sleeveless training top",
        lambda p, w: 0.98 <= p.z <= 1.535 and w["torso"] >= 0.28 and w["arms"] < 0.55,
        fabric,
        offset=0.003,
        thickness=0.0015,
    )
    create_garment(
        body,
        "Training shorts",
        lambda p, w: 0.70 <= p.z <= 1.075 and w["hips"] >= 0.24 and w["torso"] < 0.58,
        fabric,
        offset=0.004,
        thickness=0.002,
    )

    for action in bpy.data.actions:
        action.use_fake_user = True

    bpy.ops.export_scene.gltf(
        filepath=OUTPUT,
        export_format="GLB",
        export_yup=True,
        export_apply=False,
        export_animation_mode="ACTIONS",
        export_force_sampling=True,
        export_skins=True,
        export_morph=False,
        export_def_bones=False,
        export_image_format="AUTO",
        export_draco_mesh_compression_enable=False,
        export_cameras=False,
        export_lights=False,
    )
    print(f"[owner-body] exported {OUTPUT}; armature {armature.name}; actions {len(bpy.data.actions)}")


if __name__ == "__main__":
    main()
