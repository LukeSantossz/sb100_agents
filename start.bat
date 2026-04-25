@echo off
echo === SmartB100 Startup ===
echo.

REM Localizar Ollama dinamicamente via PATH
for /f "tokens=*" %%i in ('where ollama 2^>nul') do set OLLAMA_EXE=%%i

if not defined OLLAMA_EXE (
    echo ERRO: Ollama nao encontrado no PATH do sistema.
    echo.
    echo Instale o Ollama em: https://ollama.com
    echo Apos instalar, reinicie o terminal e execute este script novamente.
    exit /b 1
)

echo [1/5] Verificando Qdrant...
docker-compose up -d
if %ERRORLEVEL% EQU 0 (
    echo Qdrant: OK
) else (
    echo Qdrant: ERRO - Verifique se o Docker esta rodando
)

echo.
echo [2/5] Verificando modelos Ollama...
"%OLLAMA_EXE%" list | findstr "nomic-embed-text" >nul
if %ERRORLEVEL% NEQ 0 (
    echo Baixando modelo de embeddings...
    "%OLLAMA_EXE%" pull nomic-embed-text
)

"%OLLAMA_EXE%" list | findstr "llama3.1:8b" >nul
if %ERRORLEVEL% NEQ 0 (
    echo Baixando modelo de chat...
    "%OLLAMA_EXE%" pull llama3.1:8b
)
echo Ollama: OK

echo.
echo [3/5] Verificando dependencias do frontend...
if not exist "frontend\smartb100\node_modules" (
    echo Instalando dependencias do frontend...
    cd frontend\smartb100 && npm install && cd ..\..
)
echo Frontend deps: OK

echo.
echo [4/5] Verificando concurrently...
if not exist "node_modules" (
    echo Instalando dependencias raiz...
    npm install
)
echo Concurrently: OK

echo.
echo [5/5] Iniciando servicos...
echo.
echo API: http://localhost:8000
echo Frontend: http://localhost:5173
echo Qdrant: http://localhost:6333
echo.
npm run start
