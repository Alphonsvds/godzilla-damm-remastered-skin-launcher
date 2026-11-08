import sys, os
import bpy
from mathutils import Matrix

args = sys.argv[sys.argv.index("--") + 1:]
glb, out_blend = args[0], args[1]
TORSO = (args[2].split(",") if len(args) > 2 else
         ["Bip01", "Bip01_Pelvis", "Bip01_Spine", "Bip01_Spine1", "Bip01_Neck", "Bip01_Neck1"])

body = bpy.data.objects["SK_GZPro_Gigan_FW"]
NO_NEW_TAIL = len(args) > 3 and args[3] == "no-new-tail"
had_tail = {v.index for v in body.data.vertices
            if any(body.vertex_groups[g.group].name.startswith("Bip01_Tail") and g.weight > 0 for g in v.groups)}
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=glb)
src = next(o for o in bpy.data.objects if o not in before and o.type == "MESH" and o.name.startswith("SK_GZPro"))
mw = src.matrix_world.copy()
src.parent = None
for m in list(src.modifiers):
    src.modifiers.remove(m)
src.data.transform(Matrix.Scale(100, 4) @ mw)
src.matrix_world = Matrix.Identity(4)
for o in [o for o in bpy.data.objects if o not in before and o != src]:
    bpy.data.objects.remove(o)

mask = body.vertex_groups.new(name="TorsoMask")
idx = {g.index: g.name for g in body.vertex_groups}
n_masked = 0
for v in body.data.vertices:
    w = sum(g.weight for g in v.groups if idx[g.group] in TORSO)
    if w > 0:
        mask.add([v.index], min(1.0, w * 1.5), "REPLACE")
        n_masked += 1
print(f"[xfer] torso-driven vertices: {n_masked} / {len(body.data.vertices)}")

for g in src.vertex_groups:
    if g.name not in body.vertex_groups:
        body.vertex_groups.new(name=g.name)

mod = body.modifiers.new("TorsoWeights", "DATA_TRANSFER")
mod.object = src
mod.use_vert_data = True
mod.data_types_verts = {"VGROUP_WEIGHTS"}
mod.vert_mapping = "POLYINTERP_NEAREST"
mod.layers_vgroup_select_src = "ALL"
mod.layers_vgroup_select_dst = "NAME"
mod.mix_mode = "REPLACE"
mod.mix_factor = 1.0
mod.vertex_group = "TorsoMask"
bpy.context.view_layer.objects.active = body
while body.modifiers[0].name != "TorsoWeights":
    bpy.ops.object.modifier_move_up(modifier="TorsoWeights")
with bpy.context.temp_override(object=body, active_object=body, selected_objects=[body]):
    bpy.ops.object.modifier_apply(modifier="TorsoWeights")
    body.vertex_groups.remove(body.vertex_groups["TorsoMask"])
    if NO_NEW_TAIL:
        tails = [g for g in body.vertex_groups if g.name.startswith("Bip01_Tail")]
        drop = [v.index for v in body.data.vertices if v.index not in had_tail]
        for g in tails:
            g.remove(drop)
        print(f"[xfer] kept tail weights only on the {len(had_tail)} vertices that had them")
    bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
    bpy.ops.object.vertex_group_clean(group_select_mode="ALL", limit=0.001)

empty = [g.name for g in body.vertex_groups if not any(ge.group == g.index for v in body.data.vertices for ge in v.groups)]
for n in empty:
    body.vertex_groups.remove(body.vertex_groups[n])
unweighted = sum(1 for v in body.data.vertices if not v.groups)
print(f"[xfer] groups now: {len(body.vertex_groups)}, unweighted vertices: {unweighted}")
bpy.data.objects.remove(src)
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
print("[xfer] saved", out_blend)
