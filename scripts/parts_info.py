import bpy
from collections import Counter
from mathutils import Vector
body = bpy.data.objects["SK_GZPro_Gigan_FW"]
me = body.data
idx = {g.index: g.name for g in body.vertex_groups}
dom = Counter()
for v in me.vertices:
    if v.groups:
        dom[idx[max(v.groups, key=lambda g: g.weight).group]] += 1
print("[p] dominant-bone vertex counts (arms):", {k: n for k, n in dom.items() if any(s in k for s in ("Hand", "Forearm", "UpperArm", "Clavicle"))})
uv = me.uv_layers.active.data
us = [l.uv[0] for l in uv]; vs = [l.uv[1] for l in uv]
print(f"[p] UV range u {min(us):.3f}..{max(us):.3f} v {min(vs):.3f}..{max(vs):.3f}")
for side in ("L", "R"):
    for bone in (f"Bip01_{side}_Hand", f"Bip01_{side}_Forearm"):
        pts = [v.co for v in me.vertices if v.groups and idx[max(v.groups, key=lambda g: g.weight).group] == bone]
        if pts:
            lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
            print(f"[p] {bone}: {len(pts)} verts, box {tuple(round(x,1) for x in lo)}..{tuple(round(x,1) for x in hi)}")
