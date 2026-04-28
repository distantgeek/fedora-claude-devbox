# fedora-claude-devbox

A security-conscious Claude Code development environment built on Fedora bootc,
Podman, and Quadlets. Rewritten for RHEL-family systems from
[intelligentcode-ai/claude-code-vm](https://github.com/intelligentcode-ai/claude-code-vm)
(MIT), with hook-based security enforcement, Proxmox-native deployment, and
Podman/SELinux throughout.

## Philosophy

- **Fedora bootc** — immutable, versioned, rollback-capable system image
- **Podman + Quadlets** — no Docker daemon, rootless by default, SELinux-native
- **Hook-based security** — actual enforcement via PreToolUse/PostToolUse hooks,
  not `settings.json` deny rules (which are unreliable in Claude Code)
- **Version managers, not toolchains** — rustup, fnm, uv, mise pre-installed;
  language toolchains installed ad hoc per project
- **Kubernetes optional** — not installed by default; enable with `make enable-kubernetes`

## Quick Start

```bash
# Build the image
make build-image

# Convert to Proxmox-compatible raw disk
make build-disk-image

# (Import disk to Proxmox — see docs/PROXMOX_SETUP.md)

# After VM is running, run thin configuration
make deploy VM_HOST=192.168.x.x

# Verify
make validate VM_HOST=192.168.x.x
```

## Upgrading

```bash
# After changes to Containerfile or config:
make build-image && make push-image && make upgrade VM_HOST=192.168.x.x

# Rollback if needed:
make rollback VM_HOST=192.168.x.x
```

## Tiers

| Target | What's included |
|--------|----------------|
| Base image | Git, Podman, buildah, skopeo, fnm, uv, rustup, mise, direnv, Claude Code, hooks |
| `make deploy` | firewalld rules, user lingering, SSH keys, API key env wiring |
| `make deploy DEVBOX_TIER=enhanced` | + MCP servers (memory, sequential-thinking, puppeteer, brave-search) |
| `make enable-kubernetes` | kubectl, helm, k3s or KIND |

## Security Model

See `CLAUDE.md` and `hooks/` for details. Short version:
- `hooks/pre_tool_use/enforce_permissions.py` — blocks dangerous operations before execution
- `hooks/post_tool_use/scrub_output.py` — scrubs sensitive data from tool output
- `settings.json` — behavioral guidance only, not a security boundary
- VM isolation (Proxmox) is the outer security boundary

## Proxmox Setup

See `docs/PROXMOX_SETUP.md` for recommended VM hardware settings and
bootc image import workflow.

## Credits

Architectural inspiration and Ansible role patterns from
[intelligentcode-ai/claude-code-vm](https://github.com/intelligentcode-ai/claude-code-vm)
(MIT License). This project is a ground-up rewrite for Fedora/RHEL systems using
Podman, bootc, SELinux, and Proxmox in place of Ubuntu, Docker, and generic VM targets.

## License

Apache 2.0
