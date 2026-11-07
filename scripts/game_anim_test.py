"""Sanity check: rebuild the game skeleton from the bone dump, bind the game's own mesh to it and play a
game animation. If this looks right, the bone/animation conversion is right.
Usage: blender -b --python game_anim_test.py -- <bones.json> <mesh.glb> <anim.json> <out_prefix> <frames,comma,list>
"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from mathutils import Vector, Matrix
from gzrig import game_world, build_armature, anim_frame_world, apply_pose

bones_json, glb, anim_json, out_prefix, frames = sys.argv[sys.argv.index("--") + 1:]
UNIT = 0.01  # glb mesh is in metres (UE cm / 100)

bpy.ops.wm.read_factory_settings(use_empty=True)
gw, order = game_world(bones_json)
arm = build_armature("GZ1_Gigan", gw, order, UNIT)

bpy.ops.import_scene.gltf(filepath=glb)
mesh = next(o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("SK_GZPro"))
for m in list(mesh.modifiers):
    mesh.modifiers.remove(m)
for o in list(bpy.data.objects):
    if o not in (arm, mesh):
        bpy.data.objects.remove(o)
mw = mesh.matrix_world.copy()
mesh.parent = None
mesh.data.transform(Matrix.Scale(100, 4) @ mw)  # raw verts are /100; the root bone's x100 scale restores them
mesh.matrix_world = Matrix.Identity(4)

# Make sure the glb mesh sits on our joints (axis signs can differ between glTF and our UE->Blender flip).
def centroid(group):
    gi = mesh.vertex_groups[group].index
    pts = [v.co for v in mesh.data.vertices if any(g.group == gi and g.weight > 0.2 for g in v.groups)]
    return sum(pts, Vector()) / len(pts)

fix = Matrix.Identity(4)
for axis, bone in ((0, "Bip01_L_Forearm"), (1, "Bip01_Tail10")):
    joint = arm.data.bones[bone].head_local
    c = centroid(bone)
    if (c[axis] > 0) != (joint[axis] > 0):
        fix[axis][axis] = -1
if fix != Matrix.Identity(4):
    mesh.data.transform(fix)
    mesh.data.flip_normals()
print("[test] axis fix:", [fix[i][i] for i in range(3)])
mesh.parent = arm
mod = mesh.modifiers.new("Armature", "ARMATURE")
mod.object = arm

anim = json.load(open(anim_json))
parents = {n: gw[n][0] for n in order}
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
# figure out facing: put the camera on the side the head points to
head = arm.data.bones["Bip01_Head"].head_local
if head.y > 0:
    cam.location.y = -cam.location.y + 40
    cam.rotation_euler = (math.radians(90), 0, math.radians(180) - a)

for f in [int(x) for x in frames.split(",")]:
    f = min(f, len(anim["frames"]) - 1)
    apply_pose(arm, anim_frame_world(anim, f, parents, UNIT))
    bpy.context.view_layer.update()
    scn.render.filepath = f"{out_prefix}_{f:03d}.png"
    bpy.ops.render.render(write_still=True)
    print("[test] rendered", scn.render.filepath)

