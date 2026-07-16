@echo off
setlocal
cd /d "%~dp0.."
if not exist ".runtime" mkdir ".runtime"
".venv\Scripts\streamlit.exe" run "agent\app.py" --server.address=127.0.0.1 --server.port=8501 --server.headless=true --browser.gatherUsageStats=false
endlocal
