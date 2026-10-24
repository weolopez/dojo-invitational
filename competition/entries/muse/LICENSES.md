# Licences — Muse entry, Dojo Invitational

Everything in this entry traces to the shared competition assets supplied by
the owner in `/Users/weo/Development/3d/assets/`, or to tools. Nothing was
scraped, ripped from a game, or taken from a stock-asset site.

## Fighter mesh and textures

- **Kachujin character** (mesh, skeleton, embedded PBR textures):
  Adobe Mixamo — https://www.mixamo.com
  Source file in the shared assets: `assets/mixamo/roster/muse.fbx`
  (the roster character designated for Muse in the owner's dojo project).
  Mixamo's terms allow its characters and animations to be used in rendered
  content and games. The character is used inside this competition entry
  only and is not redistributed as a standalone asset.

## Animation

- **All 28 fight clips** (`block`, `jab`, `roundhouse_kick`, …):
  Adobe Mixamo — https://www.mixamo.com
  Source files in the shared assets: `assets/mixamo/<clip>.fbx`
  ("Without Skin" exports on the standard `mixamorig:` skeleton).
  Clips are used unmodified except for being packed into `fighter.glb`
  alongside the character; names and durations are preserved.

## Not used

- No Poly Haven, Kenney, Sketchfab, or other third-party models, textures,
  HDRIs, or sounds are used in `fighter.glb` or `brain.js`.
- No real person's likeness is depicted. Kachujin is a fictional Mixamo
  character.

## Tools (not assets)

- Blender 4.5.3 (GPL) — build and export pipeline (`source/build_fighter.py`).
- three.js r160 (MIT) — verification of the exported GLB and the beauty
  renders in `renders/` (neutral studio lighting; no third-party HDRI).
