# Credentials — Injection & Session Access

How tokens and keys get into the open-atomic agent, and how session-scoped
access works. No credentials are baked into either image — everything is
injected at runtime on the VM host.

## Credential inventory

| Credential | Purpose | Where it lives | Injected how |
|------------|---------|----------------|--------------|
| Model provider keys (`opencode-go`, `openrouter`, …) | LLM access | `~/.local/share/opencode/auth.json` | Persistent volume into the agent container |
| `GITHUB_PAT` | GitHub MCP | `~/.config/open-atomic/agent.env` | `EnvironmentFile` in the Quadlet |
| `CONTEXT7_API_KEY` | Context7 MCP | `~/.config/open-atomic/agent.env` | `EnvironmentFile` in the Quadlet |
| Proxmox API token | Proxmox API (optional) | `~/.config/proxmox/token` (host) | sourced in `.bashrc`; or via `agent.env` |
| SSH session certs | Proxmox/TrueNAS management | `~/.config/opencode/sessions/<target>.cert` | minted by `grant-session` |

## Standing credentials

These persist on the VM host and survive container image updates.

### 1. Model provider keys (`opencode auth login`)

The agent container mounts `~/.local/share/opencode` (host) at
`/home/agent/.local/share/opencode` (container), so opencode's auth store is
persistent and shared.

**First-time setup** — enter the container and authenticate each provider:

```bash
# On the VM host, as the devbox user:
open-atomic                          # alias for `podman exec -it opencode-agent bash`
opencode auth login                  # interactive: pick provider, paste API key
exit
```

This writes `~/.local/share/opencode/auth.json` (host-side), in the form:

```json
{
  "opencode-go": { "type": "api", "key": "sk-..." },
  "openrouter":  { "type": "api", "key": "sk-or-v1-..." }
}
```

**Non-interactive alternative** — write the file directly:

```bash
mkdir -p ~/.local/share/opencode
cat > ~/.local/share/opencode/auth.json << 'EOF'
{"opencode-go": {"type": "api", "key": "sk-YOUR_KEY"}}
EOF
chmod 600 ~/.local/share/opencode/auth.json
systemctl --user restart opencode-agent
```

### 2. MCP / API keys (`agent.env`)

`~/.config/open-atomic/agent.env` is injected into the container via the Quadlet's
`EnvironmentFile=-%h/.config/open-atomic/agent.env` directive — systemd reads the
file and passes each `KEY=VALUE` line as a container env var. The leading `-` makes
the file optional: a fresh box boots cleanly with no secrets.

`make deploy` seeds the file automatically (copies the baked-in
`agent.env.example` → `agent.env`, chmod 600) on first deploy. To add keys:

```bash
vi ~/.config/open-atomic/agent.env     # edit placeholders
chmod 600 ~/.config/open-atomic/agent.env
systemctl --user restart opencode-agent
```

> **Verify:** `podman exec opencode-agent env | grep -E 'GITHUB|CONTEXT7'`

### 3. Proxmox API token (optional)

`~/.config/proxmox/token` is sourced into the **host** shell by the `.bashrc`
block (see AGENTS.md). The agent normally reaches Proxmox via SSH certs
(grant-session); if you also want direct API access, add the four `PROXMOX_*`
vars to `agent.env` (see the example).

## Session-scoped credentials — grant-session

For privileged work on Proxmox/TrueNAS, grant a **short-lived SSH cert**
instead of a standing key. The CA key lives on the host; only the cert is
mounted into the container.

### One-time CA trust setup (per target)

```bash
grant-session --setup              # generates CA key + agent key (first run)

# Install the CA public key as cert-authority on each target (e.g. Proxmox):
cat ~/.ssh/ca/open-atomic-ca.pub \
  | ssh -i ~/.ssh/id_ed25519_pve_opencode root@192.168.2.2 \
      "cat >> /root/.ssh/authorized_keys"
```

### Grant a session

```bash
grant-session proxmox 30m           # 30-minute root cert for the Proxmox host
grant-session truenas 1h            # 1-hour cert for TrueNAS
grant-session --list                # active sessions
grant-session --revoke proxmox      # revoke early
```

The cert lands at `~/.config/opencode/sessions/<target>.cert`, mounted into the
container at `/sessions/<target>.cert`. The agent uses it:

```bash
ssh -i /sessions/proxmox.cert root@192.168.2.2
```

The cert **self-expires** — no revocation list, no cleanup. See
`docs/REMOTE_MANAGEMENT.md` for the full design.

## Adding / rotating a credential

1. **MCP key:** edit `~/.config/open-atomic/agent.env` → `systemctl --user restart opencode-agent`
2. **Model key:** `opencode auth login` (or edit `auth.json`) → `systemctl --user restart opencode-agent`
3. **New target for grant-session:** add a line to `~/.config/open-atomic/targets.conf` + install the CA pubkey on the target once
4. **Rotate the CA key:** `grant-session --setup` regenerates only if absent — delete `~/.ssh/ca/open-atomic-ca*` first, then re-run setup and re-install the CA pubkey on every target
