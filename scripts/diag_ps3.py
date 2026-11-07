import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from gzrig import game_world, build_armature, umeyama

bones_json = sys.argv[sys.argv.index("--") + 1]
gw, gorder = game_world(bones_json)
game = build_armature("GZ1_Gigan", gw, gorder, 0.01)
G = {b.name: b.head_local.copy() for b in game.data.bones}
ps3 = bpy.data.objects["Gigan_PS3_Armature"]
J = {b.name: b.head_local.copy() for b in ps3.data.bones}

core = {"joint1": "Bip01_Pelvis", "joint2": "Bip01_Spine", "joint3": "Bip01_Spine1", "joint5": "Bip01_Neck",
        "joint13": "Bip01_Neck1", "joint14": "Bip01_Head", "joint35": "Bip01_Tail"}
legs = [("joint27", "joint31"), ("joint28", "joint32"), ("joint29", "joint33")]
M, s = umeyama([J[k] for k in core], [G[v] for v in core.values()])
print(f"[d] align scale {s:.3f}")
A = {k: M @ v for k, v in J.items()}
for side, a in (("L", "joint7"), ("R", "joint20")):
    print(f"[d] {a} aligned {tuple(round(x, 1) for x in A[a])}  game L_Clav {tuple(round(x, 1) for x in G['Bip01_L_Clavicle'])} R_Clav {tuple(round(x, 1) for x in G['Bip01_R_Clavicle'])}")
for a, b in (("joint7", "joint8"), ("joint8", "joint9"), ("joint9", "joint10"), ("joint10", "joint11"),
             ("joint27", "joint28"), ("joint28", "joint29"), ("joint29", "joint30"), ("joint1", "joint2"), ("joint5", "joint13"), ("joint13", "joint14")):
    print(f"[d] ps3 {a}->{b}: {(A[b] - A[a]).length:6.1f}")
for a, b in (("Bip01_L_Clavicle", "Bip01_L_UpperArm"), ("Bip01_L_UpperArm", "Bip01_L_Forearm"), ("Bip01_L_Forearm", "Bip01_L_Hand"),
             ("Bip01_L_Thigh", "Bip01_L_Calf"), ("Bip01_L_Calf", "Bip01_L_Foot"), ("Bip01_L_Foot", "Bip01_L_Toe0"), ("Bip01_Pelvis", "Bip01_Spine"), ("Bip01_Neck", "Bip01_Neck1"), ("Bip01_Neck1", "Bip01_Head")):
    print(f"[d] game {a}->{b}: {(G[b] - G[a]).length:6.1f}")
for k, v in core.items():
    print(f"[d] core err {k}->{v}: {(A[k] - G[v]).length:5.1f}")
for j in ("joint7", "joint8", "joint9", "joint10", "joint11"):
    near = min(("Bip01_L_Clavicle", "Bip01_L_UpperArm", "Bip01_L_Forearm", "Bip01_L_Hand", "Bip01_R_Clavicle", "Bip01_R_UpperArm", "Bip01_R_Forearm", "Bip01_R_Hand"), key=lambda n: (G[n] - A[j]).length)
    print(f"[d] {j} nearest game bone {near} ({(G[near] - A[j]).length:.1f})")
