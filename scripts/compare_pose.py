import sys, os, json, math
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from mathutils import Matrix, Vector
from gzrig import game_world, build_armature, anim_frame_world, apply_pose

bones_json, glb, anim_json, frame, out_prefix = sys.argv[sys.argv.index("--") + 1:]
frame = int(frame)
gw, order = game_world(bones_json)
parents = {n: gw[n][0] for n in order}
fw_arm = bpy.data.objects["GZ1_Gigan"]

game_arm = build_armature("GameRig", gw, order, 0.01)
bpy.ops.import_scene.gltf(filepath=glb)
mesh = next(o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("SK_GZPro_Gigan") and o.name != "SK_GZPro_Gigan_FW")
for m in list(mesh.modifiers):
    mesh.modifiers.remove(m)
mw = mesh.matrix_world.copy()
mesh.parent = None
mesh.data.transform(Matrix.Scale(100, 4) @ mw)
mesh.matrix_world = Matrix.Identity(4)
for o in list(bpy.data.objects):
    if o.type in ("ARMATURE", "MESH") and o not in (fw_arm, game_arm, mesh) and o.parent is None and o.name != "SK_GZPro_Gigan_FW":
        if o.type == "ARMATURE" or o.name.startswith("Icosphere"):
            bpy.data.objects.remove(o)
mesh.parent = game_arm
mesh.modifiers.new("Armature", "ARMATURE").object = game_arm

anim = json.load(open(anim_json, encoding="utf-8-sig"))
pose = anim_frame_world(anim, frame, parents, 0.01)
root = pose["GiganRoot"].translation.copy()
for k in pose:
    pose[k] = Matrix.Translation(-Vector((root.x, root.y, 0))) @ pose[k]
apply_pose(fw_arm, pose)
apply_pose(game_arm, pose)
bpy.context.view_layer.update()

scn = bpy.context.scene
scn.render.engine = "BLENDER_WORKBENCH"
scn.display.shading.color_type = "TEXTURE"
scn.display.shading.light = "STUDIO"
scn.render.resolution_x, scn.render.resolution_y = 600, 700
scn.world = bpy.data.worlds.get("w") or bpy.data.worlds.new("w")
cd = bpy.data.cameras.new("cmp")
cd.type = "ORTHO"
cd.ortho_scale = 190
cam = bpy.data.objects.new("cmp", cd)
scn.collection.objects.link(cam)
scn.camera = cam
fw_body = bpy.data.objects["SK_GZPro_Gigan_FW"]
center = pose["Bip01_Pelvis"].translation.copy()
center.z = 60
for who, show, hide in (("fw", fw_body, mesh), ("game", mesh, fw_body)):
    show.hide_render, hide.hide_render = False, True
    for label, ang in (("front", -20), ("side", 75)):
        a = math.radians(ang)
        cam.location = center + Vector((math.sin(a) * 800, -math.cos(a) * 800, 0))
        cam.rotation_euler = (math.radians(90), 0, a)
        scn.render.filepath = f"{out_prefix}_{who}_{label}.png"
        bpy.ops.render.render(write_still=True)
        print("[cmp] rendered", scn.render.filepath)
