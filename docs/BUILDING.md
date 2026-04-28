# Building fedora-claude-devbox

## Prerequisites

- Podman installed on the build machine
- Internet access (tool installers fetched at build time)
- ~4GB free disk space for the build context and image layers

## Basic Build

```bash
# Public image — generic 'devbox' user baked in
make build-image

# Personal build — your username in the image, home pre-populated from skel
make build-image DEVBOX_USER=yourname
```

Tags produced: `ghcr.io/distantgeek/fedora-claude-devbox:latest` and `:<git-sha>`

Subsequent builds use Podman's layer cache aggressively. Only changed layers rebuild.
The dnf package layer (~900MB) is the slowest — it only rebuilds if the package list changes.

## DEVBOX_USER Build Argument

The image creates one primary user via `useradd -m` at build time. This user's home
directory is pre-populated from `/etc/skel`, which contains the full Claude Code hook
suite, settings, shell integrations, and DEVBOX_INSTALLED.md.

```bash
# Default (public image — generic name, no personal info)
make build-image                        # DEVBOX_USER=devbox

# Personal deployment — bake in your username
make build-image DEVBOX_USER=kevbot

# Direct podman build
podman build --build-arg DEVBOX_USER=kevbot -f build/Containerfile .
```

SSH authorized keys are **not** baked into the image — they are injected post-deploy
via Ansible or a bootstrap procedure (see `docs/PROXMOX_SETUP.md`).

## Pushing to GHCR

Requires `podman login ghcr.io` with a GitHub PAT that has `write:packages` scope.

```bash
# One-time: add write:packages to your gh token
gh auth refresh --hostname github.com --scopes write:packages

# Log podman into GHCR
gh auth token | podman login ghcr.io -u distantgeek --password-stdin

# Push
make push-image
```

## Converting to Raw Disk for Proxmox

```bash
make build-disk-image
# Output: output/image/disk.raw   (NOT output/disk.raw — bootc-image-builder nests in image/)
# Requires: sudo (bootc-image-builder runs privileged)
```

This uses `quay.io/centos-bootc/bootc-image-builder` to convert the container image
to a bootable raw disk image. The output is suitable for direct import into Proxmox
via `qm disk import` (PVE 9+) or `qm importdisk` (PVE 8).

**Note:** `bootc-image-builder` requires the image to have explicit filesystem root
type metadata. This project writes `/usr/lib/bootc/install/10-fedora-claude-devbox.toml`
in the Containerfile to satisfy this requirement. Without it the build will fail with
a `DefaultRootFs` error.

---

## Containerfile Layer Design

Layers are ordered to maximize cache hits during iterative development:

| Layer | Contents | Rebuild trigger |
|-------|----------|-----------------|
| 1 | `FROM fedora-bootc:43` | Base image update |
| 2 | dnf packages (incl. ansible-core, python3-libselinux) | Package list change |
| 3 | systemd enables | Service list change |
| 4 | bootc filesystem config | Never (static) |
| 5 | fnm + Node LTS | fnm version change |
| 6 | uv + uvx | uv version change |
| 7 | rustup binary | rustup version change |
| 8 | mise | mise version change |
| 9 | Claude Code CLI | claude-code version change |
| 10–14 | COPY hooks, config, skel | Any file change |
| 15 | DEVBOX_USER creation | DEVBOX_USER arg change |

Tool installer layers (5–9) are the most network-intensive. Changing a hook script
only rebuilds layers 10+, which is fast.

---

## Known Build Quirks: `/root` in fedora-bootc

**Problem:** In the fedora-bootc base image, `/root` is a symlink (part of the
ostree/bootc filesystem layout where `/var` is the mutable state layer). Any installer
script that writes to `$HOME` during build fails with `EEXIST` or `ENOTDIR` because
the tools try to create directories under `/root` and encounter the symlink.

**Affected tools:** uv, rustup, mise, npm (all use `$HOME` for cache or install paths).

**Fix applied in this project:**

| Tool | Solution |
|------|---------|
| uv | Direct tarball download from GitHub releases → `/usr/local/bin/` |
| rustup | Direct `rustup-init` binary download → `/usr/local/bin/rustup` |
| mise | Direct binary download from GitHub releases API → `/usr/local/bin/mise` |
| npm (Claude Code) | `HOME=/tmp` prefix on the npm install command |

The `HOME=/tmp` approach for npm works because npm's cache goes to `/tmp/.npm`
(disposable in a build layer), while the actual package installs to the fnm node
prefix under `/usr/local/share/fnm` — a real directory accessible system-wide.

**Direct binary installs** are also preferable for a shared system image because the
binaries land in `/usr/local/bin` (in PATH for all users) rather than a home
directory that only root can access.

---

## ostree Filesystem Layout — What Goes Where

Understanding the ostree layout matters for debugging first-boot issues.

The raw disk image created by bootc-image-builder has this partition layout:

| Partition | Size | Type | Runtime mount |
|-----------|------|------|---------------|
| p1 | 1MB | BIOS boot | (none) |
| p2 | 501MB | EFI System | `/boot/efi` |
| p3 | 1GB | Linux filesystem | `/boot` |
| p4 | remainder | Linux filesystem | `/` (sysroot) |

Within p4, the ostree deployment lives at:
```
/ostree/deploy/default/deploy/<hash>/   ← immutable image content (read-only)
/ostree/deploy/default/var/             ← mutable state (writable, persists across upgrades)
```

At runtime, `/root` (root's home) maps to `var/roothome/` — not to a directory in
the deployment. If you need to inject files for root (e.g. SSH authorized keys) on
a stopped VM, mount p4 and write to:
```
/mnt/vm/ostree/deploy/default/var/roothome/.ssh/authorized_keys
```

Similarly, `/home` maps to `var/home/` and user home directories to `var/home/<user>/`.

---

## System Services Enabled in the Image

| Service | Purpose |
|---------|---------|
| `qemu-guest-agent` | Allows Proxmox to shut down the VM gracefully and report IP |
| `firewalld` | Host-based firewall — rules applied post-deploy via Ansible |
| `podman.socket` | Enables rootless Podman socket activation |

---

## SELinux in the Build

SELinux policy modules cannot be loaded during `podman build` (no running policy service).
Custom policy modules should be built separately and applied via Ansible post-deploy,
or baked as pre-compiled `.pp` files with `semodule -i` in the Containerfile (the
placeholder exists in the file).

**Known SELinux behavior:** The QEMU guest agent (`virtd_t` domain) is restricted from
executing arbitrary binaries inside the VM. This means `qm guest exec` calls that
invoke standard tools like `ip` or `useradd` will fail with "Permission denied" from
SELinux — this is expected and correct behavior. Use SSH for VM management instead.

If AVC denials appear on the running devbox:
```bash
ausearch -m avc -ts recent
audit2allow -M mymodule < /var/log/audit/audit.log
semodule -i mymodule.pp
```

Once stable, add the compiled `.pp` to the repo and install it in the Containerfile.

---

## Updating Tool Versions

All tool versions track "latest at build time" via direct download. To pin:

```dockerfile
# Pin uv
RUN curl -fsSL "https://github.com/astral-sh/uv/releases/download/0.x.y/uv-x86_64-unknown-linux-gnu.tar.gz" \
    | tar -xz -C /tmp ...

# Pin mise
RUN curl -fsSL "https://github.com/jdx/mise/releases/download/v2024.x.y/mise-v2024.x.y-linux-x64" \
    -o /usr/local/bin/mise ...
```

Node LTS tracks the current LTS release via fnm. To pin:
```dockerfile
RUN fnm install 22 && fnm default 22
```
