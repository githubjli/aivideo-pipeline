$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$pythonExe = Join-Path $projectRoot 'ComfyUI_windows_portable\python_embeded\python.exe'
$mainFile = Join-Path $projectRoot 'ComfyUI_windows_portable\ComfyUI\main.py'
$logRoot = Join-Path $projectRoot 'logs'
New-Item -ItemType Directory -Force $logRoot | Out-Null
try {
    $existing = Invoke-RestMethod 'http://127.0.0.1:8188/system_stats' -TimeoutSec 2
    if ($existing.system) {
        Write-Host 'ComfyUI is already running: http://127.0.0.1:8188'
        exit 0
    }
} catch { }
$arguments = @('-s', ('"' + $mainFile + '"'), '--windows-standalone-build', '--listen', '127.0.0.1', '--port', '8188', '--disable-auto-launch', '--disable-api-nodes', '--output-directory', ('"' + (Join-Path $projectRoot 'outputs') + '"'))
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$outLog = Join-Path $logRoot "comfyui-$stamp.stdout.log"
$errLog = Join-Path $logRoot "comfyui-$stamp.stderr.log"
$serverProcess = Start-Process -FilePath $pythonExe -ArgumentList $arguments -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru
$serverProcess.Id | Set-Content (Join-Path $logRoot 'comfyui.pid')
Write-Host "Starting ComfyUI (PID $($serverProcess.Id)): http://127.0.0.1:8188"
Write-Host "Startup log: $errLog"
