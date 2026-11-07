import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from gzrig import game_world, build_armature, anim_frame_world, apply_pose

bones_json = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
gw, order = game_world(bones_json)
arm = build_armature("GZ1_Gigan", gw, order, 0.01)
ref = json.load(open(bones_json))["bones"]
anim = {"bones": [b["name"] for b in ref], "frames": [ref]}
parents = {n: gw[n][0] for n in order}
pose = anim_frame_world(anim, 0, parents, 0.01)
worst = 0
for n in order:
    d = max(abs(a - b) for ra, rb in zip(pose[n], arm.data.bones[n].matrix_local) for a, b in zip(ra, rb))
    worst = max(worst, d)
    if d > 1e-3:
        print(f"[dbg] target vs rest {n}: {d:.4f}")
print(f"[dbg] worst target-vs-rest {worst:.5f}")
apply_pose(arm, pose)
bpy.context.view_layer.update()
worst = 0
for pb in arm.pose.bones:
    d = max(abs(a - b) for ra, rb in zip(pb.matrix, pose[pb.name]) for a, b in zip(ra, rb))
    worst = max(worst, d)
print(f"[dbg] worst posed-vs-target {worst:.5f}")
print("[dbg] sample basis", arm.pose.bones["Bip01_Spine"].matrix_basis)
