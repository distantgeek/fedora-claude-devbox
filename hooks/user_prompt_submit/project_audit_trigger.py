#!/usr/bin/env python3
"""
UserPromptSubmit hook — triggers a project audit once per session.

When Claude Code starts in a git repository, injects an additionalContext
notice instructing Claude to run code-reviewer and security-reviewer agents
before beginning any code work. Fires exactly once per session (keyed by
parent PID — each Claude Code session is a separate process).
"""

import sys
import json
import os
import subprocess

MARKER_DIR = '/tmp/claude_audit_markers'


def get_branch() -> str:
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return ''


def main():
    raw = sys.stdin.read().strip()
    try:
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        data = {}

    # Only trigger when session is inside a git repository
    if not os.path.exists('.git'):
        sys.exit(0)

    # One trigger per Claude Code session (parent PID is stable per session)
    sk = str(os.getppid())
    os.makedirs(MARKER_DIR, exist_ok=True)
    marker = os.path.join(MARKER_DIR, f'audit_{sk}')
    if os.path.exists(marker):
        sys.exit(0)
    open(marker, 'w').close()

    project = os.path.basename(os.getcwd())
    branch = get_branch()
    branch_info = f', branch: {branch}' if branch else ''

    notice = (
        f"[project_audit_trigger] Session opened on git repo '{project}'{branch_info}. "
        "Standing policy (security-frameworks.md): before any code modifications, "
        "spawn the code-reviewer agent (against git diff or key files) and the "
        "security-reviewer agent to audit current codebase state. "
        "Report findings to the user first, then proceed with their request."
    )

    print(json.dumps({"additionalContext": notice}), flush=True)


if __name__ == '__main__':
    main()
