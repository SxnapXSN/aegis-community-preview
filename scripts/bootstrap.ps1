param([switch]$ConnectClients)

$ErrorActionPreference = 'Stop'

function Invoke-NativeSilently {
    param(
        [Parameter(Mandatory)][string]$Runner,
        [Parameter(Mandatory)][string[]]$RunnerArguments
    )

    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $Runner @RunnerArguments *> $null
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousPreference
    return $exitCode
}

function Install-Community {
    param(
        [Parameter(Mandatory)][string]$Runner,
        [Parameter(Mandatory)][string[]]$RunnerArguments
    )

    if ((Invoke-NativeSilently $Runner $RunnerArguments) -ne 0) {
        throw 'Aegis Community installation failed.'
    }
}

$pythonCommand = Get-Command py -ErrorAction SilentlyContinue
if ($null -ne $pythonCommand) {
    if ((Invoke-NativeSilently 'py' @('-3', '-c', 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)')) -ne 0) {
        throw 'Python 3.10 or newer is required.'
    }
    Install-Community 'py' @('-3', '-m', 'pip', 'install', '--no-deps', '--no-build-isolation', '--editable', '.')
} else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $pythonCommand) {
        throw 'Python 3.10 or newer was not found.'
    }
    if ((Invoke-NativeSilently 'python' @('-c', 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)')) -ne 0) {
        throw 'Python 3.10 or newer is required.'
    }
    Install-Community 'python' @('-m', 'pip', 'install', '--no-deps', '--no-build-isolation', '--editable', '.')
}

Write-Host 'Aegis Community installation completed.' -ForegroundColor Green
Write-Host 'Run: aegis-community preflight' -ForegroundColor Cyan
Write-Host 'Run: aegis-community manifest' -ForegroundColor Cyan

if ($ConnectClients) {
    & (Join-Path $PSScriptRoot 'connect-clients.ps1') -Client auto
}
