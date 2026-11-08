import bpy
from collections import Counter
from mathutils import Vector
body = bpy.data.objects["SK_GZPro_Gigan_FW"]; arm = bpy.data.objects["GZ1_Gigan"]
idx = {g.index: g.name for g in body.vertex_groups}
pel = arm.data.bones["Bip01_Pelvis"].head_local; saw = arm.data.bones["Bip01_BuzzSaw"].head_local
head = arm.data.bones["Bip01_Head"].head_local
tip = arm.data.bones["Bip01_Tail16"].head_local
front = -1 if tip.y > pel.y else 1
print(f"[r] pelvis {tuple(round(x,1) for x in pel)} buzzsaw {tuple(round(x,1) for x in saw)} front sign {front}")
c = Counter(); n = 0; tailish = 0; zs = []
for v in body.data.vertices:
    if abs(v.co.x) < 6 and (v.co.y - pel.y) * front > 6 and 25 < v.co.z < 80:
        n += 1; zs.append(v.co.z)
        ws = {idx[g.group]: g.weight for g in v.groups}
        for k, w in ws.items(): c[k] += w
        if any(k.startswith("Bip01_Tail") or "Thigh" in k for k in ws): tailish += 1
print(f"[r] front-centre verts {n}, z {min(zs):.1f}..{max(zs):.1f}, touching tail/thigh bones: {tailish}")
print("[r] weight by bone:", [(k, round(w, 1)) for k, w in c.most_common(10)])
print(f"[r] lowest vertex z {min(v.co.z for v in body.data.vertices):.1f}")
