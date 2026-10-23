Place RealityKit-ready models here:

  fullbody_fighter_arena.usdz
  user_hyperrealistic_avatar.usdz

Generate them from your Blender files:

  /Applications/Blender.app/Contents/MacOS/Blender --background \
    --python DojoFighterNative/Scripts/export_usdz_from_blender.py

If Blender only writes .usd, convert with Reality Converter or:
  xcrun usdzconvert model.usd model.usdz

The app also looks for models next to the repo root in DEBUG builds.
