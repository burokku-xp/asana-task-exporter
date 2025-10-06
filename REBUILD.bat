@echo off
echo Cleaning and rebuilding...
rmdir /s /q build dist 2>nul
pyinstaller --clean build_no_hooks.spec
if exist dist\AsanaTaskExporter.exe (
    echo.
    echo SUCCESS
    echo.
    dist\AsanaTaskExporter.exe
) else (
    echo FAILED
)
pause
