# Downloads

This page explains the three supported ways to obtain Aegis Community.

## Latest release

The preferred download is the latest GitHub Release:

[Open the latest release](https://github.com/SxnapXSN/aegis-community-preview/releases/latest)

Each public release is intended to contain:

- a Python wheel (.whl) for a direct local install;
- a source distribution (.tar.gz) for packaging and inspection;
- SHA256SUMS.txt for integrity verification;
- the GitHub-generated source archive for the tagged commit.

For Community 1.1.1, the direct wheel link is:

[Download aegis_community_preview-1.1.1-py3-none-any.whl](https://github.com/SxnapXSN/aegis-community-preview/releases/download/v1.1.1/aegis_community_preview-1.1.1-py3-none-any.whl)

Install it with:

~~~powershell
python -m pip install --no-deps .\aegis_community_preview-1.1.1-py3-none-any.whl
aegis-community preflight
~~~

## Source checkout

~~~powershell
git clone https://github.com/SxnapXSN/aegis-community-preview.git
Set-Location aegis-community-preview
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1
~~~

This is the best option for contributors and users who want to inspect or
modify the public source.

## Source ZIP

[Download the v1.1.1 source ZIP](https://github.com/SxnapXSN/aegis-community-preview/archive/refs/tags/v1.1.1.zip)

Extract it, open PowerShell in the extracted folder, and run:

~~~powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1
~~~

## Integrity

When verifying a release asset, download SHA256SUMS.txt from the same
release and compare it with a local hash:

~~~powershell
Get-FileHash .\aegis_community_preview-1.1.1-py3-none-any.whl -Algorithm SHA256
~~~

The release workflow builds artifacts from the tagged source only after the
version in pyproject.toml matches the tag. It also reruns the unit suite and
the public-boundary checker before publishing the assets.

## Troubleshooting

- Python 3.10 or newer is required.
- The package has no required runtime dependencies.
- OCR for scanned documents is optional and must be configured locally.
- Legacy binary .doc, .xls, and .ppt files are not parsed directly.
- The wheel does not contain private Stable code, model weights, or an MD
  backend.
