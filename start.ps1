# SmartB100 - Startup script (PowerShell)
Write-Host "=== SmartB100 Startup ===" -ForegroundColor Green
Write-Host ""

# Locate Ollama dynamically via PATH
$ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue

if (-not $ollamaCmd) {
    Write-Host "ERROR: Ollama was not found on the system PATH." -ForegroundColor Red
    Write-Host ""
    Write-Host "Install Ollama from: https://ollama.com" -ForegroundColor Yellow
    Write-Host "Then restart the terminal and run this script again."
    exit 1
}

$ollamaPath = $ollamaCmd.Source

# 1. Check Qdrant
Write-Host "[1/4] Checking Qdrant..." -ForegroundColor Yellow
try {
    docker compose --profile infra up -d
    Write-Host "Qdrant: OK" -ForegroundColor Green
} catch {
    Write-Host "Qdrant: ERROR - check that Docker is running" -ForegroundColor Red
}

# 2. Check the Ollama models
Write-Host ""
Write-Host "[2/4] Checking Ollama models..." -ForegroundColor Yellow

# Joined into one string on purpose. `ollama list` returns an array of lines, and
# `-notmatch` against an array filters it instead of answering yes or no: it returns
# every line that does not match, which is almost always non-empty, so `if` saw True
# and both models were re-downloaded on every run even when already installed.
$models = (& $ollamaPath list 2>$null) -join [Environment]::NewLine

if ($models -notlike "*nomic-embed-text*") {
    Write-Host "Downloading the embedding model..."
    & $ollamaPath pull nomic-embed-text
}
if ($models -notlike "*llama3.2:3b*") {
    Write-Host "Downloading the chat model..."
    & $ollamaPath pull llama3.2:3b
}
Write-Host "Ollama: OK" -ForegroundColor Green

# 3. Show the service URLs
Write-Host ""
Write-Host "[3/4] Service URLs:" -ForegroundColor Yellow
Write-Host ""
Write-Host "API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Gradio UI: http://localhost:7860" -ForegroundColor Cyan
Write-Host "Qdrant: http://localhost:6333" -ForegroundColor Cyan
Write-Host ""

# 4. Start the services
Write-Host "[4/4] Starting the services..." -ForegroundColor Yellow

# Start the API in its own window
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "-m", "uvicorn", "api.main:app", "--reload" -WindowStyle Normal

# Give the API a moment to come up
Start-Sleep -Seconds 3

# Start the Gradio UI
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "ui/chat_ui.py" -WindowStyle Normal

Write-Host ""
Write-Host "Services started in separate windows." -ForegroundColor Green
Write-Host "Press Enter to close this window..."
Read-Host
