param([ValidateSet("gigan", "godzilla2k", "heisei")] [string]$Target = "gigan", [string]$Name = "")
# Packs only the shipped skin assets (mesh + textures) from the cooked GZPro project into an
# IoStore mod: <Name>.pak / .utoc / .ucas. Stand-ins (skeleton, physics asset, material) are left out.
#   gigan       -> zGiganFW_P        (Final Wars Gigan over SK_GZPro_Gigan)
#   godzilla2k  -> zGodzilla2004_P   (2004 Godzilla over SK_GZPro_Godzilla2k)
#   heisei      -> zHeisei2004_P     (2004 Godzilla over the regular Godzilla, SK_GZPro_HeiseiGodzilla)
if (-not $Name) { $Name = @{ gigan = "zGiganFW_P"; godzilla2k = "zGodzilla2004_P"; heisei = "zHeisei2004_P" }[$Target] }
$ErrorActionPreference = "Stop"
$U = "C:\Users\halst\GiganModUE\GZPro"
$Cooked = "$U\Saved\Cooked\Windows"
$Out = "$U\Saved\Mod"
$Pak = "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealPak.exe"
New-Item -ItemType Directory -Force $Out | Out-Null
Remove-Item "$Out\*" -Force -ErrorAction SilentlyContinue

if ($Target -eq "godzilla2k") {
    $home_ = "Characters/GZPro_Monsters/Godzilla2K"
    $ship = @("$home_/SK_GZPro_Godzilla2k") +
            @("body_C", "body_N", "body_AOR", "body_H", "body_MSK", "body_ATK_MSK",
              "spines_C", "spines_N", "spines_AOR", "spines_E", "spines_MSK", "spines_ATK_MSK" |
              ForEach-Object { "$home_/Textures/Godzilla2k_LP_$_" })
    $readmeName, $readmeText = "Godzilla2004.txt", "2004 (Final Wars) Godzilla skin for Godzilla DAMM Remastered. Model by JJJ and MMDCharizard."
} elseif ($Target -eq "heisei") {
    $home_ = "Characters/GZPro_Monsters/HeiseiGodzilla"
    # the skeleton ships too: a copy of the game's whose upper-body bones take their positions from the mesh
    $ship = @("$home_/SK_GZPro_HeiseiGodzilla", "Characters/GZ1_Monsters/HeiseiGodzilla/SKEL_GZ1_HeiseiGodzilla_Skeleton") +
            @("Body", "Spines" | ForEach-Object { $p = $_; "C", "N", "AORM", "H", "MSK", "ATK_MSK" |
              ForEach-Object { "$home_/Textures/HeiseiGodzilla_$($p)_LP_$_" } })
    $readmeName, $readmeText = "Heisei2004.txt", "2004 (Final Wars) Godzilla skin over the regular Godzilla, for Godzilla DAMM Remastered. Model by JJJ and MMDCharizard."
} else {
    $ship = @("Characters/GZPro_Monsters/Gigan/SK_GZPro_Gigan") +
            @("C", "N", "AOR", "E", "H", "MSK", "ATKMSK" | ForEach-Object { "Characters/GZPro_Monsters/Gigan/Textures/Gigan_LP_base_$_" })
    $readmeName, $readmeText = "GiganFW.txt", "Final Wars Gigan skin (Wii model) for Godzilla DAMM Remastered."
}
$missing = $ship | Where-Object { -not (Test-Path (Join-Path "$Cooked\GZPro\Content" ($_.Replace("/", "\") + ".uasset"))) }
if ($missing) { throw "not cooked: $($missing -join ', ')" }

$lines = foreach ($a in $ship) {
    foreach ($ext in ".uasset", ".ubulk") {  # .uexp is picked up with its .uasset
        $src = Join-Path "$Cooked\GZPro\Content" ($a.Replace("/", "\") + $ext)
        if (Test-Path $src) { "`"$src`" `"../../../GZPro/Content/$a$ext`" -compress" }
    }
}
$resp = "$Out\files.txt"
[IO.File]::WriteAllLines($resp, $lines)
$cmds = "$Out\commands.txt"
[IO.File]::WriteAllText($cmds, "-Output=`"$Out\$Name.utoc`" -ContainerName=$Name -ResponseFile=`"$resp`"")

# IoStore containers are mounted through a .pak of the same name; give it one small loose file.
$readme = "$Out\$readmeName"
$readmeText | Set-Content $readme
[IO.File]::WriteAllText("$Out\pak.txt", "`"$readme`" `"../../../GZPro/Content/Mods/$readmeName`"")

& $Pak "$U\GZPro.uproject" "$U\GZPro.uproject" -CreateGlobalContainer="$Out\global_unused.utoc" `
    -PackageStoreManifest="$Cooked\GZPro\Metadata\packagestore.manifest" -CookedDirectory="$Cooked" `
    -Commands="$cmds" -ScriptObjects="$Cooked\GZPro\Metadata\scriptobjects.bin" `
    -patchpaddingalign=2048 -compressionformats=Oodle -compresslevel=4 -compressmethod=Kraken `
    -cryptokeys="$Cooked\GZPro\Metadata\Crypto.json" -compressionMinBytesSaved=1024 -compressionMinPercentSaved=5 `
    -WriteBackMetadataToAssetRegistry=Disabled -platform=Windows -unattended | Select-String -Pattern "Error|error|Warning: .*(package|Package)|$Name" | ForEach-Object { "  $_" }
& $Pak "$Out\$Name.pak" -create="$Out\pak.txt" -platform=Windows -unattended | Select-String -Pattern "Error|Created" | ForEach-Object { "  $_" }

Remove-Item "$Out\global_unused.*" -ErrorAction SilentlyContinue
Get-ChildItem "$Out\$Name.*" | ForEach-Object { "{0,-20} {1,10:N0} bytes" -f $_.Name, $_.Length }
"files packed: $($lines.Count)"
