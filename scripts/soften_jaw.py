import sys
import bpy

args = sys.argv[sys.argv.index("--") + 1:]
out_blend = args[0]
share = float(args[1]) if len(args) > 1 else 0.6

body = bpy.data.objects["SK_GZPro_Gigan_FW"]
jaw = body.vertex_groups["Bip01_Ponytail1"]
head = body.vertex_groups["Bip01_Head"]
n = 0
for v in body.data.vertices:
    w = next((g.weight for g in v.groups if g.group == jaw.index), 0.0)
    if w <= 0:
        continue
    jaw.add([v.index], w * share, "REPLACE")
    head.add([v.index], w * (1 - share), "ADD")
    n += 1
print(f"[jaw] softened {n} jaw vertices to {share:.0%} of the animated opening")
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
