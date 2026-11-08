import sys
import bpy

args = sys.argv[sys.argv.index("--") + 1:]
out_blend = args[0]
floor = float(args[1]) if len(args) > 1 else -0.6

body = bpy.data.objects["SK_GZPro_Gigan_FW"]
idx = {g.index: g.name for g in body.vertex_groups}
FOOT = ("_Foot", "_Toe0", "_Toe01")

def drive(v):
    foot = sum(g.weight for g in v.groups if idx[g.group].endswith(FOOT))
    calf = sum(g.weight for g in v.groups if idx[g.group].endswith("_Calf"))
    return foot + 0.5 * calf

low = min((v.co.z for v in body.data.vertices if drive(v) > 0.5), default=floor)
lift = max(0.0, floor - low)
for v in body.data.vertices:
    d = drive(v)
    if d > 0:
        v.co.z += lift * min(1.0, d)
body.data.update()
print(f"[feet] lifted soles by {lift:.2f} (lowest foot vertex was {low:.2f})")
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
