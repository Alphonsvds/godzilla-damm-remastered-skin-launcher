"""Import an MMD .pmx model (mesh, materials/textures, bones, skin weights) into Blender 5.x, which has no PMX importer.

MMD is Y-up, left-handed: (x, y, z)_mmd -> (x, -z... ) here mapped to Blender as (-x, z, y) so the model stands on Z and
faces -Y like Blender's front view. SDEF/QDEF weights are read as plain linear weights.

Usage: blender -b --factory-startup --python import_pmx.py -- <model.pmx> <out.blend> [armature_name]
"""
import sys, os, struct, math
import bpy
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index("--") + 1:]
pmx_path, out_blend = args[0], args[1]
ARM = args[2] if len(args) > 2 else "PMX_Armature"
tex_dir = os.path.dirname(pmx_path)
data = open(pmx_path, "rb").read()
pos = 0


def take(fmt):
    global pos
    vals = struct.unpack_from("<" + fmt, data, pos)
    pos += struct.calcsize("<" + fmt)
    return vals if len(vals) > 1 else vals[0]


assert data[:4] == b"PMX ", "not a PMX file"
pos = 4
version = take("f")
n_globals = take("B")
g = list(data[pos:pos + n_globals])
pos += n_globals
ENC, ADD_UV, VSZ, TSZ, MSZ, BSZ = g[0], g[1], g[2], g[3], g[4], g[5]


def text():
    n = take("i")
    global pos
    raw = data[pos:pos + n]
    pos += n
    return raw.decode("utf-16-le" if ENC == 0 else "utf-8", errors="replace")


def index(size, signed=True):
    fmt = {1: "b", 2: "h", 4: "i"}[size]
    return take(fmt if signed else fmt.upper() if size < 4 else "i")


def to_blender(x, y, z):
    return Vector((-x, z, y))


name_jp, name_en, _, _ = text(), text(), text(), text()
print(f"[pmx] {name_jp} / {name_en} (PMX {version})")

# vertices
nv = take("i")
co, nrm, uvs, weights = [], [], [], []
for _ in range(nv):
    px, py, pz = take("3f")
    nx, ny, nz = take("3f")
    u, v = take("2f")
    for _a in range(ADD_UV):
        take("4f")
    wt = take("B")
    if wt == 0:
        w = [(index(BSZ), 1.0)]
    elif wt == 1:
        b1, b2 = index(BSZ), index(BSZ)
        f = take("f")
        w = [(b1, f), (b2, 1 - f)]
    elif wt in (2, 4):
        bs = [index(BSZ) for _i in range(4)]
        fs = take("4f")
        w = list(zip(bs, fs))
    elif wt == 3:
        b1, b2 = index(BSZ), index(BSZ)
        f = take("f")
        take("9f")  # SDEF C, R0, R1
        w = [(b1, f), (b2, 1 - f)]
    take("f")  # edge scale
    co.append(to_blender(px, py, pz))
    nrm.append(to_blender(nx, ny, nz).normalized())
    uvs.append((u, 1 - v))
    weights.append([(b, f) for b, f in w if b >= 0 and f > 0])

# faces: kept in file order. MMD winds clockwise in its left-handed space, and to_blender is a proper rotation
# (no mirror), which turns that into Blender's counter-clockwise front faces. Reversing them made every face point
# inward (against the stored normals), which showed the inside of the model in Unreal (back faces culled).
nf = take("i")
idx = [index(VSZ, signed=False) for _ in range(nf)]
faces = [(idx[i], idx[i + 1], idx[i + 2]) for i in range(0, nf, 3)]

# textures
textures = [text() for _ in range(take("i"))]

# materials
mats = []
for _ in range(take("i")):
    mname, mname_en = text(), text()
    diffuse = take("4f")
    take("3f"); take("f"); take("3f")
    flag = take("B")
    take("4f"); take("f")
    tex = index(TSZ)
    index(TSZ)
    take("B")
    toon_shared = take("B")
    index(TSZ) if toon_shared == 0 else take("B")
    text()
    count = take("i")
    mats.append((mname_en or mname, diffuse, tex, count, bool(flag & 0x01)))

# bones
bones = []
for _ in range(take("i")):
    bname, bname_en = text(), text()
    p = to_blender(*take("3f"))
    parent = index(BSZ)
    take("i")
    flags = take("H")
    tail = index(BSZ) if flags & 0x0001 else to_blender(*take("3f"))
    if flags & (0x0100 | 0x0200):
        index(BSZ); take("f")
    if flags & 0x0400:
        take("3f")
    if flags & 0x0800:
        take("3f"); take("3f")
    if flags & 0x2000:
        take("i")
    if flags & 0x0020:
        index(BSZ); take("i"); take("f")
        for _l in range(take("i")):
            index(BSZ)
            if take("B"):
                take("3f"); take("3f")
    bones.append(dict(jp=bname, en=bname_en, pos=p, parent=parent, tail=tail, flags=flags))
print(f"[pmx] {nv} verts, {len(faces)} tris, {len(textures)} textures, {len(mats)} materials, {len(bones)} bones")

# --- build ----------------------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
arm_data = bpy.data.armatures.new(ARM)
arm = bpy.data.objects.new(ARM, arm_data)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
bnames = []
for i, b in enumerate(bones):
    nm = b["jp"] if b["jp"] not in bnames else f"{b['jp']}.{i}"
    bnames.append(nm)
    eb = arm_data.edit_bones.new(nm)
    eb.head = b["pos"]
    t = bones[b["tail"]]["pos"] if isinstance(b["tail"], int) and b["tail"] >= 0 else (
        b["pos"] + b["tail"] if isinstance(b["tail"], Vector) else None)
    if t is None or (t - b["pos"]).length < 1e-4:
        t = b["pos"] + Vector((0, 0, 0.3))
    eb.tail = t
for i, b in enumerate(bones):
    if b["parent"] >= 0:
        arm_data.edit_bones[bnames[i]].parent = arm_data.edit_bones[bnames[b["parent"]]]
bpy.ops.object.mode_set(mode="OBJECT")
for i, b in enumerate(bones):
    arm_data.bones[bnames[i]]["mmd_name_en"] = b["en"]

me = bpy.data.meshes.new("PMX_Mesh")
me.from_pydata([tuple(c) for c in co], [], faces)
uvl = me.uv_layers.new(name="UVMap")
for li, loop in enumerate(me.loops):
    uvl.data[li].uv = uvs[loop.vertex_index]
me.normals_split_custom_set_from_vertices([tuple(n) for n in nrm])
images = {}
start = 0
for mi, (mname, diffuse, tex, count, double) in enumerate(mats):
    mat = bpy.data.materials.new(mname)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = diffuse
    if 0 <= tex < len(textures):
        path = os.path.join(tex_dir, textures[tex].replace("\\", os.sep))
        if os.path.exists(path):
            node = mat.node_tree.nodes.new("ShaderNodeTexImage")
            node.image = images.get(path) or bpy.data.images.load(path)
            images[path] = node.image
            mat.node_tree.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])
            if node.image.depth == 32:
                mat.node_tree.links.new(node.outputs["Alpha"], bsdf.inputs["Alpha"])
    me.materials.append(mat)
    for f in range(start // 3, (start + count) // 3):
        me.polygons[f].material_index = mi
    start += count
    print(f"[pmx]   material {mi}: {mname!r} tris={count // 3} tex={textures[tex] if 0 <= tex < len(textures) else None}")
me.validate()
ob = bpy.data.objects.new("PMX_Mesh", me)
bpy.context.scene.collection.objects.link(ob)
ob.parent = arm
groups = [ob.vertex_groups.new(name=n) for n in bnames]
for vi, w in enumerate(weights):
    for b, f in w:
        groups[b].add([vi], f, "ADD")
ob.modifiers.new("Armature", "ARMATURE").object = arm

lo = Vector([min(c[i] for c in co) for i in range(3)])
hi = Vector([max(c[i] for c in co) for i in range(3)])
print(f"[pmx] bounds {tuple(round(x, 2) for x in lo)} .. {tuple(round(x, 2) for x in hi)}")
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
print("[pmx] saved", out_blend)
