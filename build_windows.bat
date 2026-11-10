@echo off
setlocal
cd /d "%~dp0"
echo Building LIGGGHTS UI Basic v1.1.1 - Mishal Mohanlal
py -3 -m pip install "pyinstaller>=6.15,<7"
if errorlevel 1 goto fail
py -3 -m unittest discover -s tests -v
if errorlevel 1 goto fail
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name LIGGGHTS_UI_basic --version-file version_info.txt liggghts_ui.py
if errorlevel 1 goto fail
echo.
echo SUCCESS: dist\LIGGGHTS_UI_basic.exe
pause
exit /b 0
:fail
echo.
echo Build FAILED. See messages above.
pause
exit /b 1
