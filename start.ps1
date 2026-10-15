# MAVIRA — kill existing, then start backend + frontend in separate windows
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Stopping any existing MAVIRA processes..."

# Kill processes holding ports 8000 and 3000
foreach ($port in @(8000, 3000)) {
    $conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($conn) {
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        Write-Host "  Killed process on port $port"
    }
}

# Kill any lingering python / node / uvicorn processes
Get-Process -Name python, python3, uvicorn, node -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 1

Write-Host "Starting MAVIRA..."

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\backend'; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload" -WindowStyle Normal

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\frontend'; npm run dev" -WindowStyle Normal

Write-Host ""
Write-Host "  Backend  ->  http://localhost:8000/api/docs"
Write-Host "  Frontend ->  http://localhost:3000"
Write-Host ""
Write-Host "Close the two terminal windows to stop."
