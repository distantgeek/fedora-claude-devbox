#!/usr/bin/env python3
"""
PreToolUse hook — enforce security policies before any tool executes.

Blocks:
- Reads/writes to sensitive paths
- SSH/SCP to non-allowlisted hosts
- Destructive commands outside project scope
- Force push to protected branches
- Credential exposure via shell commands
"""

import sys
import json
import re
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from patterns import (
    is_sensitive_path, is_allowed_ssh_target,
    block, allow, warn, load_hook_input, write_hook_output,
    SENSITIVE_PATH_PATTERNS,
)


# ---------------------------------------------------------------------------
# Dangerous command patterns
# ---------------------------------------------------------------------------

FORCE_PUSH_PATTERN = re.compile(r"git\s+push.*(?:--force|-f)\s+(?:origin\s+)?(?:main|master)")
RM_RF_OUTSIDE_PROJECT = re.compile(r"rm\s+-rf?\s+(?!\./)(?!/home/[^/]+/(?:repos?|projects?|src|code))")
SUDO_CREDENTIAL_EXPOSURE = re.compile(r"(?:cat|less|more|head|tail|echo|print)\s+.*(?:\.env|\.key|\.pem|password|secret|credentials)")
ENV_DUMP = re.compile(r"^\s*(?:env|printenv|export)\s*$")

# Matches: npm install pkg, npm i pkg, npm add pkg — but not bare `npm install` (lockfile restore)
NPM_ADD_PACKAGE = re.compile(r"npm\s+(?:install|i|add)\s+(?!.*--save-dev\s*$)(?!-{0,2}\s*$)(?!ci\b)(\S+)")


def check_bash(command: str) -> dict:
    """Validate bash commands before execution."""

    # Credential file exposure
    if SUDO_CREDENTIAL_EXPOSURE.search(command):
        return block(f"Command appears to expose credential file contents: {command[:80]}")

    # Full environment dump (would expose all env vars including API keys)
    if ENV_DUMP.match(command):
        return warn("env/printenv will expose all environment variables including API keys. Output will be scrubbed.")

    # Force push to protected branches
    if FORCE_PUSH_PATTERN.search(command):
        return block("Force push to main/master is not allowed.")

    # rm -rf outside of project-relative paths
    if RM_RF_OUTSIDE_PROJECT.search(command):
        return block("rm -rf outside of project directory requires explicit user confirmation. Ask the user first.")

    # SSH/SCP host validation
    ssh_match = re.search(r"(?:ssh|scp)\s+(?:-[A-Za-z0-9]+\s+)*(?:[A-Za-z0-9._-]+@)?([A-Za-z0-9._-]+)", command)
    if ssh_match:
        host = ssh_match.group(1)
        if not is_allowed_ssh_target(host):
            return block(f"SSH/SCP to '{host}' is outside the allowed network ranges (192.168.x.x, 10.x.x.x, github.com, ghcr.io, quay.io).")

    # curl/wget to external hosts (warn but allow — scrubber handles output)
    if re.search(r"(?:curl|wget)\s+", command):
        return warn("Network request detected. Output will be scrubbed for sensitive data.")

    # New npm package installs — prompt for Socket screening
    npm_match = NPM_ADD_PACKAGE.search(command)
    if npm_match:
        pkg = npm_match.group(1)
        return warn(
            f"npm install detected for '{pkg}'. "
            "Screen with Socket before installing: "
            f"`socket npm install {pkg}` "
            "(catches supply chain attacks, typosquatting, and behavioral anomalies "
            "that npm audit misses). Proceeding with original command."
        )

    return allow()


def check_file_operation(tool_name: str, path: str) -> dict:
    """Validate file read/write/edit operations."""
    if not path:
        return allow()

    if is_sensitive_path(path):
        return block(
            f"Path '{path}' matches sensitive path policy. "
            "If you need data from this file, ask the user to provide it "
            "via environment variable or explicit input."
        )

    return allow()


def main():
    data = load_hook_input()
    if not data:
        write_hook_output(allow())
        return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        result = check_bash(command)

    elif tool_name in ("Read", "Write", "Edit", "MultiEdit"):
        path = tool_input.get("file_path", tool_input.get("path", ""))
        result = check_file_operation(tool_name, path)

    elif tool_name == "WebFetch":
        url = tool_input.get("url", "")
        # Allow fetching but warn; scrubber handles output
        result = warn(f"WebFetch to {url} — output will be scrubbed.")

    else:
        result = allow()

    write_hook_output(result)


if __name__ == "__main__":
    main()
