[CmdletBinding()]
param(
    [switch]$StopDatabase
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$runtimeDirectory = Join-Path $repoRoot ".local"

function Stop-ManagedProcessTree {
    param(
        [Parameter(Mandatory)]
        [int]$RootProcessId
    )

    $childProcesses = Get-CimInstance Win32_Process -Filter (
        "ParentProcessId = $RootProcessId"
    )

    foreach ($childProcess in $childProcesses) {
        Stop-ManagedProcessTree -RootProcessId $childProcess.ProcessId
    }

    $process = Get-Process -Id $RootProcessId -ErrorAction SilentlyContinue

    if ($null -ne $process) {
        Stop-Process -Id $RootProcessId
    }
}

foreach ($serviceName in @("frontend", "backend")) {
    $pidPath = Join-Path $runtimeDirectory "$serviceName.pid"

    if (-not (Test-Path -LiteralPath $pidPath)) {
        Write-Host "No managed $serviceName process was found."
        continue
    }

    $processId = [int](Get-Content -LiteralPath $pidPath -Raw)
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue

    if ($null -ne $process) {
        Stop-ManagedProcessTree -RootProcessId $processId
        Write-Host "Stopped $serviceName process $processId."
    }
    else {
        Write-Host "$serviceName process $processId is no longer running."
    }

    Remove-Item -LiteralPath $pidPath -Force
}

if ($StopDatabase) {
    $dockerCommand = Get-Command docker -ErrorAction Stop
    & $dockerCommand.Source compose -f (Join-Path $repoRoot "docker-compose.yml") stop db

    if ($LASTEXITCODE -ne 0) {
        throw "Docker could not stop the PostgreSQL service."
    }
}
