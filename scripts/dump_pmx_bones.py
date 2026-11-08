import bpy
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
ob = next(o for o in bpy.data.objects if o.type == "MESH")
from collections import Counter
c = Counter()
idx = {g.index: g.name for g in ob.vertex_groups}
for v in ob.data.vertices:
    if v.groups: c[idx[max(v.groups, key=lambda g: g.weight).group]] += 1
def walk(b, d):
    h = b.head_local
    print(f"[b] {'  '*d}{b.name} ({b.get('mmd_name_en','')}) z={h.z:.1f} y={h.y:.1f} x={h.x:.1f} verts={c[b.name]}")
    for ch in b.children: walk(ch, d + 1)
for b in arm.data.bones:
    if b.parent is None: walk(b, 0)
