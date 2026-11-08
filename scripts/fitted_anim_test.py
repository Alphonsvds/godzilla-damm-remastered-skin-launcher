import sys, os, json, math
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from mathutils import Vector
from gzrig import game_world, anim_frame_world, apply_pose

args = sys.argv[sys.argv.index("--") + 1:]
bones_json, out_prefix, specs = args[0], args[1], args[2:]
gw, order = game_world(bones_json)
parents = {n: gw[n][0] for n in order}
arm = bpy.data.objects["GZ1_Gigan"]
OWN = set(filter(None, os.environ.get("ANIM_OWN", "").split(",")))

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
a = math.radians(float(os.environ.get("ANIM_ANGLE", "-35")))
cam.location = (math.sin(a) * 600, -math.cos(a) * 600 + 20, 60)
cam.rotation_euler = (math.radians(90), 0, a)

for spec in specs:
    path, frames = spec.rsplit(":", 1)
    anim = json.load(open(path, encoding="utf-8-sig"))
    for f in [int(x) for x in frames.split(",")]:
        f = min(f, len(anim["frames"]) - 1)
        pose = anim_frame_world(anim, f, parents, 0.01)
        if OWN:
            rest = {b.name: b.matrix_local for b in arm.data.bones}
            local = {n: pose[parents[n]].inverted() @ pose[n] for n in order if n in pose and parents[n] in pose}
            for n in order:
                if n in local:
                    L = local[n].copy()
                    if n in OWN:
                        L.translation = (rest[parents[n]].inverted() @ rest[n]).translation
                    pose[n] = pose[parents[n]] @ L
        apply_pose(arm, pose)
        bpy.context.view_layer.update()
        if os.environ.get("ANIM_FRAME"):
            scn.view_settings.exposure = float(os.environ.get("ANIM_EXPOSURE", "0"))
            deps = bpy.context.evaluated_depsgraph_get()
            pts = []
            for ob in (o for o in scn.objects if o.type == "MESH"):
                ev = ob.evaluated_get(deps)
                pts += [ob.matrix_world @ v.co for v in ev.to_mesh().vertices]
                ev.to_mesh_clear()
            c = sum(pts, Vector()) / len(pts)
            ext = max((p - c).length for p in pts)
            cam_data.ortho_scale = ext * 2.05
            if os.environ.get("ANIM_FOCUS"):
                zoom, fz = (float(x) for x in os.environ["ANIM_FOCUS"].split(","))
                zs = [p.z for p in pts]
                c = Vector((c.x, c.y, min(zs) + (max(zs) - min(zs)) * fz))
                cam_data.ortho_scale = ext * 2.05 / zoom
            cam.location = (c.x + math.sin(a) * 600, c.y - math.cos(a) * 600, c.z)
        scn.render.filepath = f"{out_prefix}_{anim['name']}_{f:03d}.png"
        bpy.ops.render.render(write_still=True)
        print("[anim] rendered", scn.render.filepath)
