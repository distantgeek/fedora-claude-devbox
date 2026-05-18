#!/usr/bin/env python3
"""
PostToolUse hook — SAST scan after Write/Edit operations on code files.

Runs language-appropriate static analysis and appends findings to tool
output so Claude sees them immediately and can remediate before commit.

  Python  → bandit  (OWASP-aligned, CWE-mapped)       per file
  Rust    → cargo audit (advisory DB)                  once per session per project
  TS/JS   → npm audit (--audit-level=high)             once per session per project

When a required tool is not installed, emits an install suggestion rather
than failing silently.
"""

import sys
import json
import os
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from patterns import load_hook_input

MARKER_DIR = '/tmp/claude_sast_markers'

CODE_EXTENSIONS = {
    '.py':  'python',
    '.rs':  'rust',
    '.ts':  'typescript',
    '.tsx': 'typescript',
    '.js':  'javascript',
    '.jsx': 'javascript',
}

INSTALL_HINTS = {
    'bandit': (
        "bandit is the OWASP-recommended Python SAST scanner.\n"
        "  Install (project dev dep): uv add --dev bandit\n"
        "  Install (global):          uv tool install bandit\n"
        "  One-off (no install):      uvx bandit <file>"
    ),
    'cargo-audit': (
        "cargo-audit scans Rust dependencies against the RustSec advisory database.\n"
        "  Install (global, one-time): cargo install cargo-audit\n"
        "  Docs: https://github.com/rustsec/rustsec"
    ),
    'npm': (
        "npm audit is bundled with npm (part of Node.js).\n"
        "  Install Node via fnm: fnm install --lts && fnm use lts-latest"
    ),
}

# npm audit --parseable columns: action|module|resolve|path|more
# non-zero exit = vulnerabilities at or above --audit-level threshold


def session_key() -> str:
    return str(os.getppid())


def find_project_root(filepath: str, markers: list) -> str | None:
    d = os.path.dirname(os.path.abspath(filepath))
    while d != '/':
        if any(os.path.exists(os.path.join(d, m)) for m in markers):
            return d
        d = os.path.dirname(d)
    return None


def run_bandit(filepath: str) -> tuple[str, str]:
    """Return (findings, install_hint). Exactly one will be non-empty, or both empty (clean)."""
    try:
        result = subprocess.run(
            ['bandit', '-f', 'txt', '-ll', '-q', filepath],
            capture_output=True, text=True, timeout=30,
        )
        out = result.stdout.strip()
        if not out or 'No issues identified' in out:
            return '', ''
        keep = ('Issue:', 'Severity:', 'CWE:', 'Location:', 'More Info:')
        lines = [l for l in out.splitlines() if any(k in l for k in keep)]
        return ('\n'.join(lines) if lines else ''), ''
    except FileNotFoundError:
        return '', INSTALL_HINTS['bandit']
    except subprocess.TimeoutExpired:
        return '', ''


def run_once(
    marker_name: str, cmd: list, cwd: str, install_hint: str = ''
) -> tuple[str, str]:
    """Run cmd once per session per project. Return (findings, install_hint)."""
    os.makedirs(MARKER_DIR, exist_ok=True)
    marker = os.path.join(MARKER_DIR, marker_name)
    if os.path.exists(marker):
        return '', ''
    open(marker, 'w').close()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, cwd=cwd,
        )
        if result.returncode == 0:
            return '', ''
        return (result.stdout or result.stderr or '').strip()[:1500], ''
    except FileNotFoundError:
        return '', install_hint
    except subprocess.TimeoutExpired:
        return '', ''


def build_sast_block(language: str, filename: str, findings: str, hint: str) -> str:
    if hint:
        return (
            f"\n\n[SAST:{language.upper()}:{filename} — TOOL NOT INSTALLED]\n"
            f"{hint}\n"
            "[/SAST — install the tool above to enable automatic scanning]"
        )
    return (
        f"\n\n[SAST:{language.upper()}:{filename}]\n"
        f"{findings}\n"
        "[/SAST — remediate HIGH/MEDIUM findings before committing]"
    )


def main():
    data = load_hook_input()
    if not data:
        sys.exit(0)

    if data.get('tool_name') not in ('Write', 'Edit', 'MultiEdit'):
        sys.exit(0)

    tool_input = data.get('tool_input', {})
    filepath = tool_input.get('file_path') or tool_input.get('path', '')
    if not filepath or not os.path.exists(filepath):
        sys.exit(0)

    ext = os.path.splitext(filepath)[1].lower()
    language = CODE_EXTENSIONS.get(ext)
    if not language:
        sys.exit(0)

    sk = session_key()
    findings, hint = '', ''

    if language == 'python':
        findings, hint = run_bandit(filepath)

    elif language == 'rust':
        root = find_project_root(filepath, ['Cargo.lock', 'Cargo.toml'])
        if root:
            findings, hint = run_once(
                f'cargo_{sk}_{abs(hash(root))}',
                ['cargo', 'audit', '--quiet'],
                root,
                install_hint=INSTALL_HINTS['cargo-audit'],
            )

    elif language in ('typescript', 'javascript'):
        root = find_project_root(
            filepath, ['package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'package.json']
        )
        if root:
            # Layer 1: known CVE scan
            findings, hint = run_once(
                f'npm_audit_{sk}_{abs(hash(root))}',
                ['npm', 'audit', '--audit-level=high', '--parseable'],
                root,
                install_hint=INSTALL_HINTS['npm'],
            )
            # Layer 2: registry signature / provenance check (requires node_modules)
            nm = os.path.join(root, 'node_modules')
            if os.path.isdir(nm):
                sig_out, _ = run_once(
                    f'npm_sigs_{sk}_{abs(hash(root))}',
                    ['npm', 'audit', 'signatures'],
                    root,
                )
                if sig_out and 'verified' not in sig_out.lower():
                    sig_block = f'\n\n[npm audit signatures]\n{sig_out}'
                    findings = (findings + sig_block).strip()

    if not findings and not hint:
        sys.exit(0)

    original = data.get('tool_output', '')
    if not isinstance(original, str):
        original = json.dumps(original)

    sast_block = build_sast_block(language, os.path.basename(filepath), findings, hint)
    print(json.dumps({"tool_output": original + sast_block}), flush=True)


if __name__ == '__main__':
    main()
