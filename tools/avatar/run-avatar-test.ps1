# Runs one Wan2GP settings JSON headlessly (wgp.py --process), records elapsed time, GPU memory samples and the log.
# Usage: powershell -File tools/avatar/run-avatar-test.ps1 -Settings productions/math/tests/avatar/infinitetalk-mom-test.json
param(
    [Parameter(Mandatory = $true)][string]$Settings,
    [string]$OutputDir = 'productions/math/tests/avatar/out',
    [int]$SampleSeconds = 3,
    [string]$Attention = 'sdpa'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $root
$settingsPath = (Resolve-Path -LiteralPath $Settings).Path
$name = [IO.Path]::GetFileNameWithoutExtension($settingsPath)
$stamp = (Get-Date -Format 'yyyyMMdd-HHmmss') + "-$Attention"
$outDir = Join-Path $root $OutputDir
New-Item -ItemType Directory -Force -Path $outDir, (Join-Path $root 'logs') | Out-Null
$log = Join-Path $root "logs/avatar-test-$name-$stamp.log"
$gpuCsv = Join-Path $root "logs/avatar-test-$name-$stamp.gpu.csv"

$env:GIT_PYTHON_REFRESH = 'quiet'
$env:HF_HOME = Join-Path $root 'tools/avatar/cache/huggingface'
$env:HF_HUB_DISABLE_XET = '1'
$env:GRADIO_ANALYTICS_ENABLED = 'False'
$env:PYTHONIOENCODING = 'utf-8'
$wgpRoot = Join-Path $root 'tools/avatar/Wan2GP'
$py = Join-Path $wgpRoot '.venv/Scripts/python.exe'

# GPU sampler: whole-card memory used, every N seconds (includes other processes; not a per-task peak).
$sampler = Start-Job -ScriptBlock {
    param($csv, $every)
    'time,used_mib,util_pct' | Set-Content -Path $csv -Encoding utf8
    while ($true) {
        $q = nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits
        "$(Get-Date -Format 'HH:mm:ss'),$($q -replace '\s','')" | Add-Content -Path $csv -Encoding utf8
        Start-Sleep -Seconds $every
    }
} -ArgumentList $gpuCsv, $SampleSeconds

$before = @(Get-ChildItem -LiteralPath $outDir -File -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
$sw = [Diagnostics.Stopwatch]::StartNew()
"START $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') settings=$settingsPath" | Tee-Object -FilePath $log -Append | Out-Host
try {
    # Do not pipe the native process with 2>&1: under PowerShell 5.1 with ErrorActionPreference=Stop, the first
    # tqdm line on stderr becomes a terminating NativeCommandError and the pipeline kills python mid-generation.
    $stdoutLog = Join-Path $root "logs/avatar-test-$name-$stamp.stdout.log"
    $stderrLog = Join-Path $root "logs/avatar-test-$name-$stamp.stderr.log"
    $proc = Start-Process -FilePath $py -ArgumentList '-X','utf8','-X','faulthandler','-u','wgp.py','--process',"`"$settingsPath`"",'--output-dir',"`"$outDir`"",'--attention',$Attention,'--profile','4','--verbose','1' `
        -WorkingDirectory $wgpRoot -NoNewWindow -PassThru -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog
    $proc.WaitForExit()
    $proc.Refresh()
    $code = $proc.ExitCode
    if ($null -eq $code) { $code = if (Select-String -Path $stdoutLog -Pattern 'Queue completed: (\d+)/\1 tasks' -Quiet) { 0 } else { 1 } }
    Get-Content $stdoutLog | Add-Content -Path $log -Encoding utf8
    "--- stderr (progress bars) ---" | Add-Content -Path $log -Encoding utf8
    Get-Content $stderrLog | Add-Content -Path $log -Encoding utf8
} finally {
    $sw.Stop()
    Stop-Job $sampler -ErrorAction SilentlyContinue | Out-Null
    Remove-Job $sampler -Force -ErrorAction SilentlyContinue | Out-Null
}
$after = @(Get-ChildItem -LiteralPath $outDir -File -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
$new = $after | Where-Object { $before -notcontains $_ }
$peak = (Import-Csv $gpuCsv | Measure-Object -Property used_mib -Maximum).Maximum
$summary = [ordered]@{
    settings = $settingsPath; attention = $Attention; exit_code = $code; elapsed_seconds = [math]::Round($sw.Elapsed.TotalSeconds, 1)
    peak_gpu_used_mib_sampled = $peak; new_files = @($new); log = $log; gpu_samples = $gpuCsv
}
$summaryPath = Join-Path $root "logs/avatar-test-$name-$stamp.json"
$summary | ConvertTo-Json -Depth 4 | Set-Content -Path $summaryPath -Encoding utf8
"END exit=$code elapsed=$($summary.elapsed_seconds)s peak_gpu=$peak MiB new_files=$($new.Count) summary=$summaryPath" | Tee-Object -FilePath $log -Append | Out-Host
exit $code
