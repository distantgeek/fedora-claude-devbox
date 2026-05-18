---
description: Mandatory security framework requirements — CIS Controls v8, NIST SP 800-53 Rev 5, OWASP ASVS/Top 10. Applied to all code, configuration, and infrastructure work.
---

# Security Framework Requirements

All code, configuration, and infrastructure changes must satisfy the controls below.
When a conflict exists between frameworks, apply the strictest control.

---

## OWASP (Primary Application Security Reference)

Apply **OWASP Top 10** checks on every code change touching user input, auth, or data:

| # | Risk | Mandatory Check |
|---|------|----------------|
| A01 | Broken Access Control | Verify authz on every endpoint; deny by default |
| A02 | Cryptographic Failures | TLS 1.2+ only; AES-256/ChaCha20; no MD5/SHA1 for security use |
| A03 | Injection | Parameterized queries; no string-concatenated SQL; subprocess with arg lists |
| A04 | Insecure Design | Threat model new features; trust boundaries explicit |
| A05 | Security Misconfiguration | No default creds; disable unused features; env-separated configs |
| A06 | Vulnerable Components | `npm audit`/`cargo audit`/`pip-audit` before commit; no known critical CVEs |
| A07 | Auth/Identity Failures | MFA where supported; secure session handling; bcrypt/argon2 for passwords |
| A08 | Integrity Failures | Verify signatures on dependencies; no untrusted deserialization |
| A09 | Logging Failures | Log auth events, access control failures, input validation errors |
| A10 | SSRF | Allowlist outbound destinations; validate URLs before fetch |

Apply **OWASP ASVS Level 2** for any component handling PII, credentials, or health data.

When working with Python, run `bandit -r <path> -ll` and resolve HIGH/MEDIUM findings before committing.

Use the `docs-lookup` agent to fetch current OWASP guidance when implementing controls — do not rely on training data alone for specific OWASP requirements.

---

## CIS Controls v8 (Infrastructure and Configuration Hardening)

Priority: IG1 controls are non-negotiable. IG2 applies to all server/container workloads.

**IG1 — Basic Cyber Hygiene (always required):**
- CIS 1: Inventory and control of enterprise assets — document all hosts in DEVBOX_INSTALLED.md and homelab inventory
- CIS 2: Inventory and control of software assets — track installed packages; use `dnf` only; no shadow installs
- CIS 4: Secure configuration — no default passwords; harden before deploying (Fedora/RHEL: apply CIS RHEL 9 Benchmark where applicable)
- CIS 5: Account management — principle of least privilege; no shared accounts; `claude@pam` scoped to minimum required Proxmox permissions
- CIS 6: Access control management — deny by default; explicit allowlist
- CIS 11: Data recovery — verify backups exist before destructive operations

**IG2 — Additional for server/container workloads:**
- CIS 3: Data protection — classify data sensitivity; encrypt at rest for sensitive paths (`~/.ssh/`, `~/.config/proxmox/`, SOC credentials)
- CIS 7: Continuous vulnerability management — apply OS patches; review `dnf updateinfo list security` before major deploys
- CIS 8: Audit log management — systemd-journal retained; auditd enabled on SOC stack; logs not writable by application user
- CIS 9: Email and web browser protections — (N/A for server workloads)
- CIS 12: Network infrastructure management — document firewall rules; no management interfaces on untrusted networks; firewalld zones explicit
- CIS 13: Network monitoring — SOC stack (Elastic/Velociraptor) covers this; alert on new outbound connections from server workloads
- CIS 16: Application software security — SAST on every language (bandit/ruff for Python, `cargo audit` for Rust, `npm audit` for Node)

**Container-specific (CIS Docker/Podman Benchmark):**
- Run containers as non-root where possible; explicit UID in Containerfile
- No `--privileged` unless documented and justified
- Read-only root filesystem where feasible (`--read-only`)
- Drop all capabilities; add back only what's needed (`--cap-drop ALL --cap-add ...`)
- SELinux labels on all volume mounts (`:Z` or `:z`)
- No secrets in environment variables visible via `podman inspect`; use secrets or bind mounts

---

## NIST SP 800-53 Rev 5 (Control Families — applied by context)

Apply relevant control families based on the component being built:

**AC — Access Control**
- AC-2: Account management — document privileged accounts; review quarterly
- AC-3: Access enforcement — RBAC; deny-by-default
- AC-6: Least privilege — no more permissions than required; Proxmox token scoped per CLAUDE.md
- AC-17: Remote access — SSH key auth only; no password auth; ProxyJump documented

**AU — Audit and Accountability**
- AU-2: Event logging — log: login attempts, privilege use, config changes, process creation
- AU-3: Content of audit records — include: timestamp, source, user/process, outcome
- AU-9: Protection of audit information — logs not modifiable by application users
- AU-12: Audit record generation — auditd for system calls on SOC stack; journald everywhere else

**CM — Configuration Management**
- CM-2: Baseline configuration — bootc image is the baseline; deviations tracked in DEVBOX_INSTALLED.md
- CM-6: Configuration settings — CIS hardening applied; document deviations with justification
- CM-7: Least functionality — disable unused services; `systemctl disable` anything not needed
- CM-8: System component inventory — DEVBOX_INSTALLED.md + homelab system inventory in CLAUDE.md

**IA — Identification and Authentication**
- IA-2: Identification and authentication — unique accounts; no shared credentials
- IA-5: Authenticator management — rotate secrets on suspected compromise; use token auth (not passwords) for API access
- IA-8: Non-organizational users — external service accounts (e.g., `claude@pam`) scoped minimally

**SC — System and Communications Protection**
- SC-8: Transmission confidentiality — TLS 1.2+ for all network communication; no plaintext protocols
- SC-12: Cryptographic key management — keys in `~/.ssh/`; never committed; rotated if exposed
- SC-28: Protection of information at rest — sensitive paths encrypted; credentials in dedicated files outside repo

**SI — System and Information Integrity**
- SI-2: Flaw remediation — apply security patches within 30 days of release
- SI-3: Malware protection — no unnecessary execution of untrusted code; Podman image signatures where available
- SI-10: Information input validation — validate all external inputs at system boundary
- SI-12: Information management and retention — logs retained per operational need; no indefinite growth without rotation

---

## Workflow Integration

**Before writing code:** Identify which OWASP categories and CIS/NIST controls apply to the component. State them in the plan.

**During implementation:**
- Invoke `security-reviewer` agent for any component handling auth, external input, credentials, or network I/O
- Invoke `silent-failure-hunter` for error handling review
- Run SAST tools appropriate to the language (`bandit`, `cargo audit`, `npm audit`)

**Before committing:**
- All OWASP Top 10 checks from `rules/ecc/common/security.md` must pass
- No hardcoded secrets (hook suite enforces; also manual check)
- SAST clean at HIGH severity or above

**For infrastructure changes (Proxmox, Quadlets, Ansible):**
- Invoke `network-config-reviewer` for firewall and network config changes
- Invoke `homelab-architect` for topology or VLAN changes
- Document CIS IG1 compliance for any new host added to the homelab
