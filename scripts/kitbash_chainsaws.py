"""Wii Final Wars Gigan with the PS3 model's chainsaw hands.

Both inputs are already fitted to the game skeleton, so the parts line up at the wrists:
  - the Wii blades (vertices driven mostly by the Hand bones) are removed,
  - the PS3 chainsaw assemblies (vertices driven mostly by the Forearm/wrist bones) are copied in, staying on the
    wrist bone so they move like arm-mounted saws, not like hooks,
  - the saws are re-UV'd onto the Wii texture's blade metal, so they wear the same metal as the hook hands did.

Usage: blender -b gigan_fw_final.blend --python kitbash_chainsaws.py -- <gigan_ps3_fitted.blend> <out.blend>
"""
import sys
import bpy, bmesh
import numpy as np
from mathutils import Vector

ps3_blend, out_blend = sys.argv[sys.argv.index("--") + 1:]
body = bpy.data.objects["SK_GZPro_Gigan_FW"]
SIDES = ("L", "R")


def dominant(ob):
    idx = {g.index: g.name for g in ob.vertex_groups}
    return [idx[max(v.groups, key=lambda g: g.weight).group] if v.groups else None for v in ob.data.vertices]


# --- blade UV area on the Wii texture (where the hook-hand metal lives) -------------------------
dom = dominant(body)
uv = body.data.uv_layers.active.data
blade_uv = {s: [] for s in SIDES}
for poly in body.data.polygons:
    for s in SIDES:
        if all(dom[vi] == f"Bip01_{s}_Hand" for vi in poly.vertices):
            blade_uv[s] += [tuple(uv[li].uv) for li in poly.loop_indices]
uvs = np.array(blade_uv["L"] + blade_uv["R"])
u0, v0 = np.percentile(uvs, 10, axis=0)  # inner part of the blade islands, away from their edges
u1, v1 = np.percentile(uvs, 90, axis=0)
print(f"[saw] blade metal UV area u {u0:.3f}..{u1:.3f} v {v0:.3f}..{v1:.3f}")

# --- the line each Wii blade runs along, measured before the blades go ---------------------------
# The PS3 saws arrive at the PS3 forearm's angle, which kinks upward off the Wii forearm and leaves a gap. Each saw
# is turned onto its blade's line and slid back so its housing overlaps the Wii forearm cuff.
OVERLAP = 2.0  # how far the saw housing reaches back past where the blade started, working units
rig = body.parent
blade = {}
for s in SIDES:
    pivot = Vector(rig.data.bones[f"Bip01_{s}_Hand"].head_local)
    pts = np.array([tuple(body.data.vertices[i].co) for i, d in enumerate(dom) if d == f"Bip01_{s}_Hand"])
    c = pts.mean(0)
    axis = np.linalg.svd(pts - c, full_matrices=False)[2][0]
    if np.dot(c - np.array(pivot), axis) < 0:
        axis = -axis
    start = ((pts - np.array(pivot)) @ axis).min()
    blade[s] = (pivot, Vector(axis), start)

# --- remove the Wii blades ----------------------------------------------------------------------
bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
hand = {f"Bip01_{s}_Hand" for s in SIDES}
kill = [f for f in bm.faces if sum(dom[v.index] in hand for v in f.verts) * 2 > len(f.verts)]
bmesh.ops.delete(bm, geom=kill, context="FACES_ONLY")
loose = [v for v in bm.verts if not v.link_faces]
bmesh.ops.delete(bm, geom=loose, context="VERTS")
bm.to_mesh(body.data)
bm.free()
print(f"[saw] removed {len(kill)} blade faces")

# --- bring in the PS3 chainsaws -----------------------------------------------------------------
with bpy.data.libraries.load(ps3_blend) as (src, dst):
    dst.objects = ["SK_GZPro_Gigan_FW"]
saw = dst.objects[0]
saw.name = "PS3_Chainsaws"
bpy.context.scene.collection.objects.link(saw)
saw.parent = None
saw.modifiers.clear()
sdom = dominant(saw)
keep = {f"Bip01_{s}_Forearm" for s in SIDES}
bm = bmesh.new()
bm.from_mesh(saw.data)
bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[v for v in bm.verts if sdom[v.index] not in keep], context="VERTS")
bm.to_mesh(saw.data)
bm.free()
sdom = dominant(saw)
print(f"[saw] chainsaw vertices kept: {len(saw.data.vertices)}")

for s in SIDES:
    pivot, baxis, bstart = blade[s]
    vids = [i for i, d in enumerate(sdom) if d == f"Bip01_{s}_Forearm"]
    pts = [saw.data.vertices[i].co.copy() for i in vids]
    c = sum(pts, Vector()) / len(pts)
    arr = np.array([tuple(p - c) for p in pts])
    saxis = Vector(np.linalg.svd(arr, full_matrices=False)[2][0])
    if (c - pivot).dot(saxis) < 0:
        saxis = -saxis
    rot = saxis.rotation_difference(baxis).to_matrix()
    moved = [pivot + rot @ (p - pivot) for p in pts]
    near = min((p - pivot).dot(baxis) for p in moved)
    shift = baxis * ((bstart - OVERLAP) - near)
    for i, p in zip(vids, moved):
        saw.data.vertices[i].co = p + shift
    print(f"[saw] {s} chainsaw turned {saxis.angle(baxis) * 57.2958:.0f} deg onto the blade line, moved {shift.length:.1f}")
saw.data.update()

# --- re-UV the saws onto the blade metal: planar projection on each saw's two longest axes ------
suv = saw.data.uv_layers.active.data
for s in SIDES:
    vids = [i for i, d in enumerate(sdom) if d == f"Bip01_{s}_Forearm"]
    pts = np.array([tuple(saw.data.vertices[i].co) for i in vids])
    c = pts.mean(0)
    _, _, axes = np.linalg.svd(pts - c, full_matrices=False)
    a, b = (pts - c) @ axes[0], (pts - c) @ axes[1]
    lo_a, hi_a, lo_b, hi_b = a.min(), a.max(), b.min(), b.max()
    proj = {}
    for k, vi in enumerate(vids):
        proj[vi] = (u0 + (a[k] - lo_a) / (hi_a - lo_a) * (u1 - u0), v0 + (b[k] - lo_b) / (hi_b - lo_b) * (v1 - v0))
    for li, loop in enumerate(saw.data.loops):
        if loop.vertex_index in proj:
            suv[li].uv = proj[loop.vertex_index]
saw.data.materials.clear()
for m in body.data.materials:
    saw.data.materials.append(m)
for poly in saw.data.polygons:
    poly.material_index = 0

# --- merge into the Wii mesh ---------------------------------------------------------------------
bpy.ops.object.select_all(action="DESELECT")
saw.select_set(True)
body.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()
unweighted = sum(1 for v in body.data.vertices if not v.groups)
print(f"[saw] merged mesh: {len(body.data.vertices)} verts, {len(body.data.polygons)} faces, unweighted {unweighted}")
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
print("[saw] saved", out_blend)
