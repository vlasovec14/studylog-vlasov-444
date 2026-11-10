@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3.14 -m venv .venv
  if errorlevel 1 goto python_error
)
".venv\Scripts\python.exe" -c "import sys; assert sys.version_info >= (3,14)" >nul 2>&1
if errorlevel 1 goto python_error
".venv\Scripts\python.exe" -c "import django; assert django.VERSION[:2] == (6,0)" >nul 2>&1
if errorlevel 1 (
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto error
)
".venv\Scripts\python.exe" manage.py migrate --noinput
if errorlevel 1 goto error
start "" "http://127.0.0.1:8000/"
".venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000
if errorlevel 1 goto error
exit /b 0
:python_error
echo Python 3.14 is required. Install it from https://www.python.org/downloads/
echo Then run: py -3.14 -m venv .venv
pause
exit /b 1
:error
echo Startup failed. Read the error above. Port 8000 may already be in use.
pause
exit /b 1
