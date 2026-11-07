"""Unreal Editor (5.8) Python: build the Final Wars Gigan mod content inside the GZPro project.

Ships (chunk 1):  SK_GZPro_Gigan + the seven Gigan_LP_base_* textures, at the game's own paths.
Stand-ins only (chunk 0, discarded): SKEL_GZ1_Gigan_Skeleton, PHYS_GZ1_Gigan_PhysicsAsset, MI_GZPro_Gigan_Body.
At runtime the mesh's references resolve to the game's real skeleton, physics asset and material.

Run: UnrealEditor-Cmd.exe GZPro.uproject -run=pythonscript -script="ue_import.py" (paths via env GZ_EXPORT)
"""
import os
import unreal

EXPORT = os.environ.get("GZ_EXPORT", r"C:\Users\halst\OneDrive\Desktop\Projects\gigan-fw-mod\export")
GIGAN = "/Game/Characters/GZPro_Monsters/Gigan"
GZ1 = "/Game/Characters/GZ1_Monsters/Gigan"
SKEL = f"{GZ1}/SKEL_GZ1_Gigan_Skeleton"
PHYS = f"{GZ1}/PHYS_GZ1_Gigan_PhysicsAsset"
MI = f"{GIGAN}/Materials/MI_GZPro_Gigan_Body"
MESH = f"{GIGAN}/SK_GZPro_Gigan"

eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
TCS = unreal.TextureCompressionSettings
TG = unreal.TextureGroup
TEXTURES = {  # name: (compression, sRGB, LOD group) -- matches the game's cooked textures
    "C": (TCS.TC_DEFAULT, True, TG.TEXTUREGROUP_CHARACTER),
    "N": (TCS.TC_NORMALMAP, False, TG.TEXTUREGROUP_CHARACTER_NORMAL_MAP),
    "AOR": (TCS.TC_DEFAULT, False, TG.TEXTUREGROUP_CHARACTER),
    "E": (TCS.TC_DEFAULT, True, TG.TEXTUREGROUP_CHARACTER),
    "H": (TCS.TC_GRAYSCALE, False, TG.TEXTUREGROUP_CHARACTER),
    "MSK": (TCS.TC_MASKS, False, TG.TEXTUREGROUP_CHARACTER),
    "ATKMSK": (TCS.TC_MASKS, False, TG.TEXTUREGROUP_CHARACTER),
}


def log(msg):
    unreal.log_warning(f"[gzmod] {msg}")


def run_import(filename, dest_path, dest_name, options=None):
    task = unreal.AssetImportTask()
    task.filename = filename
    task.destination_path = dest_path
    task.destination_name = dest_name
    task.automated = True
    task.replace_existing = True
    task.save = True
    if options is not None:
        task.options = options
    tools.import_asset_tasks([task])
    return list(task.imported_object_paths)


for path in (MESH, f"{MESH}_Skeleton", f"{MESH}_PhysicsAsset", SKEL, PHYS, MI):
    if eal.does_asset_exist(path):
        eal.delete_asset(path)

# --- mesh ------------------------------------------------------------------------------------
ui = unreal.FbxImportUI()
ui.import_mesh = True
ui.import_as_skeletal = True
ui.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
ui.import_materials = False
ui.import_textures = False
ui.import_animations = False
ui.create_physics_asset = True
sk = ui.skeletal_mesh_import_data


def setp(obj, name, value):
    try:
        obj.set_editor_property(name, value)
    except Exception as e:  # option names shift between engine versions; report and carry on
        log(f"option {type(obj).__name__}.{name} not set: {e}")


log("skeletal import options: " + ", ".join(sorted(n for n in dir(sk) if not n.startswith("_"))))
setp(sk, "import_morph_targets", False)
setp(sk, "convert_scene", True)
setp(sk, "force_front_x_axis", False)
setp(sk, "convert_scene_unit", False)
setp(sk, "import_uniform_scale", 1.0)
setp(sk, "use_t0_as_ref_pose", False)
setp(sk, "preserve_smoothing_groups", False)  # normals come from the FBX; smoothing groups split every corner
setp(sk, "import_meshes_in_bone_hierarchy", True)
setp(sk, "normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
setp(sk, "vertex_color_import_option", unreal.VertexColorImportOption.OVERRIDE)
setp(sk, "vertex_override_color", unreal.Color(255, 255, 255, 255))
log("import mesh: " + str(run_import(os.path.join(EXPORT, "SK_GZPro_Gigan_FW.fbx"), GIGAN, "SK_GZPro_Gigan", ui)))

for src, dst in ((f"{MESH}_Skeleton", SKEL), (f"{MESH}_PhysicsAsset", PHYS)):
    ok = eal.rename_asset(src, dst)
    log(f"rename {src} -> {dst}: {ok}")
    if not ok:
        raise RuntimeError("rename failed")

# --- stand-in material at the game's material path ---------------------------------------------
mic = tools.create_asset("MI_GZPro_Gigan_Body", f"{GIGAN}/Materials", unreal.MaterialInstanceConstant,
                         unreal.MaterialInstanceConstantFactoryNew())
unreal.MaterialEditingLibrary.set_material_instance_parent(mic, unreal.load_asset("/Engine/EngineMaterials/DefaultMaterial"))
eal.save_loaded_asset(mic)

mesh = unreal.load_asset(MESH)
new_mats = []
for m in mesh.get_editor_property("materials"):
    slot = m.get_editor_property("material_slot_name")
    nm = unreal.SkeletalMaterial(material_interface=mic, material_slot_name=slot)
    for prop in ("imported_material_slot_name", "uv_channel_data"):
        try:
            nm.set_editor_property(prop, m.get_editor_property(prop))
        except Exception:
            pass
    new_mats.append(nm)
mesh.set_editor_property("materials", new_mats)
mesh.set_editor_property("physics_asset", unreal.load_asset(PHYS))
eal.save_loaded_asset(mesh)

# --- textures --------------------------------------------------------------------------------
tex_assets = []
for key, (comp, srgb, group) in TEXTURES.items():
    name = f"Gigan_LP_base_{key}"
    run_import(os.path.join(EXPORT, "textures", name + ".png"), f"{GIGAN}/Textures", name)
    t = unreal.load_asset(f"{GIGAN}/Textures/{name}")
    t.set_editor_property("compression_settings", comp)
    t.set_editor_property("srgb", srgb)
    t.set_editor_property("lod_group", group)
    eal.save_loaded_asset(t)
    tex_assets.append(t)

# --- chunk labels: 1 = ship, 0 = stand-ins -------------------------------------------------------
def make_label(name, chunk, priority, assets):
    path = f"/Game/ModLabels/{name}"
    if eal.does_asset_exist(path):
        eal.delete_asset(path)
    factory = unreal.DataAssetFactory()
    factory.set_editor_property("data_asset_class", unreal.PrimaryAssetLabel)
    label = tools.create_asset(name, "/Game/ModLabels", unreal.PrimaryAssetLabel, factory)
    rules = unreal.PrimaryAssetRules()
    rules.set_editor_property("priority", priority)
    rules.set_editor_property("chunk_id", chunk)
    rules.set_editor_property("apply_recursively", True)
    rules.set_editor_property("cook_rule", unreal.PrimaryAssetCookRule.ALWAYS_COOK)
    label.set_editor_property("rules", rules)
    label.set_editor_property("label_assets_in_my_directory", False)
    label.set_editor_property("explicit_assets", assets)
    eal.save_loaded_asset(label)


mesh = unreal.load_asset(MESH)
make_label("Label_Ship_GiganFW", 1, 10, [mesh] + tex_assets)
make_label("Label_StandIns", 0, 20, [unreal.load_asset(p) for p in (SKEL, PHYS, MI)])

skel = mesh.get_editor_property("skeleton")
log(f"mesh skeleton = {skel.get_path_name()}")
log(f"mesh physics  = {mesh.get_editor_property('physics_asset').get_path_name()}")
for m in mesh.get_editor_property("materials"):
    mi = m.get_editor_property("material_interface")
    log(f"mesh slot     = {m.get_editor_property('material_slot_name')} -> {mi.get_path_name() if mi else None}")
rs = mesh.get_editor_property("skeleton").get_reference_pose() if hasattr(skel, "get_reference_pose") else None
log(f"skeleton bones = {skel.get_editor_property('bone_tree').__len__() if hasattr(skel, 'bone_tree') else 'n/a'}")
log(f"mesh bounds   = {mesh.get_bounds()}")
log("done")
