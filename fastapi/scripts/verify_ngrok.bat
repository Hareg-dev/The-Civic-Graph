@echo off
REM Verify ngrok installation

echo ==========================================
echo Verifying ngrok Installation
echo ==========================================
echo.

set "NGROK_EXE=%USERPROFILE%\ngrok\ngrok.exe"

if exist "%NGROK_EXE%" (
    echo [OK] ngrok found at: %NGROK_EXE%
    echo.
    echo Version:
    "%NGROK_EXE%" version
    echo.
    echo Configuration:
    "%NGROK_EXE%" config check
    echo.
    echo ==========================================
    echo ngrok is ready to use!
    echo ==========================================
    echo.
    echo To deploy your platform:
    echo   deploy_with_ngrok_direct.bat
    echo.
) else (
    echo [ERROR] ngrok not found at: %NGROK_EXE%
    echo.
    echo Please run: setup_ngrok_simple.bat
    echo.
)

pause
