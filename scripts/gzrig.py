import json, math
import bpy
from mathutils import Matrix, Quaternion, Vector

TO_BONE = Matrix.Rotation(math.radians(-90), 4, "Z")
FLIP = Matrix.Diagonal((1, -1, 1, 1))

def ue_local(b):
    t = Matrix.Translation(Vector(b["t"]))
    x, y, z, w = b["q"]
    r = Quaternion((w, x, y, z)).to_matrix().to_4x4()
    s = Matrix.Diagonal((*b["s"], 1))
    return t @ r @ s

def game_world(bones_json):
    bones = json.load(open(bones_json))["bones"]
    world_ue, out = [], {}
    for b in bones:
        local = ue_local(b)
        w = local if b["parent"] < 0 else world_ue[b["parent"]] @ local
        world_ue.append(w)
        out[b["name"]] = (bones[b["parent"]]["name"] if b["parent"] >= 0 else None, FLIP @ w @ FLIP)
    return out, [b["name"] for b in bones]

def rot_only(m):
    return m.to_3x3().normalized().to_4x4()

def wii_world(arm):
    return {b.name: (b.parent.name if b.parent else None, arm.matrix_world @ b.matrix_local @ TO_BONE.inverted())
            for b in arm.data.bones}

def build_armature(name, world, order, unit_scale=1.0):
    data = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    for nm in order:
        m = world[nm][1]
        eb = data.edit_bones.new(nm)
        eb.head, eb.tail = (0, 0, 0), (0, 3.0, 0)
        frame = rot_only(m) @ TO_BONE
        frame.translation = m.translation * unit_scale
        eb.matrix = frame
    for nm in order:
        if world[nm][0]:
            data.edit_bones[nm].parent = data.edit_bones[world[nm][0]]
    bpy.ops.object.mode_set(mode="OBJECT")
    return ob

def anim_frame_world(anim, frame, parents, unit_scale):
    names = anim["bones"]
    world_ue, out = {}, {}
    for i, nm in enumerate(names):
        local = ue_local(anim["frames"][frame][i])
        p = parents[nm]
        w = local if p is None else world_ue[p] @ local
        world_ue[nm] = w
        m = FLIP @ w @ FLIP
        f = rot_only(m) @ TO_BONE
        f.translation = m.translation * unit_scale
        out[nm] = f
    return out

def apply_pose(arm, pose):
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
    def solved(pb):
        return pose.get(pb.name) if pb.name in pose else (
            solved(pb.parent) @ pb.parent.bone.matrix_local.inverted() @ pb.bone.matrix_local if pb.parent else pb.bone.matrix_local)
    for pb in arm.pose.bones:
        P = solved(pb)
        if pb.parent:
            Pp = solved(pb.parent)
            rest_rel = pb.parent.bone.matrix_local.inverted() @ pb.bone.matrix_local
            pb.matrix_basis = rest_rel.inverted() @ Pp.inverted() @ P
        else:
            pb.matrix_basis = pb.bone.matrix_local.inverted() @ P

def umeyama(src, dst, with_scale=True):
    import numpy as np
    A, B = np.array([tuple(p) for p in src]), np.array([tuple(p) for p in dst])
    ma, mb = A.mean(0), B.mean(0)
    A0, B0 = A - ma, B - mb
    U, S, Vt = np.linalg.svd(B0.T @ A0 / len(A))
    D = np.eye(3)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0:
        D[2, 2] = -1
    R = U @ D @ Vt
    s = (S * np.diag(D)).sum() / A0.var(0).sum() if with_scale else 1.0
    t = mb - s * R @ ma
    M = Matrix.Identity(4)
    for i in range(3):
        for j in range(3):
            M[i][j] = s * R[i, j]
        M[i][3] = t[i]
    return M, s
