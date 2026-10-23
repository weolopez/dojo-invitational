"""Install MPFB 2.0.18 into this entry's private Blender profile and point it at the CC0 assets.
Run: BLENDER_USER_RESOURCES=<entry>/.work/blender_user Blender --background --python source/00_install_mpfb.py
"""
import os
import bpy

WORK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".work")
bpy.ops.extensions.package_install_files(filepath=os.path.join(WORK, "downloads", "add-on-mpfb-v2.0.18.zip"),
                                         repo="user_default", enable_on_install=True)
prefs = bpy.context.preferences.addons["bl_ext.user_default.mpfb"].preferences
prefs.mpfb_user_data = os.path.join(WORK, "mpfb_user")
bpy.ops.wm.save_userpref()
print("[install] mpfb enabled, user data:", prefs.mpfb_user_data)
