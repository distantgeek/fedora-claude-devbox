# Remote Management — Session-Scoped Access

The devbox has **no local root/sudo**. Remote servers (Proxmox, TrueNAS) are managed
via **short-lived SSH certificates** minted per session, plus scoped API tokens where
supported.

## Why SSH Certificates

An SSH CA lets you grant **time-boxed** access without touching the target server each
time. Trust is established **once** (the CA public key is installed on the target);
granting access thereafter is purely local and self-expiring.

## One-Time Setup (per target server)

Generate an SSH CA keypair (held on the VM host, **never** mounted into the agent
container):

```bash
ssh-keygen -t ed25519 -N "" -f ~/.ssh/ca/open-atomic-ca
```

Install the CA **public** key as a `cert-authority` on the target. For the Proxmox host:

```bash
# On the Proxmox host (root), append to /root/.ssh/authorized_keys:
echo "cert-authority $(cat ~/.ssh/ca/open-atomic-ca.pub)" \
  | ssh -i ~/.ssh/id_ed25519_pve_opencode root@192.168.2.2 "cat >> /root/.ssh/authorized_keys"
```

Do this once per target (Proxmox, TrueNAS, etc.).

## Per-Session Grant (local only)

`grant-session` signs the agent's SSH key with the CA private key to produce a
certificate valid for the requested window. This runs entirely on the VM — no server
interaction.

```
grant-session proxmox 30m     # 30-minute cert for the Proxmox host
grant-session truenas 1h      # 1-hour cert for TrueNAS
grant-session --list          # show active sessions
grant-session --revoke <id>   # revoke early
```

The cert is written to `~/.config/opencode/sessions/<target>.cert` inside the container
(the session dir is mounted; the CA key is not). The agent uses the cert for SSH.

## How the Cert Grants Sudo

The cert carries a **principal** (username) and validity window:

- **Principal = root** → the agent SSHes directly as root on the target. No sudo needed.
- **Principal = normal user** → the target's sudoers grants that user scoped elevation.
  Optionally add `force-command` restrictions to scope what the agent can run.

The cert **is** the elevation, and it self-destructs at expiry. No revocation list.

## Scoped API Tokens (where supported)

| Service | Mechanism | Notes |
|---------|-----------|-------|
| GitHub | Fine-grained PAT | Scoped to specific repos + `write:packages` |
| Proxmox | `opencode@pve!opencode0` | Custom role, VM-management scope |
| TrueNAS | — | API keys are root-equivalent → use SSH certs instead |

## grant-session Implementation Notes

- CA key: `~/.ssh/ca/open-atomic-ca` on the VM host (devbox user), mode 0600, **not**
  bind-mounted into the agent container.
- Agent key: a dedicated keypair the agent uses; its public key is what `grant-session`
  signs.
- Session dir: `~/.config/opencode/sessions/` — mounted into the container read-write;
  certs are named by target and overwritten per session.
- Expiry: `ssh-keygen -s ca -V +<duration>` sets the validity window.
