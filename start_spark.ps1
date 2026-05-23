$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'

function Get-EnvValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [string]$Default = ''
    )

    $currentValue = [Environment]::GetEnvironmentVariable($Name)
    if ($currentValue) {
        return $currentValue
    }

    $envFile = Join-Path $PSScriptRoot '.env'
    if (Test-Path $envFile) {
        foreach ($line in Get-Content -LiteralPath $envFile) {
            if ($line -match "^\s*$([regex]::Escape($Name))\s*=\s*(.*)$") {
                return $Matches[1].Trim().Trim('"').Trim("'")
            }
        }
    }

    return $Default
}

if (-not (Test-Path $venvPython)) {
    throw "Virtual environment Python not found at $venvPython"
}

$env:PYTHONUNBUFFERED = '1'
$env:SPARK_HOST = '0.0.0.0'
$env:SPARK_PORT = '8000'
$env:SPARK_ACCESS_TOKEN = Get-EnvValue -Name 'SPARK_ACCESS_TOKEN' -Default $env:SPARK_ACCESS_TOKEN
$env:SPARK_TOKEN = Get-EnvValue -Name 'SPARK_TOKEN' -Default $env:SPARK_TOKEN

if (-not $env:SPARK_ACCESS_TOKEN -or $env:SPARK_ACCESS_TOKEN -eq 'change-this-token') {
    Write-Warning 'SPARK_ACCESS_TOKEN is not set to a strong secret. Remote access should not be exposed until you configure one.'
}

$serverArgs = @('-m', 'uvicorn', 'api.server:app', '--host', '0.0.0.0', '--port', '8000')
$serverLog = Join-Path $PSScriptRoot 'spark-server.log'
$serverErrLog = Join-Path $PSScriptRoot 'spark-server.err.log'

Start-Process -FilePath $venvPython -ArgumentList $serverArgs -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput $serverLog -RedirectStandardError $serverErrLog | Out-Null

Start-Sleep -Seconds 3

$cloudflaredToken = Get-EnvValue -Name 'CLOUDFLARED_TOKEN'
if ($cloudflaredToken) {
    $tunnelLog = Join-Path $PSScriptRoot 'spark-tunnel.log'
    $tunnelErrLog = Join-Path $PSScriptRoot 'spark-tunnel.err.log'
    $tunnelArgs = @('tunnel', 'run', '--token', $cloudflaredToken)
    Start-Process -FilePath 'cloudflared' -ArgumentList $tunnelArgs -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput $tunnelLog -RedirectStandardError $tunnelErrLog | Out-Null
}
elseif (Test-Path (Join-Path $PSScriptRoot 'cloudflared-config.yml')) {
    $cloudflaredConfig = Join-Path $PSScriptRoot 'cloudflared-config.yml'
    $configText = Get-Content -LiteralPath $cloudflaredConfig -Raw
    if ($configText -match 'spark\.yourdomain\.example' -or $configText -match 'yourdomain\.example') {
        Write-Warning 'cloudflared-config.yml still contains a placeholder hostname. Update it before relying on public access.'
    }
    else {
        $tunnelLog = Join-Path $PSScriptRoot 'spark-tunnel.log'
        $tunnelErrLog = Join-Path $PSScriptRoot 'spark-tunnel.err.log'
        Start-Process -FilePath 'cloudflared' -ArgumentList @('tunnel', '--config', $cloudflaredConfig, 'run') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput $tunnelLog -RedirectStandardError $tunnelErrLog | Out-Null
    }
}

Write-Host 'SPARK server and tunnel start sequence launched.'
