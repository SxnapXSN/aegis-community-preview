# Contributing

This repository is a deliberately limited technical preview.

Before opening a pull request:

1. Keep changes inside the public allow-list in `COMMUNITY_SCOPE.md`.
2. Do not add credentials, `.env` files, telemetry, network access, agent
   execution, provider integrations, or private Aegis Stable code.
3. Run `python -m unittest discover -s tests -v`.
4. Run `python scripts/verify_preview_boundary.py .`.

Contributions are submitted under the Apache-2.0 license.
