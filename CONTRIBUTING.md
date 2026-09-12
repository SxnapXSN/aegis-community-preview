# Contributing

Community is intentionally bounded. Contributions must keep the public
contract useful without exposing private Aegis or machine-specific data.

Before opening a pull request:

1. Keep changes inside the public allow-list in `COMMUNITY_SCOPE.md`.
2. Do not add credentials, environment files, model weights, model caches,
   telemetry, private endpoints, or private Stable material.
3. Keep MCP tools plan-only unless the public safety contract is updated and
   tested first.
4. Run `python -m unittest discover -s tests -v`.
5. Run `python scripts/verify_preview_boundary.py .`.
6. Review the staged file list manually before publication.

Contributions are submitted under the Apache-2.0 license. Third-party MD
backends retain their own licenses.
