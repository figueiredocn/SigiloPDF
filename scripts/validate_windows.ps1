param(
    [Parameter(Mandatory = $true)][string]$Executable,
    [string]$Report = ""
)

$ErrorActionPreference = "Stop"
$exe = (Resolve-Path -LiteralPath $Executable).Path
$previousPath = $env:PATH
$previousPythonHome = $env:PYTHONHOME
$previousPythonPath = $env:PYTHONPATH
$process = $null
$validationFile = Join-Path $env:TEMP ("sigilopdf-build-" + [guid]::NewGuid().ToString() + ".json")
$result = [ordered]@{ abertura = $false; fechamento = $false; python_externo = $false }

try {
    # Evitar que a versão portátil encontre Python/Qt da máquina de desenvolvimento.
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    $env:PYTHONHOME = $null
    $env:PYTHONPATH = $null
    $process = Start-Process -FilePath $exe -WorkingDirectory $env:TEMP -ArgumentList "--validar-build", "`"$validationFile`"" -PassThru -WindowStyle Hidden
    if (-not $process.WaitForExit(60000)) { throw "O autoteste não terminou no tempo esperado." }
    if ($process.ExitCode -ne 0) { throw "O autoteste empacotado encerrou com erro." }
    $validation = Get-Content -LiteralPath $validationFile -Raw | ConvertFrom-Json
    if (-not $validation.aprovado -or -not $validation.empacotado -or $validation.plataforma -ne "windows") { throw "O pacote não foi aprovado." }
    $result.abertura = $validation.abertura
    $result.fechamento = $validation.fechamento
    $result.ferramentas = $validation.aprovado
    Write-Host "Executável e ferramentas validados sem Python externo no PATH."
} finally {
    $env:PATH = $previousPath
    $env:PYTHONHOME = $previousPythonHome
    $env:PYTHONPATH = $previousPythonPath
    if ($process -and -not $process.HasExited) { Stop-Process -Id $process.Id }
    if (Test-Path -LiteralPath $validationFile) { Remove-Item -LiteralPath $validationFile }
    if ($Report) { $result | ConvertTo-Json | Set-Content -Encoding utf8 $Report }
}
