"""Redaction helpers for values that may leave the local Community runtime."""

from __future__ import annotations

import re


_SECRET_ASSIGNMENT = re.compile(
    r"(?is)(\b(?:api[_-]?key|secret|access[_-]?token|password)\b\s*[:=]\s*)"
    r"([\"'][^\"'\r\n]{4,}[\"']|[^\s,;}]+)"
)
_URL = re.compile(r"(?i)\b(?:https?|wss?)://[^\s<>\"']+")
_WINDOWS_PATH = re.compile(
    r"(?i)(?:[a-z]:[\\/](?![\\/])|\\\\[^\\/\s]+[\\/]+)[^<>\r\n\"']*"
)
_UNIX_PATH = re.compile(r"(?i)(?<![\w])/(?:home|users|mnt|tmp|var|opt|workspace)/[^\s<>\"']*")
_IPV4 = re.compile(
    r"(?<![\w.])(?:25[0-5]|2[0-4]\d|1?\d?\d)"
    r"(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}(?::\d{1,5})?(?![\w.])"
)
_LOOPBACK_HOST = re.compile(r"(?i)(?<![\w.-])localhost(?::\d{1,5})?(?![\w.-])")


def redact_public_text(value: str) -> str:
    """Remove local paths, network locations, and credential-like values."""

    redacted = _SECRET_ASSIGNMENT.sub(r"\1[redacted]", value)
    redacted = _URL.sub("[redacted-url]", redacted)
    redacted = _WINDOWS_PATH.sub("[redacted-path]", redacted)
    redacted = _UNIX_PATH.sub("[redacted-path]", redacted)
    redacted = _IPV4.sub("[redacted-address]", redacted)
    return _LOOPBACK_HOST.sub("[redacted-host]", redacted)
