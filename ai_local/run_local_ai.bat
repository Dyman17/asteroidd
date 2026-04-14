@echo off
setlocal

set "CLOUD_BACKEND_URL=https://asteroidd-server.onrender.com"
set "AI_PORT=8000"
set "AI_PATH=/analyze_bytes"
set "AI_DEVICE_ID=ai-laptop-1"
set "AI_HEALTH_PATH=/health"
set "PULL_INTERVAL=2.0"

echo Starting local AI server on port %AI_PORT%...
echo Cloud backend: %CLOUD_BACKEND_URL%
echo AI device ID: %AI_DEVICE_ID%
echo Pull interval: %PULL_INTERVAL% seconds
echo.

start "Local AI Server" cmd /k "set PORT=%AI_PORT% && set CLOUD_BACKEND_URL=%CLOUD_BACKEND_URL% && set AI_DEVICE_ID=%AI_DEVICE_ID% && set PULL_INTERVAL=%PULL_INTERVAL% && python app.py"

set "AI_HEALTH_URL=http://localhost:%AI_PORT%%AI_HEALTH_PATH%"

echo Waiting for local AI server to become available at %AI_HEALTH_URL%...
python wait_for_local_ai.py
if errorlevel 1 (
    echo.
    echo ERROR: Local AI server did not respond in time.
    echo Check the server window for errors.
    pause
    goto end
)

echo Registering local AI server with cloud backend...
python register_ai.py
if errorlevel 1 (
    echo.
    echo Registration failed. Check the cloud backend URL and network connection.
) else (
    echo.
    echo Registration successful.
)
echo.
echo Local AI startup complete.
echo The server is now pulling frames from the cloud every %PULL_INTERVAL% seconds.
echo Check the "Local AI Server" window for pull status messages.
pause
:end
endlocal
