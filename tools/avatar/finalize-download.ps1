# Waits for any running download-models.py instances, then runs one full verification pass over the whole
# manifest (fills gaps, re-checks sizes and SHA256) and links the LongCat distill LoRA where Wan2GP looks for it.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $root
$log = Join-Path $root 'logs/avatar-finalize.log'
function Log($m) { $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m"; $line | Tee-Object -FilePath $log -Append | Out-Host }

Log 'finalize started; waiting for running download-models.py instances'
while ($true) {
    $running = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*download-models.py*--download*' }
    if (-not $running) { break }
    Start-Sleep -Seconds 60
}
Log 'no downloader running; starting full verification pass'
$py = Join-Path $root 'ComfyUI_windows_portable/python_embeded/python.exe'
& $py -X utf8 -u tools/avatar/download-models.py --download 2>&1 | Tee-Object -FilePath (Join-Path $root 'logs/avatar-model-download.log') -Append | Out-Host
$code = $LASTEXITCODE
Log "verification pass exit code $code"

$src = Join-Path $root 'tools/avatar/Wan2GP/ckpts/longcat_avatar_v1_5/dmd_lora.safetensors'
$dstDir = Join-Path $root 'tools/avatar/Wan2GP/loras/longcat_avatar_v1_5'
$dst = Join-Path $dstDir 'dmd_lora.safetensors'
if (Test-Path -LiteralPath $src) {
    New-Item -ItemType Directory -Force -Path $dstDir | Out-Null
    if (-not (Test-Path -LiteralPath $dst)) {
        try { New-Item -ItemType HardLink -Path $dst -Target $src | Out-Null; Log "hard-linked LoRA to $dst" }
        catch { Copy-Item -LiteralPath $src -Destination $dst; Log "copied LoRA to $dst (hardlink failed: $($_.Exception.Message))" }
    } else { Log 'LoRA already present in loras folder' }
} else { Log 'LoRA source missing in ckpts; not linked' }

& $py -X utf8 tools/avatar/status.py 2>&1 | Tee-Object -FilePath $log -Append | Out-Host
Log 'finalize done'
exit $code
