# Promotes the test cards over the kept ones and removes the test cards.
#   .\promote.ps1            both Final Wars (test) and Chainsaw (test)
#   .\promote.ps1 wii        only Final Wars (test)
#   .\promote.ps1 wiisaw     only Chainsaw (test)
param([ValidateSet("all", "wii", "wiisaw")] [string]$Which = "all")
$skins = "$PSScriptRoot\Gigan Skin Launcher\skins\gigan"
$pairs = @{ wii = @("finalwars_wii_dev", "finalwars_wii"); wiisaw = @("finalwars_wii_saw_dev", "finalwars_wii_saw") }
foreach ($k in $(if ($Which -eq "all") { "wii", "wiisaw" } else { $Which })) {
    $test, $kept = $pairs[$k]
    if (-not (Test-Path "$skins\$test\zGiganFW_P.ucas")) { "no test build for $k"; continue }
    Copy-Item "$skins\$test\zGiganFW_P.*" "$skins\$kept\" -Force
    Remove-Item -LiteralPath "$skins\$test" -Recurse -Force
    "promoted $test -> $kept"
}
