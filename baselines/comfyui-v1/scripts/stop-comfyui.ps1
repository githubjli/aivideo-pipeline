$ErrorActionPreference = 'Stop'
$pidFile = Join-Path $PSScriptRoot 'logs\comfyui.pid'
if (-not (Test-Path -LiteralPath $pidFile)) { Write-Host 'No project server PID recorded.'; exit 0 }
$serverId = [int](Get-Content -LiteralPath $pidFile)
$serverProcess = Get-Process -Id $serverId -ErrorAction SilentlyContinue
if (-not $serverProcess) { Write-Host 'Server is already stopped.'; exit 0 }
$expectedExe = Join-Path $PSScriptRoot 'ComfyUI_windows_portable\python_embeded\python.exe'
if ($serverProcess.Path -ne $expectedExe) { throw 'PID belongs to another application; stop cancelled.' }
Stop-Process -Id $serverId
Write-Host 'Project ComfyUI server stopped.'
