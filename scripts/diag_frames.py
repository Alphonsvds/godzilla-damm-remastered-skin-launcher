import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from gzrig import game_world, wii_world, rot_only, umeyama

bones_json = sys.argv[sys.argv.index("--") + 1]
gw, gorder = game_world(bones_json)
ww = wii_world(bpy.data.objects["Gigan_FW_Armature"])

core = ["Bip01_Pelvis", "Bip01_Spine", "Bip01_Spine1", "Bip01_Neck", "Bip01_Neck1", "Bip01_Head",
        "Bip01_L_Clavicle", "Bip01_R_Clavicle", "Bip01_L_Thigh", "Bip01_R_Thigh", "Bip01_L_Calf", "Bip01_R_Calf",
        "Bip01_L_Foot", "Bip01_R_Foot"]
M, s = umeyama([ww[n][1].translation for n in core], [gw[n][1].translation for n in core])
yaw = math.degrees(math.atan2(M[1][0], M[0][0]))
print(f"[diag] align scale={s:.3f} yaw={yaw:.1f} deg")
for n in core:
    err = (M @ ww[n][1].translation - gw[n][1].translation).length
    print(f"[diag] pos err {n:18s} {err:8.1f}  (game units)")

Ralign = rot_only(M)
print("[diag] per-bone frame difference (deg) and axis, Wii(aligned) -> game:")
for n in gorder:
    if n not in ww:
        continue
    rw = Ralign @ rot_only(ww[n][1])
    rg = rot_only(gw[n][1])
    d = (rw.inverted() @ rg).to_quaternion()
    ang = math.degrees(d.angle)
    ax = d.axis
    print(f"[diag]   {n:20s} {ang:6.1f}  local axis=({ax.x:+.2f},{ax.y:+.2f},{ax.z:+.2f})")
