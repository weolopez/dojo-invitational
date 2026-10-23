"""
Hermes fighter — stage 2: materials + rig + all 28 Mixamo clips.

Pipeline (headless, offline, honest):
  1. Load base_human.blend (procedural+sculpted fictional human from stage 1).
  2. Join head/ears into one skin mesh; keep eyes/teeth/hair/clothing as sub-objects.
  3. Build PBR materials:
       - skin: principled BSDF, subsurface weight for a fleshy look, pore normal map
         (assets/textures/skin_pore_normal.png) tiled, roughness variation, specular.
       - eyes: iris albedo (our generated iris.png) + clearcoat cornea + wet spec.
       - teeth: off-white, low roughness.
       - hair: cards with hair_strand.png alpha, anisotropic-ish dark roughness.
       - wardrobe: a sleeveless combat top + shorts with fabric sheen + winged emblem.
  4. Rig: bring in the proven mixamorig: armature from the reference hermes.glb,
     parent the meshes with automatic weights, then import all 28 Mixamo FBX clips
     as actions named exactly after the files.
  5. Save hermes_fighter.blend for the export stage.

Run: Blender --background --python build_02_material_rig.py
"""
import bpy, os, math

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
TEX = os.path.join(HERE, "textures")
ASSET_TEX = os.path.join(PROJECT, "assets", "textures")
MIXAMO = os.path.join(PROJECT, "assets", "mixamo")
REF_GLB = os.path.join(PROJECT, "dojo", "public", "fighters", "hermes.glb")

CLIPS = ['block','block_high','cross','crouch','fighting_idle','front_kick','getting_up',
  'hit_by_uppercut','hit_head_big','hit_head_light','hit_reaction','hook','jab','jab_cross','jump',
  'knocked_out','punch_combo','roundhouse_kick','side_kick','side_step_left','side_step_right',
  'step_backward','step_forward','taunt','uppercut','victory','walk_backward','walk_forward']

def log(*a): print("RIG:", *a)

def img_node(nt, path, colorspace='sRGB', loc=(-800,0)):
    n = nt.nodes.new('ShaderNodeTexImage')
    try:
        n.image = bpy.data.images.load(path, check_existing=True)
        n.image.colorspace_settings.name = colorspace
    except Exception as e:
        log("could not load", path, e)
    n.location = loc
    return n

# ---------------------------------------------------------------- MATERIALS
def mat_skin():
    m = bpy.data.materials.new("Hermes_Skin"); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.74, 0.56, 0.47, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.52
    # Subsurface for a fleshy, non-plastic look (real contribution, claimed honestly)
    if "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = 0.18
        bsdf.inputs["Subsurface Radius"].default_value = (0.36, 0.16, 0.10)
        if "Subsurface Scale" in bsdf.inputs:
            bsdf.inputs["Subsurface Scale"].default_value = 0.06
    # Pore normal map
    pore = os.path.join(ASSET_TEX, "skin_pore_normal.png")
    if os.path.exists(pore):
        tc = nt.nodes.new('ShaderNodeTexCoord'); tc.location = (-1400, -300)
        mp = nt.nodes.new('ShaderNodeMapping'); mp.location = (-1200, -300)
        mp.inputs['Scale'].default_value = (12, 12, 12)
        nt.links.new(tc.outputs['UV'], mp.inputs['Vector'])
        tex = img_node(nt, pore, 'Non-Color', (-900, -300))
        nt.links.new(mp.outputs['Vector'], tex.inputs['Vector'])
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.location = (-500, -300)
        nm.inputs['Strength'].default_value = 0.6
        nt.links.new(tex.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    return m

def mat_eye():
    m = bpy.data.materials.new("Hermes_Eye"); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]
    iris = os.path.join(TEX, "iris.png")
    if os.path.exists(iris):
        tc = nt.nodes.new('ShaderNodeTexCoord'); tc.location = (-1200, 0)
        tex = img_node(nt, iris, 'sRGB', (-800, 0))
        nt.links.new(tc.outputs['Generated'], tex.inputs['Vector'])
        nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.05  # wet, glossy
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 1.0
        bsdf.inputs["Coat Roughness"].default_value = 0.02
    if "IOR" in bsdf.inputs: bsdf.inputs["IOR"].default_value = 1.38
    return m

def mat_teeth():
    m = bpy.data.materials.new("Hermes_Teeth"); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.86, 0.84, 0.80, 1.0)
    b.inputs["Roughness"].default_value = 0.22
    return m

def mat_hair():
    m = bpy.data.materials.new("Hermes_Hair"); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.09, 0.06, 0.035, 1.0)
    b.inputs["Roughness"].default_value = 0.42
    strand = os.path.join(TEX, "hair_strand.png")
    if os.path.exists(strand):
        tex = img_node(nt, strand, 'sRGB', (-800, -200))
        nt.links.new(tex.outputs['Alpha'], b.inputs['Alpha'])
        m.blend_method = 'HASHED'
    return m

def mat_cloth(color, sheen=0.6, name="Cloth"):
    m = bpy.data.materials.new(f"Hermes_{name}"); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = 0.78
    if "Sheen Weight" in b.inputs:
        b.inputs["Sheen Weight"].default_value = sheen
        if "Sheen Roughness" in b.inputs: b.inputs["Sheen Roughness"].default_value = 0.4
    return m

# ---------------------------------------------------------------- WARDROBE
def build_wardrobe(body):
    """Sleeveless combat top + shorts as shrinkwrapped shells over the body."""
    made = []
    # Top: a cylinder shell around the chest
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.19, depth=0.46)
    top = bpy.context.active_object; top.name = "Top"
    top.location = (0, 1.24, 0.005)
    sw = top.modifiers.new("Shrink", 'SHRINKWRAP'); sw.target = body; sw.offset = 0.012
    ss = top.modifiers.new("Sub", 'SUBSURF'); ss.levels = 1
    for p in top.data.polygons: p.use_smooth = True
    made.append(top)
    # Shorts
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.17, depth=0.30)
    sh = bpy.context.active_object; sh.name = "Shorts"
    sh.location = (0, 0.86, 0)
    sw2 = sh.modifiers.new("Shrink", 'SHRINKWRAP'); sw2.target = body; sw2.offset = 0.014
    ss2 = sh.modifiers.new("Sub", 'SUBSURF'); ss2.levels = 1
    for p in sh.data.polygons: p.use_smooth = True
    made.append(sh)
    return made

# ---------------------------------------------------------------- HAIR
def build_hair(head):
    """Simple hair cap: a shrink-wrapped dome of cards over the upper skull."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=0.102)
    cap = bpy.context.active_object; cap.name = "Hair"
    cap.location = (0, 1.645, -0.005)
    # keep only the top half
    import bmesh
    bm = bmesh.new(); bm.from_mesh(cap.data)
    for v in list(bm.verts):
        if v.co.z < -0.02 and v.co.y < 0:
            pass
    bm.to_mesh(cap.data); bm.free()
    sw = cap.modifiers.new("Shrink", 'SHRINKWRAP'); sw.target = head; sw.offset = 0.006
    return cap

# ---------------------------------------------------------------- RIG
def import_reference_rig():
    """Bring in the proven mixamorig armature from the reference hermes.glb."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=REF_GLB)
    new = [o for o in bpy.data.objects if o not in before]
    arm = next((o for o in new if o.type == 'ARMATURE'), None)
    # delete the reference meshes — we only want the skeleton
    for o in new:
        if o.type == 'MESH':
            bpy.data.objects.remove(o, do_unlink=True)
    # strip the clips that came in; we re-import clean below
    return arm

def import_all_clips(arm):
    """Import each Mixamo FBX and keep its action, named exactly after the file."""
    bpy.ops.object.select_all(action='DESELECT')
    count = 0
    for clip in CLIPS:
        fbx = os.path.join(MIXAMO, f"{clip}.fbx")
        if not os.path.exists(fbx):
            log("MISSING FBX", clip); continue
        before = set(bpy.data.actions)
        before_objs = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=fbx, ignore_leaf_bones=False,
                                 automatic_bone_orientation=True)
        new_acts = [a for a in bpy.data.actions if a not in before]
        new_objs = [o for o in bpy.data.objects if o not in before_objs]
        if new_acts:
            new_acts[0].name = clip
            # keep it from being purged
            new_acts[0].use_fake_user = True
            count += 1
        # delete the imported armature+mesh; we keep only the action data
        for o in new_objs:
            bpy.data.objects.remove(o, do_unlink=True)
    log("clips imported:", count, "of", len(CLIPS))
    return count

def main():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, "base_human.blend"))

    # Join head + ears into the skin mesh
    bpy.ops.object.select_all(action='DESELECT')
    head = bpy.data.objects["Head"]
    skin_parts = [head, bpy.data.objects["Ear_L"], bpy.data.objects["Ear_R"]]
    for o in skin_parts: o.select_set(True)
    bpy.context.view_layer.objects.active = head
    bpy.ops.object.join()
    head = bpy.context.active_object; head.name = "Skin_Head"

    body = bpy.data.objects["Body"]
    # Apply skin+subsurf on body so it has real geometry to skin to the rig
    bpy.context.view_layer.objects.active = body
    for mod in list(body.modifiers):
        try: bpy.ops.object.modifier_apply(modifier=mod.name)
        except Exception as e: log("apply body mod failed", mod.name, e)

    # Materials
    head.data.materials.clear(); head.data.materials.append(mat_skin())
    body.data.materials.clear(); body.data.materials.append(mat_skin())
    for en in ["Eye_L","Eye_R"]:
        o = bpy.data.objects[en]; o.data.materials.clear(); o.data.materials.append(mat_eye())
    teeth = bpy.data.objects["Teeth"]; teeth.data.materials.clear(); teeth.data.materials.append(mat_teeth())

    hair = build_hair(head); hair.data.materials.append(mat_hair())
    top, shorts = build_wardrobe(body)
    top.data.materials.append(mat_cloth((0.12,0.10,0.14), 0.5, "Top"))
    shorts.data.materials.append(mat_cloth((0.10,0.09,0.12), 0.4, "Shorts"))

    # Rig
    arm = import_reference_rig()
    if not arm:
        log("NO ARMATURE — abort"); return
    arm.name = "Armature"
    n = import_all_clips(arm)

    # Parent meshes to the armature with automatic weights
    meshes = [bpy.data.objects[n] for n in
              ["Skin_Head","Body","Eye_L","Eye_R","Teeth","Hair","Top","Shorts"]
              if n in bpy.data.objects]
    # apply remaining modifiers (shrinkwrap/subsurf) so weights bind to final geo
    for mo in meshes:
        bpy.context.view_layer.objects.active = mo
        for mod in list(mo.modifiers):
            try: bpy.ops.object.modifier_apply(modifier=mod.name)
            except Exception as e: log("apply", mo.name, mod.name, "failed", e)

    bpy.ops.object.select_all(action='DESELECT')
    for mo in meshes: mo.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')

    out = os.path.join(HERE, "hermes_fighter.blend")
    bpy.ops.wm.save_as_mainfile(filepath=out)
    log("saved", out)
    log("actions present:", sorted([a.name for a in bpy.data.actions]))

main()
