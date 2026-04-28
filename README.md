# fedora-claude-devbox

A security-conscious Claude Code development environment built on Fedora bootc,
Podman, and Quadlets. Designed for homelab use on Proxmox, with hook-based security
enforcement, immutable system images, and SELinux throughout.

Rewritten for RHEL-family systems from
[intelligentcode-ai/claude-code-vm](https://github.com/intelligentcode-ai/claude-code-vm)
(MIT) — Ansible role patterns and CLAUDE.md tier template structure adapted from
that project; everything else is a ground-up rewrite for Fedora/bootc/Podman/Proxmox.

**Registry:** `ghcr.io/distantgeek/fedora-claude-devbox`

---

## Philosophy

- **Fedora bootc** — immutable, versioned, rollback-capable system image. Upgrades
  are atomic; rollback is one command.
- **Podman + Quadlets** — no Docker daemon. Rootless containers by default.
  Persistent services are systemd Quadlet `.container` units, not compose stacks.
- **SELinux always enforcing** — never disabled, always accounted for.
- **Hook-based security** — real enforcement via PreToolUse/PostToolUse Python hooks.
  `settings.json` deny rules are not a reliable security boundary in Claude Code
  (multiple open upstream bugs as of 2026); hooks are.
- **Version managers, not system toolchains** — `rustup`, `fnm`, `uv`, `mise`
  baked in. Language toolchains installed per-project, not system-wide.
- **Kubernetes optional** — not in the base image. Added via `make enable-kubernetes`
  on a running devbox without rebuilding the image.

---

## What's Baked In

| Category | Tools |
|----------|-------|
| Core dev | git, gh, curl, wget, tmux, zsh, vim, jq, yq, make |
| Build tools | gcc, gcc-c++, openssl-devel, pkg-config |
| Containers | podman, buildah, skopeo, podman-compose |
| System | firewalld, qemu-guest-agent, direnv |
| CLI utilities | ripgrep, fd-find, bat, tree, htop, unzip |
| Node | fnm (Fast Node Manager) + Node LTS |
| Python | python3, python3-libselinux, uv + uvx |
| Rust | rustup binary (no default toolchain — pin via `rust-toolchain.toml`) |
| Versions | mise (unified version manager for Node/Python/Ruby/Go) |
| Automation | ansible-core (system-wide, all users) |
| AI | Claude Code CLI (`claude`) |
| Security | PreToolUse + PostToolUse hook suite |

All version manager binaries (`uv`, `rustup`, `mise`) are installed system-wide to
`/usr/local/bin`. Language toolchains are installed per-user at runtime.

---

## Repository Structure

```
fedora-claude-devbox/
├── build/
│   └── Containerfile          # bootc image definition
├── config/
│   ├── settings.json          # Claude Code behavioral guidance (not a security boundary)
│   ├── env.example            # Environment variables template
│   ├── mcp-servers.template.json  # MCP server config reference
│   └── containers/            # Rootless Podman config skeleton (baked into image skel)
├── hooks/
│   ├── pre_tool_use/
│   │   └── enforce_permissions.py   # Blocks dangerous operations before execution
│   ├── post_tool_use/
│   │   └── scrub_output.py          # Scrubs credentials from tool output
│   └── lib/
│       └── patterns.py              # Shared patterns, scrub functions, allowlists
├── ansible/
│   ├── ansible.cfg
│   ├── playbooks/
│   │   ├── configure.yml      # Thin post-boot configuration
│   │   ├── validate.yml       # Post-deployment health checks
│   │   └── kubernetes.yml     # Optional Kubernetes layer
│   └── roles/
│       ├── common/            # firewalld, lingering, base dirs
│       ├── claude-config/     # Hook suite, settings.json, CLAUDE.md tier deployment
│       ├── git/               # Git user config, credential setup
│       ├── git-repos/         # Auto-clone repos from env vars
│       └── kubernetes/        # kubectl, helm, k3s or KIND
├── docs/
│   ├── PROXMOX_SETUP.md       # VM hardware spec and bootc image import workflow
│   ├── BUILDING.md            # Build notes, layer design, known bootc quirks
│   └── HOOKS.md               # Security hook architecture and pattern reference
├── CLAUDE.md                  # Full project context for Claude Code
└── Makefile                   # All operations — never run Ansible directly
```

---

## Prerequisites

**On the build machine** (where you run `make`):

- Podman
- `gh` CLI authenticated with `write:packages` scope
- `podman login ghcr.io` with a GitHub PAT that has `write:packages`
- `~/.config/proxmox/token` sourced in your shell (see `CLAUDE.md`)

> `ansible-core` is baked into the devbox image — you do not need it on the build machine.
> The devbox manages itself and other homelab targets once deployed.

**For Proxmox import:**

- SSH access to the Proxmox host as root (or via dedicated key — see `docs/PROXMOX_SETUP.md`)
- Proxmox API token with `ClaudeDevbox` role (see `CLAUDE.md` → Proxmox API Access)
- A VMID reserved for the devbox
- An LVM thin or directory storage pool

---

## Quick Start

### 1. Build the image

```bash
# Public image (generic 'devbox' user):
make build-image

# Personal build with your username baked in:
make build-image DEVBOX_USER=yourname
```

See `docs/BUILDING.md` for notes on bootc-specific build quirks and the `DEVBOX_USER` arg.

### 2. Push to registry

```bash
make push-image
```

### 3. Convert to raw disk for Proxmox

```bash
make build-disk-image
# Output: output/image/disk.raw
```

### 4. Import to Proxmox and create VM

```bash
scp output/image/disk.raw root@<proxmox-host>:/tmp/

# PVE 9+ syntax:
ssh root@<proxmox-host> "qm disk import <VMID> /tmp/disk.raw <storage-pool>"

# Attach, resize to 60G, set boot order — full workflow in docs/PROXMOX_SETUP.md
```

Full hardware configuration and VM settings: see `docs/PROXMOX_SETUP.md`.

### 5. Configure the running VM

```bash
cp config/env.example .env
# Edit .env — set VM_HOST, git credentials, etc.

make deploy VM_HOST=192.168.x.x
```

This runs the Ansible `configure.yml` playbook: firewalld rules, user lingering,
SSH keys, Proxmox token env wiring, hook suite deployment, CLAUDE.md tier selection.

### 6. Validate

```bash
make validate VM_HOST=192.168.x.x
```

Checks: bootc status, Podman, Claude Code, Node, uv, rustup, mise, SELinux enforcing,
firewalld active, user lingering enabled, hooks installed and executable.

---

## Deployment Tiers

The Ansible `configure.yml` playbook supports three tiers, selected via `DEVBOX_TIER`:

| Tier | Command | What's added |
|------|---------|-------------|
| `minimal` | `make deploy DEVBOX_TIER=minimal` | Git config, firewalld, hooks only |
| `enhanced` | `make deploy` (default) | + MCP servers |
| `full` | `make enable-kubernetes` after deploy | + kubectl, helm, k3s or KIND |

Each tier deploys a matching `CLAUDE.runtime.md` to `~/.claude/` on the devbox,
giving Claude Code accurate context about what's available in the current environment.

---

## MCP Servers (Enhanced Tier)

Deployed to `~/.claude/claude_desktop_config.json` on the devbox.

| Server | Purpose | API Key |
|--------|---------|---------|
| memory | Persistent cross-session knowledge graph | No |
| sequential-thinking | Structured multi-step reasoning | No |
| puppeteer | Headless Chromium — real DOM, JS, screenshots | No (runs via `podman run`) |
| doc-forge | Document generation and manipulation | No |
| brave-search | Web search | `BRAVE_API_KEY` |
| context7 | Up-to-date library documentation | `UPSTASH_*` |
| omnisearch | Multi-provider search aggregator | `TAVILY_API_KEY` |

API-key servers are only deployed if the relevant key is present in `.env`.

---

## Upgrade Workflow

```bash
# Modify Containerfile or config, then:
make build-image
make push-image
make upgrade VM_HOST=192.168.x.x
# (runs: bootc upgrade + reboot on the devbox)

# If something breaks after upgrade:
make rollback VM_HOST=192.168.x.x
# (runs: bootc rollback + reboot)
```

Take a Proxmox snapshot before the first `bootc upgrade` — see `docs/PROXMOX_SETUP.md`.

---

## Security Model

See `docs/HOOKS.md` for the full hook architecture. Short version:

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

**What hooks enforce:**
- Sensitive path reads/writes blocked (`~/.ssh/`, `~/.config/proxmox/`, `.env`, `*.key`)
- SSH/SCP restricted to homelab ranges (`192.168.x.x`, `10.x.x.x`) and known registries
- Force push to `main`/`master` blocked
- `rm -rf` outside project directories blocked
- Credential file exposure via `cat`/`echo` blocked
- Full env dumps warned and scrubbed
- All Proxmox token UUIDs, API keys, SSH keys, JWTs scrubbed from tool output

`settings.json` is behavioral guidance only. VM isolation via Proxmox is the outer
security boundary.

---

## Credits

Architectural inspiration, Ansible role structure, and CLAUDE.md tier template patterns
from [intelligentcode-ai/claude-code-vm](https://github.com/intelligentcode-ai/claude-code-vm)
(MIT License). This project replaces Ubuntu/Docker/generic-VM with Fedora bootc,
Podman, SELinux, and Proxmox throughout.

## License

Apache 2.0 — see [LICENSE](LICENSE).
