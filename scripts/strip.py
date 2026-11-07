"""Stitch PNGs side by side. Usage: blender -b --python strip.py -- out.png in1.png in2.png ..."""
import sys, bpy
import numpy as np

args = sys.argv[sys.argv.index("--") + 1:]
out, ins = args[0], args[1:]
imgs = [bpy.data.images.load(p) for p in ins]
w, h = imgs[0].size
buf = np.zeros((h, w * len(imgs), 4), dtype=np.float32)
for i, im in enumerate(imgs):
    buf[:, i * w:(i + 1) * w] = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
img = bpy.data.images.new("strip", w * len(imgs), h, alpha=True)
img.pixels = buf.ravel()
img.filepath_raw = out
img.file_format = "PNG"
img.save()
print("[strip] saved", out)
