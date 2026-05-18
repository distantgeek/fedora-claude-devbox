# fedora-claude-devbox
## Claude Code Context Document

> **First time with this project?** Read the [First Run Checklist](#first-run-checklist)
> before doing anything else.

---

## Project Identity

**What this is:** `fedora-claude-devbox` — a security-conscious Claude Code development
environment built on Fedora bootc, Podman, and Quadlets. Forked and rewritten from
`intelligentcode-ai/claude-code-vm` for RHEL-family systems with hook-based security
enforcement replacing unreliable `settings.json` deny rules.

**Owner:** distantgeek
**Primary registry:** GHCR (`ghcr.io/distantgeek/fedora-claude-devbox`)
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
| `fedora-claude-devbox` | **This project** |

---

## Deployed VM — Current State

| Property | Value |
|----------|-------|
| VMID | 199 |
| Hostname | `fedora-claude-devbox` |
| IP | `192.168.2.156` (set DHCP reservation for MAC `BC:24:11:16:86:68`) |
| Proxmox host | `kevbot-pve` at `192.168.2.146` |
| SSH user | `kevbot` (manually bootstrapped; will be baked in after next upgrade) |
| bootc image | `ghcr.io/distantgeek/fedora-claude-devbox:latest` |
| Status | Running — pending `make build-image DEVBOX_USER=kevbot && make push-image && make upgrade` |

**Claude's dedicated SSH key for Proxmox host:** `~/.ssh/id_ed25519_claude_proxmox`
Installed in `root@192.168.2.146:/root/.ssh/authorized_keys`. Use this key — not
the personal `id_ed25519` — for all Claude-initiated SSH to the Proxmox host.

---

## First Run Checklist

When Claude Code first opens this project, complete these steps before any other work:

- [ ] **Verify environment variables are loaded.** Run `echo $PROXMOX_HOST` — if empty,
      source `~/.config/proxmox/token`. See [Proxmox API Access](#proxmox-api-access).
- [ ] **Confirm Claude's Proxmox SSH key exists:** `ls ~/.ssh/id_ed25519_claude_proxmox`
      If missing, regenerate and reinstall on the Proxmox host (see Deployed VM section above).
- [ ] **Confirm hook suite is wired.** Check `~/.claude/hooks/` exists and scripts are
      executable. If not:
      ```bash
      chmod +x ~/.claude/hooks/pre_tool_use/*.py \
               ~/.claude/hooks/post_tool_use/*.py \
               ~/.claude/hooks/user_prompt_submit/*.py
      ```
- [ ] **Confirm `proxmox_token` UUID pattern** exists in `hooks/lib/patterns.py`.
      See [Credential Scrubbing](#credential-scrubbing).
- [ ] **Test Proxmox API connectivity** (source token file first):
      ```bash
      set -a && source ~/.config/proxmox/token && set +a
      curl -sk -H "Authorization: PVEAPIToken=${PROXMOX_USER}!${PROXMOX_TOKEN_NAME}=${PROXMOX_TOKEN_VALUE}" \
        "https://${PROXMOX_HOST}:8006/api2/json/nodes" | python3 -m json.tool
      ```
- [ ] **Test Claude's SSH key to Proxmox:**
      `ssh -i ~/.ssh/id_ed25519_claude_proxmox root@192.168.2.146 "pveversion"`
- [ ] **Check git remote** is set correctly. Run `git remote -v` and flag anything unexpected.
- [ ] **Review Project Roadmap** at the bottom of this file — do not start roadmap items
      without explicit instruction.

---

## Homelab Infrastructure

### System Inventory

| System | Role | OS | Notes |
|--------|------|----|-------|
| Proxmox host | Primary hypervisor | Proxmox VE | Hosts this devbox VM |
| TrueNAS | NAS + Docker stacks | TrueNAS Scale | Dockge, NPM, Arr stack, Jellyfin, etc. |
| Fedora Server | SOC stack | Fedora Server 43 | soc-deploy, rootful Podman Quadlets |
| ThinkCentre | ADHD assistant | CentOS Stream 10 (bootc) | adhd-hermes (Hermes Agent appliance) |
| FX-8 / GTX 1060 6GB | Auxiliary inference | Fedora | faster-whisper STT, local LLM compression |
| Aurora-nvidia | Daily driver desktop | Aurora (Universal Blue) | NVIDIA GPU, primary dev workstation |
| Laptop | Mobile dev | (varies) | SSH client to this devbox |
| This VM | Claude Code devbox | Fedora bootc | **You are here** |

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
| Proxmox API | `claude@pam` | Claude Code service account, token auth only |

### SSH Access Pattern

- **From desktop (LAN):** Direct — `ssh kevbot@<host>` with `~/.ssh/id_ed25519`
- **From laptop (external):** ProxyJump through `homelab-jumpbox`; no ForwardAgent
- **Git remotes:** Per-repo deploy keys, not personal SSH key
- **Claude Code → Proxmox:** SSH to Proxmox host with `id_ed25519` + API token
  for VM management operations

---

## Proxmox API Access

### Credential File

Credentials live at `~/.config/proxmox/token` on the **operator's machine** — wherever
Claude Code is running (laptop or desktop). This file is sourced into the shell
automatically. It is never committed to any repo and must be in `.gitignore`.

**File format:**
```bash
PROXMOX_HOST=192.168.x.x
PROXMOX_USER=claude@pam
PROXMOX_TOKEN_NAME=claudeToken
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

`set -a` before sourcing auto-exports all variables defined in the file. Every shell
session Claude Code spawns will then have these available without manual export.

If `$PROXMOX_HOST` is empty in the environment, **stop and ask the user** to source
the file before proceeding with any Proxmox operations.

### Using the Token

```bash
# Test connectivity
pvesh get /nodes \
  --apitoken "$PROXMOX_USER!$PROXMOX_TOKEN_NAME=$PROXMOX_TOKEN_VALUE"

# List VMs on a node
pvesh get /nodes/<nodename>/qemu \
  --apitoken "$PROXMOX_USER!$PROXMOX_TOKEN_NAME=$PROXMOX_TOKEN_VALUE"

# In Ansible proxmox_* modules:
# api_host:         "{{ lookup('env', 'PROXMOX_HOST') }}"
# api_user:         "{{ lookup('env', 'PROXMOX_USER') }}"
# api_token_id:     "{{ lookup('env', 'PROXMOX_TOKEN_NAME') }}"
# api_token_secret: "{{ lookup('env', 'PROXMOX_TOKEN_VALUE') }}"
```

### Token Permissions

`claude@pam!claudeToken` holds the custom role `ClaudeDevbox` with:

**Granted:** VM.Allocate, VM.Config.Disk, VM.Config.CPU, VM.Config.Memory,
VM.Config.Network, VM.Config.Options, VM.Config.Boot, VM.PowerMgmt, VM.Snapshot,
VM.Audit, Datastore.AllocateSpace, Datastore.Audit, Sys.Audit

**Applied on:** `/vms/`, `/storage/<ssd-pool>`, `/nodes/<node>`

**Never grant:** Sys.Modify, Sys.PowerMgmt, Permissions.Modify, User.Modify,
Administrator, PVEAdmin

Privilege separation is **enabled** on the token — effective permissions are the
intersection of the user's and token's grants, so the token can never escalate beyond
its explicit ACLs.

---

## Security Model

### Enforcement Architecture

`settings.json` deny rules are **not a security boundary.** They are inconsistently
enforced by Claude Code (multiple open upstream bugs as of April 2026). Actual
enforcement is the hook suite in `~/.claude/hooks/`.

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

`settings.json` is kept for **behavioral guidance and allow-list documentation only.**

### Sensitive Paths — Never Read, Write, or Expose

```
/etc/soc/credentials/          SOC stack credentials
~/.ssh/                        All SSH keys
~/.hermes/.env                 Hermes Agent secrets
~/.hermes/secrets/
~/.config/anthropic/           Anthropic API keys
~/.config/proxmox/token        Proxmox API credentials  ← added
*.key  *.pem  *.p12  *.pfx
*_rsa  *_ed25519  *_ecdsa
.env   .env.*
credentials  secrets
```

If any of the above appears in tool output, treat it as a scrubber miss. Do not
reproduce the content. Note the miss and continue.

### Credential Scrubbing

`hooks/post_tool_use/scrub_output.py` processes all tool output before context
injection, replacing matches with tagged placeholders like `[REDACTED:label]`.

Patterns defined in `hooks/lib/patterns.py`:

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

**First run task:** verify `proxmox_token` UUID pattern exists. If missing, add to
`hooks/lib/patterns.py`:
```python
"proxmox_token": re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
),
```

When a `[REDACTED:*]` tag appears in output:
- Do not attempt to retrieve the original value
- Do not suggest workarounds to access it
- Ask the user to provide it explicitly via environment variable if needed

### Git Safety

- Never force push to `main` or `master`
- Never push to a remote not matching `github.com/distantgeek*`
- Never commit files matching sensitive path patterns above
- Always run `git diff --staged` before committing; flag anything unexpected
- Verify `.gitignore` covers `*.key`, `*.pem`, `.env*`, `credentials`, `token`
  before first commit in any new repo

### Network Boundaries

SSH, SCP, and rsync are allowed only to:
- `192.168.x.x` — homelab LAN
- `10.x.x.x` — homelab VPN/overlay
- `github.com`, `ghcr.io`, `quay.io` — package and registry access

The pre-tool hook enforces this. Do not suggest commands that would bypass it
without explicit user instruction.

---

## Container Paradigm

### Runtime: Podman Only

Never suggest `docker` or `docker-compose`. This environment is Podman exclusively.

| Concept | Convention |
|---------|-----------|
| Runtime | `podman` |
| Compose | `podman-compose` |
| Persistent services | Quadlet `.container` files |
| User services | `systemctl --user` + rootless Podman |
| System services | `systemctl` + rootful Podman |
| User Quadlet path | `~/.config/containers/systemd/` |
| System Quadlet path | `/etc/containers/systemd/` |

After any Quadlet change:
```bash
systemctl --user daemon-reload && systemctl --user start <unit>   # rootless
systemctl daemon-reload && systemctl start <unit>                  # system
```

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
- System installs require `sudo` and must be logged in `DEVBOX_INSTALLED.md`

### Systemd

- Prefer Quadlet `.container` files over bare `podman run` for anything persistent
- `loginctl enable-linger kevbot` required for user services to survive logout
- Verify: `loginctl show-user kevbot | grep Linger`

---

## Toolchain Philosophy

### Pre-installed in the bootc Image

| Tool | Purpose | Notes |
|------|---------|-------|
| `rustup` | Rust toolchain manager | No default toolchain — projects pin via `rust-toolchain.toml` |
| `fnm` | Node version manager | Use this, not nvm or system Node |
| `uv` | Python package manager | Replaces pip + virtualenv + pyenv |
| `mise` | Unified version manager | Node, Python, Ruby, Go via `.mise.toml` |
| `direnv` | Per-directory env loader | Auto-activates `.envrc` on `cd` |
| Node.js LTS | Runtime | One default version via fnm for Claude Code |
| `claude` | Claude Code CLI | Global via fnm-managed Node |
| Git, gh, base tools | Core dev | System packages |

### Ad Hoc Installs

When a project needs a specific toolchain:

1. Check for pin files: `rust-toolchain.toml`, `.node-version`, `.nvmrc`,
   `.mise.toml`, `.python-version`
2. Install via the appropriate manager
3. Prefer project-local toolchains over global
4. Log every install in `DEVBOX_INSTALLED.md` immediately

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
| `make build-image [DEVBOX_USER=name]` | Build bootc image; defaults to `devbox` user |
| `make push-image` | Push to GHCR |
| `make build-disk-image` | Convert to raw disk via bootc-image-builder; output at `output/image/disk.raw` |
| `make deploy VM_HOST=<ip>` | Thin Ansible `configure.yml` against running VM |
| `make upgrade VM_HOST=<ip>` | `bootc upgrade` + reboot on target |
| `make rollback VM_HOST=<ip>` | `bootc rollback` + reboot on target |
| `make configure-hooks VM_HOST=<ip>` | Rsync hook suite, fix permissions |
| `make enable-kubernetes VM_HOST=<ip>` | Optional k8s layer (k3s or KIND) |
| `make validate VM_HOST=<ip>` | Ansible validation playbook |
| `make test-connection VM_HOST=<ip>` | SSH test + bootc status |

**Personal build command (bakes in kevbot user):**
```bash
make build-image DEVBOX_USER=kevbot && make push-image && make upgrade VM_HOST=192.168.2.156
```

**Disk import — PVE 9 requires `qm disk import`, not `qm importdisk`:**
`qm importdisk` silently writes the VM config without creating the LVM volume in PVE 9.
Always use `qm disk import <vmid> <file> <storage>` and verify with `lvs pve | grep vm-<vmid>`.

### Kubernetes — Optional, Not Default

Disabled by default (`ENABLE_KUBERNETES=false` in `.env`). `make enable-kubernetes`
is additive — it does not rebuild the image. kubectl, helm, and k3s or KIND are
installed via `ansible/playbooks/kubernetes.yml` only.

Do not include Kubernetes tooling in `build/Containerfile`.

### Containerfile Layer Order

1. `quay.io/fedora/fedora-bootc:43`
2. System packages (git, podman, buildah, skopeo, tmux, firewalld, python3, etc.)
3. `qemu-guest-agent` + systemd enable
4. bootc filesystem config
5. `fnm` → Node LTS
6. `uv`
7. `rustup` (no default toolchain)
8. `mise`
9. Claude Code CLI (`npm global` via fnm)
10. SAST tools: `bandit`, `pip-audit` (uv tool); `@socketsecurity/cli` (npm); `cargo-audit` (binary)
11. Hook suite → `/etc/skel/.claude/hooks/`
12. `settings.json` + `CLAUDE.md` → `/etc/skel/.claude/`
13. Agents → `/etc/skel/.claude/agents/`
14. Rules → `/etc/skel/.claude/rules/`
15. Rootless Podman config + OpenCode config + `.npmrc` + shell integrations + `DEVBOX_INSTALLED.md` → `/etc/skel/`
16. DEVBOX_USER creation

---

## DEVBOX_INSTALLED.md Convention

`~/DEVBOX_INSTALLED.md` lives on the running devbox VM. Create it before installing
anything if it does not exist.

```markdown
# DEVBOX_INSTALLED.md
_Tracks ad hoc installs. Update on every install outside the base bootc image._

| Date | Tool | Version | Method | Project | Reason |
|------|------|---------|--------|---------|--------|
| (image) | git, podman, buildah | system | dnf | base | Core tooling |
| (image) | fnm, uv, rustup, mise | latest | curl installer | base | Version managers |
| (image) | claude | latest | npm global | base | Claude Code CLI |
```

---

## Working Style

**Change discipline**
- Small, reviewable diffs over large atomic rewrites
- Always show `git diff` or file preview before committing or pushing
- Commit message format: `feat:`, `fix:`, `chore:`, `docs:`, `security:`

**Quadlets**
- Validate before applying — required fields: `[Container]`, `Image=`, `[Install]`
- Always include `Restart=on-failure` unless there is a specific reason not to

**Ansible**
- Idempotent modules over raw shell commands
- `lookup('env', 'VAR')` for credentials — never hardcode
- Tag all tasks to allow targeted runs

**Long-running operations**
- Use `tmux` for anything over a minute: `tmux new -s <task-name>`
- Protects against SSH disconnects killing in-progress work

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

Items Claude Code should know about but **not start without explicit instruction:**

1. **Ansible playbooks** — `configure.yml`, `validate.yml`, `kubernetes.yml` not yet written
2. **Hook test suite** — unit tests for `enforce_permissions.py` and `scrub_output.py`
3. **Proxmox provisioning automation** — full VM creation pipeline from raw disk to
   running devbox
4. **CLAUDE.md tier variants** — minimal/enhanced/containerized template variants
5. **`config/containers/` skeleton** — rootless Podman `registries.conf` and
   `storage.conf` defaults

Do not begin any of the above unless the user asks.
