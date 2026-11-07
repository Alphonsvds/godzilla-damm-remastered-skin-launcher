param([string]$Name = "zGiganFW_P")
# Packs only the shipped Final Wars assets (mesh + textures) from the cooked GZPro project into an
# IoStore mod: <Name>.pak / .utoc / .ucas. Stand-ins (skeleton, physics asset, material) are left out.
$ErrorActionPreference = "Stop"
$U = "C:\Users\halst\GiganModUE\GZPro"
$Cooked = "$U\Saved\Cooked\Windows"
$Out = "$U\Saved\Mod"
$Pak = "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealPak.exe"
New-Item -ItemType Directory -Force $Out | Out-Null
Remove-Item "$Out\*" -Force -ErrorAction SilentlyContinue

$ship = @("Characters/GZPro_Monsters/Gigan/SK_GZPro_Gigan") +
        @("C", "N", "AOR", "E", "H", "MSK", "ATKMSK" | ForEach-Object { "Characters/GZPro_Monsters/Gigan/Textures/Gigan_LP_base_$_" })

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
$readme = "$Out\GiganFW.txt"
"Final Wars Gigan skin (Wii model) for Godzilla DAMM Remastered." | Set-Content $readme
[IO.File]::WriteAllText("$Out\pak.txt", "`"$readme`" `"../../../GZPro/Content/Mods/GiganFW.txt`"")

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
