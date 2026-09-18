# Runs several settings JSON files one after another on the GPU (never in parallel) via run-avatar-test.ps1.
# Usage: powershell -File tools/avatar/run-test-queue.ps1 -Settings a.json,b.json [-Attention sage2]
param(
    [Parameter(Mandatory = $true)][string[]]$Settings,
    [string]$Attention = 'sage2'
)
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $root
$queueLog = Join-Path $root 'logs/avatar-test-queue.log'
# When launched with -File, a comma-joined list arrives as one string; split it here.
$Settings = @($Settings | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
foreach ($s in $Settings) {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') QUEUE START $s" | Add-Content -Path $queueLog -Encoding utf8
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'run-avatar-test.ps1') -Settings $s -Attention $Attention *> $null
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') QUEUE END   $s exit=$LASTEXITCODE" | Add-Content -Path $queueLog -Encoding utf8
}
"$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') QUEUE DONE" | Add-Content -Path $queueLog -Encoding utf8
