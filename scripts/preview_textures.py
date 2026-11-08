import sys, os, bpy
tex, prefix, *rest = sys.argv[sys.argv.index("--") + 1:]
body = next(o for o in bpy.data.objects if o.type == "MESH")
for mat, part in zip(body.data.materials, ("body", "spines")):
    mat.use_nodes = True
    nt = mat.node_tree
    t = next((n for n in nt.nodes if n.type == "TEX_IMAGE"), None) or nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(os.path.join(tex, f"{prefix}_{part}_C.png"))
    nt.links.new(t.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    print("[prev]", mat.name, "->", t.image.filepath)
bpy.ops.wm.save_as_mainfile(filepath=rest[0] if rest else bpy.data.filepath)
