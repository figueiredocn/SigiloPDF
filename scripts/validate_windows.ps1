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
$result = [ordered]@{ abertura = $false; fechamento = $false; python_externo = $false }

try {
    # Evitar que a versão portátil encontre Python/Qt da máquina de desenvolvimento.
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    $env:PYTHONHOME = $null
    $env:PYTHONPATH = $null
    $process = Start-Process -FilePath $exe -WorkingDirectory $env:TEMP -PassThru -WindowStyle Normal
    $deadline = (Get-Date).AddSeconds(45)
    do {
        Start-Sleep -Milliseconds 200
        $process.Refresh()
        if ($process.HasExited) { throw "O executável encerrou antes de abrir a janela." }
    } while ($process.MainWindowHandle -eq 0 -and (Get-Date) -lt $deadline)
    if ($process.MainWindowHandle -eq 0) { throw "A janela não abriu no tempo esperado." }
    if ($process.MainWindowTitle -notlike "*SigiloPDF*") { throw "Janela inesperada." }
    $result.abertura = $true
    if (-not $process.CloseMainWindow()) { throw "Não foi possível solicitar o fechamento." }
    if (-not $process.WaitForExit(15000)) { throw "A janela permaneceu ativa após fechar." }
    if ($process.ExitCode -ne 0) { throw "O aplicativo encerrou com erro." }
    $result.fechamento = $true
    Write-Host "Executável abriu e fechou sem Python externo no PATH."
} finally {
    $env:PATH = $previousPath
    $env:PYTHONHOME = $previousPythonHome
    $env:PYTHONPATH = $previousPythonPath
    if ($process -and -not $process.HasExited) { Stop-Process -Id $process.Id }
    if ($Report) { $result | ConvertTo-Json | Set-Content -Encoding utf8 $Report }
}
