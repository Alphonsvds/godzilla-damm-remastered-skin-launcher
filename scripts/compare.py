"""Load the Wii FW Gigan .blend, import the Remastered SK_GZPro_Gigan .glb next to it, report
sizes / rest poses and render a side-by-side.
Usage: blender -b gigan_fw_wii.blend --python compare.py -- <SK_GZPro_Gigan.glb> <out.png> <report.txt>
"""
import sys, math, bpy
from mathutils import Vector

glb, out_png, report = sys.argv[sys.argv.index("--") + 1:]
lines = []

before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=glb)
game_objs = [o for o in bpy.data.objects if o not in before]
game_arm = next(o for o in game_objs if o.type == "ARMATURE")
wii_arm = bpy.data.objects["Gigan_FW_Armature"]


def bounds(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs if o.type == "MESH" for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return lo, hi


wii_objs = [o for o in bpy.data.objects if o.parent == wii_arm]
for label, objs in (("wii", wii_objs), ("game", game_objs)):
    lo, hi = bounds(objs)
    lines.append(f"{label} bounds min={tuple(round(v, 2) for v in lo)} max={tuple(round(v, 2) for v in hi)} size={tuple(round(v, 2) for v in hi - lo)}")
lines.append(f"game armature: {game_arm.name} scale={tuple(round(v, 4) for v in game_arm.matrix_world.to_scale())} bones={len(game_arm.data.bones)}")
for o in game_objs:
    if o.type == "MESH":
        lines.append(f"game mesh {o.name}: {len(o.data.vertices)} verts, mats={[m.name for m in o.data.materials]}")

# Compare world-space joint positions for bones both rigs share.
def wpos(arm, name):
    b = arm.data.bones.get(name)
    return None if b is None else arm.matrix_world @ b.head_local

lo_w, hi_w = bounds(wii_objs)
lo_g, hi_g = bounds(game_objs)
scale = (hi_g.z - lo_g.z) / (hi_w.z - lo_w.z)
lines.append(f"height ratio game/wii = {scale:.4f}")
for name in ("Bip01", "Bip01_Pelvis", "Bip01_Spine1", "Bip01_Head", "Bip01_L_UpperArm", "Bip01_L_Hand",
             "Bip01_R_Hand", "Bip01_L_Thigh", "Bip01_L_Foot", "Bip01_BuzzSaw", "Lift_Node"):
    pw, pg = wpos(wii_arm, name), wpos(game_arm, name)
    lines.append(f"  {name:20s} wii*s={tuple(round(v, 1) for v in pw * scale) if pw else None}  game={tuple(round(v, 1) for v in pg) if pg else None}")

open(report, "w").write("\n".join(lines))
print("\n".join(lines))

# Side-by-side render: scale Wii to game height and place it to the right.
wii_arm.scale = (scale, scale, scale)
bpy.context.view_layer.update()
lo_w, hi_w = bounds(wii_objs)
wii_arm.location.x += (hi_g.x - lo_w.x) + (hi_g.x - lo_g.x) * 0.15
bpy.context.view_layer.update()
lo, hi = bounds(wii_objs + game_objs)
ctr, size = (lo + hi) / 2, hi - lo
scn = bpy.context.scene
scn.render.engine = "BLENDER_WORKBENCH"
scn.display.shading.color_type = "TEXTURE"
scn.display.shading.light = "STUDIO"
scn.render.resolution_x, scn.render.resolution_y = 1600, 900
cam_data = bpy.data.cameras.new("cmpcam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = max(size.x, size.z * 16 / 9) * 1.1
cam = bpy.data.objects.new("cmpcam", cam_data)
scn.collection.objects.link(cam)
scn.camera = cam
a = math.radians(160)
d = max(size) * 4
cam.location = ctr + Vector((math.sin(a) * d, -math.cos(a) * d, 0))
cam.rotation_euler = (math.radians(90), 0, a)
scn.render.filepath = out_png
bpy.ops.render.render(write_still=True)
