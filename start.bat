@echo off
echo === SmartB100 Startup ===
echo.

REM Localizar Ollama dinamicamente via PATH
for /f "tokens=*" %%i in ('where ollama 2^>NUL') do set OLLAMA_EXE=%%i

if not defined OLLAMA_EXE (
    echo ERRO: Ollama nao encontrado no PATH do sistema.
    echo.
    echo Instale o Ollama em: https://ollama.com
    echo Apos instalar, reinicie o terminal e execute este script novamente.
    exit /b 1
)

echo [1/4] Verificando Qdrant...
docker compose --profile infra up -d
if %ERRORLEVEL% EQU 0 (
    echo Qdrant: OK
) else (
    echo Qdrant: ERRO - Verifique se o Docker esta rodando
)

echo.
echo [2/4] Verificando modelos Ollama...
"%OLLAMA_EXE%" list | findstr "nomic-embed-text" >NUL
if %ERRORLEVEL% NEQ 0 (
    echo Baixando modelo de embeddings...
    "%OLLAMA_EXE%" pull nomic-embed-text
)

"%OLLAMA_EXE%" list | findstr "llama3.2:3b" >NUL
if %ERRORLEVEL% NEQ 0 (
    echo Baixando modelo de chat...
    "%OLLAMA_EXE%" pull llama3.2:3b
)
echo Ollama: OK

echo.
echo [3/4] Iniciando API...
echo.
echo API: http://localhost:8000
echo Gradio UI: http://localhost:7860
echo Qdrant: http://localhost:6333
echo.

echo [4/4] Iniciando servicos...
start "SmartB100 API" cmd /k ".venv\Scripts\python.exe -m uvicorn api.main:app --reload"
timeout /t 3 /nobreak >NUL
start "SmartB100 Gradio" cmd /k ".venv\Scripts\python.exe ui/chat_ui.py"

echo.
echo Servicos iniciados em janelas separadas.
echo Pressione qualquer tecla para fechar esta janela...
pause >NUL
