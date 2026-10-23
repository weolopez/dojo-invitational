# Licenses — Hermes entry

Every third-party asset used in this entry, with source and license.

## Reused from the project's shared material (allowed by RULES.md §2)
| Asset | Path | Source / License | Use |
|---|---|---|---|
| Mixamo `mixamorig:` skeleton + 28 animation clips | `dojo/public/fighters/hermes.glb`, `assets/mixamo/*.fbx` | Adobe Mixamo. The project owner exported these; per the asset README they are standard Mixamo motions. Used under the owner's Mixamo access as provided in this repo. | Skeleton + all 28 fight clips |
| Skin pore normal map | `assets/textures/skin_pore_normal.png` | Provided in the repo's `assets/textures/` kit (CC0 per `assets/README.md` Poly Haven / asset-kit convention). | Tiled skin micro-normal |
| HDRI `basement_boxing_ring_2k.hdr` | `assets/polyhaven/hdri/` | Poly Haven — CC0. | Lighting for the beauty renders only (not embedded in the GLB) |

Note: the Mixamo clips are reused exactly as the project shipped them in its reference
rig. If the judge requires every competitor to re-license Mixamo motions independently,
flag it — they were taken only from the owner-provided files this repo already contains,
not re-downloaded.

## Original assets created for this entry (no third-party license)
| Asset | Path | Origin |
|---|---|---|
| Iris texture | `source/textures/iris.png` | Generated procedurally with PIL in `source/gen_textures.py`. Original. |
| Hair strand alpha | `source/textures/hair_strand.png` | Generated procedurally with PIL. Original. |
| Winged emblem | `source/textures/winged_emblem.png` | Generated procedurally with PIL. Fictional emblem, not a logo or trademark. |
| Base mesh (head, body, ears, eyes, teeth, hair, top, shorts) | built in `source/*.py` | Modeled from scratch in Blender. Fictional person; not derived from any real photo or scan. |

## Tools
- Blender 5.2.3 LTS — GNU GPL.
- Python 3 + Pillow (PIL) — HPND/MIT-style license.
- Node.js (validator only).

No celebrities, no real employees, no scraped scans, no paid/ripped assets, no runtime
network access.
