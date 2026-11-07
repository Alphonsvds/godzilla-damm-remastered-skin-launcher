import sys, math, bpy
from mathutils import Euler

out = sys.argv[sys.argv.index("--") + 1]
arm = bpy.data.objects["Gigan_FW_Armature"]
pb = arm.pose.bones
for side, sgn in (("L", 1), ("R", -1)):
    pb[f"Bip01_{side}_UpperArm"].rotation_mode = "XYZ"
    pb[f"Bip01_{side}_UpperArm"].rotation_euler = Euler((0, 0, math.radians(-55)), "XYZ")
    pb[f"Bip01_{side}_Forearm"].rotation_mode = "XYZ"
    pb[f"Bip01_{side}_Forearm"].rotation_euler = Euler((0, 0, math.radians(-50)), "XYZ")
for i in range(1, 8):
    b = pb[f"Bip01_Tail{i:02d}"]
    b.rotation_mode = "XYZ"
    b.rotation_euler = Euler((math.radians(10), 0, 0), "XYZ")
pb["Bip01_L_Thigh"].rotation_mode = "XYZ"
pb["Bip01_L_Thigh"].rotation_euler = Euler((0, 0, math.radians(35)), "XYZ")
pb["Bip01_Head"].rotation_mode = "XYZ"
pb["Bip01_Head"].rotation_euler = Euler((0, 0, math.radians(25)), "XYZ")
scn = bpy.context.scene
cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = 260
cam = bpy.data.objects.new("cam", cam_data)
scn.collection.objects.link(cam)
scn.camera = cam
a = math.radians(145)
cam.location = (math.sin(a) * 600, -60 - math.cos(a) * 600, 56)
cam.rotation_euler = (math.radians(90), 0, a)
scn.render.engine = "BLENDER_WORKBENCH"
scn.display.shading.color_type = "TEXTURE"
scn.render.resolution_x, scn.render.resolution_y = 1400, 900
scn.render.filepath = out
bpy.ops.render.render(write_still=True)
