import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from mathutils import Vector, Matrix
from gzrig import game_world, wii_world, build_armature, apply_pose, rot_only, umeyama

bones_json, out_blend = sys.argv[sys.argv.index("--") + 1:]
UNIT = 0.01

gw, gorder = game_world(bones_json)
game = build_armature("GZ1_Gigan", gw, gorder, UNIT)
gframe = {b.name: b.matrix_local.copy() for b in game.data.bones}

wii = bpy.data.objects["Gigan_FW_Armature"]
wii_meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.parent == wii]

core = ["Bip01_Pelvis", "Bip01_Spine", "Bip01_Spine1", "Bip01_Neck", "Bip01_Neck1", "Bip01_Head",
        "Bip01_L_Clavicle", "Bip01_R_Clavicle", "Bip01_L_Thigh", "Bip01_R_Thigh", "Bip01_L_Calf", "Bip01_R_Calf",
        "Bip01_L_Foot", "Bip01_R_Foot"]
ww = wii_world(wii)
M, s = umeyama([ww[n][1].translation for n in core], [gframe[n].translation for n in core])
print(f"[fit] align scale={s:.4f}")
bpy.ops.object.select_all(action="DESELECT")
for o in [wii] + wii_meshes:
    o.select_set(True)
for o in wii_meshes:
    o.matrix_world = M @ o.matrix_world
wii.matrix_world = M @ wii.matrix_world
for o in wii_meshes:
    o.matrix_parent_inverse = Matrix.Identity(4)
    o.matrix_world = M
bpy.context.view_layer.objects.active = wii
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

SHOULDER_HALF_TWIST = False
TWIST = {"L": "Bip01_L_Deltoid_Twist_1", "R": "Bip01_R_Deltoid_Twist_1"}
FOLD = {
    "Bip01_Neck2": "Bip01_Neck1",
    "Bip01_L_Deltoid_Twist_2": "Bip01_L_UpperArm", "Bip01_R_Deltoid_Twist_2": "Bip01_R_UpperArm",
    "Bip01_L_Armpit_Mover": "Bip01_Spine1", "Bip01_R_Armpit_Mover": "Bip01_Spine1",
    "Bip01_L_Femur_Twist": "Bip01_L_Thigh", "Bip01_R_Femur_Twist": "Bip01_R_Thigh",
    "Bip01_Rectus_Abdominis_Flexor": "Bip01_Spine",
    "Bip01_L_Hipfat_Mover": "Bip01_Pelvis", "Bip01_R_Hipfat_Mover": "Bip01_Pelvis",
    "Bip01_L_Toe1": "Bip01_L_Toe0", "Bip01_R_Toe1": "Bip01_R_Toe0",
}

def merge_group(ob, src, dst):
    g = ob.vertex_groups.get(src)
    if g is None:
        return 0
    d = ob.vertex_groups.get(dst) or ob.vertex_groups.new(name=dst)
    n = 0
    for v in ob.data.vertices:
        for ge in v.groups:
            if ge.group == g.index and ge.weight > 0:
                d.add([v.index], ge.weight, "ADD")
                n += 1
    ob.vertex_groups.remove(g)
    return n

if not SHOULDER_HALF_TWIST:
    FOLD.update({tw: f"Bip01_{side}_UpperArm" for side, tw in TWIST.items()})
for ob in wii_meshes:
    for src, dst in FOLD.items():
        merge_group(ob, src, dst)

wii_tail = sorted([b.name for b in wii.data.bones if re.fullmatch(r"Bip01_Tail\d\d", b.name)])
game_tail = ["Bip01_Tail"] + [f"Bip01_Tail{i}" for i in range(1, 17)]

def chain_points(frames):
    pts = [f.translation.copy() for f in frames]
    pts.append(pts[-1] + (pts[-1] - pts[-2]))
    return pts

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
            t = 0.0 if seg == 0 else (d - acc[i]) / seg
            return pts[i].lerp(pts[i + 1], t), i, t
    return pts[-1], len(pts) - 2, 1.0

ww = wii_world(wii)
w_pts = chain_points([ww[n][1] for n in wii_tail])
g_pts = chain_points([gframe[n] for n in game_tail])
w_acc, g_acc = arclen(w_pts), arclen(g_pts)
print(f"[fit] tail length wii={w_acc[-1]:.1f} game={g_acc[-1]:.1f} ({len(wii_tail)} vs {len(game_tail)} bones)")

target = {}
for b in wii.data.bones:
    if b.name in gframe:
        target[b.name] = gframe[b.name]
for j, n in enumerate(wii_tail):
    d = w_acc[j] / w_acc[-1] * g_acc[-1]
    p, seg, _ = at(g_pts, g_acc, d)
    p2, _, _ = at(g_pts, g_acc, w_acc[j + 1] / w_acc[-1] * g_acc[-1])
    f = gframe[game_tail[min(seg, len(game_tail) - 1)]].copy()
    cur = f.to_3x3() @ Vector((0, 1, 0))
    rot = cur.rotation_difference((p2 - p).normalized()).to_matrix()
    f3 = rot @ f.to_3x3()
    f = f3.to_4x4()
    f.translation = p
    target[n] = f

for side, tw in (TWIST.items() if SHOULDER_HALF_TWIST else ()):
    cl, ua = f"Bip01_{side}_Clavicle", f"Bip01_{side}_UpperArm"
    btw, bcl, bua = (wii.data.bones[n].matrix_local for n in (tw, cl, ua))
    via_ua = target[ua] @ bua.inverted() @ btw
    via_cl = target[cl] @ bcl.inverted() @ btw
    half = via_cl.to_quaternion().slerp(via_ua.to_quaternion(), 0.5).to_matrix().to_4x4()
    half.translation = via_ua.translation
    target[tw] = half
apply_pose(wii, target)
bpy.context.view_layer.update()

for ob in wii_meshes:
    with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob]):
        bpy.ops.object.modifier_apply(modifier="Armature")

tail_bones = game_tail
for ob in (wii_meshes if SHOULDER_HALF_TWIST else ()):
    for side, tw in TWIST.items():
        g = ob.vertex_groups.get(tw)
        if g is None:
            continue
        cl = ob.vertex_groups.get(f"Bip01_{side}_Clavicle") or ob.vertex_groups.new(name=f"Bip01_{side}_Clavicle")
        ua = ob.vertex_groups.get(f"Bip01_{side}_UpperArm") or ob.vertex_groups.new(name=f"Bip01_{side}_UpperArm")
        for v in ob.data.vertices:
            for ge in v.groups:
                if ge.group == g.index and ge.weight > 0:
                    cl.add([v.index], ge.weight * 0.5, "ADD")
                    ua.add([v.index], ge.weight * 0.5, "ADD")
        ob.vertex_groups.remove(g)

g_len = g_acc[-1]
w_frac = [a / w_acc[-1] for a in w_acc]

def game_seg_at(d):
    d = max(0.0, min(d, g_len))
    for i in range(len(g_pts) - 1):
        if d <= g_acc[i + 1] or i == len(g_pts) - 2:
            seg = g_acc[i + 1] - g_acc[i]
            return i, (0.0 if seg == 0 else (d - g_acc[i]) / seg)

for ob in wii_meshes:
    for n in wii_tail:
        if n in ob.vertex_groups:
            ob.vertex_groups[n].name = "WII_" + n
    tgs = {ob.vertex_groups["WII_" + n].index: j for j, n in enumerate(wii_tail) if "WII_" + n in ob.vertex_groups}
    if not tgs:
        continue
    new = {n: (ob.vertex_groups.get(n) or ob.vertex_groups.new(name=n)) for n in tail_bones}
    for v in ob.data.vertices:
        for ge in v.groups:
            if ge.group not in tgs or ge.weight <= 0:
                continue
            j, w = tgs[ge.group], ge.weight
            a, _, _ = at(g_pts, g_acc, w_frac[j] * g_len)
            b, _, _ = at(g_pts, g_acc, w_frac[j + 1] * g_len)
            ab = b - a
            t = max(0.0, min(1.0, (v.co - a).dot(ab) / max(ab.length_squared, 1e-9)))
            k, u = game_seg_at((w_frac[j] + t * (w_frac[j + 1] - w_frac[j])) * g_len)
            k = min(k, len(tail_bones) - 1)
            if u < 0.5 and k > 0:
                new[tail_bones[k]].add([v.index], w * (0.5 + u), "ADD")
                new[tail_bones[k - 1]].add([v.index], w * (0.5 - u), "ADD")
            elif u >= 0.5 and k < len(tail_bones) - 1:
                new[tail_bones[k]].add([v.index], w * (1.5 - u), "ADD")
                new[tail_bones[k + 1]].add([v.index], w * (u - 0.5), "ADD")
            else:
                new[tail_bones[k]].add([v.index], w, "ADD")
    for gi in sorted(tgs, reverse=True):
        ob.vertex_groups.remove(ob.vertex_groups[gi])

for ob in wii_meshes:
    part = int(ob.name.rsplit("_", 1)[-1])
    attr = ob.data.attributes.new("wii_part", "INT", "FACE")
    attr.data.foreach_set("value", [part] * len(ob.data.polygons))
bpy.ops.object.select_all(action="DESELECT")
for ob in wii_meshes:
    ob.select_set(True)
bpy.context.view_layer.objects.active = wii_meshes[1]
bpy.ops.object.join()
body = bpy.context.view_layer.objects.active
body.name = "SK_GZPro_Gigan_FW"
body.parent = None
for m in list(body.modifiers):
    body.modifiers.remove(m)

unknown = [g.name for g in body.vertex_groups if g.name not in gframe]
print("[fit] groups not on game skeleton:", unknown)
for n in unknown:
    parent = wii.data.bones[n].parent.name if n in wii.data.bones and wii.data.bones[n].parent else "Bip01_Pelvis"
    merge_group(body, n, parent)

tex = next(m for m in bpy.data.materials if m.name.startswith("Gigan_FW"))
base = bpy.data.materials.new("gigan_base")
saw = bpy.data.materials.new("gigan_buzzsaw_static")
for mat in (base, saw):
    mat.use_nodes = True
    src = tex.node_tree.nodes.get("Image Texture")
    if src:
        t = mat.node_tree.nodes.new("ShaderNodeTexImage")
        t.image = src.image
        mat.node_tree.links.new(t.outputs["Color"], mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
body.data.materials.clear()
body.data.materials.append(base)
body.data.materials.append(saw)
sg = body.vertex_groups.get("Bip01_BuzzSaw")
saw_faces = 0
for poly in body.data.polygons:
    on_saw = sg is not None and all(
        any(ge.group == sg.index and ge.weight > 0.5 for ge in body.data.vertices[vi].groups) for vi in poly.vertices)
    poly.material_index = 1 if on_saw else 0
    saw_faces += on_saw
print(f"[fit] buzzsaw faces: {saw_faces} / {len(body.data.polygons)}")

with bpy.context.temp_override(object=body, active_object=body, selected_objects=[body]):
    bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)

unweighted = [v.index for v in body.data.vertices if not any(ge.weight > 0 for ge in v.groups)]
print(f"[fit] unweighted vertices: {len(unweighted)}")
body.parent = game
mod = body.modifiers.new("Armature", "ARMATURE")
mod.object = game
bpy.data.objects.remove(wii)
for o in list(bpy.data.objects):
    if o.type == "CAMERA":
        bpy.data.objects.remove(o)
used = sorted({g.name for g in body.vertex_groups})
print(f"[fit] final mesh: {len(body.data.vertices)} verts, {len(body.data.polygons)} faces, {len(used)} weighted bones")
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
print("[fit] saved", out_blend)
