import sys, math
import bpy
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index("--") + 1:]
out_png = args[0]
if len(args) > 1:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=args[1])
    for o in list(bpy.data.objects):
        if o.type == "MESH" and o.name.startswith("SK_"):
            mw = o.matrix_world.copy()
            o.parent = None
            for m in list(o.modifiers):
                o.modifiers.remove(m)
            o.data.transform(Matrix.Scale(100, 4) @ mw)
            o.matrix_world = Matrix.Identity(4)
        elif o.type != "MESH" or o.name.startswith("Icosphere"):
            bpy.data.objects.remove(o)
for o in list(bpy.data.objects):
    if o.type in ("CAMERA", "LIGHT"):
        bpy.data.objects.remove(o)
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
for ob in meshes:
    for mat in ob.data.materials:
        if mat and mat.node_tree and (b := mat.node_tree.nodes.get("Principled BSDF")):
            b.inputs["Roughness"].default_value = 0.5

deps = bpy.context.evaluated_depsgraph_get()
pts = []
for ob in meshes:
    ev = ob.evaluated_get(deps).to_mesh()
    pts += [ob.matrix_world @ v.co for v in ev.vertices]
    ob.evaluated_get(deps).to_mesh_clear()
lo = Vector([min(p[i] for p in pts) for i in range(3)])
hi = Vector([max(p[i] for p in pts) for i in range(3)])
ctr, height = (lo + hi) / 2, hi.z - lo.z
ys = sorted(p.y for p in pts)
front = Vector((0, -1 if abs(ys[len(ys) // 2] - lo.y) > abs(hi.y - ys[len(ys) // 2]) else 1, 0))
front = Vector((0, 1 if (ys[len(ys) // 2] - ctr.y) < 0 else -1, 0)) * -1
side = Vector((-front.y, front.x, 0))

scn = bpy.context.scene
scn.render.engine = "BLENDER_EEVEE"
scn.render.resolution_x, scn.render.resolution_y = 720, 1080
scn.view_settings.view_transform = "AgX"
scn.view_settings.look = "AgX - Punchy"
world = bpy.data.worlds.new("card")
scn.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.05, 0.008, 0.008, 1)
bpy.ops.mesh.primitive_plane_add(size=5000, location=(0, 0, lo.z))
gm = bpy.data.materials.new("ground")
gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.006, 0.006, 0.007, 1)
bpy.context.active_object.data.materials.append(gm)

def light(name, loc, energy, color, size):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy, ld.color, ld.size = energy, color, size
    ob = bpy.data.objects.new(name, ld)
    scn.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (ctr - Vector(loc)).to_track_quat("-Z", "Y").to_euler()

k = height / 113
light("Key", ctr + (front * 260 + side * 180 + Vector((0, 0, 160))) * k, 2.2e6 * k * k, (1.0, 0.86, 0.72), 120 * k)
light("Rim", ctr + (-front * 220 - side * 120 + Vector((0, 0, 220))) * k, 3.0e6 * k * k, (1.0, 0.18, 0.12), 60 * k)
light("Fill", ctr + (front * 200 - side * 220 + Vector((0, 0, 40))) * k, 4.0e5 * k * k, (0.45, 0.6, 1.0), 160 * k)
cd = bpy.data.cameras.new("cam")
cd.lens = 50
cd.clip_end = 100000
cam = bpy.data.objects.new("cam", cd)
scn.collection.objects.link(cam)
scn.camera = cam
look = Vector((ctr.x, ctr.y, lo.z + height * 0.55))
look += front * (hi.y - lo.y) * 0.15
cam.location = look + front * height * 2.0 + side * height * 0.9 + Vector((0, 0, -height * 0.3))
cam.rotation_euler = (look - cam.location).to_track_quat("-Z", "Y").to_euler()
scn.render.filepath = out_png
bpy.ops.render.render(write_still=True)
print("[card] rendered", out_png)
