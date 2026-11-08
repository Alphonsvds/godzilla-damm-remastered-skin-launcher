import sys, xml.etree.ElementTree as ET

NS = "{http://www.collada.org/2005/11/COLLADASchema}"
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]

def walk(node, depth, out):
    if node.get("type") == "JOINT":
        out.append("  " * depth + (node.get("sid") or node.get("name") or node.get("id")))
        depth += 1
    for c in node.findall(NS + "node"):
        walk(c, depth, out)

for path in args:
    print("=" * 70)
    print(path)
    root = ET.parse(path).getroot()
    for g in root.iter(NS + "geometry"):
        mesh = g.find(NS + "mesh")
        srcs = {s.get("id"): s for s in mesh.findall(NS + "source")}
        verts = None
        for s in srcs.values():
            fa = s.find(NS + "float_array")
            acc = s.find(f"{NS}technique_common/{NS}accessor")
            if acc is not None and acc.get("stride") == "3" and verts is None:
                verts = int(acc.get("count"))
        print(f"  geometry {g.get('name')}: ~{verts} verts")
    joints = []
    for vs in root.iter(NS + "visual_scene"):
        for n in vs.findall(NS + "node"):
            walk(n, 0, joints)
    print(f"  joints ({len(joints)}):")
    print("\n".join("    " + j for j in joints))
