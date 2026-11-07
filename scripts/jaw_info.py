import bpy
from mathutils import Vector
body = bpy.data.objects["SK_GZPro_Gigan_FW"]; arm = bpy.data.objects["GZ1_Gigan"]
idx = {g.index: g.name for g in body.vertex_groups}
for bone in ("Bip01_Ponytail1", "Bip01_Head"):
    vs = [v for v in body.data.vertices if any(idx[g.group] == bone and g.weight > 0.3 for g in v.groups)]
    if vs:
        c = sum((v.co for v in vs), Vector()) / len(vs)
        print(f"[jaw] {bone}: {len(vs)} verts, centroid={tuple(round(x,1) for x in c)}")
b = arm.data.bones["Bip01_Ponytail1"]; h = arm.data.bones["Bip01_Head"]
print(f"[jaw] Ponytail1 head={tuple(round(x,1) for x in b.head_local)} Head bone head={tuple(round(x,1) for x in h.head_local)}")
