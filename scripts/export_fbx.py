"""Export the fitted Final Wars Gigan as an FBX that matches the game's SK_GZPro_Gigan layout.

Game layout (UE component space): root bone GiganRoot = 180 deg about Z, scale 100; every other bone's local
translation is in "root units" (Bip01 at 47.64); mesh vertices ~11343 tall. Our working blend is that space / 100
with Y flipped, so:
  - the armature OBJECT becomes GiganRoot (rotation 180 Z, scale 100); UE turns a non-"Armature" armature node
    into the root bone,
  - bones and mesh live inside it in working units, rotated back by the root's 180 deg,
  - scene unit = 1 cm so FBX units come out as UE centimetres.

Usage: blender -b gigan_fw_fitted.blend --python export_fbx.py -- <out.fbx> [primary_axis] [secondary_axis]
"""
import sys, math
import bpy
from mathutils import Matrix

args = sys.argv[sys.argv.index("--") + 1:]
out_fbx = args[0]
primary = args[1] if len(args) > 1 else "X"
secondary = args[2] if len(args) > 2 else "-Y"

src_arm = bpy.data.objects["GZ1_Gigan"]
body = bpy.data.objects["SK_GZPro_Gigan_FW"]
R = Matrix.Rotation(math.radians(180), 4, "Z")
Rinv = R.inverted()

# New armature object named GiganRoot, bones = source bones minus the GiganRoot bone, rotated by R^-1.
data = bpy.data.armatures.new("GiganRoot")
root = bpy.data.objects.new("GiganRoot", data)
bpy.context.scene.collection.objects.link(root)
bpy.context.view_layer.objects.active = root
bpy.ops.object.mode_set(mode="EDIT")
for b in src_arm.data.bones:
    if b.name == "GiganRoot":
        continue
    eb = data.edit_bones.new(b.name)
    eb.head, eb.tail = (0, 0, 0), (0, b.length, 0)
    eb.matrix = Rinv @ b.matrix_local
for b in src_arm.data.bones:
    if b.name != "GiganRoot" and b.parent and b.parent.name != "GiganRoot":
        data.edit_bones[b.name].parent = data.edit_bones[b.parent.name]
bpy.ops.object.mode_set(mode="OBJECT")
root.matrix_world = R @ Matrix.Diagonal((100, 100, 100, 1))

# Mesh: bake R^-1 into the vertices and hang it under GiganRoot with no extra transform.
body.modifiers.clear()
body.parent = None
body.matrix_world = Matrix.Identity(4)
body.data.transform(Rinv)
# Faces built by from_pydata are flagged flat (sharp_face); Unreal then splits every corner into its own vertex.
# Shading comes from the custom normals anyway, so mark everything smooth.
body.data.shade_smooth()
body.name = "SK_GZPro_Gigan"
body.data.name = "SK_GZPro_Gigan"
body.parent = root
body.matrix_parent_inverse = Matrix.Identity(4)
body.matrix_basis = Matrix.Identity(4)
mod = body.modifiers.new("Armature", "ARMATURE")
mod.object = root
bpy.data.objects.remove(src_arm)

scn = bpy.context.scene
scn.unit_settings.system = "METRIC"
scn.unit_settings.scale_length = 0.01  # 1 Blender unit = 1 cm

bpy.ops.object.select_all(action="DESELECT")
root.select_set(True)
body.select_set(True)
bpy.ops.export_scene.fbx(
    filepath=out_fbx, use_selection=True, object_types={"ARMATURE", "MESH"},
    global_scale=1.0, apply_unit_scale=True, apply_scale_options="FBX_SCALE_NONE",
    axis_forward="-Z", axis_up="Y", use_space_transform=True,
    primary_bone_axis=primary, secondary_bone_axis=secondary,
    add_leaf_bones=False, use_armature_deform_only=False, armature_nodetype="NULL",
    mesh_smooth_type="OFF", use_tspace=False, use_mesh_modifiers=False,
    bake_anim=False, path_mode="COPY", embed_textures=False,
)
print(f"[fbx] wrote {out_fbx} (bone axes {primary}/{secondary}), {len(body.data.vertices)} verts, "
      f"{len(data.bones)} bones, mats={[m.name for m in body.data.materials]}")
