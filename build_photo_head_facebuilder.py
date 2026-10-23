"""
Build a textured head from the photos in ./photos using KeenTools FaceBuilder (auto face detection + preset pins).
Run with:
  /Applications/Blender.app/Contents/MacOS/Blender --background --python build_photo_head_facebuilder.py
Outputs my_head_facebuilder.blend, my_head_facebuilder.glb and my_head_texture.png in this folder.
Open the .blend in Blender to refine pins by hand (FaceBuilder panel -> Pin mode) if the auto fit is off.
"""

import glob
import os

import bpy

from keentools.addon_config import fb_settings
from keentools.facebuilder.fbloader import FBLoader
from keentools.utils.coords import update_head_mesh_non_neutral
from keentools.utils.detect_faces import get_detected_faces, sort_detected_faces
from keentools.utils.focal_length import configure_focal_mode_and_fixes
from keentools.utils.images import load_rgba
from keentools.utils.materials import bake_tex

PROJECT_DIR = "/Users/weo/Development/3d"
PHOTOS = sorted(glob.glob(os.path.join(PROJECT_DIR, "photos", "*.png"))
                + glob.glob(os.path.join(PROJECT_DIR, "photos", "*.jpg"))
                + glob.glob(os.path.join(PROJECT_DIR, "photos", "*.jpeg")))
HEADNUM = 0


def auto_pin_camera(fb, head, camnum, photo):
    camera = head.get_camera(camnum)
    kid = camera.get_keyframe()
    img = load_rgba(camera)
    fb.set_use_emotions(head.should_use_emotions())
    from keentools.utils.detect_faces import set_detected_faces
    set_detected_faces(fb.detect_faces(img, fb.pixel_aspect_ratio(kid)))
    sort_detected_faces()
    faces = get_detected_faces()
    if not faces:
        print(f"[head] no face detected in {os.path.basename(photo)}")
        return False
    configure_focal_mode_and_fixes(fb, head)
    if not fb.detect_face_pose(kid, faces[0]):
        print(f"[head] face pose not found in {os.path.basename(photo)}")
        return False
    fb.remove_pins(kid)
    fb.add_preset_pins_and_solve(kid)
    update_head_mesh_non_neutral(fb, head)
    print(f"[head] fitted {os.path.basename(photo)}: {fb.pins_count(kid)} pins")
    return True


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_enable(module="keentools")
    if not PHOTOS:
        raise SystemExit("[head] no photos found in ./photos")

    bpy.ops.keentools_fb.add_head()
    settings = fb_settings()
    head = settings.get_head(HEADNUM)
    FBLoader.load_model(HEADNUM)
    fb = FBLoader.get_builder()

    for photo in PHOTOS:
        FBLoader.add_new_camera_with_image(HEADNUM, photo)

    fitted = [auto_pin_camera(fb, head, i, p) for i, p in enumerate(PHOTOS)]
    for camnum in range(len(PHOTOS)):
        FBLoader.update_camera_pins_count(HEADNUM, camnum)
    FBLoader.update_all_camera_positions(HEADNUM)
    FBLoader.update_all_camera_focals(HEADNUM)
    FBLoader.save_fb_serial_and_image_pathes(HEADNUM)
    print(f"[head] fitted {sum(fitted)} of {len(PHOTOS)} photos")

    status = bake_tex(HEADNUM, head.preview_texture_name())
    print(f"[head] texture baked: {status.success} {getattr(status, 'error_message', '')}")
    tex = bpy.data.images.get(head.preview_texture_name())
    if tex is not None:
        tex.filepath_raw = os.path.join(PROJECT_DIR, "my_head_texture.png")
        tex.file_format = "PNG"
        tex.save()
        mat = bpy.data.materials.new("FaceBuilder_Head_Texture")
        mat.use_nodes = True
        node = mat.node_tree.nodes.new("ShaderNodeTexImage")
        node.image = tex
        bsdf = mat.node_tree.nodes["Principled BSDF"]
        mat.node_tree.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])
        head.headobj.data.materials.clear()
        head.headobj.data.materials.append(mat)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PROJECT_DIR, "my_head_facebuilder.blend"))
    bpy.ops.object.select_all(action="DESELECT")
    head.headobj.select_set(True)
    bpy.context.view_layer.objects.active = head.headobj
    bpy.ops.export_scene.gltf(filepath=os.path.join(PROJECT_DIR, "my_head_facebuilder.glb"),
                              export_format="GLB", use_selection=True)
    print("[head] done")


main()
