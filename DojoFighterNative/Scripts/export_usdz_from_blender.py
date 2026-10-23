"""
Export Blender fighter / avatar scenes to USDZ for RealityKit.

Run from repo root:
  /Applications/Blender.app/Contents/MacOS/Blender --background \\
    --python DojoFighterNative/Scripts/export_usdz_from_blender.py

Outputs:
  DojoFighterNative/DojoFighter/Resources/Models/fullbody_fighter_arena.usdz
  DojoFighterNative/DojoFighter/Resources/Models/user_hyperrealistic_avatar.usdz

Also writes companion .glb copies next to the USDZ files when possible.
"""

from __future__ import annotations

import os
import sys
import traceback

import bpy

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_DIR = os.path.join(
    REPO_ROOT, "DojoFighterNative", "DojoFighter", "Resources", "Models"
)

JOBS = [
    {
        "blend": os.path.join(REPO_ROOT, "fullbody_fighter_arena.blend"),
        "usdz": os.path.join(OUT_DIR, "fullbody_fighter_arena.usdz"),
        "glb": os.path.join(OUT_DIR, "fullbody_fighter_arena.glb"),
        "label": "full-body fighter + arena",
    },
    {
        "blend": os.path.join(REPO_ROOT, "user_hyperrealistic_avatar.blend"),
        "usdz": os.path.join(OUT_DIR, "user_hyperrealistic_avatar.usdz"),
        "glb": os.path.join(OUT_DIR, "user_hyperrealistic_avatar.glb"),
        "label": "hyper-realistic avatar",
    },
]


def ensure_out_dir() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)


def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def open_blend(path: str) -> None:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Missing blend file: {path}")
    bpy.ops.wm.open_mainfile(filepath=path)


def export_gltf(path: str) -> None:
    kwargs = dict(
        filepath=path,
        export_format="GLB",
        export_animations=True,
        export_apply=False,
    )
    # Blender 3/4/5 kw compatibility
    try:
        bpy.ops.export_scene.gltf(**kwargs)
    except TypeError:
        kwargs.pop("export_apply", None)
        bpy.ops.export_scene.gltf(**kwargs)


def export_usdz(path: str) -> None:
    """
    Prefer native USD export when the build has it.
    Falls back to USD (without Z) then notes Reality Converter.
    """
    # Blender 4+ experimental / extensions vary by build.
    operators = [
        ("wm.usd_export", {"filepath": path, "export_animations": True}),
        ("wm.usd_export", {"filepath": path}),
        ("export_scene.usd", {"filepath": path, "export_animations": True}),
        ("export_scene.usd", {"filepath": path}),
    ]

    last_error: Exception | None = None
    for op_id, kwargs in operators:
        op = bpy.ops
        for part in op_id.split("."):
            op = getattr(op, part, None)
            if op is None:
                break
        if op is None:
            continue
        try:
            # Some builds want .usd / .usdc intermediate
            base, ext = os.path.splitext(path)
            if ext.lower() == ".usdz":
                # Try direct usdz; if rejected, write .usd
                try:
                    op(**kwargs)
                    if os.path.isfile(path):
                        return
                except Exception as err:  # noqa: BLE001
                    last_error = err
                    usd_path = base + ".usd"
                    kwargs = dict(kwargs)
                    kwargs["filepath"] = usd_path
                    op(**kwargs)
                    if os.path.isfile(usd_path):
                        # Keep .usd; RealityKit can often load file URL in dev,
                        # and user can zip/convert to usdz with Reality Converter.
                        print(f"Wrote USD (not packaged): {usd_path}")
                        print(
                            "Tip: open in Reality Converter or "
                            "`xcrun usdzconvert` if available to make .usdz"
                        )
                        return
            else:
                op(**kwargs)
                return
        except Exception as err:  # noqa: BLE001
            last_error = err
            continue

    # Last resort: only GLB was possible
    msg = "USD/USDZ export operator not available in this Blender build."
    if last_error:
        msg += f" Last error: {last_error}"
    raise RuntimeError(msg)


def process_job(job: dict) -> None:
    print(f"\n=== Exporting {job['label']} ===")
    reset_scene()
    open_blend(job["blend"])

    # GLB always — useful for web tools and as backup
    try:
        export_gltf(job["glb"])
        print(f"GLB OK: {job['glb']}")
    except Exception as err:  # noqa: BLE001
        print(f"GLB export skipped: {err}")

    try:
        export_usdz(job["usdz"])
        if os.path.isfile(job["usdz"]):
            print(f"USDZ OK: {job['usdz']}")
        else:
            print("USD written (see messages above). Convert to .usdz if needed.")
    except Exception as err:  # noqa: BLE001
        print(f"USDZ export failed: {err}")
        print("The Swift app can still run with the procedural arena fallback.")
        print("Install a Blender build with USD export, or use Reality Converter on the GLB.")


def main() -> int:
    ensure_out_dir()
    print(f"Repo root: {REPO_ROOT}")
    print(f"Output:    {OUT_DIR}")

    failures = 0
    for job in JOBS:
        try:
            process_job(job)
        except Exception:
            failures += 1
            traceback.print_exc()

    print("\nDone.")
    if failures:
        print(f"{failures} job(s) had errors.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
