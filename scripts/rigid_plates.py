"""Pin each dorsal plate to the skin under it. Without this the plates keep their MMD parent's single bone while the
back under them follows blended torso/tail weights, so in motion the plates slide off the back and float.
A plate's buried base takes the weights of the skin right around it (so it stays sealed in a bending back); further
out it fades to one rigid set of weights from the skin at its root, so the blade itself doesn't bend.

Plate vertices are the ones fit_g2004.py marked with the "is_plate" attribute.
Usage: blender -b in.blend --python rigid_plates.py -- <out.blend> [plate_scale]
"""
import sys
import bpy
from mathutils.kdtree import KDTree

args = sys.argv[sys.argv.index("--") + 1:]
out_blend = args[0]
PLATE_SCALE = float(args[1]) if len(args) > 1 else 1.0  # grow each plate about its root (taller, still sealed in)
BASE_NEAR, BASE_FAR = 1.0, 4.0  # plate vertices within BASE_NEAR of the skin follow it; rigid beyond BASE_FAR
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
    if PLATE_SCALE != 1.0:  # grow about the skin point under the root, so the base stays in the skin
        c = co.copy()
        for v in isl:
            me.vertices[v].co = c + (me.vertices[v].co - c) * PLATE_SCALE
    acc = {}
    for _co, i, d in kd.find_n(me.vertices[root].co, 8):
        for n, w in weights(i).items():
            acc[n] = acc.get(n, 0) + w / (1 + d)
    tot = sum(acc.values())
    root_w = {n: w / tot for n, w in acc.items()}
    for v in isl:
        # the buried base follows the skin around it exactly (so it can't poke out of or sink under a bending back);
        # further out the plate goes rigid with its root
        co_v = me.vertices[v].co
        near = kd.find_n(co_v, 4)
        d = near[0][2]
        a = max(0.0, min(1.0, (d - BASE_NEAR) / (BASE_FAR - BASE_NEAR)))
        loc = {}
        for _co, i, dd in near:
            for n, w in weights(i).items():
                loc[n] = loc.get(n, 0) + w / (1 + dd)
        lt = sum(loc.values()) or 1.0
        mix = {n: (1 - a) * loc.get(n, 0) / lt + a * root_w.get(n, 0) for n in set(loc) | set(root_w)}
        top = sorted(mix.items(), key=lambda t: -t[1])[:4]
        tt = sum(w for _, w in top)
        for g in list(me.vertices[v].groups):
            body.vertex_groups[g.group].remove([v])
        for n, w in top:
            groups[n].add([v], w / tt, "REPLACE")
    moved += len(isl)
print(f"[plates] pinned {len(islands)} plates ({moved} vertices) to the skin under them")
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
