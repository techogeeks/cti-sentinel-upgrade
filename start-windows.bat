@echo off
setlocal
cd /d "%~dp0"
if not exist "frontend\package.json" (
  echo ERROR: This batch file must be next to the frontend folder.
  pause
  exit /b 1
)
where python >nul 2>&1
if errorlevel 1 (echo ERROR: Python is not on PATH. & pause & exit /b 1)
where npm >nul 2>&1
if errorlevel 1 (echo ERROR: Node.js/npm is not on PATH. & pause & exit /b 1)
if not exist "frontend\node_modules" (
  echo Frontend packages not found. Run: cd frontend ^&^& npm install
  pause
  exit /b 1
)
echo Checking for Ollama local model service...
where ollama >nul 2>&1
if errorlevel 1 (
  if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
    echo Ollama installed but not on PATH. Reopen VS Code to enable its CLI.
  ) else (
    echo Ollama is not installed. Get it at https://ollama.com/download/windows
  )
) else (
  echo Ollama detected. If the AI assistant reports no models, run: ollama pull qwen2.5:3b
)
echo Launching CTI Sentinel backend and frontend in separate terminals...
start "CTI Sentinel API" cmd /k "cd /d ""%~dp0"" && python -m backend.app"
start "CTI Sentinel Frontend" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"
echo Open http://localhost:5173 when Vite reports ready.
pause
