"""Play game animations on the fitted Final Wars Gigan (open gigan_fw_fitted.blend).
Usage: blender -b gigan_fw_fitted.blend --python fitted_anim_test.py -- <bones.json> <out_prefix> <anim.json>:<f,f,f> ...
"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from gzrig import game_world, anim_frame_world, apply_pose

args = sys.argv[sys.argv.index("--") + 1:]
bones_json, out_prefix, specs = args[0], args[1], args[2:]
gw, order = game_world(bones_json)
parents = {n: gw[n][0] for n in order}
arm = bpy.data.objects["GZ1_Gigan"]

scn = bpy.context.scene
scn.render.engine = "BLENDER_WORKBENCH"
scn.display.shading.color_type = "TEXTURE"
scn.display.shading.light = "STUDIO"
scn.render.resolution_x, scn.render.resolution_y = 700, 700
scn.world = bpy.data.worlds.new("w")
cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = 220
cam = bpy.data.objects.new("cam", cam_data)
scn.collection.objects.link(cam)
scn.camera = cam
a = math.radians(-35)
cam.location = (math.sin(a) * 600, -math.cos(a) * 600 + 20, 60)
cam.rotation_euler = (math.radians(90), 0, a)

for spec in specs:
    path, frames = spec.rsplit(":", 1)
    anim = json.load(open(path, encoding="utf-8-sig"))
    for f in [int(x) for x in frames.split(",")]:
        f = min(f, len(anim["frames"]) - 1)
        apply_pose(arm, anim_frame_world(anim, f, parents, 0.01))
        bpy.context.view_layer.update()
        scn.render.filepath = f"{out_prefix}_{anim['name']}_{f:03d}.png"
        bpy.ops.render.render(write_still=True)
        print("[anim] rendered", scn.render.filepath)
