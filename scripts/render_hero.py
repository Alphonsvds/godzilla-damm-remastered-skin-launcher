import sys, os, json, math
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from mathutils import Matrix, Vector
from gzrig import game_world, build_armature, anim_frame_world, apply_pose

args = sys.argv[sys.argv.index("--") + 1:]
bones_json, anim_json, frame, out_png = args[0], args[1], int(args[2]), args[3]
extra = args[4:]
gw, order = game_world(bones_json)
parents = {n: gw[n][0] for n in order}

if extra and extra[0] == "--glb":
    bpy.ops.wm.read_factory_settings(use_empty=True)
    arm = build_armature("GZ1_Gigan", gw, order, 0.01)
    bpy.ops.import_scene.gltf(filepath=extra[1])
    body = next(o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("SK_GZPro_Gigan"))
    for m in list(body.modifiers):
        body.modifiers.remove(m)
    mw = body.matrix_world.copy()
    body.parent = None
    body.data.transform(Matrix.Scale(100, 4) @ mw)
    body.matrix_world = Matrix.Identity(4)
    for o in list(bpy.data.objects):
        if o not in (arm, body):
            bpy.data.objects.remove(o)
    body.parent = arm
    body.modifiers.new("Armature", "ARMATURE").object = arm
else:
    arm = bpy.data.objects["GZ1_Gigan"]
    body = bpy.data.objects["SK_GZPro_Gigan_FW"]
    for o in list(bpy.data.objects):
        if o.type in ("CAMERA", "LIGHT"):
            bpy.data.objects.remove(o)
    if extra:
        for im in bpy.data.images:
            if im.source == "FILE" or im.packed_file:
                im.unpack(method="REMOVE") if im.packed_file else None
                im.filepath = extra[0]
                im.reload()

anim = json.load(open(anim_json, encoding="utf-8-sig"))
pose = anim_frame_world(anim, frame, parents, 0.01)
root = pose["GiganRoot"].translation.copy()
for k in pose:
    pose[k] = Matrix.Translation(-Vector((root.x, root.y, 0))) @ pose[k]
apply_pose(arm, pose)
bpy.context.view_layer.update()

for mat in body.data.materials:
    if mat and mat.node_tree:
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Roughness"].default_value = 0.45
            bsdf.inputs["Metallic"].default_value = 0.35

scn = bpy.context.scene
scn.render.engine = "BLENDER_EEVEE"
scn.render.resolution_x, scn.render.resolution_y = 720, 1080
scn.render.film_transparent = False
scn.view_settings.view_transform = "AgX"
scn.view_settings.look = "AgX - Punchy"

world = bpy.data.worlds.new("hero")
scn.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
grad = world.node_tree.nodes.new("ShaderNodeTexGradient")
coord = world.node_tree.nodes.new("ShaderNodeTexCoord")
mapn = world.node_tree.nodes.new("ShaderNodeMapping")
mapn.inputs["Rotation"].default_value = (0, math.radians(-90), 0)
ramp = world.node_tree.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].color = (0.10, 0.012, 0.01, 1)
ramp.color_ramp.elements[1].position = 0.62
ramp.color_ramp.elements[1].color = (0.006, 0.006, 0.009, 1)
links = world.node_tree.links
links.new(coord.outputs["Generated"], mapn.inputs["Vector"])
links.new(mapn.outputs["Vector"], grad.inputs["Vector"])
links.new(grad.outputs["Fac"], ramp.inputs["Fac"])
links.new(ramp.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 1.0

bpy.ops.mesh.primitive_plane_add(size=900, location=(0, 0, -0.6))
ground = bpy.context.active_object
gmat = bpy.data.materials.new("ground")
gmat.use_nodes = True
gb = gmat.node_tree.nodes["Principled BSDF"]
gb.inputs["Base Color"].default_value = (0.006, 0.006, 0.007, 1)
gb.inputs["Roughness"].default_value = 0.85
ground.data.materials.append(gmat)

deps = bpy.context.evaluated_depsgraph_get()
ev = body.evaluated_get(deps).to_mesh()
pts = [body.matrix_world @ v.co for v in ev.vertices]
lo = Vector([min(p[i] for p in pts) for i in range(3)])
hi = Vector([max(p[i] for p in pts) for i in range(3)])
body.evaluated_get(deps).to_mesh_clear()
ctr = (lo + hi) / 2
tail = arm.pose.bones["Bip01_Tail16"].matrix.translation
front = Vector((ctr.x - tail.x, ctr.y - tail.y, 0)).normalized()
side = Vector((-front.y, front.x, 0))
height = hi.z - lo.z

def light(name, kind, loc, energy, color, size=None):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    if size is not None:
        ld.size = size
    ob = bpy.data.objects.new(name, ld)
    scn.collection.objects.link(ob)
    ob.location = loc
    d = (ctr + Vector((0, 0, height * 0.1))) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob

light("Key", "AREA", ctr + front * 260 + side * 180 + Vector((0, 0, 160)), 2.2e6, (1.0, 0.86, 0.72), 120)
light("Rim", "AREA", ctr - front * 220 - side * 120 + Vector((0, 0, 220)), 3.0e6, (1.0, 0.18, 0.12), 60)
light("Fill", "AREA", ctr + front * 200 - side * 220 + Vector((0, 0, 40)), 4.0e5, (0.45, 0.6, 1.0), 160)

cd = bpy.data.cameras.new("cam")
cd.lens = 50
cd.clip_end = 5000
cam = bpy.data.objects.new("cam", cd)
scn.collection.objects.link(cam)
scn.camera = cam
look = Vector((ctr.x, ctr.y, lo.z + height * 0.5))
cam.location = look + front * height * 1.85 + side * height * 0.85 + Vector((0, 0, -height * 0.38))
cam.rotation_euler = (look - cam.location).to_track_quat("-Z", "Y").to_euler()

scn.render.filepath = out_png
bpy.ops.render.render(write_still=True)
print("[hero] rendered", out_png)
