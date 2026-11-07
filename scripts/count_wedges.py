import bpy
me = bpy.data.objects["SK_GZPro_Gigan_FW"].data
uv = me.uv_layers.active.data
wedges_n, wedges_nu = set(), set()
for li, loop in enumerate(me.loops):
    n = tuple(round(x, 3) for x in me.corner_normals[li].vector)
    u = tuple(round(x, 4) for x in uv[li].uv)
    wedges_n.add((loop.vertex_index, n))
    wedges_nu.add((loop.vertex_index, n, u))
print(f"[w] verts={len(me.vertices)} loops={len(me.loops)} unique(v,normal)={len(wedges_n)} unique(v,normal,uv)={len(wedges_nu)} sharp_edges={sum(e.use_edge_sharp for e in me.edges)}")
print("[w] attributes:", [(a.name, a.domain, a.data_type) for a in me.attributes])
