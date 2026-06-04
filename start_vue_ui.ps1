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
  "cd '$Root'; '$Python' -B -m src.api.server"
)

Start-Sleep -Seconds 2

Start-Process powershell.exe -ArgumentList @(
  "-NoExit",
  "-Command",
  "cd '$Root'; '$Python' -m http.server 5175 --bind 127.0.0.1 --directory frontend"
)

Start-Sleep -Seconds 1
Start-Process "http://127.0.0.1:5175"

Write-Host "Started:"
Write-Host "API: http://127.0.0.1:8765"
Write-Host "UI:  http://127.0.0.1:5175"
