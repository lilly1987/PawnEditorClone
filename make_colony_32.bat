@echo off
py -3 "%~dp0clone_colony_preset.py"
if errorlevel 1 (
    echo Failed to create Colony 32.xml.
    pause
    exit /b 1
)
pause
