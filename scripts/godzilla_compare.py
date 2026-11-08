import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from mathutils import Matrix, Vector
from gzrig import game_world, build_armature

game_dir, out_prefix = sys.argv[sys.argv.index("--") + 1:]
mmd_arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mmd_mesh = next(o for o in bpy.data.objects if o.type == "MESH")

MAP = {"lowerbody": "Bip01_Pelvis", "upperbody": "Bip01_Spine", "upperbody2": "Bip01_Spine1", "neck": "Bip01_Neck",
       "neck2": "Bip01_Neck1", "head": "Bip01_Head", "jaw": "Bip01_Jaw",
       "shoulder_L": "Bip01_L_Clavicle", "arm_L": "Bip01_L_UpperArm", "elbow_L": "Bip01_L_Forearm", "wrist_L": "Bip01_L_Hand",
       "leg_L": "Bip01_L_Thigh", "knee_L": "Bip01_L_Calf", "ankle_L": "Bip01_L_Foot", "toes_L": "Bip01_L_Toe0",
       "tail": "Bip01_Tail"}
mmd = {b.get("mmd_name_en", b.name): b.head_local.copy() for b in mmd_arm.data.bones}

def measures(J):
    h = J["head"].z
    return {
        "head height": 1.0,
        "hip height": J["hip"].z / h,
        "shoulder height": J["shoulder"].z / h,
        "neck length": (J["head"] - J["neck"]).length / h,
        "torso length": (J["neck"] - J["hip"]).length / h,
        "arm length": ((J["elbow"] - J["arm"]).length + (J["wrist"] - J["elbow"]).length) / h,
        "leg length": ((J["knee"] - J["leg"]).length + (J["ankle"] - J["knee"]).length) / h,
        "shoulder width": abs(J["arm"].x) * 2 / h,
        "head forward of hips": abs(J["head"].y - J["hip"].y) / h,
        "neck lean (deg from vertical)": math.degrees((J["head"] - J["neck"]).angle(Vector((0, 0, 1)))),
        "torso lean (deg from vertical)": math.degrees((J["neck"] - J["hip"]).angle(Vector((0, 0, 1)))),
    }

rows = {"2004 (MMD)": measures({"head": mmd["head"], "hip": mmd["lowerbody"], "shoulder": mmd["shoulder_L"],
                                 "neck": mmd["neck"], "arm": mmd["arm_L"], "elbow": mmd["elbow_L"], "wrist": mmd["wrist_L"],
                                 "leg": mmd["leg_L"], "knee": mmd["knee_L"], "ankle": mmd["ankle_L"]})}
models = [("2004", mmd_arm, mmd_mesh)]
for label, key in (("Godzilla 2000", "Godzilla2k"), ("Heisei", "HeiseiGodzilla")):
    gw, order = game_world(os.path.join(game_dir, f"bones_SK_GZPro_{key}.json"))
    arm = build_armature(f"Game_{key}", gw, order, 0.01)
    G = {b.name: b.head_local.copy() for b in arm.data.bones}
    rows[label] = measures({"head": G["Bip01_Head"], "hip": G["Bip01_Pelvis"], "shoulder": G["Bip01_L_Clavicle"],
                            "neck": G["Bip01_Neck"], "arm": G["Bip01_L_UpperArm"], "elbow": G["Bip01_L_Forearm"],
                            "wrist": G["Bip01_L_Hand"], "leg": G["Bip01_L_Thigh"], "knee": G["Bip01_L_Calf"],
                            "ankle": G["Bip01_L_Foot"]})
    before = set(bpy.data.objects)
    glb = os.path.join(game_dir, "export", "GZPro", "Content", "Characters", "GZPro_Monsters",
                       "Godzilla2k" if key == "Godzilla2k" else "HeiseiGodzilla", f"SK_GZPro_{key}.glb")
    bpy.ops.import_scene.gltf(filepath=glb)
    mesh = next(o for o in bpy.data.objects if o not in before and o.type == "MESH" and o.name.startswith("SK_"))
    mw = mesh.matrix_world.copy()
    mesh.parent = None
    for m in list(mesh.modifiers):
        mesh.modifiers.remove(m)
    mesh.data.transform(Matrix.Scale(100, 4) @ mw)
    mesh.matrix_world = Matrix.Identity(4)
    for o in [o for o in bpy.data.objects if o not in before and o not in (mesh, arm)]:
        bpy.data.objects.remove(o)
    models.append((label, arm, mesh))

names = list(rows)
print("[cmp] " + f"{'':32s}" + "".join(f"{n:>16s}" for n in names))
for k in rows[names[0]]:
    print("[cmp] " + f"{k:32s}" + "".join(f"{rows[n][k]:16.2f}" for n in names))

game_head = models[1][1].data.bones["Bip01_Head"].head_local.z
s = game_head / mmd["head"].z
mmd_arm.matrix_world = Matrix.Scale(s, 4)
tail_dir = {}
for label, arm, mesh in models:
    if label == "2004":
        tail_dir[label] = (mmd["tail"] - mmd["lowerbody"]).y
    else:
        b = arm.data.bones
        tail_dir[label] = (b["Bip01_Tail"].head_local - b["Bip01_Pelvis"].head_local).y
for i, (label, arm, mesh) in enumerate(models):
    root = arm if label == "2004" else mesh
    if label != "2004":
        arm.hide_render = True
    flip = Matrix.Rotation(math.pi, 4, "Z") if (tail_dir[label] > 0) != (tail_dir["Godzilla 2000"] > 0) else Matrix.Identity(4)
    root.matrix_world = Matrix.Translation((i * 130, 0, 0)) @ flip @ root.matrix_world

scn = bpy.context.scene
scn.render.engine = "BLENDER_WORKBENCH"
scn.display.shading.color_type = "TEXTURE"
scn.display.shading.light = "STUDIO"
scn.render.resolution_x, scn.render.resolution_y = 1500, 800
scn.world = bpy.data.worlds.new("w")
cd = bpy.data.cameras.new("cam")
cd.type = "ORTHO"
cd.ortho_scale = 420
cam = bpy.data.objects.new("cam", cd)
scn.collection.objects.link(cam)
scn.camera = cam
front = -1 if tail_dir["Godzilla 2000"] > 0 else 1
cam.location = (130, front * 900, 60)
cam.rotation_euler = (math.radians(90), 0, 0 if front < 0 else math.pi)
scn.render.filepath = f"{out_prefix}_front.png"
bpy.ops.render.render(write_still=True)
print("[cmp] rendered", scn.render.filepath)
scn.render.resolution_x, scn.render.resolution_y = 900, 700
cd.ortho_scale = 330
meshes = [(label, mmd_mesh if label == "2004" else mesh) for label, arm, mesh in models]
for i, (label, mesh) in enumerate(meshes):
    for _l, other in meshes:
        other.hide_render = other is not mesh
    cam.location = (i * 130 + 900, -60 * front, 70)
    cam.rotation_euler = (math.radians(90), 0, math.radians(90))
    scn.render.filepath = f"{out_prefix}_side_{i}.png"
    bpy.ops.render.render(write_still=True)
    print("[cmp] rendered", scn.render.filepath)
