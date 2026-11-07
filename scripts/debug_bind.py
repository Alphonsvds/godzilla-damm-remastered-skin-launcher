import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from mathutils import Vector, Matrix
from gzrig import game_world, build_armature
bones_json, glb = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
gw, order = game_world(bones_json)
arm = build_armature("GZ1_Gigan", gw, order, 0.01)
bpy.ops.import_scene.gltf(filepath=glb)
mesh = next(o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("SK_GZPro"))
print("[dbg] glb mesh world", [tuple(round(v,3) for v in r) for r in mesh.matrix_world])
print("[dbg] mesh modifiers", [(m.name, m.type, getattr(m,'object',None)) for m in mesh.modifiers])
print("[dbg] shape keys", mesh.data.shape_keys and [k.name for k in mesh.data.shape_keys.key_blocks])
def bb(o):
    dg = bpy.context.evaluated_depsgraph_get(); e = o.evaluated_get(dg); me = e.to_mesh()
    pts = [o.matrix_world @ v.co for v in me.vertices]; e.to_mesh_clear()
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return tuple(round(x,2) for x in lo), tuple(round(x,2) for x in hi)
print("[dbg] eval bounds as imported", bb(mesh))
for o in list(bpy.data.objects):
    if o not in (arm, mesh): bpy.data.objects.remove(o)
mw = mesh.matrix_world.copy(); mesh.parent = None; mesh.data.transform(mw); mesh.matrix_world = Matrix.Identity(4)
for m in list(mesh.modifiers): mesh.modifiers.remove(m)
print("[dbg] eval bounds no modifier", bb(mesh))
mesh.parent = arm; mod = mesh.modifiers.new("Armature", "ARMATURE"); mod.object = arm
print("[dbg] eval bounds with my armature", bb(mesh))
print("[dbg] groups not in armature", [g.name for g in mesh.vertex_groups if g.name not in arm.data.bones])
print("[dbg] root bone matrix_local", [tuple(round(v,3) for v in r) for r in arm.data.bones["GiganRoot"].matrix_local])
