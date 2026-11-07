"""Replacement Gigan_LP_base_* textures from the PS3 (Godzilla 2014) Final Wars Gigan maps.
Usage: blender -b --python make_textures_ps3.py -- <ps3_source_dir> <out_dir>
"""
import sys, os, bpy
import numpy as np

src, out = sys.argv[sys.argv.index("--") + 1:]
os.makedirs(out, exist_ok=True)
TINT = np.array([0.9, 1.0, 0.931925])  # MI_GZPro_Gigan_Body tint / saturation, undone below
SATURATION = 1.25


def load(name, size):
    im = bpy.data.images.load(os.path.join(src, name))
    im.colorspace_settings.name = "Non-Color"
    if tuple(im.size) != (size, size):
        im.scale(size, size)
    return np.array(im.pixels[:], dtype=np.float32).reshape(size, size, 4).copy()


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


# C: the PS3 colour map is very dark (its shader brightened it); lift it, then undo the game's tint/saturation.
c = load("pl15_color.png", 2048)[..., :3]
c = 1.2 * np.power(c, 0.7)
lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
luma = (lin * [0.2126, 0.7152, 0.0722]).sum(-1, keepdims=True)
lin = (luma + (lin - luma) / SATURATION) / TINT
c = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.clip(lin, 0, None) ** (1 / 2.4) - 0.055)
save("Gigan_LP_base_C", c, 2048)

# N: PS3 normal map, 4096 -> 2048.
save("Gigan_LP_base_N", load("pl15_normal.png", 2048)[..., :3], 2048)

# AOR: AO from the PS3 ambient map; metal = bright, unsaturated areas (blades, chainsaws, armour edges).
amb = load("pl15_ambient.png", 1024)[..., 0]
c1k = load("pl15_color.png", 1024)[..., :3]
bright = c1k.max(-1)
sat = (c1k.max(-1) - c1k.min(-1)) / np.maximum(bright, 1e-4)
metal = np.clip((bright - 0.22) / 0.12, 0, 1) * np.clip((0.35 - sat) / 0.2, 0, 1)
rough = 0.8 - 0.4 * metal
save("Gigan_LP_base_AOR", np.stack([0.35 + 0.65 * amb, rough, metal], -1), 1024)

# no glow yet (red visor and red wings share colours); flat height; no subsurface; no attack-glow mask
save("Gigan_LP_base_E", np.zeros((1024, 1024, 3)), 1024)
save("Gigan_LP_base_ATKMSK", np.zeros((256, 256, 3)), 256)
save("Gigan_LP_base_H", np.full((1024, 1024, 3), 0.5), 1024)
save("Gigan_LP_base_MSK", np.zeros((512, 512, 3)), 512)
