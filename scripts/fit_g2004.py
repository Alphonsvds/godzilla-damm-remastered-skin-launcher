"""Fit the MMD Godzilla 2004 (Final Wars) model onto a Remastered Godzilla skeleton: Godzilla 2000 or
the regular (Heisei) Godzilla, which share the Bip01 rig (Heisei has no Bip_Belly / Bip_Face, which this doesn't use).

Same approach as fit_ps3.py: map MMD bones (by their English names) to game bones, align with a similarity transform,
move each mapped joint onto its game joint (swing only; limbs also stretched to the game's lengths), bake with linear
blend skinning, then re-weight onto the game bones. Unmapped MMD bones (spines, eyes, fingers...) move with their nearest
mapped parent and are weighted to that parent's game bone, unless WEIGHT_TO names a game bone for them.

Materials go to the game's two slots: body + eyes -> slot 0 (eyes packed into the right half of a 2:1 body sheet),
claws/teeth/tongue/spines -> slot 1. The see-through eye overlays (eyes2, eyefire) are removed.
Also writes the spine-plate UV mask used for the attack glow textures.

Output object names match the Gigan fits (GZ1_Gigan / SK_GZPro_Gigan_FW) so export_fbx.py works unchanged.
Usage: blender -b g2004.blend --python fit_g2004.py -- <bones.json> <out.blend> <plates_mask.png> [body_slot spines_slot [own-upper]]
  slot names default to Godzilla 2000's; the regular (Heisei) Godzilla uses body_mat spines_mat.
  own-upper: move the upper-body bones onto the model's joints instead (needs the shipped skeleton, see ue_import.py).
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import bpy, bmesh
import numpy as np
from mathutils import Matrix, Vector
from gzrig import game_world, build_armature, umeyama

ARGS = sys.argv[sys.argv.index("--") + 1:]
bones_json, out_blend, mask_png = ARGS[:3]
BODY_SLOT, SPINES_SLOT = ARGS[3:5] if len(ARGS) >= 5 else ("Godzilla2k_Mesh_body_mtl", "Godzilla2k_Mesh_spines_mtl")
OWN_UPPER = "own-upper" in ARGS[5:]
gw, gorder = game_world(bones_json)
game = build_armature("GZ1_Gigan", gw, gorder, 0.01)
G = {b.name: b.head_local.copy() for b in game.data.bones}
mmd = next(o for o in bpy.data.objects if o.type == "ARMATURE")
body = next(o for o in bpy.data.objects if o.type == "MESH")
EN = {b.name: (b.get("mmd_name_en") or b.name) for b in mmd.data.bones}  # bone name -> English name
BY_EN = {v: k for k, v in EN.items()}
J = {EN[b.name]: b.head_local.copy() for b in mmd.data.bones}
PARENT = {EN[b.name]: (EN[b.parent.name] if b.parent else None) for b in mmd.data.bones}


def side_map(flip):
    """MMD side suffix -> game side; flip swaps L/R (MMD 'left' is the model's left)."""
    a, b = ("L", "R") if not flip else ("R", "L")
    m = {"lowerbody": "Bip01_Pelvis", "upperbody": "Bip01_Spine", "upperbody2": "Bip01_Spine1",
         "neck": "Bip01_Neck1", "head": "Bip01_Head"}
    for s, g in (("L", a), ("R", b)):
        m.update({f"shoulder_{s}": f"Bip01_{g}_Clavicle", f"arm_{s}": f"Bip01_{g}_UpperArm",
                  f"elbow_{s}": f"Bip01_{g}_Forearm", f"wrist_{s}": f"Bip01_{g}_Hand",
                  f"leg_{s}": f"Bip01_{g}_Thigh", f"knee_{s}": f"Bip01_{g}_Calf", f"ankle_{s}": f"Bip01_{g}_Foot"})
    return m


core = ["lowerbody", "upperbody", "upperbody2", "neck", "head", "leg_L", "leg_R", "knee_L", "knee_R", "ankle_L", "ankle_R",
        "shoulder_L", "shoulder_R"]
best = None
for flip in (False, True):
    m = side_map(flip)
    M, s = umeyama([J[k] for k in core], [G[m[k]] for k in core])
    err = sum((M @ J[k] - G[m[k]]).length for k in core)
    if best is None or err < best[0]:
        best = (err, flip, M, s, m)
err, flip, Malign, scale, MAP = best
A = {k: Malign @ v for k, v in J.items()}
print(f"[g04] align scale {scale:.3f}, L/R {'swapped' if flip else 'kept'}, mean core error {err / len(core):.2f}")
for k in ("lowerbody", "upperbody", "upperbody2", "neck", "head", "shoulder_L", "arm_L", "elbow_L", "wrist_L", "leg_L",
          "knee_L", "ankle_L"):
    d = G[MAP[k]] - A[k]
    print(f"[g04]   {k:<11} -> {MAP[k]:<18} game minus 2004: x {d.x:6.1f}  fwd(-y) {-d.y:6.1f}  up {d.z:6.1f}")

# weights-only targets: these move with their parent but are animated by their own game bone
gs = "R" if flip else "L"
go = "L" if flip else "R"
WEIGHT_TO = {"jaw": "Bip01_Jaw", "lips2": "Bip01_Jaw", "tongue": "Bip01_Jaw", "tongue2": "Bip01_Jaw", "tongue3": "Bip01_Jaw",
             "tongue4": "Bip01_Jaw", "tongue5": "Bip01_Jaw", "neck2": "Bip01_Neck1"}
for s, g in (("L", gs), ("R", go)):
    WEIGHT_TO.update({f"thumb_{s}1": f"Bip01_{g}_Finger0", f"thumb_{s}2": f"Bip01_{g}_Finger01",
                      f"fore_{s}1": f"Bip01_{g}_Finger1", f"fore_{s}2": f"Bip01_{g}_Finger11",
                      f"middle_{s}1": f"Bip01_{g}_Finger1", f"middle_{s}2": f"Bip01_{g}_Finger11",
                      f"third_{s}1": f"Bip01_{g}_Finger1", f"third_{s}2": f"Bip01_{g}_Finger11",
                      f"toes_{s}": f"Bip01_{g}_Toe0", f"toe_{s}": f"Bip01_{g}_Toe01", f"toe_{s}2": f"Bip01_{g}_Toe01",
                      f"toe_{s}3": f"Bip01_{g}_Toe01"})

# own-upper: game bones move onto the 2004 model's own joints instead of the model being bent onto the game's
# (rotations stay the game's, so animation rotations mean the same thing). The shipped skeleton takes these bones'
# positions from the mesh (Skeleton translation retargeting, set in ue_import.py), so the game's longer neck, lower
# shoulders, higher hips and longer arms no longer stretch the model. Pelvis, feet and tail stay on the game's joints.
NO_MOVE = set()  # MMD joints whose mesh stays where it is (its game bone is only a pivot for the weights)
if OWN_UPPER:
    d1 = (G["Bip01_Neck"] - G["Bip01_Spine1"]).length
    d2 = (G["Bip01_Neck1"] - G["Bip01_Neck"]).length
    f = d1 / (d1 + d2)  # the game's Neck bone (where the clavicles hang) has no MMD joint: same fraction of the way
    nk = A["upperbody2"].lerp(A["neck"], f)
    # spine, neck, head, shoulders and hips: exactly at the model's joints, so the torso keeps its own posture
    exact = {"Bip01_Spine": A["upperbody"], "Bip01_Spine1": A["upperbody2"], "Bip01_Neck": nk,
             "Bip01_Neck1": A["neck"], "Bip01_Head": A["head"], "Bip01_Jaw": A["jaw"]}
    # arms below the shoulder: the game's direction from the parent with the model's length. The MMD rest pose holds
    # its arms raised; at its own elbow/wrist positions every animation would lift the arms by that much.
    seg = {}
    for s, g in (("L", gs), ("R", go)):
        exact.update({f"Bip01_{g}_Clavicle": A[f"shoulder_{s}"], f"Bip01_{g}_UpperArm": A[f"arm_{s}"],
                      f"Bip01_{g}_Thigh": A[f"leg_{s}"]})
        seg.update({f"Bip01_{g}_Forearm": (A[f"arm_{s}"], A[f"elbow_{s}"]),
                    f"Bip01_{g}_Hand": (A[f"elbow_{s}"], A[f"wrist_{s}"]),
                    f"Bip01_{g}_Finger0": (A[f"wrist_{s}"], A[f"thumb_{s}1"]),
                    f"Bip01_{g}_Finger01": (A[f"thumb_{s}1"], A[f"thumb_{s}2"]),
                    f"Bip01_{g}_Finger1": (A[f"wrist_{s}"], A[f"middle_{s}1"]),
                    f"Bip01_{g}_Finger11": (A[f"middle_{s}1"], A[f"middle_{s}2"])})
    # the thighs hang from the model's own hips; the knees (Calf) stay on the game's knees so the feet still land
    G0 = {k: v.copy() for k, v in G.items()}
    newpos = {}
    for name in gorder:  # parents before children
        p = gw[name][0]
        if name in exact:
            newpos[name] = exact[name].copy()
        elif name in seg:
            a, b = seg[name]
            newpos[name] = newpos.get(p, G0[p]) + (G0[name] - G0[p]).normalized() * (b - a).length
    NO_MOVE = {"lowerbody"}  # the pelvis bone stays on the game's (animated) pivot; the hips around it don't move
    bpy.context.view_layer.objects.active = game
    bpy.ops.object.mode_set(mode="EDIT")
    for name, p in newpos.items():
        eb = game.data.edit_bones[name]
        m = eb.matrix.copy()
        m.translation = p
        eb.matrix = m
    bpy.ops.object.mode_set(mode="OBJECT")
    for name, p in newpos.items():
        print(f"[g04] own joint {name:<18} moved {(p - G[name]).length:5.1f}")
        G[name] = p.copy()
CHILD = {"lowerbody": ("upperbody", "Bip01_Spine"), "upperbody": ("upperbody2", "Bip01_Spine1"),
         "upperbody2": ("neck", "Bip01_Neck1"), "neck": ("head", "Bip01_Head")}
for s, g in (("L", gs), ("R", go)):
    CHILD.update({f"shoulder_{s}": (f"arm_{s}", f"Bip01_{g}_UpperArm"), f"arm_{s}": (f"elbow_{s}", f"Bip01_{g}_Forearm"),
                  f"elbow_{s}": (f"wrist_{s}", f"Bip01_{g}_Hand"), f"leg_{s}": (f"knee_{s}", f"Bip01_{g}_Calf"),
                  f"knee_{s}": (f"ankle_{s}", f"Bip01_{g}_Foot"), f"ankle_{s}": (f"toes_{s}", f"Bip01_{g}_Toe0")})
STRETCH = {f"{j}_{s}" for j in ("arm", "elbow", "leg", "knee") for s in "LR"}
MMD_TAIL = [f"tail{i}" if i > 1 else "tail" for i in range(1, 23)]
GAME_TAIL = ["Bip01_Tail"] + [f"Bip01_Tail{i}" for i in range(1, 15)]


def stretch(axis, k):
    a = axis.normalized()
    return (Matrix.Identity(3) + (k - 1) * Matrix([[a.x * a.x, a.x * a.y, a.x * a.z], [a.y * a.x, a.y * a.y, a.y * a.z],
                                                     [a.z * a.x, a.z * a.y, a.z * a.z]])).to_4x4()


order = [EN[b.name] for b in mmd.data.bones]
Mj, Rj = {}, {}
for j in order:
    if j in NO_MOVE:
        Rj[j], Mj[j] = Matrix.Identity(4), Malign
    elif j in MAP:
        g = MAP[j]
        R = Rj.get(PARENT[j], Matrix.Identity(4))
        S = Matrix.Identity(4)
        if j in CHILD and CHILD[j][0] in A:
            c, gc = CHILD[j]
            d0, d1 = A[c] - A[j], G[gc] - G[g]
            R = d0.normalized().rotation_difference(d1.normalized()).to_matrix().to_4x4()
            if j in STRETCH:
                S = stretch(d0, max(0.6, min(1.7, d1.length / d0.length)))
        Rj[j] = R
        Mj[j] = Matrix.Translation(G[g]) @ R @ S @ Matrix.Translation(-A[j]) @ Malign
    elif j not in MMD_TAIL:
        p = PARENT[j]
        while p is not None and p not in Mj:
            p = PARENT[p]
        Rj[j], Mj[j] = (Rj[p], Mj[p]) if p else (Matrix.Identity(4), Malign)

# tail: spread the 22 MMD tail joints along the 15-bone game tail by arc length
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

p_pts = [A[j] for j in MMD_TAIL]
p_pts.append(p_pts[-1] + (p_pts[-1] - p_pts[-2]))
g_pts = [G[n] for n in GAME_TAIL]
g_pts.append(g_pts[-1] + (g_pts[-1] - g_pts[-2]))
p_acc, g_acc = arclen(p_pts), arclen(g_pts)
tail_seg = {}
for i, j in enumerate(MMD_TAIL):
    q0 = at(g_pts, g_acc, p_acc[i] / p_acc[-1] * g_acc[-1])
    q1 = at(g_pts, g_acc, p_acc[i + 1] / p_acc[-1] * g_acc[-1])
    d0 = p_pts[i + 1] - p_pts[i]
    R = d0.normalized().rotation_difference((q1 - q0).normalized()).to_matrix().to_4x4()
    Mj[j] = Matrix.Translation(q0) @ R @ stretch(d0, (q1 - q0).length / d0.length) @ Matrix.Translation(-p_pts[i]) @ Malign
    Rj[j] = R
    tail_seg[j] = (q0, q1, p_acc[i] / p_acc[-1], p_acc[i + 1] / p_acc[-1])
for j in order:  # anything hanging off the tail (tail spines) follows its tail bone
    if j not in Mj:
        p = PARENT[j]
        while p not in Mj:
            p = PARENT[p]
        Mj[j], Rj[j] = Mj[p], Rj[p]
print(f"[g04] tail length mmd={p_acc[-1]:.1f} game={g_acc[-1]:.1f}")

# --- materials: drop see-through overlays, sort into the two game slots, pack eyes into the body sheet ----------
me = body.data
mat_names = [m.name for m in me.materials]
DROP = {"eyes2", "eyefire"}
EYES = {"eyes"}
SPINES = {"claws", "teeth", "tongue", "spines", "spines2"}
PLATES = {"spines", "spines2"}
bm = bmesh.new()
bm.from_mesh(me)
bmesh.ops.delete(bm, geom=[f for f in bm.faces if mat_names[f.material_index] in DROP], context="FACES")
bm.to_mesh(me)
bm.free()
uv = me.uv_layers.active.data
plate_tris = []
for poly in me.polygons:
    name = mat_names[poly.material_index]
    for li in poly.loop_indices:
        u, v = uv[li].uv
        if name in SPINES:
            continue
        uv[li].uv = ((0.5 + u * 0.5) if name in EYES else (u * 0.5), v)
    if name in PLATES:
        plate_tris.append([tuple(uv[li].uv) for li in poly.loop_indices])
print(f"[g04] removed overlay faces; {len(plate_tris)} spine-plate faces for the glow mask")
# mark the dorsal-plate vertices so rigid_plates.py can pin each plate to the skin under it
is_plate = [False] * len(me.vertices)
for poly in me.polygons:
    if mat_names[poly.material_index] in PLATES:
        for vi in poly.vertices:
            is_plate[vi] = True
me.attributes.new("is_plate", "BOOLEAN", "POINT").data.foreach_set("value", is_plate)

# plate mask (1024, rows top-down like a PNG) by filling each plate face's UV triangle(s)
SIZE = 1024
mask = np.zeros((SIZE, SIZE), dtype=np.float32)
for tri in plate_tris:
    for k in range(1, len(tri) - 1):
        a, b, c = (np.array([p[0] * SIZE, (1 - p[1]) * SIZE]) for p in (tri[0], tri[k], tri[k + 1]))
        x0, x1 = int(max(0, np.floor(min(a[0], b[0], c[0])))), int(min(SIZE - 1, np.ceil(max(a[0], b[0], c[0]))))
        y0, y1 = int(max(0, np.floor(min(a[1], b[1], c[1])))), int(min(SIZE - 1, np.ceil(max(a[1], b[1], c[1]))))
        if x1 < x0 or y1 < y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-9:
            continue
        l1 = ((b[1] - c[1]) * (xs - c[0]) + (c[0] - b[0]) * (ys - c[1])) / d
        l2 = ((c[1] - a[1]) * (xs - c[0]) + (a[0] - c[0]) * (ys - c[1])) / d
        inside = (l1 >= -0.01) & (l2 >= -0.01) & (1 - l1 - l2 >= -0.01)
        mask[y0:y1 + 1, x0:x1 + 1][inside] = 1.0
img = bpy.data.images.new("plates", SIZE, SIZE, alpha=False)
img.colorspace_settings.name = "Non-Color"
rgba = np.ones((SIZE, SIZE, 4), dtype=np.float32)
rgba[..., :3] = np.flipud(mask)[..., None]  # Blender pixel rows run bottom-up
img.pixels = rgba.ravel()
img.filepath_raw = mask_png
img.file_format = "PNG"
img.save()
print(f"[g04] plate mask covers {mask.mean() * 100:.1f}% of the spines sheet -> {mask_png}")

# --- bake the move (linear blend skinning) ----------------------------------------------------------------------
n = len(me.vertices)
co = np.empty(n * 3)
me.vertices.foreach_get("co", co)
co = np.c_[co.reshape(n, 3), np.ones(n)]
names = {g.index: EN.get(g.name, g.name) for g in body.vertex_groups}
Mnp = {j: np.array(Mj[j]) for j in Mj}
out = np.zeros((n, 4))
lin = np.zeros((n, 3, 3))
for v in me.vertices:
    gs_ = [(names[g.group], g.weight) for g in v.groups if g.weight > 0 and names[g.group] in Mnp]
    tw = sum(w for _, w in gs_) or 1.0
    if not gs_:
        out[v.index] = np.array(Malign) @ co[v.index]
        lin[v.index] = np.array(Malign)[:3, :3]
        continue
    for j, w in gs_:
        out[v.index] += (w / tw) * (Mnp[j] @ co[v.index])
        lin[v.index] += (w / tw) * Mnp[j][:3, :3]
corner_n = [me.corner_normals[i].vector.copy() for i in range(len(me.loops))]
me.vertices.foreach_set("co", out[:, :3].ravel())
me.normals_split_custom_set([Vector(np.linalg.inv(lin[l.vertex_index]).T @ np.array(corner_n[i])).normalized()
                             for i, l in enumerate(me.loops)])
me.update()

# --- re-weight onto game bones ----------------------------------------------------------------------------------
def game_bone(j):
    if j in WEIGHT_TO:
        return WEIGHT_TO[j]
    while j is not None and j not in MAP:
        if j in tail_seg:
            return None  # handled by the tail mapping
        j = PARENT[j]
    return MAP.get(j, "Bip01_Pelvis") if j else "Bip01_Pelvis"


def tail_owner(j):
    while j not in tail_seg:
        j = PARENT[j]
    return j


def tail_split(co_, j):
    q0, q1, f0, f1 = tail_seg[j]
    ab = q1 - q0
    t = max(0.0, min(1.0, (co_ - q0).dot(ab) / max(ab.length_squared, 1e-9)))
    d = (f0 + t * (f1 - f0)) * g_acc[-1]
    for i in range(len(g_pts) - 1):
        if d <= g_acc[i + 1] or i == len(g_pts) - 2:
            seg = g_acc[i + 1] - g_acc[i]
            u = 0.0 if seg == 0 else (d - g_acc[i]) / seg
            k = min(i, len(GAME_TAIL) - 1)
            if u < 0.5 and k > 0:
                return [(GAME_TAIL[k], 0.5 + u), (GAME_TAIL[k - 1], 0.5 - u)]
            if u >= 0.5 and k < len(GAME_TAIL) - 1:
                return [(GAME_TAIL[k], 1.5 - u), (GAME_TAIL[k + 1], u - 0.5)]
            return [(GAME_TAIL[k], 1.0)]


neck_z, spine1_z = G["Bip01_Neck"].z, G["Bip01_Spine1"].z
per_vert = []
for v in me.vertices:
    acc = {}
    for g in v.groups:
        j = names[g.group]
        if g.weight <= 0:
            continue
        gb = game_bone(j)
        if gb is None:
            for name, f in tail_split(v.co, tail_owner(j)):
                acc[name] = acc.get(name, 0) + g.weight * f
            continue
        if gb == "Bip01_Spine1":  # upper chest: blend toward the game's Neck bone (where the arms hang) by height
            t = max(0.0, min(1.0, (v.co.z - spine1_z) / (neck_z - spine1_z)))
            acc["Bip01_Spine1"] = acc.get("Bip01_Spine1", 0) + g.weight * (1 - t)
            acc["Bip01_Neck"] = acc.get("Bip01_Neck", 0) + g.weight * t
            continue
        acc[gb] = acc.get(gb, 0) + g.weight
    per_vert.append(acc or {"Bip01_Pelvis": 1.0})
for g in list(body.vertex_groups):
    body.vertex_groups.remove(g)
groups = {}
for vi, acc in enumerate(per_vert):
    for name, w in acc.items():
        if name not in groups:
            groups[name] = body.vertex_groups.new(name=name)
        groups[name].add([vi], w, "REPLACE")
body.modifiers.clear()

# --- two game slots, smooth shading, final objects --------------------------------------------------------------
base = bpy.data.materials.new(BODY_SLOT)
spines = bpy.data.materials.new(SPINES_SLOT)
slot_of = [1 if name in SPINES else 0 for name in mat_names]
src_tex = {}
for m in me.materials:
    node = m.node_tree.nodes.get("Image Texture") if m.node_tree else None
    if node:
        src_tex[m.name] = node.image
for mat, key in ((base, "body"), (spines, "spines")):
    mat.use_nodes = True
    if key in src_tex:
        t = mat.node_tree.nodes.new("ShaderNodeTexImage")
        t.image = src_tex[key]
        mat.node_tree.links.new(t.outputs["Color"], mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
old_index = [p.material_index for p in me.polygons]
me.materials.clear()
me.materials.append(base)
me.materials.append(spines)
for p, oi in zip(me.polygons, old_index):
    p.material_index = slot_of[oi]
with bpy.context.temp_override(object=body, active_object=body, selected_objects=[body]):
    bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
body.name = "SK_GZPro_Gigan_FW"
body.parent = game
body.matrix_parent_inverse = Matrix.Identity(4)
body.modifiers.new("Armature", "ARMATURE").object = game
bpy.data.objects.remove(mmd)

zs = [v.co.z for v in me.vertices]
print(f"[g04] final mesh: {len(me.vertices)} verts, {len(me.polygons)} faces, {len(body.vertex_groups)} bones, "
      f"height {max(zs) - min(zs):.1f} (game ~101.4), lowest {min(zs):.1f} (game ~-0.2)")
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
print("[g04] saved", out_blend)
