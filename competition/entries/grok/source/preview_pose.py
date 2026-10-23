import bpy, sys, os, math
from mathutils import Vector
args = sys.argv[sys.argv.index('--')+1:]
blend, out = args[0], args[1]; shots = args[2:]  # clip:frame
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'; sc.render.resolution_x = 400; sc.render.resolution_y = 500
rig = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
imgs = []
for i, s in enumerate(shots):
    clip, fr, view = s.split(':')
    rig.animation_data.action = bpy.data.actions[clip]
    sc.frame_set(int(fr))
    ang = {'front': 0, 'side': 90, 'q': 35}[view]
    a = math.radians(ang); d = 4.5
    cam.location = (d*math.sin(a), -d*math.cos(a), 1.0)
    cam.rotation_euler = (math.radians(90), 0, a)
    sc.render.filepath = f"{out}_{i}.png"; bpy.ops.render.render(write_still=True)
