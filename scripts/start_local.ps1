[CmdletBinding()]
param(
    [switch]$SkipDocker
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$frontendRoot = Join-Path $repoRoot "frontend"
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$runtimeDirectory = Join-Path $repoRoot ".local"

function Test-LocalPort {
    param(
        [Parameter(Mandatory)]
        [int]$Port
    )

    $client = [System.Net.Sockets.TcpClient]::new()

    try {
        $connection = $client.ConnectAsync("127.0.0.1", $Port)
        return $connection.Wait(500) -and $client.Connected
    }
    finally {
        $client.Dispose()
    }
}

function Wait-ForPort {
    param(
        [Parameter(Mandatory)]
        [int]$Port,

        [Parameter(Mandatory)]
        [string]$ServiceName,

        [int]$TimeoutSeconds = 30
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)

    while ((Get-Date) -lt $deadline) {
        if (Test-LocalPort -Port $Port) {
            return
        }

        Start-Sleep -Milliseconds 500
    }

    throw "$ServiceName did not start on port $Port within $TimeoutSeconds seconds."
}

function Start-LocalService {
    param(
        [Parameter(Mandatory)]
        [string]$Name,

        [Parameter(Mandatory)]
        [string]$FilePath,

        [Parameter(Mandatory)]
        [string[]]$ArgumentList,

        [Parameter(Mandatory)]
        [string]$WorkingDirectory,

        [Parameter(Mandatory)]
        [int]$Port
    )

    if (Test-LocalPort -Port $Port) {
        Write-Host "$Name is already running on port $Port."
        return
    }

    $stdoutPath = Join-Path $runtimeDirectory "$Name.log"
    $stderrPath = Join-Path $runtimeDirectory "$Name.error.log"
    $pidPath = Join-Path $runtimeDirectory "$Name.pid"

    $process = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $stdoutPath `
        -RedirectStandardError $stderrPath `
        -WindowStyle Hidden `
        -PassThru

    Set-Content -LiteralPath $pidPath -Value $process.Id
    Wait-ForPort -Port $Port -ServiceName $Name
    Write-Host "$Name started on port $Port."
}

if (-not (Test-Path -LiteralPath $python)) {
    throw "Python virtual environment not found at $python."
}

$npmCommand = Get-Command npm.cmd -ErrorAction Stop
New-Item -ItemType Directory -Path $runtimeDirectory -Force | Out-Null

if (-not $SkipDocker) {
    $dockerCommand = Get-Command docker -ErrorAction SilentlyContinue

    if ($null -eq $dockerCommand) {
        throw "Docker is not available. Start PostgreSQL manually or use -SkipDocker."
    }

    & $dockerCommand.Source compose -f (Join-Path $repoRoot "docker-compose.yml") up -d db

    if ($LASTEXITCODE -ne 0) {
        throw "Docker could not start the PostgreSQL service."
    }
}

Wait-ForPort -Port 15432 -ServiceName "PostgreSQL"

Start-LocalService `
    -Name "backend" `
    -FilePath $python `
    -ArgumentList @(
        "-m",
        "uvicorn",
        "backend.app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000"
    ) `
    -WorkingDirectory $repoRoot `
    -Port 8000

Start-LocalService `
    -Name "frontend" `
    -FilePath $npmCommand.Source `
    -ArgumentList @(
        "run",
        "dev",
        "--",
        "--host",
        "127.0.0.1"
    ) `
    -WorkingDirectory $frontendRoot `
    -Port 5173

Write-Host ""
Write-Host "WhichMovieItIs is ready."
Write-Host "Frontend: http://127.0.0.1:5173"
Write-Host "Backend:  http://127.0.0.1:8000"
Write-Host "Logs:     $runtimeDirectory"
