# Security Architecture — open-atomic

## Why Plugins, Not settings.json

`settings.json` deny rules in Claude Code were **not a reliable security boundary** —
multiple open upstream bugs meant deny rules were inconsistently enforced. This project
now targets OpenCode, where enforcement lives in **plugins** (JavaScript/TypeScript
modules) that hook tool events. Plugins throw hard errors at the tool level, so they
cannot be bypassed by prompt injection.

## Enforcement Flow

```
Session created
        │
        ▼
session.created plugin         ← auto session-start audit (security-auditor + code-reviewer)
        │
        ▼
Tool call requested
        │
        ▼
tool.execute.before            ← env-protection (sensitive paths), security-sniffer
                               ← (secrets/injection/weak crypto), language-guard (unguarded langs)
        │ (allowed)
        ▼
Tool executes
        │
        ▼
tool.execute.after             ← scrub-daddy-bridge (scrubs credentials)
        │
        ▼
command.executed               ← commit-guard (SAST + coverage), review-gate (push)
        │
        ▼
Output enters OpenCode context window
```

## Config Split (immutable vs. writable)

| Layer | Location | Writable by agent? | Contents |
|---|---|---|---|
| Managed config | `/etc/opencode/` (root-owned in image) | No | permissions, instructions, MCPs, plugin list |
| Framework dir | `OPENCODE_CONFIG_DIR` (root-owned, read-only mount) | No | plugins, agents, skills, commands |
| User prefs | `~/.config/opencode/` | Yes | model choice, theme — nothing security-critical |

The security-critical framework lives in the two immutable layers. The agent can only
touch its personal prefs, which cannot override the managed config. All framework
changes flow through the repo + rebuild (gitops model).

## Plugins

| Plugin | Event | What it does |
|--------|-------|--------------|
| `env-protection` | `tool.execute.before` (read) | Blocks reads of `.env`, credentials, keys, certs, private keys |
| `security-sniffer` | `tool.execute.before` (write/edit) | Scans content for hardcoded secrets, injection, weak crypto, path traversal |
| `language-guard` | `tool.execute.before` (write/edit) | Halts development on unguarded languages until the security framework is scaffolded |
| `scrub-daddy-bridge` | `tool.execute.after` | Scrubs credentials from tool output via `scrub-daddy-llm` |
| `commit-guard` | `command.executed` (git commit) | Runs language SAST + coverage checks; blocks on failure; blocks staged credential files |
| `review-gate` | `command.executed` (git push/merge) | Blocks push unless a review subagent ran this session |
| `session-audit` | `session.created` | Auto-invokes security-auditor + code-reviewer at session start |

### Sensitive Paths — Never Read, Write, or Expose

```
/etc/soc/credentials/
~/.ssh/                        (session certs are the exception, via session dir)
~/.config/proxmox/token
~/.config/opencode/sessions/
*.key  *.pem  *.p12  *.pfx
*_rsa  *_ed25519  *_ecdsa
.env   .env.*
credentials  secrets
```

### Scrub Patterns

| Label | Catches |
|-------|---------|
| `ssh_private_key` | PEM private key blocks |
| `api_token` | `key=`, `token=`, `secret=` assignments |
| `anthropic_key` | `sk-ant-*` |
| `openai_key` | `sk-*` |
| `aws_access_key` | `AKIA*` |
| `aws_secret_key` | AWS secret key assignments |
| `generic_password` | `password=` assignments |
| `generic_secret` | `secret=` assignments |
| `jwt_token` | Three-segment base64 JWTs |
| `proxmox_token` | UUID format — covers Proxmox token secrets |
| `private_key_material` | Raw base64 key material blocks |

When a `[REDACTED:*]` tag appears in output:
- Do not attempt to retrieve the original value
- Do not suggest workarounds to access it
- Ask the user to provide it explicitly via environment variable if needed

## SAST Tooling

| Language | Tool | Scope |
|----------|------|-------|
| Python | `bandit` | Per-file OWASP/CWE |
| Python | `pip-audit` | Dependency CVEs |
| Rust | `cargo audit` | RustSec advisory DB |
| Node/TS | `npm audit --audit-level=high` + `npm audit signatures` | npm advisory DB + provenance |

`commit-guard` runs these at commit time. A `/sast` command lists applicable tools for
the current project. The security-auditor subagent runs them on demand.

## Default Style Directives

- **caveman** — terse output, preserve all technical substance. Override with `/verbose`.
- **ponytail** — lazy-senior YAGNI: minimal code, don't over-engineer.

Both are loaded as always-on instructions; a plugin re-asserts them at `session.created`.

## Git Safety

- Never force push to `main` or `master`
- Never push to a remote not matching `github.com/distantgeek*`
- Never commit files matching sensitive path patterns
- Always run `git diff --staged` before committing; flag anything unexpected

## Network Boundaries

SSH, SCP, and rsync are allowed only to:
- `192.168.x.x` — homelab LAN
- `10.x.x.x` — homelab VPN/overlay
- `github.com`, `ghcr.io`, `quay.io` — package and registry access

## Subagents (Security Framework)

| Agent | Role |
|-------|------|
| `security-auditor` | Vulnerability scanning, CVE checks, dependency audits, secret detection |
| `code-reviewer` | Code quality, SOLID, error handling, test coverage (read-only) |
| `project-auditor` | Full codebase audit, hallucination risk (read-only) |
| `verifier` | Verifies agent outputs, validates API/CVE claims (auto-invoked after audits) |
| `spec-assessor` | Feature spec validation (read-only) |
| `refactor` | Restructuring without behavior change |
| `docs-writer` | Documentation only |

Skills loaded: cis-benchmark, nist-csf-review, security-{bash,docker,go,iac,js,python,rust},
testing-{coverage,docker,go,iac,js,python,rust}, documentation-patterns.

Instructions loaded: security-guidelines, cis-hardening, code-quality, delegation,
hallucination-lessons.
