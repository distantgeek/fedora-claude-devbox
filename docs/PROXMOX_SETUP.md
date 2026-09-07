# Proxmox VM Configuration — open-atomic

Target host: **R820** (node `kevbotpve-0`, PVE 9.2.11, `192.168.2.2`).

## Recommended VM Hardware Settings

### General
| Setting | Value | Reason |
|---------|-------|--------|
| VM Type | KVM | Full virtualization |
| OS Type | Linux 6.x kernel | Correct VirtIO driver set |
| Machine Type | q35 | PCIe support, required for UEFI |
| BIOS | OVMF (UEFI) | Required for bootc/ostree |
| SCSI Controller | VirtIO SCSI Single | Best disk throughput |

### CPU
| Setting | Value | Reason |
|---------|-------|--------|
| CPU Type | **host** | Pass through all flags; rustup/mise need AVX2 |
| Sockets | 1 | Single-socket VM; host is 4× E5-4650 v2 (NUMA 4) |
| Cores | 4 | Comfortable for parallel builds |

> **Note:** the R820 is 4-socket with 4 NUMA nodes. A single-socket VM (1 socket,
> 4 cores) keeps the guest on one NUMA domain. Do NOT use `kvm64` — it strips
> instructions Rust/Node tooling depends on.

### Memory
| Setting | Value | Reason |
|---------|-------|--------|
| RAM | 8192 MB | Comfortable floor; host has 251 GiB available |
| Ballooning | disabled | Avoid latency spikes |

### Disk (ZFS)
| Setting | Value | Reason |
|---------|-------|--------|
| Bus | VirtIO SCSI (scsi0) | Best throughput |
| Storage pool | **`garage-0`** (ZFS `Garage0` raidz2) | ~8.6T free |
| Size | 60 GB | Base image + toolchains + repos |
| Cache | writeback | Fine on ZFS |
| Discard | enabled | TRIM passthrough |
| IO Thread | enabled | Multi-queue performance |

### Network
| Setting | Value | Reason |
|---------|-------|--------|
| Model | VirtIO | Best throughput |
| Bridge | vmbr0 | Direct LAN (`192.168.2.0/24`) |
| Firewall | disabled at Proxmox level | firewalld in the VM handles it |
| MAC Address | static/fixed | Reserve a DHCP lease |

### QEMU Guest Agent
Enabled — already installed + enabled in the image.

### Display
| Setting | Value | Reason |
|---------|-------|--------|
| Display | Serial Terminal | Headless SSH-only |
| Serial | socket (serial0) | Required for serial terminal |

---

## Proxmox API Token

OpenCode manages Proxmox via REST API with a scoped token.

**Current token:** `opencode@pve!opencode0` (host `192.168.2.2`), with a custom role
scoped to VM management. Privilege separation is **enabled** — the token cannot
escalate beyond its ACLs.

Credentials live at `~/.config/proxmox/token` (never committed):

```bash
PROXMOX_HOST=192.168.2.2
PROXMOX_USER=opencode@pve
PROXMOX_TOKEN_NAME=opencode0
PROXMOX_TOKEN_VALUE=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

Source in `~/.bashrc`:
```bash
if [ -f "$HOME/.config/proxmox/token" ]; then
    set -a; source "$HOME/.config/proxmox/token"; set +a
fi
```

### SSH access to the Proxmox host

Disk import and diagnostics need SSH. The dedicated key `~/.ssh/id_ed25519_pve_opencode`
is used for operator (not agent) access. The agent uses short-lived certs via
`grant-session` — see `docs/REMOTE_MANAGEMENT.md`.

---

## Full Deployment Workflow (PVE 9+)

### 1. Build and push

```bash
make build-image DEVBOX_USER=yourname
make build-agent-image
make push-images
```

### 2. Convert to raw disk

```bash
make build-disk-image
# Output at: output/image/disk.raw  (~10GB)
```

### 3. Transfer to the Proxmox host

```bash
scp output/image/disk.raw root@192.168.2.2:/tmp/
```

### 4. Create the VM via API

```bash
set -a && source ~/.config/proxmox/token && set +a

curl -sk -X POST \
  -H "Authorization: PVEAPIToken=${PROXMOX_USER}!${PROXMOX_TOKEN_NAME}=${PROXMOX_TOKEN_VALUE}" \
  -H "Content-Type: application/json" \
  -d '{
    "vmid": <VMID>,
    "name": "open-atomic",
    "machine": "q35",
    "bios": "ovmf",
    "scsihw": "virtio-scsi-single",
    "cpu": "host",
    "cores": 4,
    "sockets": 1,
    "memory": 8192,
    "balloon": 0,
    "net0": "virtio,bridge=vmbr0,firewall=0",
    "agent": "enabled=1",
    "efidisk0": "garage-0:0,efitype=4m,pre-enrolled-keys=0",
    "serial0": "socket",
    "vga": "serial0",
    "ostype": "l26",
    "onboot": 1
  }' \
  "https://${PROXMOX_HOST}:8006/api2/json/nodes/kevbotpve-0/qemu"
```

### 5. Import the disk (PVE 9 — on the Proxmox host)

```bash
ssh root@192.168.2.2 "qm disk import <VMID> /tmp/disk.raw garage-0"

ssh root@192.168.2.2 \
  "qm set <VMID> --scsi0 'garage-0:vm-<VMID>-disk-0,cache=writeback,discard=on,iothread=1'"

ssh root@192.168.2.2 "qm disk resize <VMID> scsi0 60G"
ssh root@192.168.2.2 "qm set <VMID> --boot order=scsi0"
ssh root@192.168.2.2 "rm -f /tmp/disk.raw"
```

> **PVE 9 note:** `qm importdisk` can silently write the VM config without creating the
> volume. Use `qm disk import`. On ZFS, verify with `zfs list | grep vm-<VMID>`.

### 6. Start and get IP

```bash
curl -sk -X POST \
  -H "Authorization: PVEAPIToken=${PROXMOX_USER}!${PROXMOX_TOKEN_NAME}=${PROXMOX_TOKEN_VALUE}" \
  "https://${PROXMOX_HOST}:8006/api2/json/nodes/kevbotpve-0/qemu/<VMID>/status/start"

ssh root@192.168.2.2 "qm guest cmd <VMID> network-get-interfaces"
```

### 7. Initial auth (SSH key is baked in — no password anywhere)

There is **no default user/password**. Both `root` and the devbox user are
created with **locked (no-password) accounts**. SSH key auth is the only way in,
and the key is injected at **image build time**:

```bash
# The Makefile reads ~/.ssh/id_ed25519.pub automatically:
make build-image DEVBOX_USER=yourname
# → passes --build-arg SSH_AUTHORIZED_KEYS="$(cat ~/.ssh/id_ed25519.pub)"
```

The public key is written to the devbox user's `~/.ssh/authorized_keys`. After the
VM boots:

```bash
ssh -i ~/.ssh/id_ed25519 yourname@<devbox-ip>     # first login
```

Use a different key: `make build-image DEVBOX_USER=yourname SSH_KEY=~/.ssh/other_key`
(or set `SSH_PUBKEY` explicitly).

> The devbox user has **no sudo**. SSH gives you the unprivileged shell only —
> there is no root login and no `sudo` escalation on the box. System changes happen
> at build time, not on the running VM (see "Ongoing Upgrade Workflow" below).

---

## Ongoing Upgrade Workflow

```bash
# VM-level change (SELinux policy, system packages):
make build-image DEVBOX_USER=yourname
make push-image
make upgrade VM_HOST=<devbox-ip>

# Framework change (add MCP/plugin):
make build-agent-image
make push-images
# update the agent container on the VM (podman pull + restart)
```

`make rollback VM_HOST=<devbox-ip>` reverts a failed `bootc upgrade`.

## VM Snapshot Strategy

| When | Action | Reason |
|------|--------|--------|
| After initial deploy | Proxmox snapshot: `initial-deploy` | Clean baseline |
| Before first `bootc upgrade` | Proxmox snapshot: `pre-upgrade-v<tag>` | External safety net |
| Before major project work | Proxmox snapshot: `pre-<project>` | Quick restore |
| Routine | Proxmox scheduled backup (weekly) | Persistent coverage |
