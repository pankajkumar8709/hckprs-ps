$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot\..
$py = ".\.venv\Scripts\python.exe"

$srv = Start-Process -FilePath $py `
  -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8071" `
  -PassThru -RedirectStandardError "server_err.log" -RedirectStandardOutput "server_out.log" -NoNewWindow

# Wait until /health responds or timeout
$up = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 700
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8071/health" -UseBasicParsing -TimeoutSec 3
        if ($resp.StatusCode -eq 200) { $up = $true; break }
    } catch { }
}

try {
    if (-not $up) {
        Write-Host "SERVER DID NOT START. --- server_err.log ---"
        if (Test-Path server_err.log) { Get-Content server_err.log -Tail 40 }
        exit 2
    }
    & $py scripts\e2e_mvp.py
    $code = $LASTEXITCODE
} finally {
    if ($srv -and -not $srv.HasExited) { Stop-Process -Id $srv.Id -Force }
}
exit $code
