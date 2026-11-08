import sys, math
import bpy
from mathutils import Matrix

args = sys.argv[sys.argv.index("--") + 1:]
out_fbx = args[0]
primary = args[1] if len(args) > 1 else "X"
secondary = args[2] if len(args) > 2 else "-Y"
mesh_name = args[3] if len(args) > 3 else "SK_GZPro_Gigan"

src_arm = bpy.data.objects["GZ1_Gigan"]
body = bpy.data.objects["SK_GZPro_Gigan_FW"]
ROOT = next(b.name for b in src_arm.data.bones if b.parent is None)
R = Matrix.Rotation(math.radians(180), 4, "Z")
Rinv = R.inverted()

data = bpy.data.armatures.new(ROOT)
root = bpy.data.objects.new(ROOT, data)
bpy.context.scene.collection.objects.link(root)
bpy.context.view_layer.objects.active = root
bpy.ops.object.mode_set(mode="EDIT")
for b in src_arm.data.bones:
    if b.name == ROOT:
        continue
    eb = data.edit_bones.new(b.name)
    eb.head, eb.tail = (0, 0, 0), (0, b.length, 0)
    eb.matrix = Rinv @ b.matrix_local
for b in src_arm.data.bones:
    if b.name != ROOT and b.parent and b.parent.name != ROOT:
        data.edit_bones[b.name].parent = data.edit_bones[b.parent.name]
bpy.ops.object.mode_set(mode="OBJECT")
root.matrix_world = R @ Matrix.Diagonal((100, 100, 100, 1))

body.modifiers.clear()
body.parent = None
body.matrix_world = Matrix.Identity(4)
body.data.transform(Rinv)
body.data.shade_smooth()
body.name = mesh_name
body.data.name = mesh_name
body.parent = root
body.matrix_parent_inverse = Matrix.Identity(4)
body.matrix_basis = Matrix.Identity(4)
mod = body.modifiers.new("Armature", "ARMATURE")
mod.object = root
bpy.data.objects.remove(src_arm)

scn = bpy.context.scene
scn.unit_settings.system = "METRIC"
scn.unit_settings.scale_length = 0.01

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
