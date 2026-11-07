import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from collections import Counter
from gzrig import game_world, anim_frame_world, apply_pose
bones_json, anim_json = sys.argv[sys.argv.index("--") + 1:]
gw, order = game_world(bones_json); parents = {n: gw[n][0] for n in order}
arm = bpy.data.objects["GZ1_Gigan"]; body = bpy.data.objects["SK_GZPro_Gigan_FW"]
anim = json.load(open(anim_json))
apply_pose(arm, anim_frame_world(anim, 12, parents, 0.01)); bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg).to_mesh()
pelvis = arm.pose.bones["Bip01_Pelvis"].matrix.translation
far = sorted(range(len(ev.vertices)), key=lambda i: -(ev.vertices[i].co - pelvis).length)[:40]
names = {g.index: g.name for g in body.vertex_groups}
c = Counter()
for i in far:
    for ge in body.data.vertices[i].groups:
        if ge.weight > 0.05: c[names[ge.group]] += 1
print("[dbg] farthest vertex dist", round((ev.vertices[far[0]].co - pelvis).length, 1), "rest", round((body.data.vertices[far[0]].co - arm.data.bones['Bip01_Pelvis'].head_local).length,1))
print("[dbg] groups on far verts", c.most_common(10))
v = body.data.vertices[far[0]]
print("[dbg] one far vert rest", tuple(round(x,1) for x in v.co), [(names[g.group], round(g.weight,3)) for g in v.groups])
for n in ["Bip01_Tail14","Bip01_Tail15","Bip01_Tail16","Lift_Node","GiganRoot","gigan_body"]:
    print("[dbg]", n, "rest", tuple(round(x,1) for x in arm.data.bones[n].head_local), "posed", tuple(round(x,1) for x in arm.pose.bones[n].matrix.translation))
