"""Raise sunken soles to the ground by spreading the lift over the whole lower leg (knee -> sole), so no single joint
stretches (lifting only the feet stretched Gigan's ankles). Only leg-weighted vertices below the knees move; the lift
fades from full at the lowest sole point to zero at knee height.
Usage: blender -b in.blend --python lift_soles.py -- <out.blend> [ground_z]"""
import sys, bpy
import numpy as np
args = sys.argv[sys.argv.index("--") + 1:]
out = args[0]
ground = float(args[1]) if len(args) > 1 else -0.2
body = bpy.data.objects["SK_GZPro_Gigan_FW"]
arm = bpy.data.objects["GZ1_Gigan"]
me = body.data
LEG = ("Thigh", "Calf", "Foot", "Toe0", "Toe01")
names = {g.index: g.name for g in body.vertex_groups}
knee = min(arm.data.bones[f"Bip01_{s}_Calf"].head_local.z for s in "LR")
co = np.array([v.co[:] for v in me.vertices])
low = co[:, 2].min()
need = ground - low
if need <= 0.05:
    print(f"[lift] soles already at {low:.2f}; nothing to do")
else:
    leg = np.array([sum(g.weight for g in v.groups if names[g.group].split("_")[-1] in LEG) for v in me.vertices])
    t = np.clip((knee - co[:, 2]) / (knee - low), 0, 1)  # 1 at the sole, 0 at the knee
    co[:, 2] += need * t * np.clip(leg, 0, 1)
    me.vertices.foreach_set("co", co.ravel())
    me.update()
    print(f"[lift] soles {low:.2f} -> {co[:, 2].min():.2f} (lift {need:.2f} spread over knee height {knee:.1f})")
bpy.ops.wm.save_as_mainfile(filepath=out)
