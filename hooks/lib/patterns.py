#!/usr/bin/env python3
"""
Shared patterns and utilities for Claude Code hooks.
Loaded by pre_tool_use and post_tool_use hooks.
"""

import re
import os
import json
from pathlib import Path


# ---------------------------------------------------------------------------
# Compiled sensitive data patterns
# ---------------------------------------------------------------------------

PATTERNS = {
    "ssh_private_key": re.compile(
        r"-----BEGIN (?:RSA|EC|DSA|OPENSSH|PGP) PRIVATE KEY-----.*?-----END [A-Z ]+ PRIVATE KEY-----",
        re.DOTALL,
    ),
    "api_token": re.compile(
        r"(?i)(?:api[_\-]?key|api[_\-]?token|access[_\-]?token|bearer)['\"]?\s*[:=]\s*['\"]?([A-Za-z0-9\-_\.]{20,})",
    ),
    "anthropic_key": re.compile(r"sk-ant-[A-Za-z0-9\-_]{20,}"),
    "openai_key": re.compile(r"sk-[A-Za-z0-9]{20,}"),
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "aws_secret_key": re.compile(
        r"(?i)aws[_\-]?secret[_\-]?(?:access[_\-]?)?key['\"]?\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{40})"
    ),
    "generic_password": re.compile(
        r"(?i)password['\"]?\s*[:=]\s*['\"]?([^\s'\"]{8,})"
    ),
    "generic_secret": re.compile(
        r"(?i)secret['\"]?\s*[:=]\s*['\"]?([^\s'\"]{8,})"
    ),
    "jwt_token": re.compile(
        r"eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+"
    ),
    "private_key_material": re.compile(
        r"[A-Za-z0-9+/]{40,}={0,2}(?:\n[A-Za-z0-9+/]{40,}={0,2}){3,}"
    ),
    "proxmox_token": re.compile(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    ),
}


# ---------------------------------------------------------------------------
# Sensitive path patterns — never read, write, or expose
# ---------------------------------------------------------------------------

SENSITIVE_PATH_PATTERNS = [
    re.compile(r"/etc/soc/credentials/"),
    re.compile(r"\.ssh/"),
    re.compile(r"\.hermes/\.env"),
    re.compile(r"\.hermes/secrets/"),
    re.compile(r"\.config/anthropic/"),
    re.compile(r"\.(env)(\.|$)"),
    re.compile(r"\.(key|pem|p12|pfx)$"),
    re.compile(r"_(rsa|ed25519|ecdsa|dsa)$"),
    re.compile(r"credentials$"),
    re.compile(r"secrets$"),
]


# ---------------------------------------------------------------------------
# Network allowlist
# ---------------------------------------------------------------------------

ALLOWED_SSH_PATTERNS = [
    re.compile(r"^192\.168\.\d{1,3}\.\d{1,3}$"),
    re.compile(r"^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$"),
    re.compile(r"github\.com"),
    re.compile(r"ghcr\.io"),
    re.compile(r"quay\.io"),
]


# ---------------------------------------------------------------------------
# Core scrubbing function
# ---------------------------------------------------------------------------

def scrub(text: str) -> tuple[str, list[str]]:
    """
    Scrub sensitive data from text.
    Returns (scrubbed_text, list_of_redaction_tags_applied).
    """
    redactions = []
    result = text

    for label, pattern in PATTERNS.items():
        def replacer(m, label=label):
            redactions.append(f"[REDACTED:{label}]")
            return f"[REDACTED:{label}]"
        result = pattern.sub(replacer, result)

    return result, redactions


def is_sensitive_path(path: str) -> bool:
    """Return True if path matches any sensitive path pattern."""
    for pattern in SENSITIVE_PATH_PATTERNS:
        if pattern.search(path):
            return True
    return False


def is_allowed_ssh_target(host: str) -> bool:
    """Return True if SSH/SCP target is within allowed network ranges."""
    for pattern in ALLOWED_SSH_PATTERNS:
        if pattern.search(host):
            return True
    return False


# ---------------------------------------------------------------------------
# Hook response helpers
# ---------------------------------------------------------------------------

def block(reason: str) -> dict:
    """Return a hook response that blocks the tool call."""
    return {
        "action": "block",
        "message": f"[fedora-claude-devbox security hook] BLOCKED: {reason}",
    }


def allow() -> dict:
    """Return a hook response that allows the tool call."""
    return {"action": "allow"}


def warn(message: str) -> dict:
    """Return a hook response that allows but logs a warning."""
    print(f"[fedora-claude-devbox hook] WARNING: {message}", flush=True)
    return {"action": "allow"}


def load_hook_input() -> dict:
    """Read and parse hook input from stdin."""
    import sys
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    return json.loads(raw)


def write_hook_output(response: dict):
    """Write hook response to stdout."""
    import sys
    print(json.dumps(response), flush=True)
