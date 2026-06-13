@echo off
setlocal

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"
set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
set "PATH=%LOCALAPPDATA%\Programs\Ollama;%PATH%"

echo AI Companion Robot baslatiliyor...
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher bulunamadi. Python kurulu oldugundan emin ol.
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo npm bulunamadi. Node.js kurulu oldugundan emin ol.
  pause
  exit /b 1
)

if exist "%OLLAMA_EXE%" (
  echo Ollama bulundu: %OLLAMA_EXE%
  "%OLLAMA_EXE%" list
) else (
  echo Ollama bulunamadi. Lokal LLM devre disi kalabilir.
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
  taskkill /PID %%a /F >nul 2>nul
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
  taskkill /PID %%a /F >nul 2>nul
)

start "AI Robot Backend" /D "%BACKEND%" powershell -NoExit -ExecutionPolicy Bypass -Command "Write-Host 'Backend hazirlaniyor...'; py -m pip install -r requirements.txt; py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

start "AI Robot Frontend" /D "%FRONTEND%" powershell -NoExit -ExecutionPolicy Bypass -Command "Write-Host 'Frontend hazirlaniyor...'; if (!(Test-Path 'node_modules')) { npm install }; npm run dev -- --host 127.0.0.1"

echo Backend ve frontend pencereleri acildi.
echo Tarayici birazdan acilacak: http://localhost:5173
timeout /t 8 /nobreak >nul
start "" "http://localhost:5173"

endlocal
