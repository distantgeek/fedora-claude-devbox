# open-atomic
## OpenCode Context Document

> **First time with this project?** Read the [First Run Checklist](#first-run-checklist)
> before doing anything else.

---

## Project Identity

**What this is:** `open-atomic` — a security-conscious OpenCode development
environment. OpenCode runs inside a **rootless container** on an **immutable Fedora
bootc VM**, with plugin-based security enforcement, no local root/sudo, and
session-scoped remote access via short-lived SSH certificates. Forked and rewritten
from `fedora-claude-devbox` (originally `intelligentcode-ai/claude-code-vm`).

**Owner:** distantgeek
**Primary registry:** GHCR (`ghcr.io/distantgeek/open-atomic`)
**Target runtime:** Proxmox VM, homelab (`distantgeek.net`)
**License:** Apache 2.0

**Related active projects (all private repos):**

| Repo | Description |
|------|-------------|
| `soc-deploy` | Fedora Server SOC stack — Elastic, TheHive, MISP, Shuffle, Velociraptor |
| `adhd-hermes` | Hermes Agent ADHD executive function appliance (bootc) |
| `llm-selective-memory` | Obsidian vault privacy-tiered LLM context injection |
| `ogoa-character-builder` | Tauri/React OGoA character sheet desktop app |
| `harrmony` | Music request manager for Arr ecosystem (Node/Express) |
| `homelab-jumpbox` | SSH jump box — LinuxServer openssh-server, SOCKS5 |
| `pve-sentinel` | Proxmox monitoring/automation (CT 100 on the R820) |
| `open-atomic` | **This project** |

---

## Architecture

Two immutable images, one running system:

```
Proxmox R820 (PVE 9.2, node kevbotpve-0)
└─ VM: open-atomic (bootc Fedora 44)
   ├─ SELinux enforcing (tuned), firewalld drop zone
   ├─ devbox user — NO sudo, NO wheel/podman groups
   ├─ SSH CA key (host-only, not mounted into container)
   ├─ grant-session tool (mints short-lived SSH certs)
   └─ Rootless container: opencode-agent
      ├─ opencode + plugins (security framework)
      ├─ MCPs, agents, skills, instructions, commands (root-owned, immutable)
      ├─ SAST tools + toolchains
      ├─ session certs (mounted, auto-expire)
      └─ projects volume
```

- **VM bootc image** (`ghcr.io/distantgeek/open-atomic`): thin shell — podman,
  devbox user, grant-session, SELinux policy, qemu-guest-agent.
- **Agent container image** (`ghcr.io/distantgeek/open-atomic-agent`): opencode +
  the entire security framework. Fast-iteration layer.

**Containment chain:** agent (non-root in container) → can't modify root-owned config
→ can't escalate (no sudo) → can't break out (user namespace) → VM immutable + SELinux.

**Adding an MCP or plugin** = edit repo → rebuild the agent container image → push →
update the container on the VM. The VM bootc image only rebuilds for VM-level changes.

---

## Deployed State

| Property | Value |
|----------|-------|
| VMID | _unassigned_ (provision on R820; avoid 100 = pve-sentinel) |
| Hostname | `open-atomic` |
| IP | _reserve on `192.168.2.0/24`_ |
| Proxmox host | `kevbotpve-0` at `192.168.2.2` |
| VM disk storage | `garage-0` (ZFS pool `Garage0`, raidz2) |
| Bridge | `vmbr0` |
| bootc image | `ghcr.io/distantgeek/open-atomic:latest` |
| Status | Not yet deployed — pending build |

### R820 Host (kevbotpve-0)

| Item | Value |
|------|-------|
| CPU | 4× Intel Xeon E5-4650 v2 (40C/80T), 4 NUMA nodes |
| RAM | 251 GiB |
| ZFS pool | `Garage0` raidz2, 8× 1.09 TB SAS, storage name `garage-0` (~8.6T free) |
| Other storage | `local` (dir), `local-lvm` (lvmthin, boot disk) |
| Network | `vmbr0` @ `192.168.2.2/24`, 4× NIC (nic0 up) |
| Existing guests | CT 100 `pve-sentinel` |

---

## First Run Checklist

When OpenCode first opens this project, complete these steps before any other work:

- [ ] **Verify environment variables are loaded.** Run `echo $PROXMOX_HOST` — if empty,
      source `~/.config/proxmox/token`.
- [ ] **Confirm the Proxmox SSH key exists:** `ls ~/.ssh/id_ed25519_pve_opencode`
- [ ] **Test Proxmox API connectivity:**
      ```bash
      set -a && source ~/.config/proxmox/token && set +a
      curl -sk -H "Authorization: PVEAPIToken=${PROXMOX_USER}!${PROXMOX_TOKEN_NAME}=${PROXMOX_TOKEN_VALUE}" \
        "https://${PROXMOX_HOST}:8006/api2/json/version" | python3 -m json.tool
      ```
- [ ] **Test SSH to the Proxmox host:**
      `ssh -i ~/.ssh/id_ed25519_pve_opencode root@192.168.2.2 "pveversion"`
- [ ] **Check git remote** is set correctly. Run `git remote -v` and flag anything unexpected.
- [ ] **Review Project Roadmap** at the bottom of this file — do not start roadmap items
      without explicit instruction.

---

## Homelab Infrastructure

### System Inventory

| System | Role | OS | Notes |
|--------|------|----|-------|
| R820 (`kevbotpve-0`) | Primary hypervisor | Proxmox VE 9.2 | Hosts this devbox VM |
| TrueNAS | NAS + Docker stacks | TrueNAS Scale | Dockge, NPM, Arr stack, Jellyfin, etc. |
| Fedora Server | SOC stack | Fedora Server 43 | soc-deploy, rootful Podman Quadlets |
| ThinkCentre | ADHD assistant | CentOS Stream 10 (bootc) | adhd-hermes (Hermes Agent appliance) |
| FX-8 / GTX 1060 6GB | Auxiliary inference | Fedora | faster-whisper STT, local LLM compression |
| Aurora-nvidia | Daily driver desktop | Aurora (Universal Blue) | NVIDIA GPU, primary dev workstation |
| Laptop | Mobile dev | (varies) | SSH client to this devbox |
| This VM | OpenCode devbox | Fedora 44 bootc | **You are here** |

### Network Topology

- **Domain:** `distantgeek.net` (Cloudflare DNS)
- **Reverse proxy:** NPM on TrueNAS — shared external Docker network named `proxy`
- **LAN range:** `192.168.x.x`
- **VPN/overlay range:** `10.x.x.x`
- **Jump box:** `homelab-jumpbox` with `DynamicForward 9050` SOCKS5 for external access.
  ProxyJump for routing — no `ForwardAgent` by design.

### Username Conventions

| System | Username | UID/GID notes |
|--------|----------|---------------|
| All homelab systems | `kevbot` | Primary operator user |
| TrueNAS Docker stacks | `kevbot` | PUID=**568**, PGID=**568** always |
| Fedora/Podman systems | `kevbot` | Rootful Podman — no PUID/PGID needed |
| Proxmox API | `opencode@pve` | OpenCode service account, token auth only |

### SSH Access Pattern

- **From desktop (LAN):** Direct — `ssh kevbot@<host>` with `~/.ssh/id_ed25519`
- **From laptop (external):** ProxyJump through `homelab-jumpbox`; no ForwardAgent
- **Git remotes:** Per-repo deploy keys, not personal SSH key
- **OpenCode → Proxmox:** short-lived SSH certs minted by `grant-session` (see
  [Remote Management](#remote-management))

---

## Proxmox API Access

### Credential File

Credentials live at `~/.config/proxmox/token` on the **operator's machine**. This file
is sourced into the shell automatically. It is never committed to any repo and must be
in `.gitignore`.

**File format:**
```bash
PROXMOX_HOST=192.168.2.2
PROXMOX_USER=opencode@pve
PROXMOX_TOKEN_NAME=opencode0
PROXMOX_TOKEN_VALUE=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**Shell profile sourcing** (add to `~/.bashrc` or `~/.zshrc` if not already present):
```bash
if [ -f "$HOME/.config/proxmox/token" ]; then
    set -a
    source "$HOME/.config/proxmox/token"
    set +a
fi
```

If `$PROXMOX_HOST` is empty in the environment, **stop and ask the user** to source
the file before proceeding with any Proxmox operations.

### Using the Token

```bash
curl -sk -H "Authorization: PVEAPIToken=${PROXMOX_USER}!${PROXMOX_TOKEN_NAME}=${PROXMOX_TOKEN_VALUE}" \
  "https://${PROXMOX_HOST}:8006/api2/json/nodes"
```

### Token Permissions

`opencode@pve!opencode0` holds a custom role scoped to VM management on the R820.
Privilege separation is **enabled** — effective permissions are the intersection of
the user's and token's grants, so the token can never escalate beyond its ACLs.

**Never grant:** Sys.Modify, Sys.PowerMgmt, Permissions.Modify, User.Modify,
Administrator, PVEAdmin.

---

## Remote Management (Session-Scoped Access)

The devbox has **no local root/sudo**. Remote servers (Proxmox, TrueNAS) are managed
via **short-lived SSH certificates**, minted per session.

### How it works

1. **One-time trust setup** per target: install the CA public key as a `cert-authority`
   entry in the target's `authorized_keys`.
2. **Per-session grant (local only):** `grant-session <target> <duration>` signs the
   agent's SSH key with the CA private key → a certificate valid for that duration.
   No server interaction.
3. **Agent connects** with the cert; the target validates it against the CA key + expiry.
4. **Auto-expiry:** the cert is rejected after the window; no revocation list.

### grant-session

```
grant-session proxmox 30m     # mint a 30-minute cert for the Proxmox host
grant-session truenas 1h      # mint a 1-hour cert for TrueNAS
grant-session --list          # show active sessions
grant-session --revoke <id>   # revoke early
```

Sudo is granted via the cert **principal** (root) or a scoped sudoers rule on the
target. See `docs/REMOTE_MANAGEMENT.md`.

### Scoped API tokens (where supported)

GitHub (fine-grained PAT), Proxmox (`opencode@pve!opencode0`) use scoped tokens.
TrueNAS API keys are root-equivalent → use SSH certs instead.

---

## Security Model

### Enforcement Architecture

Security is enforced by **OpenCode plugins**, not `settings.json` deny rules (which are
advisory only). The framework lives in immutable layers the agent cannot modify.

```
Tool call requested
        │
        ▼
tool.execute.before  ← env-protection, security-sniffer, language-guard (block)
        │ (allowed)
        ▼
Tool executes
        │
        ▼
tool.execute.after   ← scrub-daddy-bridge (scrubs credentials)
        │
        ▼
Output enters OpenCode context window
```

**Plugin gates (hard enforcement):**
- `session.created` → auto session-start audit (spawn security-auditor + code-reviewer)
- `command.executed` (git commit) → commit-guard runs SAST + coverage + docs check, blocks on failure
- `command.executed` (git push/merge) → review-gate blocks unless a review subagent ran this session
- `tool.execute.before` (write/edit) → security-sniffer scans for secrets/injection/weak crypto
- `tool.execute.before` (read) → env-protection blocks sensitive paths

**Default style directives (always in context):**
- **caveman** — terse output, preserve technical substance. Override with `/verbose`.
- **ponytail** — lazy-senior YAGNI: minimal code, no over-engineering.

### Config Split (what's immutable vs. writable)

| Layer | Location | Writable by agent? | Contents |
|---|---|---|---|
| Managed config | `/etc/opencode/` (root-owned in image) | No | permissions, instructions, MCPs, plugin list |
| Framework dir | `OPENCODE_CONFIG_DIR` (root-owned, read-only mount) | No | plugins, agents, skills, commands |
| User prefs | `~/.config/opencode/` | Yes | model choice, theme — nothing security-critical |

All config changes to the framework go through the repo + rebuild (gitops model).

### Sensitive Paths — Never Read, Write, or Expose

```
/etc/soc/credentials/          SOC stack credentials
~/.ssh/                        All SSH keys (session certs are the exception, via session dir)
~/.config/proxmox/token        Proxmox API credentials
~/.config/opencode/sessions/   Active session certs — never expose
*.key  *.pem  *.p12  *.pfx
*_rsa  *_ed25519  *_ecdsa
.env   .env.*
credentials  secrets
```

If any of the above appears in tool output, treat it as a scrubber miss. Do not
reproduce the content. Note the miss and continue.

### Git Safety

- Never force push to `main` or `master`
- Never push to a remote not matching `github.com/distantgeek*`
- Never commit files matching sensitive path patterns above
- Always run `git diff --staged` before committing; flag anything unexpected

### Network Boundaries

SSH, SCP, and rsync are allowed only to:
- `192.168.x.x` — homelab LAN
- `10.x.x.x` — homelab VPN/overlay
- `github.com`, `ghcr.io`, `quay.io` — package and registry access

---

## Container Paradigm

### Runtime: Podman Only

Never suggest `docker` or `docker-compose`. This environment is Podman exclusively.
The agent itself runs inside a **rootless container** with nested rootless podman.

| Concept | Convention |
|---------|-----------|
| Runtime | `podman` |
| Compose | `podman-compose` |
| Persistent services | Quadlet `.container` files |
| Agent isolation | rootless container (user namespace) |
| User Quadlet path | `~/.config/containers/systemd/` |

### SELinux — Always Enforcing

Account for SELinux in every container and file operation.

**Never:** `setenforce 0` or `security_opt: label=disable` unless explicitly requested,
always with a comment explaining the tradeoff.

**When AVC denials appear:**
```bash
ausearch -m avc -ts recent
audit2allow -M mymodule < /var/log/audit/audit.log
semodule -i mymodule.pp
```

Volume mount labels:
- `:Z` — private relabel (default — single container)
- `:z` — shared relabel (multiple containers accessing same volume)

### Package Management

- `dnf` only — never apt, snap, or brew
- There is **no local sudo** — system installs happen at build time in the image.
  Ad hoc tooling goes in the agent container image or via version managers.

---

## Toolchain Philosophy

### Pre-installed in the image

| Tool | Purpose | Notes |
|------|---------|-------|
| `opencode` | OpenCode CLI | Global via fnm-managed Node |
| `rustup` | Rust toolchain manager | No default toolchain — projects pin via `rust-toolchain.toml` |
| `fnm` | Node version manager | Use this, not nvm or system Node |
| `uv` | Python package manager | Replaces pip + virtualenv + pyenv |
| `mise` | Unified version manager | Node, Python, Ruby, Go via `.mise.toml` |
| `direnv` | Per-directory env loader | Auto-activates `.envrc` on `cd` |
| Git, gh, base tools | Core dev | System packages |

### Ad Hoc Installs

When a project needs a specific toolchain:

1. Check for pin files: `rust-toolchain.toml`, `.node-version`, `.nvmrc`,
   `.mise.toml`, `.python-version`
2. Install via the appropriate manager
3. Prefer project-local toolchains over global

**Never:**
- Install language toolchains system-wide via `dnf`
- Install Node globally outside fnm or mise
- Install Python packages outside a `uv` virtualenv or `uvx`
- Install Rust toolchains outside `rustup`

---

## Build System

### Makefile Targets

| Target | What it does |
|--------|-------------|
| `make build-image [DEVBOX_USER=name]` | Build bootc VM image |
| `make build-agent-image` | Build the agent container image |
| `make push-images` | Push both images to GHCR |
| `make build-disk-image` | Convert bootc image to raw disk via bootc-image-builder |
| `make deploy VM_HOST=<ip>` | Thin Ansible `configure.yml` against running VM |
| `make upgrade VM_HOST=<ip>` | `bootc upgrade` + reboot on target |
| `make rollback VM_HOST=<ip>` | `bootc rollback` + reboot on target |
| `make validate VM_HOST=<ip>` | Ansible validation playbook |
| `make test-connection VM_HOST=<ip>` | SSH test + bootc status |

**Disk import — PVE 9 requires `qm disk import`, not `qm importdisk`:**
`qm importdisk` silently writes the VM config without creating the volume in PVE 9.
Always use `qm disk import <vmid> <file> <storage>`.

### Containerfile Layer Order

1. `quay.io/fedora/fedora-bootc:44`
2. System packages (git, podman, buildah, skopeo, tmux, firewalld, python3, etc.)
3. `qemu-guest-agent` + systemd enable
4. bootc filesystem config
5. `fnm` → Node LTS
6. `uv`
7. `rustup` (no default toolchain)
8. `mise`
9. OpenCode CLI (`npm global` via fnm)
10. SAST tools: `bandit`, `pip-audit` (uv tool); `@socketsecurity/cli` (npm); `cargo-audit` (binary)
11. Framework → `/etc/opencode/` + `OPENCODE_CONFIG_DIR` (managed, immutable)
12. Rootless Podman config + `.npmrc` + shell integrations → `/etc/skel/`
13. DEVBOX_USER creation — **no sudo, no wheel/podman groups**

---

## Working Style

**Change discipline**
- Small, reviewable diffs over large atomic rewrites
- Always show `git diff` or file preview before committing or pushing
- Commit message format: `feat:`, `fix:`, `chore:`, `docs:`, `security:`

**Default output style (caveman + ponytail)**
- Terse, no filler — preserve all technical substance
- Lazy-senior YAGNI — write minimal code, don't over-engineer
- Request `/verbose` to override terse mode for a session

**Ansible**
- Idempotent modules over raw shell commands
- `lookup('env', 'VAR')` for credentials — never hardcode
- Tag all tasks to allow targeted runs

**Long-running operations**
- Use `tmux` for anything over a minute: `tmux new -s <task-name>`

**Credentials**
- If a credential is needed and not in environment, ask the user to `export VAR=value`
- Never pass credentials as CLI arguments (visible in process list and shell history)
- Never store credentials in files not covered by `.gitignore`

**When uncertain**
- Ask before assuming network addresses, VM IDs, or storage pool names not in this doc
- For destructive operations, show the command and ask for confirmation rather than
  executing immediately

---

## Project Roadmap

Items OpenCode should know about but **not start without explicit instruction:**

1. **Agent container image** — build the `open-atomic-agent` image baking in the full
   framework (plugins, agents, skills, instructions, commands, MCPs)
2. **grant-session tool** — short-lived SSH CA cert minting + session dir wiring
3. **Session-audit + review-gate plugins** — auto-invoke subagents at session start,
   block commits/pushes without review
4. **caveman/ponytail default instructions** — terse + YAGNI as always-on directives
5. **SELinux policy module** — targeted allow rules for the devbox, baked into the image
6. **R820 provisioning** — full VM creation pipeline on `garage-0` storage

Do not begin any of the above unless the user asks.
