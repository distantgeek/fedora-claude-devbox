# Security Hook Architecture

## Why Hooks Instead of settings.json

`settings.json` deny rules in Claude Code are **not a reliable security boundary.**
As of April 2026, there are multiple open upstream bugs where deny rules are
inconsistently enforced — rules that should block operations sometimes don't,
depending on how the tool call is constructed.

This project uses a hook-based enforcement model instead:

```
User prompt submitted
        │
        ▼
hooks/user_prompt_submit/project_audit_trigger.py   ← injects session-start audit
        │
        ▼
Tool call requested
        │
        ▼
hooks/pre_tool_use/enforce_permissions.py           ← blocks before execution
        │ (allowed)
        ▼
Tool executes
        │
        ▼
hooks/post_tool_use/scrub_output.py                 ← scrubs credentials
hooks/post_tool_use/sast_scan.py                    ← appends SAST findings
        │
        ▼
Output enters Claude Code context window
```

Hooks run as Python scripts invoked by Claude Code's hook runner. They read the
tool call as JSON from stdin and write a response to stdout. A `block` response
prevents execution entirely. The hook runner is part of Claude Code itself — it
cannot be bypassed by prompt injection.

`settings.json` is kept in this repo for **behavioral guidance and allow-list
documentation only** — it helps Claude Code make better default choices but is
not relied upon for security.

---

## Hook Wiring

Hooks are registered in `config/settings.json` under the `hooks` key. Each event
type maps to an ordered list of matchers and commands:

```json
"hooks": {
  "UserPromptSubmit": [
    { "matcher": ".*", "hooks": [{ "type": "command", "command": "python3 ~/.claude/hooks/user_prompt_submit/project_audit_trigger.py", "timeout": 10 }] }
  ],
  "PreToolUse": [
    { "matcher": ".*", "hooks": [{ "type": "command", "command": "python3 ~/.claude/hooks/pre_tool_use/enforce_permissions.py", "timeout": 10 }] }
  ],
  "PostToolUse": [
    { "matcher": ".*",              "hooks": [{ "type": "command", "command": "python3 ~/.claude/hooks/post_tool_use/scrub_output.py", "timeout": 10 }] },
    { "matcher": "Write|Edit|MultiEdit", "hooks": [{ "type": "command", "command": "python3 ~/.claude/hooks/post_tool_use/sast_scan.py",    "timeout": 90 }] }
  ]
}
```

PostToolUse hooks run in order: `scrub_output.py` first (all tools), then
`sast_scan.py` (Write/Edit/MultiEdit only). The 90-second timeout on `sast_scan.py`
accommodates `cargo audit` and `npm audit` network fetches.

---

## UserPromptSubmit Hook: `project_audit_trigger.py`

**Location:** `hooks/user_prompt_submit/project_audit_trigger.py`

Fires once per Claude Code session when the working directory contains a `.git`
repository. Injects an `additionalContext` notice instructing Claude to run the
`code-reviewer` and `security-reviewer` agents before beginning any code work.

### Session Deduplication

Uses `/tmp/claude_audit_markers/audit_<ppid>` as a session marker — the parent
PID is stable for the lifetime of a Claude Code session. Subsequent prompts in
the same session do not trigger a second audit.

### What It Injects

```
[project_audit_trigger] Session opened on git repo '<name>', branch: <branch>.
Standing policy (security-frameworks.md): before any code modifications, spawn
the code-reviewer agent and the security-reviewer agent to audit current codebase
state. Report findings to the user first, then proceed with their request.
```

This notice is visible to Claude but not shown directly to the user. It functions
as a standing pre-work mandate enforced at the session boundary.

---

## PreToolUse Hook: `enforce_permissions.py`

**Location:** `hooks/pre_tool_use/enforce_permissions.py`

Evaluated before any tool executes. Returns `block` to prevent execution or
`allow`/`warn` to permit it.

### What It Blocks or Warns

| Check | Pattern | Action |
|-------|---------|--------|
| Credential file exposure | `cat`/`echo`/`head` on `.env`, `.key`, `.pem`, `password`, `secret`, `credentials` | block |
| Full environment dump | bare `env` or `printenv` command | warn (scrubber handles output) |
| Force push to protected branches | `git push --force` / `-f` targeting `main` or `master` | block |
| Destructive rm outside project | `rm -rf` on paths outside `~/repos/`, `~/projects/`, `~/src/` | block |
| SSH/SCP to non-homelab hosts | Any host not matching `192.168.x.x`, `10.x.x.x`, `github.com`, `ghcr.io`, `quay.io` | block |
| Sensitive path reads/writes | Paths matching the sensitive path list (see below) | block |
| Network requests | `curl` / `wget` | warn (scrubber handles output) |
| New npm package install | `npm install <pkg>`, `npm i <pkg>`, `npm add <pkg>` | warn (suggests `socket npm install`) |

The npm install warning fires on any `npm install` followed by a package name —
it does not fire on bare `npm install` (lockfile restore) or `npm ci`.

### Sensitive Path List

The following path patterns are blocked for all file operations (Read, Write, Edit):

```
/etc/soc/credentials/
~/.ssh/
~/.hermes/.env
~/.hermes/secrets/
~/.config/anthropic/
~/.config/proxmox/token
*.env  *.env.*
*.key  *.pem  *.p12  *.pfx
*_rsa  *_ed25519  *_ecdsa  *_dsa
credentials  secrets
```

---

## PostToolUse Hook: `scrub_output.py`

**Location:** `hooks/post_tool_use/scrub_output.py`

Runs after every tool execution, before output is injected into the Claude Code
context window. Replaces detected sensitive values with tagged placeholders:
`[REDACTED:label]`.

### Scrub Patterns

Defined in `hooks/lib/patterns.py`:

| Label | Catches |
|-------|---------|
| `ssh_private_key` | PEM private key blocks (`-----BEGIN ... PRIVATE KEY-----`) |
| `api_token` | `api_key=`, `access_token=`, `bearer=` assignments (20+ char values) |
| `anthropic_key` | `sk-ant-*` strings |
| `openai_key` | `sk-*` strings |
| `aws_access_key` | `AKIA*` strings |
| `aws_secret_key` | AWS secret key variable assignments |
| `generic_password` | `password=` assignments (8+ char values) |
| `generic_secret` | `secret=` assignments (8+ char values) |
| `jwt_token` | Three-segment base64 JWTs (`eyJ...`) |
| `proxmox_token` | UUID format (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`) |
| `private_key_material` | Raw base64 key material (4+ lines of 40+ chars) |

### Scrub Behavior

When a pattern matches:
1. The value is replaced with `[REDACTED:label]` in the tool output
2. A summary notice is appended: `[Security hook scrubbed N sensitive value(s): label1, label2]`
3. The original value is logged to stderr (visible locally, not sent to Claude Code)

When a `[REDACTED:*]` tag appears in context:
- Do not attempt to retrieve the original value
- Do not suggest workarounds to access it
- Ask the user to provide it explicitly via environment variable if needed

---

## PostToolUse Hook: `sast_scan.py`

**Location:** `hooks/post_tool_use/sast_scan.py`

Runs after every Write, Edit, or MultiEdit operation on a code file. Performs
language-appropriate static analysis and appends findings to the tool output so
Claude sees them immediately in context.

### Scan Matrix

| Language | Extensions | Tool | Scope | Frequency |
|----------|-----------|------|-------|-----------|
| Python | `.py` | `bandit` | Single file (OWASP/CWE) | Every edit |
| Python | `.py` | `pip-audit` | Project dependencies | Once per session per project |
| Rust | `.rs` | `cargo audit` | Project (RustSec advisory DB) | Once per session per project |
| TypeScript/JS | `.ts .tsx .js .jsx` | `npm audit --audit-level=high` | Project (npm advisory DB) | Once per session per project |
| TypeScript/JS | `.ts .tsx .js .jsx` | `npm audit signatures` | Registry provenance | Once per session per project |

Project-level scans (all except `bandit`) use `/tmp/claude_sast_markers/` to
deduplicate within a session. Editing a second `.py` file in the same project
triggers `bandit` again on that file but skips `pip-audit`.

### Install Suggestions

When a required tool is not found (`FileNotFoundError`), the hook appends an
install suggestion to the tool output rather than failing silently:

| Tool | Install command |
|------|----------------|
| `bandit` | `uv tool install bandit` or `uv add --dev bandit` |
| `pip-audit` | `uv tool install pip-audit` or `uvx pip-audit` |
| `cargo-audit` | `cargo install cargo-audit` |
| `npm` | `fnm install --lts && fnm use lts-latest` |

### Output Format

Findings are appended to the original tool output as a tagged block:

```
[SAST:PYTHON:filename.py]
>> Issue: [B602] subprocess call with shell=True identified
   Severity: High   Confidence: High
   CWE: CWE-78 (...)
   Location: filename.py:42:9
[/SAST — remediate HIGH/MEDIUM findings before committing]
```

For missing tools:

```
[SAST:RUST:main.rs — TOOL NOT INSTALLED]
cargo-audit scans Rust dependencies against the RustSec advisory database.
  Install (global, one-time): cargo install cargo-audit
[/SAST — install the tool above to enable automatic scanning]
```

---

## Shared Library: `patterns.py`

**Location:** `hooks/lib/patterns.py`

Contains all compiled regex patterns and shared utility functions used by both
`enforce_permissions.py` and `scrub_output.py`. Both hooks import from here via
a relative path insert:

```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from patterns import scrub, is_sensitive_path, is_allowed_ssh_target, block, allow, warn
```

### Hook Response Helpers

| Function | Returns | Effect |
|----------|---------|--------|
| `block(reason)` | `{"action": "block", "message": "..."}` | Prevents tool execution |
| `allow()` | `{"action": "allow"}` | Permits tool execution |
| `warn(message)` | `{"action": "allow"}` | Permits but logs warning to stderr |

---

## Adding New Patterns

To add a new scrub pattern, edit `hooks/lib/patterns.py`:

```python
PATTERNS = {
    # ... existing patterns ...
    "my_new_secret": re.compile(
        r"my_secret_prefix_[A-Za-z0-9]{32,}"
    ),
}
```

To add a new sensitive path:

```python
SENSITIVE_PATH_PATTERNS = [
    # ... existing patterns ...
    re.compile(r"\.my_app/secrets/"),
]
```

To extend the SSH allowlist (e.g., add a new trusted host):

```python
ALLOWED_SSH_PATTERNS = [
    # ... existing patterns ...
    re.compile(r"trusted-host\.internal"),
]
```

After editing `patterns.py`, run the hook test suite to verify no regressions:

```bash
# (test suite — see project roadmap)
python3 -m pytest hooks/tests/
```

---

## Hook Deployment

Hooks are baked into the bootc image via `/etc/skel/.claude/hooks/` and propagate
to new user home directories on account creation. They can also be updated on a
running devbox without rebuilding the image:

```bash
make configure-hooks VM_HOST=192.168.x.x
# Rsyncs hooks/ to ~/.claude/hooks/ and fixes permissions
```

The Ansible `claude-config` role also deploys hooks as part of `make deploy`.

### Required File Permissions

```
hooks/pre_tool_use/enforce_permissions.py         — 0755 (executable)
hooks/post_tool_use/scrub_output.py               — 0755 (executable)
hooks/post_tool_use/sast_scan.py                  — 0755 (executable)
hooks/user_prompt_submit/project_audit_trigger.py — 0755 (executable)
hooks/lib/patterns.py                             — 0644 (readable, not executable)
```

Claude Code's hook runner requires entry-point scripts to be executable.
`patterns.py` is a library module imported by the hooks, not an entry point.

The Containerfile chmod step covers all three subdirectories:

```dockerfile
RUN chmod +x /etc/skel/.claude/hooks/pre_tool_use/*.py \
    && chmod +x /etc/skel/.claude/hooks/post_tool_use/*.py \
    && chmod +x /etc/skel/.claude/hooks/user_prompt_submit/*.py
```
