"""Give the Wii's single-sided parts (wing membranes, wii_part == 4) a flipped back face, because the game
material renders front faces only. Back-face loops get the negated normal of the matching front loop.
Usage: blender -b in.blend --python double_side.py -- <out.blend> [part,part...]
"""
import sys
import bpy, bmesh

args = sys.argv[sys.argv.index("--") + 1:]
out_blend = args[0]
parts = {int(p) for p in args[1].split(",")} if len(args) > 1 else {4}

body = bpy.data.objects["SK_GZPro_Gigan_FW"]
me = body.data
# per-corner normals as the mesh currently has them, keyed by (face, vertex)
loop_normals = {}
for poly in me.polygons:
    for li in poly.loop_indices:
        loop_normals[(poly.index, me.loops[li].vertex_index)] = me.corner_normals[li].vector.copy()

bm = bmesh.new()
bm.from_mesh(me)
part_layer = bm.faces.layers.int.get("wii_part")
src_faces = [f for f in bm.faces if f[part_layer] in parts]
src_index = {f: f.index for f in src_faces}
dup = bmesh.ops.duplicate(bm, geom=src_faces)
new_faces = [g for g in dup["geom"] if isinstance(g, bmesh.types.BMFace)]
face_map = dup["face_map"]  # old -> new and new -> old
vert_map = dup["vert_map"]
bmesh.ops.reverse_faces(bm, faces=new_faces)
bm.faces.index_update()
bm.verts.index_update()

# back-face normals: negate the front face's normal at the original vertex
inv_vert = {}
for k, v in vert_map.items():
    if isinstance(k, bmesh.types.BMVert) and isinstance(v, bmesh.types.BMVert):
        inv_vert[v] = k
        inv_vert[k] = v
back_normals = {}
for nf in new_faces:
    of = face_map.get(nf)
    if of is None or of not in src_index:
        continue
    for loop in nf.loops:
        ov = inv_vert.get(loop.vert)
        if ov is not None:
            back_normals[(nf.index, loop.vert.index)] = -loop_normals[(src_index[of], ov.index)]
bm.to_mesh(me)
bm.free()

normals = []
for poly in me.polygons:
    for li in poly.loop_indices:
        key = (poly.index, me.loops[li].vertex_index)
        normals.append(back_normals.get(key) or loop_normals.get(key) or poly.normal)
me.normals_split_custom_set(normals)
print(f"[2side] parts {sorted(parts)}: added {len(new_faces)} back faces ({len(back_normals)} corners with flipped normals)")
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
print("[2side] saved", out_blend)
