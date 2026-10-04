$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$inputFolder = Join-Path $root "build\sandbox-input"
$reports = Join-Path $root "build\sandbox-reports"
if (Test-Path -LiteralPath $inputFolder) { throw "A pasta de entrada do Sandbox já existe. Use uma pasta nova para outra validação." }
New-Item -ItemType Directory -Path $inputFolder, $reports | Out-Null
Copy-Item -LiteralPath "$root\dist\SigiloPDF" -Destination $inputFolder -Recurse
Copy-Item -LiteralPath "$root\dist\installer" -Destination $inputFolder -Recurse
Copy-Item -LiteralPath "$PSScriptRoot\validate_windows.ps1", "$PSScriptRoot\sandbox_bootstrap.ps1" -Destination $inputFolder
$escapedInput = [System.Security.SecurityElement]::Escape($inputFolder)
$escapedReports = [System.Security.SecurityElement]::Escape($reports)
@"
<Configuration>
  <Networking>Disable</Networking>
  <ClipboardRedirection>Disable</ClipboardRedirection>
  <MappedFolders>
    <MappedFolder><HostFolder>$escapedInput</HostFolder><SandboxFolder>C:\SigiloPDF-input</SandboxFolder><ReadOnly>true</ReadOnly></MappedFolder>
    <MappedFolder><HostFolder>$escapedReports</HostFolder><SandboxFolder>C:\SigiloPDF-reports</SandboxFolder><ReadOnly>false</ReadOnly></MappedFolder>
  </MappedFolders>
  <LogonCommand><Command>powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\SigiloPDF-input\sandbox_bootstrap.ps1</Command></LogonCommand>
</Configuration>
"@ | Set-Content -Encoding utf8 "$root\build\SigiloPDF.wsb"
Write-Host "Abra build\SigiloPDF.wsb. O relatório será gravado em build\sandbox-reports\resultado.json."
