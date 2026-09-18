$ErrorActionPreference = 'Stop'
$avatarDownloadScript = Join-Path $PSScriptRoot 'tools/avatar/download-models.py'
$avatarExisting = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*download-models.py*--download*' }
if ($avatarExisting) { Write-Host 'Avatar model download is already running. See logs/avatar-model-download.log.'; exit 0 }
$avatarPython = Join-Path $PSScriptRoot 'ComfyUI_windows_portable/python_embeded/python.exe'
& $avatarPython -u $avatarDownloadScript --download 2>&1 | Tee-Object -FilePath (Join-Path $PSScriptRoot 'logs/avatar-model-download.log') -Append
exit $LASTEXITCODE
