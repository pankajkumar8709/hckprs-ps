$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot\..
$py = ".\.venv\Scripts\python.exe"
$srv = Start-Process -FilePath $py `
  -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8074" `
  -PassThru -RedirectStandardError "cf_err.log" -RedirectStandardOutput "cf_out.log" -NoNewWindow
$up = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 700
    try { $r = Invoke-WebRequest "http://127.0.0.1:8074/health" -UseBasicParsing -TimeoutSec 3; if ($r.StatusCode -eq 200) { $up = $true; break } } catch {}
}
try {
    if (-not $up) { Write-Host "SERVER DID NOT START"; Get-Content cf_err.log -Tail 30; exit 2 }
    & $py scripts\check_chat_fallback.py
    $code = $LASTEXITCODE
} finally {
    if ($srv -and -not $srv.HasExited) { Stop-Process -Id $srv.Id -Force }
    Remove-Item cf_err.log,cf_out.log -ErrorAction SilentlyContinue
}
exit $code
