$ErrorActionPreference = "Continue"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
New-Item -ItemType Directory -Force .runtime | Out-Null
& .\.venv\Scripts\streamlit.exe run agent\app.py `
  --server.address=127.0.0.1 `
  --server.port=8501 `
  --server.headless=true `
  --browser.gatherUsageStats=false `
  2>&1 | Tee-Object -FilePath .runtime\streamlit.log
