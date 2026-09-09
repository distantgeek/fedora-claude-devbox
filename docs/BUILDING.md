# Building open-atomic

## Prerequisites

- Podman installed on the build machine
- Internet access (tool installers fetched at build time)
- ~6GB free disk space (two images: VM + agent container)

## Two Images

| Image | Containerfile | Contents | Rebuild frequency |
|-------|---------------|----------|-------------------|
| VM bootc image | `build/Containerfile` | Thin shell: podman, devbox user, grant-session, SELinux policy | Rare (VM-level changes) |
| Agent container | `build/agent/Containerfile` | opencode + security framework (plugins, agents, skills, MCPs) | Frequent (MCP/plugin changes) |

Adding an MCP or plugin rebuilds the **agent container** only — minutes, not a bootc
image rebuild.

## Basic Build

```bash
# Public VM image — generic 'devbox' user baked in
make build-image

# Personal build — your username baked in
make build-image DEVBOX_USER=yourname

# Agent container image (opencode + framework)
make build-agent-image
```

Tags: `ghcr.io/distantgeek/open-atomic:latest` and
`ghcr.io/distantgeek/open-atomic-agent:latest` (plus `:<git-sha>`).

## DEVBOX_USER Build Argument

The VM image creates one primary user via `useradd -m` at build time — **no sudo, no
wheel, no podman groups**. The user's home is pre-populated from `/etc/skel` (shell
integrations, `.npmrc`, rootless podman config).

```bash
make build-image                        # DEVBOX_USER=devbox (public default)
make build-image DEVBOX_USER=kevbot     # personal
```

SSH access is via **key only** — no passwords on any account. The operator's public
key (`~/.ssh/id_ed25519.pub`, or `SSH_PUBKEY`) is baked into the user's
`~/.ssh/authorized_keys` via the `SSH_AUTHORIZED_KEYS` build arg at build time.
Override with `SSH_KEY=~/.ssh/other_key` (see `docs/PROXMOX_SETUP.md`).

## Pushing to GHCR

```bash
gh auth refresh --hostname github.com --scopes write:packages
gh auth token | podman login ghcr.io -u distantgeek --password-stdin
make push-images
```

## Converting to Raw Disk for Proxmox

```bash
make build-disk-image
# Output: output/image/disk.raw   (NOT output/disk.raw — bootc-image-builder nests in image/)
# Requires: sudo (bootc-image-builder runs privileged)
```

Uses `quay.io/centos-bootc/bootc-image-builder`. The Containerfile writes
`/usr/lib/bootc/install/10-open-atomic.toml` (explicit root filesystem type) — without
it the build fails with a `DefaultRootFs` error.

---

## Containerfile Layer Design (VM image)

| Layer | Contents | Rebuild trigger |
|-------|----------|-----------------|
| 1 | `FROM fedora-bootc:44` | Base image update |
| 2 | dnf packages (podman, firewalld, qemu-guest-agent, …) | Package list change |
| 3 | systemd enables (qemu-guest-agent, firewalld) | Service list change |
| 4 | bootc filesystem config | Never (static) |
| 5 | grant-session + agent.env.example | Tool/example change |
| 6 | Rootless podman config + agent Quadlet | Infra config change |
| 7 | shell integrations | `.bashrc` change |
| 8 | SSH authorized_keys (`SSH_AUTHORIZED_KEYS`) | Operator key change |
| 9 | DEVBOX_USER creation (no sudo) | DEVBOX_USER arg change |

The agent container (`build/agent/Containerfile`) holds the toolchains (fnm, uv,
rustup, mise), OpenCode CLI, SAST tools, scrub-daddy-llm, and the framework — see
its own layer order in `AGENTS.md`.

---

## Known Build Quirks: `/root` in fedora-bootc

**Problem:** In the fedora-bootc base image, `/root` is a symlink (ostree layout where
`/var` is the mutable state layer). Installers that write to `$HOME` fail with `EEXIST`
or `ENOTDIR`.

**Fix:**

| Tool | Solution |
|------|---------|
| uv | Direct tarball → `/usr/local/bin/` |
| rustup | Direct `rustup-init` binary → `/usr/local/bin/rustup` |
| mise | Direct binary from GitHub releases API → `/usr/local/bin/mise` |
| npm (opencode) | `HOME=/tmp` prefix on the npm install command |

## Agent Container Home (`/home/agent`)

The agent Containerfile pre-creates `/home/agent/.local` (agent-owned) so podman
does **not** create the volume mount-point parents as root. If the parents are
root-owned, the non-root agent user gets `EACCES` creating siblings like
`~/.local/state`. Keep this in the Containerfile whenever the agent home layout
changes.

---

## ostree Filesystem Layout

| Partition | Size | Type | Runtime mount |
|-----------|------|------|---------------|
| p1 | 1MB | BIOS boot | (none) |
| p2 | 501MB | EFI System | `/boot/efi` |
| p3 | 1GB | Linux filesystem | `/boot` |
| p4 | remainder | Linux filesystem | `/` (sysroot) |

Within p4:
```
/ostree/deploy/default/deploy/<hash>/   ← immutable image content (read-only)
/ostree/deploy/default/var/             ← mutable state (persists across upgrades)
```

`/root` maps to `var/roothome/`, `/home` maps to `var/home/`.

---

## System Services Enabled in the VM Image

| Service | Purpose |
|---------|---------|
| `qemu-guest-agent` | Graceful shutdown, IP reporting |
| `firewalld` | Host firewall — rules applied post-deploy via Ansible |

`podman.socket` (root) is **disabled** — the agent container must never see the VM's
podman socket (escape vector). Rootless podman runs under the devbox user.

---

## SELinux in the Build

Policy modules can't load during `podman build`. Build pre-compiled `.pp` files and
`semodule -i` them in the Containerfile, or apply via Ansible post-deploy.

**Known behavior:** the QEMU guest agent (`virtd_t`) can't exec arbitrary binaries —
`qm guest exec` of `ip`/`useradd` fails. Use SSH for VM management.

## Updating Tool Versions

All tools track "latest at build time". Pin by editing the download URLs in the
Containerfile. Node LTS tracks the current LTS via fnm; pin with `fnm install 22`.
