import sys, bpy
from collections import Counter
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
counts = Counter()
for o in bpy.data.objects:
    if o.type == "MESH":
        idx = {g.index: g.name for g in o.vertex_groups}
        for v in o.data.vertices:
            for g in v.groups:
                if g.weight > 0.3: counts[idx[g.group]] += 1
def walk(b, d):
    h = b.head_local
    print(f"[j] {'  '*d}{b.name:10s} pos=({h.x:6.1f},{h.y:6.1f},{h.z:6.1f}) verts={counts[b.name]}")
    for c in sorted(b.children, key=lambda c: int(c.name[5:])):
        walk(c, d + 1)
for b in arm.data.bones:
    if b.parent is None: walk(b, 0)
