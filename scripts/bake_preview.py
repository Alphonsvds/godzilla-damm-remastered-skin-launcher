"""Bake game animations onto the fitted Final Wars Gigan so they can be played back in Blender.
Root motion is removed so Gigan stays in place. Each animation gets a timeline marker.
Usage: blender -b gigan_fw_fitted.blend --python bake_preview.py -- <bones.json> <out.blend> <anim.json>...
"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from gzrig import game_world, anim_frame_world, apply_pose

args = sys.argv[sys.argv.index("--") + 1:]
bones_json, out_blend, anims = args[0], args[1], args[2:]
gw, order = game_world(bones_json)
parents = {n: gw[n][0] for n in order}
arm = bpy.data.objects["GZ1_Gigan"]
scn = bpy.context.scene
scn.render.fps = 30

arm.animation_data_create()
arm.animation_data.action = bpy.data.actions.new("GameAnims_on_FinalWars")
start = 1
for path in anims:
    anim = json.load(open(path, encoding="utf-8-sig"))
    scn.timeline_markers.new(anim["name"], frame=start)
    for f in range(len(anim["frames"])):
        frame = [dict(b) for b in anim["frames"][f]]
        frame[0] = dict(frame[0], t=[0.0, 0.0, 0.0])  # strip GiganRoot root motion
        apply_pose(arm, anim_frame_world({"bones": anim["bones"], "frames": [frame]}, 0, parents, 0.01))
        for pb in arm.pose.bones:
            pb.keyframe_insert("location", frame=start + f)
            pb.keyframe_insert("rotation_quaternion", frame=start + f)
    print(f"[bake] {anim['name']}: frames {start}-{start + len(anim['frames']) - 1}")
    start += len(anim["frames"]) + 10  # short hold between moves
scn.frame_start, scn.frame_end = 1, start - 10

cam_data = bpy.data.cameras.new("Camera")
cam = bpy.data.objects.new("Camera", cam_data)
scn.collection.objects.link(cam)
a = math.radians(-35)
cam.location = (math.sin(a) * 420, -math.cos(a) * 420, 75)
cam.rotation_euler = (math.radians(86), 0, a)
cam_data.lens = 35
cam_data.clip_end = 5000
scn.camera = cam
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
sun.rotation_euler = (math.radians(50), 0, math.radians(-30))
scn.collection.objects.link(sun)
scn.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
print("[bake] saved", out_blend)
