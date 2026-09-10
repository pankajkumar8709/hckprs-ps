$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot\..
$py = ".\.venv\Scripts\python.exe"
$srv = Start-Process -FilePath $py `
  -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8075" `
  -PassThru -RedirectStandardError "q_err.log" -RedirectStandardOutput "q_out.log" -NoNewWindow
$up = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 700
    try { $r = Invoke-WebRequest "http://127.0.0.1:8075/health" -UseBasicParsing -TimeoutSec 3; if ($r.StatusCode -eq 200) { $up = $true; break } } catch {}
}
try {
    if (-not $up) { Write-Host "SERVER DID NOT START"; Get-Content q_err.log -Tail 30; exit 2 }
    & $py scripts\check_chat_query.py
    $code = $LASTEXITCODE
} finally {
    if ($srv -and -not $srv.HasExited) { Stop-Process -Id $srv.Id -Force }
    Remove-Item q_err.log,q_out.log -ErrorAction SilentlyContinue
}
exit $code
