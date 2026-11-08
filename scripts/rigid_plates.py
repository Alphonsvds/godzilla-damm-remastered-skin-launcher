"""Pin each dorsal plate to the skin under it: every vertex of a plate gets the same skin weights, copied from the
body skin where the plate sits. Without this the plates keep their MMD parent's single bone while the back under them
follows blended torso/tail weights, so in motion the plates slide off the back and float.

Plate vertices are the ones fit_g2004.py marked with the "is_plate" attribute.
Usage: blender -b in.blend --python rigid_plates.py -- <out.blend>
"""
import sys
import bpy
from mathutils.kdtree import KDTree

out_blend = sys.argv[sys.argv.index("--") + 1]
body = bpy.data.objects["SK_GZPro_Gigan_FW"]
me = body.data
plate = [False] * len(me.vertices)
me.attributes["is_plate"].data.foreach_get("value", plate)

# skin = vertices used only by body-slot faces (not plates, claws, teeth)
in_slot1 = [False] * len(me.vertices)
for p in me.polygons:
    if p.material_index == 1:
        for vi in p.vertices:
            in_slot1[vi] = True
skin = [v.index for v in me.vertices if not in_slot1[v.index]]
kd = KDTree(len(skin))
for i in skin:
    kd.insert(me.vertices[i].co, i)
kd.balance()

# plates as connected islands of plate vertices
adj = {}
for e in me.edges:
    a, b = e.vertices
    if plate[a] and plate[b]:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
seen, islands = set(), []
for v in range(len(me.vertices)):
    if plate[v] and v not in seen:
        stack, isl = [v], []
        seen.add(v)
        while stack:
            x = stack.pop()
            isl.append(x)
            for y in adj.get(x, ()):
                if y not in seen:
                    seen.add(y)
                    stack.append(y)
        islands.append(isl)

names = {g.index: g.name for g in body.vertex_groups}
groups = {g.name: g for g in body.vertex_groups}


def weights(vi):
    return {names[g.group]: g.weight for g in me.vertices[vi].groups if g.weight > 0}


moved = 0
for isl in islands:
    # the plate's root: the plate vertex closest to the skin; average the weights of the skin around that spot
    root, (co, si, dist) = min(((v, kd.find(me.vertices[v].co)) for v in isl), key=lambda t: t[1][2])
    acc = {}
    for _co, i, d in kd.find_n(me.vertices[root].co, 8):
        for n, w in weights(i).items():
            acc[n] = acc.get(n, 0) + w / (1 + d)
    top = sorted(acc.items(), key=lambda t: -t[1])[:4]
    tot = sum(w for _, w in top)
    for v in isl:
        for g in list(me.vertices[v].groups):
            body.vertex_groups[g.group].remove([v])
        for n, w in top:
            groups[n].add([v], w / tot, "REPLACE")
    moved += len(isl)
print(f"[plates] pinned {len(islands)} plates ({moved} vertices) to the skin under them")
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
