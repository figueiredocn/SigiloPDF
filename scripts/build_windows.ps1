param(
    [string]$Python = ".venv\Scripts\python.exe",
    [string]$Iscc = ""
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Falha ao executar: $Program" }
}

Invoke-Checked $Python @("-m", "pytest", "-q")
Invoke-Checked $Python @("packaging/prepare_notices.py")
Invoke-Checked $Python @("-m", "PyInstaller", "--clean", "--noconfirm", "packaging/SigiloPDF.spec")
Invoke-Checked $Python @("packaging/audit_bundle.py")

if (-not $Iscc) {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    $Iscc = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $Iscc) { throw "Instale Inno Setup 6 ou informe -Iscc com o caminho do compilador." }
Invoke-Checked $Iscc @("packaging/installer.iss")

$archive = "dist\SigiloPDF-1.0.0-windows-x64-portable.zip"
if (Test-Path -LiteralPath $archive) { throw "O ZIP já existe. Escolha outro destino antes de gerar novamente." }
Compress-Archive -LiteralPath "dist\SigiloPDF" -DestinationPath $archive
Get-FileHash -Algorithm SHA256 $archive, "dist\installer\SigiloPDF-1.0.0-windows-x64-setup.exe" |
    ForEach-Object { "$($_.Hash.ToLower())  $(Split-Path $_.Path -Leaf)" } |
    Set-Content -Encoding ascii "dist\SHA256SUMS.txt"
Write-Host "Pacotes locais gerados. Valide os artefatos e as fontes correspondentes antes de publicar."
