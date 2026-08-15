# Aegis Community Preview

This is a deliberately small, local-only technical preview. It validates a
task envelope and produces a conservative execution brief from JSON input.

It is not the Aegis Stable engine and is not a source mirror of it. The
private Aegis Stable engine remains separate and proprietary.

## Included

- A documented JSON task contract.
- Input validation for task identifiers, objectives, risk levels, and allowed
  actions.
- A conservative planner: high-risk tasks always require human review.
- Standard-library-only tests and a preview boundary checker.

## Deliberately Not Included

- Agent execution, autonomous orchestration, providers, model routing, or
  background workers.
- Network access, telemetry, credentials, customer data, or persistent
  storage.
- Private Aegis Stable modules, policies, licensing, operations, or runtime
  artifacts.

## Run Locally

```powershell
python -m aegis_community.cli --input examples/sample_task.json
python -m unittest discover -s tests -v
python scripts/verify_preview_boundary.py .
```

The CLI writes a JSON brief to standard output and makes no network requests.

## Preview Status

This directory is a local release candidate for the separate public preview
repository. It is licensed under Apache-2.0. A public push still requires a
final staged-file review and confirmation that the historical private-engine
telemetry credential has been revoked.
