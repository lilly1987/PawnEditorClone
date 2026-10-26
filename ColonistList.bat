@echo off
py -3 "%~dp0ColonistList.py"
if errorlevel 1 (
    echo Failed to create Colonists 32.xml.
    @REM  pause
    exit /b 1
)
@REM  pause
