import bpy, json, glob, os, math
from mathutils import Vector
out={}
for f in sorted(glob.glob('/workspace/dojo-invitational/assets/mixamo/extra/*.fbx')):
    n=os.path.basename(f)[:-4]
    if n.startswith('xbot'): continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=f)
    arm=[o for o in bpy.data.objects if o.type=='ARMATURE'][0]
    sc=bpy.context.scene; act=arm.animation_data.action
    fps=sc.render.fps/sc.render.fps_base
    f0,f1=act.frame_range
    def m(): 
        d={}
        for s in 'Left','Right':
            fo=arm.matrix_world@arm.pose.bones['mixamorig:%sFoot'%s].head
            to=arm.matrix_world@arm.pose.bones['mixamorig:%sToeBase'%s].head
            v=to-fo; d[s]=(math.asin(v.z/v.length), fo.z, to.z)
        hp=arm.matrix_world@arm.pose.bones['mixamorig:Hips'].head
        d['hip']=hp.z; return d
    # rest
    arm.data.pose_position='REST'; sc.frame_set(int(f0)); bpy.context.view_layer.update(); rest=m()
    arm.data.pose_position='POSE'
    fr=[]
    for i in range(int(f0),int(f1)+1):
        sc.frame_set(i); fr.append(m())
    out[n]={'fps':fps,'f0':f0,'rest':rest,'frames':fr}
    print(n,len(fr),fps)
json.dump(out,open('src.json','w'))
