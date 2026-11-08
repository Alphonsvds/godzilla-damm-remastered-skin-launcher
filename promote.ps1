param([ValidateSet("all", "wii", "wiisaw")] [string]$Which = "all")
$skins = "$PSScriptRoot\Godzilla DAMMR Skin Launcher\skins\gigan"
$pairs = @{ wii = @("finalwars_wii_dev", "finalwars_wii"); wiisaw = @("finalwars_wii_saw_dev", "finalwars_wii_saw") }
foreach ($k in $(if ($Which -eq "all") { "wii", "wiisaw" } else { $Which })) {
    $test, $kept = $pairs[$k]
    if (-not (Test-Path "$skins\$test\zGiganFW_P.ucas")) { "no test build for $k"; continue }
    Copy-Item "$skins\$test\zGiganFW_P.*" "$skins\$kept\" -Force
    Remove-Item -LiteralPath "$skins\$test" -Recurse -Force
    "promoted $test -> $kept"
}
