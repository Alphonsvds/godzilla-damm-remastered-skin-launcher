import sys, os
import bpy, bmesh
import numpy as np
from mathutils import Matrix

glb, burn_dir, our_dir, mask_png, out = sys.argv[sys.argv.index("--") + 1:]
os.makedirs(out, exist_ok=True)
J = os.path.join
W, H = 4096, 2048
BURN = "2kBurningGodzilla_LP_"

def load(path, w=None, h=None):
    im = bpy.data.images.load(path)
    im.colorspace_settings.name = "Non-Color"
    if w and tuple(im.size) != (w, h):
        im.scale(w, h)
    a = np.empty(im.size[0] * im.size[1] * 4, np.float32)
    im.pixels.foreach_get(a)
    return a.reshape(im.size[1], im.size[0], 4)[..., :3].copy()

def save(name, rgb):
    h, w = rgb.shape[:2]
    a = np.ones((h, w, 4), np.float32)
    a[..., :3] = np.clip(rgb, 0, 1)
    im = bpy.data.images.new(name, w, h, alpha=False)
    im.colorspace_settings.name = "Non-Color"
    im.pixels.foreach_set(a.ravel())
    im.filepath_raw = J(out, name + ".png")
    im.file_format = "PNG"
    im.save()
    print(f"[burn] {name}.png {w}x{h} mean={a[..., :3].mean(axis=(0, 1)).round(3)}")

def blur(x, r):
    for _ in range(2):
        for ax in (0, 1):
            c = np.cumsum(np.concatenate([x.take(range(-r - 1, 0), ax), x, x.take(range(r), ax)], ax), ax)
            x = (c.take(range(2 * r + 1, c.shape[ax]), ax) - c.take(range(0, c.shape[ax] - 2 * r - 1), ax)) / (2 * r + 1)
    return x

LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)

body = bpy.data.objects["SK_GZPro_Gigan_FW"]
tgt = body.copy()
tgt.data = body.data.copy()
bpy.context.scene.collection.objects.link(tgt)
tgt.modifiers.clear()
tgt.parent = None
tgt.matrix_world = body.matrix_world.copy()
bm = bmesh.new()
bm.from_mesh(tgt.data)
bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index != 0], context="FACES")
bm.to_mesh(tgt.data)
bm.free()
tmat = bpy.data.materials.new("bake_target")
tmat.use_nodes = True
node = tmat.node_tree.nodes.new("ShaderNodeTexImage")
tmat.node_tree.nodes.active = node
tgt.data.materials.clear()
tgt.data.materials.append(tmat)

before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=glb)
src = next(o for o in bpy.data.objects if o not in before and o.type == "MESH" and o.name.startswith("SK_GZPro"))
mw = src.matrix_world.copy()
src.parent = None
for m in list(src.modifiers):
    src.modifiers.remove(m)
src.data.transform(Matrix.Scale(100, 4) @ mw)
src.matrix_world = Matrix.Identity(4)
bm = bmesh.new()
bm.from_mesh(src.data)
bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index != 0], context="FACES")
bm.to_mesh(src.data)
bm.free()
smat = bpy.data.materials.new("bake_source")
smat.use_nodes = True
nt = smat.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
s_tex = nt.nodes.new("ShaderNodeTexImage")
s_emit = nt.nodes.new("ShaderNodeEmission")
s_out = nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(s_tex.outputs["Color"], s_emit.inputs["Color"])
nt.links.new(s_emit.outputs["Emission"], s_out.inputs["Surface"])
src.data.materials.clear()
src.data.materials.append(smat)

scn = bpy.context.scene
scn.render.engine = "CYCLES"
scn.cycles.device = "CPU"
scn.cycles.samples = 1
for o in bpy.data.objects:
    o.hide_render = o not in (src, tgt)
    o.select_set(False)
src.select_set(True)
tgt.select_set(True)
bpy.context.view_layer.objects.active = tgt

def bake(tex_name):
    img = bpy.data.images.load(J(burn_dir, BURN + tex_name + ".png"))
    img.colorspace_settings.name = "Non-Color"
    s_tex.image = img
    t = bpy.data.images.new("t_" + tex_name, W, H, alpha=True, float_buffer=True)
    t.colorspace_settings.name = "Non-Color"
    t.pixels.foreach_set(np.tile(np.array([1, 0, 1, 1], np.float32), W * H))
    node.image = t
    bpy.ops.object.bake(type="EMIT", use_selected_to_active=True, cage_extrusion=2.0, max_ray_distance=10.0,
                        margin=8, use_clear=False)
    a = np.empty(W * H * 4, np.float32)
    t.pixels.foreach_get(a)
    a = a.reshape(H, W, 4)[..., :3]
    miss = (a[..., 1] < 0.6 * np.minimum(a[..., 0], a[..., 2])) & (a[..., 2] > 0.25)
    print(f"[burn] baked {tex_name}: {100 * (1 - miss[:, :W // 2].mean()):.1f}% of the body half reached")
    return a, miss

c_burn, c_miss = bake("Body_C")
e_burn, e_miss = bake("Body_E")

ours_c = load(J(our_dir, "Godzilla2k_LP_body_C.png"), W, H)
luma = ours_c @ LUMA
detail = np.clip(luma / np.maximum(blur(luma, 8), 1e-3), 0.6, 1.6)[..., None]
burn_ref = load(J(burn_dir, BURN + "Body_C.png"))
tint = burn_ref.reshape(-1, 3).mean(0) / np.maximum(ours_c[:, :W // 2].reshape(-1, 3).mean(0), 1e-3)
fallback = ours_c * tint
body_c = np.where(c_miss[..., None], fallback, c_burn * detail)
body_c[:, W // 2:] = ours_c[:, W // 2:]
save(BURN + "Body_C", body_c)
body_e = np.where(e_miss[..., None], 0.0, e_burn)
body_e[:, W // 2:] = 0
save(BURN + "Body_E", body_e)
glow = np.clip((body_e @ LUMA) * 3, 0, 1)
small = lambda x, w, h: x.reshape(h, x.shape[0] // h, w, x.shape[1] // w, -1).mean((1, 3))
save(BURN + "Body_MSK", np.repeat(small(glow[..., None], 1024, 512), 3, -1))
save(BURN + "Body_N", load(J(our_dir, "Godzilla2k_LP_body_N.png"), W, H))
save(BURN + "Body_AORM", load(J(our_dir, "Godzilla2k_LP_body_AOR.png"), W, H))
save(BURN + "Body_H", np.full((1024, 2048, 3), 0.5))

sp = load(J(our_dir, "Godzilla2k_LP_spines_C.png"), 2048, 2048)
plates = blur(load(mask_png, 2048, 2048)[..., 0], 2)[..., None]
plate_col = load(J(burn_dir, BURN + "spines_C.png")).reshape(-1, 3).mean(0)
glow_col = load(J(burn_dir, BURN + "spines_E.png")).reshape(-1, 3).mean(0)
sp_l = (sp @ LUMA)[..., None]
save(BURN + "spines_C", sp * (1 - plates) + (sp_l / max(float(sp_l.mean()), 1e-3)) * plate_col * plates)
edge = np.clip((sp_l - 0.2) / 0.4, 0, 1)
save(BURN + "spines_E", plates * (0.45 + 0.55 * edge) * glow_col)
save(BURN + "spines_MSK", np.repeat(plates * 0.8, 3, -1))
save(BURN + "spines_N", load(J(our_dir, "Godzilla2k_LP_spines_N.png"), 2048, 2048))
save(BURN + "spines_AORM", load(J(our_dir, "Godzilla2k_LP_spines_AOR.png"), 2048, 2048))
