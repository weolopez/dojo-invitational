"""Stage 3: put CLAUDE's MPFB Mixamo rig into the clips' T-pose rest, then retarget all 30 shared Mixamo clips and,
since call #9, the 12 optional/extra clips the arena would otherwise lend (assets/mixamo/extra), then ground the feet.
Opens .work/claude_materials.blend, writes .work/claude_rigged.blend.

Retarget: for every frame, each bone's world rotation is copied from the source skeleton (X Bot clips in
assets/mixamo), corrected by the rest-pose difference between the two bones (both rests are T-poses after step 1),
then converted to the target bone's local rotation. Hip translation is scaled by the hip-height ratio.

Grounding (call #9, ground()): the rotation copy left both feet 4-7 cm above the floor in most stance clips (CLAUDE's
legs and feet are proportioned differently from the X Bot's), with heels lifted. Per clip, the hips are lowered so
the lowest foot touches the floor whenever the source's foot does, then each foot in contact is planted with a
two-bone leg IK: put on the floor, held in place while it's in contact, and in stance clips turned flat (heel down).
The walks are made in place, since the arena moves the fighter itself.
"""
import glob
import math
import os

import bpy
from mathutils import Matrix, Quaternion, Vector

ENTRY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ENTRY, ".work")
MIXAMO = "/Users/weo/Development/3d/assets/mixamo"
HIPS = "mixamorig:Hips"
FPS = 30
UP = Vector((0, 0, 1))

# Extra clips (assets/mixamo/extra). The arena plays a fighter's own copy whole (lent.js), and lends Mixamo's get-ups
# and dodges trimmed to these windows (seconds), so the same windows are cut here.
TRIM = {"getup_back": (3.2, 6.3), "getup_front": (1.9, 6.3), "dodge_in": (0, 1.1), "dodge_back": (0, 1.2)}

# How each clip's feet are grounded (see ground()):
#   flat  - stance clips: feet on the floor and turned flat (heel down) whenever they're in contact
#   stand - like flat, but both feet are held for the whole clip (the fighting stance itself)
#   plant - feet put on the floor and held while in contact, but not flattened (pivots, steps, kicks, jumps)
#   walk  - like plant, made in place: the hips' travel is removed and a planted foot moves back at the walk's speed
#   none  - falls, throws and get-ups: left as retargeted
MODE = {
    "fighting_idle": "stand", "block": "stand", "block_high": "stand",
    "crouch": "flat", "taunt": "flat", "jab": "flat", "cross": "flat", "jab_cross": "flat", "hook": "flat",
    "uppercut": "flat", "punch_combo": "flat", "hit_head_light": "flat", "hit_head_big": "flat",
    "hit_reaction": "flat", "hit_by_uppercut": "flat", "dodge_in": "flat", "dodge_back": "flat", "knee": "flat",
    "front_kick": "flat", "side_kick": "flat", "low_kick": "flat",
    "roundhouse_kick": "plant", "spin_kick": "plant", "sweep": "plant", "jump": "plant", "victory": "plant",
    "step_forward": "plant", "step_backward": "plant", "side_step_left": "plant", "side_step_right": "plant",
    "throw": "plant",
    "walk_forward": "walk", "walk_backward": "walk",
}


def import_clip(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = set(bpy.data.objects) - before
    arm = next(o for o in new if o.type == "ARMATURE")
    return arm, new


def remove(objs):
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)


def ordered(arm):
    """Bones parents-first."""
    out = []
    def walk(b):
        out.append(b.name)
        for c in b.children:
            walk(c)
    for b in arm.data.bones:
        if b.parent is None:
            walk(b)
    return out


def match_rest_pose(target, source):
    """Swing the arm chains (A-pose to T-pose) so they point the same way as the source rest bones, in world space.
    Spine, hips and legs already match closely and are left alone, so no bone can be flipped end to end."""
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.mode_set(mode="POSE")
    for name in ordered(target):
        if name not in source.data.bones or not any(k in name for k in ("Shoulder", "Arm", "Hand")):
            continue
        sb = source.data.bones[name]
        d_src = (source.matrix_world @ sb.tail_local) - (source.matrix_world @ sb.head_local)
        if d_src.length < 1e-6:
            continue
        pb = target.pose.bones[name]
        head = target.matrix_world @ pb.head
        d_tgt = (target.matrix_world @ pb.tail) - head
        q = d_tgt.normalized().rotation_difference(d_src.normalized())
        if q.angle > math.radians(100):
            print(f"[rig] skipped {name}: {math.degrees(q.angle):.0f} degrees apart")
            continue
        world = target.matrix_world @ pb.matrix
        swung = Matrix.Translation(head) @ q.to_matrix().to_4x4() @ Matrix.Translation(-head) @ world
        pb.matrix = target.matrix_world.inverted() @ swung
        bpy.context.view_layer.update()
    bpy.ops.object.mode_set(mode="OBJECT")


def apply_pose_as_rest(target):
    """Bake the current pose into every skinned mesh, then make it the armature's rest pose."""
    for obj in [o for o in bpy.data.objects if o.type == "MESH"]:
        mod = next((m for m in obj.modifiers if m.type == "ARMATURE" and m.object == target), None)
        if not mod:
            continue
        if obj.data.shape_keys:
            # Keep the body shape (MPFB macro targets) by baking the current shape-key mix into the mesh.
            with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj]):
                bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
        name = mod.name
        with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj]):
            bpy.ops.object.modifier_apply(modifier=name)
        new = obj.modifiers.new(name, "ARMATURE")
        new.object = target
        while obj.modifiers.find(name) > 0:
            with bpy.context.temp_override(object=obj, active_object=obj):
                bpy.ops.object.modifier_move_up(modifier=name)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.armature_apply(selected=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def world_rest_rot(arm, name):
    return (arm.matrix_world @ arm.data.bones[name].matrix_local).to_quaternion()


class Feet:
    """Ground markers on each foot, fixed in the foot bone's rest frame: the heel (the lowest, rearmost skin under the
    ankle), the ball (the ToeBase joint) and the toe tip (the ToeBase tail), with their rest heights."""

    def __init__(self, arm, body):
        self.arm = arm
        W = arm.matrix_world
        self.side = {}
        verts = body.data.vertices
        for s in ("Left", "Right"):
            foot, toe = arm.data.bones[f"mixamorig:{s}Foot"], arm.data.bones[f"mixamorig:{s}ToeBase"]
            ankle = W @ foot.head_local
            # Skin below the ankle, within the foot's width (MPFB's hidden helper shells sit around the body, so only
            # the 'body' group counts).
            gi = body.vertex_groups["body"].index
            low = [body.matrix_world @ v.co for v in verts if any(g.group == gi and g.weight > 0 for g in v.groups)]
            low = [p for p in low if p.z < ankle.z * 0.5 and abs(p.x - ankle.x) < 0.05 and abs(p.y - ankle.y) < 0.12]
            # The rearmost of them (the glTF front is -Y in Blender, so the heel has the largest y).
            heel = max(low, key=lambda p: p.y)
            heel = Vector((ankle.x, heel.y, min(p.z for p in low)))
            frame = (W @ foot.matrix_local).inverted()
            self.side[s] = {
                "heel": frame @ heel, "ball": frame @ (W @ toe.head_local), "toe": frame @ (W @ toe.tail_local),
                "rest": {"heel": heel.z, "ball": (W @ toe.head_local).z, "toe": (W @ toe.tail_local).z},
            }
            print(f"[feet] {s}: heel {heel.z * 100:.1f} cm, ball {(W @ toe.head_local).z * 100:.1f} cm, "
                  f"ankle {ankle.z * 100:.1f} cm above the floor in the rest pose")

    def markers(self, s, foot_world):
        d = self.side[s]
        return {k: foot_world @ d[k] for k in ("heel", "ball", "toe")}

    def lift(self, s, foot_world):
        """How far the foot's lowest marker is above its rest height (its 'on the floor' height), and which one."""
        m = self.markers(s, foot_world)
        k = min(m, key=lambda n: m[n].z - self.side[s]["rest"][n])
        return m[k].z - self.side[s]["rest"][k], k, m


def source_floor(src, rest):
    """How high the source's lowest foot marker is above where it sits in the source's rest pose (metres)."""
    W = src.matrix_world
    best = 1e9
    for s in ("Left", "Right"):
        for b, part in ((f"mixamorig:{s}Foot", "head"), (f"mixamorig:{s}ToeBase", "head"), (f"mixamorig:{s}ToeBase", "tail")):
            if b not in src.pose.bones:
                continue
            p = W @ getattr(src.pose.bones[b], part)
            best = min(best, p.z - rest[(b, part)])
    return best


def retarget(target, source, clip_name, ratio, window=None):
    names = [n for n in ordered(target) if n in source.data.bones]
    rest_t = {n: world_rest_rot(target, n) for n in ordered(target)}
    rest_s = {n: world_rest_rot(source, n) for n in names}
    align = {n: rest_s[n].inverted() @ rest_t[n] for n in names}
    hips_rest_t = target.matrix_world @ target.data.bones[HIPS].head_local
    hips_rest_s = source.matrix_world @ source.data.bones[HIPS].head_local
    hips_rest_arm_rot = target.data.bones[HIPS].matrix_local.to_quaternion()
    src_rest = {}
    for b in source.data.bones:
        src_rest[(b.name, "head")] = (source.matrix_world @ b.head_local).z
        src_rest[(b.name, "tail")] = (source.matrix_world @ b.tail_local).z

    act_src = source.animation_data.action
    f0, f1 = (int(round(v)) for v in act_src.frame_range)
    if window:
        f0, f1 = f0 + round(window[0] * FPS), min(f1, f0 + round(window[1] * FPS))
    scene = bpy.context.scene
    action = bpy.data.actions.new(clip_name)
    target.animation_data_create()
    target.animation_data.action = action
    if hasattr(target.animation_data, "action_slot") and action.slots:
        target.animation_data.action_slot = action.slots[0]
    for pb in target.pose.bones:
        pb.rotation_mode = "QUATERNION"
    prev = {}
    floor = []
    for i, f in enumerate(range(f0, f1 + 1)):
        scene.frame_set(f)
        floor.append(source_floor(source, src_rest) * ratio)
        desired = {}
        for n in names:
            desired[n] = (source.matrix_world @ source.pose.bones[n].matrix).to_quaternion() @ align[n]
        for n in names:
            parent = target.data.bones[n].parent
            if parent is None:
                basis = rest_t[n].inverted() @ desired[n]
            else:
                pr = desired.get(parent.name, rest_t[parent.name])
                basis = rest_t[n].inverted() @ rest_t[parent.name] @ pr.inverted() @ desired[n]
            if n in prev and prev[n].dot(basis) < 0:
                basis = -basis
            prev[n] = basis
            pb = target.pose.bones[n]
            pb.rotation_quaternion = basis
            pb.keyframe_insert("rotation_quaternion", frame=i + 1, group=n)
        hips_world = hips_rest_t + (source.matrix_world @ source.pose.bones[HIPS].head - hips_rest_s) * ratio
        delta_arm = target.matrix_world.inverted().to_3x3() @ (hips_world - hips_rest_t)
        pb = target.pose.bones[HIPS]
        pb.location = hips_rest_arm_rot.inverted() @ delta_arm
        pb.keyframe_insert("location", frame=i + 1, group=HIPS)
    return action, floor


def smooth(values, radius=2):
    out = []
    for i in range(len(values)):
        win = values[max(0, i - radius): i + radius + 1]
        out.append(sum(win) / len(win))
    return out


def two_bone(H, K, A, D):
    """New knee position for a hip H, knee K, ankle A reaching for D, keeping the knee in the plane it bends in now."""
    l1, l2 = (K - H).length, (A - K).length
    to = D - H
    d = min(max(to.length, abs(l1 - l2) + 1e-4), l1 + l2 - 1e-4)
    axis = to.normalized()
    pole = (K - H) - axis * (K - H).dot(axis)
    if pole.length < 1e-6:
        pole = Vector((0, -1, 0))
    pole.normalize()
    a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    h = math.sqrt(max(l1 * l1 - a * a, 0.0))
    return H + axis * a + pole * h, H + axis * d


def about(point, q):
    return Matrix.Translation(point) @ q.to_matrix().to_4x4() @ Matrix.Translation(-point)


def ground(target, action, floor, mode, feet, clip_name):
    """Lower the hips onto the floor and plant the feet (see the module docstring). Works on the keyed action."""
    if mode == "none":
        return
    scene = bpy.context.scene
    W = target.matrix_world
    Wi = W.inverted()
    n = len(floor)
    P = target.pose.bones
    bones = {s: [P[f"mixamorig:{s}{b}"] for b in ("UpLeg", "Leg", "Foot", "ToeBase")] for s in ("Left", "Right")}
    hips = P[HIPS]
    hips_rest_arm_rot = target.data.bones[HIPS].matrix_local.to_quaternion()

    # Pass 1: read the retargeted pose (world matrices of the leg bones and the hips' keyed location).
    frames = []
    for i in range(n):
        scene.frame_set(i + 1)
        rec = {"hips_loc": hips.location.copy()}
        for s, chain in bones.items():
            rec[s] = [W @ pb.matrix for pb in chain]
            rec[s + "_toe_basis"] = chain[3].rotation_quaternion.copy()
        frames.append(rec)

    # In place for the walks: remove the hips' average travel over the floor; a planted foot then moves back at that
    # speed in the fighter's own space.
    tread = Vector((0, 0, 0))
    if mode == "walk":
        h0 = frames[0]["Left"][0].translation.copy()
        h1 = frames[-1]["Left"][0].translation.copy()
        tread = (h1 - h0) / max(1, n - 1)
        tread.z = 0
        for i, rec in enumerate(frames):
            shift = Matrix.Translation(-tread * i)
            for s in bones:
                rec[s] = [shift @ m for m in rec[s]]
            rec["travel"] = -tread * i

    # Pass 2: hips drop. g = the lower foot's lift; lowered fully while the source's own foot is on its floor, and
    # only by the extra lift the retarget added while the source is airborne (jumps).
    drop = []
    for i, rec in enumerate(frames):
        g = min(feet.lift(s, rec[s][2])[0] for s in bones)
        k = min(1.0, max(0.0, (0.10 - floor[i]) / 0.05))
        drop.append(-(g * k + (g - max(floor[i], 0.0)) * (1 - k)))
    drop = smooth(drop, 2)
    for i, rec in enumerate(frames):
        shift = Matrix.Translation(Vector((0, 0, drop[i])))
        for s in bones:
            rec[s] = [shift @ m for m in rec[s]]
        rec["drop"] = drop[i]

    # Pass 3: contact weights per foot: the lowest marker near the floor and slow (relative to the treadmill).
    weights = {}
    for s in bones:
        raw = []
        for i, rec in enumerate(frames):
            lift, key, m = feet.lift(s, rec[s][2])
            j = min(n - 1, i + 1) if i == 0 else i
            a = feet.markers(s, frames[j - 1][s][2])[key] if j > 0 else m[key]
            b = feet.markers(s, frames[j][s][2])[key]
            v = (b - a)
            v.z = 0
            speed = (v + tread).length * FPS
            w_h = min(1.0, max(0.0, (0.05 - lift) / 0.03))
            w_v = min(1.0, max(0.0, (0.9 - speed) / 0.5))
            raw.append(1.0 if mode == "stand" else w_h * w_v)
        weights[s] = [min(1.0, x * 1.25) for x in smooth(raw, 2)]

    flatten = mode in ("flat", "stand")
    foot_rest = {s: (W @ target.data.bones[f"mixamorig:{s}Foot"].matrix_local).to_quaternion() for s in bones}

    def flat_rot(s, R):
        """The foot's rotation with its sole turned level (the rest pose's tilt), keeping which way it points."""
        sole_up = (R @ foot_rest[s].inverted()) @ UP
        return sole_up.rotation_difference(UP) @ R

    # Contact segments per foot: the ball is held where it is when the foot is most firmly down (moving with the
    # treadmill for the walks; for the stance clips, at its average place), and a flattened foot keeps one heading for
    # the whole contact (a heel on the floor doesn't swivel).
    hold = {}
    for s in bones:
        w = weights[s]
        anchor, heading = [None] * n, [None] * n
        i = 0
        while i < n:
            if w[i] < 0.5:
                i += 1
                continue
            j = i
            while j < n and w[j] >= 0.5:
                j += 1
            ball = [feet.markers(s, frames[t][s][2])["ball"] for t in range(i, j)]
            rots = [flat_rot(s, frames[t][s][2].to_quaternion()) for t in range(i, j)]
            if mode == "stand":
                ref = sum(ball, Vector()) / len(ball)
                acc = Vector((0, 0, 0, 0))
                for q in rots:
                    acc += Vector(q) if Vector(q).dot(Vector(rots[0])) >= 0 else -Vector(q)
                head = Quaternion(tuple(acc)).normalized()  # (Quaternion(Vector) would set w to 1)
                for t in range(i, j):
                    anchor[t], heading[t] = ref.copy(), head
            else:
                ref_t = max(range(i, j), key=lambda t: w[t])
                for t in range(i, j):
                    anchor[t] = ball[ref_t - i] - tread * (t - ref_t)
                    heading[t] = rots[ref_t - i]
            i = j
        hold[s] = (anchor, heading)

    def target_for(s, i, amount):
        """Planted foot (world matrix) for frame i, with `amount` of the flattening (1 = heel fully down)."""
        rest = feet.side[s]["rest"]
        anchor, heading = hold[s]
        foot_m = frames[i][s][2]
        R = foot_m.to_quaternion()
        if flatten:
            Rt = R.slerp(heading[i] or flat_rot(s, R), amount)
        else:
            Rt = R
        m = Matrix.Translation(foot_m.translation) @ Rt.to_matrix().to_4x4() @ Matrix.Scale(foot_m.to_scale()[0], 4)
        lift, key, mk = feet.lift(s, m)
        m = Matrix.Translation(Vector((0, 0, rest[key] - mk[key].z))) @ m  # lowest marker on the floor
        if anchor[i] is not None:
            off = anchor[i] - feet.markers(s, m)["ball"]
            off.z = 0
            m = Matrix.Translation(off) @ m
        return m

    def solve(s, i, amount):
        """Leg IK toward the planted foot, blended with the clip by the contact weight. Returns the new matrices and
        how far the leg falls short of the target."""
        w = weights[s][i]
        up_m, leg_m, foot_m, toe_m = frames[i][s]
        tm = target_for(s, i, amount)
        D = foot_m.translation.lerp(tm.translation, w)
        Rq = foot_m.to_quaternion().slerp(tm.to_quaternion(), w)
        H, K, A = up_m.translation, leg_m.translation, foot_m.translation
        reach = (K - H).length + (A - K).length - 0.003
        r = D - H
        flat2 = r.x * r.x + r.y * r.y
        short = 0.0
        if r.length > reach:
            short = -r.z - math.sqrt(reach * reach - flat2) if flat2 < reach * reach else r.length - reach
        K2, D2 = two_bone(H, K, A, D)
        r1 = (K - H).rotation_difference(K2 - H)
        up2 = about(H, r1) @ up_m
        leg1 = about(H, r1) @ leg_m
        A1 = about(H, r1) @ A
        r2 = (A1 - K2).rotation_difference(D2 - K2)
        leg2 = about(K2, r2) @ leg1
        foot2 = Matrix.Translation(D2) @ Rq.to_matrix().to_4x4() @ Matrix.Scale(foot_m.to_scale()[0], 4)
        return (up2, leg2, foot2, w * amount if flatten else 0.0), short

    # Where a straightened leg can't reach a flat foot, lower the hips a little (up to 3 cm more)...
    budget = [0.03] * n
    for _ in range(4):
        short = [max((solve(s, i, 1.0)[1] if weights[s][i] > 1e-3 else 0.0) for s in bones) for i in range(n)]
        if max(short) < 0.001:
            break
        extra = smooth([min(x * 1.1, b) for x, b in zip(short, budget)], 2)
        if max(extra) < 0.001:
            break
        for i, rec in enumerate(frames):
            budget[i] -= extra[i]
            shift = Matrix.Translation(Vector((0, 0, -extra[i])))
            for s in bones:
                rec[s] = [shift @ m for m in rec[s]]
            rec["drop"] -= extra[i]
            drop[i] -= extra[i]
    # ...and past that, let the heel come up just enough (a straight back leg pivots on its ball).
    lifted = 0
    for s in bones:
        for i, rec in enumerate(frames):
            if weights[s][i] <= 1e-3:
                continue
            new, short = solve(s, i, 1.0)
            if flatten and short > 0.001:
                lo, hi = 0.0, 1.0
                for _ in range(10):
                    mid = (lo + hi) / 2
                    if solve(s, i, mid)[1] > 0.001:
                        hi = mid
                    else:
                        lo = mid
                new = solve(s, i, lo)[0]
                lifted += 1
            rec[s + "_new"] = new

    # Pass 4: key the new pose.
    for i, rec in enumerate(frames):
        f = i + 1
        travel = rec.get("travel", Vector((0, 0, 0)))
        delta_world = travel + Vector((0, 0, rec["drop"]))
        delta_arm = Wi.to_3x3() @ delta_world
        hips.location = rec["hips_loc"] + hips_rest_arm_rot.inverted() @ delta_arm
        hips.keyframe_insert("location", frame=f, group=HIPS)
        for s, chain in bones.items():
            new = rec.get(s + "_new")
            if not new:
                continue
            up2, leg2, foot2, toe_w = new
            mats = [Wi @ up2, Wi @ leg2, Wi @ foot2]
            for k, pb in enumerate(chain[:3]):
                b = pb.bone
                if k == 0:
                    scene.frame_set(f)  # the hips as just keyed (lowered, in place)
                    par = pb.parent.matrix.copy()
                else:
                    par = mats[k - 1]
                rest_rel = b.parent.matrix_local.inverted() @ b.matrix_local
                basis = (par @ rest_rel).inverted() @ mats[k]
                q = basis.to_quaternion()
                if pb.rotation_quaternion.dot(q) < 0:
                    q = -q
                pb.rotation_quaternion = q
                pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)
            if toe_w > 0:
                toe = chain[3]
                q = rec[s + "_toe_basis"].slerp(Quaternion(), toe_w)
                toe.rotation_quaternion = q
                toe.keyframe_insert("rotation_quaternion", frame=f, group=toe.name)
    print(f"[ground] {clip_name}: {mode}, hips lowered {-max(drop) * 100:.1f} to {-min(drop) * 100:.1f} cm, "
          f"contact frames L {sum(x > 0.5 for x in weights['Left'])}, R {sum(x > 0.5 for x in weights['Right'])} of {n}, "
          f"heel let up in {lifted}"
          + (f", in place (removed {tread.length * FPS:.2f} m/s of travel)" if mode == "walk" else ""))


def push(target, action, clip_name):
    target.animation_data.action = None
    track = target.animation_data.nla_tracks.new()
    track.name = clip_name
    track.strips.new(clip_name, 1, action).name = clip_name


def main():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(WORK, "claude_materials.blend"))
    target = bpy.data.objects["Human.rig"]
    ref, ref_objs = import_clip(os.path.join(MIXAMO, "fighting_idle.fbx"))
    ref.animation_data.action = None
    for pb in ref.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    match_rest_pose(target, ref)
    apply_pose_as_rest(target)
    ratio = (target.matrix_world @ target.data.bones[HIPS].head_local).z / (ref.matrix_world @ ref.data.bones[HIPS].head_local).z
    remove(ref_objs)
    print(f"[rig] T-pose rest applied; hip ratio {ratio:.3f}")
    feet = Feet(target, bpy.data.objects["Human"])
    # The meshes don't need evaluating while clips are baked (much faster frame changes).
    hidden = [o for o in bpy.data.objects if o.type == "MESH" and not o.hide_viewport]
    for o in hidden:
        o.hide_viewport = True

    clips = sorted(p for p in glob.glob(os.path.join(MIXAMO, "*.fbx")) if "with_skin" not in p)
    clips += sorted(glob.glob(os.path.join(MIXAMO, "extra", "*.fbx")))
    for path in clips:
        name = os.path.splitext(os.path.basename(path))[0]
        src, objs = import_clip(path)
        action, floor = retarget(target, src, name, ratio, TRIM.get(name))
        src_action = src.animation_data.action
        remove(objs)
        if src_action:
            bpy.data.actions.remove(src_action)
        ground(target, action, floor, MODE.get(name, "none"), feet, name)
        push(target, action, name)
        print(f"[rig] {name}: {len(floor)} frames")
    for o in hidden:
        o.hide_viewport = False
    bpy.context.scene.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(WORK, "claude_rigged.blend"))
    print("[rig] done")


main()
