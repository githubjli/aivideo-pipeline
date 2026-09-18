# Polls the pinned manifest until every file InfiniteTalk needs (plus Wan2GP shared assets and the 4-step LoRA)
# is present at its expected size. Prints progress once a minute; exits 0 when ready, 2 on the given time limit.
param([int]$MaxMinutes = 9, [string]$Model = 'infinitetalk')
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$manifest = Get-Content (Join-Path $root 'tools/avatar/model-manifest.json') -Raw | ConvertFrom-Json
$shared = @('pose/', 'scribble/', 'flow/', 'depth/', 'wav2vec/', 'roformer/', 'pyannote/', 'det_align/', 'mask/')
$perModel = @{
    infinitetalk        = @('wan2.1_image2video_480p_14B_quanto', 'wan2.1_infinitetalk_single', 'Wan2.1_VAE', 'umt5-xxl/', 'xlm-roberta-large/', 'chinese-wav2vec2-base/', 'loras_accelerators/')
    hunyuan_avatar      = @('hunyuan_video_avatar_720', 'hunyuan_video_720_quanto_int8_map', 'hunyuan_video_custom_VAE', 'hunyuan_video_VAE', 'llava-llama-3-8b/', 'clip_vit_large_patch14/', 'whisper-tiny/')
    longcat_avatar_v1_5 = @('longcat_avatar_v1_5', 'longcat_avatar_v1_5/', 'whisper-large-v3/', 'umt5-xxl/', 'Wan2.1_VAE_bf16')
}
if (-not $perModel.ContainsKey($Model)) { throw "unknown model $Model" }
$needPrefixes = $shared + $perModel[$Model]
$need = $manifest | Where-Object { $f = $_.file; ($needPrefixes | Where-Object { $f.StartsWith($_) }).Count -gt 0 }
$deadline = (Get-Date).AddMinutes($MaxMinutes)
$lastParts = -1
while ($true) {
    $missing = @($need | Where-Object {
        $rel = if ($_.target) { $_.target } else { 'ckpts/' + $_.file }
        $p = Join-Path $root ('tools/avatar/Wan2GP/' + $rel)
        -not ((Test-Path -LiteralPath $p) -and (Get-Item -LiteralPath $p).Length -eq $_.size)
    })
    $parts = (Get-ChildItem -Recurse -File (Join-Path $root 'tools/avatar/cache/parts') -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    $rate = if ($lastParts -ge 0) { [math]::Round(($parts - $lastParts) / 1MB / 60, 1) } else { $null }
    $lastParts = $parts
    $missingGiB = [math]::Round((($missing | Measure-Object size -Sum).Sum) / 1GB, 2)
    "$(Get-Date -Format 'HH:mm:ss') missing=$($missing.Count) files ($missingGiB GiB) parts=$([math]::Round($parts/1GB,2)) GiB rate=$rate MB/s"
    if ($missing.Count -eq 0) { 'READY'; exit 0 }
    if ((Get-Date) -gt $deadline) { 'TIMEOUT: ' + (($missing | Select-Object -First 6 | ForEach-Object { $_.file }) -join ', '); exit 2 }
    Start-Sleep -Seconds 60
}
