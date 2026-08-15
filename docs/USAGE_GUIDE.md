# Usage Guide

## 1. Get The Preview

Choose one of these local installation methods.

### Download A Source Bundle

1. Download the [v0.1.1 source ZIP](https://github.com/SxnapXSN/aegis-community-preview/archive/refs/tags/v0.1.1.zip).
2. Extract it to a local folder.
3. Open PowerShell in the extracted folder.

### Clone With Git

```powershell
git clone https://github.com/SxnapXSN/aegis-community-preview.git
cd aegis-community-preview
```

## 2. Install

Python 3.10 or newer is required. The preview has no runtime dependencies
outside the Python standard library.

```powershell
python -m pip install -e .
```

## 3. Run The Included Example

```powershell
python -m aegis_community.cli --input examples/sample_task.json
```

The command prints a JSON execution brief. It does not run the listed actions.

## 4. Create A Task File

Create a JSON file such as `my-task.json`:

```json
{
  "task_id": "docs-001",
  "title": "Draft a guide",
  "objective": "Prepare a local documentation outline.",
  "risk_level": "low",
  "allowed_actions": ["draft_outline", "request_human_review"]
}
```

Then run it:

```powershell
python -m aegis_community.cli --input my-task.json
```

Risk levels are `low`, `medium`, and `high`. A `high` task always returns
`requires_human_review` and exposes no enabled actions.

## 5. Verify A Local Copy

Run both commands before contributing or sharing a modified copy:

```powershell
python -m unittest discover -s tests -v
python scripts/verify_preview_boundary.py .
```

The boundary check rejects files outside the public allow-list and common
credential file types. It is a release aid, not a replacement for human review.

## Important Limits

This preview is not the private Aegis Stable engine. It does not include model
providers, networking, autonomous execution, persistent storage, telemetry,
or credentials. Do not use it for security-critical or production decisions.
