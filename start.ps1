# SmartB100 - Script de Inicializacao (PowerShell)
Write-Host "=== SmartB100 Startup ===" -ForegroundColor Green
Write-Host ""

# Localizar Ollama dinamicamente via PATH
$ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue

if (-not $ollamaCmd) {
    Write-Host "ERRO: Ollama nao encontrado no PATH do sistema." -ForegroundColor Red
    Write-Host ""
    Write-Host "Instale o Ollama em: https://ollama.com" -ForegroundColor Yellow
    Write-Host "Apos instalar, reinicie o terminal e execute este script novamente."
    exit 1
}

$ollamaPath = $ollamaCmd.Source

# 1. Verificar Qdrant
Write-Host "[1/4] Verificando Qdrant..." -ForegroundColor Yellow
try {
    docker compose --profile infra up -d
    Write-Host "Qdrant: OK" -ForegroundColor Green
} catch {
    Write-Host "Qdrant: ERRO - Verifique se o Docker esta rodando" -ForegroundColor Red
}

# 2. Verificar modelos Ollama
Write-Host ""
Write-Host "[2/4] Verificando modelos Ollama..." -ForegroundColor Yellow

$models = & $ollamaPath list 2>$null
if ($models -notmatch "nomic-embed-text") {
    Write-Host "Baixando modelo de embeddings..."
    & $ollamaPath pull nomic-embed-text
}
if ($models -notmatch "llama3.2:3b") {
    Write-Host "Baixando modelo de chat..."
    & $ollamaPath pull llama3.2:3b
}
Write-Host "Ollama: OK" -ForegroundColor Green

# 3. Exibir URLs
Write-Host ""
Write-Host "[3/4] URLs dos servicos:" -ForegroundColor Yellow
Write-Host ""
Write-Host "API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Gradio UI: http://localhost:7860" -ForegroundColor Cyan
Write-Host "Qdrant: http://localhost:6333" -ForegroundColor Cyan
Write-Host ""

# 4. Iniciar servicos
Write-Host "[4/4] Iniciando servicos..." -ForegroundColor Yellow

# Iniciar API em background
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "-m", "uvicorn", "api.main:app", "--reload" -WindowStyle Normal

# Aguardar API iniciar
Start-Sleep -Seconds 3

# Iniciar Gradio UI
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "ui/chat_ui.py" -WindowStyle Normal

Write-Host ""
Write-Host "Servicos iniciados em janelas separadas." -ForegroundColor Green
Write-Host "Pressione Enter para fechar esta janela..."
Read-Host
