import sys
import bpy
from mathutils.geometry import intersect_point_line

out_blend, factor = sys.argv[sys.argv.index("--") + 1:]
factor = float(factor)
body = bpy.data.objects["SK_GZPro_Gigan_FW"]
arm = bpy.data.objects["GZ1_Gigan"]
me = body.data
H = {b.name: b.head_local.copy() for b in arm.data.bones}
plate = [False] * len(me.vertices)
if "is_plate" in me.attributes:
    me.attributes["is_plate"].data.foreach_get("value", plate)
names = {g.index: g.name for g in body.vertex_groups}

def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)

moved = 0
for v in me.vertices:
    if plate[v.index]:
        continue
    for g in v.groups:
        n = names[g.group]
        if not n.endswith("_Thigh") or g.weight <= 0:
            continue
        side = n[6]
        hip, knee = H[n], H[f"Bip01_{side}_Calf"]
        p, t = intersect_point_line(v.co, hip, knee)
        fade = smooth(t / 0.3) * smooth((1.0 - t) / 0.2)
        k = 1.0 - (1.0 - factor) * g.weight * fade
        if k < 1.0:
            v.co = p + (v.co - p) * k
            moved += 1
print(f"[thighs] slimmed {moved} vertices toward the thigh bones (factor {factor})")
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
