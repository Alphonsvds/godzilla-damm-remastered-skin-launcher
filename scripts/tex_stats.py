import sys, bpy
import numpy as np

for path in sys.argv[sys.argv.index("--") + 1:]:
    im = bpy.data.images.load(path)
    im.colorspace_settings.name = "Non-Color"
    w, h = im.size
    px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, im.channels)
    stats = []
    for c, name in enumerate("RGBA"[:im.channels]):
        ch = px[..., c]
        stats.append(f"{name}: min={ch.min():.2f} mean={ch.mean():.2f} max={ch.max():.2f} >0.5:{(ch > 0.5).mean() * 100:.0f}%")
    print(f"[tex] {path.split(chr(92))[-1]:28s} {w}x{h}  " + "  ".join(stats))
