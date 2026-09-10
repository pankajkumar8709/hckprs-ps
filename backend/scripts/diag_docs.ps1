$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot\..
$py = ".\.venv\Scripts\python.exe"
$srv = Start-Process -FilePath $py `
  -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8072" `
  -PassThru -RedirectStandardError "diag_err.log" -RedirectStandardOutput "diag_out.log" -NoNewWindow
$up = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 700
    try { $r = Invoke-WebRequest "http://127.0.0.1:8072/health" -UseBasicParsing -TimeoutSec 3; if ($r.StatusCode -eq 200) { $up = $true; break } } catch {}
}
try {
    if (-not $up) { Write-Host "SERVER DID NOT START"; Get-Content diag_err.log -Tail 30; exit 2 }
    $docs = Invoke-WebRequest "http://127.0.0.1:8072/docs" -UseBasicParsing -TimeoutSec 5
    Write-Host "=== /docs status:" $docs.StatusCode " length:" $docs.Content.Length
    Write-Host "=== /docs first 600 chars ==="
    Write-Host $docs.Content.Substring(0, [Math]::Min(600, $docs.Content.Length))
    $oapi = Invoke-WebRequest "http://127.0.0.1:8072/openapi.json" -UseBasicParsing -TimeoutSec 5
    Write-Host "`n=== /openapi.json status:" $oapi.StatusCode " length:" $oapi.Content.Length
} finally {
    if ($srv -and -not $srv.HasExited) { Stop-Process -Id $srv.Id -Force }
}
