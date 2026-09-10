$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot\..
$py = ".\.venv\Scripts\python.exe"
$srv = Start-Process -FilePath $py `
  -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8073" `
  -PassThru -RedirectStandardError "web_err.log" -RedirectStandardOutput "web_out.log" -NoNewWindow
$up = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 700
    try { $r = Invoke-WebRequest "http://127.0.0.1:8073/health" -UseBasicParsing -TimeoutSec 3; if ($r.StatusCode -eq 200) { $up = $true; break } } catch {}
}
try {
    if (-not $up) { Write-Host "SERVER DID NOT START"; Get-Content web_err.log -Tail 30; exit 2 }
    $root = Invoke-WebRequest "http://127.0.0.1:8073/" -UseBasicParsing -TimeoutSec 5
    $hasReact = $root.Content -match "react" -and $root.Content -match "LifeOS"
    Write-Host "GET / -> status" $root.StatusCode "length" $root.Content.Length "reactApp:" $hasReact
    $h = Invoke-WebRequest "http://127.0.0.1:8073/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "GET /health ->" $h.Content
    $o = Invoke-WebRequest "http://127.0.0.1:8073/openapi.json" -UseBasicParsing -TimeoutSec 5
    Write-Host "GET /openapi.json -> status" $o.StatusCode "length" $o.Content.Length
} finally {
    if ($srv -and -not $srv.HasExited) { Stop-Process -Id $srv.Id -Force }
    Remove-Item web_err.log,web_out.log -ErrorAction SilentlyContinue
}
