# Rebuilds a skin mod end to end and drops it into its launcher slot.
#   .\build_all.ps1            Wii Final Wars  -> skins\gigan\finalwars_wii_dev  (test slot; finalwars_wii is the kept one)
#   .\build_all.ps1 -Skin ps3  PS3 Final Wars  -> archive\skins\finalwars_ps3 (not in the launcher)
#   .\build_all.ps1 -Skin wiisaw  Wii Final Wars with the PS3 chainsaw hands -> skins\gigan\finalwars_wii_saw_dev
#   .\build_all.ps1 -Skin g2004   2004 (Final Wars) Godzilla over Godzilla 2000 -> skins\godzilla\godzilla_2004
#   .\build_all.ps1 -Skin g2004h  2004 (Final Wars) Godzilla over the regular (Heisei) Godzilla -> skins\heisei\godzilla_2004
# Model steps differ per skin; Unreal import -> cook -> pack -> verify -> launcher slot are shared.
param([ValidateSet("wii", "ps3", "wiisaw", "g2004", "g2004h")] [string]$Skin = "wii")
$ErrorActionPreference = "Continue"  # tools write warnings to stderr; failures are caught via exit codes
$P = $PSScriptRoot
$Blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$UE = "C:\Program Files\Epic Games\UE_5.8\Engine"
$Bones = "$P\work\game\bones_SKEL_GZ1.json"
$Glb = "$P\work\game\export\GZPro\Content\Characters\GZPro_Monsters\Gigan\SK_GZPro_Gigan.glb"
$Proj = "C:\Users\halst\GiganModUE\GZPro\GZPro.uproject"
# the PS3 build is archived (not shown in the launcher), so it is written outside skins\
# wii and wiisaw build into test cards; promote.ps1 copies a test card over the kept one once it looks right
$Slot = @{ wii = "gigan\finalwars_wii_dev"; ps3 = "..\..\archive\skins\finalwars_ps3"; wiisaw = "gigan\finalwars_wii_saw_dev"
           g2004 = "godzilla\godzilla_2004"; g2004h = "heisei\godzilla_2004" }[$Skin]
# per-monster target: which game mesh is replaced, where the export goes, the mod's file name
$Target = @{ g2004 = "godzilla2k"; g2004h = "heisei" }[$Skin]; if (-not $Target) { $Target = "gigan" }
$Export = @{ g2004 = "$P\export\godzilla2004"; g2004h = "$P\export\heisei2004" }[$Skin]; if (-not $Export) { $Export = "$P\export" }
$ModName = @{ godzilla2k = "zGodzilla2004_P"; heisei = "zHeisei2004_P"; gigan = "zGiganFW_P" }[$Target]

function Step($name, [scriptblock]$body) {
    Write-Host "== $name" -ForegroundColor Cyan
    & $body
    if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw "$name failed (exit $LASTEXITCODE)" }
}
function Blend($in, $script, [string[]]$rest) {
    & $Blender -b $in --python-exit-code 1 --python "$P\scripts\$script" -- @rest 2>&1 |
        Where-Object { $_ -match '^\[|Error|Traceback' } | ForEach-Object { "   $_" }
}
function Textures($script, $src) {
    & $Blender -b --factory-startup --python-exit-code 1 --python "$P\scripts\$script" -- $src "$P\export\textures" 2>&1 |
        Where-Object { $_ -match '^\[|Error' } | ForEach-Object { "   $_" }
}

if ($Skin -like "g2004*") {
    $W = "$P\work\godzilla"
    if ($Skin -eq "g2004h") {  # regular Godzilla: same Bip01 rig as Godzilla 2000, its own slot and texture names
        $GB = "$W\game\bones_SKEL_GZ1_HeiseiGodzilla.json"
        $GGlb = "$W\game\export\GZPro\Content\Characters\GZPro_Monsters\HeiseiGodzilla\SK_GZPro_HeiseiGodzilla.glb"
        # own-upper: upper-body bones sit at the model's own joints (the mod ships a skeleton that uses them)
        $T, $MeshName, $Slots, $TexTarget, $Who = "h2004", "SK_GZPro_HeiseiGodzilla", @("body_mat", "spines_mat", "own-upper"), "heisei", "regular Godzilla"
        $TorsoXfer = ""  # bones sit at the model's own joints, so it keeps its own weights (no game-mesh transfer)
        $env:GZ_SKEL_JSON = "$W\game\SKEL_GZ1_HeiseiGodzilla.json"
    } else {
        $GB = "$W\game\bones_SKEL_GZ1_Godzilla2k.json"
        $GGlb = "$W\game\export\GZPro\Content\Characters\GZPro_Monsters\Godzilla2k\SK_GZPro_Godzilla2k.glb"
        $T, $MeshName, $Slots, $TexTarget, $Who = "g2004", "SK_GZPro_Godzilla2k", @(), "g2k", "Godzilla 2000"
        $TorsoXfer = "Bip01,Bip01_Pelvis,Bip01_Spine,Bip01_Spine1,Bip01_Neck,Bip01_L_Thigh,Bip01_R_Thigh"
        Remove-Item Env:GZ_SKEL_JSON -ErrorAction SilentlyContinue
    }
    $Src = "$P\source\godzilla_2004\Godzilla 2004 (JJJ and MMDCharizard)"
    $Hips = "Bip01_Pelvis,Bip01_L_Thigh,Bip01_R_Thigh,Bip01_L_Calf,Bip01_R_Calf,Bip01_Tail,Bip01_Tail1"
    New-Item -ItemType Directory -Force $Export | Out-Null
    if (-not (Test-Path "$W\g2004.blend")) {
        Step "import MMD model" { & $Blender -b --factory-startup --python-exit-code 1 --python "$P\scripts\import_pmx.py" -- "$Src\Godzilla 2004 1.2.pmx" "$W\g2004.blend" G2004_Armature 2>&1 | Where-Object { $_ -match '^\[|Error' } }
    }
    Step "fit 2004 model to $Who skeleton" { Blend "$W\g2004.blend" "fit_g2004.py" (@($GB, "$W\$($T)_fitted.blend", "$Export\plates_mask.png") + $Slots) }
    if ($TorsoXfer) {
        Step "torso + hip weights from game mesh" { Blend "$W\$($T)_fitted.blend" "transfer_torso_weights.py" @($GGlb, "$W\$($T)_v2.blend", $TorsoXfer, "no-new-tail") }
        Step "smooth hip seam"                { Blend "$W\$($T)_v2.blend" "smooth_hips.py" @("$W\$($T)_v3.blend", "30", "0.6", $Hips) }
    } else {
        Copy-Item "$W\$($T)_fitted.blend" "$W\$($T)_v3.blend" -Force
    }
    Step "smooth overlapping shells"      { Blend "$W\$($T)_v3.blend" "smooth_shells.py" @("$W\$($T)_final.blend", "2.5", "3", "Bip01_Pelvis,Bip01_L_Thigh,Bip01_R_Thigh,Bip01_Tail") }
    Step "pin dorsal plates to the skin"  { Blend "$W\$($T)_final.blend" "rigid_plates.py" @("$W\$($T)_final.blend") }
    Step "soles onto the ground"          { Blend "$W\$($T)_final.blend" "lift_soles.py" @("$W\$($T)_final.blend") }
    Step "export FBX"                     { Blend "$W\$($T)_final.blend" "export_fbx.py" @("$Export\$MeshName.fbx", "X", "-Y", $MeshName) }
    Step "textures" {
        & $Blender -b --factory-startup --python-exit-code 1 --python "$P\scripts\make_textures_g2004.py" -- $Src "$Export\plates_mask.png" "$Export\textures" $TexTarget 2>&1 |
            Where-Object { $_ -match '^\[|Error' } | ForEach-Object { "   $_" }
    }
} elseif ($Skin -ne "ps3") {
    Step "fit Wii model to game skeleton" { Blend "$P\work\gigan_fw_wii.blend" "fit_wii.py" @($Bones, "$P\work\gigan_fw_fitted.blend") }
    Step "torso weights from game mesh"   { Blend "$P\work\gigan_fw_fitted.blend" "transfer_torso_weights.py" @($Glb, "$P\work\gigan_fw_fitted_v2.blend") }
    Step "belly ridge onto torso"         { Blend "$P\work\gigan_fw_fitted_v2.blend" "ridge_to_torso.py" @("$P\work\gigan_fw_fitted_v2.blend") }
    Step "double-sided wings"             { Blend "$P\work\gigan_fw_fitted_v2.blend" "double_side.py" @("$P\work\gigan_fw_final.blend") }
    Step "soften jaw"                     { Blend "$P\work\gigan_fw_final.blend" "soften_jaw.py" @("$P\work\gigan_fw_final.blend", "0.6") }
    # lift_feet.py is not used for the Wii model: raising the soles stretched the ankles
    $final = "$P\work\gigan_fw_final.blend"
    if ($Skin -eq "wiisaw") {
        Step "fit PS3 model (for its chainsaws)" { Blend "$P\work\gigan_ps3.blend" "fit_ps3.py" @($Bones, "$P\work\gigan_ps3_fitted.blend") }
        Step "swap blades for chainsaws"      { Blend $final "kitbash_chainsaws.py" @("$P\work\gigan_ps3_fitted.blend", "$P\work\gigan_fw_saw.blend") }
        $final = "$P\work\gigan_fw_saw.blend"
    }
    Step "export FBX"                     { Blend $final "export_fbx.py" @("$P\export\SK_GZPro_Gigan_FW.fbx") }
    if (-not (Test-Path "$P\source\wii_gigan_fw_x4\Gigan_FW_512_C.png")) { Step "AI upscale Wii maps" { & "$P\scripts\upscale_textures.ps1" } }
    Step "textures"                       { Textures "make_textures.py" "$P\source\wii_gigan_fw" }
} else {
    Step "fit PS3 model to game skeleton" { Blend "$P\work\gigan_ps3.blend" "fit_ps3.py" @($Bones, "$P\work\gigan_ps3_fitted.blend") }
    Step "soften jaw"                     { Blend "$P\work\gigan_ps3_fitted.blend" "soften_jaw.py" @("$P\work\gigan_ps3_fitted.blend", "0.6") }
    Step "export FBX"                     { Blend "$P\work\gigan_ps3_fitted.blend" "export_fbx.py" @("$P\export\SK_GZPro_Gigan_FW.fbx") }
    Step "textures"                       { Textures "make_textures_ps3.py" "$P\source\ps3_gigan" }
}

Step "Unreal import" {
    # start from clean generated content so renames onto the game's asset paths can't collide
    $content = Join-Path (Split-Path $Proj) "Content"
    foreach ($d in "Characters", "ModLabels") {
        if (Test-Path "$content\$d") { Remove-Item -LiteralPath "$content\$d" -Recurse -Force }
    }
    $env:GZ_EXPORT = $Export
    $env:GZ_TARGET = $Target
    & "$UE\Binaries\Win64\UnrealEditor-Cmd.exe" $Proj -run=pythonscript -script="$P\scripts\ue_import.py" -unattended -nop4 -nosplash -stdout -FullStdOutLogOutput 2>&1 |
        Where-Object { $_ -match '\[gzmod\] (rename|skeleton:|mesh skeleton|mesh slot|done)|LogPython: Error|Unrecognized|LogSkeletalMesh: Error' -and $_ -notmatch 'LogInit' } | ForEach-Object { "   $_" }
}
Step "cook" {
    & "$UE\Build\BatchFiles\RunUAT.bat" BuildCookRun "-project=$Proj" -noP4 -platform=Win64 -clientconfig=Shipping -cook -stage -pak -iostore -skipbuild -nocompileeditor -unattended -utf8output -unversionedcookedcontent *> "C:\Users\halst\GiganModUE\package.log"
    Select-String -Path "C:\Users\halst\GiganModUE\package.log" -Pattern "BUILD SUCCESSFUL|BUILD FAILED" | ForEach-Object { "   $($_.Line)" }
}
Step "pack mod container" { & "$P\scripts\build_mod_container.ps1" -Target $Target | Where-Object { $_ -match "bytes|files packed|Error" } }
Step "verify against game" { & "$P\scripts\verify_mod.ps1" -ModDir "C:\Users\halst\GiganModUE\GZPro\Saved\Mod" -Target $Target 2>$null | Where-Object { $_ -match "LOD0|mismatches|<--|BONE COUNT" } }
Step "launcher slot" {
    $dir = "$P\Gigan Skin Launcher\skins\$Slot"
    New-Item -ItemType Directory -Force $dir | Out-Null
    if (-not (Test-Path "$dir\skin.json")) {
        $name = @{ wii = "Final Wars (test)"; ps3 = "Final Wars (PS3) - chainsaws"; wiisaw = "Chainsaw (test)"; g2004h = "2004" }[$Skin]
        "{ `"name`": `"$name`", `"description`": `"`" }" | Set-Content -Encoding utf8 "$dir\skin.json"
        $prev = @{ wii = "$P\source\card_art\finalwars.png"; ps3 = "$P\work\ps3_preview_threequarter.png"; wiisaw = "$P\source\card_art\finalwars_chainsaw.png" }[$Skin]
        if (Test-Path $prev) { Copy-Item $prev "$dir\preview.png" }
    }
    Copy-Item "C:\Users\halst\GiganModUE\GZPro\Saved\Mod\$ModName.*" $dir -Force
    "   copied to launcher slot '$Slot'; pick it and Apply & Play to load the new build"
}
