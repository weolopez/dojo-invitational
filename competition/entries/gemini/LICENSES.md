# Licenses & Third-Party Asset Attribution (`gemini`)

All assets used in this entry come from the shared local repository (`/Users/weo/Development/3d/assets/`) provided for **The Dojo Invitational** or are generated procedurally by our build scripts in `source/`, and are permitted for glTF 2.0 redistribution and offline real-time rendering.

## 1. Character Base Mesh, Textures & Rig
- **Asset:** `gemini.fbx` (`/Users/weo/Development/3d/assets/mixamo/roster/gemini.fbx`) and `xbot_with_skin_fighting_idle.fbx` (`/Users/weo/Development/3d/assets/mixamo/xbot_with_skin_fighting_idle.fbx`)
- **Source:** Adobe Mixamo (`https://www.mixamo.com/`)
- **License:** Adobe Mixamo Terms of Use — Royalty-free license for use, modification, and embedding in 3D applications, games, and redistributable runtime packages (`.glb` / `.gltf`). No real person or celebrity likeness is depicted.

## 2. Skeletal Combat Animation Library (28 Clips)
- **Assets:** All 28 FBX skeletal motion-capture clips in `/Users/weo/Development/3d/assets/mixamo/*.fbx` (`block`, `block_high`, `cross`, `crouch`, `fighting_idle`, `front_kick`, `getting_up`, `hit_by_uppercut`, `hit_head_big`, `hit_head_light`, `hit_reaction`, `hook`, `jab`, `jab_cross`, `jump`, `knocked_out`, `punch_combo`, `roundhouse_kick`, `side_kick`, `side_step_left`, `side_step_right`, `step_backward`, `step_forward`, `taunt`, `uppercut`, `victory`, `walk_backward`, `walk_forward`)
- **Source:** Adobe Mixamo (`https://www.mixamo.com/`)
- **License:** Adobe Mixamo Royalty-Free Animation License.

## 3. Combat Sound Effects (`sfx/*.ogg` & `sfx/*.wav`)
- **Curated `.ogg` Assets (`sfx/*.ogg`):** `impactPunch_heavy_000..002.ogg`, `impactPunch_medium_000..001.ogg`, `impactSoft_heavy_000.ogg`, `impactBell_heavy_000.ogg`, `footstep_carpet_000.ogg`, and `cloth1..3.ogg` from `/Users/weo/Development/3d/assets/kenney/kenney_impact-sounds/` and `/Users/weo/Development/3d/assets/kenney/kenney_rpg-audio/`
  - **Source:** Kenney (`https://kenney.nl/assets/impact-sounds` and `https://kenney.nl/assets/rpg-audio`)
  - **License:** CC0 1.0 Universal (Public Domain Dedication — `https://creativecommons.org/publicdomain/zero/1.0/`).
- **Mastered Multi-Layer `.wav` Assets (`sfx/*.wav`):** `jab_snap.wav`, `cross_heavy.wav`, `hook_crunch.wav`, `uppercut_launch.wav`, `frontkick_thud.wav`, `roundhouse_whip.wav`, `guard_block.wav`, and `ko_bell_gong.wav`
  - **Source:** Procedurally synthesized and mastered by `source/build_sound_effects.py`
  - **License:** CC0 1.0 Universal / MIT.

## 4. Lighting Environment Reference
- **Asset:** `basement_boxing_ring_2k.hdr` (`/Users/weo/Development/3d/assets/polyhaven/hdri/basement_boxing_ring_2k.hdr`)
- **Source:** Poly Haven (`https://polyhaven.com/a/basement_boxing_ring`)
- **License:** CC0 1.0 Universal (`https://creativecommons.org/publicdomain/zero/1.0/`).

## 5. Custom Code & Fight AI (`brain.js`, `source/upgrade_and_render.py`, `source/build_sound_effects.py`)
- **Author:** Gemini
- **License:** MIT / CC0 — Written from scratch specifically for The Dojo Invitational.
