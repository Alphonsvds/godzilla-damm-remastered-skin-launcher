import sys
import bpy

out_blend = sys.argv[sys.argv.index("--") + 1]
body = bpy.data.objects["SK_GZPro_Gigan_FW"]
arm = body.parent
chain = [(n, arm.data.bones[n].head_local.z) for n in ("Bip01_Spine", "Bip01_Spine1", "Bip01_Neck")]
saw = body.vertex_groups["Bip01_BuzzSaw"]
groups = {n: body.vertex_groups.get(n) or body.vertex_groups.new(name=n) for n, _ in chain}

moved = 0
for v in body.data.vertices:
    w = next((g.weight for g in v.groups if g.group == saw.index), 0.0)
    if w <= 0:
        continue
    z = v.co.z
    if z <= chain[0][1]:
        parts = [(chain[0][0], 1.0)]
    elif z >= chain[-1][1]:
        parts = [(chain[-1][0], 1.0)]
    else:
        for (a, za), (b, zb) in zip(chain, chain[1:]):
            if za <= z <= zb:
                t = (z - za) / (zb - za)
                parts = [(a, 1 - t), (b, t)]
                break
    for name, f in parts:
        groups[name].add([v.index], w * f, "ADD")
    moved += 1
body.vertex_groups.remove(saw)
print(f"[ridge] moved {moved} ridge vertices from BuzzSaw onto {[n for n, _ in chain]}")
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
