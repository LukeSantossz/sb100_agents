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
Write-Host "[1/5] Verificando Qdrant..." -ForegroundColor Yellow
try {
    docker-compose up -d
    Write-Host "Qdrant: OK" -ForegroundColor Green
} catch {
    Write-Host "Qdrant: ERRO - Verifique se o Docker esta rodando" -ForegroundColor Red
}

# 2. Verificar modelos Ollama
Write-Host ""
Write-Host "[2/5] Verificando modelos Ollama..." -ForegroundColor Yellow

$models = & $ollamaPath list 2>$null
if ($models -notmatch "nomic-embed-text") {
    Write-Host "Baixando modelo de embeddings..."
    & $ollamaPath pull nomic-embed-text
}
if ($models -notmatch "llama3.1:8b") {
    Write-Host "Baixando modelo de chat..."
    & $ollamaPath pull llama3.1:8b
}
Write-Host "Ollama: OK" -ForegroundColor Green

# 3. Verificar dependencias do frontend
Write-Host ""
Write-Host "[3/5] Verificando dependencias do frontend..." -ForegroundColor Yellow
if (-not (Test-Path "frontend\smartb100\node_modules")) {
    Write-Host "Instalando dependencias do frontend..."
    Push-Location "frontend\smartb100"
    npm install
    Pop-Location
}
Write-Host "Frontend deps: OK" -ForegroundColor Green

# 4. Verificar concurrently
Write-Host ""
Write-Host "[4/5] Verificando concurrently..." -ForegroundColor Yellow
if (-not (Test-Path "node_modules")) {
    Write-Host "Instalando dependencias raiz..."
    npm install
}
Write-Host "Concurrently: OK" -ForegroundColor Green

# 5. Iniciar servicos
Write-Host ""
Write-Host "[5/5] Iniciando servicos..." -ForegroundColor Yellow
Write-Host ""
Write-Host "API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host "Qdrant: http://localhost:6333" -ForegroundColor Cyan
Write-Host ""

npm run start
