$ErrorActionPreference = 'Stop'
$avatarRoot = Join-Path $PSScriptRoot 'tools/avatar/Wan2GP'
$avatarPython = Join-Path $avatarRoot '.venv/Scripts/python.exe'
$env:HF_HOME = Join-Path $PSScriptRoot 'tools/avatar/cache/huggingface'
$env:HF_HUB_DISABLE_XET = '1'
$env:GRADIO_ANALYTICS_ENABLED = 'False'
$env:GIT_PYTHON_REFRESH = 'quiet'
Set-Location -LiteralPath $avatarRoot
& $avatarPython -u wgp.py --server-name 127.0.0.1 --server-port 7861 --profile 4 --attention sage2 @args
exit $LASTEXITCODE
