import sys, bpy
import numpy as np
from mathutils import kdtree
out, radius, iters, bones = sys.argv[sys.argv.index("--") + 1:]
radius, iters, ZONE = float(radius), int(iters), set(bones.split(","))
body = bpy.data.objects["SK_GZPro_Gigan_FW"]
me = body.data
names = [g.name for g in body.vertex_groups]
n, m = len(me.vertices), len(names)
W = np.zeros((n, m), dtype=np.float32)
for v in me.vertices:
    for g in v.groups:
        W[v.index, g.group] = g.weight
zone_cols = [names.index(b) for b in ZONE if b in names]
zone = np.nonzero(W[:, zone_cols].sum(1) > 0)[0]
co = np.array([v.co[:] for v in me.vertices])
kd = kdtree.KDTree(n)
for i, c in enumerate(co):
    kd.insert(c, i)
kd.balance()
nbrs = []
for vi in zone:
    hits = kd.find_range(co[vi], radius)
    idx = np.array([h[1] for h in hits])
    w = np.array([1.0 - h[2] / radius for h in hits]) + 1e-3
    nbrs.append((idx, w / w.sum()))
for _ in range(iters):
    new = W.copy()
    for vi, (idx, w) in zip(zone, nbrs):
        new[vi] = w @ W[idx]
    W = new
changed = 0
for vi in zone:
    row = W[vi]
    keep = np.argsort(-row)[:4]
    row2 = np.zeros_like(row)
    row2[keep] = row[keep]
    row2 /= max(row2.sum(), 1e-9)
    v = me.vertices[int(vi)]
    for g in list(v.groups):
        body.vertex_groups[g.group].remove([int(vi)])
    for k in keep:
        if row2[k] > 1e-4:
            body.vertex_groups[int(k)].add([int(vi)], float(row2[k]), "REPLACE")
print(f"[shells] smoothed {len(zone)} vertices within {radius} over {iters} passes "
      f"(avg {np.mean([len(i) for i, _ in nbrs]):.0f} neighbours)")
bpy.ops.wm.save_as_mainfile(filepath=out)
