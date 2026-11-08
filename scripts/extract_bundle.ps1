param([string]$Exe, [string]$Name, [string]$OutDir)
$sig = [byte[]](0x8b,0x12,0x02,0xb9,0x6a,0x61,0x20,0x38,0x72,0x7b,0x93,0x02,0x14,0xd7,0xa0,0x32,0x13,0xf5,0xb9,0xe6,0xef,0xae,0x33,0x18,0xee,0x3b,0x2d,0xce,0x24,0xb3,0x6a,0xae)
$bytes = [IO.File]::ReadAllBytes($Exe)
$pos = -1
for ($i = 8; $i -le $bytes.Length - 32; $i++) {
    if ($bytes[$i] -ne $sig[0]) { continue }
    $ok = $true
    for ($j = 1; $j -lt 32; $j++) { if ($bytes[$i + $j] -ne $sig[$j]) { $ok = $false; break } }
    if ($ok) { $pos = $i; break }
}
if ($pos -lt 0) { throw "bundle signature not found" }
$headerOffset = [BitConverter]::ToInt64($bytes, $pos - 8)
$ms = New-Object IO.MemoryStream(, $bytes)
$br = New-Object IO.BinaryReader($ms)
$ms.Position = $headerOffset
$major = $br.ReadUInt32(); $minor = $br.ReadUInt32(); $count = $br.ReadInt32(); [void]$br.ReadString()
if ($major -ge 2) { [void]$br.ReadInt64(); [void]$br.ReadInt64(); [void]$br.ReadInt64(); [void]$br.ReadInt64(); [void]$br.ReadUInt64() }
for ($k = 0; $k -lt $count; $k++) {
    $off = $br.ReadInt64(); $size = $br.ReadInt64()
    $csize = if ($major -ge 6) { $br.ReadInt64() } else { 0 }
    [void]$br.ReadByte(); $path = $br.ReadString()
    if ([IO.Path]::GetFileName($path) -ne $Name) { continue }
    $out = Join-Path $OutDir $Name
    if ($csize -gt 0) {
        $src = New-Object IO.MemoryStream($bytes, [int]$off, [int]$csize)
        $z = New-Object IO.Compression.DeflateStream($src, [IO.Compression.CompressionMode]::Decompress)
        $fs = [IO.File]::Create($out); $z.CopyTo($fs); $fs.Close()
    } else {
        $buf = New-Object byte[] $size; [Array]::Copy($bytes, $off, $buf, 0, $size); [IO.File]::WriteAllBytes($out, $buf)
    }
    "extracted $path ($size bytes) -> $out"
    return
}
throw "$Name not found in bundle (v$major.$minor, $count files)"
