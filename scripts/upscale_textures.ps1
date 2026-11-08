param([string]$Source = "$PSScriptRoot\..\source\wii_gigan_fw", [string[]]$Names = @("Gigan_FW_512_C", "Gigan_FW_512_B", "Gigan_FW_512_S"))
$R = "C:\Users\halst\GiganModTools\realesrgan"
$Source = (Resolve-Path $Source).Path
$out = "${Source}_x4"
New-Item -ItemType Directory -Force $out | Out-Null
foreach ($n in $Names) {
    & "$R\realesrgan-ncnn-vulkan.exe" -i "$Source\$n.png" -o "$out\$n.png" -n realesrgan-x4plus -m "$R\models" 2>&1 | Out-Null
    "   upscaled $n -> $(Test-Path "$out\$n.png")"
}
