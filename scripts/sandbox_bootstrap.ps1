# Validação isolada: somente arquivos gerados são mapeados para o Sandbox.
$ErrorActionPreference = "Stop"
$inputFolder = "C:\SigiloPDF-input"
$reports = "C:\SigiloPDF-reports"
$result = [ordered]@{
    python_preinstalado = $false
    portatil = $false
    ferramentas_portatil = $false
    instalacao = $false
    instalado = $false
    ferramentas_instalado = $false
    desinstalacao = $false
    documentos_preservados = $false
    erro = ""
}
try {
    $result.python_preinstalado = [bool](Get-Command python.exe -ErrorAction SilentlyContinue)
    if ($result.python_preinstalado) { throw "O Sandbox possui Python no PATH; revise a imagem." }
    & "$inputFolder\validate_windows.ps1" -Executable "$inputFolder\SigiloPDF\SigiloPDF.exe"
    $result.portatil = $true
    $process = Start-Process -FilePath "$inputFolder\SigiloPDF\SigiloPDF.exe" -ArgumentList "--validar-build", "$reports\ferramentas-portatil.json" -PassThru -Wait -WindowStyle Hidden
    if ($process.ExitCode -ne 0) { throw "Falha no autoteste portátil." }
    $result.ferramentas_portatil = [bool](Get-Content "$reports\ferramentas-portatil.json" -Raw | ConvertFrom-Json).aprovado
    if (-not $result.ferramentas_portatil) { throw "Ferramentas portáteis não aprovadas." }
    $setup = Get-ChildItem "$inputFolder\installer\*-setup.exe" | Select-Object -First 1
    if (-not $setup) { throw "Instalador não encontrado." }
    $installation = "C:\SigiloPDF-install"
    $process = Start-Process -FilePath $setup.FullName -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-", "/DIR=$installation" -PassThru -Wait -WindowStyle Hidden
    if ($process.ExitCode -ne 0) { throw "Falha na instalação." }
    $result.instalacao = $true
    & "$inputFolder\validate_windows.ps1" -Executable "$installation\SigiloPDF.exe"
    $result.instalado = $true
    $process = Start-Process -FilePath "$installation\SigiloPDF.exe" -ArgumentList "--validar-build", "$reports\ferramentas-instalado.json" -PassThru -Wait -WindowStyle Hidden
    if ($process.ExitCode -ne 0) { throw "Falha no autoteste instalado." }
    $result.ferramentas_instalado = [bool](Get-Content "$reports\ferramentas-instalado.json" -Raw | ConvertFrom-Json).aprovado
    if (-not $result.ferramentas_instalado) { throw "Ferramentas instaladas não aprovadas." }
    $documents = "C:\SigiloPDF-documentos"
    New-Item -ItemType Directory -Path $documents | Out-Null
    $sentinel = Join-Path $documents "sintetico.pdf"
    Set-Content -Encoding ascii -LiteralPath $sentinel -Value "%PDF-1.4 documento sintetico de preservacao"
    $beforeHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $sentinel).Hash
    $process = Start-Process -FilePath "$installation\unins000.exe" -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART" -PassThru -Wait -WindowStyle Hidden
    if ($process.ExitCode -ne 0) { throw "Falha na desinstalação." }
    $deadline = (Get-Date).AddSeconds(30)
    while ((Test-Path "$installation\SigiloPDF.exe") -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 300 }
    if (Test-Path "$installation\SigiloPDF.exe") { throw "O executável permaneceu após desinstalar." }
    $result.desinstalacao = $true
    $result.documentos_preservados = (Get-FileHash -Algorithm SHA256 -LiteralPath $sentinel).Hash -eq $beforeHash
    if (-not $result.documentos_preservados) { throw "Documento sintético foi alterado." }
} catch {
    $result.erro = $_.Exception.Message
} finally {
    $result | ConvertTo-Json | Set-Content -Encoding utf8 "$reports\resultado.json"
}
