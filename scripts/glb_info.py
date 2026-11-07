import sys, bpy
from mathutils import Vector

glb = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
for o in bpy.data.objects:
    print(f"OBJ {o.name:24s} type={o.type:9s} parent={o.parent.name if o.parent else None} "
          f"loc={tuple(round(v, 3) for v in o.matrix_world.translation)} scale={tuple(round(v, 4) for v in o.matrix_world.to_scale())} "
          f"dims={tuple(round(v, 2) for v in o.dimensions)} pbone={o.parent_bone!r}")
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
for b in list(arm.data.bones)[:8]:
    print(f"BONE {b.name:18s} head={tuple(round(v, 4) for v in b.head_local)}")
for w in bpy.data.worlds:
    print("WORLD", w.name)
