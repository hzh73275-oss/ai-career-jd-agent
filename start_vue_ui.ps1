$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectPython = Join-Path $Root ".venv\Scripts\python.exe"
$ParentPython = Join-Path $Root "..\.venv\Scripts\python.exe"

if (Test-Path $ProjectPython) {
  $Python = $ProjectPython
} elseif (Test-Path $ParentPython) {
  $Python = $ParentPython
} else {
  $Python = "python"
}

Start-Process powershell.exe -ArgumentList @(
  "-NoExit",
  "-Command",
  "cd '$Root'; '$Python' -B run_app.py"
)

Write-Host "Started:"
Write-Host "API: http://127.0.0.1:8765"
Write-Host "UI:  http://127.0.0.1:5175"
