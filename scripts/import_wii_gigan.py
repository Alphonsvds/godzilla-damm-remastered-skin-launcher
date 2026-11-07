"""Import the Wii Godzilla Unleashed Gigan COLLADA rip into Blender 5.x (which has no DAE importer).

Usage: blender -b --factory-startup --python import_wii_gigan.py -- <model.dae> <out.blend> [preview.png]
"""
import sys, os, math
import xml.etree.ElementTree as ET
import bpy
from mathutils import Matrix, Vector

NS = "{http://www.collada.org/2005/11/COLLADASchema}"
args = sys.argv[sys.argv.index("--") + 1:]
dae_path, out_blend = args[0], args[1]
preview = args[2] if len(args) > 2 else None
tex_dir = os.path.dirname(dae_path)
TEX = os.environ.get("GZ_TEX", "Gigan_FW_512_C.png")       # colour texture for every material
ARM = os.environ.get("GZ_ARM", "Gigan_FW_Armature")        # armature object name

root = ET.parse(dae_path).getroot()
up = root.find(f"{NS}asset/{NS}up_axis")
# Y-up files (e.g. the PS3 rip) get turned Z-up; the Wii rip has no up_axis and is already Z-up.
UP = Matrix.Rotation(math.radians(90), 4, "X") if up is not None and up.text.strip() == "Y_UP" else Matrix.Identity(4)


def floats(el):
    return [float(x) for x in el.text.split()]


def mat16(vals):
    return Matrix([vals[0:4], vals[4:8], vals[8:12], vals[12:16]])


def node_local(node):
    """Local transform from a <matrix> or a translate/rotate/scale stack, in document order."""
    m = Matrix.Identity(4)
    for el in node:
        tag = el.tag.replace(NS, "")
        if tag == "matrix":
            m = m @ mat16(floats(el))
        elif tag == "translate":
            m = m @ Matrix.Translation(Vector(floats(el)))
        elif tag == "rotate":
            x, y, z, deg = floats(el)
            m = m @ Matrix.Rotation(math.radians(deg), 4, Vector((x, y, z)))
        elif tag == "scale":
            m = m @ Matrix.Diagonal((*floats(el), 1))
    return m


# --- Joints (rest pose from scene nodes) ---
joints = {}  # name -> (parent, world matrix)
order = []


def walk(node, parent, parent_world):
    world = parent_world
    if node.get("type") == "JOINT":
        local = node_local(node)
        world = parent_world @ local
        name = node.get("sid") or node.get("name")
        joints[name] = (parent, world)
        order.append(name)
        parent = name
    for c in node.findall(NS + "node"):
        walk(c, parent, world)


for vs in root.iter(NS + "visual_scene"):
    for n in vs.findall(NS + "node"):
        walk(n, None, UP)

# --- Bind pose from inverse bind matrices (what the mesh was actually skinned against) ---
bind_world = {}
for skin in root.iter(NS + "skin"):
    srcs = {s.get("id"): s for s in skin.findall(NS + "source")}
    jsrc = jmat = None
    for inp in skin.find(NS + "joints").findall(NS + "input"):
        if inp.get("semantic") == "JOINT":
            jsrc = srcs[inp.get("source")[1:]]
        elif inp.get("semantic") == "INV_BIND_MATRIX":
            jmat = srcs[inp.get("source")[1:]]
    names = jsrc.find(NS + "Name_array").text.split()
    mats = floats(jmat.find(NS + "float_array"))
    for i, nm in enumerate(names):
        bind_world[nm] = UP @ mat16(mats[i * 16:(i + 1) * 16]).inverted()

max_diff = 0.0
for nm, bw in bind_world.items():
    rw = joints[nm][1]
    max_diff = max(max_diff, max(abs(bw[r][c] - rw[r][c]) for r in range(4) for c in range(4)))
print(f"[wii] {len(joints)} joints, {len(bind_world)} used for skinning; max rest-vs-bind diff = {max_diff:.5f}")

# --- Clean scene ---
bpy.ops.wm.read_factory_settings(use_empty=True)

# --- Armature ---
# Max/Biped joints point down local +X; Blender bones point down local +Y.
to_bone = Matrix.Rotation(math.radians(-90), 4, "Z")
arm_data = bpy.data.armatures.new(ARM)
arm = bpy.data.objects.new(ARM, arm_data)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
for nm in order:
    world = bind_world.get(nm, joints[nm][1])
    eb = arm_data.edit_bones.new(nm)
    eb.head = (0, 0, 0)
    eb.tail = (0, 2.0, 0)
    eb.matrix = world @ to_bone
for nm in order:
    parent = joints[nm][0]
    if parent:
        arm_data.edit_bones[nm].parent = arm_data.edit_bones[parent]
bpy.ops.object.mode_set(mode="OBJECT")
for nm in order:
    w = joints[nm][1]
    arm_data.bones[nm]["dae_rest_world"] = [v for row in w for v in row]

# --- Materials ---
mats = {}
for m in root.iter(NS + "material"):
    name = m.get("name")
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    img_path = os.path.join(tex_dir, TEX)
    if os.path.exists(img_path) and bsdf:
        tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(img_path, check_existing=True)
        mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if bsdf and "Metal" in name:
        bsdf.inputs["Metallic"].default_value = 0.6
    mats[name] = mat

# --- Meshes + skin weights ---
controllers = {}
for ctrl in root.iter(NS + "controller"):
    skin = ctrl.find(NS + "skin")
    controllers[skin.get("source")[1:]] = skin

for geo in root.iter(NS + "geometry"):
    gname = geo.get("name") or geo.get("id")
    mesh_el = geo.find(NS + "mesh")
    srcs = {s.get("id"): floats(s.find(NS + "float_array")) for s in mesh_el.findall(NS + "source")}
    pos_id = mesh_el.find(NS + "vertices").find(NS + "input").get("source")[1:]
    pos = srcs[pos_id]
    verts = [(UP @ Vector(pos[i:i + 3]).to_4d()).to_3d() for i in range(0, len(pos), 3)]

    faces, face_nrm, face_uv, face_mat = [], [], [], []
    mat_names = []
    for tri in mesh_el.findall(NS + "triangles"):
        mname = tri.get("material")
        if mname not in mat_names:
            mat_names.append(mname)
        inputs = {i.get("semantic"): (int(i.get("offset")), i.get("source")[1:]) for i in tri.findall(NS + "input")}
        stride = max(o for o, _ in inputs.values()) + 1
        p = [int(x) for x in tri.find(NS + "p").text.split()]
        nrm = srcs[inputs["NORMAL"][1]] if "NORMAL" in inputs else None
        uv = srcs[inputs["TEXCOORD"][1]] if "TEXCOORD" in inputs else None
        for t in range(0, len(p), stride * 3):
            corners = [p[t + k * stride:t + (k + 1) * stride] for k in range(3)]
            faces.append([c[inputs["VERTEX"][0]] for c in corners])
            if nrm:
                o = inputs["NORMAL"][0]
                face_nrm.append([UP.to_3x3() @ Vector(nrm[c[o] * 3:c[o] * 3 + 3]) for c in corners])
            if uv:
                o = inputs["TEXCOORD"][0]
                face_uv.append([(uv[c[o] * 2], uv[c[o] * 2 + 1]) for c in corners])
            face_mat.append(mat_names.index(mname))

    me = bpy.data.meshes.new(gname)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    for mn in mat_names:
        me.materials.append(mats.get(mn) or next(iter(mats.values())))  # PS3 triangles name a symbol, not the material
    for poly, mi in zip(me.polygons, face_mat):
        poly.material_index = mi
    if face_uv:
        uvl = me.uv_layers.new(name="UVMap")
        for poly, fuv in zip(me.polygons, face_uv):
            for li, uvc in zip(poly.loop_indices, fuv):
                uvl.data[li].uv = uvc
    if face_nrm:
        me.normals_split_custom_set([n for fn in face_nrm for n in fn])
    me.validate()

    ob = bpy.data.objects.new(gname.split("|")[-1], me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = arm
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = arm

    skin = controllers[geo.get("id")]
    ssrc = {s.get("id"): s for s in skin.findall(NS + "source")}
    vw = skin.find(NS + "vertex_weights")
    vin = {i.get("semantic"): (int(i.get("offset")), i.get("source")[1:]) for i in vw.findall(NS + "input")}
    jnames = ssrc[vin["JOINT"][1]].find(NS + "Name_array").text.split()
    wvals = floats(ssrc[vin["WEIGHT"][1]].find(NS + "float_array"))
    groups = [ob.vertex_groups.get(j) or ob.vertex_groups.new(name=j) for j in jnames]
    vcount = [int(x) for x in vw.find(NS + "vcount").text.split()]
    v = [int(x) for x in vw.find(NS + "v").text.split()]
    vstride = max(o for o, _ in vin.values()) + 1
    k = 0
    for vi, cnt in enumerate(vcount):
        for _ in range(cnt):
            ji = v[k + vin["JOINT"][0]]
            wi = v[k + vin["WEIGHT"][0]]
            groups[ji].add([vi], wvals[wi], "REPLACE")
            k += vstride
    print(f"[wii] mesh {ob.name}: {len(me.vertices)} verts, {len(me.polygons)} tris, {len(groups)} bones")

bpy.ops.wm.save_as_mainfile(filepath=out_blend)
print("[wii] saved", out_blend)

if preview:
    # Quick turnaround render with the workbench engine.
    scn = bpy.context.scene
    objs = [o for o in scn.objects if o.type == "MESH"]
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    ctr, size = (lo + hi) / 2, (hi - lo)
    print(f"[wii] bounds min={tuple(round(x, 2) for x in lo)} max={tuple(round(x, 2) for x in hi)}")
    scn.render.engine = "BLENDER_WORKBENCH"
    scn.display.shading.color_type = "TEXTURE"
    scn.display.shading.light = "STUDIO"
    scn.render.resolution_x, scn.render.resolution_y = 1400, 900
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = max(size) * 1.15
    cam = bpy.data.objects.new("cam", cam_data)
    scn.collection.objects.link(cam)
    scn.camera = cam
    dist = max(size) * 3
    for label, ang in (("front", 180), ("side", 90), ("threequarter", 145)):
        a = math.radians(ang)
        cam.location = ctr + Vector((math.sin(a) * dist, -math.cos(a) * dist, 0))
        cam.rotation_euler = (math.radians(90), 0, a)
        scn.render.filepath = preview.replace(".png", f"_{label}.png")
        bpy.ops.render.render(write_still=True)
        print("[wii] rendered", scn.render.filepath)
