[CmdletBinding()]
param(
    [string]$Version,
    [switch]$SkipHash
)

$ErrorActionPreference = 'Stop'

$repository = 'SxnapXSN/aegis-community-preview'
$apiHeaders = @{
    Accept = 'application/vnd.github+json'
    'User-Agent' = 'Aegis-Community-Installer'
}
$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ('aegis-community-install-' + [guid]::NewGuid().ToString('N'))
$temporaryRoot = [IO.Path]::GetFullPath($tempRoot)
$tempBase = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())

function Invoke-Python {
    param(
        [Parameter(Mandatory)][string[]]$Arguments
    )

    if ($script:PythonCommand -eq 'py') {
        & py -3 @Arguments
    } else {
        & python @Arguments
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code $LASTEXITCODE."
    }
}

try {
    New-Item -ItemType Directory -Path $temporaryRoot -Force | Out-Null

    $releaseUrl = if ([string]::IsNullOrWhiteSpace($Version)) {
        "https://api.github.com/repos/$repository/releases/latest"
    } else {
        $tag = 'v' + $Version.TrimStart('v', 'V')
        "https://api.github.com/repos/$repository/releases/tags/$tag"
    }

    Write-Host 'Finding the latest Aegis Community release...' -ForegroundColor Cyan
    $release = Invoke-RestMethod -Uri $releaseUrl -Headers $apiHeaders
    if ($release.draft) {
        throw 'The selected release is still a draft.'
    }

    $wheel = @($release.assets | Where-Object { $_.name -like '*.whl' } | Select-Object -First 1)
    $checksums = @($release.assets | Where-Object { $_.name -eq 'SHA256SUMS.txt' } | Select-Object -First 1)
    if ($null -eq $wheel -or $wheel.Count -eq 0) {
        throw 'The selected release has no wheel asset.'
    }

    $wheelPath = Join-Path $temporaryRoot $wheel.name
    Invoke-WebRequest -Uri $wheel.browser_download_url -OutFile $wheelPath -UseBasicParsing

    if (-not $SkipHash) {
        if ($null -eq $checksums -or $checksums.Count -eq 0) {
            throw 'The selected release has no SHA256SUMS.txt asset.'
        }

        $checksumsPath = Join-Path $temporaryRoot 'SHA256SUMS.txt'
        Invoke-WebRequest -Uri $checksums.browser_download_url -OutFile $checksumsPath -UseBasicParsing
        $escapedName = [regex]::Escape($wheel.name)
        $checksumLine = Get-Content -LiteralPath $checksumsPath |
            Where-Object { $_ -match ("(?i)^\s*([0-9a-f]{64})\s+\*?(?:.*[\\/])?" + $escapedName + "\s*$") } |
            Select-Object -First 1
        if ([string]::IsNullOrWhiteSpace($checksumLine)) {
            throw "No checksum was found for $($wheel.name)."
        }

        $expectedHash = ($checksumLine -split '\s+')[0].ToLowerInvariant()
        $actualHash = (Get-FileHash -LiteralPath $wheelPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actualHash -ne $expectedHash) {
            throw 'The downloaded wheel failed SHA-256 verification.'
        }
        Write-Host 'SHA-256 verification passed.' -ForegroundColor Green
    } else {
        Write-Warning 'SHA-256 verification was skipped by request.'
    }

    $script:PythonCommand = if (Get-Command py -ErrorAction SilentlyContinue) {
        'py'
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        'python'
    } else {
        throw 'Python 3.10 or newer was not found. Install Python, then run this installer again.'
    }

    if ($script:PythonCommand -eq 'py') {
        $pythonVersion = (& py -3 --version 2>$null)
        & py -3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' 2>$null
    } else {
        $pythonVersion = (& python --version 2>$null)
        & python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' 2>$null
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Python 3.10 or newer is required. Detected: $pythonVersion"
    }

    Write-Host "Installing $($release.tag_name)..." -ForegroundColor Cyan
    Invoke-Python @('-m', 'pip', 'install', '--upgrade', '--no-deps', $wheelPath)

    Write-Host 'Running Aegis Community preflight...' -ForegroundColor Cyan
    Invoke-Python @('-m', 'aegis_community.cli', 'preflight', '--format', 'pretty')
    Write-Host "Aegis Community $($release.tag_name) is ready." -ForegroundColor Green
} finally {
    if ($temporaryRoot.StartsWith($tempBase, [StringComparison]::OrdinalIgnoreCase) -and
        (Test-Path -LiteralPath $temporaryRoot)) {
        Remove-Item -LiteralPath $temporaryRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
