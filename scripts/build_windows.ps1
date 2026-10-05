param(
    [string]$Python = ".venv\Scripts\python.exe",
    [string]$Iscc = "",
    [string]$OutputDirectory = "dist"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$output = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputDirectory))
$distRoot = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) "dist"))
if ($output -ne $distRoot -and -not $output.StartsWith($distRoot + "\", [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "A saída do build deve ficar na pasta dist do projeto."
}
$releaseVersion = (& $Python -c "from app.version import __version__; print(__version__)").Trim()
if ($LASTEXITCODE -ne 0 -or $releaseVersion -notmatch '^\d+\.\d+\.\d+$') { throw "Versão de build inválida." }
$archive = Join-Path $output "SigiloPDF-$releaseVersion-windows-x64-portable.zip"
if (Test-Path -LiteralPath $archive) { throw "O ZIP já existe. Escolha outra pasta com -OutputDirectory." }

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Falha ao executar: $Program" }
}

Invoke-Checked $Python @("-m", "pytest", "-q")
Invoke-Checked $Python @("packaging/prepare_notices.py")
Invoke-Checked $Python @("-m", "PyInstaller", "--clean", "--noconfirm", "--distpath", $output, "packaging/SigiloPDF.spec")
Invoke-Checked $Python @("packaging/audit_bundle.py", (Join-Path $output "SigiloPDF"))

if (-not $Iscc) {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    $Iscc = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $Iscc) { throw "Instale Inno Setup 6 ou informe -Iscc com o caminho do compilador." }
Invoke-Checked $Iscc @("/DBuildDir=$output", "/DAppVersion=$releaseVersion", "packaging/installer.iss")

Compress-Archive -LiteralPath (Join-Path $output "SigiloPDF") -DestinationPath $archive
Get-FileHash -Algorithm SHA256 $archive, (Join-Path $output "installer\SigiloPDF-$releaseVersion-windows-x64-setup.exe") |
    ForEach-Object { "$($_.Hash.ToLower())  $(Split-Path $_.Path -Leaf)" } |
    Set-Content -Encoding ascii (Join-Path $output "SHA256SUMS.txt")
Write-Host "Pacotes locais gerados. Valide os artefatos e as fontes correspondentes antes de publicar."
