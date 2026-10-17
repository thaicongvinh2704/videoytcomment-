@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
where python >nul 2>nul || (echo Can cai Python 3.10+ truoc khi chay. & pause & exit /b 1)
where ffmpeg >nul 2>nul || (echo Can cai FFmpeg va them vao PATH. & pause & exit /b 1)
python -m pip install -r requirements.txt
if errorlevel 1 (pause & exit /b 1)
start "" /B powershell -NoProfile -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:8765'"
python -m shorts_studio serve
pause
