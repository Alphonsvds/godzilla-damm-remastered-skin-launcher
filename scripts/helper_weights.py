import bpy
from collections import defaultdict
arm = bpy.data.objects["Gigan_FW_Armature"]
meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.parent == arm]
helpers = ["Bip01_Neck2", "Bip01_L_Hipfat_Mover", "Bip01_R_Hipfat_Mover", "Bip01_L_Armpit_Mover", "Bip01_R_Armpit_Mover",
           "Bip01_Rectus_Abdominis_Flexor", "Bip01_L_Femur_Twist", "Bip01_L_Deltoid_Twist_1", "Bip01_L_Deltoid_Twist_2", "Bip01_L_Toe1"]
stats = defaultdict(lambda: [0, 0.0, defaultdict(float)])
for ob in meshes:
    names = {g.index: g.name for g in ob.vertex_groups}
    for v in ob.data.vertices:
        ws = {names[g.group]: g.weight for g in v.groups if g.weight > 0}
        for h in helpers:
            if h in ws:
                s = stats[h]; s[0] += 1; s[1] += ws[h]
                for other, w in ws.items():
                    if other != h: s[2][other] += w
for h in helpers:
    n, tot, co = stats[h]
    top = sorted(co.items(), key=lambda x: -x[1])[:3]
    b = arm.data.bones[h]
    print(f"[hw] {h:30s} verts={n:4d} avgw={tot/max(n,1):.2f} parent={b.parent.name if b.parent else None:18s} shares-with={[(k, round(w,1)) for k, w in top]}")
