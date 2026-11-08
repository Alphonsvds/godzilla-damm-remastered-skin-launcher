import os
import unreal

EXPORT = os.environ.get("GZ_EXPORT", r"C:\Users\halst\OneDrive\Desktop\Projects\gigan-fw-mod\export")
TARGET = os.environ.get("GZ_TARGET", "gigan")

eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
TCS = unreal.TextureCompressionSettings
TG = unreal.TextureGroup
COLOR = (TCS.TC_DEFAULT, True, TG.TEXTUREGROUP_CHARACTER)
NORMAL = (TCS.TC_NORMALMAP, False, TG.TEXTUREGROUP_CHARACTER_NORMAL_MAP)
LINEAR = (TCS.TC_DEFAULT, False, TG.TEXTUREGROUP_CHARACTER)
GRAY = (TCS.TC_GRAYSCALE, False, TG.TEXTUREGROUP_CHARACTER)
MASKS = (TCS.TC_MASKS, False, TG.TEXTUREGROUP_CHARACTER)

if TARGET == "godzilla2k":
    HOME = "/Game/Characters/GZPro_Monsters/Godzilla2K"
    GZ1 = "/Game/Characters/GZ1_Monsters/Godzilla2K"
    SKEL = f"{GZ1}/SKEL_GZ1_Godzilla2k_Skeleton"
    PHYS = f"{GZ1}/PHYS_GZ1_Godzilla2k_PhysicsAsset"
    MESH_NAME = "SK_GZPro_Godzilla2k"
    FBX = "SK_GZPro_Godzilla2k.fbx"
    LABEL = "Label_Ship_Godzilla2004"
    SLOT_MI = {"Godzilla2k_Mesh_body_mtl": "MI_GZPro_Godzilla2k_Body",
               "Godzilla2k_Mesh_spines_mtl": "MI_GZPro_Godzilla2k_Spines"}
    TEXTURES = {f"Godzilla2k_LP_{p}_{k}": kind for p in ("body", "spines")
                for k, kind in (("C", COLOR), ("N", NORMAL), ("AOR", LINEAR), ("MSK", GRAY), ("ATK_MSK", GRAY))}
    TEXTURES.update({"Godzilla2k_LP_body_H": GRAY, "Godzilla2k_LP_spines_E": COLOR})
    BURN_DIR = f"{HOME}/Skins/2kBurningGodzilla/Textures"
    EXTRA_TEXTURES = {f"2kBurningGodzilla_LP_{k}": (BURN_DIR, kind) for k, kind in (
        ("Body_C", COLOR), ("Body_N", NORMAL), ("Body_AORM", LINEAR), ("Body_E", COLOR), ("Body_H", GRAY),
        ("Body_MSK", GRAY), ("spines_C", COLOR), ("spines_N", NORMAL), ("spines_AORM", LINEAR), ("spines_E", COLOR),
        ("spines_MSK", GRAY))}
elif TARGET == "heisei":
    HOME = "/Game/Characters/GZPro_Monsters/HeiseiGodzilla"
    GZ1 = "/Game/Characters/GZ1_Monsters/HeiseiGodzilla"
    SKEL = f"{GZ1}/SKEL_GZ1_HeiseiGodzilla_Skeleton"
    PHYS = f"{GZ1}/PHYS_GZ1_HeiseiGodzilla"
    MESH_NAME = "SK_GZPro_HeiseiGodzilla"
    FBX = "SK_GZPro_HeiseiGodzilla.fbx"
    LABEL = "Label_Ship_Heisei2004"
    SLOT_MI = {"body_mat": "MI_HeiseiGodzilla_Body", "spines_mat": "MI_HeiseiGodzilla_Spines"}
    TEXTURES = {f"HeiseiGodzilla_{p}_LP_{k}": kind for p in ("Body", "Spines")
                for k, kind in (("C", COLOR), ("N", NORMAL), ("AORM", LINEAR), ("H", GRAY), ("MSK", GRAY), ("ATK_MSK", GRAY))}
else:
    HOME = "/Game/Characters/GZPro_Monsters/Gigan"
    GZ1 = "/Game/Characters/GZ1_Monsters/Gigan"
    SKEL = f"{GZ1}/SKEL_GZ1_Gigan_Skeleton"
    PHYS = f"{GZ1}/PHYS_GZ1_Gigan_PhysicsAsset"
    MESH_NAME = "SK_GZPro_Gigan"
    FBX = "SK_GZPro_Gigan_FW.fbx"
    LABEL = "Label_Ship_GiganFW"
    SLOT_MI = {None: "MI_GZPro_Gigan_Body"}
    TEXTURES = {"Gigan_LP_base_C": COLOR, "Gigan_LP_base_N": NORMAL, "Gigan_LP_base_AOR": LINEAR,
                "Gigan_LP_base_E": COLOR, "Gigan_LP_base_H": GRAY, "Gigan_LP_base_MSK": MASKS,
                "Gigan_LP_base_ATKMSK": MASKS}
MESH = f"{HOME}/{MESH_NAME}"
MIS = [f"{HOME}/Materials/{n}" for n in dict.fromkeys(SLOT_MI.values())]

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

for path in (MESH, f"{MESH}_Skeleton", f"{MESH}_PhysicsAsset", SKEL, PHYS, *MIS):
    if eal.does_asset_exist(path):
        eal.delete_asset(path)

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
    except Exception as e:
        log(f"option {type(obj).__name__}.{name} not set: {e}")

log("skeletal import options: " + ", ".join(sorted(n for n in dir(sk) if not n.startswith("_"))))
setp(sk, "import_morph_targets", False)
setp(sk, "convert_scene", True)
setp(sk, "force_front_x_axis", False)
setp(sk, "convert_scene_unit", False)
setp(sk, "import_uniform_scale", 1.0)
setp(sk, "use_t0_as_ref_pose", False)
setp(sk, "preserve_smoothing_groups", False)
setp(sk, "import_meshes_in_bone_hierarchy", True)
setp(sk, "normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
setp(sk, "vertex_color_import_option", unreal.VertexColorImportOption.OVERRIDE)
setp(sk, "vertex_override_color", unreal.Color(255, 255, 255, 255))
log("import mesh: " + str(run_import(os.path.join(EXPORT, FBX), HOME, MESH_NAME, ui)))

for src, dst in ((f"{MESH}_Skeleton", SKEL), (f"{MESH}_PhysicsAsset", PHYS)):
    ok = eal.rename_asset(src, dst)
    log(f"rename {src} -> {dst}: {ok}")
    if not ok:
        raise RuntimeError("rename failed")

SHIP_SKEL_JSON = os.environ.get("GZ_SKEL_JSON") if TARGET in ("heisei", "godzilla2k") else None
SHIP_SKEL = bool(SHIP_SKEL_JSON)
OWN_BONES = {"Bip01_Spine", "Bip01_Spine1", "Bip01_Neck", "Bip01_Neck1", "Bip01_Head", "Bip01_Jaw"} | {
    f"Bip01_{s}_{b}" for s in "LR" for b in ("Clavicle", "UpperArm", "Forearm", "Hand", "Finger0", "Finger01", "Finger1", "Finger11",
                                            "Thigh", "Calf")}
if SHIP_SKEL:
    import json
    dump = json.load(open(SHIP_SKEL_JSON))
    gskel = next(e for e in dump if e["Type"] == "Skeleton")
    bone_names = [b["Name"] for b in gskel["ReferenceSkeleton"]["FinalRefBoneInfo"]]
    skel = unreal.load_asset(SKEL)
    sk_mesh = unreal.load_asset(MESH)
    run = lambda cmd: unreal.SystemLibrary.execute_console_command(None, cmd)
    modes = ",".join(f"(TranslationRetargetingMode={'Skeleton' if n in OWN_BONES else 'Animation'})" for n in bone_names)
    run(f"setnopec {skel.get_path_name()} BoneTree ({modes})")
    vguid = gskel["Properties"].get("VirtualBoneGuid", "0" * 32).replace("-", "")
    run(f"setnopec {skel.get_path_name()} VirtualBoneGuid {vguid}")
    log(f"skeleton: {len(OWN_BONES)} of {len(bone_names)} bones take their position from the mesh; virtual bone guid {vguid}")
    n_sock = 0
    for e in dump:
        if e["Type"] != "SkeletalMeshSocket":
            continue
        p = e["Properties"]
        s = unreal.new_object(unreal.SkeletalMeshSocket, outer=sk_mesh, name=f"GZSocket_{n_sock}")
        loc, rot, scl = p.get("RelativeLocation", {}), p.get("RelativeRotation", {}), p.get("RelativeScale", {})
        for prop, val in (("SocketName", p["SocketName"]), ("BoneName", p["BoneName"]),
                          ("RelativeLocation", f"(X={loc.get('X', 0)},Y={loc.get('Y', 0)},Z={loc.get('Z', 0)})"),
                          ("RelativeRotation", f"(Pitch={rot.get('Pitch', 0)},Yaw={rot.get('Yaw', 0)},Roll={rot.get('Roll', 0)})"),
                          ("RelativeScale", f"(X={scl.get('X', 1)},Y={scl.get('Y', 1)},Z={scl.get('Z', 1)})")):
            run(f"setnopec {s.get_path_name()} {prop} {val}")
        if str(s.get_editor_property("socket_name")) != p["SocketName"]:
            raise RuntimeError(f"socket {p['SocketName']} not set (got {s.get_editor_property('socket_name')})")
        sk_mesh.add_socket(s, True)
        n_sock += 1
    log(f"skeleton: added {n_sock} sockets")
    eal.save_loaded_asset(skel, False)
    eal.save_loaded_asset(sk_mesh, False)

stand_in = {}
for name in dict.fromkeys(SLOT_MI.values()):
    mic = tools.create_asset(name, f"{HOME}/Materials", unreal.MaterialInstanceConstant,
                             unreal.MaterialInstanceConstantFactoryNew())
    unreal.MaterialEditingLibrary.set_material_instance_parent(mic, unreal.load_asset("/Engine/EngineMaterials/DefaultMaterial"))
    eal.save_loaded_asset(mic)
    stand_in[name] = mic

mesh = unreal.load_asset(MESH)
new_mats = []
for m in mesh.get_editor_property("materials"):
    slot = m.get_editor_property("material_slot_name")
    key = str(slot) if str(slot) in SLOT_MI else None
    if key not in SLOT_MI:
        raise RuntimeError(f"unexpected material slot {slot}; expected {list(SLOT_MI)}")
    nm = unreal.SkeletalMaterial(material_interface=stand_in[SLOT_MI[key]], material_slot_name=slot)
    for prop in ("imported_material_slot_name", "uv_channel_data"):
        try:
            nm.set_editor_property(prop, m.get_editor_property(prop))
        except Exception:
            pass
    new_mats.append(nm)
mesh.set_editor_property("materials", new_mats)
mesh.set_editor_property("physics_asset", unreal.load_asset(PHYS))
eal.save_loaded_asset(mesh)

tex_assets = []
all_textures = {name: (f"{HOME}/Textures", kind) for name, kind in TEXTURES.items()}
all_textures.update(globals().get("EXTRA_TEXTURES", {}))
for name, (folder, (comp, srgb, group)) in all_textures.items():
    if not os.path.exists(os.path.join(EXPORT, "textures", name + ".png")):
        raise RuntimeError(f"missing texture {name}.png")
    run_import(os.path.join(EXPORT, "textures", name + ".png"), folder, name)
    t = unreal.load_asset(f"{folder}/{name}")
    t.set_editor_property("compression_settings", comp)
    t.set_editor_property("srgb", srgb)
    t.set_editor_property("lod_group", group)
    eal.save_loaded_asset(t)
    tex_assets.append(t)

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
shipped_skel = [unreal.load_asset(SKEL)] if SHIP_SKEL else []
make_label(LABEL, 1, 10, [mesh] + shipped_skel + tex_assets)
make_label("Label_StandIns", 0, 20, [unreal.load_asset(p) for p in ((PHYS, *MIS) if SHIP_SKEL else (SKEL, PHYS, *MIS))])

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
