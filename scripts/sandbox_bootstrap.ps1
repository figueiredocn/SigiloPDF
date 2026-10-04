# Validação isolada: somente arquivos gerados são mapeados para o Sandbox.
$ErrorActionPreference = "Stop"
$inputFolder = "C:\SigiloPDF-input"
$reports = "C:\SigiloPDF-reports"
$result = [ordered]@{
    python_preinstalado = $false
    portatil = $false
    instalacao = $false
    instalado = $false
    desinstalacao = $false
    erro = ""
}
try {
    $result.python_preinstalado = [bool](Get-Command python.exe -ErrorAction SilentlyContinue)
    if ($result.python_preinstalado) { throw "O Sandbox possui Python no PATH; revise a imagem." }
    & "$inputFolder\validate_windows.ps1" -Executable "$inputFolder\SigiloPDF\SigiloPDF.exe"
    $result.portatil = $true
    $setup = Get-ChildItem "$inputFolder\installer\*-setup.exe" | Select-Object -First 1
    if (-not $setup) { throw "Instalador não encontrado." }
    $installation = Join-Path $env:LOCALAPPDATA "Programs\SigiloPDF"
    $process = Start-Process -FilePath $setup.FullName -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-" -PassThru -Wait -WindowStyle Hidden
    if ($process.ExitCode -ne 0) { throw "Falha na instalação." }
    $result.instalacao = $true
    & "$inputFolder\validate_windows.ps1" -Executable "$installation\SigiloPDF.exe"
    $result.instalado = $true
    $process = Start-Process -FilePath "$installation\unins000.exe" -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART" -PassThru -Wait -WindowStyle Hidden
    if ($process.ExitCode -ne 0) { throw "Falha na desinstalação." }
    $deadline = (Get-Date).AddSeconds(30)
    while ((Test-Path "$installation\SigiloPDF.exe") -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 300 }
    if (Test-Path "$installation\SigiloPDF.exe") { throw "O executável permaneceu após desinstalar." }
    $result.desinstalacao = $true
} catch {
    $result.erro = $_.Exception.Message
} finally {
    $result | ConvertTo-Json | Set-Content -Encoding utf8 "$reports\resultado.json"
}
