@echo off
REM Simple ngrok setup without admin rights

echo ==========================================
echo Setting up ngrok (Simple Method)
echo ==========================================
echo.

REM Create ngrok directory in user folder
set "NGROK_DIR=%USERPROFILE%\ngrok"
if not exist "%NGROK_DIR%" mkdir "%NGROK_DIR%"

echo Downloading ngrok...
powershell -Command "Invoke-WebRequest -Uri 'https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip' -OutFile '%NGROK_DIR%\ngrok.zip'"

echo Extracting ngrok...
powershell -Command "Expand-Archive -Path '%NGROK_DIR%\ngrok.zip' -DestinationPath '%NGROK_DIR%' -Force"

echo Configuring auth token...
"%NGROK_DIR%\ngrok.exe" config add-authtoken 36dyWRteksM8siCAt3M8Vz6JXEv_6dzWUD64rzTsoF4Xf4NMs

echo.
echo ==========================================
echo Setup Complete!
echo ==========================================
echo.
echo ngrok installed at: %NGROK_DIR%
echo.
echo To use ngrok, run:
echo   %NGROK_DIR%\ngrok.exe http 80
echo.
echo Or use the deployment script:
echo   deploy_with_ngrok_direct.bat
echo.
pause
