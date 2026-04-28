# Building fedora-claude-devbox

## Prerequisites

- Podman installed on the build machine
- Internet access (installers fetched at build time)
- ~4GB free disk space for the build context and image layers

## Basic Build

```bash
make build-image
# Tags: ghcr.io/distantgeek/fedora-claude-devbox:latest
#       ghcr.io/distantgeek/fedora-claude-devbox:<git-sha>
```

Subsequent builds use Podman's layer cache aggressively. Only changed layers rebuild.
The dnf package layer (~800MB) is the slowest — it only rebuilds if the package list changes.

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
# Output: output/disk.raw
# Requires: sudo (bootc-image-builder runs privileged)
```

This uses `quay.io/centos-bootc/bootc-image-builder` to convert the container image
to a bootable raw disk image. The output is suitable for direct import into Proxmox
via `qm importdisk`.

---

## Containerfile Layer Design

Layers are ordered to maximize cache hits during iterative development:

| Layer | Contents | Rebuild trigger |
|-------|----------|-----------------|
| 1 | `FROM fedora-bootc:41` | Base image update |
| 2 | dnf packages | Package list change |
| 3 | systemd enables | Service list change |
| 4 | fnm + Node LTS | fnm version change |
| 5 | uv + uvx | uv version change |
| 6 | rustup binary | rustup version change |
| 7 | mise | mise version change |
| 8 | Claude Code CLI | claude-code version change |
| 9–end | COPY hooks, config, skel | Any file change |

Tool installer layers (4–8) are the most network-intensive. Changing a hook script
only rebuilds layers 9+, which is fast.

---

## Known Build Quirks: `/root` in fedora-bootc

**Problem:** In the fedora-bootc base image, `/root` is a symlink (part of the
ostree/bootc filesystem layout where `/var` is the mutable state layer). This causes
any installer script that writes to `$HOME` during build to fail with `EEXIST` or
`ENOTDIR` errors, because the tools try to create directories under `/root` and
encounter the symlink unexpectedly.

**Affected tools:** uv, rustup, mise, npm (all use `$HOME` for cache or install paths).

**Fix applied in this project:**

| Tool | Solution |
|------|---------|
| uv | Direct tarball download from GitHub releases → `/usr/local/bin/` |
| rustup | Direct `rustup-init` binary download → `/usr/local/bin/rustup` |
| mise | Direct binary download from GitHub releases → `/usr/local/bin/mise` |
| npm (Claude Code) | `HOME=/tmp` prefix on the npm install command |

The `HOME=/tmp` approach for npm works because npm's cache goes to `/tmp/.npm`
(disposable in a build layer), while the actual package installs to the fnm node
prefix under `/usr/local/share/fnm` — a real directory that's accessible system-wide.

**Direct binary installs** are also preferable for a shared system image because the
binaries land in `/usr/local/bin` (in PATH for all users) rather than a root home
directory that non-root users can't access.

---

## System Services Enabled in the Image

These are enabled via `systemctl enable` in the Containerfile and start automatically
on first boot:

| Service | Purpose |
|---------|---------|
| `qemu-guest-agent` | Allows Proxmox to gracefully shut down the VM and report IP addresses |
| `firewalld` | Host-based firewall — rules applied post-deploy via Ansible |
| `podman.socket` | Enables rootless Podman socket activation |

---

## Updating Tool Versions

All tool versions in the image track "latest at build time" via the direct download
approach. To pin to a specific version, modify the relevant `RUN` step:

```dockerfile
# Pin uv to a specific version
RUN curl -fsSL "https://github.com/astral-sh/uv/releases/download/0.x.y/uv-x86_64-unknown-linux-gnu.tar.gz" \
    | tar -xz -C /tmp ...

# Pin mise to a specific version
RUN curl -fsSL "https://github.com/jdx/mise/releases/download/v2024.x.y/mise-v2024.x.y-linux-x64" \
    -o /usr/local/bin/mise ...
```

Node LTS tracks the current LTS release via fnm. To pin:
```dockerfile
RUN fnm install 22 && fnm default 22
```

---

## SELinux in the Build

SELinux policy modules cannot be loaded during `podman build` (no running SELinux
policy service). Custom policy modules should be built separately and applied via
Ansible post-deploy, or baked as pre-compiled `.pp` files with `semodule -i` in
the Containerfile (the placeholder exists in the file).

If AVC denials appear on the running devbox:
```bash
ausearch -m avc -ts recent
audit2allow -M mymodule < /var/log/audit/audit.log
semodule -i mymodule.pp
```

Once stable, add the compiled `.pp` to the repo and install it in the Containerfile.
