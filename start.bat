@echo off
echo === SmartB100 Startup ===
echo.

REM Locate Ollama dynamically via PATH
for /f "tokens=*" %%i in ('where ollama 2^>NUL') do set OLLAMA_EXE=%%i

if not defined OLLAMA_EXE (
    echo ERROR: Ollama was not found on the system PATH.
    echo.
    echo Install Ollama from: https://ollama.com
    echo Then restart the terminal and run this script again.
    exit /b 1
)

echo [1/4] Checking Qdrant...
docker compose --profile infra up -d
if %ERRORLEVEL% EQU 0 (
    echo Qdrant: OK
) else (
    echo Qdrant: ERROR - check that Docker is running
)

echo.
echo [2/4] Checking Ollama models...
"%OLLAMA_EXE%" list | findstr "nomic-embed-text" >NUL
if %ERRORLEVEL% NEQ 0 (
    echo Downloading the embedding model...
    "%OLLAMA_EXE%" pull nomic-embed-text
)

"%OLLAMA_EXE%" list | findstr "llama3.2:3b" >NUL
if %ERRORLEVEL% NEQ 0 (
    echo Downloading the chat model...
    "%OLLAMA_EXE%" pull llama3.2:3b
)
echo Ollama: OK

echo.
echo [3/4] Starting the API...
echo.
echo API: http://localhost:8000
echo Gradio UI: http://localhost:7860
echo Qdrant: http://localhost:6333
echo.

echo [4/4] Starting the services...
start "SmartB100 API" cmd /k ".venv\Scripts\python.exe -m uvicorn api.main:app --reload"
timeout /t 3 /nobreak >NUL
start "SmartB100 Gradio" cmd /k ".venv\Scripts\python.exe ui/chat_ui.py"

echo.
echo Services started in separate windows.
echo Press any key to close this window...
pause >NUL
