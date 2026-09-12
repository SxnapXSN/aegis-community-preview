param(
    [ValidateSet('auto', 'codex', 'claude', 'both')]
    [string]$Client = 'auto',
    [switch]$NoBackup
)

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

function Backup-Config {
    param([string]$ConfigPath)

    if ($NoBackup -or -not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
        return
    }

    $backupPath = "$ConfigPath.aegis-community.bak"
    Copy-Item -LiteralPath $ConfigPath -Destination $backupPath -Force
}

function Invoke-Client {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string[]]$Arguments
    )

    if ((Invoke-NativeSilently $Name $Arguments) -ne 0) {
        throw "Could not configure $Name."
    }
}

function Has-Command {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Connect-Codex {
    if (-not (Has-Command 'codex')) {
        throw 'Codex CLI was not found.'
    }

    $codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
    Backup-Config (Join-Path $codexHome 'config.toml')

    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $existing = (& codex mcp get aegis-community 2>&1 | Out-String).Trim()
    $getExitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousPreference
    if ($getExitCode -eq 0) {
        if ($existing -match 'aegis_community\.mcp_server') {
            Write-Host 'Codex: already connected.' -ForegroundColor Green
            return
        }
        throw 'Codex already has an Aegis Community entry with a different configuration.'
    }

    Invoke-Client 'codex' @('mcp', 'add', 'aegis-community', '--', 'python', '-m', 'aegis_community.mcp_server')
    Write-Host 'Codex: connected.' -ForegroundColor Green
}

function Connect-Claude {
    if (-not (Has-Command 'claude')) {
        throw 'Claude CLI was not found.'
    }

    Backup-Config (Join-Path $HOME '.claude.json')

    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $existing = (& claude mcp get aegis-community 2>&1 | Out-String).Trim()
    $getExitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousPreference
    if ($getExitCode -eq 0) {
        if ($existing -match 'aegis_community\.mcp_server') {
            Write-Host 'Claude: already connected.' -ForegroundColor Green
            return
        }
        throw 'Claude already has an Aegis Community entry with a different configuration.'
    }

    Invoke-Client 'claude' @('mcp', 'add', '--scope', 'user', 'aegis-community', '--', 'python', '-m', 'aegis_community.mcp_server')
    Write-Host 'Claude: connected.' -ForegroundColor Green
}

$selected = switch ($Client) {
    'auto' {
        @('codex', 'claude') | Where-Object { Has-Command $_ }
    }
    'both' { @('codex', 'claude') }
    default { @($Client) }
}

if (-not $selected -or $selected.Count -eq 0) {
    throw 'No supported AI client CLI was found.'
}

foreach ($name in $selected) {
    if ($name -eq 'codex') {
        Connect-Codex
    } else {
        Connect-Claude
    }
}

Write-Host 'Aegis Community client connection completed.' -ForegroundColor Cyan
