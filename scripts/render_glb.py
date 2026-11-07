import sys, math, bpy
from mathutils import Vector

glb, out = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
for o in list(bpy.data.objects):
    if o.name.startswith("Icosphere"):
        bpy.data.objects.remove(o)
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
lo = Vector([min(p[i] for p in pts) for i in range(3)])
hi = Vector([max(p[i] for p in pts) for i in range(3)])
ctr, size = (lo + hi) / 2, hi - lo
scn = bpy.context.scene
scn.render.engine = "BLENDER_WORKBENCH"
scn.display.shading.color_type = "TEXTURE"
scn.display.shading.light = "STUDIO"
scn.render.resolution_x, scn.render.resolution_y = 1000, 900
world = bpy.data.worlds.new("w")
scn.world = world
cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = max(size) * 1.15
cam = bpy.data.objects.new("cam", cam_data)
scn.collection.objects.link(cam)
scn.camera = cam
d = max(size) * 4
for label, ang in (("front", 0), ("side", 90), ("threequarter", 35)):
    a = math.radians(ang)
    cam.location = ctr + Vector((math.sin(a) * d, -math.cos(a) * d, 0))
    cam.rotation_euler = (math.radians(90), 0, a)
    scn.render.filepath = out.replace(".png", f"_{label}.png")
    bpy.ops.render.render(write_still=True)
    print("[glb] rendered", scn.render.filepath)
