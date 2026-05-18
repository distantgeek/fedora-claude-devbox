#!/usr/bin/env python3
"""
PreToolUse hook — verify docs and context are current before git commit or push.

Fires once per session on the first git commit or git push. Blocks with a
targeted checklist so Claude can update documentation before proceeding.
The check fires exactly once per session (PPID-keyed marker). Setting the
marker before the block ensures the retry after docs are updated is allowed.

Skips: git commit --amend --no-edit (no new content).
"""

import sys
import json
import os
import re
import subprocess

MARKER_DIR = '/tmp/claude_commit_markers'

GIT_COMMIT    = re.compile(r'\bgit\s+commit\b')
GIT_PUSH      = re.compile(r'\bgit\s+push\b')
AMEND_NO_EDIT = re.compile(r'git\s+commit\b.*--amend.*--no-edit|git\s+commit\b.*--no-edit.*--amend')


def get_staged_files() -> list:
    try:
        r = subprocess.run(
            ['git', 'diff', '--cached', '--name-only'],
            capture_output=True, text=True, timeout=5,
        )
        return [f.strip() for f in r.stdout.splitlines() if f.strip()]
    except Exception:
        return []


def build_checklist(staged: list) -> list:
    """Return a targeted list of docs to verify based on what's staged."""
    checks = []

    any_hooks  = any(f.startswith('hooks/')   for f in staged)
    any_build  = any(f.startswith('build/')   or f == 'Makefile' for f in staged)
    any_config = any(f.startswith('config/')  for f in staged)
    any_ansible = any(f.startswith('ansible/') for f in staged)

    checks.append("README.md — current feature list, architecture, What's Baked In table")
    checks.append("CLAUDE.md — project context: layer order, checklist, installed tools")

    if any_hooks:
        checks.append("docs/HOOKS.md — hook descriptions, scan matrix, wiring JSON, permissions table")
    if any_build:
        checks.append("docs/BUILDING.md — layer design table, known quirks, tool versions")
    if any_config or any_ansible:
        checks.append("README.md → Security Model and/or Quick Start — reflect config/tooling changes")

    checks.append("DEVBOX_INSTALLED.md — log any ad hoc installs made this session")
    checks.append("`git diff --staged` — no secrets, no unintended files, no debug artifacts")

    return checks


def main():
    raw = sys.stdin.read().strip()
    try:
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        data = {}

    tool_name  = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name != "Bash":
        print(json.dumps({"action": "allow"}), flush=True)
        return

    command = tool_input.get("command", "")

    is_commit = bool(GIT_COMMIT.search(command))
    is_push   = bool(GIT_PUSH.search(command))

    if not (is_commit or is_push):
        print(json.dumps({"action": "allow"}), flush=True)
        return

    # --amend --no-edit rewrites the previous commit message without new content
    if AMEND_NO_EDIT.search(command):
        print(json.dumps({"action": "allow"}), flush=True)
        return

    sk = str(os.getppid())
    os.makedirs(MARKER_DIR, exist_ok=True)
    marker = os.path.join(MARKER_DIR, f'docs_check_{sk}')

    if os.path.exists(marker):
        print(json.dumps({"action": "allow"}), flush=True)
        return

    # Set marker BEFORE blocking — the retry after docs are updated will be allowed
    open(marker, 'w').close()

    staged   = get_staged_files()
    checklist = build_checklist(staged)

    if staged:
        n = len(staged)
        preview = ', '.join(staged[:4]) + (f' (+{n - 4} more)' if n > 4 else '')
        staged_line = f"Staged ({n} file{'s' if n != 1 else ''}): {preview}"
    else:
        staged_line = "No staged files detected (push without new commit?)"

    action_label = "commit" if is_commit else "push"
    items = '\n'.join(f"  {i + 1}. {c}" for i, c in enumerate(checklist))

    message = (
        f"[pre_commit_docs_check] Docs and context check before {action_label}.\n"
        f"{staged_line}\n\n"
        f"Verify and update as needed before committing:\n"
        f"{items}\n\n"
        "Stage any updates, then re-run the commit command."
    )

    print(json.dumps({"action": "block", "message": message}), flush=True)


if __name__ == '__main__':
    main()
