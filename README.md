# open-atomic

A security-conscious OpenCode development environment: OpenCode runs inside a
**rootless container** on an **immutable Fedora bootc VM**, with plugin-based security
enforcement, **no local root/sudo**, SELinux throughout, and session-scoped remote
access via short-lived SSH certificates. Designed for homelab use on Proxmox.

Forked and rewritten from `fedora-claude-devbox` (originally
[intelligentcode-ai/claude-code-vm](https://github.com/intelligentcode-ai/claude-code-vm)),
now adapted exclusively for OpenCode.

**Registry:** `ghcr.io/distantgeek/open-atomic` (VM image) ·
`ghcr.io/distantgeek/open-atomic-agent` (agent container)

---

## Philosophy

- **Immutable by default** — Fedora bootc VM + rootless agent container. The agent is
  confined to a user namespace; a corrupted agent cannot escalate or break out.
- **No local sudo** — the devbox has no root access. Remote servers (Proxmox, TrueNAS)
  are managed via short-lived SSH certificates minted per session.
- **Plugin-based security** — real enforcement via OpenCode plugins
  (`tool.execute.before/after`, `session.created`, `command.executed`), not advisory
  `settings.json` deny rules.
- **SELinux always enforcing** — never disabled, tuned not restricted.
- **Framework baked in, immutable** — plugins, agents, skills, instructions, commands
  live in managed config the agent cannot modify. Changes flow through the repo + rebuild.
- **Version managers, not system toolchains** — `rustup`, `fnm`, `uv`, `mise` baked in.
- **Kubernetes optional** — not in the base image.

---

## Architecture

```
Proxmox R820 (PVE 9.2, node kevbotpve-0)
└─ VM: open-atomic (bootc Fedora 44)
   ├─ SELinux enforcing, firewalld drop zone
   ├─ devbox user — NO sudo
   ├─ SSH CA key (host-only)
   ├─ grant-session tool
   └─ Rootless container: opencode-agent
      ├─ opencode + security plugins
      ├─ MCPs, agents, skills, instructions (root-owned, immutable)
      ├─ SAST tools + toolchains
      └─ session certs (mounted, auto-expire)
```

**Adding an MCP or plugin** = edit repo → rebuild the agent container image → push →
update the container. Minutes, not an earth-moving rebuild of the bootc VM.

---

## What's Baked In

| Category | Contents |
|----------|----------|
| AI | OpenCode CLI + security framework |
| Security plugins | commit-guard, env-protection, language-guard, scrub-daddy-bridge, security-sniffer |
| Subagents | security-auditor, code-reviewer, docs-writer, refactor, project-auditor, spec-assessor, verifier |
| Skills | cis-benchmark, nist-csf-review, security-{bash,docker,go,iac,js,python,rust}, testing-{coverage,docker,go,iac,js,python,rust}, documentation-patterns |
| MCPs | github, cve, context7, duckduckgo-search, filesystem, playwright, memory, sequential-thinking |
| SAST | bandit, pip-audit, cargo-audit, @socketsecurity/cli |
| Core dev | git, gh, tmux, zsh, vim, jq, yq, make, ripgrep, fd-find, bat |
| Containers | podman, buildah, skopeo, podman-compose |
| Toolchains | fnm (Node LTS), uv, rustup, mise, direnv |

---

## Repository Structure

```
open-atomic/
├── build/
│   ├── Containerfile          # bootc VM image definition
│   └── agent/
│       └── Containerfile      # agent container image (opencode + framework)
├── config/
│   ├── opencode.jsonc         # OpenCode config: agents, commands, permissions
│   ├── env.example            # Environment variables template
│   ├── agents/                # Subagent definitions
│   ├── rules/                 # Security framework rules
│   ├── skills/                # Skill definitions
│   ├── instructions/          # security-guidelines, cis-hardening, etc.
│   └── containers/            # Rootless Podman config
├── plugins/                   # OpenCode plugins (security framework)
├── ansible/
│   ├── playbooks/             # configure.yml, validate.yml
│   └── roles/                 # common, opencode-config, git, git-repos
├── docs/
│   ├── PROXMOX_SETUP.md       # VM hardware spec and bootc import workflow
│   ├── BUILDING.md            # Build notes, layer design, bootc quirks
│   ├── SECURITY.md            # Plugin architecture and security model
│   ├── REMOTE_MANAGEMENT.md   # Session-scoped SSH cert access
│   └── CREDENTIALS.md         # Token/key injection + grant-session workflow
├── AGENTS.md                  # Full project context for OpenCode
└── Makefile                   # All operations
```

---

## Quick Start

### 1. Build the images

```bash
make build-image          # bootc VM image
make build-agent-image    # agent container image
```

### 2. Push to registry

```bash
make push-images
```

### 3. Convert to raw disk for Proxmox

```bash
make build-disk-image
# Output: output/image/disk.raw
```

### 4. Import to Proxmox and create VM

```bash
scp output/image/disk.raw root@192.168.2.2:/tmp/
ssh root@192.168.2.2 "qm disk import <VMID> /tmp/disk.raw garage-0"
```

Full hardware configuration and VM settings: see `docs/PROXMOX_SETUP.md`.

### 5. Configure and validate

Deployment is two-phase: root-level tasks (firewalld drop zone, SELinux relabel,
dirs, agent.env seed) run as root; user-state tasks (podman pull, agent service)
run as the target user.

```bash
# Root-level config
make deploy VM_HOST=192.168.2.150 VM_USER=root TARGET_USER=kevbot

# User-state steps (on the VM, as kevbot):
#   podman pull ghcr.io/distantgeek/open-atomic-agent:latest
#   systemctl --user enable --now opencode-agent.service

make validate VM_HOST=192.168.2.150 VM_USER=root TARGET_USER=kevbot
```

---

## Security Model

OpenCode plugins enforce security at the tool level. See `docs/SECURITY.md` for the
full architecture. Short version:

- `tool.execute.before` — env-protection blocks sensitive paths; security-sniffer
  scans writes for secrets/injection/weak crypto; language-guard halts unguarded langs
- `tool.execute.after` — scrub-daddy-bridge scrubs credentials from output
- `session.created` — auto session-start audit (spawn security-auditor + code-reviewer)
- `command.executed` — commit-guard runs SAST + coverage on commit; review-gate blocks
  pushes without review

Default style directives: **caveman** (terse) + **ponytail** (YAGNI). Override terse
mode with `/verbose`.

---

## Credits

Architectural inspiration from
[intelligentcode-ai/claude-code-vm](https://github.com/intelligentcode-ai/claude-code-vm)
(MIT). This project replaces Ubuntu/Docker/generic-VM with Fedora bootc, rootless
containers, OpenCode plugins, SELinux, and Proxmox throughout.

## License

Apache 2.0 — see [LICENSE](LICENSE).
