import sys, os, bpy
import numpy as np

src, out = sys.argv[sys.argv.index("--") + 1:]
os.makedirs(out, exist_ok=True)

TINT = np.array([0.9, 1.0, 0.931925])
SATURATION = 1.25
VISOR_BOX = (250, 345, 25, 100)

UPSCALED = src.rstrip("\\/") + "_x4"

def load(name, size):
    up = os.path.join(UPSCALED, name)
    im = bpy.data.images.load(up if os.path.exists(up) else os.path.join(src, name))
    im.colorspace_settings.name = "Non-Color"
    if tuple(im.size) != (size, size):
        im.scale(size, size)
    return np.array(im.pixels[:], dtype=np.float32).reshape(size, size, 4)[..., :4].copy()

def save(name, rgb, size):
    a = np.ones((size, size, 4), dtype=np.float32)
    a[..., :3] = np.clip(rgb, 0, 1)
    im = bpy.data.images.new(name, size, size, alpha=False)
    im.colorspace_settings.name = "Non-Color"
    im.pixels = a.ravel()
    im.filepath_raw = os.path.join(out, name + ".png")
    im.file_format = "PNG"
    im.save()
    print(f"[tex] {name}.png {size}x{size} mean={a[..., :3].mean(axis=(0, 1)).round(3)}")

def box_mask(size):
    x0, x1, y0, y1 = (v * size / 512 for v in VISOR_BOX)
    m = np.zeros((size, size), dtype=np.float32)
    m[int(size - y1):int(size - y0), int(x0):int(x1)] = 1
    return m

c = load("Gigan_FW_512_C.png", 2048)[..., :3]
lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
luma = (lin * [0.2126, 0.7152, 0.0722]).sum(-1, keepdims=True)
lin = luma + (lin - luma) / SATURATION
lin = lin / TINT
c = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.clip(lin, 0, None) ** (1 / 2.4) - 0.055)
save("Gigan_LP_base_C", c, 2048)

n = load("Gigan_FW_512_B.png", 2048)[..., :3]
n[..., 1] = 1.0 - n[..., 1]
v = n * 2 - 1
NORMAL_STRENGTH = 0.5
v[..., :2] *= NORMAL_STRENGTH
v[..., 2] = np.sqrt(np.clip(1 - v[..., 0] ** 2 - v[..., 1] ** 2, 0, 1))
n = v * 0.5 + 0.5
save("Gigan_LP_base_N", n, 2048)

s = load("Gigan_FW_512_S.png", 1024)[..., 0]
metal = np.clip((s - 0.53) / 0.07, 0, 1)
rough = 1.0 - 0.5 * metal
ao = 0.55 + 0.45 * metal
aor = np.stack([ao, rough, metal], -1)
save("Gigan_LP_base_AOR", aor, 1024)

m = load("Gigan_FW_256_M.png", 1024)
glow = np.maximum(m[..., 0], m[..., 3])
c1k = load("Gigan_FW_512_C.png", 1024)[..., :3]
red = np.clip((c1k[..., 0] - np.maximum(c1k[..., 1], c1k[..., 2]) - 0.15) / 0.2, 0, 1)
visor = glow * box_mask(1024) * red * 0.35
save("Gigan_LP_base_E", np.stack([visor, visor * 0.4, visor * 0.4], -1), 1024)
m256 = load("Gigan_FW_256_M.png", 256)
save("Gigan_LP_base_ATKMSK", np.repeat(np.maximum(m256[..., 0], m256[..., 3])[..., None], 3, -1), 256)

save("Gigan_LP_base_H", np.full((1024, 1024, 3), 0.5), 1024)
save("Gigan_LP_base_MSK", np.zeros((512, 512, 3)), 512)
