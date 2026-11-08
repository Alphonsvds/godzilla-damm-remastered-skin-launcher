"""Smooth skin weights across the hip seam (pelvis <-> thighs) so the belly's lower edge and the thigh move together
instead of tearing apart when the legs swing. Only vertices that already use one of the hip bones are touched, and
only those bones' weights are smoothed (tail and spine weights stay as they are).
Usage: blender -b in.blend --python smooth_hips.py -- <out.blend> [iterations] [factor] [bone,bone,...]"""
import sys, bpy
import numpy as np
args = sys.argv[sys.argv.index("--") + 1:]
out = args[0]
iters = int(args[1]) if len(args) > 1 else 8
fac = float(args[2]) if len(args) > 2 else 0.5
HIP = (args[3].split(",") if len(args) > 3 else ["Bip01_Pelvis", "Bip01_L_Thigh", "Bip01_R_Thigh"])
body = bpy.data.objects["SK_GZPro_Gigan_FW"]
me = body.data
n = len(me.vertices)
gi = {g.name: g.index for g in body.vertex_groups}
W = np.zeros((n, len(HIP)))
other = np.zeros(n)
for v in me.vertices:
    for g in v.groups:
        name = body.vertex_groups[g.group].name
        if name in HIP:
            W[v.index, HIP.index(name)] = g.weight
        else:
            other[v.index] += g.weight
hip_total = W.sum(1)
touched = (W > 0).sum(1) > 0
# neighbours by edges
e = np.empty(len(me.edges) * 2, dtype=np.int64)
me.edges.foreach_get("vertices", e)
e = e.reshape(-1, 2)
deg = np.bincount(e.ravel(), minlength=n).astype(float)
share = np.where((hip_total > 0)[:, None], W / np.maximum(hip_total, 1e-9)[:, None], 0.0)  # hip weights as shares
for _ in range(iters):
    acc = np.zeros_like(share)
    np.add.at(acc, e[:, 0], share[e[:, 1]])
    np.add.at(acc, e[:, 1], share[e[:, 0]])
    avg = acc / np.maximum(deg, 1)[:, None]
    has = avg.sum(1) > 0
    upd = touched & has
    share[upd] = (1 - fac) * share[upd] + fac * avg[upd] / avg[upd].sum(1, keepdims=True)
newW = share * hip_total[:, None]
changed = 0
for k, name in enumerate(HIP):
    grp = body.vertex_groups[name]
    for vi in np.nonzero(touched)[0]:
        w = float(newW[vi, k])
        if w > 1e-4:
            grp.add([int(vi)], w, "REPLACE")
        elif W[vi, k] > 0:
            grp.remove([int(vi)])
        changed += abs(w - W[vi, k]) > 0.02
print(f"[hips] smoothed {touched.sum()} hip vertices, {changed} weights changed noticeably")
with bpy.context.temp_override(object=body, active_object=body, selected_objects=[body]):
    bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
bpy.ops.wm.save_as_mainfile(filepath=out)
