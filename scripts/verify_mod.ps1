param([string]$ModDir, [ValidateSet("gigan", "godzilla2k", "heisei")] [string]$Target = "gigan", [string]$ModName = "")
# Reads the packaged mod back with gzexport and compares it with the game's own mesh (bones, slots, size).
$ErrorActionPreference = "Continue"  # gzexport logs to stderr; don't treat that as failure
$P = "C:\Users\halst\OneDrive\Desktop\Projects\gigan-fw-mod"
$X = "C:\Users\halst\GiganModTools\gzexport\gzexport.exe"
$Game = "C:\Program Files (x86)\Steam\steamapps\common\Godzilla Destroy All Monsters Melee Remastered\GZPro\Content\Paks"
if ($Target -eq "godzilla2k") {
    if (-not $ModName) { $ModName = "zGodzilla2004_P" }
    $Mesh = "GZPro/Content/Characters/GZPro_Monsters/Godzilla2K/SK_GZPro_Godzilla2k.SK_GZPro_Godzilla2k"
    $GameBones = "$P\work\godzilla\game\bones_SK_GZPro_Godzilla2k.json"
    $Filter, $RootName = "SK_GZPro_Godzilla2k|Godzilla2k_LP|SKEL_GZ1|PHYS_GZ1|MI_GZPro", "Godzilla2KRoot"
} elseif ($Target -eq "heisei") {
    if (-not $ModName) { $ModName = "zHeisei2004_P" }
    $Mesh = "GZPro/Content/Characters/GZPro_Monsters/HeiseiGodzilla/SK_GZPro_HeiseiGodzilla.SK_GZPro_HeiseiGodzilla"
    $GameBones = "$P\work\godzilla\game\bones_SK_GZPro_HeiseiGodzilla.json"
    $Filter, $RootName = "SK_GZPro_HeiseiGodzilla|HeiseiGodzilla_.*_LP|SKEL_GZ1|PHYS_GZ1|MI_HeiseiGodzilla", "Godzilla90Root"
} else {
    if (-not $ModName) { $ModName = "zGiganFW_P" }
    $Mesh = "GZPro/Content/Characters/GZPro_Monsters/Gigan/SK_GZPro_Gigan.SK_GZPro_Gigan"
    $GameBones = "$P\work\game\bones_SK_GZPro.json"
    $Filter, $RootName = "SK_GZPro_Gigan|Gigan_LP_base|SKEL_GZ1|PHYS_GZ1|MI_GZPro", "GiganRoot"
}
$work = Join-Path $P "work\verify"
New-Item -ItemType Directory -Force $work | Out-Null

# mod only (+ game's global container so script imports resolve)
$solo = Join-Path $work "solo"
Remove-Item -Recurse -Force $solo -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $solo | Out-Null
Copy-Item "$ModDir\$ModName.*" $solo
Copy-Item "$Game\global.utoc", "$Game\global.ucas" $solo

$env:GZ_PAKS = $solo
& $X list $Filter 2>$null | ForEach-Object { "  in mod: $_" }
& $X meshinfo $Mesh 2>&1 | Where-Object { $_ -notmatch "mounted" } | ForEach-Object { "  mod  $_" }
& $X bones $Mesh "$work\bones_mod.json" 2>&1 | Where-Object { $_ -notmatch "mounted" }
Remove-Item Env:GZ_PAKS
& $X meshinfo $Mesh 2>&1 | Where-Object { $_ -match "LOD0|slot|$RootName|Bip01 " } | ForEach-Object { "  game $_" }

$a = (Get-Content $GameBones -Raw | ConvertFrom-Json).bones
$b = (Get-Content "$work\bones_mod.json" -Raw | ConvertFrom-Json).bones
if ($a.Count -ne $b.Count) { "BONE COUNT DIFFERS: game $($a.Count) vs mod $($b.Count)" }
$bad = 0
for ($i = 0; $i -lt [Math]::Min($a.Count, $b.Count); $i++) {
    $dot = 0; for ($k = 0; $k -lt 4; $k++) { $dot += $a[$i].q[$k] * $b[$i].q[$k] }
    $ang = 2 * [Math]::Acos([Math]::Min(1, [Math]::Abs($dot))) * 180 / [Math]::PI
    $dt = 0; for ($k = 0; $k -lt 3; $k++) { $dt = [Math]::Max($dt, [Math]::Abs($a[$i].t[$k] - $b[$i].t[$k])) }
    $ds = [Math]::Abs($a[$i].s[0] - $b[$i].s[0])
    $flag = if ($a[$i].name -ne $b[$i].name -or $ang -gt 1 -or $dt -gt 0.5 -or $ds -gt 0.01) { "  <--"; $bad++ } else { "" }
    if ($flag -or $i -lt 3) { "{0,-18} {1,-18} rot {2,6:N2} deg  move {3,6:N2}  scale {4} vs {5}{6}" -f $a[$i].name, $b[$i].name, $ang, $dt, $a[$i].s[0], $b[$i].s[0], $flag }
}
"bones checked: $([Math]::Min($a.Count, $b.Count)), mismatches: $bad"
