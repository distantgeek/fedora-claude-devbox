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

SSH authorized keys are **not** baked in — injected post-deploy (see
`docs/PROXMOX_SETUP.md`).

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
| 2 | dnf packages | Package list change |
| 3 | systemd enables | Service list change |
| 4 | bootc filesystem config | Never (static) |
| 5 | fnm + Node LTS | fnm version change |
| 6 | uv + uvx | uv version change |
| 7 | rustup binary | rustup version change |
| 8 | mise | mise version change |
| 9 | OpenCode CLI | opencode version change |
| 10 | SAST tools (bandit, pip-audit, socket, cargo-audit) | Tool version changes |
| 11 | Framework → `/etc/opencode/` + `OPENCODE_CONFIG_DIR` | Any config change |
| 12 | Rootless podman config, `.npmrc`, shell integrations | Infra config change |
| 13 | DEVBOX_USER creation (no sudo) | DEVBOX_USER arg change |

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
