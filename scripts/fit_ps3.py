"""Fit the PS3 (Godzilla 2014) Final Wars Gigan onto the Remastered game's SKEL_GZ1_Gigan_Skeleton.

The PS3 rig (joint1..joint43) is mapped onto game bones by role, aligned by a similarity transform, then each
mapped joint is moved onto its game joint: rotated so its segment points the same way as the game's (swing only,
the PS3 model keeps its own twist) and, for limbs, stretched to the game's segment length. The pose is baked with
plain linear blend skinning, so stretch is allowed. Output uses the same object names as the Wii fit so
export_fbx.py / ue_import.py work unchanged.

Usage: blender -b gigan_ps3.blend --python fit_ps3.py -- <bones.json> <out.blend>
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))
import bpy
import numpy as np
from mathutils import Matrix, Vector
from gzrig import game_world, build_armature, umeyama

bones_json, out_blend = sys.argv[sys.argv.index("--") + 1:]
gw, gorder = game_world(bones_json)
game = build_armature("GZ1_Gigan", gw, gorder, 0.01)
G = {b.name: b.head_local.copy() for b in game.data.bones}
ps3 = bpy.data.objects["Gigan_PS3_Armature"]
J = {b.name: b.head_local.copy() for b in ps3.data.bones}
JP = {b.name: (b.parent.name if b.parent else None) for b in ps3.data.bones}
meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.parent == ps3]

# joint -> game bone. Arms: the game's UpperArm runs shoulder->wrist, so the PS3 elbow (joint10/23) is folded in.
MAP = {
    "joint1": "Bip01_Pelvis", "joint2": "Bip01_Spine", "joint3": "Bip01_Spine1", "joint5": "Bip01_Neck",
    "joint13": "Bip01_Neck1", "joint14": "Bip01_Head",
    "joint7": "Bip01_L_Clavicle", "joint9": "Bip01_L_UpperArm", "joint11": "Bip01_L_Forearm",
    "joint20": "Bip01_R_Clavicle", "joint22": "Bip01_R_UpperArm", "joint24": "Bip01_R_Forearm",
    "joint27": "Bip01_L_Thigh", "joint28": "Bip01_L_Calf", "joint29": "Bip01_L_Foot", "joint30": "Bip01_L_Toe0",
    "joint31": "Bip01_R_Thigh", "joint32": "Bip01_R_Calf", "joint33": "Bip01_R_Foot", "joint34": "Bip01_R_Toe0",
}
# joint -> joint it moves with (and whose game bone it is weighted to); jaw is the exception, see JAW.
FOLLOW = {"joint4": "joint3", "joint6": "joint5", "joint12": "joint5", "joint25": "joint5", "joint26": "joint5",
          "joint8": "joint7", "joint10": "joint9", "joint21": "joint20", "joint23": "joint22",
          "joint15": "joint14", "joint16": "joint14", "joint17": "joint14", "joint18": "joint14", "joint19": "joint14"}
JAW = {"joint17": "Bip01_Ponytail1", "joint16": "Bip01_Ponytail1"}  # moves with the head at rest, animated as the jaw
# segment direction: joint -> (child joint, game child bone); limbs in STRETCH also match length
CHILD = {"joint1": ("joint2", "Bip01_Spine"), "joint2": ("joint3", "Bip01_Spine1"), "joint3": ("joint5", "Bip01_Neck"),
         "joint5": ("joint13", "Bip01_Neck1"), "joint13": ("joint14", "Bip01_Head"),
         "joint7": ("joint9", "Bip01_L_UpperArm"), "joint9": ("joint11", "Bip01_L_Forearm"),
         "joint20": ("joint22", "Bip01_R_UpperArm"), "joint22": ("joint24", "Bip01_R_Forearm"),
         "joint27": ("joint28", "Bip01_L_Calf"), "joint28": ("joint29", "Bip01_L_Foot"), "joint29": ("joint30", "Bip01_L_Toe0"),
         "joint31": ("joint32", "Bip01_R_Calf"), "joint32": ("joint33", "Bip01_R_Foot"), "joint33": ("joint34", "Bip01_R_Toe0")}
STRETCH = {"joint9", "joint22", "joint27", "joint28", "joint31", "joint32"}
PS3_TAIL = [f"joint{i}" for i in range(35, 44)]
GAME_TAIL = ["Bip01_Tail"] + [f"Bip01_Tail{i}" for i in range(1, 17)]

core = ["joint1", "joint2", "joint3", "joint5", "joint13", "joint14", "joint27", "joint31", "joint28", "joint32"]
Malign, s = umeyama([J[k] for k in core], [G[MAP[k]] for k in core])
A = {k: Malign @ v for k, v in J.items()}
print(f"[ps3] align scale {s:.3f}; left arm check: joint7 x={A['joint7'].x:+.1f} vs game L_Clavicle x={G['Bip01_L_Clavicle'].x:+.1f}")


def stretch(axis, k):
    a = axis.normalized()
    m = Matrix.Identity(3) + (k - 1) * Matrix([[a.x * a.x, a.x * a.y, a.x * a.z], [a.y * a.x, a.y * a.y, a.y * a.z], [a.z * a.x, a.z * a.y, a.z * a.z]])
    return m.to_4x4()


# per-joint world transform: v' = M @ v
Mj, Rj = {}, {}
order = [b.name for b in ps3.data.bones]  # parents before children
for j in order:
    if j in MAP:
        g = MAP[j]
        R = Rj.get(JP[j], Matrix.Identity(4)) if JP[j] else Matrix.Identity(4)
        S = Matrix.Identity(4)
        if j in CHILD:
            c, gc = CHILD[j]
            d0, d1 = A[c] - A[j], G[gc] - G[g]
            R = d0.normalized().rotation_difference(d1.normalized()).to_matrix().to_4x4()
            if j in STRETCH:
                S = stretch(d0, max(0.6, min(1.6, d1.length / d0.length)))
        Rj[j] = R
        Mj[j] = Matrix.Translation(G[g]) @ R @ S @ Matrix.Translation(-A[j]) @ Malign
    elif j in FOLLOW or j in JAW:
        t = FOLLOW.get(j, "joint14")
        Rj[j], Mj[j] = Rj[t], Mj[t]

# tail: spread the 9 PS3 tail joints along the 17-bone game tail by arc length
def arclen(pts):
    acc = [0.0]
    for a, b in zip(pts, pts[1:]):
        acc.append(acc[-1] + (b - a).length)
    return acc

def at(pts, acc, d):
    d = max(0.0, min(d, acc[-1]))
    for i in range(len(pts) - 1):
        if d <= acc[i + 1] or i == len(pts) - 2:
            seg = acc[i + 1] - acc[i]
            return pts[i].lerp(pts[i + 1], 0.0 if seg == 0 else (d - acc[i]) / seg)

p_pts = [A[j] for j in PS3_TAIL]
p_pts.append(p_pts[-1] + (p_pts[-1] - p_pts[-2]))
g_pts = [G[n] for n in GAME_TAIL]
g_pts.append(g_pts[-1] + (g_pts[-1] - g_pts[-2]))
p_acc, g_acc = arclen(p_pts), arclen(g_pts)
print(f"[ps3] tail length ps3={p_acc[-1]:.1f} game={g_acc[-1]:.1f}")
tail_seg = {}  # PS3 tail joint -> its segment on the game tail after the move (for re-weighting)
for i, j in enumerate(PS3_TAIL):
    q0 = at(g_pts, g_acc, p_acc[i] / p_acc[-1] * g_acc[-1])
    q1 = at(g_pts, g_acc, p_acc[i + 1] / p_acc[-1] * g_acc[-1])
    tail_seg[j] = (q0, q1, p_acc[i] / p_acc[-1], p_acc[i + 1] / p_acc[-1])
    d0 = p_pts[i + 1] - p_pts[i]
    R = d0.normalized().rotation_difference((q1 - q0).normalized()).to_matrix().to_4x4()
    S = stretch(d0, (q1 - q0).length / d0.length)
    Mj[j] = Matrix.Translation(q0) @ R @ S @ Matrix.Translation(-p_pts[i]) @ Malign

missing = [j for j in order if j not in Mj]
print(f"[ps3] joints without a transform: {missing}")

# Chainsaws ride the game's wrist bone (Forearm), not Hand: the game flicks Hand around for hook swipes, which threw
# the bulky saws across his face. In the film they are mounted along the forearm, so they stay an arm extension.
# CHAINSAW_TURN=True instead points them the way the game's hook hangs (tried: still blocked the face in idle).
CHAINSAW_SCALE = 0.85
CHAINSAW_TURN = False
GLB = os.path.join(os.path.dirname(bones_json), "export", "GZPro", "Content", "Characters", "GZPro_Monsters", "Gigan", "SK_GZPro_Gigan.glb")
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=GLB)
gmesh = next(o for o in bpy.data.objects if o not in before and o.type == "MESH" and o.name.startswith("SK_GZPro_Gigan"))
gm = Matrix.Scale(100, 4) @ gmesh.matrix_world  # raw glb verts are /100 (see game_anim_test.py)
gidx = {g.index: g.name for g in gmesh.vertex_groups}


def centroid(ob, mat, pick):
    idx = {g.index: g.name for g in ob.vertex_groups}
    pts = [mat @ v.co for v in ob.data.vertices if v.groups and pick(idx[max(v.groups, key=lambda g: g.weight).group])]
    return sum(pts, Vector()) / len(pts)


for side, saw in (("L", "joint11"), ("R", "joint24")):
    hand = G[f"Bip01_{side}_Hand"]
    hook = centroid(gmesh, gm, lambda n: n == f"Bip01_{side}_Hand")
    saw_c = sum((Mj[saw] @ v.co for ob in meshes for v in ob.data.vertices
                 if v.groups and ob.vertex_groups[max(v.groups, key=lambda g: g.weight).group].name == saw), Vector())
    n_saw = sum(1 for ob in meshes for v in ob.data.vertices
                if v.groups and ob.vertex_groups[max(v.groups, key=lambda g: g.weight).group].name == saw)
    saw_c /= n_saw
    R = (saw_c - hand).normalized().rotation_difference((hook - hand).normalized()).to_matrix().to_4x4() if CHAINSAW_TURN else Matrix.Identity(4)
    Mj[saw] = Matrix.Translation(hand) @ R @ Matrix.Scale(CHAINSAW_SCALE, 4) @ Matrix.Translation(-hand) @ Mj[saw]
    ang = (saw_c - hand).angle(hook - hand) * 57.2958
    print(f"[ps3] {side} chainsaw on the wrist bone, turned {ang if CHAINSAW_TURN else 0:.0f} deg, scaled {CHAINSAW_SCALE}")
for o in [o for o in bpy.data.objects if o not in before]:
    bpy.data.objects.remove(o)

# The PS3 foot has more geometry below its ankle than the game's, so after the move the soles end up under the
# ground. Lift the feet (and half that at the knees) so the lowest foot vertex sits at the game's floor.
FEET, KNEES = ("joint29", "joint30", "joint33", "joint34"), ("joint28", "joint32")
low = 1e9
for ob in meshes:
    idx = {g.index: g.name for g in ob.vertex_groups}
    for v in ob.data.vertices:
        if v.groups and idx[max(v.groups, key=lambda g: g.weight).group] in FEET:
            j = idx[max(v.groups, key=lambda g: g.weight).group]
            low = min(low, (Mj[j] @ v.co).z)
FLOOR = -0.6  # the game mesh's lowest point, in working units
lift = max(0.0, FLOOR - low)
for j in FEET:
    Mj[j] = Matrix.Translation((0, 0, lift)) @ Mj[j]
for j in KNEES:
    Mj[j] = Matrix.Translation((0, 0, lift / 2)) @ Mj[j]
print(f"[ps3] feet lifted by {lift:.1f} (lowest foot vertex was {low:.1f})")

# --- bake (linear blend skinning in numpy) ---
for ob in meshes:
    me = ob.data
    n = len(me.vertices)
    co = np.empty(n * 3, dtype=np.float64)
    me.vertices.foreach_get("co", co)
    co = np.c_[co.reshape(n, 3), np.ones(n)]
    names = {g.index: g.name for g in ob.vertex_groups}
    out = np.zeros((n, 4))
    lin = np.zeros((n, 3, 3))
    for v in me.vertices:
        tw = sum(g.weight for g in v.groups) or 1.0
        for g in v.groups:
            M = np.array(Mj[names[g.group]])
            out[v.index] += (g.weight / tw) * (M @ co[v.index])
            lin[v.index] += (g.weight / tw) * M[:3, :3]
    corner_n = [me.corner_normals[i].vector.copy() for i in range(len(me.loops))]
    me.vertices.foreach_set("co", out[:, :3].ravel())
    new_n = []
    for li, loop in enumerate(me.loops):
        L = lin[loop.vertex_index]
        nn = np.linalg.inv(L).T @ np.array(corner_n[li])
        new_n.append(Vector(nn).normalized())
    me.normals_split_custom_set(new_n)
    me.update()

# --- re-weight to game bones ---
def game_bone(j):
    if j in JAW:
        return JAW[j]
    while j not in MAP:
        j = FOLLOW[j]
    return MAP[j]

# Tail weights move bone by bone along the tail's length (never "closest game tail bone": the game tail curls,
# and a nearest-point search sends hip/belly vertices to the tail tip).
def tail_param(co, j):
    q0, q1, f0, f1 = tail_seg[j]
    ab = q1 - q0
    t = max(0.0, min(1.0, (co - q0).dot(ab) / max(ab.length_squared, 1e-9)))
    d = (f0 + t * (f1 - f0)) * g_acc[-1]
    for i in range(len(g_pts) - 1):
        if d <= g_acc[i + 1] or i == len(g_pts) - 2:
            seg = g_acc[i + 1] - g_acc[i]
            return i, (0.0 if seg == 0 else (d - g_acc[i]) / seg)

for ob in meshes:
    old = {g.index: g.name for g in ob.vertex_groups}
    per_vert = []
    for v in ob.data.vertices:
        acc = {}
        for g in v.groups:
            j = old[g.group]
            if j in PS3_TAIL:
                i, t = tail_param(v.co, j)
                k = min(i, len(GAME_TAIL) - 1)
                if t < 0.5 and k > 0:
                    pairs = [(k, 0.5 + t), (k - 1, 0.5 - t)]
                elif t >= 0.5 and k < len(GAME_TAIL) - 1:
                    pairs = [(k, 1.5 - t), (k + 1, t - 0.5)]
                else:
                    pairs = [(k, 1.0)]
                for kk, f in pairs:
                    acc[GAME_TAIL[kk]] = acc.get(GAME_TAIL[kk], 0) + g.weight * f
            else:
                gb = game_bone(j)
                acc[gb] = acc.get(gb, 0) + g.weight
        per_vert.append(acc)
    for g in list(ob.vertex_groups):
        ob.vertex_groups.remove(g)
    groups = {}
    for vi, acc in enumerate(per_vert):
        for name, w in acc.items():
            if name not in groups:
                groups[name] = ob.vertex_groups.new(name=name)
            groups[name].add([vi], w, "REPLACE")
    ob.modifiers.clear()

# --- one mesh on the game skeleton ---
bpy.ops.object.select_all(action="DESELECT")
for ob in meshes:
    ob.parent = None
    ob.select_set(True)
bpy.context.view_layer.objects.active = max(meshes, key=lambda o: len(o.data.vertices))
bpy.ops.object.join()
body = bpy.context.view_layer.objects.active
body.name = "SK_GZPro_Gigan_FW"
tex = bpy.data.materials.get("pl15_color") or next(m for m in bpy.data.materials)
base = bpy.data.materials.new("gigan_base")
saw = bpy.data.materials.new("gigan_buzzsaw_static")
for mat in (base, saw):
    mat.use_nodes = True
    src = tex.node_tree.nodes.get("Image Texture") if tex.node_tree else None
    if src:
        t = mat.node_tree.nodes.new("ShaderNodeTexImage")
        t.image = src.image
        mat.node_tree.links.new(t.outputs["Color"], mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
body.data.materials.clear()
body.data.materials.append(base)
body.data.materials.append(saw)
for poly in body.data.polygons:
    poly.material_index = 0
with bpy.context.temp_override(object=body, active_object=body, selected_objects=[body]):
    bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
unweighted = sum(1 for v in body.data.vertices if not v.groups)
body.parent = game
body.modifiers.new("Armature", "ARMATURE").object = game
bpy.data.objects.remove(ps3)
for o in list(bpy.data.objects):
    if o.type == "CAMERA":
        bpy.data.objects.remove(o)
lo = Vector([min(v.co[i] for v in body.data.vertices) for i in range(3)])
hi = Vector([max(v.co[i] for v in body.data.vertices) for i in range(3)])
print(f"[ps3] final mesh: {len(body.data.vertices)} verts, {len(body.data.polygons)} faces, "
      f"{len(body.vertex_groups)} bones, unweighted {unweighted}, height {hi.z - lo.z:.1f} (game ~113.4)")
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
print("[ps3] saved", out_blend)
