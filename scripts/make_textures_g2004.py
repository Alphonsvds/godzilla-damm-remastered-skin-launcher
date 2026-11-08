"""Textures for the 2004 Godzilla, under the names of the replaced game Godzilla's own textures, so the game's
materials are kept and only their textures change:
  g2k     Godzilla 2000          Godzilla2k_LP_{body,spines}_*        (MI_GZPro_Godzilla2k_Body / _Spines)
  heisei  regular Godzilla       HeiseiGodzilla_{Body,Spines}_LP_*    (MI_HeiseiGodzilla_Body / _Spines)

Body slot: one 4096x2048 sheet, the MMD body texture on the left half and the eye texture on the right half
(fit_g2004.py moved the UVs to match). Spines slot: the MMD spines/teeth/claws texture as it is.
The MMD model has colour maps only, so the other maps are made to match what the game's own maps average out to:
matte skin, no metal, translucent glowing dorsal plates (plate mask from fit_g2004.py).

Usage: blender -b --factory-startup --python make_textures_g2004.py -- <mmd_texture_dir> <plates_mask.png> <out_dir> [g2k|heisei]
"""
import sys, os, bpy
import numpy as np

args = sys.argv[sys.argv.index("--") + 1:]
src, mask_png, out = args[:3]
target = args[3] if len(args) > 3 else "g2k"
os.makedirs(out, exist_ok=True)
if target == "heisei":
    BODY, SPINES, AOR = "HeiseiGodzilla_Body_LP_", "HeiseiGodzilla_Spines_LP_", "AORM"
else:
    BODY, SPINES, AOR = "Godzilla2k_LP_body_", "Godzilla2k_LP_spines_", "AOR"


def load(path, w, h=None):
    h = h or w
    im = bpy.data.images.load(path)
    im.colorspace_settings.name = "Non-Color"
    if tuple(im.size) != (w, h):
        im.scale(w, h)
    px = np.empty(w * h * 4, dtype=np.float32)
    im.pixels.foreach_get(px)
    return px.reshape(h, w, 4)[..., :3].copy()


def save(name, rgb):
    h, w = rgb.shape[:2]
    a = np.ones((h, w, 4), dtype=np.float32)
    a[..., :3] = np.clip(rgb, 0, 1)
    im = bpy.data.images.new(name, w, h, alpha=False)
    im.colorspace_settings.name = "Non-Color"
    im.pixels.foreach_set(a.ravel())
    im.filepath_raw = os.path.join(out, name + ".png")
    im.file_format = "PNG"
    im.save()
    print(f"[tex] {name}.png {w}x{h} mean={a[..., :3].mean(axis=(0, 1)).round(3)}")


def blur(x, r):
    """Box blur (twice, close to a gaussian), wrapping at the edges."""
    for _ in range(2):
        for ax in (0, 1):
            c = np.cumsum(np.concatenate([x.take(range(-r - 1, 0), ax), x, x.take(range(r), ax)], ax), ax)
            x = (c.take(range(2 * r + 1, c.shape[ax]), ax) - c.take(range(0, c.shape[ax] - 2 * r - 1), ax)) / (2 * r + 1)
    return x


def detail_normal(luma, strength):
    """Fine bumps from the painted skin detail (high-pass of brightness), DirectX green like UE expects."""
    hp = luma - blur(luma, 6)
    gy, gx = np.gradient(hp)
    n = np.stack([-gx * strength, gy * strength, np.ones_like(hp)], -1)  # rows run bottom-up in Blender
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


LUMA = np.array([0.2126, 0.7152, 0.0722])
F = os.path.join

# ---- body + eye sheet -----------------------------------------------------------------------------------------
body = load(F(src, "FinalGoji_TexturesNW-.png"), 2048)
eye = load(F(src, "Eye-.png"), 2048)
save(BODY + "C", np.concatenate([body, eye], 1))
flat = np.zeros((2048, 2048, 3)) + [0.5, 0.5, 1.0]
save(BODY + "N", np.concatenate([detail_normal(body @ LUMA, 30.0), flat], 1))
# game's own body maps: roughness ~0.75, metal ~0.03-0.05. AO from the painted crevices (the game's Heisei map
# averages ~0.7), roughest in the crevices. The eye half is a little glossier so it catches light.
cav = np.clip((body @ LUMA - blur(body @ LUMA, 12)) * 4.0, -1, 1)
ao_body = np.clip(0.85 + 0.6 * cav, 0.45, 1.0)
aor = np.zeros((2048, 4096, 3)) + [1.0, 0.8, 0.0]
aor[:, :2048, 0] = ao_body
aor[:, :2048, 1] = np.clip(0.82 - 0.1 * cav, 0.65, 0.95)
aor[:, 2048:, 1] = 0.45
save(BODY + AOR, aor)
save(BODY + "H", np.full((1024, 2048, 3), 0.5))  # flat: the material's height centre is 0.5
save(BODY + "MSK", np.zeros((1024, 2048, 3)))     # no subsurface on the skin
save(BODY + "ATK_MSK", np.zeros((256, 512, 3)))  # body doesn't glow

# ---- spines, teeth, claws, tongue -----------------------------------------------------------------------------
sp = load(F(src, "FinalSpinesNW.png"), 2048)
save(SPINES + "C", sp)
save(SPINES + "N", detail_normal(sp @ LUMA, 12.0))
plates = load(mask_png, 2048)[..., 0]
plates_soft = blur(plates, 2)
save(SPINES + AOR, np.stack([np.ones_like(plates), 0.75 - 0.15 * plates_soft, np.zeros_like(plates)], -1))
save(SPINES + "MSK", np.repeat((plates_soft * 0.8)[..., None], 3, -1))  # plates let light through
edge = np.clip((sp @ LUMA - 0.2) / 0.4, 0, 1)
if target == "heisei":
    save(SPINES + "H", np.full((512, 512, 3), 0.5))
else:
    # glow: like the game's map, brightest along the plates' pale edges, in the game's pink glow colour
    save(SPINES + "E", (plates_soft * (0.35 + 0.65 * edge))[..., None] * [0.9, 0.6, 0.8])
small = load(mask_png, 512)[..., 0]
sp512 = load(F(src, "FinalSpinesNW.png"), 512)
save(SPINES + "ATK_MSK", np.repeat((small * (0.35 + 0.65 * np.clip((sp512 @ LUMA - 0.2) / 0.4, 0, 1)))[..., None], 3, -1))
