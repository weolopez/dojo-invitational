#!/usr/bin/env python3
"""
Hyper-Realism, 3D Anatomy & Athletic Combat Gear Upgrade Pipeline for `competition/entries/gemini/fighter.glb`
1. Meter-Scale Skeleton & Armature Normalization:
   - Converts `Armature` (node 67) from `scale=0.01, rotation=Rx(+90 deg)` to exact Identity (`scale=1.0`),
     scaling all 65 bone translations, animation tracks, and `inverseBindMatrices` into metres so Three.js
     `Skeleton.prototype.pose()` in `dojo/src/judge.js` renders all 6 views at full 1.73m scale in frame.
   - Grounds `fighting_idle` so the supporting boot sole sits flush at `y = 0.000 m`.
2. 3D Mesh De-Sci-Fi & Anatomical Facial Resculpting:
   - Removes the 6 floating sci-fi spacesuit armor/gadget pods (`Comp 11, 18` left-forearm computer pod;
     `Comp 19, 20, 21, 22` floating shoulder armor pods) and 3 duplicate opaque eyelash cards (`Comp 23..25`)
     from `Mesh 0 Prim 0`.
   - Flattens `Comp 4` (back jetpack hump) and `Comp 5` (rigid spacesuit helmet collar bowl) via boundary-locked
     Laplacian smoothing into a natural athletic upper back and low-profile crew-neck collar.
   - Resculpts `Prim 1 Comp 0` (Head & Face) from stylized Mixamo Astra proportions into adult athletic human
     bone structure (chin projection +5.2mm, jaw/gonial width +14%, zygomatic cheekbones +2.2mm, supraorbital
     brow ridge lowered -2.0mm & projected +2.2mm, vertical eye aperture refined -12%, lip protrusion refined -1.6mm),
     tucks the outer eyelash card corners inward so there is zero winged spike, and aligns the 3D eyeball meshes
     (`Comp 6 & 7`) to straight-ahead binocular gaze.
3. Dedicated glTF 2.0 PBR Materials (`Mesh 0 Prim 1` split into Skin, Wet Eyes, and Upper Combat Gear):
   - Disables all `emissiveTexture` / `emissiveFactor` maps so zero sci-fi lights or emblems glow.
   - Separates `Ch48_eyes` (`clearcoatFactor: 1.0, clearcoatRoughnessFactor: 0.01, roughnessFactor: 0.03, ior: 1.38`),
     `Ch48_skin` (`roughnessFactor: 1.0, metallicFactor: 0.0, ior: 1.40, sheen, specularFactor: 0.32`), and
     `Ch48_upper_gear` / `Ch48_body1` (`roughnessFactor: 1.0, metallicFactor: 0.0, sheen`).
4. 4K/2K Multi-Channel Texture Reconstruction (Diffuse, Normal, MetallicRoughness, Specular):
   - Rasterizes exact 4096x4096 UV zone masks (`mask_1001.bin`, `mask_1002.bin`) directly from the 3D triangles.
   - Completely removes the winged eyeliner on the face (across Diffuse, Normal, Roughness, and Specular),
     places photorealistic amber-chestnut human irises at the exact straight-ahead gaze centers `(0.9478, 0.3125)`
     and `(0.8676, 0.3125)` with moist pink lacrimal caruncles, and synthesizes 3D sebaceous skin pores and
     pore-level roughness breakup.
   - Completely removes the yellow chest emblem, white sci-fi circuit lines, kidney pods, purple straps, and
     hexagonal spacesuit honeycomb across all texture maps, replacing them with a matte charcoal-obsidian &
     deep slate-navy interlock-knit compression rashguard, open-finger black pebbled-leather MMA gloves with
     bare human skin fingers and woven wrist wraps, compression fight tights, and black leather shin guards.
"""

import json
import math
import os
import re
import shutil
import struct
import subprocess
from collections import defaultdict, deque

PROJECT_DIR = "/Users/weo/Development/3d"
ENTRY_DIR = os.path.join(PROJECT_DIR, "competition", "entries", "gemini")
RENDERS_DIR = os.path.join(ENTRY_DIR, "renders")
JUDGING_DIR = os.path.join(PROJECT_DIR, "competition", "judging", "gemini")
BASE_GLB = os.path.join(PROJECT_DIR, "dojo", "public", "fighters", "gemini.glb")
FBX_PATH = os.path.join(PROJECT_DIR, "assets", "mixamo", "roster", "gemini.fbx")
OUT_GLB = os.path.join(ENTRY_DIR, "fighter.glb")
WORK_DIR = os.path.join(ENTRY_DIR, ".work")

# Zone IDs for 4096x4096 UV raster masks
ZONE_NONE = 0
ZONE_SKIN_HEAD_NECK = 1
ZONE_EYEBALL_LEFT = 2
ZONE_EYEBALL_RIGHT = 3
ZONE_EYE_CARUNCLE = 4
ZONE_TEETH = 5
ZONE_HAND_FINGERS = 6
ZONE_HAND_GLOVE = 7
ZONE_HAND_WRAP = 8
ZONE_RASHGUARD_UPPER = 9

ZONE_NECK_SKIN_LOWER = 10
ZONE_COLLAR_TRIM = 11
ZONE_RASHGUARD_YOKE = 12
ZONE_FIGHT_TIGHTS = 13
ZONE_SHIN_GUARDS = 14
ZONE_WRESTLING_SHOES = 15


def extract_fbx_pngs():
    os.makedirs(WORK_DIR, exist_ok=True)
    with open(FBX_PATH, "rb") as f:
        fbx = f.read()

    pos = 0
    extracted = {}
    while True:
        idx = fbx.find(b"\x89PNG\r\n\x1a\n", pos)
        if idx == -1:
            break
        iend = fbx.find(b"IEND\xaeB`\x82", idx)
        if iend == -1:
            break
        png_bytes = fbx[idx : iend + 8]
        ctx = fbx[max(0, idx - 300) : idx]
        names = re.findall(rb"[A-Za-z0-9_]+\.png", ctx)
        if names:
            stem = os.path.splitext(names[-1].decode("utf-8"))[0]
            out_path = os.path.join(WORK_DIR, f"{stem}.png")
            with open(out_path, "wb") as pf:
                pf.write(png_bytes)
            extracted[stem] = out_path
        pos = iend + 8
    return extracted


def find_components(vc, indices):
    adj = defaultdict(list)
    for k in range(0, len(indices), 3):
        a, b, c = indices[k], indices[k + 1], indices[k + 2]
        adj[a].extend((b, c))
        adj[b].extend((a, c))
        adj[c].extend((a, b))
    vis = [False] * vc
    comps = []
    for v in range(vc):
        if not vis[v] and v in adj:
            q = deque([v])
            vis[v] = True
            comp = [v]
            while q:
                u = q.popleft()
                for w in adj[u]:
                    if not vis[w]:
                        vis[w] = True
                        q.append(w)
                        comp.append(w)
            comps.append(comp)
    comps.sort(key=len, reverse=True)
    return comps, adj


def recompute_normals(vc, pos, indices):
    nx = [0.0] * vc
    ny = [0.0] * vc
    nz = [0.0] * vc
    for k in range(0, len(indices), 3):
        i0, i1, i2 = indices[k], indices[k + 1], indices[k + 2]
        ax, ay, az = pos[i0 * 3], pos[i0 * 3 + 1], pos[i0 * 3 + 2]
        bx, by, bz = pos[i1 * 3], pos[i1 * 3 + 1], pos[i1 * 3 + 2]
        cx, cy, cz = pos[i2 * 3], pos[i2 * 3 + 1], pos[i2 * 3 + 2]
        ux, uy, uz = bx - ax, by - ay, bz - az
        vx, vy, vz = cx - ax, cy - ay, cz - az
        fnx = uy * vz - uz * vy
        fny = uz * vx - ux * vz
        fnz = ux * vy - uy * vx
        for iv in (i0, i1, i2):
            nx[iv] += fnx
            ny[iv] += fny
            nz[iv] += fnz
    out = [0.0] * (vc * 3)
    for v in range(vc):
        l = math.sqrt(nx[v] * nx[v] + ny[v] * ny[v] + nz[v] * nz[v]) or 1.0
        out[v * 3] = nx[v] / l
        out[v * 3 + 1] = ny[v] / l
        out[v * 3 + 2] = nz[v] / l
    return out


def weld_spatial_normals(pos_list, nor_list):
    """Weld vertex normals across vertices sharing identical 3D positions."""
    accum = defaultdict(lambda: [0.0, 0.0, 0.0])
    for pos, nor in zip(pos_list, nor_list):
        vc = len(pos) // 3
        for v in range(vc):
            key = (round(pos[v * 3], 4), round(pos[v * 3 + 1], 4), round(pos[v * 3 + 2], 4))
            acc = accum[key]
            acc[0] += nor[v * 3]
            acc[1] += nor[v * 3 + 1]
            acc[2] += nor[v * 3 + 2]
    for pos, nor in zip(pos_list, nor_list):
        vc = len(pos) // 3
        for v in range(vc):
            key = (round(pos[v * 3], 4), round(pos[v * 3 + 1], 4), round(pos[v * 3 + 2], 4))
            ax, ay, az = accum[key]
            l = math.sqrt(ax * ax + ay * ay + az * az) or 1.0
            nor[v * 3] = ax / l
            nor[v * 3 + 1] = ay / l
            nor[v * 3 + 2] = az / l


def rasterize_uv_mask(uvs, indices, tri_zones, size=4096):
    """Rasterizes triangle zone IDs into a size x size uint8 UV mask with 18px gutter dilation."""
    mask = bytearray(size * size)
    s_1 = size - 1
    for k in range(0, len(indices), 3):
        z = tri_zones[k // 3]
        if z == 0:
            continue
        i0, i1, i2 = indices[k], indices[k + 1], indices[k + 2]
        u0, v0 = uvs[i0 * 2], uvs[i0 * 2 + 1]
        u1, v1 = uvs[i1 * 2], uvs[i1 * 2 + 1]
        u2, v2 = uvs[i2 * 2], uvs[i2 * 2 + 1]
        x0, y0 = u0 * s_1, v0 * s_1
        x1, y1 = u1 * s_1, v1 * s_1
        x2, y2 = u2 * s_1, v2 * s_1
        min_x = max(0, int(math.floor(min(x0, x1, x2))) - 1)
        max_x = min(s_1, int(math.ceil(max(x0, x1, x2))) + 1)
        min_y = max(0, int(math.floor(min(y0, y1, y2))) - 1)
        max_y = min(s_1, int(math.ceil(max(y0, y1, y2))) + 1)
        denom = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(denom) < 1e-6:
            for py in range(min_y, max_y + 1):
                row = py * size
                for px in range(min_x, max_x + 1):
                    mask[row + px] = z
            continue
        inv_d = 1.0 / denom
        for py in range(min_y, max_y + 1):
            fy = py + 0.5
            row = py * size
            for px in range(min_x, max_x + 1):
                fx = px + 0.5
                w0 = ((y1 - y2) * (fx - x2) + (x2 - x1) * (fy - y2)) * inv_d
                w1 = ((y2 - y0) * (fx - x2) + (x0 - x2) * (fy - y2)) * inv_d
                w2 = 1.0 - w0 - w1
                if w0 >= -0.05 and w1 >= -0.05 and w2 >= -0.05:
                    mask[row + px] = z
    return mask


def upgrade_geometry_and_build_masks():
    with open(BASE_GLB, "rb") as f:
        buf = f.read()
    jlen, _ = struct.unpack("<II", buf[12:20])
    j = json.loads(buf[20 : 20 + jlen].decode("utf-8"))
    bin_chunk = bytearray(buf[20 + jlen + 8 :])

    def get_acc_slice(acc_idx):
        acc = j["accessors"][acc_idx]
        bv = j["bufferViews"][acc["bufferView"]]
        off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
        return acc, bv, off

    # 1. Normalize Armature (node 67) scale from 0.01 to 1.0 & Rx(+90) into mixamorig:Hips
    s45 = math.sqrt(0.5)

    def qmul_rx90(q):
        x, y, z, w = q
        return [
            s45 * w + s45 * x,
            s45 * y - s45 * z,
            s45 * z + s45 * y,
            s45 * w - s45 * x,
        ]

    arm_node = j["nodes"][67]
    if arm_node.get("scale") and arm_node["scale"][0] < 0.1:
        arm_node.pop("translation", None)
        arm_node.pop("rotation", None)
        arm_node.pop("scale", None)

        for idx in range(65):
            n = j["nodes"][idx]
            t = n.get("translation", [0.0, 0.0, 0.0])
            r = n.get("rotation", [0.0, 0.0, 0.0, 1.0])
            if idx == 64:  # mixamorig:Hips
                n["translation"] = [0.01 * t[0], -0.01 * t[2], 0.01 * t[1]]
                n["rotation"] = qmul_rx90(r)
            else:
                n["translation"] = [0.01 * t[0], 0.01 * t[1], 0.01 * t[2]]
            n["scale"] = [1.0, 1.0, 1.0]

        done_acc = set()
        for anim in j.get("animations", []):
            is_idle = anim.get("name") == "fighting_idle"
            for ch in anim["channels"]:
                node_idx = ch["target"]["node"]
                tpath = ch["target"]["path"]
                out_idx = anim["samplers"][ch["sampler"]]["output"]
                if out_idx in done_acc:
                    continue
                done_acc.add(out_idx)
                acc, bv, off = get_acc_slice(out_idx)
                cnt = acc["count"]
                if tpath == "translation":
                    vals = list(struct.unpack(f"<{cnt * 3}f", bin_chunk[off : off + cnt * 12]))
                    new_vals = []
                    for k in range(cnt):
                        tx, ty, tz = vals[k * 3 : k * 3 + 3]
                        if node_idx == 64:
                            ny = -0.01 * tz + (0.0096 if is_idle else 0.0)
                            new_vals.extend([0.01 * tx, ny, 0.01 * ty])
                        else:
                            new_vals.extend([0.01 * tx, 0.01 * ty, 0.01 * tz])
                    bin_chunk[off : off + cnt * 12] = struct.pack(f"<{cnt * 3}f", *new_vals)
                    acc["min"] = [min(new_vals[i::3]) for i in range(3)]
                    acc["max"] = [max(new_vals[i::3]) for i in range(3)]
                elif tpath == "rotation" and node_idx == 64 and acc["componentType"] == 5126:
                    vals = list(struct.unpack(f"<{cnt * 4}f", bin_chunk[off : off + cnt * 16]))
                    new_vals = []
                    for k in range(cnt):
                        new_vals.extend(qmul_rx90(vals[k * 4 : k * 4 + 4]))
                    bin_chunk[off : off + cnt * 16] = struct.pack(f"<{cnt * 4}f", *new_vals)
                    acc["min"] = [min(new_vals[i::4]) for i in range(4)]
                    acc["max"] = [max(new_vals[i::4]) for i in range(4)]
                elif tpath == "scale":
                    new_vals = [1.0] * (cnt * 3)
                    bin_chunk[off : off + cnt * 12] = struct.pack(f"<{cnt * 3}f", *new_vals)
                    acc["min"] = [1.0, 1.0, 1.0]
                    acc["max"] = [1.0, 1.0, 1.0]

        ibm_acc, ibm_bv, ibm_off = get_acc_slice(j["skins"][0]["inverseBindMatrices"])
        cnt = ibm_acc["count"]
        mats = list(struct.unpack(f"<{cnt * 16}f", bin_chunk[ibm_off : ibm_off + cnt * 64]))
        for k in range(cnt):
            base = k * 16
            for col in range(4):
                mats[base + col * 4 + 0] *= 0.01
                mats[base + col * 4 + 1] *= 0.01
                mats[base + col * 4 + 2] *= 0.01
        bin_chunk[ibm_off : ibm_off + cnt * 64] = struct.pack(f"<{cnt * 16}f", *mats)

    # 2. Extract and upgrade Prim 0, Prim 1, Prim 2 of Mesh 0
    m0 = j["meshes"][0]
    p0, p1, p2 = m0["primitives"][0], m0["primitives"][1], m0["primitives"][2]

    # --- Load Prim 0 ---
    pos0_acc, _, pos0_off = get_acc_slice(p0["attributes"]["POSITION"])
    nor0_acc, _, nor0_off = get_acc_slice(p0["attributes"]["NORMAL"])
    uv0_acc, _, uv0_off = get_acc_slice(p0["attributes"]["TEXCOORD_0"])
    idx0_acc, _, idx0_off = get_acc_slice(p0["indices"])
    vc0 = pos0_acc["count"]
    ic0 = idx0_acc["count"]
    pos0 = list(struct.unpack(f"<{vc0 * 3}f", bin_chunk[pos0_off : pos0_off + vc0 * 12]))
    uv0 = list(struct.unpack(f"<{vc0 * 2}f", bin_chunk[uv0_off : uv0_off + vc0 * 8]))
    idx0 = list(struct.unpack(f"<{ic0}H", bin_chunk[idx0_off : idx0_off + ic0 * 2]))
    comps0, adj0 = find_components(vc0, idx0)

    # Identify spatial neighbors within Prim 0 by rounded position
    pos_to_verts0 = defaultdict(list)
    for v in range(vc0):
        key = (round(pos0[v * 3], 4), round(pos0[v * 3 + 1], 4), round(pos0[v * 3 + 2], 4))
        pos_to_verts0[key].append(v)

    # Unified harmonic smoothing across Prim 0 (suit/collar/yoke/tights/boots) and Prim 1 (torso/sleeves)
    # 1. Identify topological rings d=0..13 of Comp 5 from the 26 inner-neck open vertices
    remove_comps0 = set()
    for ci in (11, 18, 19, 20, 21, 22, 23, 24, 25):
        if ci < len(comps0):
            remove_comps0.update(comps0[ci])

    orig_key0 = {
        v: (round(pos0[v * 3], 3), round(pos0[v * 3 + 1], 3), round(pos0[v * 3 + 2], 3))
        for v in range(vc0)
        if v not in remove_comps0
    }
    edge_cnt5 = defaultdict(int)
    c5_set = set(comps0[5])
    for k in range(0, len(idx0), 3):
        a, b, c = idx0[k], idx0[k + 1], idx0[k + 2]
        if a in c5_set:
            for u, w in ((a, b), (b, c), (c, a)):
                pu, pw = orig_key0[u], orig_key0[w]
                if pu != pw:
                    edge_cnt5[tuple(sorted((pu, pw)))] += 1

    open_pts5 = set()
    for (pu, pw), cnt in edge_cnt5.items():
        if cnt == 1:
            open_pts5.add(pu)
            open_pts5.add(pw)

    sp_adj5 = defaultdict(set)
    for v in comps0[5]:
        kv = orig_key0[v]
        for u in adj0[v]:
            if u in c5_set:
                ku = orig_key0[u]
                if ku != kv:
                    sp_adj5[kv].add(ku)

    start_keys5 = [
        orig_key0[v]
        for v in comps0[5]
        if orig_key0[v] in open_pts5 and math.hypot(pos0[v * 3], pos0[v * 3 + 2] - 0.015) < 0.065
    ]
    dist_key5 = {k: 0 for k in start_keys5}
    q5 = deque(start_keys5)
    while q5:
        k = q5.popleft()
        for nb in sp_adj5[k]:
            if nb not in dist_key5:
                dist_key5[nb] = dist_key5[k] + 1
                q5.append(nb)

    #Parameterize Comp 5 rings d=0..13 as a sleek crew-neck collar sitting cleanly at clavicle level
    d0_verts5 = [v for v in comps0[5] if dist_key5.get(orig_key0[v], 99) == 0]
    d13_verts5 = [v for v in comps0[5] if dist_key5.get(orig_key0[v], 99) >= 12]

    def ang_diff(a, b):
        d = (a - b + math.pi) % (2.0 * math.pi) - math.pi
        return abs(d)

    c5_target_key = {}
    for v in comps0[5]:
        kv = orig_key0[v]
        if kv in c5_target_key:
            continue
        x, y, z = pos0[v * 3], pos0[v * 3 + 1], pos0[v * 3 + 2]
        ang = math.atan2(x, z - 0.015)
        d5 = min(13, dist_key5.get(kv, 13))
        t = d5 / 13.0
        v0 = min(d0_verts5, key=lambda u: ang_diff(math.atan2(pos0[u * 3], pos0[u * 3 + 2] - 0.015), ang))
        v13 = min(d13_verts5, key=lambda u: ang_diff(math.atan2(pos0[u * 3], pos0[u * 3 + 2] - 0.015), ang))
        r0 = math.hypot(pos0[v0 * 3], pos0[v0 * 3 + 2] - 0.015) * 0.95
        y0 = 1.442 - 0.008 * math.cos(ang)
        r13 = math.hypot(pos0[v13 * 3], pos0[v13 * 3 + 2] - 0.015)
        y13 = 1.422 - 0.008 * math.cos(ang)
        nr = r0 + (r13 - r0) * (t ** 1.10)
        ny = y0 + (y13 - y0) * t
        c5_target_key[kv] = [nr * math.sin(ang), ny, 0.015 + nr * math.cos(ang)]

    vert_comp0 = {}
    for ci, comp in enumerate(comps0):
        for v in comp:
            vert_comp0[v] = ci

    new_idx0 = []
    tri_zones0 = []
    for k in range(0, len(idx0), 3):
        a, b, c = idx0[k], idx0[k + 1], idx0[k + 2]
        if a in remove_comps0 or b in remove_comps0 or c in remove_comps0:
            continue
        new_idx0.extend((a, b, c))
        ci = vert_comp0.get(a, 0)
        if ci == 5:
            tri_zones0.append(ZONE_COLLAR_TRIM)
        elif ci in (4, 6, 7, 8, 16, 17):
            tri_zones0.append(ZONE_RASHGUARD_YOKE)
        elif ci in (2, 3):
            tri_zones0.append(ZONE_FIGHT_TIGHTS)
        elif ci in (0, 1, 12, 13):
            tri_zones0.append(ZONE_SHIN_GUARDS)
        else:
            tri_zones0.append(ZONE_WRESTLING_SHOES)

    # --- Load Prim 1 ---
    pos1_acc, _, pos1_off = get_acc_slice(p1["attributes"]["POSITION"])
    nor1_acc, _, nor1_off = get_acc_slice(p1["attributes"]["NORMAL"])
    uv1_acc, _, uv1_off = get_acc_slice(p1["attributes"]["TEXCOORD_0"])
    idx1_acc, _, idx1_off = get_acc_slice(p1["indices"])
    vc1 = pos1_acc["count"]
    ic1 = idx1_acc["count"]
    pos1 = list(struct.unpack(f"<{vc1 * 3}f", bin_chunk[pos1_off : pos1_off + vc1 * 12]))
    uv1 = list(struct.unpack(f"<{vc1 * 2}f", bin_chunk[uv1_off : uv1_off + vc1 * 8]))
    idx1 = list(struct.unpack(f"<{ic1}H", bin_chunk[idx1_off : idx1_off + ic1 * 2]))
    comps1, adj1 = find_components(vc1, idx1)

    # 2b. Unified harmonic smoothing of ONLY the upper torso yoke (Prim 0 Comp 4,5,6,7,8,16,17)
    #     PLUS the upper-chest shelf patch of Prim 1 Comp 1 (y >= 1.315, z >= 0.065, |x| <= 0.105).
    #     Preserves 100% of arm, shoulder, waist, hip, and leg volume while erasing the chest shelf & back hump!
    yoke0_set = set()
    for ci in (4, 5, 6, 7, 8, 16, 17):
        yoke0_set.update(comps0[ci])
    chest1_set = {
        v
        for v in comps1[1]
        if pos1[v * 3 + 1] >= 1.312 and pos1[v * 3 + 2] >= 0.060 and abs(pos1[v * 3]) <= 0.105
    }
    orig_key1_chest = {
        v: (round(pos1[v * 3], 3), round(pos1[v * 3 + 1], 3), round(pos1[v * 3 + 2], 3)) for v in chest1_set
    }

    edge_cnt_yoke = defaultdict(int)
    sp_adj_yoke = defaultdict(set)
    for k in range(0, len(idx0), 3):
        a, b, c = idx0[k], idx0[k + 1], idx0[k + 2]
        if a in yoke0_set:
            for u, w in ((a, b), (b, c), (c, a)):
                pu, pw = orig_key0[u], orig_key0[w]
                if pu != pw:
                    edge_cnt_yoke[tuple(sorted((pu, pw)))] += 1
                    sp_adj_yoke[pu].add(pw)
                    sp_adj_yoke[pw].add(pu)

    for k in range(0, len(idx1), 3):
        a, b, c = idx1[k], idx1[k + 1], idx1[k + 2]
        if a in chest1_set and b in chest1_set and c in chest1_set:
            for u, w in ((a, b), (b, c), (c, a)):
                pu, pw = orig_key1_chest[u], orig_key1_chest[w]
                if pu != pw:
                    edge_cnt_yoke[tuple(sorted((pu, pw)))] += 1
                    sp_adj_yoke[pu].add(pw)
                    sp_adj_yoke[pw].add(pu)

    open_pts_yoke = set()
    for (pu, pw), cnt in edge_cnt_yoke.items():
        if cnt == 1:
            open_pts_yoke.add(pu)
            open_pts_yoke.add(pw)

    c4_set = set(comps0[4])
    key_pos_yoke = {}
    locked_yoke = set()
    for v in yoke0_set:
        kv = orig_key0[v]
        x, y, z = pos0[v * 3], pos0[v * 3 + 1], pos0[v * 3 + 2]
        if kv in c5_target_key:
            key_pos_yoke[kv] = c5_target_key[kv]
            if dist_key5.get(kv, 13) <= 2:
                locked_yoke.add(kv)
        elif kv in open_pts_yoke:
            locked_yoke.add(kv)
            key_pos_yoke[kv] = [x, y, z]
        else:
            ny = min(y, 1.422)
            nz = (-0.086 + (z - (-0.086)) * 0.14) if (v in c4_set and z < -0.086) else z
            key_pos_yoke[kv] = [x, ny, nz]

    for v in chest1_set:
        kv = orig_key1_chest[v]
        if kv in key_pos_yoke:
            continue
        x, y, z = pos1[v * 3], pos1[v * 3 + 1], pos1[v * 3 + 2]
        if kv in open_pts_yoke:
            locked_yoke.add(kv)
        key_pos_yoke[kv] = [x, y, z]

    for _ in range(90):
        next_pos_yoke = {}
        for k, p in key_pos_yoke.items():
            if k in locked_yoke or not sp_adj_yoke[k]:
                next_pos_yoke[k] = p
            else:
                nbrs = sp_adj_yoke[k]
                nx = sum(key_pos_yoke[nb][0] for nb in nbrs) / len(nbrs)
                ny = sum(key_pos_yoke[nb][1] for nb in nbrs) / len(nbrs)
                nz = sum(key_pos_yoke[nb][2] for nb in nbrs) / len(nbrs)
                next_pos_yoke[k] = [nx, ny, nz]
        key_pos_yoke = next_pos_yoke

    for v in yoke0_set:
        pos0[v * 3 : v * 3 + 3] = key_pos_yoke[orig_key0[v]]
    for v in chest1_set:
        pos1[v * 3 : v * 3 + 3] = key_pos_yoke[orig_key1_chest[v]]

    # 3. Anatomical 3D Resculpting of Head & Neck (Comp 0 in Prim 1)
    #    First compute topological ring distance d_neck from the 30 open bottom-neck vertices
    c0_set = set(comps1[0])
    key1_c0 = {
        v: (round(pos1[v * 3], 4), round(pos1[v * 3 + 1], 4), round(pos1[v * 3 + 2], 4)) for v in c0_set
    }
    ec_c0 = defaultdict(int)
    sp_adj_c0 = defaultdict(set)
    for k in range(0, len(idx1), 3):
        a, b, c = idx1[k], idx1[k + 1], idx1[k + 2]
        if a in c0_set:
            for u, w in ((a, b), (b, c), (c, a)):
                ku, kw = key1_c0[u], key1_c0[w]
                if ku != kw:
                    ec_c0[tuple(sorted((ku, kw)))] += 1
                    sp_adj_c0[ku].add(kw)
                    sp_adj_c0[kw].add(ku)

    open_neck_c0 = set()
    for (ku, kw), cnt in ec_c0.items():
        if cnt == 1:
            if ku[1] < 1.51:
                open_neck_c0.add(ku)
            if kw[1] < 1.51:
                open_neck_c0.add(kw)

    dist_neck = {k: 0 for k in open_neck_c0}
    q_neck = deque(open_neck_c0)
    while q_neck:
        k = q_neck.popleft()
        for nb in sp_adj_c0[k]:
            if nb not in dist_neck:
                dist_neck[nb] = dist_neck[k] + 1
                q_neck.append(nb)

    def smoothstep(e0, e1, x):
        t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
        return t * t * (3.0 - 2.0 * t)

    def gauss(x, mu, sigma):
        return math.exp(-0.5 * ((x - mu) / sigma) ** 2)

    for v in comps1[0]:
        x, y, z = pos1[v * 3], pos1[v * 3 + 1], pos1[v * 3 + 2]
        orig_y = y
        ax = abs(x)
        dn = dist_neck.get(key1_c0[v], 99)
        if dn <= 4:
            # Smoothly extend cylindrical neck rings d=0..4 down into the crew-neck collar opening (Comp 5)
            # without touching the submental chin (which has dn >= 6)
            drop_map = {0: 0.048, 1: 0.034, 2: 0.020, 3: 0.009, 4: 0.003}
            flare_map = {0: 1.120, 1: 1.075, 2: 1.040, 3: 1.018, 4: 1.005}
            y -= drop_map[dn]
            fl = flare_map[dn]
            x *= fl
            z = 0.015 + (z - 0.015) * fl

        w_head = smoothstep(1.488, 1.502, orig_y) if dn > 3 else 0.0
        if w_head > 0.0:
            # A. Mental protuberance (chin) & mandibular jaw structure: fix recessed anime V-chin
            w_chin_y = gauss(y, 1.502, 0.011) * smoothstep(0.065, 0.098, z)
            z += w_head * w_chin_y * 0.0052 * gauss(ax, 0.0, 0.022)
            x *= 1.0 + w_head * gauss(y, 1.508, 0.016) * smoothstep(0.04, 0.09, z) * 0.14

            # Mandibular angle (gonial jaw width)
            w_jaw = gauss(y, 1.526, 0.018) * gauss(ax, 0.048, 0.018) * smoothstep(0.01, 0.06, z)
            x *= 1.0 + w_head * w_jaw * 0.085

            # B. Zygomatic arch / malar cheekbone prominence & subtle buccal contour
            w_cheek = gauss(y, 1.576, 0.014) * gauss(ax, 0.046, 0.016) * smoothstep(0.05, 0.09, z)
            x += math.copysign(w_head * w_cheek * 0.0020, x)
            z += w_head * w_cheek * 0.0022

            w_buccal = gauss(y, 1.544, 0.012) * gauss(ax, 0.042, 0.012) * smoothstep(0.06, 0.10, z)
            x -= math.copysign(w_head * w_buccal * 0.0012, x)

            # C. Supraorbital brow ridge: lower exaggerated cartoon brow arch & add realistic brow bone depth
            w_brow = gauss(y, 1.613, 0.009) * smoothstep(0.085, 0.112, z) * smoothstep(0.055, 0.010, ax)
            z += w_head * w_brow * 0.0022
            y -= w_head * gauss(y, 1.615, 0.010) * gauss(ax, 0.034, 0.014) * smoothstep(0.085, 0.110, z) * 0.0022

            # D. Palpebral fissure (eyelid opening): reduce vertical anime doe-eye height by 12% toward Y=1.5950
            w_eye = gauss(y, 1.5950, 0.011) * gauss(ax, 0.030, 0.014) * smoothstep(0.095, 0.108, z)
            y = 1.5950 + (y - 1.5950) * (1.0 - 0.12 * w_eye)

            # E. Nasal bridge dorsum & alar refinement
            w_bridge = gauss(y, 1.586, 0.010) * gauss(ax, 0.0, 0.009) * smoothstep(0.110, 0.125, z)
            z += w_head * w_bridge * 0.0018
            w_alar = gauss(y, 1.566, 0.008) * gauss(ax, 0.016, 0.007) * smoothstep(0.115, 0.132, z)
            x *= 1.0 - w_head * w_alar * 0.05

            # F. Lip vermilion refinement (reduce exaggerated cartoon pout)
            w_lip = gauss(y, 1.5435, 0.009) * gauss(ax, 0.0, 0.022) * smoothstep(0.118, 0.130, z)
            z -= w_head * w_lip * 0.0016
            y = 1.5435 + (y - 1.5435) * (1.0 - 0.07 * w_lip)

        pos1[v * 3], pos1[v * 3 + 1], pos1[v * 3 + 2] = x, y, z

    # Rotate eyeballs (Comp 6 & 7) slightly outward (3.2 deg) so corneal apex points straight forward (+Z)
    for ci, sign in ((6, 1.0), (7, -1.0)):
        cx_eye = sign * 0.0285
        cz_eye = 0.1015
        ang = sign * math.radians(3.2)
        ca, sa = math.cos(ang), math.sin(ang)
        for v in comps1[ci]:
            dx = pos1[v * 3] - cx_eye
            dz = pos1[v * 3 + 2] - cz_eye
            pos1[v * 3] = cx_eye + dx * ca + dz * sa
            pos1[v * 3 + 2] = cz_eye - dx * sa + dz * ca

    # Refine Eyelash Cards (Prim 2) to match the 12% narrower eye aperture & eliminate outer winged spikes
    pos2_acc, _, pos2_off = get_acc_slice(p2["attributes"]["POSITION"])
    vc2 = pos2_acc["count"]
    pos2 = list(struct.unpack(f"<{vc2 * 3}f", bin_chunk[pos2_off : pos2_off + vc2 * 12]))
    for v in range(vc2):
        x, y, z = pos2[v * 3], pos2[v * 3 + 1], pos2[v * 3 + 2]
        ax = abs(x)
        y = 1.5950 + (y - 1.5950) * 0.86
        # Pull in the lateral winged eyelash spike (|X| > 0.038)
        if ax > 0.038:
            excess = ax - 0.038
            new_ax = 0.038 + excess * 0.42
            x = math.copysign(new_ax, x)
            y -= excess * 0.28
            z -= excess * 0.25
        pos2[v * 3], pos2[v * 3 + 1], pos2[v * 3 + 2] = x, y, z

    # Recompute and weld normals across Prim 0 and Prim 1
    nor0 = recompute_normals(vc0, pos0, new_idx0)
    nor1 = recompute_normals(vc1, pos1, idx1)
    weld_spatial_normals([pos0, pos1], [nor0, nor1])

    # Write updated positions & normals into bin_chunk
    bin_chunk[pos0_off : pos0_off + vc0 * 12] = struct.pack(f"<{vc0 * 3}f", *pos0)
    bin_chunk[nor0_off : nor0_off + vc0 * 12] = struct.pack(f"<{vc0 * 3}f", *nor0)
    pos0_acc["min"] = [min(pos0[i::3]) for i in range(3)]
    pos0_acc["max"] = [max(pos0[i::3]) for i in range(3)]

    bin_chunk[pos1_off : pos1_off + vc1 * 12] = struct.pack(f"<{vc1 * 3}f", *pos1)
    bin_chunk[nor1_off : nor1_off + vc1 * 12] = struct.pack(f"<{vc1 * 3}f", *nor1)
    pos1_acc["min"] = [min(pos1[i::3]) for i in range(3)]
    pos1_acc["max"] = [max(pos1[i::3]) for i in range(3)]

    bin_chunk[pos2_off : pos2_off + vc2 * 12] = struct.pack(f"<{vc2 * 3}f", *pos2)
    pos2_acc["min"] = [min(pos2[i::3]) for i in range(3)]
    pos2_acc["max"] = [max(pos2[i::3]) for i in range(3)]

    # Update Prim 0 index buffer with removed floating sci-fi pods
    bin_chunk[idx0_off : idx0_off + len(new_idx0) * 2] = struct.pack(f"<{len(new_idx0)}H", *new_idx0)
    idx0_acc["count"] = len(new_idx0)
    idx0_acc["min"] = [min(new_idx0)]
    idx0_acc["max"] = [max(new_idx0)]

    # Build triangle zone list for Prim 1 (and split Prim 1 indices into Skin, Eyes, UpperGear)
    vert_comp1 = {}
    for ci, comp in enumerate(comps1):
        for v in comp:
            vert_comp1[v] = ci

    idx1_skin = []
    idx1_eyes = []
    idx1_gear = []
    tri_zones1 = []

    for k in range(0, len(idx1), 3):
        a, b, c = idx1[k], idx1[k + 1], idx1[k + 2]
        ci = vert_comp1.get(a, 0)
        if ci == 0:
            idx1_skin.extend((a, b, c))
            tri_zones1.append(ZONE_SKIN_HEAD_NECK)
        elif ci == 8:
            idx1_skin.extend((a, b, c))
            tri_zones1.append(ZONE_TEETH)
        elif ci == 6:
            idx1_eyes.extend((a, b, c))
            tri_zones1.append(ZONE_EYEBALL_LEFT)
        elif ci == 7:
            idx1_eyes.extend((a, b, c))
            tri_zones1.append(ZONE_EYEBALL_RIGHT)
        elif ci in (9, 10):
            idx1_eyes.extend((a, b, c))
            tri_zones1.append(ZONE_EYE_CARUNCLE)
        elif ci in (2, 3):
            # Hands: classify by average |X| into Fingers, Leather MMA Glove, and Wrist Wrap
            ax_avg = (abs(pos1[a * 3]) + abs(pos1[b * 3]) + abs(pos1[c * 3])) / 3.0
            if ax_avg >= 0.716:
                idx1_skin.extend((a, b, c))
                tri_zones1.append(ZONE_HAND_FINGERS)
            elif ax_avg >= 0.632:
                idx1_gear.extend((a, b, c))
                tri_zones1.append(ZONE_HAND_GLOVE)
            else:
                idx1_gear.extend((a, b, c))
                tri_zones1.append(ZONE_HAND_WRAP)
        else:
            idx1_gear.extend((a, b, c))
            tri_zones1.append(ZONE_RASHGUARD_UPPER)

    # Rasterize 4096x4096 UV masks for 1001 and 1002
    print("[mask] Rasterizing 4096x4096 UV zone masks from 3D triangles...")
    mask1001 = rasterize_uv_mask(uv1, idx1, tri_zones1, 4096)
    mask1002 = rasterize_uv_mask(uv0, new_idx0, tri_zones0, 4096)
    mask1001_path = os.path.join(WORK_DIR, "mask_1001.bin")
    mask1002_path = os.path.join(WORK_DIR, "mask_1002.bin")
    with open(mask1001_path, "wb") as f:
        f.write(mask1001)
    with open(mask1002_path, "wb") as f:
        f.write(mask1002)

    return j, bin_chunk, (idx1_skin, idx1_eyes, idx1_gear), mask1001_path, mask1002_path


def build_and_run_c_texture_engine(extracted, mask1001_path, mask1002_path):
    c_src = os.path.join(WORK_DIR, "process_textures.c")
    c_bin = os.path.join(WORK_DIR, "process_textures")
    with open(c_src, "w") as f:
        f.write(r"""
#include <CoreGraphics/CoreGraphics.h>
#include <ImageIO/ImageIO.h>
#include <CoreFoundation/CoreFoundation.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>

#define ZONE_NONE 0
#define ZONE_SKIN_HEAD_NECK 1
#define ZONE_EYEBALL_LEFT 2
#define ZONE_EYEBALL_RIGHT 3
#define ZONE_EYE_CARUNCLE 4
#define ZONE_TEETH 5
#define ZONE_HAND_FINGERS 6
#define ZONE_HAND_GLOVE 7
#define ZONE_HAND_WRAP 8
#define ZONE_RASHGUARD_UPPER 9

#define ZONE_NECK_SKIN_LOWER 10
#define ZONE_COLLAR_TRIM 11
#define ZONE_RASHGUARD_YOKE 12
#define ZONE_FIGHT_TIGHTS 13
#define ZONE_SHIN_GUARDS 14
#define ZONE_WRESTLING_SHOES 15

static float clampf(float x, float lo, float hi) {
    return x < lo ? lo : (x > hi ? hi : x);
}

static float smoothstep(float e0, float e1, float x) {
    float t = clampf((x - e0) / (e1 - e0), 0.0f, 1.0f);
    return t * t * (3.0f - 2.0f * t);
}

static float hash2d(int x, int y) {
    uint32_t h = (uint32_t)(x * 374761393U + y * 668265263U);
    h = (h ^ (h >> 13)) * 1274126177U;
    return (float)(h & 0x00FFFFFFU) / 16777215.0f;
}

static float value_noise(float x, float y) {
    int ix = (int)floorf(x), iy = (int)floorf(y);
    float fx = x - ix, fy = y - iy;
    float u = fx * fx * (3.0f - 2.0f * fx);
    float v = fy * fy * (3.0f - 2.0f * fy);
    float n00 = hash2d(ix, iy), n10 = hash2d(ix + 1, iy);
    float n01 = hash2d(ix, iy + 1), n11 = hash2d(ix + 1, iy + 1);
    return (n00 * (1.0f - u) + n10 * u) * (1.0f - v) + (n01 * (1.0f - u) + n11 * u) * v;
}

static float fbm_pores(float x, float y) {
    float v1 = value_noise(x, y);
    float v2 = value_noise(x * 2.13f + 17.3f, y * 2.13f + 31.7f);
    float v3 = value_noise(x * 4.27f + 53.1f, y * 4.27f + 11.9f);
    return 0.50f * v1 + 0.32f * v2 + 0.18f * v3;
}

static void dilate_mask(uint8_t *mask, int size, int passes) {
    uint8_t *tmp = (uint8_t *)malloc((size_t)size * size);
    for (int p = 0; p < passes; p++) {
        memcpy(tmp, mask, (size_t)size * size);
        for (int y = 1; y < size - 1; y++) {
            int row = y * size;
            for (int x = 1; x < size - 1; x++) {
                if (tmp[row + x] != 0) continue;
                uint8_t z = tmp[row + x - 1];
                if (!z) z = tmp[row + x + 1];
                if (!z) z = tmp[row - size + x];
                if (!z) z = tmp[row + size + x];
                if (z) mask[row + x] = z;
            }
        }
    }
    free(tmp);
}

static uint8_t *load_image_rgba(const char *path, int target_w, int target_h) {
    CFStringRef cf_path = CFStringCreateWithCString(NULL, path, kCFStringEncodingUTF8);
    CFURLRef url = CFURLCreateWithFileSystemPath(NULL, cf_path, kCFURLPOSIXPathStyle, false);
    CFRelease(cf_path);
    CGImageSourceRef src = CGImageSourceCreateWithURL(url, NULL);
    CFRelease(url);
    if (!src) return NULL;
    CGImageRef img = CGImageSourceCreateImageAtIndex(src, 0, NULL);
    CFRelease(src);
    if (!img) return NULL;

    uint8_t *raw = (uint8_t *)calloc((size_t)target_w * target_h * 4, 1);
    CGColorSpaceRef cs = CGColorSpaceCreateDeviceRGB();
    CGContextRef ctx = CGBitmapContextCreate(raw, target_w, target_h, 8, target_w * 4, cs, kCGImageAlphaPremultipliedLast);
    CGContextSetInterpolationQuality(ctx, kCGInterpolationHigh);
    CGContextDrawImage(ctx, CGRectMake(0, 0, target_w, target_h), img);
    CGContextRelease(ctx);
    CGColorSpaceRelease(cs);
    CGImageRelease(img);
    return raw;
}

static void save_image_rgba(const char *path, uint8_t *raw, int w, int h) {
    CGColorSpaceRef cs = CGColorSpaceCreateDeviceRGB();
    CGContextRef ctx = CGBitmapContextCreate(raw, w, h, 8, w * 4, cs, kCGImageAlphaPremultipliedLast);
    CGImageRef img = CGBitmapContextCreateImage(ctx);
    CFStringRef cf_path = CFStringCreateWithCString(NULL, path, kCFStringEncodingUTF8);
    CFURLRef url = CFURLCreateWithFileSystemPath(NULL, cf_path, kCFURLPOSIXPathStyle, false);
    CFRelease(cf_path);
    CGImageDestinationRef dest = CGImageDestinationCreateWithURL(url, CFSTR("public.png"), 1, NULL);
    CGImageDestinationAddImage(dest, img, NULL);
    CGImageDestinationFinalize(dest);
    CFRelease(dest);
    CFRelease(url);
    CGImageRelease(img);
    CGContextRelease(ctx);
    CGColorSpaceRelease(cs);
}

static float *compute_blurred_lum(const uint8_t *raw, int w, int h, int radius) {
    double *sat = (double *)calloc((size_t)(w + 1) * (h + 1), sizeof(double));
    for (int y = 0; y < h; y++) {
        double row_sum = 0.0;
        for (int x = 0; x < w; x++) {
            const uint8_t *p = raw + ((size_t)y * w + x) * 4;
            double lum = (0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]) / 255.0;
            row_sum += lum;
            sat[(size_t)(y + 1) * (w + 1) + (x + 1)] = sat[(size_t)y * (w + 1) + (x + 1)] + row_sum;
        }
    }
    float *out = (float *)malloc((size_t)w * h * sizeof(float));
    for (int y = 0; y < h; y++) {
        int y0 = y - radius < 0 ? 0 : y - radius;
        int y1 = y + radius >= h ? h - 1 : y + radius;
        for (int x = 0; x < w; x++) {
            int x0 = x - radius < 0 ? 0 : x - radius;
            int x1 = x + radius >= w ? w - 1 : x + radius;
            double sum = sat[(size_t)(y1 + 1) * (w + 1) + (x1 + 1)]
                       - sat[(size_t)y0 * (w + 1) + (x1 + 1)]
                       - sat[(size_t)(y1 + 1) * (w + 1) + x0]
                       + sat[(size_t)y0 * (w + 1) + x0];
            out[(size_t)y * w + x] = (float)(sum / ((x1 - x0 + 1) * (y1 - y0 + 1)));
        }
    }
    free(sat);
    return out;
}

int main(int argc, char **argv) {
    const char *work_dir = argv[1];
    char path[1024];

    // Load 4096x4096 UV zone masks and dilate by 20px into UV gutters
    uint8_t *mask1001 = (uint8_t *)malloc(4096 * 4096);
    uint8_t *mask1002 = (uint8_t *)malloc(4096 * 4096);
    snprintf(path, sizeof(path), "%s/mask_1001.bin", work_dir);
    FILE *fm1 = fopen(path, "rb"); fread(mask1001, 1, 4096 * 4096, fm1); fclose(fm1);
    snprintf(path, sizeof(path), "%s/mask_1002.bin", work_dir);
    FILE *fm2 = fopen(path, "rb"); fread(mask1002, 1, 4096 * 4096, fm2); fclose(fm2);
    dilate_mask(mask1001, 4096, 20);
    dilate_mask(mask1002, 4096, 20);

    // =========================================================================
    // 1. Process Ch48_1001_Diffuse (4096x4096)
    // =========================================================================
    snprintf(path, sizeof(path), "%s/Ch48_1001_Diffuse.png", work_dir);
    uint8_t *d1001 = load_image_rgba(path, 4096, 4096);
    float *blur1001 = compute_blurred_lum(d1001, 4096, 4096, 48);

    for (int py = 0; py < 4096; py++) {
        float v = (float)py / 4096.0f;
        for (int px = 0; px < 4096; px++) {
            float u = (float)px / 4096.0f;
            size_t idx = (size_t)py * 4096 + px;
            uint8_t z = mask1001[idx];
            uint8_t *p = d1001 + idx * 4;
            float r = p[0], g = p[1], b = p[2];

            // Fallback zone detection for UV gutter regions outside dilated mask
            if (z == ZONE_NONE) {
                if (u >= 0.830f && u <= 0.985f && v >= 0.275f && v <= 0.352f) {
                    z = (u >= 0.908f) ? ZONE_EYEBALL_LEFT : ZONE_EYEBALL_RIGHT;
                } else if (u >= 0.963f && u <= 0.992f && v >= 0.193f && v <= 0.250f) {
                    z = ZONE_EYE_CARUNCLE;
                } else if (u >= 0.476f && v <= 0.278f) {
                    z = ZONE_SKIN_HEAD_NECK;
                } else {
                    z = ZONE_RASHGUARD_UPPER;
                }
            }

            if (z == ZONE_EYEBALL_LEFT || z == ZONE_EYEBALL_RIGHT) {
                // Exact straight-ahead gaze iris centers aligned with 3D eyelid opening (X = +/-0.0305)
                float cx = (z == ZONE_EYEBALL_LEFT) ? 0.9462f : 0.8686f;
                float cy = 0.3130f;
                float irisR = 0.0144f;
                float pupilR = 0.0047f;
                float dx = u - cx, dy = v - cy;
                float dist = sqrtf(dx * dx + dy * dy);

                if (dist < pupilR) {
                    float edge = smoothstep(pupilR * 0.80f, pupilR, dist);
                    r = 4.0f * (1.0f - edge) + 26.0f * edge;
                    g = 4.0f * (1.0f - edge) + 16.0f * edge;
                    b = 5.0f * (1.0f - edge) + 10.0f * edge;
                } else if (dist < irisR) {
                    float t = (dist - pupilR) / (irisR - pupilR);
                    float ang = atan2f(dy, dx);
                    float f1 = sinf(ang * 52.0f + sinf(t * 9.0f) * 1.4f);
                    float f2 = cosf(ang * 29.0f - cosf(t * 13.0f));
                    float fibers = 0.5f + 0.32f * f1 + 0.18f * f2;
                    float collarette = expf(-powf((t - 0.30f) / 0.16f, 2.0f));
                    float limbal = smoothstep(0.70f, 0.98f, t);

                    // Rich photorealistic warm hazel-chestnut iris stroma
                    float ir = 64.0f + 46.0f * fibers + 34.0f * collarette;
                    float ig = 38.0f + 28.0f * fibers + 20.0f * collarette;
                    float ib = 18.0f + 13.0f * fibers + 8.0f * collarette;

                    ir = ir * (1.0f - 0.82f * limbal) + 12.0f * (0.82f * limbal);
                    ig = ig * (1.0f - 0.82f * limbal) + 8.0f * (0.82f * limbal);
                    ib = ib * (1.0f - 0.82f * limbal) + 7.0f * (0.82f * limbal);

                    // Upper eyelid ambient occlusion shadow across top of iris
                    float lid_ao = 1.0f - 0.28f * smoothstep(cy - 0.002f, cy - 0.011f, v);
                    r = ir * lid_ao; g = ig * lid_ao; b = ib * lid_ao;
                } else {
                    // Natural off-white human sclera preserving subtle original capillary veins
                    float orig_vein = clampf((r - g) / 45.0f, 0.0f, 1.0f);
                    float lid_ao = 1.0f - 0.22f * smoothstep(cy - 0.001f, cy - 0.015f, v);
                    float corner_pink = smoothstep(0.014f, 0.028f, dist - irisR);
                    r = (232.0f - 18.0f * corner_pink + 6.0f * orig_vein) * lid_ao;
                    g = (224.0f - 34.0f * corner_pink - 4.0f * orig_vein) * lid_ao;
                    b = (218.0f - 38.0f * corner_pink - 5.0f * orig_vein) * lid_ao;
                }
            } else if (z == ZONE_EYE_CARUNCLE) {
                // Moist mucosal pink-coral lacrimal caruncle (tear duct)
                float n = fbm_pores(u * 400.0f, v * 400.0f);
                r = 188.0f + 14.0f * n;
                g = 108.0f + 10.0f * n;
                b = 102.0f + 8.0f * n;
            } else if (z == ZONE_SKIN_HEAD_NECK) {
                // 1. Seamlessly remove cyan & black winged eyeliner around both eyes (strictly below eyebrow ridge v >= 0.1200)
                float ex_c = (u < 0.721f) ? 0.6834f : 0.7583f;
                float ey_c = 0.1339f;
                float edx = (u - ex_c) / 0.0124f;
                float edy = (v - ey_c) / 0.0108f;
                float ell = sqrtf(edx * edx + edy * edy);
                if (u >= 0.646f && u <= 0.796f && v >= 0.1195f && v <= 0.148f) {
                    float lum_px = 0.299f * r + 0.587f * g + 0.114f * b;
                    float w_cyan = smoothstep(-8.0f, 4.0f, fmaxf(b - r, g - r));
                    float w_wing = smoothstep(0.95f, 1.12f, ell) * smoothstep(2.45f, 1.80f, ell) * smoothstep(148.0f, 118.0f, lum_px);
                    float w_clean = clampf(fmaxf(w_cyan, w_wing), 0.0f, 1.0f) * smoothstep(0.1195f, 0.1220f, v);
                    if (w_clean > 0.0f) {
                        float crease = expf(-powf((v - 0.1230f) / 0.0024f, 2.0f)) * smoothstep(1.75f, 0.80f, ell);
                        float lash_margin = expf(-powf((ell - 0.96f) / 0.075f, 2.0f)) * smoothstep(1.10f, 0.70f, fabsf(edx));
                        float rl = 184.0f - 16.0f * crease - 26.0f * lash_margin;
                        float gl = 136.0f - 14.0f * crease - 22.0f * lash_margin;
                        float bl = 124.0f - 12.0f * crease - 20.0f * lash_margin;
                        r = r * (1.0f - w_clean) + rl * w_clean;
                        g = g * (1.0f - w_clean) + gl * w_clean;
                        b = b * (1.0f - w_clean) + bl * w_clean;
                    }
                }

                // 2. Transform dark goth lipstick into natural human rose-terracotta vermilion lips
                if (u >= 0.695f && u <= 0.748f && v >= 0.172f && v <= 0.205f) {
                    float l_dx = (u - 0.7214f) / 0.023f;
                    float l_dy = (v - 0.1890f) / 0.014f;
                    float l_r = sqrtf(l_dx * l_dx + l_dy * l_dy);
                    if (l_r < 1.05f && (r < 165.0f && g < 115.0f)) {
                        // Keep the thin inner oral parting line (v in [0.190, 0.197]) softly shaded
                        float inner_mouth = expf(-powf((v - 0.1938f) / 0.0028f, 2.0f)) * smoothstep(0.85f, 0.3f, fabsf(l_dx));
                        float striae = sinf(u * 2600.0f + sinf(v * 400.0f) * 2.5f) * 3.5f;
                        float lip_w = smoothstep(1.05f, 0.65f, l_r);
                        float vr = (176.0f + striae) * (1.0f - 0.68f * inner_mouth);
                        float vg = (104.0f + striae * 0.6f) * (1.0f - 0.72f * inner_mouth);
                        float vb = (95.0f + striae * 0.5f) * (1.0f - 0.72f * inner_mouth);
                        r = r * (1.0f - lip_w) + vr * lip_w;
                        g = g * (1.0f - lip_w) + vg * lip_w;
                        b = b * (1.0f - lip_w) + vb * lip_w;
                    }
                }

                // 3. Harmonize forehead/scalp chromophores so overhead key light matches cheek complexion
                float b_lum = fmaxf(0.25f, blur1001[idx]);
                float lum_cur = 0.299f * r + 0.587f * g + 0.114f * b;
                float hf = clampf((lum_cur - b_lum * 255.0f) * 1.35f, -14.0f, 14.0f);
                float fh_weight = smoothstep(0.124f, 0.096f, v) * smoothstep(0.61f, 0.66f, u) * smoothstep(0.83f, 0.78f, u);
                if (fh_weight > 0.0f) {
                    float temple_ao = 1.0f - 0.10f * smoothstep(0.020f, 0.052f, fabsf(u - 0.721f));
                    float scalp_ao = 1.0f - 0.14f * smoothstep(0.082f, 0.054f, v);
                    float env_fh = temple_ao * scalp_ao;
                    float r_fh = 166.0f * env_fh + hf;
                    float g_fh = 116.0f * env_fh + hf * 0.80f;
                    float b_fh = 98.0f * env_fh + hf * 0.70f;
                    r = r * (1.0f - fh_weight) + r_fh * fh_weight;
                    g = g * (1.0f - fh_weight) + g_fh * fh_weight;
                    b = b * (1.0f - fh_weight) + b_fh * fh_weight;
                }

                // 4. Enhance natural directional micro-hair eyebrows along exact 3D brow ridge (v in [0.106, 0.119])
                float du_brow = fabsf(u - 0.72085f);
                if (du_brow >= 0.011f && du_brow <= 0.056f && v >= 0.105f && v <= 0.120f) {
                    float bx_c = (u < 0.72085f) ? 0.684f : 0.758f;
                    float t_arch = clampf((du_brow - 0.012f) / 0.043f, 0.0f, 1.0f);
                    float by_c = 0.1150f - 0.0044f * sinf(t_arch * 3.14159f);
                    float b_dx = (du_brow - 0.0335f) / 0.0215f;
                    float b_dy = (v - by_c) / 0.0034f;
                    if (fabsf(b_dx) < 1.05f && fabsf(b_dy) < 1.15f) {
                        float env = smoothstep(1.05f, 0.35f, fabsf(b_dx)) * expf(-b_dy * b_dy * 1.8f);
                        float hair_u = (u - bx_c) * 2200.0f + (v - by_c) * 1100.0f;
                        float strands = 0.5f + 0.5f * sinf(hair_u) * cosf(hair_u * 0.67f + v * 700.0f);
                        float h_alpha = env * (0.45f + 0.45f * strands);
                        r = r * (1.0f - h_alpha) + 34.0f * h_alpha;
                        g = g * (1.0f - h_alpha) + 24.0f * h_alpha;
                        b = b * (1.0f - h_alpha) + 20.0f * h_alpha;
                    }
                }

                // 5. Physiological chromophore zones (hemoglobin warmth, subtle melanin pores, forehead micro-lines)
                float micro = (r + g + b) / 3.0f;
                float pore_n = fbm_pores(u * 1550.0f, v * 1550.0f) - 0.5f;
                float malar = expf(-powf((v - 0.156f) / 0.026f, 2.0f)) * expf(-powf((fabsf(u - 0.721f) - 0.036f) / 0.034f, 2.0f));
                float frontalis = (v >= 0.070f && v <= 0.104f && u >= 0.66f && u <= 0.78f)
                    ? (sinf(v * 1900.0f + fbm_pores(u * 300.0f, v * 300.0f) * 3.0f) * 1.8f)
                    : 0.0f;

                r = r * 0.96f + 4.0f + 7.5f * malar + pore_n * 4.2f + frontalis + (r - micro) * 0.14f;
                g = g * 0.88f - 2.0f - 2.0f * malar + pore_n * 3.2f + frontalis * 0.8f;
                b = b * 0.81f - 6.0f - 3.5f * malar + pore_n * 2.6f + frontalis * 0.7f;
            } else if (z == ZONE_HAND_FINGERS) {
                // Bare human fingers protruding from open-finger MMA leather gloves
                float min_c = fminf(r, fminf(g, b));
                if (min_c > 108.0f) {
                    // Convert original white finger texture into realistic warm human finger skin
                    float shade = clampf(blur1001[idx] / 0.68f, 0.78f, 1.08f);
                    float crease = (fbm_pores(u * 900.0f, v * 900.0f) - 0.5f) * 4.5f;
                    r = 186.0f * shade + crease;
                    g = 136.0f * shade + crease * 0.8f;
                    b = 116.0f * shade + crease * 0.7f;
                } else {
                    // Black leather open-finger glove piping edge
                    float pebble = (fbm_pores(u * 750.0f, v * 750.0f) - 0.5f) * 4.0f;
                    r = 24.0f + pebble; g = 26.0f + pebble; b = 30.0f + pebble;
                }
            } else if (z == ZONE_HAND_GLOVE) {
                // Matte black pebbled cowhide leather MMA open-finger glove (erasing [o o o] sci-fi badge & circles!)
                float fold = 0.92f + 0.14f * clampf(blur1001[idx] / 0.50f, 0.0f, 1.0f);
                float pebble = (fbm_pores(u * 820.0f, v * 820.0f) - 0.5f) * 4.5f;
                r = 25.0f * fold + pebble;
                g = 27.0f * fold + pebble;
                b = 32.0f * fold + pebble;
            } else if (z == ZONE_HAND_WRAP) {
                // Woven dark crimson-charcoal Muay Thai / MMA cotton wrist wraps
                float wrap_rib = 1.0f + 0.06f * sinf(v * 950.0f + u * 120.0f);
                float shade = 0.90f + 0.16f * clampf(blur1001[idx] / 0.50f, 0.0f, 1.0f);
                r = 68.0f * shade * wrap_rib;
                g = 24.0f * shade * wrap_rib;
                b = 28.0f * shade * wrap_rib;
            } else if (z == ZONE_TEETH) {
                r = fminf(235.0f, r * 0.95f + 10.0f);
                g = fminf(225.0f, g * 0.92f + 6.0f);
                b = fminf(210.0f, b * 0.88f + 2.0f);
            } else {
                // ZONE_RASHGUARD_UPPER: Matte charcoal-obsidian & deep slate-navy athletic compression rashguard
                float fold = 0.94f + 0.10f * clampf(blur1001[idx] / 0.65f, 0.0f, 1.0f);
                float grain = (fbm_pores(u * 1200.0f, v * 1200.0f) - 0.5f) * 2.2f;
                int is_center_zip = (r < 42.0f && g < 42.0f && b < 42.0f && v > 0.48f && u > 0.30f && u < 0.48f);
                if (is_center_zip) {
                    r = 20.0f + grain; g = 23.0f + grain; b = 30.0f + grain;
                } else {
                    r = 28.0f * fold + grain;
                    g = 33.0f * fold + grain;
                    b = 44.0f * fold + grain;
                }
            }

            p[0] = (uint8_t)clampf(r, 0.0f, 255.0f);
            p[1] = (uint8_t)clampf(g, 0.0f, 255.0f);
            p[2] = (uint8_t)clampf(b, 0.0f, 255.0f);
            p[3] = 255;
        }
    }
    snprintf(path, sizeof(path), "%s/graded_Ch48_1001_Diffuse.png", work_dir);
    save_image_rgba(path, d1001, 4096, 4096);
    free(blur1001);
    free(d1001);

    // =========================================================================
    // 2. Process Ch48_1002_Diffuse (4096x4096) — Erasing Yellow Chest Emblem & Spacesuit Straps
    // =========================================================================
    snprintf(path, sizeof(path), "%s/Ch48_1002_Diffuse.png", work_dir);
    uint8_t *d1002 = load_image_rgba(path, 4096, 4096);
    float *blur1002 = compute_blurred_lum(d1002, 4096, 4096, 48);

    for (int py = 0; py < 4096; py++) {
        float v = (float)py / 4096.0f;
        for (int px = 0; px < 4096; px++) {
            float u = (float)px / 4096.0f;
            size_t idx = (size_t)py * 4096 + px;
            uint8_t z = mask1002[idx];
            uint8_t *p = d1002 + idx * 4;
            float fold = 0.95f + 0.08f * clampf(blur1002[idx] / 0.60f, 0.0f, 1.0f);
            float grain = (fbm_pores(u * 1200.0f, v * 1200.0f) - 0.5f) * 2.2f;
            float pebble = (fbm_pores(u * 850.0f, v * 850.0f) - 0.5f) * 4.5f;
            float r = 26.0f, g = 30.0f, b = 40.0f;

            if (z == ZONE_NECK_SKIN_LOWER) {
                // Warm human lower-neck skin seamlessly continuing Prim 1 Comp 0 submental neck tone down to the clavicles
                float pore = (fbm_pores(u * 1350.0f, v * 1350.0f) - 0.5f) * 3.0f;
                r = 152.0f * fold + pore;
                g = 102.0f * fold + pore * 0.8f;
                b = 82.0f * fold + pore * 0.7f;
            } else if (z == ZONE_COLLAR_TRIM || z == ZONE_RASHGUARD_YOKE) {
                // Unified matte charcoal-navy rashguard collar & upper chest yoke (100% erases yellow chest emblem & strap shadows!)
                r = 28.0f * fold + grain;
                g = 33.0f * fold + grain;
                b = 44.0f * fold + grain;
            } else if (z == ZONE_FIGHT_TIGHTS) {
                // Matte charcoal-obsidian athletic compression fight tights/spats
                r = 25.0f * fold + grain;
                g = 29.0f * fold + grain;
                b = 38.0f * fold + grain;
            } else {
                // ZONE_SHIN_GUARDS & ZONE_WRESTLING_SHOES: Matte black pebbled leather MMA shin guards & wrestling shoes
                r = 22.0f * fold + pebble;
                g = 24.0f * fold + pebble;
                b = 28.0f * fold + pebble;
            }

            p[0] = (uint8_t)clampf(r, 0.0f, 255.0f);
            p[1] = (uint8_t)clampf(g, 0.0f, 255.0f);
            p[2] = (uint8_t)clampf(b, 0.0f, 255.0f);
            p[3] = 255;
        }
    }
    snprintf(path, sizeof(path), "%s/graded_Ch48_1002_Diffuse.png", work_dir);
    save_image_rgba(path, d1002, 4096, 4096);
    free(blur1002);
    free(d1002);

    // =========================================================================
    // 3. Process Ch48_1001_Normal & Ch48_1002_Normal (2048x2048)
    //    - Add fine, calibrated 3D dermatological sebaceous pores on skin
    //    - Scrub sci-fi hexagonal honeycomb & spacesuit grooves on rashguard/tights
    // =========================================================================
    snprintf(path, sizeof(path), "%s/Ch48_1001_Normal.png", work_dir);
    uint8_t *n1001 = load_image_rgba(path, 2048, 2048);
    uint8_t *n1001_orig = (uint8_t *)malloc(2048 * 2048 * 4);
    memcpy(n1001_orig, n1001, 2048 * 2048 * 4);

    for (int py = 1; py < 2047; py++) {
        float v = (float)py / 2048.0f;
        for (int px = 1; px < 2047; px++) {
            float u = (float)px / 2048.0f;
            uint8_t z = mask1001[(py * 2) * 4096 + (px * 2)];
            uint8_t *p = n1001 + (py * 2048 + px) * 4;

            if (z == ZONE_EYEBALL_LEFT || z == ZONE_EYEBALL_RIGHT || z == ZONE_EYE_CARUNCLE) {
                p[0] = 128; p[1] = 128; p[2] = 255; p[3] = 255;
            } else if (z == ZONE_SKIN_HEAD_NECK || z == ZONE_HAND_FINGERS) {
                // Fine dermatological pore heightfield gradient (subtle +-5.5 normal delta, never stucco!)
                float freq = 1650.0f;
                float h_c = fbm_pores(u * freq, v * freq);
                float h_x = fbm_pores((u + 0.00040f) * freq, v * freq);
                float h_y = fbm_pores(u * freq, (v + 0.00040f) * freq);

                float t_zone = expf(-powf((u - 0.721f) / 0.045f, 2.0f)) * expf(-powf((v - 0.155f) / 0.055f, 2.0f));
                float scale = (z == ZONE_SKIN_HEAD_NECK) ? (22.0f + 14.0f * t_zone) : 14.0f;
                float dnx = clampf((h_c - h_x) * scale, -6.0f, 6.0f);
                float dny = clampf((h_c - h_y) * scale, -6.0f, 6.0f);

                p[0] = (uint8_t)clampf(p[0] + dnx, 110.0f, 146.0f);
                p[1] = (uint8_t)clampf(p[1] + dny, 110.0f, 146.0f);
                p[2] = 255; p[3] = 255;
            } else {
                // Scrub sci-fi hexagonal honeycomb & spaceship grooves on suit/gloves; add fine organic micro-grain
                int sum_x = 0, sum_y = 0, cnt = 0;
                for (int dy = -6; dy <= 6; dy += 3) {
                    int sy = clampf(py + dy, 0, 2047);
                    for (int dx = -6; dx <= 6; dx += 3) {
                        int sx = clampf(px + dx, 0, 2047);
                        uint8_t *sp = n1001_orig + (sy * 2048 + sx) * 4;
                        sum_x += sp[0]; sum_y += sp[1]; cnt++;
                    }
                }
                float bx = 128.0f + ((float)sum_x / cnt - 128.0f) * 0.08f;
                float by = 128.0f + ((float)sum_y / cnt - 128.0f) * 0.08f;
                float gx = (fbm_pores(u * 900.0f, v * 900.0f) - 0.5f) * 3.0f;
                float gy = (fbm_pores(u * 900.0f + 7.3f, v * 900.0f + 3.1f) - 0.5f) * 3.0f;
                p[0] = (uint8_t)clampf(bx + gx, 0.0f, 255.0f);
                p[1] = (uint8_t)clampf(by + gy, 0.0f, 255.0f);
                p[2] = 255; p[3] = 255;
            }
        }
    }
    snprintf(path, sizeof(path), "%s/graded_Ch48_1001_Normal.png", work_dir);
    save_image_rgba(path, n1001, 2048, 2048);
    free(n1001_orig);
    free(n1001);

    snprintf(path, sizeof(path), "%s/Ch48_1002_Normal.png", work_dir);
    uint8_t *n1002 = load_image_rgba(path, 2048, 2048);
    uint8_t *n1002_orig = (uint8_t *)malloc(2048 * 2048 * 4);
    memcpy(n1002_orig, n1002, 2048 * 2048 * 4);
    for (int py = 1; py < 2047; py++) {
        float v = (float)py / 2048.0f;
        for (int px = 1; px < 2047; px++) {
            float u = (float)px / 2048.0f;
            uint8_t *p = n1002 + (py * 2048 + px) * 4;
            int sum_x = 0, sum_y = 0, cnt = 0;
            for (int dy = -6; dy <= 6; dy += 3) {
                int sy = clampf(py + dy, 0, 2047);
                for (int dx = -6; dx <= 6; dx += 3) {
                    int sx = clampf(px + dx, 0, 2047);
                    uint8_t *sp = n1002_orig + (sy * 2048 + sx) * 4;
                    sum_x += sp[0]; sum_y += sp[1]; cnt++;
                }
            }
            float bx = 128.0f + ((float)sum_x / cnt - 128.0f) * 0.05f;
            float by = 128.0f + ((float)sum_y / cnt - 128.0f) * 0.05f;
            float gx = (fbm_pores(u * 900.0f, v * 900.0f) - 0.5f) * 3.0f;
            float gy = (fbm_pores(u * 900.0f + 7.3f, v * 900.0f + 3.1f) - 0.5f) * 3.0f;
            p[0] = (uint8_t)clampf(bx + gx, 0.0f, 255.0f);
            p[1] = (uint8_t)clampf(by + gy, 0.0f, 255.0f);
            p[2] = 255; p[3] = 255;
        }
    }
    snprintf(path, sizeof(path), "%s/graded_Ch48_1002_Normal.png", work_dir);
    save_image_rgba(path, n1002, 2048, 2048);
    free(n1002_orig);
    free(n1002);

    // =========================================================================
    // 4. Build Calibrated glTF MetallicRoughness (`Glossiness`) & Specular Maps (2048x2048)
    //    In glTF 2.0: Green = Roughness, Blue = Metallic
    // =========================================================================
    uint8_t *mr1001 = (uint8_t *)malloc(2048 * 2048 * 4);
    uint8_t *sp1001 = (uint8_t *)malloc(2048 * 2048 * 4);
    for (int py = 0; py < 2048; py++) {
        float v = (float)py / 2048.0f;
        for (int px = 0; px < 2048; px++) {
            float u = (float)px / 2048.0f;
            uint8_t z = mask1001[(py * 2) * 4096 + (px * 2)];
            uint8_t *pm = mr1001 + (py * 2048 + px) * 4;
            uint8_t *ps = sp1001 + (py * 2048 + px) * 4;

            float rough = 200.0f;
            float spec = 48.0f;
            if (z == ZONE_EYEBALL_LEFT || z == ZONE_EYEBALL_RIGHT || z == ZONE_EYE_CARUNCLE) {
                rough = 8.0f;   // 0.031 mirror-wet tear film
                spec = 255.0f;
            } else if (z == ZONE_SKIN_HEAD_NECK || z == ZONE_HAND_FINGERS) {
                float pore = fbm_pores(u * 1450.0f, v * 1450.0f);
                // Calibrated skin roughness (196..236) prevents overhead studio light blowout on the forehead (N.H ~ 1.0)
                float fh_rough = (v < 0.120f) ? 24.0f * smoothstep(0.120f, 0.085f, v) : 0.0f;
                rough = 188.0f + fh_rough + (pore < 0.38f ? 42.0f : (pore - 0.5f) * 28.0f);
                // Moist lower lip vermilion is slightly glossier
                if (u >= 0.695f && u <= 0.748f && v >= 0.172f && v <= 0.205f) {
                    rough = 118.0f;
                }
                spec = (v < 0.118f) ? 28.0f : 44.0f;
            } else if (z == ZONE_HAND_GLOVE) {
                // Satin-matte pebbled leather MMA gloves
                rough = 122.0f + (fbm_pores(u * 800.0f, v * 800.0f) - 0.5f) * 18.0f;
                spec = 56.0f;
            } else {
                // Matte woven rashguard & cotton wrist wraps (zero sci-fi honeycomb!)
                rough = 204.0f + sinf((float)px * 1.57f) * 6.0f;
                spec = 32.0f;
            }
            pm[0] = 255;
            pm[1] = (uint8_t)clampf(rough, 4.0f, 252.0f);
            pm[2] = 0; // Metallic = 0.0
            pm[3] = 255;

            uint8_t sv = (uint8_t)clampf(spec, 0.0f, 255.0f);
            ps[0] = sv; ps[1] = sv; ps[2] = sv; ps[3] = 255;
        }
    }
    snprintf(path, sizeof(path), "%s/graded_Ch48_1001_Glossiness.png", work_dir);
    save_image_rgba(path, mr1001, 2048, 2048);
    snprintf(path, sizeof(path), "%s/graded_Ch48_1001_Specular.png", work_dir);
    save_image_rgba(path, sp1001, 2048, 2048);
    free(mr1001);
    free(sp1001);

    uint8_t *mr1002 = (uint8_t *)malloc(2048 * 2048 * 4);
    uint8_t *sp1002 = (uint8_t *)malloc(2048 * 2048 * 4);
    for (int py = 0; py < 2048; py++) {
        float v = (float)py / 2048.0f;
        for (int px = 0; px < 2048; px++) {
            float u = (float)px / 2048.0f;
            uint8_t z = mask1002[(py * 2) * 4096 + (px * 2)];
            uint8_t *pm = mr1002 + (py * 2048 + px) * 4;
            uint8_t *ps = sp1002 + (py * 2048 + px) * 4;

            float rough = 204.0f;
            float spec = 32.0f;
            if (z == ZONE_NECK_SKIN_LOWER) {
                float pore = fbm_pores(u * 1450.0f, v * 1450.0f);
                rough = 142.0f + (pore < 0.38f ? 68.0f : (pore - 0.5f) * 35.0f);
                spec = 68.0f;
            } else if (z == ZONE_SHIN_GUARDS || z == ZONE_WRESTLING_SHOES) {
                rough = 126.0f + (fbm_pores(u * 800.0f, v * 800.0f) - 0.5f) * 16.0f;
                spec = 54.0f;
            } else {
                rough = 204.0f + sinf((float)px * 1.57f) * 6.0f;
                spec = 32.0f;
            }
            pm[0] = 255;
            pm[1] = (uint8_t)clampf(rough, 4.0f, 252.0f);
            pm[2] = 0;
            pm[3] = 255;

            uint8_t sv = (uint8_t)clampf(spec, 0.0f, 255.0f);
            ps[0] = sv; ps[1] = sv; ps[2] = sv; ps[3] = 255;
        }
    }
    snprintf(path, sizeof(path), "%s/graded_Ch48_1002_Glossiness.png", work_dir);
    save_image_rgba(path, mr1002, 2048, 2048);
    snprintf(path, sizeof(path), "%s/graded_Ch48_1002_Specular.png", work_dir);
    save_image_rgba(path, sp1002, 2048, 2048);
    free(mr1002);
    free(sp1002);

    // =========================================================================
    // 5. Process Ch48_1003_Diffuse (2048x2048 Hair & Feathery Tapered Eyelashes)
    // =========================================================================
    snprintf(path, sizeof(path), "%s/Ch48_1003_Diffuse.png", work_dir);
    uint8_t *d1003 = load_image_rgba(path, 2048, 2048);
    for (int py = 0; py < 2048; py++) {
        float v = (float)py / 2048.0f;
        for (int px = 0; px < 2048; px++) {
            float u = (float)px / 2048.0f;
            uint8_t *p = d1003 + (py * 2048 + px) * 4;
            int a = p[3];
            if (a == 0) continue;

            // Check if inside Eyelash UV region: U in [0.612, 0.776], V in [0.075, 0.206]
            if (u >= 0.612f && u <= 0.776f && v >= 0.075f && v <= 0.206f) {
                // Replace clumpy black triangular eyelash wedge with delicate tapered individual lashes
                float u_norm = (u - 0.617f) / (0.771f - 0.617f);
                float v_norm = (v - 0.079f) / (0.202f - 0.079f);
                // Taper out both lateral ends so there is ZERO winged eyeliner spike!
                float end_taper = smoothstep(0.0f, 0.22f, u_norm) * smoothstep(1.0f, 0.74f, u_norm);
                float tip_taper = smoothstep(0.05f, 0.85f, v_norm);
                float lash_comb = 0.45f + 0.55f * sinf(u_norm * 195.0f + sinf(v_norm * 6.0f) * 0.8f);
                float new_a = (float)a * end_taper * tip_taper * lash_comb * 0.72f;
                int ia = (int)clampf(new_a, 0.0f, 255.0f);
                p[0] = (uint8_t)((24 * ia) / 255);
                p[1] = (uint8_t)((18 * ia) / 255);
                p[2] = (uint8_t)((15 * ia) / 255);
                p[3] = (uint8_t)ia;
            } else {
                float r = (float)p[0] * 255.0f / a;
                float g = (float)p[1] * 255.0f / a;
                float b = (float)p[2] * 255.0f / a;
                float lum = 0.299f * r + 0.587f * g + 0.114f * b;
                float strand = 0.85f + 0.30f * sinf(u * 1400.0f);
                float darkLum = powf(lum / 255.0f, 1.25f) * 78.0f * strand;
                float nr = clampf(darkLum * 1.14f + 12.0f, 0.0f, 255.0f);
                float ng = clampf(darkLum * 0.90f + 8.0f, 0.0f, 255.0f);
                float nb = clampf(darkLum * 0.74f + 6.0f, 0.0f, 255.0f);
                p[0] = (uint8_t)((nr * a) / 255.0f);
                p[1] = (uint8_t)((ng * a) / 255.0f);
                p[2] = (uint8_t)((nb * a) / 255.0f);
            }
        }
    }
    snprintf(path, sizeof(path), "%s/graded_Ch48_1003_Diffuse.png", work_dir);
    save_image_rgba(path, d1003, 2048, 2048);
    free(d1003);

    free(mask1001);
    free(mask1002);
    return 0;
}
""")
    subprocess.run(
        [
            "clang",
            "-O3",
            "-framework",
            "CoreGraphics",
            "-framework",
            "ImageIO",
            "-framework",
            "CoreFoundation",
            c_src,
            "-o",
            c_bin,
        ],
        check=True,
    )
    print("[textures] Running C 4K/2K dermatological & combat gear texture engine...")
    subprocess.run([c_bin, WORK_DIR], check=True)

    graded = {}
    for stem in (
        "Ch48_1001_Diffuse",
        "Ch48_1001_Normal",
        "Ch48_1001_Glossiness",
        "Ch48_1001_Specular",
        "Ch48_1002_Diffuse",
        "Ch48_1002_Normal",
        "Ch48_1002_Glossiness",
        "Ch48_1002_Specular",
        "Ch48_1003_Diffuse",
    ):
        p = os.path.join(WORK_DIR, f"graded_{stem}.png")
        with open(p, "rb") as f:
            graded[stem] = f.read()
    return graded


def assemble_final_glb(j, bin_chunk, split_prim1, graded_pngs):
    idx1_skin, idx1_eyes, idx1_gear = split_prim1

    # Split Mesh 0 Prim 1 into 3 primitives with dedicated materials:
    # mat 1 = Ch48_skin, mat 3 = Ch48_eyes, mat 4 = Ch48_upper_gear
    m0 = j["meshes"][0]
    p1_orig = m0["primitives"][1]
    attrs = dict(p1_orig["attributes"])

    def append_index_accessor(indices_list, name):
        raw_bytes = struct.pack(f"<{len(indices_list)}H", *indices_list)
        bv_idx = len(j["bufferViews"])
        j["bufferViews"].append(
            {
                "buffer": 0,
                "byteOffset": 0,  # filled during buffer rebuild
                "byteLength": len(raw_bytes),
                "target": 34963,
            }
        )
        acc_idx = len(j["accessors"])
        j["accessors"].append(
            {
                "bufferView": bv_idx,
                "componentType": 5123,
                "count": len(indices_list),
                "type": "SCALAR",
                "min": [min(indices_list)],
                "max": [max(indices_list)],
                "name": name,
            }
        )
        return bv_idx, acc_idx, raw_bytes

    extra_bvs = {}
    bv_skin, acc_skin, bytes_skin = append_index_accessor(idx1_skin, "Prim1_Skin_Indices")
    bv_eyes, acc_eyes, bytes_eyes = append_index_accessor(idx1_eyes, "Prim1_Eyes_Indices")
    bv_gear, acc_gear, bytes_gear = append_index_accessor(idx1_gear, "Prim1_Gear_Indices")
    extra_bvs[bv_skin] = bytes_skin
    extra_bvs[bv_eyes] = bytes_eyes
    extra_bvs[bv_gear] = bytes_gear

    # Configure 5 dedicated physically based glTF materials (ZERO emissive lights/logos!)
    j["materials"] = [
        {
            "name": "Ch48_lower_gear",
            "doubleSided": True,
            "normalTexture": {"index": 2},
            "pbrMetallicRoughness": {
                "baseColorTexture": {"index": 3},
                "metallicRoughnessTexture": {"index": 4},
                "metallicFactor": 0.0,
                "roughnessFactor": 1.0,
            },
            "extensions": {
                "KHR_materials_specular": {"specularTexture": {"index": 1}, "specularFactor": 0.45},
                "KHR_materials_sheen": {
                    "sheenColorFactor": [0.16, 0.20, 0.28],
                    "sheenRoughnessFactor": 0.58,
                },
            },
        },
        {
            "name": "Ch48_skin",
            "doubleSided": True,
            "normalTexture": {"index": 7, "scale": 1.15},
            "pbrMetallicRoughness": {
                "baseColorTexture": {"index": 8},
                "metallicRoughnessTexture": {"index": 9},
                "metallicFactor": 0.0,
                "roughnessFactor": 1.0,
            },
            "extensions": {
                "KHR_materials_ior": {"ior": 1.38},
                "KHR_materials_specular": {"specularTexture": {"index": 6}, "specularFactor": 0.22},
                "KHR_materials_sheen": {
                    "sheenColorFactor": [0.42, 0.20, 0.14],
                    "sheenRoughnessFactor": 0.68,
                },
            },
        },
        {
            "name": "Ch48_hair",
            "alphaMode": "BLEND",
            "doubleSided": True,
            "pbrMetallicRoughness": {
                "baseColorTexture": {"index": 11},
                "metallicRoughnessTexture": {"index": 12},
                "metallicFactor": 0.0,
                "roughnessFactor": 0.68,
            },
            "extensions": {
                "KHR_materials_specular": {"specularTexture": {"index": 10}, "specularFactor": 0.35},
                "KHR_materials_sheen": {
                    "sheenColorFactor": [0.24, 0.18, 0.14],
                    "sheenRoughnessFactor": 0.38,
                },
            },
        },
        {
            "name": "Ch48_eyes",
            "doubleSided": True,
            "normalTexture": {"index": 7},
            "pbrMetallicRoughness": {
                "baseColorTexture": {"index": 8},
                "metallicRoughnessTexture": {"index": 9},
                "metallicFactor": 0.0,
                "roughnessFactor": 0.15,
            },
            "extensions": {
                "KHR_materials_ior": {"ior": 1.38},
                "KHR_materials_specular": {"specularFactor": 1.0},
                "KHR_materials_clearcoat": {
                    "clearcoatFactor": 1.0,
                    "clearcoatRoughnessFactor": 0.01,
                },
            },
        },
        {
            "name": "Ch48_upper_gear",
            "doubleSided": True,
            "normalTexture": {"index": 7},
            "pbrMetallicRoughness": {
                "baseColorTexture": {"index": 8},
                "metallicRoughnessTexture": {"index": 9},
                "metallicFactor": 0.0,
                "roughnessFactor": 1.0,
            },
            "extensions": {
                "KHR_materials_specular": {"specularTexture": {"index": 6}, "specularFactor": 0.45},
                "KHR_materials_sheen": {
                    "sheenColorFactor": [0.16, 0.20, 0.28],
                    "sheenRoughnessFactor": 0.58,
                },
            },
        },
    ]

    m0["primitives"] = [
        m0["primitives"][0],
        {"attributes": attrs, "indices": acc_skin, "material": 1, "mode": 4},
        {"attributes": attrs, "indices": acc_eyes, "material": 3, "mode": 4},
        {"attributes": attrs, "indices": acc_gear, "material": 4, "mode": 4},
        m0["primitives"][2],
    ]

    image_bv_indices = {im["bufferView"]: idx for idx, im in enumerate(j["images"])}
    new_bin = bytearray()

    for bv_idx, bv in enumerate(j["bufferViews"]):
        if bv_idx in extra_bvs:
            raw_slice = extra_bvs[bv_idx]
        else:
            old_offset = bv.get("byteOffset", 0)
            old_len = bv["byteLength"]
            raw_slice = bytes(bin_chunk[old_offset : old_offset + old_len])

            if bv_idx in image_bv_indices:
                im_idx = image_bv_indices[bv_idx]
                im_name = j["images"][im_idx].get("name", "")
                if im_name in graded_pngs:
                    raw_slice = graded_pngs[im_name]
                    w, h = struct.unpack(">II", raw_slice[16:24])
                    print(f"  -> Embedded image[{im_idx:2d}] {im_name:22s}: {w}x{h} ({len(raw_slice) // 1024} KB)")

        while len(new_bin) % 4 != 0:
            new_bin.append(0)
        bv["byteOffset"] = len(new_bin)
        bv["byteLength"] = len(raw_slice)
        new_bin.extend(raw_slice)

    while len(new_bin) % 4 != 0:
        new_bin.append(0)
    j["buffers"][0]["byteLength"] = len(new_bin)

    ext_used = set(j.get("extensionsUsed", []))
    ext_used.update(
        [
            "KHR_materials_specular",
            "KHR_materials_sheen",
            "KHR_materials_clearcoat",
            "KHR_materials_ior",
        ]
    )
    j["extensionsUsed"] = sorted(ext_used)

    json_bytes = json.dumps(j, separators=(",", ":")).encode("utf-8")
    while len(json_bytes) % 4 != 0:
        json_bytes += b" "

    total_len = 12 + 8 + len(json_bytes) + 8 + len(new_bin)
    with open(OUT_GLB, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total_len))
        f.write(struct.pack("<II", len(json_bytes), 0x4E4F534A))
        f.write(json_bytes)
        f.write(struct.pack("<II", len(new_bin), 0x004E4942))
        f.write(new_bin)

    print(f"[upgrade] Wrote {OUT_GLB} ({total_len / 1e6:.2f} MB)")


def main():
    extracted = extract_fbx_pngs()
    j, bin_chunk, split_prim1, mask1001_path, mask1002_path = upgrade_geometry_and_build_masks()
    graded = build_and_run_c_texture_engine(extracted, mask1001_path, mask1002_path)
    assemble_final_glb(j, bin_chunk, split_prim1, graded)


if __name__ == "__main__":
    main()
