@echo off
setlocal

title SO-101 Robotics Studio V4 Bootstrapper
cd /d "%~dp0"

echo =====================================================================
echo           SO-101 ROBOTICS STUDIO V4 - ONE-CLICK LAUNCHER
echo =====================================================================
echo.

:: 1. Verify system Python installation
where python >nul 2>nul
if errorlevel 1 goto :no_python

:: 2. Check / Create Isolated Virtual Environment
if exist ".venv\Scripts\python.exe" goto :launch_app

echo [*] Creating isolated virtual environment in .venv ...
python -m venv .venv --system-site-packages
if errorlevel 1 (
    python -m venv .venv
)
if not exist ".venv\Scripts\python.exe" goto :venv_failed

echo [OK] Virtual environment created successfully.
echo [*] Installing GUI dependencies from requirements_gui.txt ...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :install_failed
".venv\Scripts\python.exe" -m pip install -r requirements_gui.txt
if errorlevel 1 goto :install_failed

:launch_app
echo [*] Virtual environment verified [.venv].
echo [*] Launching SO-101 Studio V4 Desktop Application...
echo.
".venv\Scripts\python.exe" app_v4.py %*
set APP_EXIT_CODE=%ERRORLEVEL%

if %APP_EXIT_CODE% neq 0 (
    echo.
    echo [ERROR] Application exited with error code %APP_EXIT_CODE%.
    echo Please check the console output or v4_studio.log for details.
    pause
)
exit /b %APP_EXIT_CODE%

:install_failed
echo [ERROR] Failed to install GUI dependencies. Check your network/Python version and retry.
pause
exit /b 1

:no_python
echo [ERROR] Python was not found on your system PATH!
echo Please install Python 3.10+ 64-bit from https://www.python.org/
echo and ensure "Add Python to PATH" is checked during installation.
echo.
pause
exit /b 1

:venv_failed
echo [ERROR] Failed to create virtual environment!
pause
exit /b 1
