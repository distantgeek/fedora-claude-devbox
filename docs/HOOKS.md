# Security Hook Architecture

## Why Hooks Instead of settings.json

`settings.json` deny rules in Claude Code are **not a reliable security boundary.**
As of April 2026, there are multiple open upstream bugs where deny rules are
inconsistently enforced — rules that should block operations sometimes don't,
depending on how the tool call is constructed.

This project uses a hook-based enforcement model instead:

```
Tool call requested
        │
        ▼
hooks/pre_tool_use/enforce_permissions.py   ← blocks before execution
        │ (allowed)
        ▼
Tool executes
        │
        ▼
hooks/post_tool_use/scrub_output.py         ← scrubs before context injection
        │
        ▼
Output enters Claude Code context window
```

Hooks run as Python scripts invoked by Claude Code's hook runner. They read the
tool call as JSON from stdin and write a response to stdout. A `block` response
prevents execution entirely. The hook runner is part of Claude Code itself, so
it cannot be bypassed by prompt injection.

`settings.json` is kept in this repo for **behavioral guidance and allow-list
documentation only** — it helps Claude Code make better default choices but is
not relied upon for security.

---

## PreToolUse Hook: `enforce_permissions.py`

**Location:** `hooks/pre_tool_use/enforce_permissions.py`

Evaluated before any tool executes. Returns `block` to prevent execution or
`allow` to permit it.

### What It Blocks

| Check | Pattern | Action |
|-------|---------|--------|
| Credential file exposure | `cat`/`echo`/`head` on `.env`, `.key`, `.pem`, `password`, `secret`, `credentials` | block |
| Full environment dump | bare `env` or `printenv` command | warn (scrubber handles output) |
| Force push to protected branches | `git push --force` / `-f` targeting `main` or `master` | block |
| Destructive rm outside project | `rm -rf` on paths outside `~/repos/`, `~/projects/`, `~/src/` | block |
| SSH/SCP to non-homelab hosts | Any host not matching `192.168.x.x`, `10.x.x.x`, `github.com`, `ghcr.io`, `quay.io` | block |
| Sensitive path reads/writes | Paths matching the sensitive path list (see below) | block |
| Network requests | `curl` / `wget` | warn (scrubber handles output) |

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

If access to a sensitive file is genuinely needed, the user should provide the
value explicitly via environment variable rather than having Claude Code read
the file directly.

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

## Shared Library: `patterns.py`

**Location:** `hooks/lib/patterns.py`

Contains all compiled regex patterns and shared utility functions used by both
hooks. Both hooks import from here via a relative path insert:

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

To extend SSH allowlist (e.g., add a new trusted host):

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
hooks/pre_tool_use/enforce_permissions.py  — 0755 (executable)
hooks/post_tool_use/scrub_output.py        — 0755 (executable)
hooks/lib/patterns.py                      — 0644 (readable, not executable)
```

Claude Code's hook runner requires the entry-point scripts to be executable.
`patterns.py` is a library module, not a hook entry point.
